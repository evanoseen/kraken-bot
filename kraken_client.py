import krakenex
import logging
from config import KRAKEN_API_KEY, KRAKEN_PRIVATE_KEY

logger = logging.getLogger(__name__)


def get_client():
    k = krakenex.API()
    k.key = KRAKEN_API_KEY
    k.secret = KRAKEN_PRIVATE_KEY
    return k


def get_balance(client) -> float:
    resp = client.query_private("Balance")
    if resp.get("error"):
        logger.error(f"Balance error: {resp['error']}")
        return 0.0
    balances = resp.get("result", {})
    return float(balances.get("ZCAD", balances.get("ZUSD", balances.get("CAD", balances.get("USD", 0)))))


def get_holdings(client) -> dict:
    """Return dict of {symbol: amount} for coins currently held."""
    resp = client.query_private("Balance")
    if resp.get("error"):
        return {}
    balances = resp.get("result", {})
    holdings = {}
    skip = {"ZCAD", "ZUSD", "ZEUR", "CAD", "USD", "EUR"}
    for key, val in balances.items():
        amount = float(val)
        if amount > 0 and key not in skip:
            clean = key.lstrip("X").lstrip("Z") if len(key) > 3 else key
            holdings[clean] = amount
    return holdings


def get_tradable_coins(client) -> list:
    """Fetch all coins tradable in CAD or USD on Kraken."""
    resp = client.query_public("AssetPairs")
    if resp.get("error"):
        logger.error(f"AssetPairs error: {resp['error']}")
        return []

    coins = set()
    for pair_name, pair_info in resp.get("result", {}).items():
        quote = pair_info.get("quote", "")
        base = pair_info.get("base", "")
        if quote in ("ZCAD", "ZUSD", "CAD", "USD"):
            # Clean up the base name
            clean = base.lstrip("X").lstrip("Z") if len(base) > 3 else base
            if clean not in ("CAD", "USD", "EUR", "GBP"):
                coins.add(clean)

    return sorted(list(coins))


def get_pair(client, coin: str) -> str:
    """Find the best trading pair for a coin (prefer CAD, fallback USD)."""
    resp = client.query_public("AssetPairs")
    if resp.get("error"):
        return None

    cad_pair = None
    usd_pair = None

    for pair_name, pair_info in resp.get("result", {}).items():
        base = pair_info.get("base", "").lstrip("X").lstrip("Z")
        quote = pair_info.get("quote", "")
        if base.upper() == coin.upper() or base.upper() == f"X{coin.upper()}":
            if quote in ("ZCAD", "CAD"):
                cad_pair = pair_name
            elif quote in ("ZUSD", "USD") and not cad_pair:
                usd_pair = pair_name

    return cad_pair or usd_pair


def get_price(client, coin: str) -> float:
    """Get current ask price for a coin."""
    pair = get_pair(client, coin)
    if not pair:
        return 0.0
    resp = client.query_public("Ticker", {"pair": pair})
    if resp.get("error"):
        return 0.0
    result = resp.get("result", {})
    for key, val in result.items():
        return float(val["a"][0])
    return 0.0


def place_order(client, coin: str, action: str, amount_cad: float, price: float):
    """Place a market order. action: 'buy' or 'sell'"""
    pair = get_pair(client, coin)
    if not pair:
        logger.error(f"No pair found for {coin}")
        return None

    volume = round(amount_cad / price, 6)
    if volume <= 0:
        logger.warning(f"Volume too small for {coin}")
        return None

    resp = client.query_private("AddOrder", {
        "pair": pair,
        "type": action,
        "ordertype": "market",
        "volume": str(volume),
    })

    if resp.get("error"):
        logger.error(f"Order error for {coin}: {resp['error']}")
        return None

    logger.info(f"Order placed: {action} {volume} {coin} (~${amount_cad:.2f}) | {resp['result']}")
    return resp["result"]
