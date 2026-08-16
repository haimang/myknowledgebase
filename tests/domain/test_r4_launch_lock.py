"""R4 launch lock: four cells, suffix=-r4, no extras, Turso, no live -r4 yet."""

from __future__ import annotations

from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
R2 = REPOSITORY_ROOT / ".experiment/0815/runs/MKB-0815-R2"
R4 = REPOSITORY_ROOT / ".experiment/0815/runs/MKB-0815-R4"


def test_run_md_locks_r4_command() -> None:
    text = (R4 / "RUN.md").read_text(encoding="utf-8")
    assert "--cells N-A3,N-A6,N-A2,Q-A5" in text
    assert "--suffix=-r4" in text
    assert "--no-extras" in text
    launch = text.split("冻结发车命令")[-1].split("## 6.")[0]
    assert "--cells N-A3,N-A6,N-A2,Q-A5" in launch
    assert "N-A1" not in launch
    assert "A5g2" not in launch
    assert "mkb.turso.db" in text


def test_r2_jsonl_has_no_r4_suffix_yet() -> None:
    path = R2 / "results/runs.jsonl"
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        assert "-r4" not in line
