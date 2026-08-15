"""NS3-P4: compiler package keeps the public import surface."""

from __future__ import annotations

import ast
from pathlib import Path

from src.services import lsrag_compiler
from src.services.lsrag_compiler import (
    LsragContractCompiler,
    StructureDocument,
    structure_payload,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_public_import_surface_is_stable() -> None:
    assert LsragContractCompiler is lsrag_compiler.LsragContractCompiler
    assert StructureDocument is lsrag_compiler.StructureDocument
    assert callable(structure_payload)
    for name in lsrag_compiler.__all__:
        assert hasattr(lsrag_compiler, name)


def test_old_module_file_is_gone() -> None:
    assert not (REPOSITORY_ROOT / "src/services/lsrag_compiler.py").exists()
    assert (REPOSITORY_ROOT / "src/services/lsrag_compiler/__init__.py").is_file()


def test_leaf_services_import_only_public_compiler_names() -> None:
    allowed = set(lsrag_compiler.__all__)
    hits: list[str] = []
    for package in ("lsrag_structurize", "lsrag_construct"):
        root = REPOSITORY_ROOT / "src/services" / package
        for path in root.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom):
                    continue
                module = node.module or ""
                if module == "src.services.lsrag_compiler":
                    for alias in node.names:
                        if alias.name != "*" and alias.name not in allowed:
                            hits.append(f"{path.name}:{node.lineno}:{alias.name}")
                if module.startswith("src.services.lsrag_compiler."):
                    hits.append(f"{path.name}:{node.lineno}:private {module}")
    assert hits == []
