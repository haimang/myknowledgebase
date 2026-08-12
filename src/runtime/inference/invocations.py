"""Best-effort S11 invocation evidence, isolated from business completion."""

from __future__ import annotations

import json
from typing import Protocol, runtime_checkable

from src.contracts.common.time import utc_now
from src.contracts.inference.models import InferenceInvocationRecord
from src.persistence.ports import PersistencePort


@runtime_checkable
class InferenceInvocationRecorder(Protocol):
    """A non-authoritative audit sink used by :class:`InferenceFacade`."""

    async def record(self, record: InferenceInvocationRecord) -> bool: ...


class SqlInferenceInvocationRecorder:
    """Write the D04 invocation ledger without ever defining business success.

    This recorder is intentionally opt-in.  S08's vectorization callback
    already records its successful invocation in the same transaction as the
    vector proof; wiring this recorder into that path would create duplicate
    evidence.  It is appropriate for facade consumers that have no owning
    business transaction (for example a standalone typed generation call).
    """

    _PAYLOAD_KEYS = (
        "prompt_content_hash",
        "schema_content_digest",
        "params_digest",
        "config_snapshot_digest",
    )

    def __init__(self, persistence: PersistencePort) -> None:
        self._persistence = persistence

    async def record(self, record: InferenceInvocationRecord) -> bool:
        context = record.context
        payload_extra = {
            key: getattr(context, key)
            for key in self._PAYLOAD_KEYS
            if context is not None and getattr(context, key) is not None
        }
        try:
            async with self._persistence.transaction() as tx:
                await tx.execute(
                    "INSERT OR IGNORE INTO mkb_inference_invocations "
                    "(invocation_uuid,team_uuid,trace_uuid,task_uuid,execution_uuid,process_uuid,capability_key,adapter_kind,"
                    "model_key,model_version,request_digest,status,error_code,input_tokens,output_tokens,total_tokens,latency_ms,"
                    "generation_invocation_uuid,occurred_at,payload_extra) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        record.invocation_uuid,
                        record.team_uuid,
                        None if context is None else context.trace_uuid,
                        None if context is None else context.task_uuid,
                        None if context is None else context.execution_uuid,
                        None if context is None else context.process_uuid,
                        record.capability_key,
                        record.adapter_kind,
                        record.model_key,
                        record.model_version,
                        record.request_digest,
                        record.status,
                        record.error_code,
                        None if record.usage is None else record.usage.input_tokens,
                        None if record.usage is None else record.usage.output_tokens,
                        None if record.usage is None else record.usage.total_tokens,
                        record.latency_ms,
                        None if context is None else context.generation_invocation_uuid,
                        utc_now(),
                        json.dumps(payload_extra, sort_keys=True, separators=(",", ":")),
                    ),
                )
        except Exception:
            # Invocation persistence is audit evidence, not a business CAS or
            # an excuse to turn an otherwise valid model response into failure.
            return False
        return True


__all__ = ["InferenceInvocationRecorder", "SqlInferenceInvocationRecorder"]
