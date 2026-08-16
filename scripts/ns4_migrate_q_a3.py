"""One-shot NS4 migrate: copy Q-A3 serving onto a Turso file and stop using sqlite.

Does not invent structure-reject histograms for old failed rows.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
from pathlib import Path

Q_A3_TASK = "01a00887-3cef-7379-92ea-3a6a38fd4188"
DEFAULT_SOURCE = Path(".experiment/0815/runs/MKB-0815-R2/runtime/mkb.db")
DEFAULT_DEST = Path(".experiment/0815/runs/MKB-0815-R2/runtime/mkb.turso.db")


def migrate(source: Path, dest: Path) -> dict[str, object]:
    if not source.is_file():
        raise FileNotFoundError(f"source sqlite archive missing: {source}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.resolve() == source.resolve():
        raise ValueError("dest must be a new Turso path; refuse in-place sqlite reuse")
    shutil.copy2(source, dest)

    import turso

    connection = turso.connect(str(dest))
    try:
        vectors = connection.execute("SELECT COUNT(*) FROM mkb_vector_records").fetchone()[0]
        facets = connection.execute("SELECT COUNT(*) FROM mkb_vector_record_facets").fetchone()[0]
        task = connection.execute(
            "SELECT status FROM mkb_tasks WHERE task_uuid=?",
            (Q_A3_TASK,),
        ).fetchone()
        reports = 0
        try:
            reports = connection.execute("SELECT COUNT(*) FROM mkb_generation_stage_reports").fetchone()[0]
        except Exception:
            reports = 0
    finally:
        connection.close()

    if int(vectors) != 17 or int(facets) != 17:
        dest.unlink(missing_ok=True)
        raise RuntimeError(f"Q-A3 vector closure mismatch: records={vectors} facets={facets}")
    if task is None or task[0] != "succeeded":
        dest.unlink(missing_ok=True)
        raise RuntimeError("Q-A3 task is not succeeded on the Turso copy")
    if reports:
        dest.unlink(missing_ok=True)
        raise RuntimeError("migration invented stage reports; refused")

    # Archive source stays on disk but 0815 production paths must not open it.
    return {
        "source": str(source),
        "dest": str(dest),
        "q_a3_task": Q_A3_TASK,
        "vector_records": int(vectors),
        "vector_facets": int(facets),
        "stage_reports": int(reports),
        "source_left_as_archive": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    args = parser.parse_args()
    report = migrate(args.source, args.dest)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
