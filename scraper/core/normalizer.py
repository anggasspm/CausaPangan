from datetime import datetime
import pytz
from core.gnews_resolver import resolve_url_asli, is_gnews_redirect

WIB = pytz.timezone("Asia/Jakarta")

def ke_utc_iso8601(dt_struct, asumsi_wib=True) -> str:
    dt = datetime(*dt_struct[:6])
    if asumsi_wib:
        dt = WIB.localize(dt).astimezone(pytz.utc)
    else:
        dt = pytz.utc.localize(dt)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

def normalisasi_artikel(entry, sumber_nama: str) -> dict:
    url = entry.get("link") or entry.get("id") or ""

    # Google News RSS: link mentahnya redirect, bukan URL artikel asli.
    # Resolve di sini supaya field 'url' yang tersimpan (JSON & Supabase)
    # sudah URL asli media, bukan news.google.com -- juga dibutuhkan
    # article_fetcher biar selector per-domain bisa match.
    if is_gnews_redirect(url):
        url = resolve_url_asli(url)

    return {
        "judul": entry.title,
        "url": url,
        "sumber_media": sumber_nama,
        "tanggal_terbit": ke_utc_iso8601(entry.published_parsed),
        "isi_teks": getattr(entry, "summary", ""),
        "komoditas_terdeteksi": [],
        "wilayah_terdeteksi": [],
    }