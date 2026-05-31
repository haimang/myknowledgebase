from __future__ import annotations

import hashlib
import json
from sqlite3 import Connection, Row

from rag_constructor import build_chunks
from rag_structurizer import structurize_text
from rag_vectorizer import embed_text
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
        structured_artifact = _latest_artifact(conn, run["id"], "structured_json")
        structured = _artifact_payload(structured_artifact)
        chunks = build_chunks(structured.get("paragraphs", []))
        vector_store = VectorStore(vec_conn, workspace_key=workspace_key)
        chunk_ids: list[str] = []
        for index, text in enumerate(chunks):
            # F3-03: deterministic ids -> re-execution rewrites identical rows.
            chunk_id = f"{run['id']}:{index}"
            content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
            chunk_text_artifact_id = deterministic_artifact_id(step_id, f"chunk_text:{index}")
            chunk_text_key = f"chunks/{run['team_id']}/{run['id']}/{index}.txt"
            object_store.put_text(chunk_text_key, text)
            conn.execute(
                """
                INSERT OR IGNORE INTO artifacts(
                  id, team_id, workflow_run_id, workflow_step_id, source_id, document_id,
                  artifact_type, storage_backend, object_key, mime_type, content_hash,
                  size_bytes, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, 'chunk_text', 'object_store', ?, 'text/plain', ?, ?, ?)
                """,
                (
                    chunk_text_artifact_id,
                    run["team_id"],
                    run["id"],
                    step["id"],
                    run["source_id"],
                    run["document_id"],
                    chunk_text_key,
                    content_hash,
                    len(text.encode("utf-8")),
                    json.dumps({"chunk_index": index}),
                ),
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO chunks(
                  id, team_id, workflow_run_id, document_id,
                  source_artifact_id, content_artifact_id,
                  chunk_index, content_hash, token_count, char_count, section_path_json, vec_status,
                  embedding_model, latest_vectorized_at
                )
                VALUES (
                  ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                  'pending_vectorize', 'local-sim', NULL
                )
                """,
                (
                    chunk_id,
                    run["team_id"],
                    run["id"],
                    run["document_id"],
                    structured_artifact["id"],
                    chunk_text_artifact_id,
                    index,
                    content_hash,
                    max(1, len(text.split())),
                    len(text),
                    json.dumps([]),
                ),
            )
            vector_store.upsert_chunk(
                chunk_id=chunk_id,
                team_id=run["team_id"],
                workflow_run_id=run["id"],
                document_id=run["document_id"],
                namespace_id=f"ns_{run['team_id']}",
                embedding_model="local-sim",
                content_hash=content_hash,
                embedding=embed_text(text),
            )
            conn.execute(
                """
                UPDATE chunks
                SET vec_status = 'vectorized',
                    latest_vectorized_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now'),
                    updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                WHERE id = ?
                """,
                (chunk_id,),
            )
            chunk_ids.append(chunk_id)
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
            SET status = 'active',
                latest_constructed_artifact_id = ?,
                latest_vectorized_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now'),
                updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            WHERE id = ?
            """,
            (constructed_artifact_id, run["document_id"]),
        )
        # Terminal rag stage: kernel advances the run to completed.
        return ExecutorResult(run_advance={"status": "completed", "current_stage": "completed"})

    raise ValueError(f"unsupported rag stage: {stage}")
