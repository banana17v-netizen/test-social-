import json, os, urllib.request
from datetime import datetime, timezone
from .base import tool_harness

@tool_harness(cache_ttl=60)
def fetch_social_mentions(token: str, window_h: int = 72) -> dict:
    # LunarCrush v4: symbol goes in the path, not a query string; window is an interval bucket, not raw hours.
    base = os.environ["SOCIAL_API_ENDPOINT"].rstrip("/")
    key = os.environ["SOCIAL_API_KEY"]
    interval = "1d" if window_h <= 24 else "1w" if window_h <= 168 else "1m"
    url = f"{base}/{token.upper()}/time-series/v2?interval={interval}&bucket=hour"
    # Cloudflare blocks urllib's default User-Agent as bot traffic (HTTP 403 / cf error 1010).
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}",
                                               "User-Agent": "Mozilla/5.0 (compatible; harness/0.1)"})
    with urllib.request.urlopen(req, timeout=15) as response:
        raw = json.loads(response.read().decode())

    points = raw.get("data") or []
    if not points:
        raise ValueError("LunarCrush returned no time-series points")
    latest = points[-1]
    galaxy_score = float(latest.get("galaxy_score") or 0)
    social_dominance = float(latest.get("social_dominance") or 0)
    return {
        "token": token.upper(),
        "summary": f"{token.upper()} galaxy score {galaxy_score:.0f}/100, social dominance {social_dominance:.2f}%",
        "magnitude": max(0.0, min(1.0, galaxy_score / 100)),
        "raw_numbers": [galaxy_score, social_dominance],
        "timestamp": datetime.fromtimestamp(latest["time"], tz=timezone.utc).isoformat(),
    }
