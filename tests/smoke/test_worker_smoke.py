import subprocess
import sys


def test_worker_once() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "smind_worker.main", "--once"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0

