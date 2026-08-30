"""Append/read the one typed representation authority inside an Outcome UoW."""

from __future__ import annotations

from dataclasses import dataclass

from src.contracts.common.errors import ConflictError
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.contracts.intake.representation import (
    RepresentationObservation,
    RepresentationRouteFacts,
)
from src.contracts.intake.strategies import derive_selected_clean_strategy
from src.persistence.ports import UnitOfWork


@dataclass(frozen=True, slots=True)
class PreparedRepresentationAppend:
    fact_uuid: str
    history_uuid: str
    fact_digest: str
    observation: RepresentationObservation

    @property
    def reference(self) -> dict[str, str]:
        return {
            "representation_fact_uuid": self.fact_uuid,
            "representation_fact_digest": self.fact_digest,
        }


def prepare_representation_append(observation: RepresentationObservation) -> PreparedRepresentationAppend:
    return PreparedRepresentationAppend(
        fact_uuid=uuid7(),
        history_uuid=uuid7(),
        fact_digest=stable_digest(observation.model_dump(mode="json")),
        observation=observation,
    )


def representation_path_digest(rows: list[dict[str, str]]) -> str:
    """Hash only the frozen ordered path tuple, never row identities/timestamps."""

    return stable_digest(
        [
            {
                "step_key": row["step_key"],
                "capability": row["capability"],
                "raw_byte_digest": row["raw_byte_digest"],
                "representation_kind": row["representation_kind"],
                "observer_version": row["observer_version"],
                "main_text_presence": row.get("main_text_presence", "unknown"),
            }
            for row in rows
        ]
    )


async def append_representation_tx(
    tx: UnitOfWork,
    prepared: PreparedRepresentationAppend,
) -> str:
    """Append one fact/history pair; a second success for the step conflicts."""

    observation = prepared.observation
    existing = await tx.fetchone(
        "SELECT representation_fact_uuid,fact_digest FROM mkb_representation_facts "
        "WHERE execution_uuid=? AND step_key=?",
        (observation.execution_uuid, observation.step_key),
    )
    if existing is not None:
        raise ConflictError(
            "representation-step-conflict",
            "A representation step already has a successful durable fact",
            {"step_key": observation.step_key},
        )
    history = await tx.fetchall(
        "SELECT h.step_key,h.capability,h.raw_byte_digest,h.representation_kind,h.observer_version,"
        "f.main_text_presence "
        "FROM mkb_acquire_decode_history AS h "
        "JOIN mkb_representation_facts AS f ON f.representation_fact_uuid=h.representation_fact_uuid "
        "WHERE h.execution_uuid=? ORDER BY h.ordinal",
        (observation.execution_uuid,),
    )
    path = [
        {
            "step_key": str(row["step_key"]),
            "capability": str(row["capability"]),
            "raw_byte_digest": str(row["raw_byte_digest"]),
            "representation_kind": str(row["representation_kind"]),
            "observer_version": str(row["observer_version"]),
            "main_text_presence": str(row["main_text_presence"]),
        }
        for row in history
    ]
    path.append(
        {
            "step_key": observation.step_key,
            "capability": observation.capability,
            "raw_byte_digest": observation.raw_byte_digest,
            "representation_kind": observation.representation_kind,
            "observer_version": observation.observer_version,
            "main_text_presence": observation.main_text_presence,
        }
    )
    ordinal = len(path)
    path_digest = representation_path_digest(path)
    now = utc_now()
    await tx.execute(
        "INSERT INTO mkb_representation_facts("
        "representation_fact_uuid,team_uuid,execution_uuid,process_uuid,step_key,fact_kind,schema_version,capability,"
        "representation_kind,declared_media_type,detected_media_type,verified_media_type,raw_byte_digest,raw_byte_size,"
        "text_layer,main_text_presence,media_family,canonicalizer_key,canonicalizer_version,observer_key,observer_version,"
        "profile_identity,fact_digest,created_at,payload_extra) "
        "VALUES (?,?,?,?,?,?,'mkb.representation-fact.v1',?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'{}')",
        (
            prepared.fact_uuid,
            observation.team_uuid,
            observation.execution_uuid,
            observation.process_uuid,
            observation.step_key,
            observation.fact_kind,
            observation.capability,
            observation.representation_kind,
            observation.declared_media_type,
            observation.detected_media_type,
            observation.verified_media_type,
            observation.raw_byte_digest,
            observation.raw_byte_size,
            observation.text_layer,
            observation.main_text_presence,
            media_family(observation.verified_media_type),
            observation.canonicalizer_key,
            observation.canonicalizer_version,
            observation.observer_key,
            observation.observer_version,
            observation.profile_identity,
            prepared.fact_digest,
            now,
        ),
    )
    await tx.execute(
        "INSERT INTO mkb_acquire_decode_history("
        "history_uuid,team_uuid,execution_uuid,process_uuid,step_key,ordinal,capability,representation_fact_uuid,"
        "representation_fact_digest,raw_byte_digest,representation_kind,observer_version,representation_path_digest,"
        "created_at,payload_extra) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,'{}')",
        (
            prepared.history_uuid,
            observation.team_uuid,
            observation.execution_uuid,
            observation.process_uuid,
            observation.step_key,
            ordinal,
            observation.capability,
            prepared.fact_uuid,
            prepared.fact_digest,
            observation.raw_byte_digest,
            observation.representation_kind,
            observation.observer_version,
            path_digest,
            now,
        ),
    )
    return path_digest


