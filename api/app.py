"""The single MKB ASGI application and composition root."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse

from api.internal.routes import router as internal_router
from api.public.routes import router as public_router
from src.contracts.common.errors import MkbError
from src.contracts.common.ids import uuid7, validate_external_uuid
from src.llm_adapters.local_vllm import LocalVllmAdapter
from src.persistence.sqlite_port import SqlitePersistence
from src.runtime.config import Settings
from src.runtime.health import HealthAggregator
from src.runtime.inference.facade import InferenceFacade
from src.runtime.metrics import MetricRegistry, default_metrics
from src.runtime.security import ActiveTokenSet, FixedWindowRateLimiter, safe_request_id
from src.runtime.task_service import TaskService
from src.services.events import DomainEventWriter, SecurityAuditWriter
from src.services.registry import RegistryService
from src.services.teams import TeamService
from src.storage.local_store import LocalObjectStore


@dataclass(slots=True)
class Container:
    settings: Settings
    persistence: SqlitePersistence
    storage: LocalObjectStore
    registry: RegistryService
    tokens: ActiveTokenSet
    rate_limiter: FixedWindowRateLimiter
    metrics: MetricRegistry
    events: DomainEventWriter
    security_audit: SecurityAuditWriter
    teams: TeamService
    tasks: TaskService
    inference: InferenceFacade
    health: HealthAggregator


def _public_error_trace_uuid(
    request: Request,
    *,
    body: object | None = None,
    explicit: str | None = None,
) -> str:
    """Return a safe request correlation trace without reflecting raw input.

    A valid Task Create body keeps its caller-owned root trace even when a
    sibling field fails validation.  Other rejected requests receive a fresh
    server trace so every public error envelope remains correlatable without
    trusting arbitrary header/body text.
    """

    candidates: list[object | None] = [explicit, getattr(request.state, "trace_uuid", None)]
    if isinstance(body, dict):
        candidates.append(body.get("trace_uuid"))
    candidates.append(request.headers.get("x-mkb-trace-uuid"))
    for candidate in candidates:
        try:
            return validate_external_uuid(candidate, field="trace_uuid")
        except Exception:
            continue
    return uuid7()


def _is_task_contract_request(request: Request) -> bool:
    """Keep Task schema failures distinct from unrelated public DTO errors."""

    path = request.url.path
    return path.startswith("/v1/teams/") and "/tasks" in path


def _public_request_id(request: Request) -> str:
    """Always put a safe correlation ID on public error envelopes."""

    return safe_request_id(request.headers.get("x-request-id")) or uuid7()


async def _probe(container: Container) -> dict[str, bool]:
    persistence = await container.persistence.readiness()
    registry_ok = await container.registry.readiness()
    storage_ok = await container.storage.readiness()
    obs_tables = False
    try:
        async with container.persistence.transaction() as tx:
            names = await tx.fetchall(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name IN ('mkb_domain_events','mkb_ops_diagnostic_logs','mkb_security_audit_events')"
            )
            obs_tables = len(names) == 3
    except Exception:
        obs_tables = False
    inference_ok = registry_ok
    if inference_ok and container.settings.inference_probe_enabled:
        inference_ok = await container.inference.probe()
    return {
        **persistence,
        "registry_bootstrap": registry_ok,
        "object_root": storage_ok,
        "inference_binding": inference_ok,
        "obs_tables": obs_tables,
        "sec_token_loaded": container.tokens.loaded,
    }


def create_container(settings: Settings | None = None) -> Container:
    settings = settings or Settings()
    persistence = SqlitePersistence(settings.resolved_database_path, settings.migration_directory)
    storage = LocalObjectStore(settings.resolved_object_root, max_object_bytes=settings.object_max_bytes)
    registry = RegistryService(persistence, settings.prompt_root)
    tokens = ActiveTokenSet(settings.active_tokens)
    rate_limiter = FixedWindowRateLimiter(
        ip_limit=settings.rate_limit_ip_per_min,
        token_limit=settings.rate_limit_token_per_min,
        window_seconds=settings.rate_limit_window_seconds,
    )
    metrics = default_metrics()
    events = DomainEventWriter()
    security_audit = SecurityAuditWriter()
    teams = TeamService(persistence)
    tasks = TaskService(persistence, teams, events)
    adapter = LocalVllmAdapter(settings.inference_vllm_base_url)
    inference = InferenceFacade(
        adapter,
        max_in_flight=settings.inference_max_in_flight,
        max_attempts=settings.inference_max_attempts,
    )
    # Create once so the probe closure sees the final composition root.
    container = Container(
        settings=settings,
        persistence=persistence,
        storage=storage,
        registry=registry,
        tokens=tokens,
        rate_limiter=rate_limiter,
        metrics=metrics,
        events=events,
        security_audit=security_audit,
        teams=teams,
        tasks=tasks,
        inference=inference,
        health=None,  # type: ignore[arg-type]
    )

    async def probe() -> dict[str, bool]:
        return await _probe(container)

    container.health = HealthAggregator(probe, metrics)
    return container


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    container: Container = app.state.container
    await container.persistence.migrate()
    # Bootstrap errors do not silently make the application usable; /ready and
    # all new business admission report not-ready until operators repair them.
    try:
        await container.registry.bootstrap()
    except MkbError:
        pass
    await container.storage.readiness()
    try:
        yield
    finally:
        await container.persistence.close()


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="MKB leaf worker", version="1.0.0", lifespan=lifespan)
    app.state.container = create_container(settings)

    @app.exception_handler(MkbError)
    async def mkb_error_handler(request: Request, exc: MkbError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.as_dict(
                _public_request_id(request),
                trace_uuid=_public_error_trace_uuid(request, explicit=exc.trace_uuid),
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        # FastAPI's default ``detail`` can reflect raw body fragments.  The
        # public contract intentionally returns one stable, non-echoing error
        # family instead.
        error = MkbError(
            "task-schema-invalid" if _is_task_contract_request(request) else "request-invalid",
            "Task request does not satisfy the typed public contract"
            if _is_task_contract_request(request)
            else "Request does not satisfy the typed public contract",
            422,
        )
        return JSONResponse(
            status_code=422,
            content=error.as_dict(
                _public_request_id(request),
                trace_uuid=_public_error_trace_uuid(request, body=exc.body),
            ),
        )

    @app.get("/live", tags=["probes"])
    @app.get("/healthz", tags=["probes"])
    async def live() -> dict[str, object]:
        # Do not touch app.state, a database, object root, registry, or HTTP.
        return {"status": "live", "live": True}

    @app.get("/ready", tags=["probes"])
    async def ready(request: Request) -> JSONResponse:
        result = await request.app.state.container.health.ready()
        return JSONResponse(status_code=200 if result["status"] == "ready" else 503, content=result)

    @app.get("/metrics", tags=["operations"])
    async def metrics(request: Request) -> PlainTextResponse:
        registry: MetricRegistry = request.app.state.container.metrics
        if registry.cardinality_drops:
            registry.increment("mkb_metric_cardinality_drop_total", registry.cardinality_drops)
            registry.cardinality_drops = 0
        return PlainTextResponse(registry.render(), media_type="text/plain; version=0.0.4")

    app.include_router(public_router)
    app.include_router(internal_router)
    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run("api.app:app", host="127.0.0.1", port=8080, reload=False)
