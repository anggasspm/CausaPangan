from core.fetcher import fetch_rss

sumber_baru = [
    ("CNBC Indonesia - News", "https://www.cnbcindonesia.com/news/rss"),
    ("CNBC Indonesia - Market", "https://www.cnbcindonesia.com/market/rss/"),
    ("Republika - Ekonomi", "https://www.republika.co.id/rss/ekonomi/"),
    ("Media Indonesia", "https://mediaindonesia.com/feed"),
    ("JawaPos - Ekonomi", "https://www.jawapos.com/ekonomi/rss"),
    ("Kumparan", "https://lapi.kumparan.com/v2.0/rss/"),
]
for nama, url in sumber_baru:
    try:
        entries = fetch_rss(url)
        print(nama, "OK", len(entries))
    except Exception as e:
        print(nama, "GAGAL", e)