class PersistenceRepresentationFactReader:
    """Tx-scoped reader used by Workflow guards; never parses Process JSON."""

    async def read_route_facts(
        self,
        *,
        tx: object,
        team_uuid: str,
        execution_uuid: str,
    ) -> RepresentationRouteFacts | None:
        row = await tx.fetchone(  # type: ignore[attr-defined]
            "SELECT f.main_text_presence,f.media_family,f.observer_key,f.observer_version,f.fact_digest,"
            "f.representation_kind,f.text_layer "
            "FROM mkb_acquire_decode_history h JOIN mkb_representation_facts f "
            "ON f.representation_fact_uuid=h.representation_fact_uuid "
            "WHERE h.team_uuid=? AND h.execution_uuid=? "
            "ORDER BY h.ordinal DESC LIMIT 1",
            (team_uuid, execution_uuid),
        )
        if row is None:
            return None
        selected = derive_selected_clean_strategy(
            media_family=str(row["media_family"]) if row.get("media_family") is not None else None,
            text_layer=str(row["text_layer"]) if row.get("text_layer") is not None else None,
            representation_kind=str(row["representation_kind"]) if row.get("representation_kind") is not None else None,
        )
        return RepresentationRouteFacts(
            main_text_presence=str(row["main_text_presence"]),  # type: ignore[arg-type]
            media_family=str(row["media_family"]),  # type: ignore[arg-type]
            observer_key=str(row["observer_key"]),
            observer_version=str(row["observer_version"]),
            fact_digest=str(row["fact_digest"]),
            selected_clean_strategy=selected,  # type: ignore[arg-type]
        )


def media_family(media_type: str) -> str:
    normalized = media_type.split(";", 1)[0].strip().casefold()
    if normalized == "application/pdf":
        return "pdf"
    if normalized.startswith("image/"):
        return "image"
    if normalized.startswith("text/") or normalized == "application/json":
        return "text"
    return "opaque"


def observe_main_text(value: str, *, media_type: str, text_layer: str = "not_applicable") -> str:
    if media_type.startswith("image/"):
        return "unknown"
    if text_layer in {"encrypted", "corrupt"}:
        return "unknown"
    observed = value
    if media_type == "text/html":
        from intake.text import extract_html_text

        try:
            observed, _ = extract_html_text(value)
        except Exception:
            return "unknown"
    return "present" if observed.strip() else "absent"


__all__ = [
    "PersistenceRepresentationFactReader",
    "PreparedRepresentationAppend",
    "append_representation_tx",
    "media_family",
    "observe_main_text",
    "prepare_representation_append",
    "representation_path_digest",
]
