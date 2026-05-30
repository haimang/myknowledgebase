import argparse

from management import ManagementService
from smind_config.loader import load_settings
from storage_objects import FileSystemObjectStore
from storage_sqlite.engine import CoreSQLiteEngine
from storage_sqlite.migrations.runner import apply_core_migrations
from vector_sqlite_vec import VecSQLiteEngine, apply_vec_schema


def _service() -> ManagementService:
    settings = load_settings()
    core_conn = CoreSQLiteEngine(settings.core_db_path).connect()
    vec_conn = VecSQLiteEngine(settings.vec_db_path).connect()
    apply_core_migrations(core_conn)
    apply_vec_schema(vec_conn)
    return ManagementService(
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
        items = _service().search(team_id=args.team_id, query=args.query, limit=args.limit)
        print({"count": len(items), "items": items})
        return 0
    if args.command == "ops-health":
        print(_service().health(team_id=args.team_id))
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
