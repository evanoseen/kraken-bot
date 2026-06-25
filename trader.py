from __future__ import annotations

from typing import Optional

import krakenex
import logging
from kraken_client import get_client, get_balance, get_holdings, get_tradable_coins, get_price, place_order
from news_fetcher import fetch_top_headlines, format_headlines_for_prompt
from market_matcher import analyze_news_for_trades
from pump_detector import find_pumping_coins
from listing_monitor import check_new_listings
from config import cfg
from cooldown import is_on_cooldown, mark_traded
from kill_switch import kill_switch_active
from notifier import notify_trade
from positions import record_buy, remove_position, get_position, log_trade

logger = logging.getLogger(__name__)

_starting_balance: Optional[float] = None
_peak_balance: Optional[float] = None


def check_exit_conditions(client: krakenex.API, holdings: dict[str, float]) -> None:
    """Check all held coins for stop-loss or take-profit triggers."""
    for coin, amount in holdings.items():
        position = get_position(coin)
        if not position:
            continue

        price = get_price(client, coin)
        if not price:
            continue

        entry_price = position["entry_price"]
        amount_cad = position["amount_cad"]
        pct_change = (price - entry_price) / entry_price
        current_value = amount * price
        pnl = current_value - amount_cad

        if pct_change <= -cfg.stop_loss_pct:
            logger.warning(
                f"STOP-LOSS triggered: {coin} | "
                f"entry ${entry_price:.8f} → now ${price:.8f} "
                f"({pct_change*100:.1f}%) | P&L: ${pnl:.2f} CAD"
            )
            if not cfg.dry_run:
                result = place_order(client, coin, "sell", current_value, price)
                if result:
                    log_trade(coin, "sell_stoploss", price, current_value, pnl)
                    remove_position(coin)
                    notify_trade("sell_stoploss", coin, current_value, price, pnl=pnl)
                    mark_traded(coin)
                    logger.info(f"Stop-loss executed for {coin}")
            else:
                logger.info(f"[DRY RUN] Would stop-loss sell {coin} | P&L: ${pnl:.2f}")

        elif pct_change >= cfg.take_profit_pct:
            logger.info(
                f"TAKE-PROFIT triggered: {coin} | "
                f"entry ${entry_price:.8f} → now ${price:.8f} "
                f"(+{pct_change*100:.1f}%) | P&L: +${pnl:.2f} CAD"
            )
            if not cfg.dry_run:
                result = place_order(client, coin, "sell", current_value, price)
                if result:
                    log_trade(coin, "sell_takeprofit", price, current_value, pnl)
                    remove_position(coin)
                    notify_trade("sell_takeprofit", coin, current_value, price, pnl=pnl)
                    mark_traded(coin)
                    logger.info(f"Take-profit executed for {coin} | Profit: +${pnl:.2f} CAD")
            else:
                logger.info(f"[DRY RUN] Would take-profit sell {coin} | P&L: +${pnl:.2f}")


