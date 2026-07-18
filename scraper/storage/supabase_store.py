"""
storage/supabase_store.py

Simpan artikel hasil scraping ke Supabase (Postgres) lewat DATABASE_URL,
BERBARENGAN dengan penyimpanan JSON lokal yang sudah ada di local_store.py
-- bukan pengganti. JSON lokal tetap jalan sebagai:
  1. fallback kalau DATABASE_URL belum di-set / koneksi gagal (dev lokal
     tanpa akses DB, atau CI run tanpa secret ke-set)
  2. histori per-run yang gampang diinspeksi manual tanpa perlu query DB

Tabel: artikel_mentah -- staging TERPISAH dari 4 tabel Role 1
(wilayah, riwayat_harga, prediksi, sumber_berita). Tidak ada FK ke skema
Role 1 sama sekali, supaya scraper bisa jalan independen tanpa menunggu
pipeline model/recommendation engine selesai.
"""

import os
import json

try:
    import psycopg2
    import psycopg2.extras
    PSYCOPG2_TERSEDIA = True
except ImportError:
    PSYCOPG2_TERSEDIA = False


DDL_ARTIKEL_MENTAH = """
CREATE TABLE IF NOT EXISTS artikel_mentah (
    id                   BIGSERIAL PRIMARY KEY,
    judul                TEXT NOT NULL,
    url                  TEXT UNIQUE,
    sumber_media         VARCHAR NOT NULL,
    tanggal_terbit       TIMESTAMPTZ NOT NULL,
    isi_teks             TEXT,
    isi_teks_status      VARCHAR,
    komoditas_terdeteksi TEXT[] NOT NULL DEFAULT '{}',
    wilayah_terdeteksi   TEXT[] NOT NULL DEFAULT '{}',
    provinsi_terdeteksi  TEXT[] NOT NULL DEFAULT '{}',
    sudah_diproses       BOOLEAN NOT NULL DEFAULT false,
    dibuat_pada          TIMESTAMPTZ NOT NULL DEFAULT now(),
    diperbarui_pada      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Migrasi aman untuk DB yang sudah terlanjur dibuat sebelum kolom ini ada.
-- IF NOT EXISTS mencegah error kalau kolom sudah tersedia (idempotent).
ALTER TABLE artikel_mentah ADD COLUMN IF NOT EXISTS provinsi_terdeteksi TEXT[] NOT NULL DEFAULT '{}';

CREATE INDEX IF NOT EXISTS idx_artikel_mentah_tanggal ON artikel_mentah (tanggal_terbit);
CREATE INDEX IF NOT EXISTS idx_artikel_mentah_komoditas ON artikel_mentah USING GIN (komoditas_terdeteksi);
CREATE INDEX IF NOT EXISTS idx_artikel_mentah_wilayah ON artikel_mentah USING GIN (wilayah_terdeteksi);
CREATE INDEX IF NOT EXISTS idx_artikel_mentah_provinsi ON artikel_mentah USING GIN (provinsi_terdeteksi);
CREATE INDEX IF NOT EXISTS idx_artikel_mentah_belum_diproses ON artikel_mentah (sudah_diproses) WHERE sudah_diproses = false;
"""

# Catatan: upsert TIDAK menyentuh kolom sudah_diproses -- kalau artikel lama
# di-upsert ulang (misal isi_teks_status berubah jadi 'ok' di run berikutnya),
# status 'sudah_diproses' yang di-set pipeline NLP/model TIDAK boleh
# tertimpa balik ke false oleh scraper. Scraper cuma pemilik kolom konten,
# bukan pemilik kolom status pemrosesan.
UPSERT_ARTIKEL = """
INSERT INTO artikel_mentah (
    judul, url, sumber_media, tanggal_terbit, isi_teks,
    isi_teks_status, komoditas_terdeteksi, wilayah_terdeteksi,
    provinsi_terdeteksi, diperbarui_pada
) VALUES (
    %(judul)s, %(url)s, %(sumber_media)s, %(tanggal_terbit)s, %(isi_teks)s,
    %(isi_teks_status)s, %(komoditas_terdeteksi)s, %(wilayah_terdeteksi)s,
    %(provinsi_terdeteksi)s, now()
)
ON CONFLICT (url) DO UPDATE SET
    judul = EXCLUDED.judul,
    isi_teks = EXCLUDED.isi_teks,
    isi_teks_status = EXCLUDED.isi_teks_status,
    komoditas_terdeteksi = EXCLUDED.komoditas_terdeteksi,
    wilayah_terdeteksi = EXCLUDED.wilayah_terdeteksi,
    provinsi_terdeteksi = EXCLUDED.provinsi_terdeteksi,
    diperbarui_pada = now();
"""


def _get_connection():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        return None
    return psycopg2.connect(database_url)


def _artikel_url_kosong_ke_none(artikel: dict) -> dict:
    """
    UNIQUE constraint di kolom url butuh nilai unik atau NULL (Postgres
    memperbolehkan banyak baris NULL lolos UNIQUE, tidak dianggap duplikat).
    Artikel tanpa URL diubah ke None di sini supaya tidak semua
    artikel-tanpa-url dianggap bentrok satu sama lain oleh Postgres.
    """
    artikel = dict(artikel)
    if not artikel.get("url"):
        artikel["url"] = None
    return artikel


def simpan_ke_supabase(data: list[dict]) -> None:
    """
    Push list artikel ke Supabase. Silent no-op (dengan pesan info) kalau:
    - psycopg2 belum terinstall (dev lokal yang belum setup)
    - DATABASE_URL belum di-set (dev lokal tanpa akses DB / CI tanpa secret)
    Silent DEGRADE (bukan raise) supaya pipeline scraping tetap selesai dan
    JSON lokal tetap tersimpan walau DB gagal -- data tidak boleh hilang
    hanya karena masalah koneksi DB.
    """
    if not PSYCOPG2_TERSEDIA:
        print("[SUPABASE][INFO] psycopg2 tidak terinstall, skip push ke DB. "
              "Jalankan: pip install psycopg2-binary")
        return

    if not data:
        return

    conn = None
    try:
        conn = _get_connection()
        if conn is None:
            print("[SUPABASE][INFO] DATABASE_URL tidak di-set, skip push ke DB "
                  "(data tetap aman di seed_data/*.json).")
            return

        with conn:
            with conn.cursor() as cur:
                cur.execute(DDL_ARTIKEL_MENTAH)

                rows = [_artikel_url_kosong_ke_none(a) for a in data]
                for row in rows:
                    cur.execute(UPSERT_ARTIKEL, {
                        "judul": row.get("judul", ""),
                        "url": row.get("url"),
                        "sumber_media": row.get("sumber_media", ""),
                        "tanggal_terbit": row.get("tanggal_terbit"),
                        "isi_teks": row.get("isi_teks", ""),
                        "isi_teks_status": row.get("isi_teks_status"),
                        "komoditas_terdeteksi": row.get("komoditas_terdeteksi", []),
                        "wilayah_terdeteksi": row.get("wilayah_terdeteksi", []),
                        "provinsi_terdeteksi": row.get("provinsi_terdeteksi", []),
                    })

        print(f"[SUPABASE] {len(data)} artikel berhasil di-upsert ke tabel artikel_mentah.")

    except Exception as e:
        # Jangan biarkan kegagalan DB menghentikan pipeline scraping.
        # local_store.py (JSON) sudah jalan duluan sebelum fungsi ini
        # dipanggil, jadi data tidak hilang -- ini cuma best-effort sync.
        print(f"[SUPABASE][ERROR] Gagal push ke DB: {e}")
    finally:
        if conn is not None:
            conn.close()