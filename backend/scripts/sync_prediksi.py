"""
sync_prediksi.py -- Bagian "simpan" dari orkestrasi pipeline
scrape -> NLP -> model -> simpan -> serve (PRD §7.1, tanggung jawab Role 1).

Menggabungkan:
1. Hasil event classifier Role 2 (data/hasil_klasifikasi/latest.json)
   -> mengisi penyebab, penyebab_detail, sumber_berita
2. Baseline harga dari riwayat_harga yang sudah kita import
   -> mengisi harga_terakhir, persentase_perubahan, arah
   (BUKAN hasil forecasting model asli -- placeholder sampai
   Role 2 selesai modul forecasting/time series)

confidence sengaja di-set 0.4 (di bawah 0.5) untuk SEMUA baris yang
ditulis script ini, supaya aturan null API_CONTRACT §4 otomatis
menyembunyikan `rekomendasi` -- frontend akan menampilkan state
"belum cukup data untuk rekomendasi", bukan rekomendasi karangan.
Begitu Role 2 selesai model forecasting asli, confidence & rekomendasi
akan ditulis ulang oleh pipeline yang sebenarnya (ganti script ini).

Jalankan manual dulu:
    python sync_prediksi.py

Nanti masuk ke GitHub Actions (Tahap 5) supaya jalan otomatis setelah
scraper + classifier selesai tiap run terjadwal.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(DATABASE_URL)

# Path relatif terhadap root repo -- sesuaikan kalau struktur folder beda
HASIL_KLASIFIKASI_PATH = Path("data/hasil_klasifikasi/latest.json")

PLACEHOLDER_CONFIDENCE = 0.4   # sengaja < 0.5, lihat penjelasan di docstring atas
KOMODITAS_LIST = ["beras", "cabai_rawit_merah", "cabai_merah_keriting", "bawang_merah", "minyak_goreng"]


def load_classified_articles():
    if not HASIL_KLASIFIKASI_PATH.exists():
        print(f"WARNING: {HASIL_KLASIFIKASI_PATH} tidak ditemukan, lanjut tanpa data classifier.")
        return []
    with open(HASIL_KLASIFIKASI_PATH) as f:
        return json.load(f)


def build_article_index(articles):
    """
    Map (kode_wilayah, kode_komoditas) -> list artikel yang relevan.
    Artikel tanpa wilayah_terdeteksi di-skip (belum bisa dipetakan ke 1 kota).
    """
    index = {}
    for art in articles:
        wilayah_list = art.get("wilayah_terdeteksi") or []
        komoditas_list = art.get("komoditas_terdeteksi") or []
        for kw in wilayah_list:
            for kk in komoditas_list:
                index.setdefault((kw, kk), []).append(art)
    return index


def compute_baseline(conn, kode_wilayah, kode_komoditas):
    """
    Ambil 2 bulan terakhir yang punya harga (bukan NULL) dari riwayat_harga,
    hitung persentase_perubahan & arah secara naif (BUKAN forecasting).
    Return None kalau datanya kurang dari 2 titik.
    """
    rows = conn.execute(text("""
        SELECT bulan, harga FROM riwayat_harga
        WHERE kode_wilayah = :kw AND kode_komoditas = :kk AND harga IS NOT NULL
        ORDER BY bulan DESC LIMIT 2
    """), {"kw": kode_wilayah, "kk": kode_komoditas}).fetchall()

    if len(rows) < 2:
        return None

    terakhir, sebelumnya = rows[0].harga, rows[1].harga
    if sebelumnya == 0:
        return None

    pct = round((float(terakhir) - float(sebelumnya)) / float(sebelumnya) * 100, 2)
    arah = "stabil" if abs(pct) <= 2 else ("naik" if pct > 0 else "turun")
    return {"harga_terakhir": float(terakhir), "persentase_perubahan": pct, "arah": arah}


def main():
    articles = load_classified_articles()
    article_index = build_article_index(articles)
    print(f"Loaded {len(articles)} artikel, {len(article_index)} kombinasi kota x komoditas punya sinyal berita.")

    now = datetime.now(timezone.utc)
    written, skipped_no_baseline = 0, 0

    with engine.begin() as conn:
        kota_rows = conn.execute(text("SELECT kode_wilayah, tier_data FROM wilayah")).fetchall()

        for kota in kota_rows:
            for kode_komoditas in KOMODITAS_LIST:
                baseline = compute_baseline(conn, kota.kode_wilayah, kode_komoditas)
                if baseline is None:
                    skipped_no_baseline += 1
                    continue

                matched_articles = article_index.get((kota.kode_wilayah, kode_komoditas), [])
                # Hanya artikel yang punya penyebab non-null yang dianggap "sinyal valid" --
                # supaya sumber_berita tetap konsisten dengan penyebab sesuai API_CONTRACT §4
                # (sumber_berita WAJIB [] kalau penyebab null, tidak boleh sebagian sinyal
                # tanpa penyebab ikut nyasar ke sumber_berita).
                valid_signal_articles = [a for a in matched_articles if a.get("penyebab")]

                if valid_signal_articles:
                    best = max(valid_signal_articles, key=lambda a: a.get("llm_certainty", 0))
                    penyebab = best.get("penyebab")
                    penyebab_detail = best.get("penyebab_detail")
                else:
                    penyebab = None
                    penyebab_detail = None

                nama_komoditas = kode_komoditas.replace("_", " ").title()

                conn.execute(text("""
                    INSERT INTO prediksi (
                        kode_wilayah, kode_komoditas, nama_komoditas, harga_terakhir, satuan,
                        persentase_perubahan, arah, confidence, tier_data,
                        penyebab, penyebab_detail,
                        rekomendasi_target, rekomendasi_aksi, rekomendasi_urgensi,
                        terakhir_diperbarui
                    ) VALUES (
                        :kw, :kk, :nama, :harga, :satuan,
                        :pct, :arah, :conf, :tier,
                        :penyebab, :penyebab_detail,
                        NULL, NULL, NULL,
                        :updated
                    )
                    ON CONFLICT (kode_wilayah, kode_komoditas) DO UPDATE SET
                        harga_terakhir = EXCLUDED.harga_terakhir,
                        persentase_perubahan = EXCLUDED.persentase_perubahan,
                        arah = EXCLUDED.arah,
                        confidence = EXCLUDED.confidence,
                        penyebab = EXCLUDED.penyebab,
                        penyebab_detail = EXCLUDED.penyebab_detail,
                        terakhir_diperbarui = EXCLUDED.terakhir_diperbarui
                """), {
                    "kw": kota.kode_wilayah, "kk": kode_komoditas, "nama": nama_komoditas,
                    "harga": baseline["harga_terakhir"], "satuan": "Rp/kg",
                    "pct": baseline["persentase_perubahan"], "arah": baseline["arah"],
                    "conf": PLACEHOLDER_CONFIDENCE, "tier": kota.tier_data,
                    "penyebab": penyebab, "penyebab_detail": penyebab_detail,
                    "updated": now,
                })

                # sumber_berita: hapus yang lama untuk kombinasi ini, tulis ulang dari artikel yang match
                conn.execute(text("""
                    DELETE FROM sumber_berita WHERE kode_wilayah = :kw AND kode_komoditas = :kk
                """), {"kw": kota.kode_wilayah, "kk": kode_komoditas})

                for art in valid_signal_articles:
                    conn.execute(text("""
                        INSERT INTO sumber_berita (kode_wilayah, kode_komoditas, judul, url, sumber_media, tanggal_terbit)
                        VALUES (:kw, :kk, :judul, :url, :sumber, :tanggal)
                    """), {
                        "kw": kota.kode_wilayah, "kk": kode_komoditas,
                        "judul": art.get("judul", ""), "url": art.get("url", ""),
                        "sumber": art.get("sumber_media", ""), "tanggal": art.get("tanggal_terbit"),
                    })

                written += 1

    print(f"Selesai: {written} baris prediksi ditulis/diupdate, {skipped_no_baseline} dilewati (kurang dari 2 titik data historis).")


if __name__ == "__main__":
    main()