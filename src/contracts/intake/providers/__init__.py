"""Strict provider operation contracts."""

from src.contracts.intake.providers.chinatax import (
    ChinaTaxEnvelope,
    ChinaTaxGetArticlesRequest,
    ChinaTaxParsedMember,
    ChinaTaxRawMember,
)
from src.contracts.intake.providers.domain import (
    DomainEnvelope,
    DomainGetAgencyListingsRequest,
    DomainParsedMember,
    DomainRawMember,
)
from src.contracts.intake.providers.realestate import (
    RealestateEnvelope,
    RealestateGetListingsRequest,
    RealestateParsedMember,
    RealestateRawMember,
)

__all__ = [
    "ChinaTaxEnvelope",
    "ChinaTaxGetArticlesRequest",
    "ChinaTaxParsedMember",
    "ChinaTaxRawMember",
    "DomainEnvelope",
    "DomainGetAgencyListingsRequest",
    "DomainParsedMember",
    "DomainRawMember",
    "RealestateEnvelope",
    "RealestateGetListingsRequest",
    "RealestateParsedMember",
    "RealestateRawMember",
]
