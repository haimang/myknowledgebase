from __future__ import annotations

import hashlib
import json
from sqlite3 import Connection, Row

from provider_runtime import make_embedder
from rag_constructor import build_section_chunks, build_summary, with_context_header
from rag_structurizer import structurize_text
from smind_config import load_settings
from storage_objects import FileSystemObjectStore
from vector_sqlite_vec import VectorStore
from workflow_core.executors import (
    DownstreamStep,
    ExecutorResult,
    deterministic_artifact_id,
)


def _latest_artifact(conn: Connection, run_id: str, kind: str) -> Row:
    row = conn.execute(
        """
        SELECT id, metadata_json
        FROM artifacts
        WHERE workflow_run_id = ? AND artifact_type = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (run_id, kind),
    ).fetchone()
    if row is None:
        raise ValueError(f"artifact missing: {kind}")
    return row


def _artifact_payload(row: Row) -> dict:
    return json.loads(row["metadata_json"] or "{}")


def process_rag_step(
    conn: Connection,
    vec_conn: Connection,
    workspace_key: str,
    step_id: str,
    object_store: FileSystemObjectStore,
) -> ExecutorResult:
    """RAG executor (F3-02 contract): write data side-effects with deterministic
    idempotency keys and RETURN downstream/run-advance intent. Does NOT mark the
    step succeeded, set the run terminal state, or commit — the kernel
    (succeed_claim) owns terminal state inside the claim transaction.
    """
    step = conn.execute("SELECT * FROM workflow_steps WHERE id = ?", (step_id,)).fetchone()
    if step is None:
        raise ValueError(f"step not found: {step_id}")
    run = conn.execute(
        "SELECT * FROM workflow_runs WHERE id = ?", (step["workflow_run_id"],)
    ).fetchone()
    if run is None:
        raise ValueError(f"run not found: {step['workflow_run_id']}")
    stage = step["stage"]

    if stage == "rag:structurize":
        cleaned_artifact = _latest_artifact(conn, run["id"], "cleaned_text")
        cleaned = _artifact_payload(cleaned_artifact)
        structured = structurize_text(cleaned.get("text", ""))
        structured_artifact_id = deterministic_artifact_id(step_id, "structured_json")
        conn.execute(
            """
            INSERT OR IGNORE INTO artifacts(
              id, team_id, workflow_run_id, workflow_step_id, source_id, document_id,
              artifact_type, storage_backend, mime_type, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, 'structured_json', 'sqlite_ref', 'application/json', ?)
            """,
            (
                structured_artifact_id,
                run["team_id"],
                run["id"],
                step["id"],
                run["source_id"],
                run["document_id"],
                json.dumps(structured),
            ),
        )
        conn.execute(
            """
            UPDATE documents
            SET latest_structured_artifact_id = ?,
                updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            WHERE id = ?
            """,
            (structured_artifact_id, run["document_id"]),
        )
        return ExecutorResult(
            downstream=[
                DownstreamStep(
                    step_key=f"rag:construct:{step_id}",
                    stage="rag:construct",
                    action="rag.construct",
                    payload={"run_id": run["id"]},
                )
            ],
        )

    if stage == "rag:construct":
        # F6-05: 消费 structurize 的 sections, 产 original + summary 双通道, 确定性
        # chunk_id (channel 维度); F6-06: 仅落 chunk(pending_vectorize) + 文本 artifact,
        # 不内联 embed/upsert (向量化拆出独立 rag:vectorize step)。
        structured_artifact = _latest_artifact(conn, run["id"], "structured_json")
        structured = _artifact_payload(structured_artifact)
        sections = structured.get("sections") or []
        if not sections:
            paras = structured.get("paragraphs") or []
            if paras:
                sections = [
                    {"heading": "", "level": 0, "text": "\n".join(paras), "order": 0}
                ]
        title = (structured.get("context_meta") or {}).get("title", "")
        chunks = build_section_chunks(sections)
        chunk_ids: list[str] = []
        row_index = 0
        for ch in chunks:
            channels = [("original", with_context_header(ch, title=title))]
            summary_text = build_summary(ch)
            if summary_text:
                channels.append(("summary", summary_text))
            for channel, ctext in channels:
                # F6-05: 确定性 chunk_id (document_id:logical_index:channel) — replay 幂等。
                chunk_id = hashlib.sha256(
                    f"{run['document_id']}:{ch.index}:{channel}".encode("utf-8")
                ).hexdigest()
                # channel 入 content_hash → 满足 UNIQUE(document_id, content_hash)。
                content_hash = hashlib.sha256(f"{channel}:{ctext}".encode("utf-8")).hexdigest()
                artifact_id = deterministic_artifact_id(
                    step_id, f"chunk_text:{ch.index}:{channel}"
                )
                text_key = f"chunks/{run['team_id']}/{run['id']}/{ch.index}_{channel}.txt"
                object_store.put_text(text_key, ctext)
                conn.execute(
                    """
                    INSERT OR IGNORE INTO artifacts(
                      id, team_id, workflow_run_id, workflow_step_id, source_id, document_id,
                      artifact_type, storage_backend, object_key, mime_type, content_hash,
                      size_bytes, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, 'chunk_text', 'object_store', ?, 'text/plain', ?, ?, ?)
                    """,
                    (
                        artifact_id,
                        run["team_id"],
                        run["id"],
                        step["id"],
                        run["source_id"],
                        run["document_id"],
                        text_key,
                        content_hash,
                        len(ctext.encode("utf-8")),
                        json.dumps(
                            {"chunk_index": ch.index, "channel": channel,
                             "section_path": ch.section_path}
                        ),
                    ),
                )
                cur = conn.execute(
                    """
                    INSERT OR IGNORE INTO chunks(
                      id, team_id, workflow_run_id, document_id,
                      source_artifact_id, content_artifact_id,
                      chunk_index, content_hash, token_count, char_count, section_path_json,
                      vec_status, embedding_model, latest_vectorized_at
                    )
                    VALUES (
                      ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                      'pending_vectorize', ?, NULL
                    )
                    """,
                    (
                        chunk_id,
                        run["team_id"],
                        run["id"],
                        run["document_id"],
                        structured_artifact["id"],
                        artifact_id,
                        row_index,
                        content_hash,
                        max(1, len(ctext.split())),
                        len(ctext),
                        json.dumps([ch.section_path] if ch.section_path else []),
                        make_embedder(load_settings()).name,
                    ),
                )
                # M2: 仅在实际插入 (rowcount==1) 时计入 chunk_ids; UNIQUE(document_id,
                # content_hash) 命中被 OR IGNORE 跳过的重复内容不计 (修 chunk_count 虚高)。
                # replay 时同 chunk_id 已存在也会 rowcount==0, 不重复计 —— 仍幂等。
                if cur.rowcount == 1:
                    chunk_ids.append(chunk_id)
                row_index += 1
        constructed_artifact_id = deterministic_artifact_id(step_id, "constructed_json")
        conn.execute(
            """
            INSERT OR IGNORE INTO artifacts(
              id, team_id, workflow_run_id, workflow_step_id, source_id, document_id,
              artifact_type, storage_backend, mime_type, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, 'constructed_json', 'sqlite_ref', 'application/json', ?)
            """,
            (
                constructed_artifact_id,
                run["team_id"],
                run["id"],
                step["id"],
                run["source_id"],
                run["document_id"],
                json.dumps({"chunk_ids": chunk_ids, "chunk_count": len(chunk_ids)}),
            ),
        )
        conn.execute(
            """
            UPDATE documents
            SET latest_constructed_artifact_id = ?,
                updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            WHERE id = ?
            """,
            (constructed_artifact_id, run["document_id"]),
        )
        # F6-06: 向量化拆为独立 step (可 claim/重试/重启); 不在此 embed/upsert。
        return ExecutorResult(
            downstream=[
                DownstreamStep(
                    step_key=f"rag:vectorize:{step_id}",
                    stage="rag:vectorize",
                    action="rag.vectorize",
                    payload={"run_id": run["id"]},
                )
            ],
            run_advance={"status": "running", "current_stage": "rag:vectorize"},
        )

    if stage == "rag:vectorize":
        # F6-06: 独立向量化 step — 查 pending_vectorize chunk (含 original+summary 双通道),
        # 调 F5 Embedder (本地 1024, RWA-09) → upsert (F4-03 按 chunk_id 复用 rowid) → 回写 vectorized。
        # 五步序 (CR-7 R5): core chunk(pending) 已由 construct step 持久 → 此处 upsert vec →
        # 回写 core vectorized; 崩溃 replay 依 pending_vectorize 幂等重做 (确定性 chunk_id + 复用 rowid)。
        # L1: 写侧 workspace_key 用 run.team_id, 与 search 读侧 (workspace_key=team_id) 一致
        # (取代传入的 app_env, 消除 namespace_key/content_hash 兜底的写读错配潜在地雷)。
        vector_store = VectorStore(vec_conn, workspace_key=run["team_id"])
        # RWA-04: 写侧 embedder 经工厂装配 (与查侧同 provider → 同 name, ⛔3 写查一致)。
        embedder = make_embedder(load_settings())
        rows = conn.execute(
            """
            SELECT c.id, c.content_hash, c.document_id, a.object_key
            FROM chunks c
            JOIN artifacts a ON a.id = c.content_artifact_id
            WHERE c.workflow_run_id = ? AND c.vec_status = 'pending_vectorize'
            """,
            (run["id"],),
        ).fetchall()
        for row in rows:
            text = object_store.get_text(row["object_key"])
            vector_store.upsert_chunk(
                chunk_id=row["id"],
                team_id=run["team_id"],
                workflow_run_id=run["id"],
                document_id=row["document_id"],
                namespace_id=f"ns_{run['team_id']}",
                embedding_model=embedder.name,
                content_hash=row["content_hash"],
                embedding=embedder.embed(text),
            )
            conn.execute(
                """
                UPDATE chunks
                SET vec_status = 'vectorized',
                    latest_vectorized_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now'),
                    updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                WHERE id = ?
                """,
                (row["id"],),
            )
        conn.execute(
            """
            UPDATE documents
            SET status = 'active',
                latest_vectorized_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now'),
                updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            WHERE id = ?
            """,
            (run["document_id"],),
        )
        # Terminal rag stage: kernel advances the run to completed.
        return ExecutorResult(run_advance={"status": "completed", "current_stage": "completed"})

    raise ValueError(f"unsupported rag stage: {stage}")
