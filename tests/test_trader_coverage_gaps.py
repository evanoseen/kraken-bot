"""Tests for Day 81 — trader.py coverage gaps.

Day 72's original coverage survey flagged trader.py at 82%. Days 77-78
brought pump_detector.py/listing_monitor.py/positions.py above 90%+, and
Day 80 brought kraken_client.py to 100% — this is the last of the four.

Fills: check_exit_conditions' price-missing skip, malformed-timestamp
handling (both the stale-exit and min-hold-time parses), the trailing-stop
losing-exit branch, and the dry-run stop-loss log line; plus
run_trading_cycle's open-orders cancellation, daily-loss-limit halt, live
new-listing buys, pump-signal construction, the sell-not-held and
cooldown-active skips in the main signal loop, and — the single largest
gap — the entire live (non-dry-run) order-placement block, which no
existing test file exercised at all since every full-cycle test in the
suite uses DRY_RUN=true.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import pytest
import trader


@pytest.fixture(autouse=True)
def reset_globals():
    trader._starting_balance = None
    trader._peak_balance = None
    trader._trades_today = 0
    trader._wins = 0
    trader._losses = 0
    trader._balance_alert_sent = False
    yield
    trader._starting_balance = None
    trader._peak_balance = None
    trader._trades_today = 0
    trader._wins = 0
    trader._losses = 0
    trader._balance_alert_sent = False


def _iso(hours_ago: float = 0) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()


# ─── check_exit_conditions ──────────────────────────────────────────────────


@pytest.fixture()
def exit_setup(mocker, monkeypatch, tmp_path):
    monkeypatch.setenv("DRY_RUN", "true")
    monkeypatch.setenv("STOP_LOSS_PCT", "0.10")
    monkeypatch.setenv("TAKE_PROFIT_PCT", "0.25")
    monkeypatch.setenv("MAX_POSITION_AGE_HOURS", "999")
    monkeypatch.chdir(tmp_path)

    import config, importlib
    importlib.reload(config)
    mocker.patch("trader.cfg", config.Config.from_env())

    mocker.patch("trader.place_order", return_value={"txid": "x"})
    mocker.patch("trader.log_trade")
    mocker.patch("trader.remove_position")
    mocker.patch("trader.notify_trade")
    mocker.patch("trader.mark_traded")
    mocker.patch("trader.update_peak_price")
    client = mocker.Mock()
    return mocker, client


def test_price_missing_skips_position(exit_setup):
    mocker, client = exit_setup
    mocker.patch("trader.get_price", return_value=0.0)
    mocker.patch("trader.get_position", return_value={
        "entry_price": 0.05, "amount_cad": 10.0, "timestamp": _iso(1),
    })
    trader.check_exit_conditions(client, {"DOGE": 200.0})
    trader.place_order.assert_not_called()


def test_stale_position_winning_exit_increments_wins(exit_setup, monkeypatch, mocker):
    _, client = exit_setup
    monkeypatch.setenv("DRY_RUN", "false")
    monkeypatch.setenv("MAX_POSITION_AGE_HOURS", "1")
    import config, importlib
    importlib.reload(config)
    mocker.patch("trader.cfg", config.Config.from_env())
    mocker.patch("trader.get_price", return_value=0.10)  # up vs entry -> profit
    mocker.patch("trader.get_position", return_value={
        "entry_price": 0.05, "amount_cad": 10.0, "timestamp": _iso(25),
    })
    trader.check_exit_conditions(client, {"DOGE": 200.0})
    assert trader._wins == 1
    assert trader._losses == 0


def test_malformed_timestamp_falls_through_both_guards(exit_setup, monkeypatch, mocker, caplog):
    """A ValueError from datetime.fromisoformat is caught in both the
    stale-exit check and the min-hold-time check (lines 93-94, 108-109) —
    the position falls through to the ordinary stop-loss/take-profit
    checks as if there were no usable timestamp at all."""
    _, client = exit_setup
    monkeypatch.setenv("MIN_HOLD_MINUTES", "5")
    import config, importlib
    importlib.reload(config)
    mocker.patch("trader.cfg", config.Config.from_env())
    mocker.patch("trader.get_price", return_value=0.05)  # flat -> no stop-loss/take-profit either
    mocker.patch("trader.get_position", return_value={
        "entry_price": 0.05, "amount_cad": 10.0, "timestamp": "not-a-valid-timestamp",
    })
    with caplog.at_level(logging.WARNING, logger="trader"):
        trader.check_exit_conditions(client, {"DOGE": 200.0})
    assert "stale" not in caplog.text.lower()
    assert "Skipping exit" not in caplog.text
    trader.place_order.assert_not_called()  # DRY_RUN=true and flat price -> no trigger anyway


def test_trailing_stop_losing_exit_increments_losses(exit_setup, monkeypatch, mocker):
    _, client = exit_setup
    monkeypatch.setenv("DRY_RUN", "false")
    monkeypatch.setenv("TRAILING_STOP_PCT", "0.05")
    import config, importlib
    importlib.reload(config)
    mocker.patch("trader.cfg", config.Config.from_env())
    # entry=100, peak=110 (ran up), now 95 (net loss vs entry, but also
    # 13.6% off the peak -> well past the 5% trailing-stop threshold).
    mocker.patch("trader.get_price", return_value=95.0)
    mocker.patch("trader.get_position", return_value={
        "entry_price": 100.0, "amount_cad": 100.0, "timestamp": _iso(1),
        "peak_price": 110.0,
    })
    trader.check_exit_conditions(client, {"DOGE": 1.0})
    assert trader._losses == 1
    assert trader._wins == 0


def test_dry_run_stop_loss_logs_message(exit_setup, caplog):
    mocker, client = exit_setup
    mocker.patch("trader.get_price", return_value=0.04)  # -20% off entry -> stop-loss
    mocker.patch("trader.get_position", return_value={
        "entry_price": 0.05, "amount_cad": 10.0, "timestamp": _iso(1),
    })
    with caplog.at_level(logging.INFO, logger="trader"):
        trader.check_exit_conditions(client, {"DOGE": 200.0})
    assert "Would stop-loss sell" in caplog.text
    trader.place_order.assert_not_called()


# ─── run_trading_cycle ───────────────────────────────────────────────────────


@pytest.fixture()
def cycle_setup(mocker, monkeypatch, tmp_path):
    monkeypatch.setenv("DRY_RUN", "true")
    monkeypatch.setenv("DAILY_LOSS_LIMIT", "9999")
    monkeypatch.setenv("MAX_DRAWDOWN_PCT", "0.99")
    monkeypatch.setenv("MAX_TRADES_PER_DAY", "100")
    monkeypatch.setenv("MIN_BALANCE_RESERVE", "0")
    monkeypatch.setenv("MIN_TRADE_AMOUNT", "1.0")
    monkeypatch.setenv("MAX_TRADE_AMOUNT", "25.0")
    monkeypatch.setenv("MIN_CONFIDENCE", "0.80")
    monkeypatch.delenv("BALANCE_ALERT_THRESHOLD", raising=False)
    monkeypatch.delenv("PROFIT_TARGET", raising=False)
    monkeypatch.chdir(tmp_path)

    import config, importlib
    importlib.reload(config)
    mocker.patch("trader.cfg", config.Config.from_env())

    mocker.patch("trader.kill_switch_active", return_value=False)
    mock_client = mocker.patch("trader.get_client").return_value
    mock_client.query_private.return_value = {"result": {"open": {}}}
    mocker.patch("trader.get_balance", return_value=1000.0)
    mocker.patch("trader.get_holdings", return_value={})
    mocker.patch("trader.get_tradable_coins", return_value=["DOGE", "SHIB"])
    mocker.patch("trader.check_new_listings", return_value=[])
    mocker.patch("trader.find_pumping_coins", return_value=[])
    mocker.patch("trader.fetch_top_headlines", return_value=[
        {"title": "test headline (trader coverage)", "url": "http://test/trader-coverage"},
    ])
    mocker.patch("trader.format_headlines_for_prompt", return_value="")
    mocker.patch("trader.analyze_news_for_trades", return_value=[])
    mocker.patch("trader.get_price", return_value=0.10)
    mocker.patch("trader.place_order", return_value={"txid": "x"})
    mocker.patch("trader.log_trade")
    mocker.patch("trader.record_buy")
    mocker.patch("trader.remove_position")
    mocker.patch("trader.get_position", return_value=None)
    mocker.patch("trader.notify_trade")
    mocker.patch("trader.mark_traded")
    mocker.patch("trader.coin_increment")
    return mocker, mock_client


def test_open_orders_are_cancelled(cycle_setup):
    mocker, client = cycle_setup
    client.query_private.side_effect = lambda endpoint, payload=None: (
        {"result": {"open": {"txid-1": {}, "txid-2": {}}}}
        if endpoint == "OpenOrders"
        else {"result": {}}
    )
    trader.run_trading_cycle()

    cancel_calls = [c for c in client.query_private.call_args_list if c.args[0] == "CancelOrder"]
    assert len(cancel_calls) == 2
    cancelled_txids = {c.args[1]["txid"] for c in cancel_calls}
    assert cancelled_txids == {"txid-1", "txid-2"}


def test_daily_loss_limit_halts_cycle(cycle_setup, monkeypatch, mocker, caplog):
    _, client = cycle_setup
    monkeypatch.setenv("DAILY_LOSS_LIMIT", "50")
    import config, importlib
    importlib.reload(config)
    mocker.patch("trader.cfg", config.Config.from_env())

    balance_calls = iter([1000.0, 900.0])  # 100 CAD drop >= 50 limit on the 2nd cycle
    mocker.patch("trader.get_balance", side_effect=lambda *a, **k: next(balance_calls))

    with caplog.at_level(logging.WARNING, logger="trader"):
        trader.run_trading_cycle()  # sets _starting_balance = 1000.0
        trader.run_trading_cycle()  # balance drops to 900.0 -> halts

    assert "Daily loss limit hit" in caplog.text
    trader.get_tradable_coins.assert_called_once()  # only reached on the first (non-halted) cycle


def test_live_new_listing_buy_places_order(cycle_setup, monkeypatch, mocker):
    _, client = cycle_setup
    monkeypatch.setenv("DRY_RUN", "false")
    import config, importlib
    importlib.reload(config)
    mocker.patch("trader.cfg", config.Config.from_env())
    mocker.patch("trader.check_new_listings", return_value=["DOGS"])

    trader.run_trading_cycle()

    trader.place_order.assert_any_call(client, "DOGS", "buy", pytest.approx(25.0), 0.10)
    trader.record_buy.assert_called_once_with("DOGS", 0.10, pytest.approx(25.0))
    trader.log_trade.assert_any_call("DOGS", "buy_newlisting", 0.10, pytest.approx(25.0))


def test_pump_signal_is_built_and_evaluated(cycle_setup, mocker, caplog):
    _, client = cycle_setup
    mocker.patch("trader.find_pumping_coins", return_value=[
        {"coin": "PEPE", "volume_spike": 10.0, "price_change_24h": 5.0},
    ])
    with caplog.at_level(logging.INFO, logger="trader"):
        trader.run_trading_cycle()
    # confidence = min(0.65 + 10/50, 0.95) = 0.85 -> above MIN_CONFIDENCE (0.80),
    # so it survives dedup and gets logged as a real signal, not filtered pre-merge.
    assert "1 pump" in caplog.text


def test_sell_not_held_is_skipped(cycle_setup, caplog):
    mocker, client = cycle_setup
    mocker.patch("trader.analyze_news_for_trades", return_value=[
        {"coin": "DOGE", "action": "sell", "confidence": 0.9, "reasoning": "test"},
    ])
    with caplog.at_level(logging.INFO, logger="trader"):
        trader.run_trading_cycle()
    assert "Skipping SELL DOGE" in caplog.text
    assert "not held" in caplog.text
    trader.place_order.assert_not_called()


def test_cooldown_active_skip(cycle_setup, mocker, caplog):
    mocker.patch("trader.analyze_news_for_trades", return_value=[
        {"coin": "DOGE", "action": "buy", "confidence": 0.9, "reasoning": "test"},
    ])
    mocker.patch("trader.is_on_cooldown", return_value=True)
    with caplog.at_level(logging.INFO, logger="trader"):
        trader.run_trading_cycle()
    assert "cooldown active" in caplog.text
    trader.place_order.assert_not_called()


def test_live_buy_signal_places_order_and_records(cycle_setup, monkeypatch, mocker):
    _, client = cycle_setup
    monkeypatch.setenv("DRY_RUN", "false")
    import config, importlib
    importlib.reload(config)
    mocker.patch("trader.cfg", config.Config.from_env())
    mocker.patch("trader.analyze_news_for_trades", return_value=[
        {"coin": "DOGE", "action": "buy", "confidence": 0.99, "reasoning": "test"},
    ])

    trader.run_trading_cycle()

    trader.place_order.assert_called_once()
    trader.record_buy.assert_called_once()
    # size_position(0.99, min_confidence=0.80, min=1.0, max=25.0): t=(0.99-0.80)/0.20=0.95 -> 1+0.95*24=23.8
    trader.log_trade.assert_any_call("DOGE", "buy_signal", 0.10, pytest.approx(23.8))
    trader.mark_traded.assert_called_once_with("DOGE")
    trader.coin_increment.assert_called_once_with("DOGE")
    assert trader._trades_today == 1


def test_live_sell_signal_places_order_and_records_pnl(cycle_setup, monkeypatch, mocker):
    _, client = cycle_setup
    monkeypatch.setenv("DRY_RUN", "false")
    import config, importlib
    importlib.reload(config)
    mocker.patch("trader.cfg", config.Config.from_env())
    mocker.patch("trader.get_holdings", return_value={"DOGE": 250.0})
    # entry 0.095 vs the flat get_price mock (0.10) is a ~5.3% move — inside
    # both STOP_LOSS_PCT and TAKE_PROFIT_PCT, so check_exit_conditions (which
    # also runs earlier in the same cycle, since holdings is non-empty)
    # doesn't independently trigger its own exit on this same position
    # before the main signal loop's sell-signal path gets to it.
    mocker.patch("trader.get_position", return_value={"entry_price": 0.095, "amount_cad": 20.0})
    mocker.patch("trader.analyze_news_for_trades", return_value=[
        {"coin": "DOGE", "action": "sell", "confidence": 0.99, "reasoning": "test"},
    ])

    trader.run_trading_cycle()

    trader.place_order.assert_called_once()
    trader.remove_position.assert_called_once_with("DOGE")
    # trade_amount = size_position(0.99, ...) = 23.8 (see buy test); current_value
    # for pnl is separately holdings["DOGE"] (250.0) * price (0.10) = 25.0, pnl = 5.0
    trader.log_trade.assert_any_call("DOGE", "sell_signal", 0.10, pytest.approx(23.8), pytest.approx(5.0))
    assert trader._wins == 1
    assert trader._losses == 0


def test_live_sell_signal_losing_pnl_increments_losses(cycle_setup, monkeypatch, mocker):
    _, client = cycle_setup
    monkeypatch.setenv("DRY_RUN", "false")
    import config, importlib
    importlib.reload(config)
    mocker.patch("trader.cfg", config.Config.from_env())
    mocker.patch("trader.get_holdings", return_value={"DOGE": 250.0})
    # entry 0.105 vs the flat 0.10 price mock: a small loss, still inside
    # both exit thresholds so check_exit_conditions doesn't fire its own
    # exit on this position first (same reasoning as the winning-pnl test).
    mocker.patch("trader.get_position", return_value={"entry_price": 0.105, "amount_cad": 30.0})
    mocker.patch("trader.analyze_news_for_trades", return_value=[
        {"coin": "DOGE", "action": "sell", "confidence": 0.99, "reasoning": "test"},
    ])

    trader.run_trading_cycle()

    # current_value = 250.0 * 0.10 = 25.0; pnl = 25.0 - 30.0 = -5.0
    trader.log_trade.assert_any_call("DOGE", "sell_signal", 0.10, pytest.approx(23.8), pytest.approx(-5.0))
    assert trader._losses == 1
    assert trader._wins == 0
