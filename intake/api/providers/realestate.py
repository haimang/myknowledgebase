"""Pure REA get_listings v1 parser and semantic mapper."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from intake.text import clean_plain_text, extract_html_text
from src.contracts.common.ids import stable_digest
from src.contracts.intake.providers.realestate import (
    RealestateContactAgent,
    RealestateEnvelope,
    RealestateParsedMember,
    RealestateRawMember,
)
from src.contracts.intake.semantics import ContextMeta, FilterMeta, MappedProviderMember, semantic_tuples


def _text(value: object) -> str | None:
    if value is None:
        return None
    result = str(value).strip()
    return result or None


def _description(value: str | None) -> str | None:
    if not value:
        return None
    if "<" in value and ">" in value:
        text, _evidence = extract_html_text(value)
        return text or None
    return clean_plain_text(value) or None


def _feature(raw: RealestateRawMember, name: str) -> int | float | None:
    nested = raw.features.general if raw.features else None
    fallback = raw.generalFeatures
    primary = getattr(nested, name, None) if nested else None
    secondary = getattr(fallback, name, None) if fallback else None
    selected = primary or secondary
    return selected.value if selected else None


def unpack_realestate_envelope(envelope: RealestateEnvelope) -> list[RealestateRawMember]:
    return [member for tier in envelope.tieredResults for member in tier.results]


def parse_realestate_member(raw: RealestateRawMember) -> MappedProviderMember:
    listing_id = str(raw.listingId).strip()
    if not listing_id:
        raise ValueError("REA listing id must not be blank")
    status_type = raw.status.type if raw.status else None
    channel = raw.channel
    inactive = (channel or "").casefold() == "sold" or any(
        marker in (status_type or "").casefold() for marker in ("sold", "withdrawn")
    )
    agents = [
        RealestateContactAgent(
            name=lister.name,
            email=lister.email,
            mobile=lister.mobilePhoneNumber or lister.phoneNumber,
            id=_text(lister.id),
            title=lister.jobTitle,
        )
        for lister in raw.listers
    ]
    address = raw.address
    location = address.location if address else None
    image = raw.mainImage
    cover_image = f"{image.server}{image.uri}" if image and image.server and image.uri else None
    parsed = RealestateParsedMember(
        listing_id=listing_id,
        pretty_url=raw.links.prettyUrl.href if raw.links and raw.links.prettyUrl else None,
        channel=channel,
        status_label=raw.status.label if raw.status else None,
        status_type=status_type,
        property_type=raw.propertyType,
        construction_status=raw.constructionStatus,
        property_title=raw.title,
        property_description=_description(raw.description),
        cover_image=cover_image,
        spec_bed=_feature(raw, "bedrooms"),
        spec_bath=_feature(raw, "bathrooms"),
        spec_car=_feature(raw, "parkingSpaces"),
        spec_land_size=raw.landSize.value if raw.landSize else None,
        spec_land_unit=raw.landSize.unit if raw.landSize else None,
        property_price=raw.price.display if raw.price else None,
        property_soi=raw.statementOfInformation.href if raw.statementOfInformation else None,
        loc_region=raw.advertising.region if raw.advertising else None,
        loc_street=address.streetAddress if address else None,
        loc_postcode=address.postcode if address else None,
        loc_suburb=address.suburb if address else None,
        loc_state=address.state if address else None,
        loc_lat=location.latitude if location else None,
        loc_lon=location.longitude if location else None,
        agency_name=raw.agency.name if raw.agency else None,
        agency_id=_text(raw.agency.agencyId) if raw.agency else None,
        agency_email=raw.agency.email if raw.agency else None,
        contact_agents=agents or None,
        is_active=0 if inactive else 1,
    )
    filter_meta = FilterMeta(
        realm="realestate",
        type="listing",
        channel=parsed.channel or "unknown",
        source_name=parsed.agency_name or "Unknown Agency",
        is_active=parsed.is_active,
    )
    tags: list[str] = []
    if parsed.property_price:
        tags.append(f"Price: {parsed.property_price}")
    for value, label in ((parsed.spec_bed, "Bedroom"), (parsed.spec_bath, "Bathroom"), (parsed.spec_car, "Car")):
        if value is not None:
            tags.append(f"{label}: {value}")
    if parsed.spec_land_size is not None:
        tags.append(f"Land: {parsed.spec_land_size} {parsed.spec_land_unit or ''}".strip())
    if parsed.property_type:
        tags.append(f"Property Type: {parsed.property_type}")
    address_parts = [value for value in (parsed.loc_suburb, parsed.loc_street, parsed.loc_postcode, parsed.loc_state) if value]
    if address_parts:
        tags.append(f"Address: {' | '.join(address_parts)}")
    context_meta = ContextMeta(
        realm=filter_meta.realm,
        type=filter_meta.type,
        channel=filter_meta.channel,
        source_name=filter_meta.source_name,
        title=parsed.property_title or "Untitled Property",
        tags=tags,
    )
    clean_text = "\n\n".join(
        part.strip() for part in (parsed.property_title, parsed.property_description) if part and part.strip()
    )
    content_facts: Mapping[str, Any] = {
        "title": parsed.property_title,
        "description": parsed.property_description,
        "specs": {
            "bed": parsed.spec_bed,
            "bath": parsed.spec_bath,
            "car": parsed.spec_car,
            "land": parsed.spec_land_size,
        },
        "type": parsed.property_type,
    }
    meta_facts: Mapping[str, Any] = {
        "price": parsed.property_price,
        "status": parsed.status_label,
        "active": parsed.is_active,
        "agents": [agent.model_dump(mode="json") for agent in agents],
    }
    return MappedProviderMember(
        provider="realestate",
        operation="get_listings",
        definition_version="v1",
        external_key=listing_id,
        clean_text=clean_text,
        parsed_payload=parsed.model_dump(mode="json"),
        content_digest=stable_digest(content_facts),
        meta_digest=stable_digest(meta_facts),
        filter_meta=filter_meta,
        context_meta=context_meta,
        semantic_tuples=semantic_tuples(filter_meta, context_meta),
        identity_evidence={"listing_id": listing_id},
    )


__all__ = ["parse_realestate_member", "unpack_realestate_envelope"]
