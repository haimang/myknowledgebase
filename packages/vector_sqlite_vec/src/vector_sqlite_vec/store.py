from __future__ import annotations

import json
import math
from hashlib import sha256
from sqlite3 import Connection


class VectorStore:
    def __init__(self, conn: Connection, *, workspace_key: str = "default") -> None:
        self.conn = conn
        self.workspace_key = workspace_key

    def upsert_chunk(
        self,
        *,
        chunk_id: str,
        team_id: str = "team_default",
        workflow_run_id: str = "run_default",
        document_id: str = "doc_default",
        namespace_id: str = "ns_default",
        embedding_rowid: int | None = None,
        embedding_model: str = "local-sim",
        content_hash: str | None = None,
        embedding: list[float],
    ) -> None:
        self._ensure_namespace(
            namespace_id=namespace_id,
            team_id=team_id,
            embedding_model=embedding_model,
        )
        # F4-03: rowid 分配三态优先级——
        #   1) 显式传入 embedding_rowid 优先;
        #   2) 同 chunk_id 已存在 (含软删行) → 复用其 rowid, 消除 R3 孤儿累积;
        #   3) 否则分配单调不复用的新 rowid (基于含软删行 MAX+1, 消除 R4 重号)。
        if embedding_rowid is not None:
            rowid = embedding_rowid
        else:
            existing = self.conn.execute(
                "SELECT embedding_rowid FROM vector_records WHERE chunk_id = ?",
                (chunk_id,),
            ).fetchone()
            rowid = (
                int(existing["embedding_rowid"])
                if existing is not None
                else self._next_embedding_rowid()
            )
        digest = (
            content_hash
            or sha256(
                f"{chunk_id}:{len(embedding)}:{self.workspace_key}".encode("utf-8")
            ).hexdigest()
        )
        self.conn.execute(
            """
            INSERT OR REPLACE INTO vector_records (
                chunk_id, team_id, workflow_run_id, document_id, namespace_id,
                embedding_rowid, embedding_model, embedding_dimension,
                content_hash, updated_at, deleted_at
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, 1536, ?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'), NULL
            )
            """,
            (
                chunk_id,
                team_id,
                workflow_run_id,
                document_id,
                namespace_id,
                rowid,
                embedding_model,
                digest,
            ),
        )
        self.conn.execute(
            """
            INSERT OR REPLACE INTO chunk_embedding_index (rowid, embedding)
            VALUES (?, ?)
            """,
            (rowid, json.dumps(embedding)),
        )
        self.conn.commit()

    def delete_chunk(self, chunk_id: str) -> None:
        row = self.conn.execute(
            "SELECT embedding_rowid FROM vector_records WHERE chunk_id = ?",
            (chunk_id,),
        ).fetchone()
        if not row:
            return
        # F4-04 软/硬删统一: 仅软删 vector_records (置 deleted_at), 保留
        # chunk_embedding_index 行——使 rowid ↔ embedding_rowid 一一对应在含软删行
        # 的全集上恒成立, 软删审计不被抹除 (R9 不一致 + R3/R4 空洞镜像消除)。
        # search 已按 vr.deleted_at IS NULL 过滤, 软删 index 行不会被检索命中。
        self.conn.execute(
            """
            UPDATE vector_records
            SET deleted_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now'),
                updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            WHERE chunk_id = ?
            """,
            (chunk_id,),
        )
        self.conn.commit()

    def search(self, *, embedding: list[float], team_id: str, top_k: int = 10) -> list[dict]:
        rows = self.conn.execute(
            """
            SELECT vr.chunk_id, cei.embedding
            FROM vector_records vr
            JOIN chunk_embedding_index cei ON cei.rowid = vr.embedding_rowid
            WHERE vr.deleted_at IS NULL AND vr.team_id = ?
            """,
            (team_id,),
        ).fetchall()
        scored: list[dict] = []
        for row in rows:
            candidate = json.loads(row["embedding"])
            score = _cosine(embedding, candidate)
            scored.append({"chunk_id": row["chunk_id"], "score": score})
        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[:top_k]

    def delete_chunks(self, chunk_ids: list[str]) -> int:
        deleted = 0
        for chunk_id in chunk_ids:
            row = self.conn.execute(
                """
                SELECT embedding_rowid
                FROM vector_records
                WHERE chunk_id = ? AND deleted_at IS NULL
                """,
                (chunk_id,),
            ).fetchone()
            if row is None:
                continue
            self.delete_chunk(chunk_id)
            deleted += 1
        return deleted

    def _next_embedding_rowid(self) -> int:
        # F4-03: 单调不复用。基于 vector_records 含软删行的 MAX(embedding_rowid)+1
        # (而非会被硬删的 chunk_embedding_index, 即 R4 根因)。delete_chunk 不再硬删
        # vector_records 行 (软删保留 embedding_rowid), 故 MAX 始终前进、rowid 永不回收。
        row = self.conn.execute(
            "SELECT COALESCE(MAX(embedding_rowid), 0) + 1 AS next_id FROM vector_records"
        ).fetchone()
        return int(row["next_id"])

    def _ensure_namespace(self, *, namespace_id: str, team_id: str, embedding_model: str) -> None:
        exists = self.conn.execute(
            "SELECT 1 FROM vector_namespaces WHERE id = ?",
            (namespace_id,),
        ).fetchone()
        if exists:
            return
        self.conn.execute(
            """
            INSERT INTO vector_namespaces (
              id, team_id, namespace_key, embedding_model, embedding_dimension,
              distance_metric, status
            ) VALUES (?, ?, ?, ?, 1536, 'cosine', 'active')
            """,
            (namespace_id, team_id, self.workspace_key, embedding_model),
        )
        self.conn.commit()


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    limit = min(len(a), len(b))
    dot = sum(a[i] * b[i] for i in range(limit))
    norm_a = math.sqrt(sum(a[i] * a[i] for i in range(limit)))
    norm_b = math.sqrt(sum(b[i] * b[i] for i in range(limit)))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)
