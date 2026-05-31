from __future__ import annotations

import json
from sqlite3 import Connection
from urllib.error import URLError
from urllib.request import urlopen
from uuid import uuid4

from cleaners_universal import clean_payload
from providers_dedicated import maybe_clean_with_provider
from smind_common.time import utc_now_iso
from storage_objects import FileSystemObjectStore


def _load_raw_payload(
    conn: Connection,
    object_store: FileSystemObjectStore,
    source_id: str,
    source_kind: str,
) -> str:
    if source_kind == "file":
        row = conn.execute(
            """
            SELECT u.object_key
            FROM sources s
            JOIN uploads u ON u.id = s.upload_id
            WHERE s.id = ?
            ORDER BY u.created_at DESC
            LIMIT 1
            """,
            (source_id,),
        ).fetchone()
        if row is None:
            return ""
        return object_store.get_text(row["object_key"]).strip()
    if source_kind == "static":
        rows = conn.execute(
            "SELECT object_key FROM static_files WHERE source_id = ? ORDER BY created_at",
            (source_id,),
        ).fetchall()
        return "\n\n".join(object_store.get_text(row["object_key"]).strip() for row in rows).strip()
    if source_kind == "url":
        row = conn.execute("SELECT source_uri FROM sources WHERE id = ?", (source_id,)).fetchone()
        if row is None or not row["source_uri"]:
            return ""
        try:
            with urlopen(row["source_uri"], timeout=10) as response:  # noqa: S310
                return response.read().decode("utf-8", errors="ignore")
        except URLError:
            return row["source_uri"].strip()
    if source_kind == "api":
        row = conn.execute(
            "SELECT metadata_json, source_uri FROM sources WHERE id = ?",
            (source_id,),
        ).fetchone()
        if row is None:
            return ""
        payload = json.loads(row["metadata_json"] or "{}")
        if isinstance(payload, dict) and isinstance(payload.get("text"), str):
            return payload["text"].strip()
        if payload:
            return json.dumps(payload, ensure_ascii=False)
        return (row["source_uri"] or "").strip()
    row = conn.execute("SELECT source_uri FROM sources WHERE id = ?", (source_id,)).fetchone()
    return (row["source_uri"] if row else "").strip()


def process_clean_step(conn: Connection, step_id: str, object_store: FileSystemObjectStore) -> None:
    step = conn.execute("SELECT * FROM workflow_steps WHERE id = ?", (step_id,)).fetchone()
    if step is None:
        raise ValueError(f"step not found: {step_id}")
    run = conn.execute(
        "SELECT * FROM workflow_runs WHERE id = ?",
        (step["workflow_run_id"],),
    ).fetchone()
    if run is None:
        raise ValueError(f"run not found: {step['workflow_run_id']}")
    source = conn.execute("SELECT * FROM sources WHERE id = ?", (run["source_id"],)).fetchone()
    if source is None:
        raise ValueError(f"source not found: {run['source_id']}")
    payload = _load_raw_payload(conn, object_store, source["id"], source["source_kind"])
    provider_cleaned = maybe_clean_with_provider(source["source_uri"] or "", payload)
    cleaned = provider_cleaned or clean_payload(source["source_kind"], payload)
    artifact_id = str(uuid4())
    conn.execute(
        """
        INSERT INTO artifacts(
          id, team_id, workflow_run_id, workflow_step_id, source_id, document_id,
          artifact_type, storage_backend, mime_type, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, 'cleaned_text', 'sqlite_ref', 'text/plain', ?)
        """,
        (
            artifact_id,
            run["team_id"],
            run["id"],
            step["id"],
            source["id"],
            run["document_id"],
            json.dumps({"text": cleaned, "source_kind": source["source_kind"]}),
        ),
    )
    conn.execute(
        """
        INSERT INTO workflow_steps(
          id, team_id, workflow_run_id, parent_step_id, step_key,
          stage, action, payload_json, status
        ) VALUES (?, ?, ?, ?, ?, 'rag:structurize', 'rag.structurize', ?, 'pending')
        """,
        (
            str(uuid4()),
            run["team_id"],
            run["id"],
            step["id"],
            f"rag-struct-{uuid4().hex}",
            json.dumps({"artifact_id": artifact_id}),
        ),
    )
    now = utc_now_iso()
    conn.execute(
        "UPDATE workflow_steps SET status='succeeded', finished_at=? WHERE id = ?",
        (now, step_id),
    )
    conn.execute(
        """
        UPDATE workflow_runs
        SET status='running', current_stage='rag', updated_at=?
        WHERE id = ?
        """,
        (now, run["id"]),
    )
    conn.commit()
