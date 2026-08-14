"""The single MKB ASGI application and composition root."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from datetime import timedelta

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse

from api.dependencies import require_metrics_access
from api.internal.routes import router as internal_router
from api.public.routes import router as public_router
from src.contracts.common.errors import MkbError
from src.contracts.common.ids import uuid7, validate_external_uuid
from src.llm_adapters.local_vllm import LocalVllmAdapter
from src.persistence.factory import PersistenceEngine, build_persistence
from src.persistence.retrieval_access import ArtifactRetrievalAccess
from src.runtime.config import Settings
from src.runtime.health import HealthAggregator
from src.runtime.http_acquisition import HttpAcquirer
from src.runtime.index_retirement import IndexGenerationRetirementScanner, IndexGenerationRetirementSchedule
from src.runtime.inference.claude_cli import DeterministicNs1Stub, SubprocessClaudeCli
from src.runtime.inference.facade import InferenceFacade
from src.runtime.inference.supply import SupplyBinding, SupplyFence
from src.runtime.intake_pipeline import IntakePipeline
from src.runtime.metrics import MetricRegistry, default_metrics
from src.runtime.object_gc import ObjectGcScanner, ObjectGcSchedule
from src.runtime.security import ActiveTokenSet, EgressPolicy, FixedWindowRateLimiter, SecretResolver, safe_request_id
from src.runtime.task_service import TaskService
from src.runtime.workflow_engine import WorkflowRuntime, WorkflowWorker
from src.runtime.workflow_supervisor import WorkflowSupervisor
from src.services.artifacts import OutcomeArtifactCommitter
from src.services.config_snapshots import ConfigSnapshotService
from src.services.events import DomainEventWriter, SecurityAuditWriter
from src.services.index_retirement import IndexGenerationRetirementService
from src.services.intake_lifecycle import IntakeLifecycleService
from src.services.object_gc import ObjectGcService
from src.services.observability import ObservabilityReadService, ObservabilityRetentionService, RetentionPolicy
from src.services.registry import RegistryService, default_enabled_inference_bindings
from src.services.retrieval import RetrievalService
from src.services.teams import TeamService
from src.services.workflow_registry import WorkflowRegistryService
from src.storage.local_store import LocalObjectStore
from src.workflows.builtin_lsrag import (
    BUILTIN_EXECUTION_COMPATIBILITY_WORKFLOWS,
    BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW,
    BUILTIN_SOURCE_PROFILE_WORKFLOWS,
)
from src.workflows.builtin_scatter import (
    BUILTIN_REGISTERED_API_SCATTER_CHILD_WORKFLOW,
    BUILTIN_REGISTERED_API_SCATTER_ROOT_WORKFLOW,
)


@dataclass(slots=True)
class Container:
    settings: Settings
    persistence: PersistenceEngine
    storage: LocalObjectStore
    registry: RegistryService
    workflows: WorkflowRegistryService
    config_snapshots: ConfigSnapshotService
    tokens: ActiveTokenSet
    rate_limiter: FixedWindowRateLimiter
    metrics: MetricRegistry
    events: DomainEventWriter
    security_audit: SecurityAuditWriter
    teams: TeamService
    lifecycle: IntakeLifecycleService
    tasks: TaskService
    inference: InferenceFacade
    retrieval_access: ArtifactRetrievalAccess
    retrieval: RetrievalService
    outcome_committer: OutcomeArtifactCommitter
    workflow_runtime: WorkflowRuntime
    workflow_worker: WorkflowWorker
    workflow_supervisor: WorkflowSupervisor
    object_gc: ObjectGcService
    object_gc_scanner: ObjectGcScanner
    index_retirement: IndexGenerationRetirementService
    index_retirement_scanner: IndexGenerationRetirementScanner
    observability: ObservabilityReadService
    observability_retention: ObservabilityRetentionService
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


_INFERENCE_VLLM_TOKEN_SLOT = "INFERENCE_VLLM_TOKEN"


def _model_secret_resolver(settings: Settings) -> tuple[str | None, SecretResolver | None]:
    """Resolve one mounted inference credential without putting it in L4.

    Env token is the T-O-333 primary path.  A secret file remains a fallback
    when the env value is unset.  Neither value enters snapshots or DB rows.
    """

    env_token = settings.inference_vllm_token
    env_value = env_token.get_secret_value().strip() if env_token is not None else ""
    if env_value:
        slot = settings.inference_secret_slot or _INFERENCE_VLLM_TOKEN_SLOT
        return slot, SecretResolver({slot: env_value})
    if settings.inference_secret_slot is None:
        if settings.inference_secret_file is not None:
            raise ValueError("inference_secret_file requires inference_secret_slot")
        return None, None
    if settings.inference_secret_file is None:
        raise ValueError("inference_secret_slot requires inference_secret_file")
    try:
        value = settings.inference_secret_file.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise ValueError("inference secret file is unavailable") from exc
    return settings.inference_secret_slot, SecretResolver({settings.inference_secret_slot: value})


async def _probe(container: Container) -> dict[str, bool]:
    persistence = await container.persistence.readiness()
    registry_ok = await container.registry.readiness() and await container.workflows.readiness()
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
        try:
            # Probe the same exact L1 winners that admission freezes into L4;
            # a generic transport ping cannot prove the model/adapter/supply
            # identity is usable for future work.
            bindings = await container.registry.active_inference_bindings()
            inference_ok = all([await container.inference.probe_binding(binding) for binding in bindings])
        except Exception:
            inference_ok = False
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
    persistence = build_persistence(
        settings.resolved_database_path,
        settings.migration_directory,
        backend=settings.persistence_backend,
        vector_backend=settings.vector_backend,
        concurrent_writes_required=settings.concurrent_writes_required,
        native_vector_required=settings.native_vector_required,
    )
    storage = LocalObjectStore(settings.resolved_object_root, max_object_bytes=settings.object_max_bytes)
    registry = RegistryService(persistence, settings.prompt_root)
    workflows = WorkflowRegistryService(persistence)
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
    lifecycle = IntakeLifecycleService(persistence, events)
    secret_slot, secret_resolver = _model_secret_resolver(settings)
    adapter = LocalVllmAdapter(
        settings.inference_vllm_base_url,
        secret_slot=secret_slot,
        secret_resolver=secret_resolver,
    )
    supply_fence = SupplyFence(
        [
            SupplyBinding.from_binding(
                binding,
                base_url=settings.inference_vllm_base_url,
                secret_slot=secret_slot,
            )
            for binding in default_enabled_inference_bindings()
        ]
    )
    inference = InferenceFacade(
        adapter,
        max_in_flight=settings.inference_max_in_flight,
        max_attempts=settings.inference_max_attempts,
        supply_fence=supply_fence,
        metrics=metrics,
    )
    config_snapshots = ConfigSnapshotService(persistence, storage, workflows, settings)
    tasks = TaskService(persistence, teams, events, config_snapshots)
    retrieval_access = ArtifactRetrievalAccess(persistence, storage)
    retrieval = RetrievalService(
        persistence,
        inference,
        body_port=retrieval_access,
        eligibility_port=retrieval_access,
        live_inference=settings.live_inference,
    )
    outcome_committer = OutcomeArtifactCommitter(storage)
    http_acquirer = HttpAcquirer(
        EgressPolicy(
            allow_literal_ip=settings.egress_allow_literal_ip,
            allow_private_default=settings.egress_allow_private_default,
            max_redirects=settings.egress_max_redirects,
        ),
        allow_http=settings.egress_allow_http,
        max_response_bytes=settings.acquisition_max_response_bytes,
        on_egress_denied=lambda reason: metrics.increment("mkb_sec_egress_denied_total", reason=reason),
    )

    async def workflow_claim_readiness() -> bool:
        """Fence workers on the same complete readiness closure as admission."""

        return (await container.health.ready())["status"] == "ready"

    workflow_runtime = WorkflowRuntime(
        persistence,
        BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW,
        additional_definitions=(
            BUILTIN_REGISTERED_API_SCATTER_ROOT_WORKFLOW,
            BUILTIN_REGISTERED_API_SCATTER_CHILD_WORKFLOW,
            *BUILTIN_SOURCE_PROFILE_WORKFLOWS,
        ),
        compatibility_definitions=BUILTIN_EXECUTION_COMPATIBILITY_WORKFLOWS,
        readiness=workflow_claim_readiness,
        outcome_committer=outcome_committer,
        cleanup_recovery_window_seconds=settings.workflow_cleanup_recovery_window_seconds,
    )
    # S09 retirement intent creation is part of a successful pointer cutover,
    # so construct it before the pipeline rather than only for the scanner.
    index_retirement = IndexGenerationRetirementService(
        persistence,
        grace=timedelta(seconds=settings.index_retirement_grace_seconds),
    )
    ns1_cli = None
    if settings.ns1_cli_mode == "stub":
        ns1_cli = DeterministicNs1Stub()
    elif settings.ns1_cli_mode == "subprocess":
        ns1_cli = SubprocessClaudeCli(executable=settings.ns1_cli_executable)
    workflow_worker = WorkflowWorker(
        workflow_runtime,
        IntakePipeline(
            persistence,
            storage,
            outcome_committer,
            http_fetcher=http_acquirer,
            inference=inference,
            claude_cli=ns1_cli,
            live_inference=settings.live_inference,
            lifecycle=lifecycle,
            index_retirement=index_retirement,
        ),
    )
    workflow_supervisor = WorkflowSupervisor(workflow_runtime, workflow_worker)
    object_gc = ObjectGcService(
        persistence,
        storage,
        orphan_grace=timedelta(seconds=settings.object_gc_grace_seconds),
    )
    object_gc_scanner = ObjectGcScanner(
        object_gc,
        ObjectGcSchedule(
            interval=timedelta(seconds=settings.object_gc_interval_seconds),
            batch_size=settings.object_gc_batch_size,
        ),
    )
    index_retirement_scanner = IndexGenerationRetirementScanner(
        index_retirement,
        IndexGenerationRetirementSchedule(
            interval=timedelta(seconds=settings.index_retirement_interval_seconds),
            batch_size=settings.index_retirement_batch_size,
        ),
    )
    observability = ObservabilityReadService(persistence)
    observability_retention = ObservabilityRetentionService(
        persistence,
        metrics,
        policy=RetentionPolicy(
            domain_events_days=settings.obs_retention_domain_events_days,
            diagnostic_logs_days=settings.obs_retention_diagnostic_logs_days,
            security_audit_days=settings.obs_retention_security_audit_days,
            batch_size=settings.obs_retention_batch_size,
        ),
    )
    # Create once so the probe closure sees the final composition root.
    container = Container(
        settings=settings,
        persistence=persistence,
        storage=storage,
        registry=registry,
        workflows=workflows,
        config_snapshots=config_snapshots,
        tokens=tokens,
        rate_limiter=rate_limiter,
        metrics=metrics,
        events=events,
        security_audit=security_audit,
        teams=teams,
        lifecycle=lifecycle,
        tasks=tasks,
        inference=inference,
        retrieval_access=retrieval_access,
        retrieval=retrieval,
        outcome_committer=outcome_committer,
        workflow_runtime=workflow_runtime,
        workflow_worker=workflow_worker,
        workflow_supervisor=workflow_supervisor,
        object_gc=object_gc,
        object_gc_scanner=object_gc_scanner,
        index_retirement=index_retirement,
        index_retirement_scanner=index_retirement_scanner,
        observability=observability,
        observability_retention=observability_retention,
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
        await container.workflows.bootstrap()
    except MkbError:
        pass
    await container.storage.readiness()
    stop = asyncio.Event()
    worker_task = asyncio.create_task(container.workflow_supervisor.run(stop), name="mkb-workflow-supervisor")
    gc_task = (
        asyncio.create_task(container.object_gc_scanner.run_forever(stop), name="mkb-object-gc")
        if container.settings.object_gc_enabled
        else None
    )
    index_retirement_task = (
        asyncio.create_task(
            container.index_retirement_scanner.run_forever(stop),
            name="mkb-index-generation-retirement",
        )
        if container.settings.index_retirement_enabled
        else None
    )
    retention_task = asyncio.create_task(
        _run_retention_loop(
            container.observability_retention,
            stop,
            interval_seconds=container.settings.obs_retention_interval_seconds,
        ),
        name="mkb-observability-retention",
    )
    try:
        yield
    finally:
        stop.set()
        for background_task in (worker_task, gc_task, index_retirement_task, retention_task):
            if background_task is not None:
                with suppress(asyncio.CancelledError):
                    await background_task
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
        await require_metrics_access(request)
        registry: MetricRegistry = request.app.state.container.metrics
        if registry.cardinality_drops:
            registry.increment("mkb_metric_cardinality_drop_total", registry.cardinality_drops, reason="invalid_label")
            registry.cardinality_drops = 0
        return PlainTextResponse(registry.render(), media_type="text/plain; version=0.0.4")

    app.include_router(public_router)
    app.include_router(internal_router)
    return app


async def _run_retention_loop(
    retention: ObservabilityRetentionService,
    stop: asyncio.Event,
    *,
    interval_seconds: int,
) -> None:
    """Run bounded evidence retention without making it a business-state worker."""

    while not stop.is_set():
        try:
            await retention.run_once()
        except Exception:
            # Retention must never change a business result.  It is retried on
            # its next bounded interval while the durable evidence stays live.
            pass
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval_seconds)
        except TimeoutError:
            continue


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run("api.app:app", host="127.0.0.1", port=8080, reload=False)
