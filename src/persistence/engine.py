"""Engine capability probes for stock SQLite and the Turso Database engine.

Probes follow docs/manual.md: Concurrent Writes is BEGIN CONCURRENT after
MVCC journal mode; Native Vector is vector32 / vector_distance_*. Index-name
presence and libsql_vector_idx are never evidence.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any


def probe_concurrent_writes(connection: Any, *, restore_journal_mode: bool = True) -> bool:
    """Return True only when MVCC + BEGIN CONCURRENT actually works.

    manual.md: CONCURRENT transactions exist only in MVCC journal mode.
    If enabling MVCC fails (for example because indexes are present), report
    false. Do not leave a failed probe's transaction open.

    Callers that pass a throwaway bypass connection should set
    ``restore_journal_mode=False`` so a business handle is never mutated.
    """

    previous_mode = _journal_mode(connection)
    try:
        switched = _set_journal_mode(connection, "mvcc")
        if not switched:
            return False
        connection.execute("BEGIN CONCURRENT")
        connection.execute("ROLLBACK")
        return True
    except Exception:
        try:
            connection.execute("ROLLBACK")
        except Exception:
            pass
        return False
    finally:
        if restore_journal_mode and previous_mode and previous_mode != "mvcc":
            try:
                _set_journal_mode(connection, previous_mode)
            except Exception:
                pass


def probe_concurrent_writes_scratch(connect: Callable[[str], Any], scratch_path: Path) -> bool:
    """Measure BEGIN CONCURRENT on a throwaway file, never the live database.

    ``PRAGMA journal_mode`` is database-wide. Probing the production file —
    even through a bypass connection — can flip a live ``wal`` database to
    ``mvcc``. Scratch isolation keeps the constitution probe honest without
    mutating the leaf worker's primary file.
    """

    scratch_path.parent.mkdir(parents=True, exist_ok=True)
    connection = connect(str(scratch_path))
    try:
        return probe_concurrent_writes(connection, restore_journal_mode=False)
    finally:
        closer = getattr(connection, "close", None)
        if closer is not None:
            try:
                closer()
            except Exception:
                pass
        for leftover in scratch_path.parent.glob(scratch_path.name + "*"):
            try:
                leftover.unlink()
            except OSError:
                pass


def probe_native_vector(connection: Any) -> bool:
    """Return True only when manual.md vector SQL is executable."""

    try:
        connection.execute("SELECT vector32('[1.0, 0.0]')")
        connection.execute(
            "SELECT vector_distance_cos(vector32('[1.0, 0.0]'), vector32('[0.0, 1.0]'))"
        )
        return True
    except Exception:
        return False


def _journal_mode(connection: Any) -> str | None:
    try:
        cursor = connection.execute("PRAGMA journal_mode")
        row = cursor.fetchone()
        if row is None:
            return None
        value = row[0] if not isinstance(row, dict) else next(iter(row.values()))
        return str(value).lower()
    except Exception:
        return None


def _set_journal_mode(connection: Any, mode: str) -> bool:
    try:
        cursor = connection.execute(f"PRAGMA journal_mode = {mode}")
        row = cursor.fetchone()
        if row is None:
            return False
        value = row[0] if not isinstance(row, dict) else next(iter(row.values()))
        return str(value).lower() == mode.lower()
    except Exception:
        return False


def apply_capability_gates(
    *,
    concurrent_writes: bool,
    native_vector: bool,
    concurrent_writes_required: bool,
    native_vector_required: bool,
) -> dict[str, bool]:
    """Gate readiness on required capabilities without remapping probes.

    An explicit local waiver (required=false) reports the component ready
    because the deployment opted out of the constitution gate. The probe
    results stay available to callers that inspect them separately.
    """

    return {
        "concurrent_writes": concurrent_writes if concurrent_writes_required else True,
        "native_vector": native_vector if native_vector_required else True,
        "concurrent_writes_probe": concurrent_writes,
        "native_vector_probe": native_vector,
    }
