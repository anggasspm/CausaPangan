"""
core/gnews_resolver.py

Google News RSS tidak memberi URL artikel asli secara langsung di tag <link>.
URL yang muncul berbentuk:
    https://news.google.com/rss/articles/CBMi....?oc=5

Ini BUKAN redirect HTTP biasa (301/302) -- Google mengenkode URL asli ke
dalam base64 (kadang perlu decode protobuf-like), dan resolusinya butuh
call tambahan ke endpoint internal 'batchexecute' Google.

Strategi di sini:
1. Coba decode langsung dari base64 payload di path URL (cara cepat, tidak
   selalu berhasil karena Google kadang encode metadata tambahan bukan URL
   polos).
2. Kalau gagal, fallback ke request 'batchexecute' -- ambil signature (sid)
   dari halaman artikel Google News, lalu POST ke endpoint decode resmi
   yang dipakai frontend Google News sendiri.
3. Kalau kedua cara gagal, kembalikan None -- caller (article_fetcher)
   sudah punya fallback simpan summary RSS apa adanya, jadi tidak ada
   data yang hilang total.

Catatan: endpoint 'batchexecute' adalah endpoint internal, bukan API publik
resmi -- berpotensi berubah sewaktu-waktu tanpa pemberitahuan dari Google.
Kalau resolver ini berhenti bekerja di kemudian hari, itu tanda Google
mengubah skema internal mereka, bukan bug di kode kita.
"""

import re
import base64
import json
import requests
from tenacity import retry, stop_after_attempt, wait_fixed

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
}
REQUEST_TIMEOUT = 10


def is_gnews_redirect(url: str) -> bool:
    return "news.google.com/rss/articles/" in url


def _decode_base64_cepat(gnews_url: str) -> str | None:
    """
    Coba ekstrak URL asli langsung dari payload base64 di path.
    Berhasil untuk sebagian besar artikel format lama Google News.
    """
    try:
        match = re.search(r"/articles/([^?/]+)", gnews_url)
        if not match:
            return None
        payload = match.group(1)
        # Google pakai base64 URL-safe, tambahkan padding kalau kurang
        payload += "=" * (-len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload)
        # Cari pola URL http(s) di dalam bytes hasil decode
        url_match = re.search(rb'https?://[^\x00-\x1f"\'<>]+', decoded)
        if url_match:
            return url_match.group(0).decode("utf-8", errors="ignore")
    except Exception:
        pass
    return None


@retry(stop=stop_after_attempt(2), wait=wait_fixed(2))
def _ambil_signature(gnews_url: str) -> tuple[str, str] | None:
    """
    Ambil (signature, timestamp) yang disisipkan Google di HTML halaman
    artikel Google News -- dibutuhkan untuk request decode ke batchexecute.
    """
    resp = requests.get(gnews_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    html = resp.text

    # Signature & timestamp disisipkan di atribut data-n-a-sg / data-n-a-ts
    sig_match = re.search(r'data-n-a-sg="([^"]+)"', html)
    ts_match = re.search(r'data-n-a-ts="([^"]+)"', html)
    id_match = re.search(r'data-n-a-id="([^"]+)"', html)

    if not (sig_match and ts_match and id_match):
        return None

    return id_match.group(1), sig_match.group(1), ts_match.group(1)


@retry(stop=stop_after_attempt(2), wait=wait_fixed(2))
def _decode_via_batchexecute(article_id: str, signature: str, timestamp: str) -> str | None:
    """
    Panggil endpoint internal yang dipakai frontend Google News untuk
    resolve redirect. Payload ini meniru request yang dikirim browser saat
    membuka link Google News -- format 'f.req' adalah kontrak internal
    Google, bukan API terdokumentasi.
    """
    url = "https://news.google.com/_/DotsSplashUi/data/batchexecute"

    # Bangun struktur dulu sebagai objek Python, baru di-dump sekali di akhir.
    # Menghindari gabung string manual antara json.dumps(...) dan f-string
    # yang gampang bikin kurung/kutip tidak sinkron.
    inner_payload = [
        "garturlreq",
        [
            ["X", "X", ["X", "X"], None, None, 1, 1, "US:en", None, 1, None, None, None, None, None, 0, 1],
            "X", "X", 1, [1, 1, 1], 1, 1, None, 0, 0, None, 0
        ],
        article_id,
        int(timestamp),
        signature,
    ]

    rpc_call = ["Fbv4je", json.dumps(inner_payload), None, "generic"]
    f_req = json.dumps([[rpc_call]])

    payload = {"f.req": f_req}

    resp = requests.post(
        url,
        headers={**HEADERS, "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"},
        data=payload,
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()

    try:
        # Response berformat "prefix)]}'\n" + JSON array bersarang
        raw = resp.text.split("\n\n")[1]
        parsed = json.loads(raw)
        inner = json.loads(parsed[0][2])
        return inner[1]
    except Exception:
        return None


def resolve_url_asli(gnews_url: str) -> str:
    """
    Entry point utama. Selalu kembalikan sebuah string:
    - URL asli kalau berhasil di-resolve
    - gnews_url apa adanya kalau semua cara gagal (caller tetap bisa coba
      fetch langsung ke news.google.com sebagai upaya terakhir, walau
      kemungkinan besar article_fetcher akan gagal ekstrak isi dari sana)
    """
    if not is_gnews_redirect(gnews_url):
        return gnews_url

    cepat = _decode_base64_cepat(gnews_url)
    if cepat:
        return cepat

    try:
        sig_data = _ambil_signature(gnews_url)
        if sig_data:
            article_id, signature, timestamp = sig_data
            hasil = _decode_via_batchexecute(article_id, signature, timestamp)
            if hasil:
                return hasil
    except Exception as e:
        print(f"[GNEWS_RESOLVER][WARN] Gagal resolve {gnews_url}: {e}")

    return gnews_url