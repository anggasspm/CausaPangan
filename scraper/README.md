# Scraper Berita Harga Pangan

Bagian **Role 1** dari sistem Peringatan Dini & Rekomendasi Aksi Harga Pangan (AIC Compfest 18).
Modul ini bertugas mengambil (scrape) berita seputar harga pangan dari beberapa media daring,
mendeteksi komoditas & wilayah yang relevan secara sederhana (keyword-based), mengambil isi
artikel lengkap, lalu menyimpan hasilnya ke JSON lokal dan/atau Supabase (Postgres) — sebagai
bahan mentah untuk Role 2 (NLP & Event Classifier) dan Role 3 (Model Prediksi).

> Scraper ini **tidak** melakukan klasifikasi penyebab kenaikan harga (`penyebab` di
> `API_CONTRACT.md`). Tugasnya cuma mengumpulkan & memfilter artikel yang _kemungkinan_ relevan,
> lengkap dengan deteksi komoditas & wilayah dasar. Klasifikasi lebih dalam jadi tugas Role 2.

---

## Struktur Folder

```
scraper/
├── config/
│   ├── komoditas.py      # keyword per komoditas (beras, cabai, bawang, migor, dst)
│   ├── sumber.py         # daftar sumber RSS yang di-scrape (16 sumber, lihat tabel di bawah)
│   └── wilayah.py         # kode wilayah kab/kota (WILAYAH_TARGET) + kode provinsi (PROVINSI_TARGET)
├── core/
│   ├── fetcher.py          # fetch RSS & HTML mentah (dengan retry)
│   ├── gnews_resolver.py   # resolve redirect Google News RSS -> URL asli
│   ├── article_fetcher.py  # fetch isi artikel lengkap dari halaman berita
│   ├── normalizer.py       # normalisasi entry RSS -> struktur artikel standar
│   └── parser.py           # deteksi komoditas, wilayah (kab/kota), & provinsi dari teks
├── pipeline/
│   ├── run_scraper.py      # entrypoint utama: fetch -> filter -> enrich -> simpan
│   └── scheduler.py        # scheduler untuk run lokal/server (BUKAN dipakai di GitHub Actions)
├── storage/
│   ├── local_store.py      # simpan ke JSON (snapshot per-run + latest.json gabungan)
│   └── supabase_store.py   # simpan ke Supabase/Postgres tabel artikel_mentah (upsert, best-effort)
├── seed_data/               # hasil scraping (snapshot per-run + latest.json)
├── test.py                  # cek cepat semua sumber RSS bisa di-fetch
├── testdb.py                 # tes koneksi & insert dummy ke Supabase
├── requirements.txt
├── .env.example               # contoh env var yang dibutuhkan
└── README.md
```

---

## Sumber Berita (`config/sumber.py`)

16 sumber RSS, dipilih dari yang terverifikasi jalan (lihat `test.py`) — kanal ekonomi/bisnis
diprioritaskan supaya rasio artikel relevan lebih tinggi dibanding feed umum:

| Sumber                                                        | Cakupan                            |
| ------------------------------------------------------------- | ---------------------------------- |
| Antara - Ekonomi / Bisnis / Ekonomi Finansial / Ekonomi Bursa | Nasional                           |
| Antara Jabar / Jatim / Jateng - Ekonomi                       | Regional (provinsi cakupan MVP)    |
| Antara Banten / Sumsel / Sulsel - Ekonomi                     | Regional (sentra produksi pemasok) |
| Liputan6 - News                                               | Nasional                           |
| CNBC Indonesia - News / Market                                | Nasional                           |
| Republika - Ekonomi                                           | Nasional                           |
| Media Indonesia                                               | Nasional                           |
| Kumparan                                                      | Nasional                           |

**Sumber yang diuji tapi dibuang** (gagal fetch — block scraper atau endpoint mati):
Kontan, Suara.com, JawaPos.

**Sumber tanpa RSS publik** (butuh scraping index HTML terpisah kalau mau dipakai, belum
diimplementasikan): badanpangan.go.id, pustaka.badanpangan.go.id, IDN Times, Harian Basis. Kalau
ini jadi prioritas (khususnya badanpangan.go.id untuk kategori `kebijakan_pemerintah`), perlu
modul scraping index baru — bukan sekadar tambah baris `sumber.py`.