def run_trading_cycle() -> None:
    global _starting_balance, _peak_balance

    # Kill switch (Day 24): `touch KILL` halts trading instantly without SSH.
    # Checked before any network call so a killed cycle does nothing at all.
    if kill_switch_active():
        logger.warning("KILL switch active — halting cycle, no trades will be placed. Remove the KILL file to resume.")
        return

    logger.info("=" * 50)
    if cfg.dry_run:
        logger.info("DRY RUN MODE — no real orders will be placed")
    logger.info("Starting trading cycle...")

    client = get_client()

    # Cancel any open orders that may be holding funds
    open_orders = client.query_private("OpenOrders")
    if not open_orders.get("error"):
        orders = open_orders.get("result", {}).get("open", {})
        if orders:
            logger.info(f"Cancelling {len(orders)} open order(s) to free funds")
            for txid in orders:
                client.query_private("CancelOrder", {"txid": txid})

    balance = get_balance(client)
    logger.info(f"Balance: ${balance:.2f} CAD")

    if _starting_balance is None:
        _starting_balance = balance
        logger.info(f"Starting balance: ${_starting_balance:.2f}")

    _peak_balance = max(_peak_balance or balance, balance)

    daily_loss = _starting_balance - balance
    if daily_loss >= cfg.daily_loss_limit:
        logger.warning(f"Daily loss limit hit (${daily_loss:.2f} lost). Stopping for today.")
        return

    drawdown = (_peak_balance - balance) / _peak_balance if _peak_balance else 0.0
    if drawdown >= cfg.max_drawdown_pct:
        logger.warning(
            f"Drawdown circuit breaker triggered: "
            f"${balance:.2f} is {drawdown*100:.1f}% below peak ${_peak_balance:.2f}. "
            f"Stopping for today."
        )
        return

    if balance < 5:
        logger.warning("Insufficient balance. Skipping.")
        return

    # Get all tradable coins + current holdings
    available_coins = get_tradable_coins(client)
    holdings = get_holdings(client)
    logger.info(f"Tracking {len(available_coins)} coins | Holding: {list(holdings.keys()) or 'nothing'}")

    # Check stop-loss / take-profit on all held positions
    if holdings:
        check_exit_conditions(client, holdings)
        holdings = get_holdings(client)
        balance = get_balance(client)
        logger.info(f"Balance after exit checks: ${balance:.2f} CAD")

    # Check for new Kraken listings — buy immediately on listing day
    new_listings = check_new_listings()
    for coin in new_listings:
        logger.info(f"NEW LISTING BUY: {coin} — buying immediately!")
        price = get_price(client, coin)
        if price:
            trade_amount = min(cfg.max_trade_amount, balance * 0.3)
            if not cfg.dry_run:
                result = place_order(client, coin, "buy", trade_amount, price)
                if result:
                    record_buy(coin, price, trade_amount)
                    log_trade(coin, "buy_newlisting", price, trade_amount)

    # Detect pumping unknown coins
    pump_signals = []
    pumping = find_pumping_coins(client, min_volume_multiplier=3.0)
    for p in pumping:
        pump_signals.append({
            "coin": p["coin"],
            "action": "buy",
            "confidence": min(0.65 + (p["volume_spike"] / 50), 0.95),
            "reasoning": (
                f"Volume spike {p['volume_spike']}x normal with "
                f"+{p['price_change_24h']}% price move — early pump detected"
            ),
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
        logger.info("Trading cycle complete.")
        logger.info("=" * 50)
        return

    for signal in signals:
        coin = signal["coin"].upper()
        action = signal["action"].lower()
        confidence = signal["confidence"]

        # Skip sells on coins we don't hold
        if action == "sell" and coin not in holdings:
            logger.info(f"Skipping SELL {coin} — not held")
            continue

        # Skip coins still within the post-trade cooldown window
        if is_on_cooldown(coin, cfg.trade_cooldown_minutes):
            logger.info(f"Skipping {action.upper()} {coin} — cooldown active ({cfg.trade_cooldown_minutes:.0f}m)")
            continue

        # Skip buys when at the position limit
        if action == "buy" and len(holdings) >= cfg.max_open_positions:
            logger.info(
                f"Skipping BUY {coin} — at max open positions "
                f"({cfg.max_open_positions}): {list(holdings.keys())}"
            )
            continue

        price = get_price(client, coin)
        if not price:
            logger.warning(f"Could not get price for {coin}")
            continue

        trade_amount = min(cfg.max_trade_amount * confidence, balance * 0.25)

        logger.info(
            f"{'[DRY RUN] ' if cfg.dry_run else ''}Signal: {action.upper()} "
            f"${trade_amount:.2f} of {coin} @ ${price:.8f} "
            f"| Confidence: {confidence:.2f}"
        )
        logger.info(f"  Reason: {signal['reasoning']}")

        if not cfg.dry_run:
            result = place_order(client, coin, action, trade_amount, price)
            if result:
                if action == "buy":
                    record_buy(coin, price, trade_amount)
                    log_trade(coin, "buy_signal", price, trade_amount)
                    notify_trade("buy_signal", coin, trade_amount, price, confidence=confidence)
                    mark_traded(coin)
                else:
                    position = get_position(coin)
                    pnl = None
                    if position:
                        current_value = holdings.get(coin, 0) * price
                        pnl = current_value - position["amount_cad"]
                        remove_position(coin)
                    log_trade(coin, "sell_signal", price, trade_amount, pnl)
                    notify_trade("sell_signal", coin, trade_amount, price, confidence=confidence, pnl=pnl)
                    mark_traded(coin)
                logger.info(f"Trade successful for {coin}!")
        else:
            logger.info(f"  [DRY RUN] Set DRY_RUN=false in .env to go live.")

    logger.info("Trading cycle complete.")
    logger.info("=" * 50)
