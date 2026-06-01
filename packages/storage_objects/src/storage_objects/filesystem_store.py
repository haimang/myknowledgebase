from __future__ import annotations

import os
import tempfile
from pathlib import Path

# 文本-only 适配层 (R8 二进制能力 out-of-scope, 归 F6 PDF 解禁时重评)。
# ObjectStore 是安全 / 能力边界 (final §4 红线第 4 条): object_key 规范化在
# 适配层内强制, 不依赖调用方自律 (part-cr-3 R1 / part-cr-5 R2)。


class FileSystemObjectStore:
    def __init__(self, root_dir: str) -> None:
        self.root = Path(root_dir)
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve_safe(self, object_key: str) -> Path:
        """把 object_key 规范化为 root 内的安全绝对路径, 否则 raise。

        F4-01 最终防线 (§7.3 威胁模型落点): 快速拒绝空 / 绝对路径 / 含 ``..`` 段 /
        反斜杠 (防 Windows 风格 ``..\\`` 绕过), 再 resolve 后断言 is_relative_to(root)
        以兜底符号链接与归一化逃逸。
        """
        if not isinstance(object_key, str) or not object_key.strip():
            raise ValueError(f"unsafe object_key: empty or blank: {object_key!r}")
        if "\\" in object_key:
            raise ValueError(f"unsafe object_key: backslash not allowed: {object_key!r}")
        if object_key.startswith("/") or Path(object_key).is_absolute():
            raise ValueError(f"unsafe object_key: absolute path: {object_key!r}")
        if any(seg == ".." for seg in object_key.split("/")):
            raise ValueError(f"unsafe object_key: parent-dir segment: {object_key!r}")
        root_resolved = self.root.resolve()
        resolved = (root_resolved / object_key).resolve()
        if not resolved.is_relative_to(root_resolved):
            raise ValueError(f"unsafe object_key: escapes root: {object_key!r}")
        return resolved

    def put_text(self, object_key: str, content: str) -> None:
        path = self._resolve_safe(object_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        # F4-06 原子写: 同目录 temp 落盘后 os.replace 原子 rename, 崩溃不留半文件。
        fd, tmp_name = tempfile.mkstemp(
            dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(content)
            os.replace(tmp_name, path)
        except BaseException:
            # 失败清理 temp, 不留残留 (再向上抛)。
            try:
                os.unlink(tmp_name)
            except FileNotFoundError:
                pass
            raise

    def get_text(self, object_key: str) -> str:
        path = self._resolve_safe(object_key)
        try:
            return path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            # F4-06 受控异常: 缺失对象不抛裸 FileNotFoundError, 供调用方分类。
            raise KeyError(f"object not found: {object_key!r}") from exc

    def exists(self, object_key: str) -> bool:
        return self._resolve_safe(object_key).exists()

    def delete(self, object_key: str) -> None:
        # F4-05 删除路径同为信任边界, 经 _resolve_safe 校验后 unlink; 缺失幂等。
        path = self._resolve_safe(object_key)
        path.unlink(missing_ok=True)
