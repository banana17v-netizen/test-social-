import json, os, urllib.request
from datetime import datetime, timezone
from .base import tool_harness

@tool_harness(cache_ttl=30)
def fetch_market_data(token: str) -> dict:
    # Binance public klines: no auth needed; symbol is TICKER+USDT, not a bare ticker.
    endpoint = os.environ.get("MARKET_API_ENDPOINT") or "https://api.binance.com/api/v3/klines"
    symbol = f"{token.upper()}USDT"
    url = f"{endpoint}?symbol={symbol}&interval=4h&limit=2"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; harness/0.1)"})
    with urllib.request.urlopen(req, timeout=15) as response:
        klines = json.loads(response.read().decode())  # Binance returns a raw JSON array, not an object

    if not klines:
        raise ValueError(f"Binance returned no klines for {symbol}")
    latest = klines[-1]
    open_price, close_price = float(latest[1]), float(latest[4])
    pct = (close_price - open_price) / open_price * 100 if open_price else 0.0
    direction = "up" if pct >= 0 else "down"
    return {
        "token": token.upper(),
        "summary": f"{symbol} price {direction} {abs(pct):.2f}% over 4h (close {close_price:g})",
        "magnitude": max(0.0, min(1.0, abs(pct) / 10)),
        "raw_numbers": [pct, close_price],
        "price_change_4h_pct": pct,
        "timestamp": datetime.fromtimestamp(latest[6] / 1000, tz=timezone.utc).isoformat(),
    }
