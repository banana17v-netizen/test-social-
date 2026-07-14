import json, os, urllib.parse, urllib.request
from datetime import datetime, timezone
from .base import tool_harness

@tool_harness(cache_ttl=30)
def fetch_exchange_flow(token: str) -> dict:
    # Etherscan V1 (bare /api) is deprecated; V2 requires chainid= and is keyed as a query param.
    # IMPORTANT: `token` must be an ERC-20 contract address (0x...), not a ticker symbol —
    # Etherscan has no symbol-to-contract lookup, and this is Ethereum-only (no BTC/other chains).
    endpoint, key = os.environ["ONCHAIN_API_ENDPOINT"], os.environ["ONCHAIN_API_KEY"]
    params = {"chainid": "1", "module": "account", "action": "tokentx", "contractaddress": token,
              "page": "1", "offset": "20", "sort": "desc", "apikey": key}
    url = endpoint + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=15) as response:
        raw = json.loads(response.read().decode())

    txs = raw.get("result")
    if raw.get("status") != "1" or not isinstance(txs, list) or not txs:
        raise ValueError(f"Etherscan returned no transfers: {raw.get('result')}")
    # NOTE: this is raw transfer *activity*, not exchange-labeled flow — Etherscan doesn't
    # tag which addresses are exchanges, so "in/out of exchanges" isn't distinguishable here.
    amounts = [int(tx["value"]) / (10 ** int(tx.get("tokenDecimal", 18))) for tx in txs]
    total = sum(amounts)
    symbol = txs[0].get("tokenSymbol", token)
    return {
        "token": symbol,
        "summary": f"{len(txs)} recent {symbol} transfers, total ~{total:,.2f} {symbol}",
        "magnitude": max(0.0, min(1.0, len(txs) / 20)),
        "raw_numbers": [total, float(len(txs))],
        "timestamp": datetime.fromtimestamp(int(txs[0]["timeStamp"]), tz=timezone.utc).isoformat(),
    }
