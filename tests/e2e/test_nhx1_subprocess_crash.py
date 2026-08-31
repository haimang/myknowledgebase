"""NHX1-T29: real child process kill/restart leaves an observable recovery path."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
from pathlib import Path


def test_real_subprocess_kill_and_cold_restart(tmp_path: Path) -> None:
    marker = tmp_path / "child-started.marker"
    child_source = (
        "from pathlib import Path; import signal; "
        f"Path({str(marker)!r}).write_text('started', encoding='utf-8'); "
        "print('READY', flush=True); signal.pause()"
    )
    process = subprocess.Popen(
        (sys.executable, "-c", child_source),
        cwd=Path(__file__).resolve().parents[2],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
        text=True,
    )
    try:
        assert process.stdout is not None
        assert process.stdout.readline().strip() == "READY"
        assert marker.read_text(encoding="utf-8") == "started"
        os.killpg(process.pid, signal.SIGKILL)
        return_code = process.wait(timeout=10)
        assert return_code == -signal.SIGKILL
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=10)
        if process.stdout is not None:
            process.stdout.close()
        if process.stderr is not None:
            process.stderr.close()

    recovery = subprocess.run(
        (
            sys.executable,
            "-c",
            f"from pathlib import Path; p=Path({str(marker)!r}); print('RECOVERED' if p.is_file() else 'ORPHANED')",
        ),
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        check=False,
    )
    assert recovery.returncode == 0
    assert recovery.stdout.strip() == "RECOVERED"
