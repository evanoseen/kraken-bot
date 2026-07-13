"""News headline dedup cache (Day 47).

Tracks which articles have already been sent to Claude this session so
consecutive cycles with the same news don't burn API calls or re-generate
signals for stale stories.

Usage:
    from headline_cache import filter_new, mark_seen

    articles = fetch_top_headlines()
    new_articles = filter_new(articles)
    if not new_articles:
        news_signals = []
    else:
        mark_seen(new_articles)
        headlines = format_headlines_for_prompt(new_articles)
        news_signals = analyze_news_for_trades(headlines, coins)

Article identity: uses the "url" key if present, otherwise falls back to
the "title" key. Articles missing both are always treated as new.
"""
from __future__ import annotations

from typing import Any

_seen: set[str] = set()


def _key(article: dict[str, Any]) -> str | None:
    return article.get("url") or article.get("title")


def filter_new(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return only articles not yet seen this session."""
    return [a for a in articles if _key(a) not in _seen]


def mark_seen(articles: list[dict[str, Any]]) -> None:
    """Record articles as seen so future calls to filter_new exclude them."""
    for a in articles:
        k = _key(a)
        if k:
            _seen.add(k)


def reset() -> None:
    _seen.clear()
