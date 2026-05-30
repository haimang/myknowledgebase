import tempfile
from pathlib import Path
from sqlite3 import Connection

from storage_sqlite.engine import CoreSQLiteEngine
from storage_sqlite.migrations.runner import apply_core_migrations
from vector_sqlite_vec.engine import VecSQLiteEngine
from vector_sqlite_vec.schema import apply_vec_schema


def make_kernel_dbs() -> tuple[Connection, Connection]:
    tmp_dir = Path(tempfile.mkdtemp(prefix="smind-p1-"))
    core_conn = CoreSQLiteEngine(tmp_dir / "core.db").connect()
    vec_conn = VecSQLiteEngine(tmp_dir / "vec.db").connect()
    apply_core_migrations(core_conn)
    apply_vec_schema(vec_conn)
    return core_conn, vec_conn


def seed_minimum_graph(core_conn: Connection) -> dict[str, str]:
    ids = {
        "user_id": "usr_p1",
        "team_id": "team_p1",
        "source_id": "src_p1",
        "document_id": "doc_p1",
        "run_id": "run_p1",
    }
    core_conn.execute(
        "INSERT INTO users (id, email, display_name, password_hash) VALUES (?, ?, ?, ?)",
        (ids["user_id"], "p1@example.com", "P1", "hash"),
    )
    core_conn.execute(
        "INSERT INTO teams (id, slug, name) VALUES (?, ?, ?)",
        (ids["team_id"], "team-p1", "Team P1"),
    )
    core_conn.execute(
        """
        INSERT INTO team_members (team_id, user_id, role, status, joined_at)
        VALUES (?, ?, 'owner', 'active', strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        """,
        (ids["team_id"], ids["user_id"]),
    )
    core_conn.execute(
        """
        INSERT INTO sources (id, team_id, source_kind, source_uri, title)
        VALUES (?, ?, 'file', 'file://seed', 'Seed Source')
        """,
        (ids["source_id"], ids["team_id"]),
    )
    core_conn.execute(
        """
        INSERT INTO documents (id, team_id, source_id, canonical_uri, title)
        VALUES (?, ?, ?, 'doc://seed', 'Seed Doc')
        """,
        (ids["document_id"], ids["team_id"], ids["source_id"]),
    )
    core_conn.commit()
    return ids

