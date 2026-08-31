"""NHX1-T28: deterministic barrier races keep one durable owner/effect."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from tests.e2e.test_nhx1_observation_identity import _inline_payload
from tests.local_runtime import local_mock_settings


@pytest.mark.parametrize("seed", (0, 1, 2))
def test_observation_identity_race_soak_fixed_seed(tmp_path: Path, seed: int) -> None:
    token = f"nhx1-race-{seed}"
    team_uuid = uuid7()
    app = create_app(
        local_mock_settings(
            database_path=tmp_path / f"race-{seed}.sqlite3",
            object_root=tmp_path / f"objects-{seed}",
            internal_token=token,
            rate_limit_ip_per_min=10_000,
            rate_limit_token_per_min=20_000,
        )
    )
    headers = {"Authorization": f"Bearer {token}"}
    task_ids = (uuid7(), uuid7())
    with TestClient(app, raise_server_exceptions=True) as client:
        team = client.post(
            "/v1/teams",
            headers=headers,
            json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": f"race-{seed}"},
        )
        assert team.status_code == 201, team.text

        def submit(task_uuid: str):
            return client.post(
                f"/v1/teams/{team_uuid}/tasks",
                headers=headers,
                json=_inline_payload(
                    team_uuid,
                    task_uuid,
                    content=f"same race bytes {seed}",
                    observation_key=f"race-key-{seed}",
                ),
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(submit, task_ids))
        assert sorted(response.status_code for response in responses) == [200, 201]

        async def inspect() -> dict[str, int]:
            async with app.state.container.persistence.read_snapshot() as tx:
                observation = await tx.fetchone(
                    "SELECT COUNT(*) AS count FROM mkb_intake_observations WHERE team_uuid=? AND observation_key=?",
                    (team_uuid, f"race-key-{seed}"),
                )
                tasks = await tx.fetchone("SELECT COUNT(*) AS count FROM mkb_tasks WHERE team_uuid=?", (team_uuid,))
                attempts = await tx.fetchone(
                    "SELECT COUNT(*) AS count FROM mkb_observation_attempts WHERE team_uuid=?", (team_uuid,)
                )
            return {"observations": observation["count"], "tasks": tasks["count"], "attempts": attempts["count"]}

        assert client.portal.call(inspect) == {"observations": 1, "tasks": 1, "attempts": 1}
