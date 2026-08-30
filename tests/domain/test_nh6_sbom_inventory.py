"""NH6-T10: implementation pins are complete without becoming owner Truth."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

from src.runtime.supply.identities import SUPPLY_IDENTITIES

_MANIFEST = Path("docs/evidence/new-harvest/AP-NH6/security/sbom-inventory.json")


def _inventory() -> dict[str, object]:
    return json.loads(_MANIFEST.read_text(encoding="utf-8"))


def test_every_binary_has_pin_license_sbom_cve_or_waiver() -> None:
    manifest = _inventory()
    assert manifest["schema_version"] == "mkb.nh6-runtime-sbom.v1"
    assert manifest["repository_license"] == "Proprietary"
    records = manifest["capabilities"]
    assert isinstance(records, list)
    by_capability = {record["capability_key"]: record for record in records}
    assert set(by_capability) == {item.capability_key for item in SUPPLY_IDENTITIES}
    assert {record["readiness_key"] for record in records} == {item.readiness_key for item in SUPPLY_IDENTITIES}
    for record in records:
        assert record["identity"]
        assert record["pins"]
        assert record["license"]["spdx"]
        assert record["sbom"]["format"]
        assert record["cve_baseline"]["reviewed_at"]
        assert record["cve_baseline"]["references"]
        assert record["upgrade"] and record["rollback"] and record["isolation"]
        for pin in record["pins"]:
            assert pin["component"] and pin["version"] and pin["purl"]
            observed = pin.get("observed_path")
            expected = pin.get("sha256")
            if observed and expected:
                assert hashlib.sha256(Path(observed).read_bytes()).hexdigest() == expected
    lowered = json.dumps(manifest).casefold()
    assert '"latest"' not in lowered and ":latest" not in lowered
    copyleft = [record for record in records if any(token in record["license"]["spdx"] for token in ("GPL-", "AGPL-"))]
    assert copyleft
    assert all(record["license"]["linked_into_main_process"] is False for record in copyleft)

    packages = subprocess.run(
        ("dpkg-query", "-W", "-f=${Package} ${Version}\\n", "poppler-utils", "python3.12"),
        capture_output=True,
        check=True,
        text=True,
    ).stdout
    assert "poppler-utils 24.02.0-1ubuntu9.9" in packages
    assert "python3.12 3.12.3-1ubuntu0.16" in packages


def test_waiver_requires_owner_name() -> None:
    records = _inventory()["capabilities"]
    for record in records:
        waiver = record["owner_waiver"]
        if waiver is None:
            continue
        assert all(waiver.get(key) for key in ("owner_name", "truth_impact", "expires_at", "reopen_condition"))
        assert waiver["truth_impact"] not in {"T-O-376", "T-O-378", "T-O-399"}


def test_no_library_name_frozen_as_truth() -> None:
    manifest = _inventory()
    assert manifest["truth_status"] == "implementation_pin_only"
    for identity in SUPPLY_IDENTITIES:
        serialized = identity.model_dump_json().casefold()
        assert not re.search(r"playwright|chromium|pypdf|tesseract|poppler|firefox", serialized)
    plan = Path("docs/plan/new-harvest/AP-NH6-local-runtime-supply-and-security.md").read_text(encoding="utf-8")
    assert "库名 **不** 进 Truth" in plan
