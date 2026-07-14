from datetime import datetime, timezone
from harness.contracts import AttributionResult, EvidenceBundle, EvidenceItem, Factor
from harness.verify.gate import verify_attribution

def test_gate_rejects_hallucinated_evidence_id():
    e = EvidenceItem(type="social", summary="volume 20%", magnitude=.5, raw_numbers=[20], timestamp=datetime.now(timezone.utc))
    bundle = EvidenceBundle(token_symbol="BTC", window_start=e.timestamp, window_end=e.timestamp, items=[e], signal_type="social")
    attr = AttributionResult(price_event_id="p", contributing_factors=[Factor(evidence_id="invented", attribution_weight=1, label="x")], explanation_text="volume 20.0%")
    result = verify_attribution(attr, bundle)
    assert not result.passed and "Hallucinated" in result.problems[0]

