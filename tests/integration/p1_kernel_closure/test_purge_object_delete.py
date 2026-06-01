"""FF-F4-T05 (F4-05): purge 接线删对象 (合规清退) 端到端.

先红后绿 ([Q7]): 当前 HEAD process_purge_requests 从不接触 object_store
(part-cr-3 R5)，被 purge 文档的 raw 上传正文永久残留磁盘。修复后 purge 查
uploads/static_files/artifacts 的 object_key 逐个 object_store.delete，对象不残留。
"""

import tempfile
from pathlib import Path

from ingestion.service import IngestionService
from storage_objects import FileSystemObjectStore
from vector_sqlite_vec import VectorStore
from workflow_core.purge import create_purge_request, process_purge_requests

from tests.fixtures.sqlite_kernel import make_kernel_dbs


def _seed_team(conn) -> None:
    conn.execute("INSERT INTO teams (id, slug, name) VALUES ('team_x', 'tx', 'TX')")
    conn.execute(
        "INSERT INTO users (id, email, display_name, password_hash) "
        "VALUES ('usr_x', 'x@e.com', 'X', 'h')"
    )
    conn.commit()


def test_purge_deletes_raw_object() -> None:
    core_conn, vec_conn = make_kernel_dbs()
    _seed_team(core_conn)
    store = FileSystemObjectStore(str(Path(tempfile.mkdtemp(prefix="ff-f4-purge-")) / "obj"))
    svc = IngestionService(core_conn, store)

    init = svc.file_initiate("team_x", "usr_x", "doc.txt", "text/plain")
    confirmed = svc.file_confirm(
        team_id="team_x", upload_id=init["upload_id"], title="T", content="body text"
    )
    object_key = init["object_key"]
    assert store.exists(object_key) is True, "precondition: raw object written"

    create_purge_request(
        core_conn,
        request_id="purge_1",
        team_id="team_x",
        target_kind="document",
        target_id=confirmed["document_id"],
    )
    processed = process_purge_requests(core_conn, vec_conn, store)
    assert processed == 1

    assert store.exists(object_key) is False, "raw object残留 — 合规清退失败"


def test_purge_deletes_chunk_text_artifact_object() -> None:
    """artifacts (chunk_text, storage_backend='object_store') 的正文也被清退 (§0 目标)。"""
    core_conn, vec_conn = make_kernel_dbs()
    _seed_team(core_conn)
    store = FileSystemObjectStore(str(Path(tempfile.mkdtemp(prefix="ff-f4-art-")) / "obj"))
    svc = IngestionService(core_conn, store)
    init = svc.file_initiate("team_x", "usr_x", "doc.txt", "text/plain")
    confirmed = svc.file_confirm(
        team_id="team_x", upload_id=init["upload_id"], title="T", content="body"
    )
    # 模拟 rag chunk_text 产物落 object_store。
    art_key = f"chunks/team_x/{confirmed['document_id']}/0.txt"
    store.put_text(art_key, "chunk body text")
    core_conn.execute(
        """
        INSERT INTO artifacts (
            id, team_id, source_id, document_id, artifact_type,
            storage_backend, object_key, content_hash
        ) VALUES ('art_1', 'team_x', ?, ?, 'chunk_text', 'object_store', ?, 'h')
        """,
        (confirmed["source_id"], confirmed["document_id"], art_key),
    )
    core_conn.commit()
    assert store.exists(art_key) is True

    create_purge_request(
        core_conn,
        request_id="purge_1",
        team_id="team_x",
        target_kind="document",
        target_id=confirmed["document_id"],
    )
    assert process_purge_requests(core_conn, vec_conn, store) == 1
    assert store.exists(art_key) is False, "chunk_text artifact 正文残留"
    assert store.exists(init["object_key"]) is False


def test_purge_without_object_store_still_works() -> None:
    """向后兼容: 不传 object_store (None) 时 purge 仍处理 SQLite + vec 不报错。"""
    core_conn, vec_conn = make_kernel_dbs()
    _seed_team(core_conn)
    store = FileSystemObjectStore(str(Path(tempfile.mkdtemp(prefix="ff-f4-purge2-")) / "obj"))
    svc = IngestionService(core_conn, store)
    init = svc.file_initiate("team_x", "usr_x", "doc.txt", "text/plain")
    confirmed = svc.file_confirm(
        team_id="team_x", upload_id=init["upload_id"], title="T", content="body"
    )
    create_purge_request(
        core_conn,
        request_id="purge_1",
        team_id="team_x",
        target_kind="document",
        target_id=confirmed["document_id"],
    )
    # object_store 省略 → 默认 None，不删对象但流程完整。
    assert process_purge_requests(core_conn, vec_conn) == 1
    doc = core_conn.execute(
        "SELECT status FROM documents WHERE id = ?", (confirmed["document_id"],)
    ).fetchone()
    assert doc["status"] == "purged"
