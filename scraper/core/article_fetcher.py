"""
Fetch isi artikel lengkap dari halaman berita (bukan cuma summary RSS).
Dipakai supaya NER & event classifier (Role 2) dapat teks yang lebih kaya
daripada cuplikan 1-2 kalimat dari RSS.

Strategi:
1. Coba selector spesifik per situs (paling akurat, minim noise)
2. Kalau situs belum terdaftar / selector gagal -> fallback ke heuristik generik
   (ambil semua <p> di dalam kandidat container artikel terbesar)
"""

import re
import time
import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_fixed

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
}

REQUEST_TIMEOUT = 10
DELAY_ANTAR_REQUEST = 1.5  # detik, sopan santun ke server, hindari rate-limit/block


# -----------------------------------------------------------------
# 1. Selector spesifik per situs
#    key = potongan domain yang match di URL
#    value = CSS selector yang berisi isi artikel
# -----------------------------------------------------------------
SITE_SELECTORS = {
    "antaranews.com": "div.post-content.clearfix",
    "liputan6.com": "div.article-content-body__item-content",
    "detik.com": "div.detail__body-text",
    "bisnis.com": "div.detailsContent",
    "kompas.com": "div.read__content",
}

# Tag yang harus dibuang dari dalam container artikel karena bukan isi asli
# (iklan, caption foto, related-news, dsb)
NOISE_SELECTORS = [
    "script", "style", "iframe", "ins", "figure figcaption",
    ".baca-juga", ".artikel-terkait", ".ads", ".ad-container",
]


def _bersihkan_noise(container):
    for sel in NOISE_SELECTORS:
        for tag in container.select(sel):
            tag.decompose()
    return container


def _extract_dengan_selector(soup, selector: str) -> str | None:
    container = soup.select_one(selector)
    if not container:
        return None
    container = _bersihkan_noise(container)
    paragraphs = [p.get_text(strip=True) for p in container.find_all("p")]
    paragraphs = [p for p in paragraphs if len(p) > 20]  # buang paragraf sampah/pendek
    return "\n".join(paragraphs) if paragraphs else None


def _extract_fallback_generik(soup) -> str | None:
    """
    Fallback kalau situs belum terdaftar di SITE_SELECTORS.
    Heuristik: cari <div>/<article> dengan jumlah <p> terbanyak,
    asumsi itu adalah container isi artikel.
    """
    kandidat = soup.find_all(["article", "div", "section"])
    terbaik, jumlah_p_terbanyak = None, 0

    for tag in kandidat:
        jumlah_p = len(tag.find_all("p", recursive=False)) + len(tag.find_all("p"))
        if jumlah_p > jumlah_p_terbanyak:
            terbaik, jumlah_p_terbanyak = tag, jumlah_p

    if not terbaik or jumlah_p_terbanyak < 3:
        return None

    terbaik = _bersihkan_noise(terbaik)
    paragraphs = [p.get_text(strip=True) for p in terbaik.find_all("p")]
    paragraphs = [p for p in paragraphs if len(p) > 20]
    return "\n".join(paragraphs) if paragraphs else None


def _pilih_selector(url: str) -> str | None:
    for domain, selector in SITE_SELECTORS.items():
        if domain in url:
            return selector
    return None


@retry(stop=stop_after_attempt(2), wait=wait_fixed(2))
def _fetch_html(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.text


def fetch_isi_artikel(url: str) -> dict:
    """
    Return dict:
    {
        "isi_teks": str,       # isi artikel bersih, "" kalau gagal
        "status": "ok" | "fallback" | "gagal",
        "sumber_selector": str | None
    }
    """
    try:
        html = _fetch_html(url)
    except Exception as e:
        return {"isi_teks": "", "status": "gagal", "error": str(e)}

    soup = BeautifulSoup(html, "lxml")

    selector = _pilih_selector(url)
    if selector:
        isi = _extract_dengan_selector(soup, selector)
        if isi:
            return {"isi_teks": isi, "status": "ok", "sumber_selector": selector}

    # Selector spesifik gagal / situs belum terdaftar -> fallback generik
    isi = _extract_fallback_generik(soup)
    if isi:
        return {"isi_teks": isi, "status": "fallback", "sumber_selector": None}

    return {"isi_teks": "", "status": "gagal", "error": "Tidak ada paragraf yang bisa diekstrak"}


def perkaya_artikel(artikel_list: list[dict]) -> list[dict]:
    """
    Terima list artikel hasil scraper RSS (yang isi_teks-nya masih summary pendek),
    lalu fetch halaman aslinya untuk dapat isi_teks lengkap.
    Rate-limited supaya tidak membanjiri server situs berita.
    """
    hasil = []
    total = len(artikel_list)

    for i, artikel in enumerate(artikel_list, 1):
        url = artikel.get("url", "")
        print(f"[FETCH ARTIKEL] ({i}/{total}) {artikel.get('judul', '')[:60]}")

        info = fetch_isi_artikel(url)

        if info["status"] in ("ok", "fallback"):
            artikel["isi_teks"] = info["isi_teks"]
            artikel["isi_teks_status"] = info["status"]
        else:
            # Gagal ambil isi lengkap -> tetap simpan artikel dengan summary RSS
            # yang sudah ada sebelumnya, jangan sampai data hilang total.
            artikel["isi_teks_status"] = "gagal_pakai_summary_rss"
            print(f"  [WARN] Gagal ekstrak isi lengkap: {info.get('error', '-')}")

        hasil.append(artikel)
        time.sleep(DELAY_ANTAR_REQUEST)  # sopan ke server, hindari block

    return hasil