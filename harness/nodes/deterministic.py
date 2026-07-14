from datetime import datetime, timezone
from harness.contracts import AttributionResult, EvidenceBundle, EvidenceItem, FeedItem
from harness.tools import fetch_exchange_flow, fetch_market_data, fetch_social_mentions

def _raw(source, result):
    return {"source": source, "data": result.data, "source_health": result.source_health}

def ingest_social_node(state):
    if state.get("raw_data"): return {"raw_data": []}
    return {"raw_data": [_raw("social", fetch_social_mentions(state["token_symbol"]))]}

def ingest_onchain_node(state):
    if state.get("raw_data"): return {"raw_data": []}
    return {"raw_data": [_raw("onchain", fetch_exchange_flow(state["token_symbol"]))]}

def ingest_market_node(state):
    if state.get("raw_data"): return {"raw_data": []}
    return {"raw_data": [_raw("market", fetch_market_data(state["token_symbol"]))]}

def get_from(raw_data, source):
    return next((x for x in raw_data if x.get("source") == source), {"source": source, "data": {}, "source_health": "down"})

def _timestamp(data):
    value = data.get("timestamp")
    if value:
        try: return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError: pass
    return datetime.now(timezone.utc)

def _evidence_from_raw(raw_data):
    items = []
    for row in raw_data:
        data, source = row.get("data", {}), row.get("source")
        if not data or row.get("source_health") == "down": continue
        # market is handled exclusively via build_price_signal below (threshold-gated) —
        # also including it here duplicated near-identical evidence and confused the LLM's
        # single evidence_id-per-factor schema.
        if source == "market": continue
        if source == "social": etype = "social"
        elif source == "onchain": etype = "exchange_flow"
        else: etype = "funding_rate"
        summary = str(data.get("summary") or f"{source} signal for {data.get('token', 'token')}")
        nums = data.get("raw_numbers", [])
        magnitude = max(0.0, min(1.0, float(data.get("magnitude", 0.5))))
        items.append(EvidenceItem(type=etype, summary=summary, magnitude=magnitude,
                                  raw_numbers=nums, timestamp=_timestamp(data), source_url=data.get("source_url")))
    return items

def build_price_signal(market):
    data = market.get("data", market)
    change = float(data.get("price_change_4h_pct", 0))
    return EvidenceItem(type="funding_rate", summary=f"Price changed {change}% over 4h",
                        magnitude=min(1.0, abs(change) / 10), raw_numbers=[change], timestamp=_timestamp(data))

def aggregate_evidence(evidence, signals, token_symbol="UNKNOWN"):
    items = list(evidence) + list(signals)
    now = max((e.timestamp for e in items), default=datetime.now(timezone.utc))
    start = min((e.timestamp for e in items), default=now)
    return EvidenceBundle(token_symbol=token_symbol, window_start=start, window_end=now,
                          items=items, signal_type="price_move" if signals else "mixed")

def signal_detection_node(state):
    generated = _evidence_from_raw(state.get("raw_data", []))
    market = get_from(state.get("raw_data", []), "market")
    signals = []
    if abs(float(market.get("data", {}).get("price_change_4h_pct", 0))) >= 3.0:
        signals.append(build_price_signal(market))
    return {"bundle": aggregate_evidence(state.get("evidence", []) + generated, signals, state["token_symbol"])}

def confidence_node(state):
    base = sum(e.magnitude for e in state["bundle"].items) / max(1, len(state["bundle"].items))
    health = [r.get("source_health", "down") for r in state.get("raw_data", [])]
    factor = sum({"ok": 1.0, "degraded": 0.7, "down": 0.4}.get(h, 0.4) for h in health) / max(1, len(health))
    return {"confidence": round(max(0.0, min(1.0, base * factor)), 4)}

def personalize_node(state):
    profile = state["user_profile"]
    token = state["token_symbol"]
    held = any(h.token.upper() == token.upper() for h in profile.holdings)
    watched = token.upper() in {x.upper() for x in profile.watchlist}
    relevance = "Held asset" if held else "Watchlist asset" if watched else f"Matches {profile.risk_appetite} risk profile"
    return {"personal_relevance": relevance}

def format_output_node(state):
    narrative = state.get("narrative")
    item = FeedItem(token_symbol=state["token_symbol"],
                    narrative=narrative.narrative_name if narrative else "unclassified",
                    attribution=state["attribution"], confidence=state.get("confidence") or 0.0,
                    personal_relevance=state.get("personal_relevance", "Degraded output"))
    return {"feed_items": [item]}
