import subprocess
from pathlib import Path


def test_p7_legacy_freeze_guard() -> None:
    root = Path(__file__).resolve().parents[3]
    script = root / "tools" / "scripts" / "check_legacy_freeze.sh"
    result = subprocess.run(["bash", str(script)], check=False, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr

