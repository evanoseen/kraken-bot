import feedparser
import requests
import logging

logger = logging.getLogger(__name__)

RSS_FEEDS = [
    "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en",
    "https://cointelegraph.com/rss",
    "https://decrypt.co/feed",
    "https://coindesk.com/arc/outboundfeeds/rss/",
    "https://news.google.com/rss/search?q=dogecoin+OR+shiba+inu+OR+pepe+coin+OR+meme+coin&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=elon+musk+crypto+OR+elon+musk+doge&hl=en-US&gl=US&ceid=US:en",
    # Crypto-specific Twitter/X account RSS via nitter (free, no API key)
    "https://nitter.poast.org/elonmusk/rss",
    "https://nitter.poast.org/CoinbaseAssets/rss",
    "https://nitter.poast.org/binance/rss",
    "https://nitter.poast.org/kraken/rss",
    "https://nitter.poast.org/cz_binance/rss",
    "https://nitter.poast.org/VitalikButerin/rss",
    "https://nitter.poast.org/realDonaldTrump/rss",
]

# Backup nitter instances if primary is down
NITTER_INSTANCES = [
    "https://nitter.poast.org",
    "https://nitter.privacydev.net",
    "https://nitter.1d4.us",
]

# High-signal crypto accounts to monitor
TWITTER_ACCOUNTS = [
    # ── Billionaires / politicians that move markets ──
    "elonmusk",           # moves DOGE/crypto with single tweets
    "realDonaldTrump",    # TRUMP coin + crypto policy
    "saylor",             # Michael Saylor — BTC maximalist, huge influence
    "RobertKiyosaki",     # Rich Dad author, big crypto calls

    # ── Exchange official accounts ──
    "CoinbaseAssets",     # listing announcements — instant pump signal
    "binance",            # Binance announcements
    "kraken",             # Kraken announcements
    "krakenfx",           # Kraken futures
    "coinbase",           # general Coinbase
    "BitfinexExchange",   # Bitfinex exchange
    "gate_io",            # Gate.io listings

    # ── Exchange CEOs ──
    "cz_binance",         # Binance CEO
    "brian_armstrong",    # Coinbase CEO
    "jessepowellx",       # Kraken founder

    # ── Crypto founders ──
    "VitalikButerin",     # Ethereum founder
    "justinsuntron",      # TRON founder — very active, moves coins
    "SatoshiLite",        # Charlie Lee — Litecoin founder
    "officialmcafee",     # (archived but monitored)

    # ── Top crypto influencers / callers ──
    "APompliano",         # Anthony Pompliano — massive following
    "aantonop",           # Andreas Antonopoulos
    "CryptoWendyO",       # big meme coin caller
    "Crypto_Cobain",      # influential trader
    "MMCrypto",           # huge YouTube/Twitter following
    "altcoinpsycho",      # early altcoin calls
    "CryptoCapo_",        # macro crypto analyst
    "TechDev_52",         # on-chain analyst
    "rektcapital",        # cycle analyst
    "inversebrah",        # contrarian calls
    "CryptoCred",         # technical analyst
    "nebraskangooner",    # altcoin hunter
    "Sheldon_Sniper",     # sniper entries
    "CryptoGodJohn",      # meme coin caller
    "gainzy222",          # degenerate plays
    "LayahHeilpern",      # crypto journalist/influencer

    # ── News & media ──
    "BitcoinMagazine",    # Bitcoin news
    "Cointelegraph",      # crypto news
    "DecryptMedia",       # crypto news
    "TheBlock__",         # institutional crypto news
    "WuBlockchain",       # China crypto news — early signals
    "PeckShieldAlert",    # hack/exploit alerts — sell signals
    "zachxbt",            # on-chain detective — rug pull warnings
]


def fetch_twitter_signals(max_per_account: int = 5) -> list:
    """
    Fetch recent tweets from high-signal crypto accounts via Nitter RSS.
    No API key needed — uses public Nitter instances.
    """
    articles = []
    seen = set()

    for account in TWITTER_ACCOUNTS:
        fetched = False
        for instance in NITTER_INSTANCES:
            url = f"{instance}/{account}/rss"
            try:
                feed = feedparser.parse(url)
                if not feed.entries:
                    continue
                for entry in feed.entries[:max_per_account]:
                    title = entry.get("title", "").strip()
                    # Clean up nitter title format "R to @user: text" -> just text
                    if ": " in title:
                        title = title.split(": ", 1)[-1]
                    if title and title not in seen and len(title) > 10:
                        seen.add(title)
                        articles.append({
                            "title": f"[TWEET @{account}] {title}",
                            "summary": entry.get("summary", ""),
                            "source": "twitter",
                        })
                fetched = True
                break  # got results from this instance, move to next account
            except Exception:
                continue  # try next nitter instance

        if not fetched:
            logger.debug(f"Could not fetch tweets for @{account}")

    if articles:
        logger.info(f"Fetched {len(articles)} tweets from {len(TWITTER_ACCOUNTS)} accounts")
    return articles


def fetch_top_headlines(max_articles: int = 60) -> list:
    articles = []
    seen = set()

    # RSS news feeds
    for rss_url in RSS_FEEDS[:6]:  # original 6 news feeds only
        try:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries[:10]:
                title = entry.get("title", "")
                if title and title not in seen:
                    seen.add(title)
                    articles.append({
                        "title": title,
                        "summary": entry.get("summary", ""),
                        "source": "news",
                    })
        except Exception:
            continue

    # Twitter signals — prepend so Claude sees them first (higher priority)
    tweets = fetch_twitter_signals()
    articles = tweets + articles

    return articles[:max_articles]


def format_headlines_for_prompt(articles: list) -> str:
    lines = []
    for i, a in enumerate(articles):
        prefix = "🐦" if a.get("source") == "twitter" else "📰"
        lines.append(f"{i+1}. {prefix} {a['title']}")
    return "\n".join(lines)
