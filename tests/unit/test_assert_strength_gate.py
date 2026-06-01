"""FF-F7-T06: 断言强度门禁 self-test (防门禁本身假绿) + 全套件过关。"""

import importlib.util
from pathlib import Path

_GATE = Path(__file__).resolve().parents[2] / "tools" / "scripts" / "check_assert_strength.py"
_spec = importlib.util.spec_from_file_location("check_assert_strength", _GATE)
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)


def _scan_src(src: str, tmp_path) -> list[str]:
    f = tmp_path / "test_sample.py"
    f.write_text(src, encoding="utf-8")
    return gate.scan_file(f)


def test_flags_weak_only(tmp_path) -> None:
    src = (
        "def test_weak():\n"
        "    resp = call()\n"
        "    assert resp.status_code == 200\n"
        "    assert resp.text != ''\n"
    )
    assert _scan_src(src, tmp_path), "weak-only test should be flagged"


def test_passes_with_strong_assertion(tmp_path) -> None:
    src = (
        "def test_strong():\n"
        "    resp = call()\n"
        "    assert resp.status_code == 200\n"  # 弱前置 (允许)
        "    assert resp.json()['name'] == 'expected'\n"  # 强断言
    )
    assert _scan_src(src, tmp_path) == [], "weak prefix + strong assertion should pass"


def test_is_none_rejection_is_strong(tmp_path) -> None:
    # 安全拒绝断言 (is None) 不应被判弱。
    src = "def test_rejects():\n    assert validate('forged') is None\n"
    assert _scan_src(src, tmp_path) == []


def test_empty_boundary_is_strong(tmp_path) -> None:
    src = "def test_empty():\n    assert clean('') == ''\n"
    assert _scan_src(src, tmp_path) == []


def test_full_suite_passes_gate() -> None:
    tests_dir = Path(__file__).resolve().parents[1]
    files = [
        f for f in tests_dir.rglob("test_*.py")
        if "/smoke/" not in str(f).replace("\\", "/")
    ]
    violations = []
    for f in files:
        violations.extend(gate.scan_file(f))
    assert violations == [], f"weak-only tests present: {violations}"
