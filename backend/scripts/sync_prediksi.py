"""
sync_prediksi.py -- Bagian "simpan" dari orkestrasi pipeline
scrape -> NLP -> model -> simpan -> serve (PRD §7.1, tanggung jawab Role 1).

v3: Menggabungkan TIGA sumber hasil Role 2:
1. data/hasil_forecasting/latest.json  -> harga_terakhir, satuan,
   persentase_perubahan, arah, confidence (dari model Holt-Winters)
2. data/hasil_klasifikasi/latest.json  -> penyebab, penyebab_detail,
   sumber_berita
3. recommendation_engine (pure function, bukan file JSON) -> rekomendasi_target,
   rekomendasi_aksi, rekomendasi_urgensi

Jalankan dari root repo:
    python backend/scripts/sync_prediksi.py
"""
import json
import os
import sys
from pathlib import Path as _Path
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# recommendation_engine ada di root repo, bukan di backend/scripts/ -- karena
# script ini dijalankan langsung (bukan lewat `python -m`), Python cuma
# nambahin folder script ini sendiri ke sys.path, bukan root repo. Baris di
# bawah ini nambahin root repo secara eksplisit supaya import-nya ketemu.
sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))  # <-- BARU
from recommendation_engine import generate_recommendation  # <-- BARU

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(DATABASE_URL)

# Path relatif terhadap root repo -- jalankan script ini dari root, bukan dari backend/
HASIL_FORECASTING_PATH = Path("data/hasil_forecasting/latest.json")
HASIL_KLASIFIKASI_PATH = Path("data/hasil_klasifikasi/latest.json")


def load_json(path: Path, label: str):
    if not path.exists():
        print(f"WARNING: {path} tidak ditemukan ({label}), lanjut tanpa data ini.")
        return []
    with open(path) as f:
        return json.load(f)


def build_forecasting_index(forecasts):
    """(kode_wilayah, kode_komoditas) -> 1 baris hasil forecasting."""
    index = {}
    for row in forecasts:
        key = (row["kode_wilayah"], row["kode_komoditas"])
        index[key] = row
    return index


def build_article_index(articles):
    """
    (kode_wilayah, kode_komoditas) -> list artikel yang relevan.
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


def main():
    forecasts = load_json(HASIL_FORECASTING_PATH, "hasil forecasting")
    articles = load_json(HASIL_KLASIFIKASI_PATH, "hasil klasifikasi")

    forecasting_index = build_forecasting_index(forecasts)
    article_index = build_article_index(articles)
    print(f"Loaded {len(forecasts)} baris forecasting, {len(articles)} artikel "
          f"({len(article_index)} kombinasi kota x komoditas punya sinyal berita).")

    now = datetime.now(timezone.utc)
    written, skipped_no_forecast = 0, 0

    with engine.begin() as conn:
        kota_rows = conn.execute(text("SELECT kode_wilayah FROM wilayah")).fetchall()
        kota_codes = {k.kode_wilayah for k in kota_rows}

        for (kode_wilayah, kode_komoditas), forecast in forecasting_index.items():
            if kode_wilayah not in kota_codes:
                # forecasting kadang cakup kota di luar 13 kota MVP -- skip,
                # bukan bug, cuma di luar cakupan sistem sekarang.
                continue

            valid_signal_articles = [
                a for a in article_index.get((kode_wilayah, kode_komoditas), [])
                if a.get("penyebab")
            ]

            if valid_signal_articles:
                best = max(valid_signal_articles, key=lambda a: a.get("llm_certainty", 0))
                penyebab = best.get("penyebab")
                penyebab_detail = best.get("penyebab_detail")
            else:
                penyebab = None
                penyebab_detail = None

            # <-- BARU: panggil recommendation engine
            rekomendasi = generate_recommendation(
                penyebab=penyebab,
                arah=forecast["arah"],
                persentase_perubahan=forecast["persentase_perubahan"],
                confidence=forecast["confidence"],
            )

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
                    :rek_target, :rek_aksi, :rek_urgensi,
                    :updated
                )
                ON CONFLICT (kode_wilayah, kode_komoditas) DO UPDATE SET
                    harga_terakhir = EXCLUDED.harga_terakhir,
                    satuan = EXCLUDED.satuan,
                    persentase_perubahan = EXCLUDED.persentase_perubahan,
                    arah = EXCLUDED.arah,
                    confidence = EXCLUDED.confidence,
                    tier_data = EXCLUDED.tier_data,
                    penyebab = EXCLUDED.penyebab,
                    penyebab_detail = EXCLUDED.penyebab_detail,
                    rekomendasi_target = EXCLUDED.rekomendasi_target,
                    rekomendasi_aksi = EXCLUDED.rekomendasi_aksi,
                    rekomendasi_urgensi = EXCLUDED.rekomendasi_urgensi,
                    terakhir_diperbarui = EXCLUDED.terakhir_diperbarui
            """), {
                "kw": kode_wilayah, "kk": kode_komoditas, "nama": nama_komoditas,
                "harga": forecast["harga_terakhir"], "satuan": forecast.get("satuan", "Rp/kg"),
                "pct": forecast["persentase_perubahan"], "arah": forecast["arah"],
                "conf": forecast["confidence"], "tier": forecast.get("tier_data", "solid"),
                "penyebab": penyebab, "penyebab_detail": penyebab_detail,
                # <-- BARU: 3 baris ini gantiin NULL, NULL, NULL yang lama
                "rek_target": rekomendasi.target if rekomendasi else None,
                "rek_aksi": rekomendasi.aksi if rekomendasi else None,
                "rek_urgensi": rekomendasi.urgensi if rekomendasi else None,
                "updated": now,
            })

            conn.execute(text("""
                DELETE FROM sumber_berita WHERE kode_wilayah = :kw AND kode_komoditas = :kk
            """), {"kw": kode_wilayah, "kk": kode_komoditas})

            for art in valid_signal_articles:
                conn.execute(text("""
                    INSERT INTO sumber_berita (kode_wilayah, kode_komoditas, judul, url, sumber_media, tanggal_terbit)
                    VALUES (:kw, :kk, :judul, :url, :sumber, :tanggal)
                """), {
                    "kw": kode_wilayah, "kk": kode_komoditas,
                    "judul": art.get("judul", ""), "url": art.get("url", ""),
                    "sumber": art.get("sumber_media", ""), "tanggal": art.get("tanggal_terbit"),
                })

            written += 1

        skipped_no_forecast = len(kota_codes) * 5 - written  # 5 = jumlah komoditas tetap

    print(f"Selesai: {written} baris prediksi ditulis/diupdate dari hasil forecasting asli, "
          f"{skipped_no_forecast} kombinasi belum punya hasil forecasting.")


if __name__ == "__main__":
    main()