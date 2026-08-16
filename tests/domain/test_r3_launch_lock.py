"""R3 launch lock: T-O-375 cells, suffix, no extras, Turso, no live -r3 yet."""

from __future__ import annotations

from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
R2 = REPOSITORY_ROOT / ".experiment/0815/runs/MKB-0815-R2"
R3 = REPOSITORY_ROOT / ".experiment/0815/runs/MKB-0815-R3"


def test_run_md_locks_t_o_375_command() -> None:
    text = (R3 / "RUN.md").read_text(encoding="utf-8")
    assert "--cells N-A5,N-A3,N-A6,N-A2,Q-A5" in text
    assert "--suffix -r3" in text
    assert "--no-extras" in text
    assert "--rerun" in text
    assert "mkb.turso.db" in text
    assert "A5g2" in text
    launch = text.split("冻结发车命令")[-1].split("## 7.")[0]
    assert "N-A1" not in launch
    assert "N-A4" not in launch
    assert "Q-A3" not in launch


def test_r2_collect_and_runner_stay_on_turso() -> None:
    collect = (R2 / "collect.py").read_text(encoding="utf-8")
    runner = (R2 / "runner.py").read_text(encoding="utf-8")
    assert '"persistence_backend": "turso"' in collect
    assert 'persistence_backend="turso"' in runner
    assert '"concurrent_writes_required": True' in collect
    assert "concurrent_writes_required=True" in runner
    assert "mkb.turso.db" in runner
    assert 'persistence_backend="sqlite"' not in collect
    assert 'persistence_backend="sqlite"' not in runner


def test_r2_jsonl_has_no_r3_suffix_yet() -> None:
    path = R2 / "results/runs.jsonl"
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        assert "-r3" not in line
        assert "suffix=-r3" not in line
