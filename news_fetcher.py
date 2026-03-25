import feedparser

RSS_FEEDS = [
    "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en",
    "https://cointelegraph.com/rss",
    "https://decrypt.co/feed",
    "https://coindesk.com/arc/outboundfeeds/rss/",
    "https://news.google.com/rss/search?q=dogecoin+OR+shiba+inu+OR+pepe+coin+OR+meme+coin&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=elon+musk+crypto+OR+elon+musk+doge&hl=en-US&gl=US&ceid=US:en",
]

def fetch_top_headlines(max_articles: int = 60) -> list:
    articles = []
    seen = set()
    for rss_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries[:10]:
                title = entry.get("title", "")
                if title and title not in seen:
                    seen.add(title)
                    articles.append({
                        "title": title,
                        "summary": entry.get("summary", ""),
                    })
        except Exception:
            continue
    return articles[:max_articles]

def format_headlines_for_prompt(articles: list) -> str:
    return "\n".join(f"{i+1}. {a['title']}" for i, a in enumerate(articles))
