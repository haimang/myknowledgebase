from __future__ import annotations

import json
import logging
from hashlib import sha256
from sqlite3 import Connection

from .vector_index import BruteForceVectorIndex, Vec0VectorIndex

logger = logging.getLogger("vector_sqlite_vec.store")

# RWA-09 (Q-RW-1): 向量维度单点常量 (覆盖原散落字面 1536)。必须与
# rag_vectorizer.DIMENSION 一致 (跨包不变量, 由 test_rw_a_provider_base 守)。
EMBEDDING_DIMENSION = 1024


class VectorStore:
    def __init__(
        self,
        conn: Connection,
        *,
        workspace_key: str = "default",
        vector_index: str = "bruteforce",
    ) -> None:
        self.conn = conn
        self.workspace_key = workspace_key
        # RW-D / R1 fix: 候选式排序索引选型经此参数贯穿 (上层把 Settings.vector_index 注入),
        # 取代原先 search 硬编码 BruteForceVectorIndex (使 Settings.vector_index 成死配置)。
        # 默认 bruteforce (零回归); "vec0" → Vec0VectorIndex (扩展不可载即 fail-loud, 不静默退化)。
        self.vector_index = vector_index

    def _embedding_index_is_native_vec0(self) -> bool:
        """探测持久 chunk_embedding_index 是否为真实 vec0 虚表 (而非降级 TEXT 表)。

        R2 fix: VectorStore 以 JSON 文本读写 chunk_embedding_index, 仅在 schema 降级为
        TEXT 表时自洽。若有人把 sqlite-vec 扩展载入本连接, vec.sql 会建出真实 vec0 虚表
        (float[N]), 此时 JSON 读写与之**不兼容** (须 serialize_float32)。本探测供写/查侧
        在该错配态 fail-loud, 杜绝静默写坏 / 读崩 (owner 关注的『数据库读写错乱』地雷)。
        """
        row = self.conn.execute(
            "SELECT sql FROM sqlite_master WHERE name = 'chunk_embedding_index'"
        ).fetchone()
        sql = (row["sql"] if row else "") or ""
        return "vec0" in sql.lower()

    def _guard_json_store_compatible(self) -> None:
        if self._embedding_index_is_native_vec0():
            raise RuntimeError(
                "chunk_embedding_index is a native vec0 virtual table, but VectorStore "
                "persists embeddings as JSON text (reason=vec0_native_store_unimplemented). "
                "Do NOT load the sqlite-vec extension into the core/vec store connection "
                "until the serialize_float32 read/write migration lands (RW-D carry-over: "
                "持久 vec0 store 集成). Vec0VectorIndex ranking works on JSON-loaded "
                "candidates without a native persistent table."
            )

    def _make_query_index(self, metric: str):  # noqa: ANN202
        """按 self.vector_index 构建候选式排序索引 (R1: honor Settings.vector_index)。"""
        if self.vector_index == "vec0":
            return Vec0VectorIndex(metric)
        return BruteForceVectorIndex(distance_metric=metric)

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
        # R2: 写前确认持久索引非真实 vec0 虚表 (JSON 写入与 vec0 float 列不兼容)。
        self._guard_json_store_compatible()
        # RWA-09: 写侧维度守卫 — 维度漂移 fail-loud (TR-2/TR-4, 撞 DB CHECK 前先拦)。
        dim = len(embedding)
        if dim != EMBEDDING_DIMENSION:
            raise ValueError(
                f"embedding dimension drift on write: {dim} != {EMBEDDING_DIMENSION} "
                f"(chunk_id={chunk_id}, reason=embedding_dimension_mismatch)"
            )
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
                ?, ?, ?, ?, ?, ?, ?, ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'), NULL
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
                dim,
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

    def search(
        self,
        *,
        embedding: list[float],
        team_id: str,
        top_k: int = 10,
        namespace_id: str | None = None,
        embedding_model: str | None = None,
    ) -> list[dict]:
        # F5-03: 候选集过滤——除 team 外可按 namespace_id/embedding_model 收窄,
        # 避免跨命名空间/跨模型向量混算 cosine (G-CR3-10, ⛔2)。
        where = ["vr.deleted_at IS NULL", "vr.team_id = ?"]
        params: list[str] = [team_id]
        if namespace_id is not None:
            where.append("vr.namespace_id = ?")
            params.append(namespace_id)
        if embedding_model is not None:
            where.append("vr.embedding_model = ?")
            params.append(embedding_model)
        else:
            # 向后兼容缺省 (维持 team 维度); 记 degraded 提示, 不静默。
            logger.debug(
                "vector search without embedding_model filter (team=%s ns=%s) "
                "reason=unscoped_model_degraded_team_wide",
                team_id,
                namespace_id,
            )
        # R2: 读前确认持久索引非真实 vec0 虚表 (否则 cei.embedding 是 blob, json.loads 崩)。
        self._guard_json_store_compatible()
        rows = self.conn.execute(
            f"""
            SELECT vr.chunk_id, cei.embedding
            FROM vector_records vr
            JOIN chunk_embedding_index cei ON cei.rowid = vr.embedding_rowid
            WHERE {' AND '.join(where)}
            """,
            tuple(params),
        ).fetchall()
        candidates = [(row["chunk_id"], json.loads(row["embedding"])) for row in rows]
        # F5-03: distance_metric 从 namespace 配置读取并生效 (非硬编码 cosine, R10)。
        # R1: 索引实现按 self.vector_index 选 (BruteForce 默认 / Vec0VectorIndex), 不再硬编码。
        index = self._make_query_index(self._resolve_metric(namespace_id))
        ranked = index.query(embedding, candidates, top_k)
        return [{"chunk_id": chunk_id, "score": score} for chunk_id, score in ranked]

    def _resolve_metric(self, namespace_id: str | None) -> str:
        if namespace_id is None:
            return "cosine"
        row = self.conn.execute(
            "SELECT distance_metric FROM vector_namespaces WHERE id = ?",
            (namespace_id,),
        ).fetchone()
        return row["distance_metric"] if row and row["distance_metric"] else "cosine"

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
            ) VALUES (?, ?, ?, ?, ?, 'cosine', 'active')
            """,
            (namespace_id, team_id, self.workspace_key, embedding_model, EMBEDDING_DIMENSION),
        )
        self.conn.commit()
