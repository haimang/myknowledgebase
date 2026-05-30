from __future__ import annotations

from pathlib import Path


class FileSystemObjectStore:
    def __init__(self, root_dir: str) -> None:
        self.root = Path(root_dir)
        self.root.mkdir(parents=True, exist_ok=True)

    def put_text(self, object_key: str, content: str) -> None:
        path = self.root / object_key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def get_text(self, object_key: str) -> str:
        return (self.root / object_key).read_text(encoding="utf-8")

    def exists(self, object_key: str) -> bool:
        return (self.root / object_key).exists()