Tambah/cek sumber baru selalu lewat `test.py` dulu sebelum masuk `sumber.py` — jangan asumsikan
RSS masih hidup tanpa verifikasi, karena beberapa media Indonesia sering ganti infrastruktur
tanpa redirect yang jelas.

---

## Alur Kerja Pipeline (`run_scraper.py`)

1. **Fetch RSS** dari semua sumber di `config/sumber.py` (`core/fetcher.py`).
2. **Deteksi komoditas** per entry berdasarkan keyword di `config/komoditas.py`
   (`core/parser.py::deteksi_komoditas`).
3. **Filter relevansi** — entry dibuang kalau tidak match komoditas apa pun
   (`core/parser.py::relevan`). Deteksi wilayah **tidak** dipakai sebagai syarat filter,
   sengaja dilonggarkan supaya tidak kehilangan berita nasional yang tetap relevan.
4. **Normalisasi** entry ke struktur artikel standar, termasuk resolve URL asli kalau sumbernya
   Google News redirect (`core/normalizer.py`, `core/gnews_resolver.py`) — saat ini belum ada
   sumber Google News aktif di `sumber.py`, resolver ini siap dipakai kalau nanti ditambahkan.
5. **Deteksi wilayah** dari judul + ringkasan (`core/parser.py::deteksi_wilayah`) — mencari nama
   kab/kota literal, bisa ambigu (misal "Semarang" bisa Kabupaten atau Kota) sehingga kadang
   mengembalikan lebih dari satu kode wilayah kalau tidak ada penanda eksplisit ("Kota .../Kab.
   ...") di teks.
6. **Deteksi provinsi (fallback)** — kalau langkah 5 tidak menemukan kab/kota spesifik (mayoritas
   kasus untuk berita nasional soal Bulog/Kementan/PIHPS yang tidak menyebut kota tertentu),
   `core/parser.py::deteksi_provinsi` mencoba deteksi level provinsi dari alias nama ("jabar",
   "jateng", "jatim"). Hasilnya disimpan di field **terpisah** `provinsi_terdeteksi` (kode 2-digit)
   — **sengaja tidak digabung** ke `wilayah_terdeteksi` (kode 4-digit) supaya granularitas berbeda
   tidak tercampur dalam satu array yang sama.
7. **Ambil isi artikel lengkap** dengan fetch ke halaman aslinya, bukan cuma ringkasan RSS
   (`core/article_fetcher.py`) — pakai selector spesifik per situs kalau terdaftar, atau fallback
   ke heuristik generik (cari container dengan `<p>` terbanyak).
8. **Simpan**:
   - JSON snapshot per-run: `seed_data/berita_YYYYMMDD_HHMM.json`
   - JSON gabungan (dedup by URL): `seed_data/latest.json`
   - Upsert ke Supabase tabel `artikel_mentah` (kalau `DATABASE_URL` tersedia) — kegagalan di
     langkah ini **tidak** menggagalkan pipeline, karena JSON lokal sudah tersimpan duluan.

Jalankan manual:

```bash
cd scraper
python -m pipeline.run_scraper
```

Secara default `fetch_isi_lengkap=True`, jadi proses akan lebih lambat karena ada jeda
(`DELAY_ANTAR_REQUEST = 1.5` detik) antar-request ke setiap artikel — supaya sopan ke server
sumber berita dan menghindari rate limit/block.

---

## Struktur Data Artikel (Output)

Setiap artikel di `seed_data/latest.json` dan tabel `artikel_mentah` punya field berikut:

| Field                  | Tipe                                                  | Keterangan                                                               |
| ---------------------- | ----------------------------------------------------- | ------------------------------------------------------------------------ |
| `judul`                | string                                                |                                                                          |
| `url`                  | string \| null                                        | Bisa kosong untuk artikel tanpa URL valid dari RSS                       |
| `sumber_media`         | string                                                |                                                                          |
| `tanggal_terbit`       | string (ISO 8601 UTC)                                 |                                                                          |
| `isi_teks`             | string                                                | Isi lengkap (kalau berhasil) atau ringkasan RSS (kalau gagal)            |
| `isi_teks_status`      | `"ok"` \| `"fallback"` \| `"gagal_pakai_summary_rss"` | Lihat penjelasan di bawah                                                |
| `komoditas_terdeteksi` | list[string]                                          | Bisa >1 komoditas per artikel                                            |
| `wilayah_terdeteksi`   | list[string]                                          | Kode kab/kota 4-digit, bisa kosong                                       |
| `provinsi_terdeteksi`  | list[string]                                          | Kode provinsi 2-digit, **hanya diisi kalau `wilayah_terdeteksi` kosong** |

> ⚠️ **Untuk Role 2**: field `provinsi_terdeteksi` ini baru — schema `Article` di
> `nlp_event_classifier/ingest.py` tidak akan otomatis memakainya (pydantic abaikan field ekstra
> secara default, tidak error, tapi juga tidak terpakai). Perlu ditambahkan eksplisit ke schema
> kalian kalau mau dimanfaatkan.

---

## Setup Lokal

### 1. Install dependencies

```bash
cd scraper
python -m venv venv
source venv/Scripts/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Setup environment variable

Salin `.env.example` menjadi `.env`, lalu isi `DATABASE_URL` dengan connection string Supabase:

```bash
cp .env.example .env
```

```env
# scraper/.env
DATABASE_URL=postgresql://postgres.xxxx:PASSWORD@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres
```

> **Wajib pakai connection string Pooler** (`pooler.supabase.com`, port `6543`), bukan direct
> connection (`db.xxx.supabase.co`) — direct connection Supabase saat ini IPv6-only, sementara
> kebanyakan jaringan lokal maupun runner GitHub Actions cuma dukung IPv4. Salah pakai ini akan
> muncul sebagai error `could not translate host name`, bukan salah password.

> `.env` **tidak boleh di-commit**. Sudah dimasukkan ke `.gitignore`. Kalau butuh connection
> string yang valid, minta ke pemilik project Supabase — jangan pernah hardcode ke kode maupun
> commit ke git, walau di branch pribadi.

Kalau `.env` tidak diisi / `DATABASE_URL` kosong, pipeline tetap jalan normal dan cuma
menyimpan ke JSON lokal (`seed_data/`) — koneksi Supabase bersifat best-effort, bukan wajib untuk
development.

### 3. Uji sumber RSS

```bash
python test.py
```

### 4. Uji koneksi Supabase (opsional)

```bash
python testdb.py
```

Ini akan insert satu baris dummy ke tabel `artikel_mentah` (dibuat/dimigrasi otomatis kalau
kolom belum ada, lewat `CREATE TABLE IF NOT EXISTS` + `ALTER TABLE ADD COLUMN IF NOT EXISTS`).

---

## Otomatisasi via GitHub Actions

Pipeline dijadwalkan berjalan otomatis tiap 6 jam lewat `.github/workflows/scraper.yml`
(00:00, 06:00, 12:00, 18:00 UTC / 07:00, 13:00, 19:00, 01:00 WIB), atau bisa dipicu manual lewat
tab **Actions > Scraper Berita Harga Pangan > Run workflow**.

Setelah workflow ini selesai sukses, `.github/workflows/classifier.yml` (milik Role 2) otomatis
terpicu lewat `workflow_run` untuk menjalankan event classifier di atas `seed_data/latest.json`
yang baru saja ter-update — lihat README `nlp_event_classifier/` untuk detailnya.

### Setup yang wajib dilakukan sebelum workflow bisa jalan

1. **Tambahkan secret** `DATABASE_URL` di repo:
   **Settings > Secrets and variables > Actions > New repository secret**, isi dengan connection
   string Supabase **format Pooler** (lihat catatan di atas). Tanpa secret ini, scraper tetap
   jalan dan tetap commit `seed_data/*.json`, hanya saja tidak ada data yang masuk ke Supabase.
2. **Pastikan permission workflow sudah benar**: **Settings > Actions > General > Workflow
   permissions**, pilih **"Read and write permissions"**.
3. **Push file `.github/workflows/scraper.yml`** ke branch default — workflow terjadwal
   (`schedule`) hanya aktif kalau file-nya sudah ada di branch default repo.

### Hal lain yang perlu diketahui

- `pipeline/scheduler.py` **tidak dipakai** di Actions — file itu untuk run di server/mesin yang
  hidup terus-menerus. Di GitHub Actions, penjadwalan sudah di-handle oleh `on.schedule`.
- Hasil `seed_data/*.json` di-commit balik ke repo otomatis setelah setiap run.
- Kalau butuh cek apakah run terakhir berhasil, lihat log di tab **Actions**, bukan cuma commit
  history — commit hanya menunjukkan ada/tidaknya perubahan data, bukan status tiap sumber.

---

## Catatan & Keterbatasan yang Perlu Diketahui Role Lain

- **Kode wilayah di `config/wilayah.py` belum final** — perlu diverifikasi ulang terhadap tabel
  resmi Kemendagri/BPS sebelum dipakai untuk join ke data harga Bapanas/PIHPS.
- **Deteksi wilayah & provinsi berbasis keyword nama, bukan NER** — akurasinya terbatas, terutama
  untuk nama kota ambigu. Kalau Role 2/3 butuh deteksi lokasi lebih akurat, sebaiknya diperkaya
  dengan NER di tahap pemrosesan lanjutan, bukan mengandalkan hasil scraper sebagai kebenaran final.
- **`provinsi_terdeteksi` cuma fallback lemah** — dia cuma cari alias nama provinsi literal
  ("jabar", "jateng", "jatim") di teks. Kalau artikel bicara "Pantura" atau nama daerah lain yang
  tidak eksplisit menyebut nama provinsi, tetap tidak akan terdeteksi.
- **`isi_teks_status`** pada tiap artikel menandakan kualitas ekstraksi isi:
  - `ok` — berhasil pakai selector spesifik situs
  - `fallback` — berhasil pakai heuristik generik, isi biasanya tetap lengkap (bukan snippet),
    cuma berpotensi ada noise di pinggiran teks
  - `gagal_pakai_summary_rss` — gagal ambil isi lengkap, cuma cuplikan RSS 1-2 kalimat
- **`SITE_SELECTORS`** di `core/article_fetcher.py` baru mencakup Liputan6, Detik, Bisnis.com,
  dan Kompas — belum ada selector untuk sumber baru (CNBC Indonesia, Republika, Media Indonesia,
  Kumparan), jadi artikel dari sumber-sumber itu akan selalu lewat fallback generik untuk sekarang.
- **Resolver Google News** (`core/gnews_resolver.py`) memakai endpoint internal tidak resmi,
  berpotensi berhenti berfungsi sewaktu-waktu. **Saat ini belum ada sumber Google News aktif** di
  `sumber.py`, jadi modul ini belum benar-benar teruji di pipeline nyata — baru lolos cek sintaks.
- **Kolom `sudah_diproses`** di tabel `artikel_mentah` sengaja tidak disentuh oleh upsert scraper.
  Kolom ini murni milik pipeline NLP/model (Role 2/3) untuk menandai artikel yang sudah diproses.
- **Duplikat/near-duplikat antar-URL** (misal 2 portal daerah republish artikel pusat yang sama)
  belum ditangani — dedup saat ini cuma exact-match by URL. Diputuskan diabaikan untuk MVP karena
  tiap artikel diproses independen per-URL; revisit kalau nanti dipakai sebagai sinyal exogenous
  yang sensitif terhadap over-counting.

---

## Troubleshooting Singkat

| Gejala                                                    | Kemungkinan Penyebab                                                               | Solusi                                                                                             |
| --------------------------------------------------------- | ---------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| `test.py` melaporkan "GAGAL" untuk suatu sumber           | RSS down / berubah struktur / block scraper                                        | Cek URL manual di browser; kalau memang mati, hapus dari `sumber.py`                               |
| `testdb.py` error `psycopg2` tidak ketemu                 | Belum install dependencies                                                         | `pip install -r requirements.txt`                                                                  |
| `testdb.py` error `could not translate host name`         | Pakai direct connection (IPv6-only), bukan Pooler                                  | Ganti `DATABASE_URL` ke connection string **Pooler** (port `6543`)                                 |
| `testdb.py` error `invalid dsn`                           | Salah format string, sering karena copy-paste ganda `DATABASE_URL=` di dalam value | Pastikan `os.environ["DATABASE_URL"]` isinya cuma connection string murni                          |
| Workflow Actions gagal di step `git push`                 | Permission token read-only                                                         | Cek **Settings > Actions > General > Workflow permissions**, aktifkan "Read and write permissions" |
| Artikel banyak `isi_teks_status: gagal_pakai_summary_rss` | Situs sumber berubah struktur HTML / block scraper                                 | Cek manual, mungkin perlu update `SITE_SELECTORS` atau `HEADERS` User-Agent                        |
