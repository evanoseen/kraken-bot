"""Cycle orchestrator — the bot's main trading logic.

`run_trading_cycle` is the entry point called every `RUN_INTERVAL_MINUTES`:
kill switch and balance/drawdown gates, exit checks on held positions
(stop-loss/take-profit/max-age), the three signal sources (listing, pump,
news) merged and deduplicated, every risk gate (blacklist, cooldown,
per-coin cap, max open positions), confidence-scaled position sizing
(`size_position`, Day 62), then order placement — real or dry-run. Full
stage-by-stage detail lives in STRATEGY.md; this module is where every
guardrail from the daily-iteration backlog actually gets wired together.
"""
from __future__ import annotations

from datetime import datetime, timezone
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
from signals import deduplicate
from kill_switch import kill_switch_active
from notifier import notify_trade
from positions import record_buy, remove_position, get_position, log_trade, update_peak_price
from blacklist import is_blacklisted
from coin_trade_counter import at_cap as coin_at_cap, increment as coin_increment
from trade_logger import append_trade as csv_log
from status import write_status
from headline_cache import filter_new as filter_new_headlines, mark_seen as mark_headlines_seen
from retry import with_retry
from portfolio import compute_value as portfolio_value
from cycle_timer import timed

logger = logging.getLogger(__name__)

_starting_balance: Optional[float] = None
_peak_balance: Optional[float] = None
_trades_today: int = 0
_wins: int = 0
_losses: int = 0
_balance_alert_sent: bool = False


def check_exit_conditions(client: krakenex.API, holdings: dict[str, float]) -> None:
    """Check all held coins for stop-loss or take-profit triggers."""
    global _wins, _losses
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

        # Stale position exit (Day 31)
        timestamp = position.get("timestamp")
        if timestamp:
            try:
                entered_at = datetime.fromisoformat(timestamp).replace(tzinfo=timezone.utc)
                age_hours = (datetime.now(timezone.utc) - entered_at).total_seconds() / 3600
                if age_hours >= cfg.max_position_age_hours:
                    logger.warning(
                        f"STALE POSITION: {coin} held {age_hours:.1f}h "
                        f"(limit {cfg.max_position_age_hours:.0f}h) | P&L: ${pnl:.2f} CAD — force selling"
                    )
                    if not cfg.dry_run:
                        result = place_order(client, coin, "sell", current_value, price)
                        if result:
                            log_trade(coin, "sell_stale", price, current_value, pnl)
                            csv_log(coin, "sell_stale", current_value, price, pnl=pnl)
                            remove_position(coin)
                            notify_trade("sell_stale", coin, current_value, price, pnl=pnl)
                            mark_traded(coin)
                            if pnl >= 0:
                                _wins += 1
                            else:
                                _losses += 1
                    else:
                        logger.info(f"[DRY RUN] Would force-sell stale {coin} | P&L: ${pnl:.2f}")
                    continue
            except ValueError:
                pass

        # Minimum hold time guard (Day 44): skip stop-loss/take-profit until
        # the position has been held long enough. Stale exits bypass this.
        if cfg.min_hold_minutes > 0 and timestamp:
            try:
                entered_at = datetime.fromisoformat(timestamp).replace(tzinfo=timezone.utc)
                age_minutes = (datetime.now(timezone.utc) - entered_at).total_seconds() / 60
                if age_minutes < cfg.min_hold_minutes:
                    logger.info(
                        f"Skipping exit for {coin} — held {age_minutes:.1f}m "
                        f"(min {cfg.min_hold_minutes:.0f}m)"
                    )
                    continue
            except ValueError:
                pass

        # Trailing stop (Day 69): tracks the highest price seen since entry
        # and exits if price falls TRAILING_STOP_PCT off that peak. Disabled
        # by default (TRAILING_STOP_PCT unset). Only evaluated once the peak
        # has actually moved above entry — a position that never ran up
        # falls through to the ordinary entry-price stop-loss below instead
        # of double-triggering off a peak that equals its entry price.
        if cfg.trailing_stop_pct is not None:
            peak_price = max(position.get("peak_price", entry_price), price)
            if peak_price != position.get("peak_price"):
                update_peak_price(coin, peak_price)

            if peak_price > entry_price:
                drop_from_peak = (peak_price - price) / peak_price
                if drop_from_peak >= cfg.trailing_stop_pct:
                    logger.warning(
                        f"TRAILING STOP triggered: {coin} | "
                        f"peak ${peak_price:.8f} → now ${price:.8f} "
                        f"(-{drop_from_peak*100:.1f}% off peak) | P&L: ${pnl:.2f} CAD"
                    )
                    if not cfg.dry_run:
                        result = place_order(client, coin, "sell", current_value, price)
                        if result:
                            log_trade(coin, "sell_trailingstop", price, current_value, pnl)
                            csv_log(coin, "sell_trailingstop", current_value, price, pnl=pnl)
                            remove_position(coin)
                            notify_trade("sell_trailingstop", coin, current_value, price, pnl=pnl)
                            mark_traded(coin)
                            if pnl >= 0:
                                _wins += 1
                            else:
                                _losses += 1
                            logger.info(f"Trailing stop executed for {coin} | P&L: ${pnl:.2f}")
                    else:
                        logger.info(f"[DRY RUN] Would trailing-stop sell {coin} | P&L: ${pnl:.2f}")
                    continue

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
                    csv_log(coin, "sell_stoploss", current_value, price, pnl=pnl)
                    remove_position(coin)
                    notify_trade("sell_stoploss", coin, current_value, price, pnl=pnl)
                    mark_traded(coin)
                    _losses += 1
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
                    csv_log(coin, "sell_takeprofit", current_value, price, pnl=pnl)
                    remove_position(coin)
                    notify_trade("sell_takeprofit", coin, current_value, price, pnl=pnl)
                    mark_traded(coin)
                    _wins += 1
                    logger.info(f"Take-profit executed for {coin} | Profit: +${pnl:.2f} CAD")
            else:
                logger.info(f"[DRY RUN] Would take-profit sell {coin} | P&L: +${pnl:.2f}")


