"""The single MKB ASGI application and composition root."""

from __future__ import annotations

import asyncio
import re
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from datetime import timedelta

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

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
from src.runtime.inference.agent_router import AgentCliRouter, SubprocessAgentCli
from src.runtime.inference.claude_cli import DeterministicNs1Stub
from src.runtime.inference.facade import ConcurrencyGate, InferenceFacade
from src.runtime.inference.multimodal import (
    ObjectStoreMediaResolver,
    S11CleanLanguageModel,
    configured_multimodal_binding,
)
from src.runtime.inference.supply import SupplyBinding, SupplyFence
from src.runtime.intake.representation_history import PersistenceRepresentationFactReader
from src.runtime.intake_pipeline import IntakePipeline
from src.runtime.metrics import MetricRegistry, default_metrics
from src.runtime.object_gc import ObjectGcScanner, ObjectGcSchedule
from src.runtime.object_upload import ObjectUploadLifecycleScanner, ObjectUploadLifecycleSchedule
from src.runtime.roles import DeploymentRole, role_spec
from src.runtime.security import ActiveTokenSet, EgressPolicy, FixedWindowRateLimiter, SecretResolver, safe_request_id
from src.runtime.signals import DEFAULT_SIGNAL_REGISTRY, OperationalSignalRegistry
from src.runtime.supply.browser import HardenedBrowserRuntime
from src.runtime.supply.deterministic_ocr import IsolatedDeterministicOcr
from src.runtime.supply.pdf_parser import IsolatedPdfParser
from src.runtime.task_service import TaskService
from src.runtime.workflow.capability_registry import DEFAULT_PROCESS_CAPABILITY_REGISTRY, ProcessCapabilityRegistry
from src.runtime.workflow.dispatch import DispatchCaps
from src.runtime.workflow_engine import WorkflowRuntime, WorkflowWorker
from src.runtime.workflow_supervisor import WorkflowSupervisor
from src.services.artifacts import OutcomeArtifactCommitter
from src.services.billing import DefaultBillingService
from src.services.cleanup_jobs import CleanupJobService
from src.services.config_snapshots import ConfigSnapshotService
from src.services.events import DomainEventWriter, SecurityAuditWriter
from src.services.evidence_verification import EvidenceVerificationService
from src.services.governance_registry import GovernanceRegistryService
from src.services.index_retirement import IndexGenerationRetirementService
from src.services.intake_lifecycle import IntakeLifecycleService
from src.services.nhx1_cutover import Nhx1CutoverService
from src.services.object_gc import ObjectGcService
from src.services.object_upload import ObjectUploadService
from src.services.object_upload_ttl import ObjectUploadLifecycleService
from src.services.observability import (
    DiagnosticSink,
    ObservabilityReadService,
    ObservabilityRetentionService,
    RetentionPolicy,
)
from src.services.operator_control import OperatorControlService
from src.services.registry import RegistryService, default_enabled_inference_bindings
from src.services.retrieval import RetrievalService
from src.services.teams import TeamService
from src.services.workflow_catalog import WorkflowCatalogService
from src.services.workflow_registry import WorkflowRegistryService
from src.storage.local_store import LocalObjectStore
from src.workflows.builtin_lsrag import (
    BUILTIN_HTTP_RESOURCE_KIND_WORKFLOW,
    BUILTIN_INLINE_KIND_WORKFLOW,
    BUILTIN_LOCAL_OBJECT_KIND_WORKFLOW,
    BUILTIN_NHX1_EXECUTION_COMPATIBILITY_WORKFLOWS,
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
    governance: GovernanceRegistryService
    capability_registry: ProcessCapabilityRegistry
    workflow_catalog: WorkflowCatalogService
    signal_registry: OperationalSignalRegistry
    cleanup_jobs: CleanupJobService
    operator_control: OperatorControlService
    cutover: Nhx1CutoverService
    evidence_verification: EvidenceVerificationService
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
    pdf_parser: IsolatedPdfParser | None
    browser_runtime: HardenedBrowserRuntime | None
    clean_llm: S11CleanLanguageModel | None
    deterministic_ocr: IsolatedDeterministicOcr | None
    retrieval_access: ArtifactRetrievalAccess
    retrieval: RetrievalService
    outcome_committer: OutcomeArtifactCommitter
    workflow_runtime: WorkflowRuntime
    workflow_worker: WorkflowWorker
    workflow_supervisor: WorkflowSupervisor
    object_gc: ObjectGcService
    object_upload: ObjectUploadService
    object_upload_lifecycle: ObjectUploadLifecycleService
    object_upload_lifecycle_scanner: ObjectUploadLifecycleScanner
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
_PUBLIC_UPLOAD_PATH = re.compile(r"^/v1/teams/[0-9a-f-]{36}/objects:upload$")


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
    if inference_ok and (container.settings.inference_probe_enabled or container.settings.live_inference):
        try:
            # Probe the same exact L1 winners that admission freezes into L4;
            # a generic transport ping cannot prove the model/adapter/supply
            # identity is usable for future work.
            bindings = await container.registry.active_inference_bindings()
            if not container.settings.generation_local_enabled:
                bindings = tuple(binding for binding in bindings if binding.capability_key == "embed")
            inference_ok = all([await container.inference.probe_binding(binding) for binding in bindings])
        except Exception:
            inference_ok = False
    supplies = {
        "supply_pdf_parse": False,
        "supply_browser_render": False,
        "supply_browser_print_pdf": False,
        "supply_ocr_deterministic": False,
        "supply_s11_multimodal": False,
    }
    supply_required = container.settings.runtime_supply_readiness_required and role_spec(
        container.settings.deployment_role
    ).owns_workflow_claims
    if supply_required:

        async def safe(callable_probe) -> bool:  # type: ignore[no-untyped-def]
            if not callable(callable_probe):
                return False
            try:
                return bool(await callable_probe())
            except Exception:
                return False

        parser_probe = getattr(container.pdf_parser, "readiness", None)
        render_probe = (
            (lambda: container.browser_runtime.readiness("browser.render"))
            if container.browser_runtime is not None
            else None
        )
        print_probe = (
            (lambda: container.browser_runtime.readiness("browser.print_pdf"))
            if container.browser_runtime is not None
            else None
        )
        ocr_probe = getattr(container.deterministic_ocr, "readiness", None)
        multimodal_probe = getattr(container.clean_llm, "readiness", None)
        values = await asyncio.gather(
            safe(parser_probe),
            safe(render_probe),
            safe(print_probe),
            safe(ocr_probe),
            safe(multimodal_probe),
        )
        supplies = dict(zip(supplies, values, strict=True))
    supervisor = getattr(container, "workflow_supervisor", None)
    supervisor_ok = True
    # The explicitly split worker role is the hard claim/readiness owner.  A
    # small ``all`` deployment keeps its API/control plane available while a
    # best-effort maintenance/repair pass reports its own diagnostics; the
    # worker claim closure still consults health before leasing Process rows.
    if container.settings.deployment_role == DeploymentRole.WORKFLOW_WORKER.value and supervisor is not None:
        supervisor_ok = int(getattr(supervisor, "consecutive_failures", 0)) < container.settings.supervisor_failure_threshold
    return {
        **persistence,
        "registry_bootstrap": registry_ok,
        "object_root": storage_ok,
        "inference_binding": inference_ok,
        "obs_tables": obs_tables,
        "sec_token_loaded": container.tokens.loaded,
        "workflow_supervisor": supervisor_ok,
        **supplies,
    }


def _health_required(settings: Settings) -> tuple[str, ...]:
    spec = role_spec(settings.deployment_role)
    required = list(HealthAggregator.BASE_REQUIRED)
    if not spec.owns_workflow_claims:
        required.remove("workflow_supervisor")
        # API and maintenance processes do not claim model-bound work.
        required.remove("inference_binding")
    if not (settings.runtime_supply_readiness_required and spec.owns_workflow_claims):
        return tuple(required)
    supply = list(HealthAggregator.SUPPLY_REQUIRED)
    if not settings.multimodal_enabled or not settings.generation_local_enabled:
        supply = [name for name in supply if name != "supply_s11_multimodal"]
    return (*required, *supply)


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
    capability_registry = DEFAULT_PROCESS_CAPABILITY_REGISTRY
    workflows = WorkflowRegistryService(persistence, capability_registry)
    governance = GovernanceRegistryService(persistence, capability_registry)
    signal_registry = DEFAULT_SIGNAL_REGISTRY
    workflow_catalog = WorkflowCatalogService(persistence, workflows, capability_registry)
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
        generate_timeout_seconds=settings.inference_generate_timeout_seconds,
        media_resolver=ObjectStoreMediaResolver(storage),
    )
    enabled_bindings = default_enabled_inference_bindings()
    multimodal_binding = configured_multimodal_binding(
        model_key=settings.multimodal_model_key,
        model_version=settings.multimodal_model_version,
    )
    supply_fence = SupplyFence(
        [
            SupplyBinding.from_binding(
                binding,
                base_url=settings.inference_vllm_base_url,
                secret_slot=secret_slot,
            )
            for binding in (
                *enabled_bindings,
                *((multimodal_binding,) if settings.multimodal_enabled and settings.generation_local_enabled else ()),
            )
        ]
    )
    dispatch_caps = DispatchCaps.from_settings(settings)
    inference_gate = ConcurrencyGate(
        settings.inference_max_in_flight,
        capability_limits={
            "embed": dispatch_caps.embed_running,
            "structured_generate": dispatch_caps.local_running,
            "text_generate": dispatch_caps.local_running,
            "cli": dispatch_caps.ni_running,
            "pdf.parse": settings.pdf_parser_concurrency,
            "browser.render": settings.browser_render_concurrency,
            "browser.print_pdf": settings.browser_print_concurrency,
            "s11.multimodal": settings.multimodal_concurrency,
            "ocr.deterministic": settings.deterministic_ocr_concurrency,
        },
    )
    inference = InferenceFacade(
        adapter,
        max_in_flight=settings.inference_max_in_flight,
        max_attempts=settings.inference_max_attempts,
        capability_limits={
            "embed": dispatch_caps.embed_running,
            "structured_generate": dispatch_caps.local_running,
            "text_generate": dispatch_caps.local_running,
        },
        supply_fence=supply_fence,
        metrics=metrics,
        dispatch_caps=dispatch_caps,
        gate=inference_gate,
    )
    text_binding = next(binding for binding in enabled_bindings if binding.capability_key == "text_generate")
    clean_llm = (
        S11CleanLanguageModel(
            inference,
            text_binding=text_binding,
            multimodal_binding=multimodal_binding,
        )
        if settings.multimodal_enabled and settings.generation_local_enabled
        else None
    )
    deterministic_ocr: IsolatedDeterministicOcr | None = None
    if settings.deterministic_ocr_enabled:
        try:
            deterministic_ocr = IsolatedDeterministicOcr.discover(
                gate=inference_gate,
                timeout_seconds=settings.deterministic_ocr_timeout_seconds,
            )
        except MkbError:
            deterministic_ocr = None
    config_snapshots = ConfigSnapshotService(persistence, storage, workflows, settings, security_audit=security_audit)
    tasks = TaskService(persistence, teams, events, config_snapshots, metrics=metrics)
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
    pdf_parser: IsolatedPdfParser | None = None
    if settings.pdf_parser_enabled:
        try:
            pdf_parser = IsolatedPdfParser.discover(
                parser_binary=settings.pdf_parser_binary,
                timeout_seconds=settings.pdf_parser_timeout_seconds,
                gate=inference_gate,
            )
        except MkbError:
            # Composition remains live enough to expose an honest typed 503 and
            # a negative readiness component.  Missing native supply must not
            # turn into a silent observer fallback or an import-time crash.
            pdf_parser = None
    browser_runtime: HardenedBrowserRuntime | None = None
    if settings.browser_runtime_enabled:
        try:
            browser_runtime = HardenedBrowserRuntime.discover(
                acquirer=http_acquirer,
                gate=inference_gate,
                browser_binary=settings.browser_binary,
                webdriver_binary=settings.browser_webdriver_binary,
                render_timeout_seconds=settings.browser_render_timeout_seconds,
                print_timeout_seconds=settings.browser_print_timeout_seconds,
                render_output_bytes=settings.browser_render_max_bytes,
                print_output_bytes=settings.browser_print_max_bytes,
            )
        except MkbError:
            browser_runtime = None

    role = role_spec(settings.deployment_role)
    if role.owns_workflow_claims:
        supply_inventory = None
        if settings.runtime_supply_readiness_required:
            supply_inventory = {
                "pdf.parse": pdf_parser is not None,
                "browser.render": browser_runtime is not None,
                "browser.print_pdf": browser_runtime is not None,
                "ocr.deterministic": deterministic_ocr is not None,
                "s11.multimodal": clean_llm is not None,
            }
        claimable_process_keys = capability_registry.claimable_process_keys(
            DeploymentRole(settings.deployment_role), available_supplies=supply_inventory
        )
        if settings.worker_capabilities:
            unknown = sorted(set(settings.worker_capabilities) - {item.process_key for item in capability_registry.manifests})
            if unknown:
                raise ValueError(f"worker_capability_allowlist contains unknown process keys: {unknown}")
            claimable_process_keys = frozenset(set(claimable_process_keys) & set(settings.worker_capabilities))
    else:
        claimable_process_keys = frozenset()

    async def workflow_claim_readiness() -> bool:
        """Fence workers on the same complete readiness closure as admission."""

        if not role.owns_workflow_claims:
            return False
        return (await container.health.ready())["status"] == "ready"

    workflow_runtime = WorkflowRuntime(
        persistence,
        BUILTIN_INLINE_KIND_WORKFLOW,
        additional_definitions=(
            BUILTIN_LOCAL_OBJECT_KIND_WORKFLOW,
            BUILTIN_HTTP_RESOURCE_KIND_WORKFLOW,
            # Old profile keys stay enabled-but-unselected so an in-flight
            # Execution can resolve its exact compiled digest.
            BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW,
            *BUILTIN_SOURCE_PROFILE_WORKFLOWS,
            BUILTIN_REGISTERED_API_SCATTER_ROOT_WORKFLOW,
            BUILTIN_REGISTERED_API_SCATTER_CHILD_WORKFLOW,
        ),
        compatibility_definitions=BUILTIN_NHX1_EXECUTION_COMPATIBILITY_WORKFLOWS,
        readiness=workflow_claim_readiness,
        outcome_committer=outcome_committer,
        billing=DefaultBillingService(),
        dispatch_caps=dispatch_caps,
        live_inference=settings.live_inference,
        local_generation_enabled=settings.generation_local_enabled,
        cleanup_recovery_window_seconds=settings.workflow_cleanup_recovery_window_seconds,
        metrics=metrics,
        representation_facts=PersistenceRepresentationFactReader(),
        claimable_process_keys=claimable_process_keys,
        model_capacity_priority_gate_enabled=settings.model_capacity_priority_gate_enabled,
    )
    # S09 retirement intent creation is part of a successful pointer cutover,
    # so construct it before the pipeline rather than only for the scanner.
    index_retirement = IndexGenerationRetirementService(
        persistence,
        grace=timedelta(seconds=settings.index_retirement_grace_seconds),
    )
    ns1_cli = None
    if settings.ns1_cli_mode == "stub":
        ns1_cli = DeterministicNs1Stub(concurrency_gate=inference_gate)
    elif settings.ns1_cli_mode == "subprocess":
        provider_executables = {
            "claude": settings.ns1_cli_executable,
            "agy": settings.ns1_agy_executable,
            "cursor-agent": settings.ns1_cursor_agent_executable,
            "grok": settings.ns1_grok_executable,
        }
        ns1_cli = AgentCliRouter(
            {
                provider: SubprocessAgentCli(
                    provider=provider,
                    executable=provider_executables[provider],
                    model=settings.ns1_primary_model if provider == "claude" else None,
                )
                for provider in settings.ns1_providers
            },
            primary_model=settings.ns1_primary_model,
            provider_plan=settings.ns1_providers,
            max_concurrency=settings.ns1_cli_max_concurrency,
            provider_limits={
                "claude": settings.ns1_claude_concurrency,
                "agy": settings.ns1_agy_concurrency,
                "cursor-agent": settings.ns1_fallback_concurrency,
                "grok": settings.ns1_fallback_concurrency,
            },
        )
    diagnostic_sidecar = None
    if settings.persistence_backend == "turso":
        from src.persistence.turso.sidecar import TursoDiagnosticSidecar

        diagnostic_sidecar = TursoDiagnosticSidecar(settings.resolved_database_path)
    diagnostics = DiagnosticSink(persistence, metrics, sidecar=diagnostic_sidecar)
    workflow_worker = WorkflowWorker(
        workflow_runtime,
        IntakePipeline(
            persistence,
            storage,
            outcome_committer,
            http_fetcher=http_acquirer,
            browser_fetcher=browser_runtime,
            clean_llm=clean_llm,
            deterministic_ocr=deterministic_ocr,
            inference=inference,
            claude_cli=ns1_cli,
            live_inference=settings.live_inference and settings.generation_local_enabled,
            generation_local_enabled=settings.generation_local_enabled,
            acquisition_max_response_bytes=settings.acquisition_max_response_bytes,
            print_max_response_bytes=settings.browser_print_max_bytes,
            pdf_parser=pdf_parser,
            billing=DefaultBillingService(),
            lifecycle=lifecycle,
            index_retirement=index_retirement,
            diagnostics=diagnostics,
        ),
    )
    workflow_supervisor = WorkflowSupervisor(workflow_runtime, workflow_worker)
    object_gc = ObjectGcService(
        persistence,
        storage,
        orphan_grace=timedelta(seconds=settings.object_gc_grace_seconds),
    )
    object_upload = ObjectUploadService(persistence, storage)
    object_upload_lifecycle = ObjectUploadLifecycleService(
        persistence,
        storage,
        pending_ttl=timedelta(seconds=settings.object_upload_pending_ttl_seconds),
        staging_ttl=timedelta(seconds=settings.object_staging_ttl_seconds),
    )
    cleanup_jobs = CleanupJobService(
        persistence,
        retention=timedelta(seconds=settings.object_gc_grace_seconds),
    )
    operator_control = OperatorControlService(persistence, workflow_runtime, cleanup_jobs)
    cutover = Nhx1CutoverService(persistence)
    evidence_verification = EvidenceVerificationService(persistence)
    object_upload_lifecycle_scanner = ObjectUploadLifecycleScanner(
        object_upload_lifecycle,
        ObjectUploadLifecycleSchedule(
            interval=timedelta(seconds=settings.object_gc_interval_seconds),
            batch_size=settings.object_gc_batch_size,
        ),
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
        governance=governance,
        capability_registry=capability_registry,
        workflow_catalog=workflow_catalog,
        signal_registry=signal_registry,
        cleanup_jobs=cleanup_jobs,
        operator_control=operator_control,
        cutover=cutover,
        evidence_verification=evidence_verification,
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
        pdf_parser=pdf_parser,
        browser_runtime=browser_runtime,
        clean_llm=clean_llm,
        deterministic_ocr=deterministic_ocr,
        retrieval_access=retrieval_access,
        retrieval=retrieval,
        outcome_committer=outcome_committer,
        workflow_runtime=workflow_runtime,
        workflow_worker=workflow_worker,
        workflow_supervisor=workflow_supervisor,
        object_gc=object_gc,
        object_upload=object_upload,
        object_upload_lifecycle=object_upload_lifecycle,
        object_upload_lifecycle_scanner=object_upload_lifecycle_scanner,
        object_gc_scanner=object_gc_scanner,
        index_retirement=index_retirement,
        index_retirement_scanner=index_retirement_scanner,
        observability=observability,
        observability_retention=observability_retention,
        health=None,  # type: ignore[arg-type]
    )

    async def probe() -> dict[str, bool]:
        return await _probe(container)

    container.health = HealthAggregator(
        probe,
        metrics,
        ttl_seconds=30 if settings.runtime_supply_readiness_required else 0.5,
        cache_fingerprint=lambda: container.tokens.active_fingerprints,
        required=_health_required(settings),
    )
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
        container.health.bootstrap_failures += 1
        container.metrics.increment("mkb_repair_applied_total", 1, outcome="fail")
    try:
        await container.workflows.bootstrap()
    except MkbError:
        container.health.bootstrap_failures += 1
        container.metrics.increment("mkb_repair_applied_total", 1, outcome="fail")
    try:
        await container.governance.bootstrap()
    except MkbError:
        container.health.bootstrap_failures += 1
        container.metrics.increment("mkb_repair_applied_total", 1, outcome="fail")
    try:
        await container.cutover.ensure_state()
    except MkbError:
        container.health.bootstrap_failures += 1
        container.metrics.increment("mkb_repair_applied_total", 1, outcome="fail")
    await container.storage.readiness()
    stop = asyncio.Event()
    role = role_spec(container.settings.deployment_role)
    worker_task = (
        asyncio.create_task(container.workflow_supervisor.run(stop), name="mkb-workflow-supervisor")
        if role.owns_workflow_claims
        else None
    )
    gc_task = (
        asyncio.create_task(container.object_gc_scanner.run_forever(stop), name="mkb-object-gc")
        if role.owns_maintenance and container.settings.object_gc_enabled
        else None
    )
    upload_lifecycle_task = (
        asyncio.create_task(
            container.object_upload_lifecycle_scanner.run_forever(stop),
            name="mkb-object-upload-lifecycle",
        )
        if role.owns_maintenance and container.settings.object_gc_enabled
        else None
    )
    index_retirement_task = (
        asyncio.create_task(
            container.index_retirement_scanner.run_forever(stop),
            name="mkb-index-generation-retirement",
        )
        if role.owns_maintenance and container.settings.index_retirement_enabled
        else None
    )
    retention_task = (
        asyncio.create_task(
            _run_retention_loop(
                container.observability_retention,
                stop,
                interval_seconds=container.settings.obs_retention_interval_seconds,
            ),
            name="mkb-observability-retention",
        )
        if role.owns_retention
        else None
    )
    try:
        yield
    finally:
        stop.set()
        for background_task in (
            worker_task,
            gc_task,
            upload_lifecycle_task,
            index_retirement_task,
            retention_task,
        ):
            if background_task is not None:
                with suppress(asyncio.CancelledError):
                    await background_task
        closer = getattr(container.inference, "aclose", None)
        if closer is not None:
            with suppress(Exception):
                await closer()
        await container.persistence.close()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(title="MKB leaf worker", version="1.0.0", lifespan=lifespan)
    app.state.container = create_container(settings)
    hosts = [item.strip() for item in settings.http_trusted_hosts.split(",") if item.strip()]
    if "pytest" in sys.modules and "testserver" not in hosts:
        hosts.append("testserver")
    if hosts:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts)

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
        container: Container = request.app.state.container
        result = await container.health.ready()
        if result["status"] != "ready":
            container.signal_registry.emit(container.metrics, "readiness.false")
        deployment = role_spec(container.settings.deployment_role)
        content = {
            **result,
            "deployment_role": deployment.role.value,
            "owned_loops": deployment.loop_names,
            "capability_manifest_digest": container.capability_registry.definition_digest,
            "claimable_process_keys": tuple(sorted(container.workflow_runtime.claimable_process_keys or ())),
        }
        return JSONResponse(status_code=200 if result["status"] == "ready" else 503, content=content)

    @app.get("/metrics", tags=["operations"])
    async def metrics(request: Request) -> PlainTextResponse:
        await require_metrics_access(request)
        registry: MetricRegistry = request.app.state.container.metrics
        if registry.cardinality_drops:
            registry.increment("mkb_metric_cardinality_drop_total", registry.cardinality_drops, reason="invalid_label")
            registry.cardinality_drops = 0
        return PlainTextResponse(registry.render(), media_type="text/plain; version=0.0.4")

    @app.middleware("http")
    async def reject_oversize_body(request: Request, call_next):  # type: ignore[no-untyped-def]
        if request.method == "POST" and _PUBLIC_UPLOAD_PATH.fullmatch(request.url.path):
            object_cap = int(getattr(request.app.state.container.settings, "object_max_bytes", 256 * 1024 * 1024))
            length = request.headers.get("content-length")
            if length:
                try:
                    if int(length) > object_cap:
                        error = MkbError("OBJECT_BUDGET_SIZE", "Object exceeds the configured size limit", 413)
                        return JSONResponse(status_code=413, content=error.as_dict(_public_request_id(request)))
                except ValueError:
                    pass
            # Do not consume or cache this body: the upload handler streams it
            # directly through the object-specific bounded CAS port.
            return await call_next(request)
        cap = int(getattr(request.app.state.container.settings, "max_request_bytes", 1_048_576))
        length = request.headers.get("content-length")
        if length:
            try:
                if int(length) > cap:
                    error = MkbError("REQUEST_BODY_TOO_LARGE", "Request body exceeds the configured cap", 413)
                    return JSONResponse(status_code=413, content=error.as_dict(_public_request_id(request)))
            except ValueError:
                pass
        chunks: list[bytes] = []
        total = 0
        async for chunk in request.stream():
            total += len(chunk)
            if total > cap:
                error = MkbError("REQUEST_BODY_TOO_LARGE", "Request body exceeds the configured cap", 413)
                return JSONResponse(status_code=413, content=error.as_dict(_public_request_id(request)))
            chunks.append(chunk)
        request._body = b"".join(chunks)  # type: ignore[attr-defined]
        return await call_next(request)

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
