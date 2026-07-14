from harness.graph import app
from harness.obs.tracing import LOGGER

def test_tracing_emits_span_per_executed_node(mocked_pipeline, profile):
    LOGGER.clear()
    app.invoke({"token_symbol":"BTC", "user_profile":profile})
    names = {s["name"] for s in LOGGER.spans}
    expected = {"ingest_social","ingest_onchain","ingest_market","signal_detection","narrative",
                "attribution","confidence","verify","personalize","format_output"}
    assert expected <= names
    assert all("trace_id" in span and "latency_ms" in span for span in LOGGER.spans)

