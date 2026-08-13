"""D08 Domain operation witnesses through the real intake/API entry."""

from __future__ import annotations

from intake.api import clean_registered_api_members


def test_domain_fixture_flattens_nested_listing_and_uses_versioned_agency_name() -> None:
    raw = {
        "id": 9001,
        "advertiserIdentifiers": {"advertiserId": 12106, "contactIds": [10, 11]},
        "addressParts": {
            "unitNumber": "2",
            "streetNumber": "42",
            "street": "Main Street",
            "suburb": "Box Hill",
            "postcode": "3128",
            "stateAbbreviation": "VIC",
        },
        "priceDetails": {"displayPrice": "$1,250,000"},
        "geoLocation": {"latitude": -37.8, "longitude": 145.1},
        "headline": "Sunny family home",
        "description": "Three-bedroom home near transport.",
        "propertyTypes": ["House", "Townhouse"],
        "status": "live",
        "saleMode": "buy",
        "channel": "residential",
        "bedrooms": 3,
        "bathrooms": 2,
        "carspaces": 1,
        "dateListed": "2026-08-01",
        "media": [
            {"type": "photo", "url": "https://example.test/photo.jpg"},
            {"type": "floorplan", "url": "https://example.test/floorplan.jpg"},
        ],
    }
    member = clean_registered_api_members(
        [raw], provider="domain", operation="get_agency_listings", definition_version="v1"
    )[0]

    assert member.external_key == "9001"
    assert member.payload["suburb"] == "Box Hill"
    assert member.payload["display_price"] == "$1,250,000"
    assert member.payload["geo_lat"] == -37.8
    assert member.payload["photo"] == "https://example.test/photo.jpg"
    assert member.filter_meta == {
        "realm": "realestate_on_market",
        "type": "buy",
        "channel": "House",
        "source_name": "McGrath Box Hill",
        "is_active": 1,
    }
    assert {"Box Hill", "VIC", "3128", "3 bedrooms", "2 bathrooms", "1 carspaces", "House"} <= set(
        member.context_meta["tags"]
    )
