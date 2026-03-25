import logging
from kraken_client import get_client, get_balance, get_holdings, get_tradable_coins, get_price, place_order
from news_fetcher import fetch_top_headlines, format_headlines_for_prompt
from market_matcher import analyze_news_for_trades
from pump_detector import find_pumping_coins
from listing_monitor import check_new_listings
from config import MAX_TRADE_AMOUNT, DAILY_LOSS_LIMIT, DRY_RUN

logger = logging.getLogger(__name__)

_starting_balance = None


def run_trading_cycle():
    global _starting_balance

    logger.info("=" * 50)
    if DRY_RUN:
        logger.info("DRY RUN MODE — no real orders will be placed")
    logger.info("Starting trading cycle...")

    client = get_client()

    balance = get_balance(client)
    logger.info(f"Balance: ${balance:.2f} CAD")

    if _starting_balance is None:
        _starting_balance = balance
        logger.info(f"Starting balance: ${_starting_balance:.2f}")

    daily_loss = _starting_balance - balance
    if daily_loss >= DAILY_LOSS_LIMIT:
        logger.warning(f"Daily loss limit hit (${daily_loss:.2f} lost). Stopping for today.")
        return

    if balance < 5:
        logger.warning("Insufficient balance. Skipping.")
        return

    # Get all tradable coins + current holdings
    available_coins = get_tradable_coins(client)
    holdings = get_holdings(client)
    logger.info(f"Tracking {len(available_coins)} coins | Holding: {list(holdings.keys()) or 'nothing'}")

    # Check for new Kraken listings — buy immediately on listing day
    new_listings = check_new_listings()
    for coin in new_listings:
        logger.info(f"NEW LISTING BUY: {coin} — buying immediately!")
        price = get_price(client, coin)
        if price and not DRY_RUN:
            place_order(client, coin, "buy", min(MAX_TRADE_AMOUNT, balance * 0.3), price)

    # Detect pumping unknown coins
    pump_signals = []
    pumping = find_pumping_coins(client, min_volume_multiplier=3.0)
    for p in pumping:
        pump_signals.append({
            "coin": p["coin"],
            "action": "buy",
            "confidence": min(0.65 + (p["volume_spike"] / 50), 0.95),
            "reasoning": f"Volume spike {p['volume_spike']}x normal with +{p['price_change_24h']}% price move — early pump detected"
        })

    # Fetch news signals
    articles = fetch_top_headlines()
    headlines = format_headlines_for_prompt(articles)
    logger.info(f"Fetched {len(articles)} headlines")
    news_signals = analyze_news_for_trades(headlines, available_coins)

    # Combine both signal sources
    signals = pump_signals + news_signals
    logger.info(f"Found {len(signals)} total signal(s) ({len(pump_signals)} pump + {len(news_signals)} news)")

    if not signals:
        logger.info("No confident signals. No trades placed.")
        return

    for signal in signals:
        coin = signal["coin"].upper()
        action = signal["action"].lower()
        confidence = signal["confidence"]

        # Skip sells on coins we don't hold
        if action == "sell" and coin not in holdings:
            logger.info(f"Skipping SELL {coin} — not held")
            continue

        price = get_price(client, coin)
        if not price:
            logger.warning(f"Could not get price for {coin}")
            continue

        trade_amount = min(MAX_TRADE_AMOUNT * confidence, balance * 0.25)

        logger.info(f"{'[DRY RUN] ' if DRY_RUN else ''}Signal: {action.upper()} ${trade_amount:.2f} of {coin} @ ${price:.8f}")
        logger.info(f"  Reason: {signal['reasoning']} | Confidence: {confidence}")

        if not DRY_RUN:
            result = place_order(client, coin, action, trade_amount, price)
            if result:
                logger.info(f"Trade successful for {coin}!")
        else:
            logger.info(f"  [DRY RUN] Set DRY_RUN=false in .env to go live.")

    logger.info("Trading cycle complete.")
    logger.info("=" * 50)
