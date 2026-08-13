"""Versioned provider-operation registry; unknown bindings fail closed."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError

from intake.api.providers import (
    parse_chinatax_member,
    parse_domain_member,
    parse_realestate_member,
    unpack_chinatax_envelope,
    unpack_domain_envelope,
    unpack_realestate_envelope,
)
from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest
from src.contracts.intake.providers import (
    ChinaTaxEnvelope,
    ChinaTaxGetArticlesRequest,
    ChinaTaxRawMember,
    DomainEnvelope,
    DomainGetAgencyListingsRequest,
    DomainRawMember,
    RealestateEnvelope,
    RealestateGetListingsRequest,
    RealestateRawMember,
)
from src.contracts.intake.semantics import MappedProviderMember


@dataclass(frozen=True, slots=True)
class ProviderOperationDefinition:
    provider: str
    operation: str
    definition_version: str
    request_model: type[BaseModel]
    envelope_model: type[BaseModel]
    member_model: type[BaseModel]
    parser: Callable[[Any], MappedProviderMember]
    envelope_unpacker: Callable[[Any], list[Any]]

    @property
    def manifest(self) -> dict[str, Any]:
        schemas = {
            "request": self.request_model.model_json_schema(),
            "envelope": self.envelope_model.model_json_schema(),
            "member": self.member_model.model_json_schema(),
        }
        return {
            "provider": self.provider,
            "operation": self.operation,
            "definition_version": self.definition_version,
            "request_schema_ref": f"mkb.intake.provider.{self.provider}.{self.operation}.request.v1",
            "request_schema_digest": stable_digest(schemas["request"]),
            "envelope_schema_ref": f"mkb.intake.provider.{self.provider}.{self.operation}.envelope.v1",
            "envelope_schema_digest": stable_digest(schemas["envelope"]),
            "member_schema_ref": f"mkb.intake.provider.{self.provider}.{self.operation}.member.v1",
            "member_schema_digest": stable_digest(schemas["member"]),
            "normalizer_key": f"intake.api.{self.provider}.{self.operation}",
            "normalizer_version": "v1",
            "cardinality": "scatter",
        }

    @property
    def definition_digest(self) -> str:
        return stable_digest(self.manifest)


REGISTERED_PROVIDER_OPERATIONS: tuple[ProviderOperationDefinition, ...] = (
    ProviderOperationDefinition(
        provider="chinatax",
        operation="get_articles",
        definition_version="v1",
        request_model=ChinaTaxGetArticlesRequest,
        envelope_model=ChinaTaxEnvelope,
        member_model=ChinaTaxRawMember,
        parser=parse_chinatax_member,
        envelope_unpacker=unpack_chinatax_envelope,
    ),
    ProviderOperationDefinition(
        provider="domain",
        operation="get_agency_listings",
        definition_version="v1",
        request_model=DomainGetAgencyListingsRequest,
        envelope_model=DomainEnvelope,
        member_model=DomainRawMember,
        parser=parse_domain_member,
        envelope_unpacker=unpack_domain_envelope,
    ),
    ProviderOperationDefinition(
        provider="realestate",
        operation="get_listings",
        definition_version="v1",
        request_model=RealestateGetListingsRequest,
        envelope_model=RealestateEnvelope,
        member_model=RealestateRawMember,
        parser=parse_realestate_member,
        envelope_unpacker=unpack_realestate_envelope,
    ),
)

_REGISTRY = {
    (definition.provider, definition.operation, definition.definition_version): definition
    for definition in REGISTERED_PROVIDER_OPERATIONS
}


def registered_provider_manifest_digest() -> str:
    return stable_digest([definition.manifest for definition in REGISTERED_PROVIDER_OPERATIONS])


def resolve_provider_operation(provider: str, operation: str, definition_version: str) -> ProviderOperationDefinition:
    definition = _REGISTRY.get((provider, operation, definition_version))
    if definition is None:
        raise MkbError(
            "CLEAN_PROVIDER_OPERATION_UNSUPPORTED",
            "Registered API provider operation is not supported",
            409,
            {"provider": provider, "operation": operation, "definition_version": definition_version},
        )
    return definition


def parse_registered_api_member(
    raw: Mapping[str, Any], *, provider: str, operation: str, definition_version: str
) -> MappedProviderMember:
    definition = resolve_provider_operation(provider, operation, definition_version)
    try:
        member = definition.member_model.model_validate(dict(raw))
        return definition.parser(member)
    except (ValidationError, TypeError, ValueError) as exc:
        raise MkbError(
            "CLEAN_MEMBER_SCHEMA_INVALID",
            "Registered API member failed its versioned schema",
            422,
            {
                "rejection_evidence": {
                    "provider": provider,
                    "operation": operation,
                    "definition_version": definition_version,
                    "reason": "member_schema_invalid",
                }
            },
        ) from exc


def unpack_registered_api_envelope(
    envelope: object, *, provider: str, operation: str, definition_version: str
) -> list[dict[str, Any]]:
    definition = resolve_provider_operation(provider, operation, definition_version)
    try:
        validated = definition.envelope_model.model_validate(envelope)
        return [member.model_dump(mode="json", by_alias=True) for member in definition.envelope_unpacker(validated)]
    except (ValidationError, TypeError, ValueError) as exc:
        raise MkbError("CLEAN_ENVELOPE_SCHEMA_INVALID", "Registered API envelope failed its versioned schema", 422) from exc


__all__ = [
    "REGISTERED_PROVIDER_OPERATIONS",
    "ProviderOperationDefinition",
    "parse_registered_api_member",
    "registered_provider_manifest_digest",
    "resolve_provider_operation",
    "unpack_registered_api_envelope",
]
