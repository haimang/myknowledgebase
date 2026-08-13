"""HTTP boundary tests for S10's non-echoing validation taxonomy."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.runtime.config import Settings


class _UnexpectedRetrievalCall:
    async def search(self, _: object) -> dict[str, object]:
        raise AssertionError("invalid retrieval payload reached the retrieval service")


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    app = create_app(
        Settings(
            internal_token="retrieval-validation-token",
            database_path=tmp_path / "mkb.sqlite3",
            persistence_backend="sqlite",
            concurrent_writes_required=False,
            native_vector_required=False,
            object_root=tmp_path / "objects",
            inference_probe_enabled=False,
            rate_limit_ip_per_min=1_000,
            rate_limit_token_per_min=1_000,
        )
    )
    app.state.container.retrieval = _UnexpectedRetrievalCall()
    with TestClient(app, raise_server_exceptions=True) as test_client:
        yield test_client


def _request_payload(team_uuid: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema_version": "mkb.retrieval.v1",
        "team_uuid": team_uuid,
        "query": "a safe query",
        **extra,
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("index_generation", 3),
        ("include_answer", True),
        ("raw_query_vector", ["must-not-echo"]),
        ("model_override", {"api_key": "must-not-echo"}),
    ],
)
def test_forbidden_retrieval_controls_use_stable_non_echoing_taxonomy(
    client: TestClient, field: str, value: object
) -> None:
    team_uuid = uuid7()
    response = client.post(
        f"/v1/teams/{team_uuid}/retrieval:search",
        headers={"Authorization": "Bearer retrieval-validation-token"},
        json=_request_payload(team_uuid, **{field: value}),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "RETRIEVE_SCHEMA_FORBIDDEN_FIELD"
    assert "must-not-echo" not in response.text
    assert "details" not in response.json()["error"]


def test_unknown_retrieval_field_uses_stable_non_echoing_taxonomy(client: TestClient) -> None:
    team_uuid = uuid7()
    response = client.post(
        f"/v1/teams/{team_uuid}/retrieval:search",
        headers={"Authorization": "Bearer retrieval-validation-token"},
        json=_request_payload(team_uuid, unregistered_control="must-not-echo"),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "RETRIEVE_SCHEMA_UNKNOWN_FIELD"
    assert "must-not-echo" not in response.text
    assert "details" not in response.json()["error"]


def test_malformed_retrieval_json_uses_retrieval_schema_taxonomy(client: TestClient) -> None:
    team_uuid = uuid7()
    response = client.post(
        f"/v1/teams/{team_uuid}/retrieval:search",
        headers={
            "Authorization": "Bearer retrieval-validation-token",
            "Content-Type": "application/json",
        },
        content=b'{"query":"must-not-echo",',
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "RETRIEVE_SCHEMA_INVALID"
    assert "must-not-echo" not in response.text
    # JSON should not be delegated to FastAPI's generic validation handler.
    assert json.loads(response.text)["error"]["code"] != "request-invalid"


def test_invalid_retrieval_option_uses_specific_non_echoing_taxonomy(client: TestClient) -> None:
    team_uuid = uuid7()
    response = client.post(
        f"/v1/teams/{team_uuid}/retrieval:search",
        headers={"Authorization": "Bearer retrieval-validation-token"},
        json=_request_payload(team_uuid, include_pack="must-not-echo"),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "RETRIEVE_SCHEMA_PACK_INVALID"
    assert "must-not-echo" not in response.text
