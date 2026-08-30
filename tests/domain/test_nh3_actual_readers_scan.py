"""NH3-T06: new domain/wire readers never interpret the legacy physical alias."""

from __future__ import annotations

import re
from pathlib import Path


def test_architecture_scan_zero_actual_readers_of_legacy_column() -> None:
    """NH9-T08 🔱 alias for the NH3-T06 architecture scan node."""

    test_runtime_has_no_legacy_s05_actual_reader()


def test_runtime_has_no_legacy_s05_actual_reader() -> None:
    root = Path(__file__).resolve().parents[2]
    reader_pattern = re.compile(r"\[\s*['\"]s05_binding_digest['\"]\s*\]|\.get\(\s*['\"]s05_binding_digest")
    offenders: list[str] = []
    for base in (root / "src" / "contracts", root / "src" / "runtime", root / "src" / "services"):
        for path in base.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            if reader_pattern.search(text):
                offenders.append(str(path.relative_to(root)))
    assert offenders == []
