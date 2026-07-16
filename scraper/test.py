from core.fetcher import fetch_rss
from config.sumber import SUMBER_BERITA
for s in SUMBER_BERITA:
    try:
        entries = fetch_rss(s["rss"])
        print(s["nama"], "OK", len(entries))
    except Exception as e:
        print(s["nama"], "GAGAL", e)