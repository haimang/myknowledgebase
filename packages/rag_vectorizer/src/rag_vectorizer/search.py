from __future__ import annotations

import json
from sqlite3 import Connection, Row

from storage_objects import FileSystemObjectStore
from vector_sqlite_vec import VectorStore

from .embedder import default_embedder


class SearchService:
    def __init__(
        self,
        core_conn: Connection,
        vec_conn: Connection,
        workspace_key: str,
        object_store: FileSystemObjectStore,
    ) -> None:
        self.core_conn = core_conn
        self.vec_store = VectorStore(vec_conn, workspace_key=workspace_key)
        self.object_store = object_store

    def search(self, team_id: str, query: str, limit: int = 6) -> list[dict]:
        return self._search_internal(team_id=team_id, query=query, limit=limit)["items"]

    def search_debug(self, team_id: str, query: str, limit: int = 6) -> dict:
        result = self._search_internal(team_id=team_id, query=query, limit=limit)
        return {
            "query": query,
            "count": len(result["items"]),
            "candidate_count": result["candidate_count"],
            "hydrated_count": result["hydrated_count"],
            "filtered_count": len(result["filtered"]),
            "filtered": result["filtered"],
            "items": result["items"],
        }

    def _search_internal(self, *, team_id: str, query: str, limit: int) -> dict:
        # F5-01: 写/查共用同一 Embedder (⛔3); F5-03: 按交付模型名过滤,
        # 跨 embedding_model 向量不混算 cosine (G-CR3-10)。
        embedder = default_embedder()
        embedding = embedder.embed(query)
        hits = self.vec_store.search(
            embedding=embedding,
            team_id=team_id,
            top_k=max(limit * 2, 12),
            embedding_model=embedder.name,
        )
        if not hits:
            return {"items": [], "candidate_count": 0, "hydrated_count": 0, "filtered": []}
        chunk_ids = [hit["chunk_id"] for hit in hits]
        placeholders = ",".join("?" for _ in chunk_ids)
        rows = self.core_conn.execute(
            f"""
            SELECT
              h.chunk_id,
              h.document_id,
              h.document_title AS title,
              h.canonical_uri,
              h.core_post_filter_eligible,
              h.core_post_filter_reason,
              c.content_hash,
              a.object_key,
              a.metadata_json
            FROM v_search_hydration h
            JOIN chunks c ON c.id = h.chunk_id
            LEFT JOIN artifacts a ON a.id = c.content_artifact_id
            WHERE c.team_id = ?
              AND c.vec_status = 'vectorized'
              AND h.chunk_id IN ({placeholders})
            """,
            (team_id, *chunk_ids),
        ).fetchall()
        by_id = {row["chunk_id"]: row for row in rows}
        results: list[dict] = []
        filtered: list[dict] = []
        for hit in hits:
            row: Row | None = by_id.get(hit["chunk_id"])
            if row is None:
                filtered.append(
                    {
                        "chunk_id": hit["chunk_id"],
                        "score": float(hit["score"]),
                        "reason": "missing_hydration",
                    }
                )
                continue
            if int(row["core_post_filter_eligible"] or 0) != 1:
                filtered.append(
                    {
                        "chunk_id": row["chunk_id"],
                        "score": float(hit["score"]),
                        "reason": row["core_post_filter_reason"] or "core_post_filter_blocked",
                    }
                )
                continue
            chunk_text = self._load_chunk_text(row)
            if not chunk_text:
                filtered.append(
                    {
                        "chunk_id": row["chunk_id"],
                        "score": float(hit["score"]),
                        "reason": "empty_chunk_text",
                    }
                )
                continue
            results.append(
                {
                    "chunk_id": row["chunk_id"],
                    "document_id": row["document_id"],
                    "title": row["title"],
                    "canonical_uri": row["canonical_uri"],
                    "chunk_text": chunk_text,
                    "score": float(hit["score"]),
                }
            )
            if len(results) >= limit:
                break
        return {
            "items": results,
            "candidate_count": len(hits),
            "hydrated_count": len(rows),
            "filtered": filtered,
        }

    def _load_chunk_text(self, row: Row) -> str:
        object_key = row["object_key"]
        if object_key and self.object_store.exists(object_key):
            return self.object_store.get_text(object_key).strip()
        metadata = row["metadata_json"]
        if not metadata:
            return ""
        try:
            payload = json.loads(metadata)
        except json.JSONDecodeError:
            return ""
        text = payload.get("text")
        if isinstance(text, str):
            return text.strip()
        return ""
