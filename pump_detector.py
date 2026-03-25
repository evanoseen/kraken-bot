import logging

logger = logging.getLogger(__name__)

# Hot coins to always monitor — research-backed priority list
PRIORITY_COINS = {"PEPE", "BONK", "TRUMP", "DOGE", "SHIB"}

# Ignore stable/major coins
IGNORE_COINS = {
    "BTC", "ETH", "XRP", "SOL", "ADA", "DOT", "MATIC", "LINK", "LTC",
    "BCH", "XLM", "ATOM", "UNI", "AAVE", "ALGO", "VET", "FIL", "TRX",
    "AVAX", "NEAR", "APT", "ARB", "OP", "USD", "CAD",
    "EUR", "USDT", "USDC", "DAI", "BUSD"
}


def find_pumping_coins(client, min_volume_multiplier: float = 3.0, top_n: int = 5) -> list:
    """
    Find coins with unusual volume spikes — potential early pumps.
    Returns list of {coin, price, volume_24h, volume_change, pair}
    """
    resp = client.query_public("Ticker")
    if resp.get("error"):
        logger.error(f"Ticker error: {resp['error']}")
        return []

    # Get all pairs
    pairs_resp = client.query_public("AssetPairs")
    if pairs_resp.get("error"):
        return []

    # Build reverse map: pair_name -> (base_coin, quote)
    pair_info = {}
    for pair_name, info in pairs_resp.get("result", {}).items():
        base = info.get("base", "").lstrip("X").lstrip("Z")
        quote = info.get("quote", "")
        if quote in ("ZCAD", "ZUSD", "CAD", "USD"):
            pair_info[pair_name] = {"coin": base, "quote": quote}

    candidates = []

    for pair_name, ticker in resp.get("result", {}).items():
        if pair_name not in pair_info:
            continue

        coin = pair_info[pair_name]["coin"].upper()

        if coin in IGNORE_COINS:
            continue

        try:
            volume_today = float(ticker["v"][0])    # volume today
            volume_24h = float(ticker["v"][1])      # volume last 24h
            price = float(ticker["c"][0])           # last price
            low_24h = float(ticker["l"][1])
            high_24h = float(ticker["h"][1])

            if volume_24h <= 0 or price <= 0:
                continue

            # Volume spike ratio
            if volume_today > 0 and volume_24h > 0:
                spike_ratio = volume_today / (volume_24h / 24) if volume_24h > 0 else 0
            else:
                continue

            # Price move in 24h
            price_change_pct = ((price - low_24h) / low_24h * 100) if low_24h > 0 else 0

            if spike_ratio >= min_volume_multiplier:
                candidates.append({
                    "coin": coin,
                    "pair": pair_name,
                    "price": price,
                    "volume_spike": round(spike_ratio, 1),
                    "price_change_24h": round(price_change_pct, 1),
                })

        except (ValueError, KeyError, ZeroDivisionError):
            continue

    # Always add priority coins with baseline confidence
    for pair_name, ticker in resp.get("result", {}).items():
        if pair_name not in pair_info:
            continue
        coin = pair_info[pair_name]["coin"].upper()
        if coin in PRIORITY_COINS and coin not in {c["coin"] for c in candidates}:
            try:
                price = float(ticker["c"][0])
                volume_24h = float(ticker["v"][1])
                low_24h = float(ticker["l"][1])
                price_change_pct = ((price - low_24h) / low_24h * 100) if low_24h > 0 else 0
                if price > 0 and price_change_pct > 2:  # Only add if moving up
                    candidates.append({
                        "coin": coin,
                        "pair": pair_name,
                        "price": price,
                        "volume_spike": 1.0,
                        "price_change_24h": round(price_change_pct, 1),
                        "priority": True,
                    })
            except (ValueError, KeyError):
                continue

    # Sort by volume spike — biggest pumps first
    candidates.sort(key=lambda x: x["volume_spike"], reverse=True)

    if candidates:
        logger.info(f"Found {len(candidates)} pumping coins:")
        for c in candidates[:top_n]:
            logger.info(f"  {c['coin']} — {c['volume_spike']}x volume spike | +{c['price_change_24h']}% price | ${c['price']:.8f}")

    return candidates[:top_n]
