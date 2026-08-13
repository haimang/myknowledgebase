"""Domain get_agency_listings v1 request, envelope, and member schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, RootModel

from src.contracts.common.models import StrictModel


class DomainGetAgencyListingsRequest(StrictModel):
    agencyId: int = Field(gt=0)
    listingStatusFilter: Literal["live", "archived", "new", "sold", "leased", "pending", "depositTaken"] = "live"
    pageNumber: int = Field(default=1, ge=1)
    pageSize: int = Field(default=200, ge=1, le=200)


class DomainAddressParts(StrictModel):
    unitNumber: str | None = None
    streetNumber: str | None = None
    street: str | None = None
    suburb: str | None = None
    postcode: str | None = None
    stateAbbreviation: str | None = None


class DomainAdvertiserIdentifiers(StrictModel):
    advertiserId: int | str | None = None
    contactIds: list[int | str] = Field(default_factory=list)


class DomainPriceDetails(StrictModel):
    displayPrice: str | None = None


class DomainGeoLocation(StrictModel):
    latitude: int | float | None = None
    longitude: int | float | None = None


class DomainRentalDetails(StrictModel):
    rentalMethod: str | None = None


class DomainMedia(StrictModel):
    type: str
    url: str | None = None


class DomainRawMember(StrictModel):
    id: int
    addressParts: DomainAddressParts | None = None
    advertiserIdentifiers: DomainAdvertiserIdentifiers | None = None
    priceDetails: DomainPriceDetails | None = None
    geoLocation: DomainGeoLocation | None = None
    headline: str | None = None
    description: str | None = None
    propertyTypes: list[str] = Field(default_factory=list)
    status: str | None = None
    saleMode: str | None = None
    channel: str | None = None
    rentalDetails: DomainRentalDetails | None = None
    bedrooms: int | float | None = None
    bathrooms: int | float | None = None
    carspaces: int | float | None = None
    dateListed: str | None = None
    media: list[DomainMedia] = Field(default_factory=list)


class DomainEnvelope(RootModel[list[DomainRawMember]]):
    pass


class DomainParsedMember(StrictModel):
    id: int = Field(gt=0)
    advertiser_id: int
    agent_ids: list[int]
    headline: str | None
    description: str | None
    property_types: list[str]
    property_type: str | None
    status: str
    sale_mode: str
    channel: str
    display_price: str | None
    sale_method: str | None
    bedrooms: int | float | None
    bathrooms: int | float | None
    carspaces: int | float | None
    date_listed: str | None
    unit_number: str | None
    street_number: str | None
    street: str | None
    suburb: str | None
    postcode: str | None
    state: str | None
    geo_lat: int | float | None
    geo_lon: int | float | None
    photo: str | None
    floorplan: str | None


__all__ = ["DomainEnvelope", "DomainGetAgencyListingsRequest", "DomainParsedMember", "DomainRawMember"]
