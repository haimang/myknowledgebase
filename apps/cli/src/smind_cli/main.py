import argparse
import contextlib
from collections.abc import Iterator

from management import ManagementService
from smind_config.loader import load_settings
from storage_objects import FileSystemObjectStore
from storage_sqlite.engine import CoreSQLiteEngine
from storage_sqlite.migrations.runner import apply_core_migrations
from vector_sqlite_vec import VecSQLiteEngine, apply_vec_schema


@contextlib.contextmanager
def _service() -> Iterator[ManagementService]:
    """Yield a ManagementService, closing both connections on exit.

    F2-02 (G-CR2-01 app-level / part-cr-8.md R6): the core+vec connections are
    owned by this context manager so they are closed when the CLI command
    finishes -> no per-invocation connection leak.
    """
    settings = load_settings()
    with contextlib.closing(
        CoreSQLiteEngine(settings.core_db_path).connect()
    ) as core_conn, contextlib.closing(
        VecSQLiteEngine(settings.vec_db_path).connect()
    ) as vec_conn:
        apply_core_migrations(core_conn)
        apply_vec_schema(vec_conn)
        yield ManagementService(
            core_conn,
            vec_conn=vec_conn,
            object_store=FileSystemObjectStore(settings.object_store_dir),
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="smind-family cli")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("health", help="print current bootstrap health")
    search = sub.add_parser("search", help="semantic search")
    search.add_argument("--team-id", required=True)
    search.add_argument("--query", required=True)
    search.add_argument("--limit", type=int, default=6)
    ops = sub.add_parser("ops-health", help="show ops health")
    ops.add_argument("--team-id", required=True)
    args = parser.parse_args()

    if args.command == "health":
        settings = load_settings()
        print(f"ok env={settings.app_env}")
        return 0
    if args.command == "search":
        with _service() as svc:
            items = svc.search(team_id=args.team_id, query=args.query, limit=args.limit)
        print({"count": len(items), "items": items})
        return 0
    if args.command == "ops-health":
        with _service() as svc:
            result = svc.health(team_id=args.team_id)
        print(result)
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
