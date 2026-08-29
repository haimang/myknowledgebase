"""NH4-T03: public object surface is upload/stat only, never raw bytes."""

from __future__ import annotations

import inspect

from api.public.routes import router
from src.contracts.api.objects import PublicObjectView


def test_public_router_has_upload_stat_and_zero_raw_list_presign() -> None:
    routes = {(frozenset(route.methods or ()), route.path) for route in router.routes}
    assert (frozenset({"POST"}), "/v1/teams/{team_uuid}/objects:upload") in routes
    assert (frozenset({"GET"}), "/v1/teams/{team_uuid}/objects:stat") in routes
    assert (frozenset({"POST"}), "/v1/teams/{team_uuid}/objects:cancel") in routes
    object_routes = [(methods, path) for methods, path in routes if "object" in path]
    assert len(object_routes) == 3
    assert all("raw" not in path and "presign" not in path and "list" not in path for _, path in object_routes)

    source = inspect.getsource(__import__("api.public.routes", fromlist=["router"]))
    assert "StreamingResponse" not in source
    assert "FileResponse" not in source
    assert "presign" not in source.casefold()


def test_public_object_view_is_metadata_closed_set() -> None:
    assert set(PublicObjectView.model_fields) == {
        "handle",
        "digest",
        "size_bytes",
        "media_type",
        "disposition",
    }
    assert not {"path", "filename", "object_root", "stored_object_uuid"} & set(PublicObjectView.model_fields)
