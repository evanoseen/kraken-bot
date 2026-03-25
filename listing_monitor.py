import feedparser
import json
import logging
import os

logger = logging.getLogger(__name__)

KRAKEN_BLOG_RSS = "https://blog.kraken.com/feed"
SEEN_FILE = "seen_listings.json"

# Coins on Kraken listing roadmap — buy immediately when listed
WATCHLIST = {"DOGS", "GOAT", "FWOG", "PNUT", "MOODENG", "NEIRO", "COW", "HYPER"}


def load_seen() -> set:
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    return set()


def save_seen(seen: set):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)


def check_new_listings() -> list:
    """
    Monitor Kraken blog RSS for new listing announcements.
    Returns list of newly listed coins to buy immediately.
    """
    seen = load_seen()
    new_listings = []

    try:
        feed = feedparser.parse(KRAKEN_BLOG_RSS)
        for entry in feed.entries[:20]:
            title = entry.get("title", "").upper()
            link = entry.get("link", "")
            entry_id = entry.get("id", link)

            if entry_id in seen:
                continue

            # Check if it's a listing announcement
            if any(word in title for word in ["NOW AVAILABLE", "LISTING", "LAUNCHES", "TRADING NOW"]):
                # Check if any watchlist coin is mentioned
                for coin in WATCHLIST:
                    if coin in title:
                        logger.info(f"NEW LISTING DETECTED: {coin} — {entry.get('title')}")
                        new_listings.append(coin)
                        break
                else:
                    # Generic listing — extract ticker if possible
                    logger.info(f"New Kraken listing: {entry.get('title')}")

                seen.add(entry_id)

        save_seen(seen)

    except Exception as e:
        logger.error(f"Listing monitor error: {e}")

    return new_listings
