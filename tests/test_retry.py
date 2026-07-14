"""Tests for Day 48 — exponential backoff retry utility."""
from __future__ import annotations

import logging
import pytest
from unittest.mock import MagicMock, call, patch
from retry import with_retry, retryable


def test_success_on_first_attempt():
    fn = MagicMock(return_value=42)
    result = with_retry(fn, max_attempts=3, base_delay=0)
    assert result == 42
    assert fn.call_count == 1


def test_success_on_second_attempt():
    fn = MagicMock(side_effect=[RuntimeError("blip"), 99])
    with patch("retry.time.sleep"):
        result = with_retry(fn, max_attempts=3, base_delay=0.01)
    assert result == 99
    assert fn.call_count == 2


def test_raises_after_all_attempts_exhausted():
    fn = MagicMock(side_effect=ConnectionError("down"))
    with patch("retry.time.sleep"):
        with pytest.raises(ConnectionError, match="down"):
            with_retry(fn, max_attempts=3, base_delay=0.01)
    assert fn.call_count == 3


def test_single_attempt_raises_immediately():
    fn = MagicMock(side_effect=ValueError("bad"))
    with pytest.raises(ValueError):
        with_retry(fn, max_attempts=1, base_delay=1.0)
    assert fn.call_count == 1


def test_exponential_delay_schedule():
    fn = MagicMock(side_effect=[IOError(), IOError(), "ok"])
    sleep_calls = []
    with patch("retry.time.sleep", side_effect=lambda d: sleep_calls.append(d)):
        with_retry(fn, max_attempts=3, base_delay=2.0)
    assert sleep_calls == [2.0, 4.0]


def test_args_and_kwargs_forwarded():
    fn = MagicMock(return_value="result")
    with_retry(fn, "a", "b", key="val", max_attempts=1, base_delay=0)
    fn.assert_called_once_with("a", "b", key="val")


def test_retryable_decorator_succeeds():
    @retryable(max_attempts=3, base_delay=0.01)
    def flaky(x):
        return x * 2

    assert flaky(5) == 10


def test_retryable_decorator_retries_then_succeeds():
    attempts = {"n": 0}

    @retryable(max_attempts=3, base_delay=0.01)
    def sometimes_fails():
        attempts["n"] += 1
        if attempts["n"] < 2:
            raise RuntimeError("not yet")
        return "done"

    with patch("retry.time.sleep"):
        result = sometimes_fails()
    assert result == "done"
    assert attempts["n"] == 2


def test_retryable_decorator_preserves_name():
    @retryable(max_attempts=2, base_delay=0)
    def my_function():
        pass

    assert my_function.__name__ == "my_function"


def test_warning_logged_on_retry(caplog):
    fn = MagicMock(side_effect=[OSError("timeout"), "ok"])
    with patch("retry.time.sleep"):
        with caplog.at_level(logging.WARNING, logger="retry"):
            with_retry(fn, max_attempts=2, base_delay=0.01)
    assert "retrying" in caplog.text.lower()
