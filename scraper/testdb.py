import os
os.environ.get("DATABASE_URL")

from storage.supabase_store import simpan_ke_supabase

dummy = [{
    "judul": "Test koneksi",
    "url": "https://test-koneksi-supabase.com/1",
    "sumber_media": "test",
    "tanggal_terbit": "2026-07-16T00:00:00Z",
    "isi_teks": "isi tes",
    "isi_teks_status": "ok",
    "komoditas_terdeteksi": ["beras"],
    "wilayah_terdeteksi": [],
}]
simpan_ke_supabase(dummy)