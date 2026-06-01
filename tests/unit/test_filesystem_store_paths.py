"""FF-F4-T01 (F4-01): FileSystemObjectStore path-traversal rejection.

先红后绿 ([Q7]): 当前 HEAD 对 object_key 零校验，put_text('../escaped.txt')
会写到 root 之外（主审实测逃逸成功），故下列攻击向量用例在修复前必红。
修复后 (_resolve_safe) 所有逃逸 key 被 raise 拒绝，合法 key 正常读写。
"""

import tempfile
from pathlib import Path

import pytest

from storage_objects import FileSystemObjectStore

# §7.3 威胁模型攻击向量 + §8.5 防假绿刻死用例。
ESCAPE_KEYS = [
    "../escaped.txt",
    "../../etc/passwd",
    "/abs/path",
    "a/../../x",
    "..\\win\\path",
    "",
    "   ",
]


def _store() -> tuple[FileSystemObjectStore, Path]:
    # root 置于独立 base 下的子目录: 逃逸目标 (base/escaped.txt) 落在 *本测试独占*
    # 的 base 内, 避免共享 tmp 父目录跨用例污染防假绿断言。
    base = Path(tempfile.mkdtemp(prefix="ff-f4-paths-"))
    root = base / "store"
    return FileSystemObjectStore(str(root)), root


@pytest.mark.parametrize("key", ESCAPE_KEYS)
def test_put_text_rejects_escape(key: str) -> None:
    store, root = _store()
    with pytest.raises((ValueError, OSError)):
        store.put_text(key, "payload")
    # 防假绿: 即使某些 key 未 raise，也绝不能在 root 之外落盘。
    escaped = root.parent / "escaped.txt"
    assert not escaped.exists(), f"{key!r} escaped root and wrote {escaped}"


@pytest.mark.parametrize("key", ESCAPE_KEYS)
def test_get_text_rejects_escape(key: str) -> None:
    store, _ = _store()
    with pytest.raises((ValueError, OSError)):
        store.get_text(key)


@pytest.mark.parametrize("key", ESCAPE_KEYS)
def test_exists_rejects_escape(key: str) -> None:
    store, _ = _store()
    with pytest.raises((ValueError, OSError)):
        store.exists(key)


@pytest.mark.parametrize("key", ESCAPE_KEYS)
def test_delete_rejects_escape(key: str) -> None:
    store, _ = _store()
    with pytest.raises((ValueError, OSError)):
        store.delete(key)


def test_legal_key_round_trip() -> None:
    """合法子目录 key happy-path 不回归。"""
    store, root = _store()
    key = "raw/team_x/upload_y/file.txt"
    store.put_text(key, "hello")
    assert store.exists(key) is True
    assert store.get_text(key) == "hello"
    # 实际落在 root 内。
    assert (root / key).is_file()


def test_dot_segment_normalized_inside_root_allowed() -> None:
    """key 含 ./ 经 resolve 归一后仍在 root 内放行 (§5.1-6 边界)。"""
    store, root = _store()
    store.put_text("raw/./team/./file.txt", "ok")
    assert (root / "raw" / "team" / "file.txt").read_text() == "ok"
