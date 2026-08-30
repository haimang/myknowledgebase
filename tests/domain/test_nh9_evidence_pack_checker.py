"""NH9-T11: nine AP evidence packs are complete, dated, and experiment-isolated."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

_ROOT = Path("docs/evidence/new-harvest")
_APS = [f"AP-NH{n}" for n in range(1, 10)]
_SIX = ("manifest.json", "tests.txt", "queries", "migrations", "security", "closure.md")
_FOUNDATIONAL = ("T-O-376", "T-O-378", "T-O-381", "T-O-383")
_FG = [f"FG-NH-{n:02d}" for n in range(1, 18)]
_TEST_COUNTS = {1: 7, 2: 7, 3: 8, 4: 7, 5: 8, 6: 10, 7: 10, 8: 10, 9: 11}


def _pack(ap: str) -> Path:
    return _ROOT / ap


def test_nine_packs_have_six_artifacts() -> None:
    for ap in _APS:
        pack = _pack(ap)
        assert pack.is_dir(), ap
        for name in _SIX:
            target = pack / name
            assert target.exists(), f"{ap} missing {name}"
            if name in {"queries", "migrations", "security"}:
                assert target.is_dir()
                assert any(target.iterdir()), f"{ap} {name} is empty"
            else:
                assert target.is_file()
                assert target.read_text(encoding="utf-8").strip()


def test_each_test_id_has_four_tuple() -> None:
    sha = re.compile(r"\b[0-9a-f]{7,40}\b")
    utc = re.compile(r"20\d{2}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
    for index, ap in enumerate(_APS, start=1):
        pack = _pack(ap)
        manifest = json.loads((pack / "manifest.json").read_text(encoding="utf-8"))
        tests = (pack / "tests.txt").read_text(encoding="utf-8")
        closure = (pack / "closure.md").read_text(encoding="utf-8")
        test_ids = list(manifest.get("test_ids") or [])
        assert test_ids, ap
        assert len(test_ids) == _TEST_COUNTS[index], (ap, test_ids)
        assert "PASS" in tests
        commit = str(manifest.get("commit") or "")
        observed = str(manifest.get("observed_at_utc") or "")
        assert sha.search(commit), ap
        assert utc.search(observed), ap
        blob = tests + "\n" + closure + "\n" + json.dumps(manifest)
        for test_id in test_ids:
            assert test_id in tests or test_id in closure, f"{ap} {test_id} missing from tests/closure"
            assert test_id in blob
        assert sha.search(blob)
        assert utc.search(blob)
        assert any(token in blob for token in ("T-O-", "Q", "Truth"))


def test_fg_nh_01_to_17_all_green() -> None:
    pack = _pack("AP-NH9")
    listing = (pack / "security" / "fg-nh-01-17.md").read_text(encoding="utf-8")
    tests = (pack / "tests.txt").read_text(encoding="utf-8")
    for fg in _FG:
        assert fg in listing, fg
        assert "PASS" in listing or "green" in listing.lower()
    required_nodes = (
        "test_every_legal_knowledge_cell_namespace_facet_proof",
        "test_w_nh_create_between_identity_and_insert",
        "test_fanin_crash_repairs_via_persistence_port",
        "test_backpressure_zero_downstream",
        "RETRIEVE_SCHEMA_NAMESPACE_REQUIRED",
        "sqlite3",
    )
    evidence = listing + "\n" + tests
    for node in required_nodes:
        assert node in evidence, node
    assert "_browser_fetcher" in listing or "fetcher" in listing.lower()


def test_no_expired_waiver_and_no_foundational_override() -> None:
    now = datetime.now(UTC)
    for ap in _APS:
        security = _pack(ap) / "security"
        for path in security.rglob("*"):
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            lowered = path.name.lower()
            if "waiver" not in lowered and "waiver" not in text.lower():
                continue
            for truth in _FOUNDATIONAL:
                if truth in text:
                    assert "does not override" in text.lower() or "不得覆盖" in text or "no waiver" in text.lower()
            expires = re.findall(r"20\d{2}-\d{2}-\d{2}", text)
            for stamp in expires:
                try:
                    parsed = datetime.fromisoformat(stamp).replace(tzinfo=UTC)
                except ValueError:
                    continue
                if "expire" in text.lower() or "到期" in text:
                    assert parsed >= now, f"{path} expired {stamp}"


def test_experiment_not_in_closure_join() -> None:
    manifest = json.loads(Path("tests/fixtures/new_harvest/closed_set_manifest.v1.json").read_text(encoding="utf-8"))
    experiment = manifest["experiment"]
    assert experiment["launch_date"] is None
    assert experiment["scores"] is None
    assert experiment["in_closure_join"] is False
    schema = Path(".experiment/new-harvest/readiness.schema.json")
    if schema.exists():
        body = json.loads(schema.read_text(encoding="utf-8"))
        assert body.get("launch_date") in {None, ""}
        assert body.get("scores") in {None, {}, []}
        assert body.get("in_closure_join") is False
    for ap in _APS:
        closure = (_pack(ap) / "closure.md").read_text(encoding="utf-8")
        tests = (_pack(ap) / "tests.txt").read_text(encoding="utf-8")
        joined = closure + "\n" + tests
        for forbidden in (".experiment PASS", "0815-R7 PASS", "vendor score PASS"):
            assert forbidden not in joined
        assert "in_closure_join=true" not in joined
        if "0815" in joined or ".experiment" in joined:
            assert "not" in joined.lower() or "不" in joined or "isolated" in joined.lower()
