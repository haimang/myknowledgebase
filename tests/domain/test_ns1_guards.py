"""NS1-T12/T40: the production intake path cannot use the fixture compiler."""

import re
from pathlib import Path


def test_generation_runtime_has_no_fixture_structurize_call() -> None:
    root = Path("src/runtime/intake")
    source = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("generation_*.py"))
    assert "compiler.structurize(" not in source
    assert "adopt_layered_json" in source


def test_ns1_production_architecture_fences() -> None:
    runtime_source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in Path("src/runtime/intake").rglob("*.py")
        if "__pycache__" not in path.parts
    )
    assert re.search(r"\bstructurize\s*\(\s*clean_text", runtime_source) is None
    assert "compiler.structurize(" not in runtime_source
    assert "_live_summaries" not in runtime_source

    migration_source = "\n".join(
        path.read_text(encoding="utf-8") for path in Path("src/persistence/migrations").glob("*.sql")
    )
    assert re.search(r"\bbody_text\b", migration_source, flags=re.IGNORECASE) is None

    models_source = Path("src/contracts/api/models.py").read_text(encoding="utf-8")
    payload_start = models_source.index("class IntakeIngestPayload")
    payload_end = models_source.index("class IntakeRebuildPayload", payload_start)
    payload_source = models_source[payload_start:payload_end]
    assert "prompt_ref" not in payload_source
    assert "git_relative_path" not in payload_source
