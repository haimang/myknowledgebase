"""REA get_listings v1 request, envelope, and member schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from src.contracts.common.models import StrictModel


class RealestateFilters(StrictModel):
    suburbs: list[str] = Field(default_factory=list, max_length=100)
    states: list[str] = Field(default_factory=list, max_length=16)
    property_types: list[str] = Field(default_factory=list, max_length=32)
    min_bedrooms: int | None = Field(default=None, ge=0)
    min_bathrooms: int | None = Field(default=None, ge=0)
    min_price: int | None = Field(default=None, ge=0)
    max_price: int | None = Field(default=None, ge=0)


class RealestateGetListingsRequest(StrictModel):
    channel: Literal["buy", "rent", "sold"]
    page: int = Field(default=1, ge=1)
    pageSize: int = Field(default=50, ge=1, le=200)
    filters: RealestateFilters | None = None


class ReaLink(StrictModel):
    href: str | None = None


class ReaLinks(StrictModel):
    prettyUrl: ReaLink | None = None


class ReaStatus(StrictModel):
    label: str | None = None
    type: str | None = None


class ReaFeatureValue(StrictModel):
    value: int | float | None = None


class ReaGeneralFeatures(StrictModel):
    bedrooms: ReaFeatureValue | None = None
    bathrooms: ReaFeatureValue | None = None
    parkingSpaces: ReaFeatureValue | None = None


class ReaFeatures(StrictModel):
    general: ReaGeneralFeatures | None = None


class ReaImage(StrictModel):
    server: str | None = None
    uri: str | None = None


class ReaLandSize(StrictModel):
    value: int | float | None = None
    unit: str | None = None


class ReaPrice(StrictModel):
    display: str | None = None


class ReaAdvertising(StrictModel):
    region: str | None = None


class ReaLocation(StrictModel):
    latitude: int | float | None = None
    longitude: int | float | None = None


class ReaAddress(StrictModel):
    streetAddress: str | None = None
    postcode: str | None = None
    suburb: str | None = None
    state: str | None = None
    location: ReaLocation | None = None


class ReaAgency(StrictModel):
    name: str | None = None
    agencyId: str | int | None = None
    email: str | None = None


class ReaLister(StrictModel):
    name: str | None = None
    email: str | None = None
    mobilePhoneNumber: str | None = None
    phoneNumber: str | None = None
    id: str | int | None = None
    jobTitle: str | None = None


class RealestateRawMember(StrictModel):
    listingId: str | int
    links: ReaLinks | None = Field(default=None, alias="_links")
    channel: str | None = None
    status: ReaStatus | None = None
    propertyType: str | None = None
    constructionStatus: str | None = None
    title: str | None = None
    description: str | None = None
    mainImage: ReaImage | None = None
    features: ReaFeatures | None = None
    generalFeatures: ReaGeneralFeatures | None = None
    landSize: ReaLandSize | None = None
    price: ReaPrice | None = None
    statementOfInformation: ReaLink | None = None
    advertising: ReaAdvertising | None = None
    address: ReaAddress | None = None
    agency: ReaAgency | None = None
    listers: list[ReaLister] = Field(default_factory=list)


class RealestateTier(StrictModel):
    results: list[RealestateRawMember] = Field(default_factory=list)


class RealestateEnvelope(StrictModel):
    tieredResults: list[RealestateTier] = Field(default_factory=list)


class RealestateContactAgent(StrictModel):
    name: str | None
    email: str | None
    mobile: str | None
    id: str | None
    title: str | None


class RealestateParsedMember(StrictModel):
    listing_id: str = Field(min_length=1)
    pretty_url: str | None
    channel: str | None
    status_label: str | None
    status_type: str | None
    property_type: str | None
    construction_status: str | None
    property_title: str | None
    property_description: str | None
    cover_image: str | None
    spec_bed: int | float | None = None
    spec_bath: int | float | None = None
    spec_car: int | float | None = None
    spec_land_size: int | float | None = None
    spec_land_unit: str | None = None
    property_price: str | None
    property_soi: str | None
    loc_region: str | None
    loc_street: str | None
    loc_postcode: str | None
    loc_suburb: str | None
    loc_state: str | None
    loc_lat: int | float | None
    loc_lon: int | float | None
    agency_name: str | None
    agency_id: str | None
    agency_email: str | None
    contact_agents: list[RealestateContactAgent] | None
    is_active: Literal[0, 1]


__all__ = ["RealestateEnvelope", "RealestateGetListingsRequest", "RealestateParsedMember", "RealestateRawMember"]
