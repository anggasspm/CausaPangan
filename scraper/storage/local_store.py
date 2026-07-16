import json
import os
from datetime import datetime
from storage.supabase_store import simpan_ke_supabase


def _muat_json(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            # file korup/kosong -> jangan sampai crash pipeline, mulai dari kosong
            print(f"[STORAGE][WARN] Gagal parse {path}, dianggap kosong.")
            return []


def _gabung_dedup(lama: list[dict], baru: list[dict]) -> list[dict]:
    """
    Gabungkan artikel lama + baru, dedup berdasarkan url.
    Artikel baru menang kalau url sama (misal isi_teks_status berubah
    dari 'gagal_pakai_summary_rss' jadi 'ok' di run berikutnya).
    Artikel tanpa url (url kosong) tetap disimpan apa adanya tanpa dedup,
    karena tidak ada key yang bisa dipakai.
    """
    gabungan = {}
    tanpa_url = []

    for artikel in lama + baru:
        url = artikel.get("url", "")
        if url:
            gabungan[url] = artikel  # yang belakangan (baru) menimpa yang lama
        else:
            tanpa_url.append(artikel)

    return list(gabungan.values()) + tanpa_url


def simpan_batch(data: list[dict], folder="seed_data"):
    os.makedirs(folder, exist_ok=True)

    # Snapshot per-run tetap seperti semula (untuk histori/debug),
    # HANYA berisi hasil run ini, bukan gabungan.
    filename = f"{folder}/berita_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # latest.json: gabungkan dengan isi lama, dedup by url
    latest_path = f"{folder}/latest.json"
    lama = _muat_json(latest_path)
    hasil_akhir = _gabung_dedup(lama, data)

    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(hasil_akhir, f, ensure_ascii=False, indent=2)

    print(
        f"[STORAGE] Disimpan ke {filename} "
        f"({len(data)} artikel run ini) dan {latest_path} "
        f"({len(hasil_akhir)} total setelah gabung & dedup)"
    )

    # Push ke Supabase (tabel artikel_mentah) -- dipanggil TERAKHIR, setelah
    # JSON lokal aman tersimpan. Kalau ini gagal (DATABASE_URL belum di-set,
    # psycopg2 belum terinstall, atau koneksi gagal), pipeline tetap selesai
    # dengan sukses dan data tidak hilang -- lihat supabase_store.py untuk
    # detail penanganan errornya.
    simpan_ke_supabase(data)