"""D08 REA operation witnesses through the real intake/API entry."""

from __future__ import annotations

from intake.api import clean_registered_api_members
from intake.api.registry import unpack_registered_api_envelope


def test_rea_tiered_results_flatten_and_sold_listing_becomes_inactive() -> None:
    raw = {
        "listingId": "rea-77",
        "_links": {"prettyUrl": {"href": "https://example.test/rea-77"}},
        "channel": "sold",
        "status": {"label": "Sold", "type": "sold_listing"},
        "propertyType": "house",
        "constructionStatus": "established",
        "title": "Sold family residence",
        "description": "Spacious<br>home <strong>near parks</strong>.",
        "mainImage": {"server": "https://img.example.test", "uri": "/cover.jpg"},
        "features": {
            "general": {
                "bedrooms": {"value": 4},
                "bathrooms": {"value": 2},
                "parkingSpaces": {"value": 2},
            }
        },
        "landSize": {"value": 650, "unit": "m2"},
        "price": {"display": "$1,100,000"},
        "statementOfInformation": {"href": "https://example.test/soi.pdf"},
        "advertising": {"region": "eastern_melbourne"},
        "address": {
            "streetAddress": "1 Green Street",
            "postcode": "3133",
            "suburb": "Vermont South",
            "state": "VIC",
            "location": {"latitude": -37.85, "longitude": 145.18},
        },
        "agency": {"name": "Buxton", "agencyId": "37576", "email": "office@example.test"},
        "listers": [{"name": "Agent", "id": "a1", "jobTitle": "Director"}],
    }
    unpacked = unpack_registered_api_envelope(
        {"tieredResults": [{"results": [raw]}]},
        provider="realestate",
        operation="get_listings",
        definition_version="v1",
    )
    member = clean_registered_api_members(
        unpacked, provider="realestate", operation="get_listings", definition_version="v1"
    )[0]

    assert member.external_key == "rea-77"
    assert member.payload["listing_id"] == "rea-77"
    assert member.payload["property_description"] == "Spacious home near parks."
    assert "<" not in member.payload["property_description"]
    assert member.payload["cover_image"] == "https://img.example.test/cover.jpg"
    assert member.filter_meta["realm"] == "realestate"
    assert member.filter_meta["is_active"] == 0
    assert member.context_meta["source_name"] == "Buxton"
