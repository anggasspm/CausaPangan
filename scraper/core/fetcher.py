import feedparser
import requests
from tenacity import retry, stop_after_attempt, wait_fixed

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; AIC-Scraper/1.0)"}

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def fetch_rss(url: str):
    feed = feedparser.parse(url)
    if feed.bozo and not feed.entries:
        raise ConnectionError(f"Gagal parse RSS: {url}")
    return feed.entries

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def fetch_html(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    return resp.text