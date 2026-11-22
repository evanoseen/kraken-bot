"""Day 155: ISA.md's new ISC-50 entry claims `portfolio.compute_value()` is
called twice in `trader.run_trading_cycle` -- once mid-cycle for the logged
portfolio-value line, once at cycle end to compute the `portfolio_value`
passed to `status.write_status()`. Locks both halves of that claim against
reality: the call count, derived from trader.py's own source, and the real
end-to-end wiring (a mocked compute_value's return value actually reaches
write_status) -- rather than trusting the new claim at face value the way
Days 126/127/129/134/146/147/150 each found a previously-unlocked ISA claim
had drifted.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
ISA = REPO_ROOT / "ISA.md"
TRADER = REPO_ROOT / "trader.py"


def test_portfolio_value_called_exactly_twice_in_trader_source():
    source = TRADER.read_text()
    # `from portfolio import compute_value as portfolio_value` also contains
    # the text "portfolio_value" once, with no trailing "(" -- count call
    # sites only.
    assert len(re.findall(r"portfolio_value\(", source)) == 2


@pytest.fixture()
def cycle_env(mocker, monkeypatch, tmp_path):
    monkeypatch.setenv("DRY_RUN", "true")
    monkeypatch.setenv("DAILY_LOSS_LIMIT", "9999")
    monkeypatch.setenv("MAX_DRAWDOWN_PCT", "0.99")
    monkeypatch.setenv("MAX_TRADES_PER_DAY", "100")
    monkeypatch.delenv("BALANCE_ALERT_THRESHOLD", raising=False)
    monkeypatch.delenv("PROFIT_TARGET", raising=False)
    monkeypatch.chdir(tmp_path)

    import config
    import importlib
    importlib.reload(config)
    mocker.patch("trader.cfg", config.Config.from_env())

    mocker.patch("trader.kill_switch_active", return_value=False)
    mock_client = mocker.patch("trader.get_client").return_value
    mock_client.query_private.return_value = {"result": {"open": {}}}
    mocker.patch("trader.get_balance", return_value=100.0)
    mocker.patch("trader.get_holdings", return_value={})
    mocker.patch("trader.get_tradable_coins", return_value=["DOGE"])
    mocker.patch("trader.check_new_listings", return_value=[])
    mocker.patch("trader.find_pumping_coins", return_value=[])
    mocker.patch("trader.fetch_top_headlines", return_value=[
        {"title": "test headline (portfolio wiring)", "url": "http://test/portfolio-wiring"},
    ])
    mocker.patch("trader.format_headlines_for_prompt", return_value="")
    mocker.patch("trader.analyze_news_for_trades", return_value=[
        {"coin": "DOGE", "action": "buy", "confidence": 0.9, "reasoning": "test"},
    ])
    return mocker


@pytest.fixture(autouse=True)
def reset_trader_session_state():
    import trader
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


def test_write_status_receives_the_real_portfolio_value_result(cycle_env):
    import trader

    sentinel = 12345.6789
    mock_portfolio_value = cycle_env.patch("trader.portfolio_value", return_value=sentinel)
    mock_write_status = cycle_env.patch("trader.write_status")

    trader.run_trading_cycle()

    assert mock_portfolio_value.call_count == 2
    assert mock_write_status.called
    _, kwargs = mock_write_status.call_args
    assert kwargs["portfolio_value"] == sentinel


def test_isa_isc50_claim_matches_reality():
    isa_text = ISA.read_text()
    isc50_row = re.search(r"^- ISC-50: .*$", isa_text, re.MULTILINE)
    assert isc50_row, "Expected an ISC-50 row in ISA.md's Verification section"
    assert "called twice" in isc50_row.group(0), (
        "ISA.md's ISC-50 row should claim compute_value() is called twice "
        "in trader.run_trading_cycle, matching the real call count"
    )
    assert "status.write_status()" in isc50_row.group(0), (
        "ISA.md's ISC-50 row should name status.write_status() as the "
        "consumer of the second call's return value"
    )
