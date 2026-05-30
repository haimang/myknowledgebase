from storage_sqlite.repositories.requests import PurgeRequestRepository, RestartRequestRepository
from storage_sqlite.repositories.workflow import WorkflowRepository
from vector_sqlite_vec.store import VectorStore

from tests.fixtures.sqlite_kernel import make_kernel_dbs, seed_minimum_graph


def test_restart_and_purge_requests_persist() -> None:
    core_conn, _ = make_kernel_dbs()
    ids = seed_minimum_graph(core_conn)
    WorkflowRepository(core_conn).create_run(
        run_id=ids["run_id"],
        team_id=ids["team_id"],
        source_id=ids["source_id"],
        document_id=ids["document_id"],
    )
    restart_repo = RestartRequestRepository(core_conn)
    purge_repo = PurgeRequestRepository(core_conn)
    restart_repo.create(
        request_id="rr_1",
        team_id=ids["team_id"],
        workflow_run_id=ids["run_id"],
    )
    purge_repo.create(
        request_id="pr_1",
        team_id=ids["team_id"],
        target_kind="document",
        target_id=ids["document_id"],
    )
    assert len(restart_repo.backlog()) == 1
    assert len(purge_repo.backlog()) == 1


def test_vec_store_upsert_and_delete() -> None:
    _, vec_conn = make_kernel_dbs()
    vec_conn.execute(
        """
        INSERT INTO vector_namespaces (
            id, team_id, namespace_key, embedding_model,
            embedding_dimension, distance_metric, status
        ) VALUES ('ns_1', 'team_p1', 'default', 'mock-embedding', 1536, 'cosine', 'active')
        """
    )
    vec_conn.commit()
    store = VectorStore(vec_conn)
    store.upsert_chunk(
        chunk_id="chunk_1",
        team_id="team_p1",
        workflow_run_id="run_p1",
        document_id="doc_p1",
        namespace_id="ns_1",
        embedding_rowid=1,
        embedding_model="mock-embedding",
        content_hash="h1",
        embedding=[0.0] * 8,
    )
    row = vec_conn.execute("SELECT * FROM vector_records WHERE chunk_id='chunk_1'").fetchone()
    assert row is not None
    assert row["deleted_at"] is None
    store.delete_chunk("chunk_1")
    row = vec_conn.execute("SELECT * FROM vector_records WHERE chunk_id='chunk_1'").fetchone()
    assert row is not None
    assert row["deleted_at"] is not None
