"""FF-F4-T02 (F4-02): ingestion filename basename 源头收口 (纵深防御).

先红后绿 ([Q7]): 当前 HEAD file_initiate 把 filename 原样拼进 object_key
(service.py:17)，HTTP body {"filename":"../../../etc/passwd"} 会污染 object_key。
修复后 filename 经 basename + 拒绝分隔符/空值，object_key 始终为
raw/team/upload/<basename>。
"""

import tempfile
from pathlib import Path

import pytest

from ingestion.service import IngestionService
from storage_objects import FileSystemObjectStore
from storage_sqlite.engine import CoreSQLiteEngine
from storage_sqlite.migrations.runner import apply_core_migrations


def _service() -> IngestionService:
    tmp = Path(tempfile.mkdtemp(prefix="ff-f4-ingest-"))
    conn = CoreSQLiteEngine(tmp / "core.db").connect()
    apply_core_migrations(conn)
    conn.execute("INSERT INTO teams (id, slug, name) VALUES ('team_x', 'tx', 'TX')")
    conn.execute(
        "INSERT INTO users (id, email, display_name, password_hash) "
        "VALUES ('usr_x', 'x@e.com', 'X', 'h')"
    )
    conn.commit()
    store = FileSystemObjectStore(str(tmp / "objects"))
    return IngestionService(conn, store)


def test_file_initiate_strips_traversal_to_basename() -> None:
    svc = _service()
    out = svc.file_initiate("team_x", "usr_x", "../../../etc/passwd", "text/plain")
    key = out["object_key"]
    assert ".." not in key.split("/")
    assert key == f"raw/team_x/{out['upload_id']}/passwd", key


@pytest.mark.parametrize(
    "bad",
    ["..", "", "   ", "a\\b", "/", "."],
)
def test_file_initiate_rejects_unsafe_filename(bad: str) -> None:
    svc = _service()
    with pytest.raises(ValueError):
        svc.file_initiate("team_x", "usr_x", bad, "text/plain")


def test_file_initiate_strips_subpath_to_basename() -> None:
    """basename-strip 契约: 含分隔符但 basename 干净的值取 basename (非拒绝)。"""
    svc = _service()
    out = svc.file_initiate("team_x", "usr_x", "foo/bar.txt", "text/plain")
    assert out["object_key"] == f"raw/team_x/{out['upload_id']}/bar.txt"


def test_static_initiate_reuses_basename_guard() -> None:
    svc = _service()
    out = svc.static_initiate("team_x", "usr_x", "../../secret.txt", "text/plain")
    assert out["object_key"] == f"raw/team_x/{out['upload_id']}/secret.txt"


def test_legal_filename_unchanged() -> None:
    svc = _service()
    out = svc.file_initiate("team_x", "usr_x", "report.pdf", "application/pdf")
    assert out["object_key"] == f"raw/team_x/{out['upload_id']}/report.pdf"
