# Backend — Sistem Peringatan Dini & Rekomendasi Aksi Harga Pangan

Role 1 — Data & Infrastructure. Sesuai API_CONTRACT.md v1.1.

## Struktur folder

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py       # FastAPI app, 4 endpoint sesuai API_CONTRACT §2
│   ├── store.py       # Query layer ke Postgres (Supabase)
│   ├── db.py           # Koneksi database (baca DATABASE_URL dari .env)
│   └── models.py        # Pydantic schema + penegakan aturan null §4
├── requirements.txt
├── .env.example          # Template — copy jadi .env, isi DATABASE_URL asli
├── .gitignore
├── schema.sql             # Definisi 4 tabel (wilayah, riwayat_harga, prediksi, sumber_berita)
├── reset_schema.sql        # Drop tabel lama (dipakai kalau schema berubah)
└── seed_import.sql          # Data historis 13 kota x 5 komoditas (sudah di-run di Supabase)
```

## Setup & jalankan lokal

```bash
cd backend
pip install -r requirements.txt

cp .env.example .env
# buka .env, isi DATABASE_URL dengan connection string Supabase asli
# (Project > tombol "Connect" > Connection String > URI)

uvicorn app.main:app --reload --port 8000
```

Buka `http://localhost:8000/docs` untuk Swagger UI interaktif, atau test langsung:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/wilayah
curl "http://localhost:8000/api/v1/prediksi?kota=3273"
curl http://localhost:8000/api/v1/prediksi/ringkasan
```

## Status data saat ini

| Tabel | Isi |
|---|---|
| `wilayah` | ✅ 13 kota (Jabar/Jateng/Jatim), semua tier `solid` |
| `riwayat_harga` | ✅ 5.135 baris (13 kota × 5 komoditas × 79 bulan, Jan 2020–Jul 2026) |
| `prediksi` | 🔲 **Kosong** — menunggu output Role 2 (forecasting + event classifier + recommendation engine). Endpoint tetap jalan normal, balikin `[]`. |
| `sumber_berita` | 🔲 Kosong — terisi bareng `prediksi` |

## Kode komoditas yang dipakai (bukan generik)

```
beras, cabai_rawit_merah, cabai_merah_keriting, bawang_merah, minyak_goreng
```

## Belum dikerjakan (tahap berikutnya)

- Docker Compose (Tahap 3) — biar tim lain nggak perlu setup manual kayak di atas
- Isi tabel `prediksi` (nunggu Role 2, atau seed dummy sementara)
- GitHub Actions untuk scraping berkala (Tahap 5)
- Deploy ke Render (Tahap 6)