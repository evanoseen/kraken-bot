import logging

logger = logging.getLogger(__name__)

# Ignore majors and stablecoins only — everything else is fair game
IGNORE_COINS = {
    "BTC", "ETH", "XRP", "SOL", "ADA", "DOT", "MATIC", "LINK", "LTC",
    "BCH", "XLM", "ATOM", "UNI", "AAVE", "ALGO", "VET", "FIL", "TRX",
    "AVAX", "NEAR", "APT", "ARB", "OP", "USD", "CAD",
    "EUR", "USDT", "USDC", "DAI", "BUSD",
    # Known high-cap memes — skip these, hunt unknown ones
    "DOGE", "SHIB", "PEPE", "BONK", "TRUMP",
}


def find_pumping_coins(client, min_volume_multiplier: float = 2.0, top_n: int = 5) -> list:
    """
    Hunt obscure low-activity coins that suddenly spike in volume.
    Ignores majors AND popular memes — focuses on unknown coins nobody is talking about.
    """
    resp = client.query_public("Ticker")
    if resp.get("error"):
        logger.error(f"Ticker error: {resp['error']}")
        return []

    pairs_resp = client.query_public("AssetPairs")
    if pairs_resp.get("error"):
        return []

    # Build reverse map: pair_name -> coin
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
            volume_today = float(ticker["v"][0])   # volume so far today
            volume_24h = float(ticker["v"][1])     # volume last 24h
            price = float(ticker["c"][0])          # last price
            low_24h = float(ticker["l"][1])
            high_24h = float(ticker["h"][1])
            trades_today = int(ticker["t"][0])     # number of trades today

            if volume_24h <= 0 or price <= 0:
                continue

            # Skip coins that are already high volume (already discovered)
            # Focus on coins with normally LOW volume that suddenly spike
            avg_daily_volume_usd = volume_24h * price
            if avg_daily_volume_usd > 5_000_000:  # skip anything doing >$5M/day normally
                continue

            # Volume spike ratio — today vs average hourly rate
            avg_hourly = volume_24h / 24
            if avg_hourly <= 0:
                continue
            spike_ratio = volume_today / avg_hourly

            # Price move off the low
            price_change_pct = ((price - low_24h) / low_24h * 100) if low_24h > 0 else 0

            # Must have both volume spike AND price moving up
            if spike_ratio >= min_volume_multiplier and price_change_pct > 1.0:
                candidates.append({
                    "coin": coin,
                    "pair": pair_name,
                    "price": price,
                    "volume_spike": round(spike_ratio, 1),
                    "price_change_24h": round(price_change_pct, 1),
                    "daily_volume_usd": round(avg_daily_volume_usd, 0),
                    "trades_today": trades_today,
                })

        except (ValueError, KeyError, ZeroDivisionError):
            continue

    # Sort by volume spike — biggest unknown pumps first
    candidates.sort(key=lambda x: x["volume_spike"], reverse=True)

    if candidates:
        logger.info(f"Found {len(candidates)} obscure pumping coins:")
        for c in candidates[:top_n]:
            logger.info(
                f"  {c['coin']} — {c['volume_spike']}x spike | "
                f"+{c['price_change_24h']}% price | "
                f"${c['price']:.8f} | "
                f"daily vol ${c['daily_volume_usd']:,.0f}"
            )
    else:
        logger.info("No obscure pump signals found this cycle.")

    return candidates[:top_n]
