"""FF-F4-T06 (F4-06): put_text 原子写 + get_text 受控错误处理.

先红后绿 ([Q7]): 当前 HEAD put_text 直接 write_text (非原子)，get_text 缺失 key
裸抛 FileNotFoundError。修复后 put_text 经 temp+os.replace (无残留 temp)，
get_text 缺失对象抛受控 KeyError (非裸 FileNotFoundError)。
"""

import tempfile
from pathlib import Path

import pytest

from storage_objects import FileSystemObjectStore


def _store() -> tuple[FileSystemObjectStore, Path]:
    root = Path(tempfile.mkdtemp(prefix="ff-f4-io-"))
    return FileSystemObjectStore(str(root)), root


def test_put_text_atomic_no_temp_residue() -> None:
    store, root = _store()
    store.put_text("raw/a/b/file.txt", "content")
    assert (root / "raw/a/b/file.txt").read_text() == "content"
    # 原子写不得留下 .tmp 残留。
    residue = [p.name for p in root.rglob("*") if p.is_file() and ".tmp" in p.name]
    assert residue == [], f"temp residue left: {residue}"


def test_put_text_overwrite_atomic() -> None:
    store, root = _store()
    store.put_text("k.txt", "v1")
    store.put_text("k.txt", "v2")
    assert (root / "k.txt").read_text() == "v2"


def test_get_text_missing_controlled_exception() -> None:
    store, _ = _store()
    # 受控异常 (KeyError)，不是裸 FileNotFoundError。
    with pytest.raises(KeyError):
        store.get_text("raw/missing/object.txt")


def test_get_text_missing_not_raw_filenotfound() -> None:
    store, _ = _store()
    try:
        store.get_text("raw/missing/object.txt")
    except KeyError:
        pass
    except FileNotFoundError:  # pragma: no cover
        pytest.fail("get_text leaked raw FileNotFoundError instead of controlled KeyError")
