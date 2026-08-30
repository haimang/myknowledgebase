"""NH7-T08: three registered-API operations reach namespaced facet retrieval."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from tests.e2e.nh7_publication import assert_first_publication_closure
from tests.e2e.test_registered_api_scatter import _create_team, _settings, _submit, _wait_for_terminal

_HEADERS = {"Authorization": "Bearer scatter-token"}

_CASES = {
    "chinatax": (
        "get_articles",
        [
            {
                "id": "tax-one",
                "label": "公告",
                "column": "政策法规",
                "title": "Tax title",
                "content": "Tax fixture reaches registered API scatter.",
                "xxgk_aging": "全文有效",
            }
        ],
        "Tax fixture reaches registered API scatter.",
        "tax_china",
    ),
    "domain": (
        "get_agency_listings",
        [
            {
                "id": 1001,
                "advertiserIdentifiers": {"advertiserId": 12106, "contactIds": []},
                "headline": "Domain title",
                "description": "Domain fixture reaches registered API scatter.",
                "propertyTypes": ["House"],
                "status": "live",
                "saleMode": "buy",
                "channel": "residential",
            }
        ],
        "Domain fixture reaches registered API scatter.",
        "realestate_on_market",
    ),
    "realestate": (
        "get_listings",
        [
            {
                "listingId": "rea-one",
                "channel": "sold",
                "status": {"label": "Sold", "type": "sold_listing"},
                "title": "REA title",
                "description": "REA fixture reaches registered API scatter.",
                "agency": {"name": "Buxton", "agencyId": "37576"},
            }
        ],
        "REA fixture reaches",
        "realestate",
    ),
}


def _run_member(tmp_path: Path, provider: str) -> None:
    operation, records, sentinel, realm = _CASES[provider]
    team_uuid = uuid7()
    app = create_app(_settings(tmp_path))
    with TestClient(app, raise_server_exceptions=True) as client:
        _create_team(client, team_uuid=team_uuid, headers=_HEADERS)
        task_uuid = _submit(
            client,
            team_uuid=team_uuid,
            headers=_HEADERS,
            provider=provider,
            operation=operation,
            records=records,
        )
        terminal = _wait_for_terminal(client, team_uuid=team_uuid, task_uuid=task_uuid, headers=_HEADERS)
        assert terminal["status"] == "succeeded", (provider, terminal)
        assert terminal.get("result_disposition") != "exhausted_zero"

        async def inspect() -> str:
            async with app.state.container.persistence.transaction() as tx:
                namespace = await tx.fetchone(
                    "SELECT namespace_key FROM mkb_vector_namespaces WHERE team_uuid=? AND status='active'",
                    (team_uuid,),
                )
            assert namespace is not None
            return str(namespace["namespace_key"])

        namespace = client.portal.call(inspect)
        omitted = client.post(
            f"/v1/teams/{team_uuid}/retrieval:search",
            headers=_HEADERS,
            json={
                "schema_version": "mkb.retrieval.v2",
                "team_uuid": team_uuid,
                "query": sentinel,
                "filters": {"vector_channel": "original"},
                "return_k": 10,
                "recall_k": 20,
            },
        )
        assert omitted.status_code == 422
        assert omitted.json()["error"]["code"] == "RETRIEVE_SCHEMA_NAMESPACE_REQUIRED"
        found = client.post(
            f"/v1/teams/{team_uuid}/retrieval:search",
            headers=_HEADERS,
            json={
                "schema_version": "mkb.retrieval.v2",
                "team_uuid": team_uuid,
                "namespace_key": namespace,
                "query": sentinel,
                "filters": {"realm": realm, "vector_channel": "original"},
                "return_k": 20,
                "recall_k": 100,
            },
        )
        assert found.status_code == 200, found.text
        assert found.json()["results"], (provider, found.text)
        excluded = client.post(
            f"/v1/teams/{team_uuid}/retrieval:search",
            headers=_HEADERS,
            json={
                "schema_version": "mkb.retrieval.v2",
                "team_uuid": team_uuid,
                "namespace_key": namespace,
                "query": sentinel,
                "filters": {"realm": "documentation", "vector_channel": "original"},
                "return_k": 20,
                "recall_k": 100,
            },
        )
        assert excluded.status_code == 200, excluded.text
        assert excluded.json()["results"] == []
        assert_first_publication_closure(app, client, team_uuid, task_uuid)


def test_chinatax_member_namespace_hit(tmp_path: Path) -> None:
    _run_member(tmp_path, "chinatax")


def test_domain_member_namespace_hit(tmp_path: Path) -> None:
    _run_member(tmp_path, "domain")


def test_realestate_member_namespace_hit(tmp_path: Path) -> None:
    _run_member(tmp_path, "realestate")
