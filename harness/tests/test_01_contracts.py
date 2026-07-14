from datetime import datetime, timezone
from harness.contracts import EvidenceBundle, EvidenceItem, UserProfile

def test_schema_validation():
    e = EvidenceItem.model_validate({"type":"social", "summary":"rise", "magnitude":.5,
                                     "timestamp":datetime.now(timezone.utc)})
    b = EvidenceBundle.model_validate({"token_symbol":"BTC", "window_start":e.timestamp,
        "window_end":e.timestamp, "items":[e], "signal_type":"social"})
    p = UserProfile.model_validate({"holdings":[], "watchlist":["BTC"], "risk_appetite":"moderate", "time_horizon":"swing"})
    assert e.evidence_id in b.valid_ids() and p.watchlist == ["BTC"]

