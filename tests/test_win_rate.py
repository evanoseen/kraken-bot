"""Tests for Day 36 — session win rate tracker."""
from __future__ import annotations

import logging
import pytest
import trader


@pytest.fixture(autouse=True)
def reset_globals():
    trader._starting_balance = None
    trader._peak_balance = None
    trader._trades_today = 0
    trader._wins = 0
    trader._losses = 0
    yield
    trader._starting_balance = None
    trader._peak_balance = None
    trader._trades_today = 0
    trader._wins = 0
    trader._losses = 0


@pytest.fixture()
def patched(mocker, monkeypatch, tmp_path):
    monkeypatch.setenv("DRY_RUN", "true")
    monkeypatch.setenv("DAILY_LOSS_LIMIT", "9999")
    monkeypatch.setenv("MAX_DRAWDOWN_PCT", "0.99")
    monkeypatch.setenv("MAX_TRADES_PER_DAY", "100")
    monkeypatch.chdir(tmp_path)

    import config, importlib
    importlib.reload(config)
    mocker.patch("trader.cfg", config.Config.from_env())

    mocker.patch("trader.kill_switch_active", return_value=False)
    mock_client = mocker.patch("trader.get_client").return_value
    mock_client.query_private.return_value = {"result": {"open": {}}}
    mocker.patch("trader.get_balance", return_value=100.0)
    mocker.patch("trader.get_holdings", return_value={})
    mocker.patch("trader.get_tradable_coins", return_value=[])
    mocker.patch("trader.check_new_listings", return_value=[])
    mocker.patch("trader.find_pumping_coins", return_value=[])
    mocker.patch("trader.fetch_top_headlines", return_value=[])
    mocker.patch("trader.format_headlines_for_prompt", return_value="")
    mocker.patch("trader.analyze_news_for_trades", return_value=[])
    return mocker


def test_no_win_rate_logged_on_first_cycle(patched, caplog):
    with caplog.at_level(logging.INFO, logger="trader"):
        trader.run_trading_cycle()
    assert "W/L" not in caplog.text


def test_win_rate_logged_after_wins_set(patched, caplog):
    trader._wins = 3
    trader._losses = 1
    with caplog.at_level(logging.INFO, logger="trader"):
        trader.run_trading_cycle()
    assert "3W/1L" in caplog.text
    assert "75%" in caplog.text


def test_zero_wins_shows_0_percent(patched, caplog):
    trader._wins = 0
    trader._losses = 2
    with caplog.at_level(logging.INFO, logger="trader"):
        trader.run_trading_cycle()
    assert "0W/2L" in caplog.text
    assert "0%" in caplog.text


def test_stop_loss_increments_losses(mocker, monkeypatch, tmp_path):
    from datetime import datetime, timezone
    monkeypatch.setenv("DRY_RUN", "false")
    monkeypatch.chdir(tmp_path)
    import config, importlib
    importlib.reload(config)
    mocker.patch("trader.cfg", config.Config.from_env())
    mocker.patch("trader.get_price", return_value=0.03)
    mocker.patch("trader.place_order", return_value={"txid": "x"})
    mocker.patch("trader.log_trade")
    mocker.patch("trader.remove_position")
    mocker.patch("trader.notify_trade")
    mocker.patch("trader.mark_traded")
    mocker.patch("trader.get_position", return_value={
        "entry_price": 0.05, "amount_cad": 10.0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    trader.check_exit_conditions(mocker.Mock(), {"DOGE": 200.0})
    assert trader._losses == 1
    assert trader._wins == 0


def test_take_profit_increments_wins(mocker, monkeypatch, tmp_path):
    from datetime import datetime, timezone
    monkeypatch.setenv("DRY_RUN", "false")
    monkeypatch.chdir(tmp_path)
    import config, importlib
    importlib.reload(config)
    mocker.patch("trader.cfg", config.Config.from_env())
    mocker.patch("trader.get_price", return_value=0.08)
    mocker.patch("trader.place_order", return_value={"txid": "x"})
    mocker.patch("trader.log_trade")
    mocker.patch("trader.remove_position")
    mocker.patch("trader.notify_trade")
    mocker.patch("trader.mark_traded")
    mocker.patch("trader.get_position", return_value={
        "entry_price": 0.05, "amount_cad": 10.0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    trader.check_exit_conditions(mocker.Mock(), {"DOGE": 200.0})
    assert trader._wins == 1
    assert trader._losses == 0