def size_position(confidence: float, min_confidence: float, min_trade_amount: float, max_trade_amount: float) -> float:
    """Linearly scale trade size between MIN_TRADE_AMOUNT and MAX_TRADE_AMOUNT
    based on signal confidence (Day 62).

    Confidence maps over [min_confidence, 1.0] — the only range that reaches
    this function, since signals below min_confidence are already filtered
    out upstream. A signal right at the confidence floor sizes the minimum
    trade; a maximum-confidence (1.0) signal sizes the maximum. Formula and
    rationale documented in STRATEGY.md's "Position sizing" section.
    """
    span = 1.0 - min_confidence
    if span <= 0:
        return max_trade_amount
    t = (confidence - min_confidence) / span
    t = max(0.0, min(1.0, t))  # clamp defensively against out-of-range confidence
    return min_trade_amount + t * (max_trade_amount - min_trade_amount)


@timed
def run_trading_cycle() -> None:
    global _starting_balance, _peak_balance, _trades_today, _wins, _losses, _balance_alert_sent

    # Kill switch (Day 24): `touch KILL` halts trading instantly without SSH.
    # Checked before any network call so a killed cycle does nothing at all.
    if kill_switch_active():
        logger.warning("KILL switch active — halting cycle, no trades will be placed. Remove the KILL file to resume.")
        return

    logger.info("=" * 50)
    if cfg.dry_run:
        logger.info("DRY RUN MODE — no real orders will be placed")
    logger.info("Starting trading cycle...")
    total_closed = _wins + _losses
    if total_closed:
        win_rate = _wins / total_closed * 100
        logger.info(f"Session W/L: {_wins}W/{_losses}L ({win_rate:.0f}%)")

    client = get_client()

    # Cancel any open orders that may be holding funds
    open_orders = client.query_private("OpenOrders")
    if not open_orders.get("error"):
        orders = open_orders.get("result", {}).get("open", {})
        if orders:
            logger.info(f"Cancelling {len(orders)} open order(s) to free funds")
            for txid in orders:
                client.query_private("CancelOrder", {"txid": txid})

    balance = with_retry(get_balance, client, max_attempts=3, base_delay=1.0)
    logger.info(f"Balance: ${balance:.2f} CAD")

    if _starting_balance is None:
        _starting_balance = balance
        logger.info(f"Starting balance: ${_starting_balance:.2f}")

    _peak_balance = max(_peak_balance or balance, balance)

    daily_loss = _starting_balance - balance
    if daily_loss >= cfg.daily_loss_limit:
        logger.warning(f"Daily loss limit hit (${daily_loss:.2f} lost). Stopping for today.")
        return

    # Profit target halt (Day 40): lock in gains once session profit hits the target.
    session_profit = balance - _starting_balance
    if cfg.profit_target and session_profit >= cfg.profit_target:
        logger.info(
            f"PROFIT TARGET reached: +${session_profit:.2f} CAD this session "
            f"(target ${cfg.profit_target:.2f}). Halting to lock in gains."
        )
        return

    drawdown = (_peak_balance - balance) / _peak_balance if _peak_balance else 0.0
    if drawdown >= cfg.max_drawdown_pct:
        logger.warning(
            f"Drawdown circuit breaker triggered: "
            f"${balance:.2f} is {drawdown*100:.1f}% below peak ${_peak_balance:.2f}. "
            f"Stopping for today."
        )
        return

    if _trades_today >= cfg.max_trades_per_day:
        logger.warning(
            f"Daily trade cap reached ({_trades_today}/{cfg.max_trades_per_day}). "
            f"No new trades until restart."
        )
        return

    if cfg.balance_alert_threshold and balance < cfg.balance_alert_threshold and not _balance_alert_sent:
        logger.warning(f"LOW BALANCE: ${balance:.2f} CAD is below alert threshold ${cfg.balance_alert_threshold:.2f}")
        notify_trade("balance_alert", "WALLET", balance, 1.0)
        _balance_alert_sent = True

    if balance < 5:
        logger.warning("Insufficient balance. Skipping.")
        return

    # Balance reserve guard (Day 43): funds above the reserve are the only
    # funds available to trade. Stop if tradeable funds are too low.
    available = balance - cfg.min_balance_reserve
    if available < 5:
        logger.warning(
            f"Available balance ${available:.2f} CAD (after ${cfg.min_balance_reserve:.2f} reserve) "
            f"is below minimum. Skipping."
        )
        return

    # Get all tradable coins + current holdings
    available_coins = get_tradable_coins(client)
    holdings = get_holdings(client)
    logger.info(f"Tracking {len(available_coins)} coins | Holding: {list(holdings.keys()) or 'nothing'}")

    # Portfolio value (Day 49): cash + open positions at current market prices
    total_value = portfolio_value(client, holdings, balance)
    if holdings:
        logger.info(f"Portfolio value: ${total_value:.2f} CAD (cash ${balance:.2f} + positions ${total_value - balance:.2f})")

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

    # Fetch news signals — skip Claude if all headlines already analyzed (Day 47)
    articles = fetch_top_headlines()
    new_articles = filter_new_headlines(articles)
    logger.info(f"Fetched {len(articles)} headlines ({len(new_articles)} new)")
    if not new_articles:
        logger.info("All headlines seen this session — skipping Claude analysis.")
        news_signals = []
    else:
        mark_headlines_seen(new_articles)
        headlines = format_headlines_for_prompt(new_articles)
        news_signals = analyze_news_for_trades(headlines, available_coins)

    # Combine and deduplicate — same coin from pump + news becomes one trade
    raw_signals = pump_signals + news_signals
    signals = deduplicate(raw_signals)
    dupes = len(raw_signals) - len(signals)
    logger.info(
        f"Found {len(signals)} signal(s) after dedup "
        f"({len(pump_signals)} pump + {len(news_signals)} news"
        + (f", {dupes} merged)" if dupes else ")")
    )

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

        # Skip blacklisted coins (Day 39)
        if is_blacklisted(coin):
            logger.info(f"Skipping {action.upper()} {coin} — blacklisted")
            continue

        # Skip coins that hit the per-coin trade cap (Day 41)
        if coin_at_cap(coin, cfg.max_trades_per_coin):
            logger.info(
                f"Skipping {action.upper()} {coin} — per-coin cap reached "
                f"({cfg.max_trades_per_coin} trades this session)"
            )
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

        trade_amount = min(
            size_position(confidence, cfg.min_confidence, cfg.min_trade_amount, cfg.max_trade_amount),
            available * 0.25,
        )

        # Trade size floor (Day 46): skip orders too small for the exchange to accept.
        if trade_amount < cfg.min_trade_amount:
            logger.info(
                f"Skipping {action.upper()} {coin} — trade size ${trade_amount:.2f} "
                f"is below minimum ${cfg.min_trade_amount:.2f}"
            )
            continue

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
                    csv_log(coin, "buy_signal", trade_amount, price, confidence=confidence)
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
                    csv_log(coin, "sell_signal", trade_amount, price, confidence=confidence, pnl=pnl)
                    notify_trade("sell_signal", coin, trade_amount, price, confidence=confidence, pnl=pnl)
                    mark_traded(coin)
                    if pnl is not None:
                        if pnl >= 0:
                            _wins += 1
                        else:
                            _losses += 1
                _trades_today += 1
                coin_increment(coin)
                logger.info(f"Trade successful for {coin}! ({_trades_today}/{cfg.max_trades_per_day} today)")
        else:
            logger.info(f"  [DRY RUN] Set DRY_RUN=false in .env to go live.")

    logger.info("Trading cycle complete.")
    logger.info("=" * 50)

    holdings_now = get_holdings(client)
    final_value = portfolio_value(client, holdings_now, balance)
    write_status(
        balance=balance,
        open_positions=len(holdings_now),
        trades_today=_trades_today,
        wins=_wins,
        losses=_losses,
        starting_balance=_starting_balance,
        portfolio_value=final_value,
    )
