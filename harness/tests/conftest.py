import json, re
import pytest
from harness.contracts import AttributionResult, Factor, NarrativeClassification
from harness.tools.base import ToolResult

@pytest.fixture
def profile():
    from harness.contracts import UserProfile
    return UserProfile(holdings=[], watchlist=["BTC"], risk_appetite="moderate", time_horizon="swing")

@pytest.fixture
def mocked_pipeline(monkeypatch):
    import harness.nodes.deterministic as det
    import harness.nodes.llm_nodes as llmn
    def tool(source):
        data = {"summary": f"{source} signal 4%", "magnitude": .8, "raw_numbers": [4],
                "price_change_4h_pct": 4 if source == "market" else 0, "timestamp": "2026-01-01T00:00:00Z"}
        return ToolResult(data=data, source_health="ok")
    monkeypatch.setattr(det, "fetch_social_mentions", lambda token: tool("social"))
    monkeypatch.setattr(det, "fetch_exchange_flow", lambda token: tool("onchain"))
    monkeypatch.setattr(det, "fetch_market_data", lambda token: tool("market"))
    def fake(prompt, schema, model, **kwargs):
        ids = re.findall(r"\[([0-9a-f-]{36})\]", prompt)
        if schema is NarrativeClassification:
            return schema(narrative_name="momentum", lifecycle_stage="strengthening",
                          supporting_evidence_ids=ids[:1], reasoning="Grounded")
        return AttributionResult(price_event_id="p1", contributing_factors=[Factor(
            evidence_id=ids[0], attribution_weight=1.0, label="signal")], explanation_text="Observed 4% move")
    monkeypatch.setattr(llmn, "llm_structured", fake)

