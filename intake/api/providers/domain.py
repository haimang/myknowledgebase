"""Pure Domain get_agency_listings v1 parser and semantic mapper."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.contracts.common.ids import stable_digest
from src.contracts.intake.providers.domain import DomainEnvelope, DomainParsedMember, DomainRawMember
from src.contracts.intake.semantics import ContextMeta, FilterMeta, MappedProviderMember, semantic_tuples

_AGENCY_NAMES = {
    "12106": "McGrath Box Hill",
    "37576": "Buxton Balwyn Canterbury",
}


def _int(value: object, *, default: int = 0) -> int:
    if value is None:
        return default
    if isinstance(value, bool):
        raise ValueError("Boolean is not a provider identifier")
    return int(value)


def _media(raw: DomainRawMember, kind: str) -> str | None:
    return next((entry.url for entry in raw.media if entry.type == kind and entry.url), None)


def unpack_domain_envelope(envelope: DomainEnvelope) -> list[DomainRawMember]:
    return list(envelope.root)


def parse_domain_member(raw: DomainRawMember) -> MappedProviderMember:
    address = raw.addressParts
    advertiser = raw.advertiserIdentifiers
    price = raw.priceDetails
    geo = raw.geoLocation
    rental = raw.rentalDetails
    property_types = list(raw.propertyTypes)
    advertiser_id = _int(advertiser.advertiserId if advertiser else None)
    parsed = DomainParsedMember(
        id=raw.id,
        advertiser_id=advertiser_id,
        agent_ids=[_int(value) for value in (advertiser.contactIds if advertiser else [])],
        headline=raw.headline,
        description=raw.description,
        property_types=property_types,
        property_type=property_types[0] if property_types else None,
        status=raw.status or "unknown",
        sale_mode=raw.saleMode or "unknown",
        channel=raw.channel or "unknown",
        display_price=price.displayPrice if price else None,
        sale_method=raw.saleMode or (rental.rentalMethod if rental else None),
        bedrooms=raw.bedrooms,
        bathrooms=raw.bathrooms,
        carspaces=raw.carspaces,
        date_listed=raw.dateListed,
        unit_number=address.unitNumber if address else None,
        street_number=address.streetNumber if address else None,
        street=address.street if address else None,
        suburb=address.suburb if address else None,
        postcode=address.postcode if address else None,
        state=address.stateAbbreviation if address else None,
        geo_lat=geo.latitude if geo else None,
        geo_lon=geo.longitude if geo else None,
        photo=_media(raw, "photo"),
        floorplan=_media(raw, "floorplan"),
    )
    agency_id = str(parsed.advertiser_id)
    agency_name = _AGENCY_NAMES.get(agency_id, f"Domain Generic Agency ({agency_id})")
    channel = parsed.property_type or "Unknown"
    filter_meta = FilterMeta(
        realm="realestate_on_market",
        type=parsed.sale_mode,
        channel=channel,
        source_name=agency_name,
        is_active=1,
    )
    tags: list[str] = []
    tags.extend(value for value in (parsed.suburb, parsed.state, parsed.postcode) if value)
    for value, suffix in (
        (parsed.bedrooms, "bedrooms"),
        (parsed.bathrooms, "bathrooms"),
        (parsed.carspaces if parsed.carspaces and parsed.carspaces > 0 else None, "carspaces"),
    ):
        if value is not None:
            tags.append(f"{value} {suffix}")
    if channel != "Unknown":
        tags.append(channel)
    context_meta = ContextMeta(
        realm=filter_meta.realm,
        type=filter_meta.type,
        channel=filter_meta.channel,
        source_name=filter_meta.source_name,
        title=parsed.headline or "No Title Available",
        tags=tags,
    )
    clean_text = "\n\n".join(part.strip() for part in (parsed.headline, parsed.description) if part and part.strip())
    content_facts: Mapping[str, Any] = {
        "headline": parsed.headline,
        "description": parsed.description,
        "features": f"{parsed.bedrooms}-{parsed.bathrooms}",
    }
    meta_facts: Mapping[str, Any] = {
        "price": parsed.display_price,
        "status": parsed.status,
        "sale_mode": parsed.sale_mode,
    }
    return MappedProviderMember(
        provider="domain",
        operation="get_agency_listings",
        definition_version="v1",
        external_key=str(parsed.id),
        clean_text=clean_text,
        parsed_payload=parsed.model_dump(mode="json"),
        content_digest=stable_digest(content_facts),
        meta_digest=stable_digest(meta_facts),
        filter_meta=filter_meta,
        context_meta=context_meta,
        semantic_tuples=semantic_tuples(filter_meta, context_meta),
        identity_evidence={"listing_id": str(parsed.id), "agency_id": agency_id},
    )


__all__ = ["parse_domain_member", "unpack_domain_envelope"]
