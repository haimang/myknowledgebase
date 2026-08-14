"""NS1-T12: the production intake path cannot call the fixture compiler."""

from pathlib import Path


def test_generation_runtime_has_no_fixture_structurize_call() -> None:
    root = Path("src/runtime/intake")
    source = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("generation_*.py"))
    assert "compiler.structurize(" not in source
    assert "adopt_layered_json" in source
