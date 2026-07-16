import json, os, urllib.parse, urllib.request
from datetime import datetime, timezone
from .base import tool_harness

# Etherscan has no ticker-to-contract lookup, so common mainnet ERC-20s are mapped by hand.
# ETH itself has no ERC-20 contract (it's the chain's native coin) -- handled separately below.
KNOWN_CONTRACTS = {
    "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec",
    "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    "WBTC": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
    "LINK": "0x514910771AF9Ca656af840dff83E8264EcF986CA",
    "UNI": "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984",
    "DAI": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
    "SHIB": "0x95aD61b0a150d79219dCF64E1E6Cc01f0B64C4cE",
    "AAVE": "0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9",
    "MATIC": "0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0",
}


def _eth_native_flow(endpoint: str, key: str) -> dict:
    # ETH is the native coin (no ERC-20 contract), so action=tokentx doesn't apply. The latest
    # block's full transaction list is used instead, as a proxy for recent network-wide ETH
    # transfer activity -- Etherscan has no "all ETH transfers" endpoint independent of a block.
    params = {"chainid": "1", "module": "proxy", "action": "eth_getBlockByNumber", "tag": "latest",
              "boolean": "true", "apikey": key}
    url = endpoint + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=15) as response:
        raw = json.loads(response.read().decode())

    block = raw.get("result")
    if not isinstance(block, dict):
        raise ValueError(f"Etherscan proxy call failed: {block!r}")
    txs = block.get("transactions") or []
    if not txs:
        raise ValueError("Etherscan returned no transactions in latest block")
    amounts = [int(tx.get("value", "0x0"), 16) / 1e18 for tx in txs]
    total = sum(amounts)
    block_ts = int(block.get("timestamp", "0x0"), 16)
    return {
        "token": "ETH",
        "summary": f"{len(txs)} ETH transfers in latest block, total ~{total:,.2f} ETH",
        "magnitude": max(0.0, min(1.0, len(txs) / 150)),
        "raw_numbers": [total, float(len(txs))],
        "timestamp": datetime.fromtimestamp(block_ts, tz=timezone.utc).isoformat(),
    }


@tool_harness(cache_ttl=30)
def fetch_exchange_flow(token: str) -> dict:
    # Etherscan V1 (bare /api) is deprecated; V2 requires chainid= and is keyed as a query param.
    # This is Ethereum-only (no BTC/other chains).
    endpoint, key = os.environ["ONCHAIN_API_ENDPOINT"], os.environ["ONCHAIN_API_KEY"]
    symbol = token.upper()
    if symbol == "ETH":
        return _eth_native_flow(endpoint, key)

    # If the caller already passed a raw contract address (0x...), use it as-is; otherwise
    # resolve the ticker through the known-contracts table.
    contract = token if token.lower().startswith("0x") else KNOWN_CONTRACTS.get(symbol)
    if not contract:
        raise ValueError(f"No known ERC-20 contract address for token {symbol!r}")

    params = {"chainid": "1", "module": "account", "action": "tokentx", "contractaddress": contract,
              "page": "1", "offset": "20", "sort": "desc", "apikey": key}
    url = endpoint + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=15) as response:
        raw = json.loads(response.read().decode())

    txs = raw.get("result")
    if raw.get("status") != "1" or not isinstance(txs, list) or not txs:
        raise ValueError(f"Etherscan returned no transfers: {raw.get('result')}")
    # NOTE: this is raw transfer *activity*, not exchange-labeled flow -- Etherscan doesn't
    # tag which addresses are exchanges, so "in/out of exchanges" isn't distinguishable here.
    amounts = [int(tx["value"]) / (10 ** int(tx.get("tokenDecimal", 18))) for tx in txs]
    total = sum(amounts)
    result_symbol = txs[0].get("tokenSymbol", symbol)
    return {
        "token": result_symbol,
        "summary": f"{len(txs)} recent {result_symbol} transfers, total ~{total:,.2f} {result_symbol}",
        "magnitude": max(0.0, min(1.0, len(txs) / 20)),
        "raw_numbers": [total, float(len(txs))],
        "timestamp": datetime.fromtimestamp(int(txs[0]["timeStamp"]), tz=timezone.utc).isoformat(),
    }
