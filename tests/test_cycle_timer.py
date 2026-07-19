"""Tests for Day 50 — cycle timing decorator."""
from __future__ import annotations

import logging
import time
import pytest
from unittest.mock import patch
from cycle_timer import timed


def test_return_value_preserved():
    @timed
    def fn():
        return 42

    assert fn() == 42


def test_args_forwarded():
    @timed
    def add(a, b):
        return a + b

    assert add(3, 4) == 7


def test_function_name_preserved():
    @timed
    def my_func():
        pass

    assert my_func.__name__ == "my_func"


def test_elapsed_logged(caplog):
    @timed
    def fast():
        pass

    with caplog.at_level(logging.INFO, logger="cycle_timer"):
        fast()

    assert "cycle duration" in caplog.text.lower()


def test_elapsed_logged_on_exception(caplog):
    @timed
    def explodes():
        raise ValueError("boom")

    with caplog.at_level(logging.INFO, logger="cycle_timer"):
        with pytest.raises(ValueError):
            explodes()

    assert "cycle duration" in caplog.text.lower()


def test_exception_still_propagates():
    @timed
    def fails():
        raise RuntimeError("oops")

    with pytest.raises(RuntimeError, match="oops"):
        fails()


def test_timing_is_non_negative():
    durations = []

    def fake_monotonic():
        val = fake_monotonic._calls
        fake_monotonic._calls += 0.5
        return val

    fake_monotonic._calls = 0.0

    @timed
    def work():
        pass

    with patch("cycle_timer.time.monotonic", side_effect=fake_monotonic):
        with patch("cycle_timer.logger") as mock_log:
            work()

    args = mock_log.info.call_args[0]
    elapsed = args[1]
    assert elapsed >= 0


def test_multiple_calls_each_logged(caplog):
    @timed
    def step():
        pass

    with caplog.at_level(logging.INFO, logger="cycle_timer"):
        step()
        step()
        step()

    assert caplog.text.lower().count("cycle duration") == 3
