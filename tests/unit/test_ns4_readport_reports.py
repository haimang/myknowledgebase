"""NS4-T24: ReadPort exposes invocation status and stage reports, not extra."""

from __future__ import annotations

from src.services.observability import ObservabilityReadService


def test_generation_evidence_bundle_shape() -> None:
    service = ObservabilityReadService.__new__(ObservabilityReadService)
    bundled = {
        "p1": {
            "invocations": [{"status": "failed", "stage_key": "structurize", "error_code": "X"}],
            "reports": [{"disposition": "rejected", "granularity_set": "0,1"}],
        }
    }
    event = {"process_uuid": "p1", "event_type": "process.status_changed"}
    extra = bundled.get(str(event.get("process_uuid") or ""), {})
    event["generation_invocations"] = extra.get("invocations", [])
    event["generation_stage_reports"] = extra.get("reports", [])
    assert event["generation_invocations"][0]["status"] == "failed"
    assert "structure_reject" not in event
    assert "payload_extra" not in event
