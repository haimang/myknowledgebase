"""NHX1-T01/T30 skeleton: fake success evidence is rejected."""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

from tests.nhx1_evidence import EvidenceCommand, execute, verify

ROOT = Path(__file__).resolve().parents[2]


def _command(source: str, *, observed_layer: str = "L1") -> EvidenceCommand:
    return EvidenceCommand(
        test_id="NHX1-T01",
        argv=(sys.executable, "-c", source),
        work_items=("P1-04",),
        truth_ids=("T-O-408",),
        profile="test/sqlite",
        observed_layer=observed_layer,
        minimum_layer="L1",
    )


def test_real_command_record_round_trips() -> None:
    record = execute(_command("print('1 check passed')"), repository_root=ROOT)
    verify(record, expected_commit=str(record["commit"]))


@pytest.mark.parametrize("source", ["print('PASS')", "print('1 skipped')", "print('1 xfailed')"])
def test_fake_pass_is_rejected(source: str) -> None:
    with pytest.raises(ValueError, match="success-shaped|degraded"):
        execute(_command(source), repository_root=ROOT)


def test_fake_sha_digest_and_layer_are_rejected() -> None:
    record = execute(_command("print('1 check passed')"), repository_root=ROOT)
    fake = copy.deepcopy(record)
    fake["commit"] = "0" * 40
    with pytest.raises(ValueError, match="commit"):
        verify(fake, expected_commit=str(record["commit"]))
    fake = copy.deepcopy(record)
    fake["stdout_digest"] = "0" * 64
    with pytest.raises(ValueError, match="stdout digest"):
        verify(fake, expected_commit=str(record["commit"]))
    with pytest.raises(ValueError, match="minimum layer"):
        execute(_command("print('1 check passed')", observed_layer="contract"), repository_root=ROOT)
