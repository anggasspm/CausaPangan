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
│   ├── sumber.py         # daftar sumber RSS yang di-scrape
│   └── wilayah.py        # daftar kode wilayah (Kemendagri/BPS) target
├── core/
│   ├── fetcher.py         # fetch RSS & HTML mentah (dengan retry)
│   ├── gnews_resolver.py  # resolve redirect Google News RSS -> URL asli
│   ├── article_fetcher.py # fetch isi artikel lengkap dari halaman berita
│   ├── normalizer.py      # normalisasi entry RSS -> struktur artikel standar
│   └── parser.py          # deteksi komoditas & wilayah dari teks (keyword matching)
├── pipeline/
│   ├── run_scraper.py     # entrypoint utama: fetch -> filter -> enrich -> simpan
│   └── scheduler.py       # scheduler untuk run lokal/server (BUKAN dipakai di GitHub Actions)
├── storage/
│   ├── local_store.py     # simpan ke JSON (snapshot per-run + latest.json gabungan)
│   └── supabase_store.py  # simpan ke Supabase/Postgres (upsert, best-effort)
├── seed_data/              # hasil scraping (snapshot per-run + latest.json)
├── test.py                 # cek cepat semua sumber RSS bisa di-fetch
├── testdb.py                # tes koneksi & insert dummy ke Supabase
├── requirements.txt
├── .env.example              # contoh env var yang dibutuhkan
└── README.md
```

---

## Alur Kerja Pipeline (`run_scraper.py`)

1. **Fetch RSS** dari semua sumber di `config/sumber.py` (`core/fetcher.py`).
2. **Deteksi komoditas** per entry berdasarkan keyword di `config/komoditas.py`
   (`core/parser.py::deteksi_komoditas`).
3. **Filter relevansi** — entry dibuang kalau tidak match komoditas apa pun
   (`core/parser.py::relevan`). Deteksi wilayah saat ini **tidak** dipakai sebagai syarat filter,
   sengaja dilonggarkan supaya tidak kehilangan berita nasional yang tetap relevan.
4. **Normalisasi** entry ke struktur artikel standar, termasuk resolve URL asli kalau sumbernya
   Google News redirect (`core/normalizer.py`, `core/gnews_resolver.py`).
5. **Deteksi wilayah** dari judul + ringkasan (`core/parser.py::deteksi_wilayah`) — hasilnya bisa
   ambigu (misal "Semarang" bisa Kabupaten atau Kota) sehingga kadang mengembalikan lebih dari
   satu kode wilayah kalau tidak ada penanda eksplisit ("Kota .../Kab. ...") di teks.
6. **Ambil isi artikel lengkap** dengan fetch ke halaman aslinya, bukan cuma ringkasan RSS
   (`core/article_fetcher.py`) — pakai selector spesifik per situs kalau terdaftar, atau fallback
   ke heuristik generik (cari container dengan `<p>` terbanyak).
7. **Simpan**:
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
DATABASE_URL=postgresql://postgres.xxxx:PASSWORD@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres
```

> `.env` **tidak boleh di-commit**. Sudah dimasukkan ke `.gitignore`. Kalau butuh connection
> string yang valid, minta ke pemilik project Supabase — jangan pernah hardcode ke kode maupun
> commit ke git, walau di branch pribadi.

Kalau `.env` tidak diisi / `DATABASE_URL` kosong, pipeline tetap jalan normal dan cuma
menyimpan ke JSON lokal (`seed_data/`) — koneksi Supabase bersifat best-effort, bukan wajib untuk
development.

### 3. Uji sumber RSS

Cek semua sumber di `config/sumber.py` bisa diakses:

```bash
python test.py
```

### 4. Uji koneksi Supabase (opsional)

```bash
python testdb.py
```

Ini akan insert satu baris dummy ke tabel `artikel_mentah` (dibuat otomatis kalau belum ada).

---

## Otomatisasi via GitHub Actions

Pipeline dijadwalkan berjalan otomatis tiap 6 jam lewat `.github/workflows/scraper.yml`
(00:00, 06:00, 12:00, 18:00 UTC / 07:00, 13:00, 19:00, 01:00 WIB), atau bisa dipicu manual lewat
tab **Actions > Scraper Berita Harga Pangan > Run workflow**.

### Isi workflow (`.github/workflows/scraper.yml`)

```yaml
name: Scraper Berita Harga Pangan

on:
  schedule:
    - cron: "0 0,6,12,18 * * *"
  workflow_dispatch: {}

permissions:
  contents: write

concurrency:
  group: scraper-berita
  cancel-in-progress: false

jobs:
  scrape:
    runs-on: ubuntu-latest
    timeout-minutes: 30

    defaults:
      run:
        working-directory: scraper

    steps:
      - name: Checkout repo
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"
          cache-dependency-path: scraper/requirements.txt

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Jalankan scraper
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
        run: python -c "from pipeline.run_scraper import run; run(debug=False)"

      - name: Commit hasil scrape ke repo
        run: |
          git config --local user.email "actions@github.com"
          git config --local user.name "GitHub Actions Scraper"
          git add seed_data/
          git diff --staged --quiet || git commit -m "chore: update seed_data hasil scraping [skip ci]"
          git push
```

### Penjelasan tiap bagian

| Bagian                                      | Fungsi                                                                                                                                                                                                    |
| ------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `on.schedule`                               | Trigger otomatis 4x/hari via cron (waktu UTC, GitHub tidak menjamin presisi ke detik — bisa telat beberapa menit saat traffic Actions tinggi)                                                             |
| `on.workflow_dispatch`                      | Tombol "Run workflow" manual di tab Actions, dipakai untuk testing tanpa menunggu jadwal                                                                                                                  |
| `permissions.contents: write`               | Wajib eksplisit — default `GITHUB_TOKEN` bisa read-only tergantung setting repo, dan step `git push` di akhir akan gagal diam-diam kalau ini tidak diset                                                  |
| `concurrency`                               | Mencegah dua run jalan bersamaan (misal manual trigger pas jadwal cron juga jalan) — `local_store.py` baca+tulis `latest.json`, race condition antar dua proses bisa bikin penulisan saling menimpa/korup |
| `timeout-minutes: 30`                       | Jaga-jaga kalau ada situs sumber lambat/hang, runner tidak menggantung lama-lama dan menghabiskan minutes gratis                                                                                          |
| `working-directory: scraper`                | Semua step `run` dieksekusi relatif dari folder `scraper/`, sama seperti kalau dijalankan manual dari situ                                                                                                |
| `cache: pip`                                | Mempercepat run berikutnya dengan cache dependency, key cache mengikuti hash `requirements.txt`                                                                                                           |
| `env: DATABASE_URL`                         | Inject secret sebagai environment variable — otomatis terbaca oleh `os.environ.get("DATABASE_URL")` di `supabase_store.py` tanpa perlu file `.env` di runner                                              |
| `run(debug=False)`                          | Sengaja tidak memanggil `python -m pipeline.run_scraper` langsung, karena entrypoint `__main__` di file itu default `debug=True` (log verbose per-artikel) — kurang cocok untuk log CI terjadwal          |
| `git diff --staged --quiet \|\| git commit` | Commit hanya dibuat kalau memang ada perubahan di `seed_data/`, menghindari commit kosong tiap run                                                                                                        |
| `[skip ci]`                                 | Mencegah commit hasil scrape memicu workflow lain yang listen ke event `push`                                                                                                                             |

### Setup yang wajib dilakukan sebelum workflow bisa jalan

1. **Tambahkan secret** `DATABASE_URL` di repo:
   **Settings > Secrets and variables > Actions > New repository secret**, isi dengan connection
   string Supabase (pakai password yang sudah diverifikasi aman, bukan yang pernah ke-hardcode di
   riwayat kode). Tanpa secret ini, scraper tetap jalan dan tetap commit `seed_data/*.json`, hanya
   saja tidak ada data yang masuk ke Supabase.
2. **Pastikan permission workflow sudah benar**: **Settings > Actions > General > Workflow
   permissions**, pilih **"Read and write permissions"**. `permissions: contents: write` di YAML
   saja kadang tidak cukup kalau setting repo di halaman ini masih dibatasi read-only.
3. **Push file `.github/workflows/scraper.yml`** ke branch default — workflow terjadwal
   (`schedule`) hanya aktif kalau file-nya sudah ada di branch default repo, bukan di branch lain.

### Hal lain yang perlu diketahui

- `pipeline/scheduler.py` **tidak dipakai** di Actions — file itu untuk run di server/mesin yang
  hidup terus-menerus (pakai `schedule` + infinite loop). Di GitHub Actions, penjadwalan sudah
  di-handle oleh `on.schedule`, jadi yang dipanggil langsung `run_scraper.run()` sekali per
  trigger, lalu proses selesai dan runner dimatikan.
- Hasil `seed_data/*.json` di-commit balik ke repo otomatis setelah setiap run, supaya
  `latest.json` di git history tetap sinkron dengan yang ada di Supabase — berguna juga sebagai
  histori/debug yang gampang diinspeksi manual tanpa perlu query database.
- Kalau butuh cek apakah run terakhir berhasil (misal banyak sumber RSS gagal), lihat log di tab
  **Actions**, bukan cuma commit history — commit hanya menunjukkan ada/tidaknya perubahan data,
  bukan status keberhasilan tiap sumber.

---

## Catatan & Keterbatasan yang Perlu Diketahui Role Lain

- **Kode wilayah di `config/wilayah.py` belum final** — perlu diverifikasi ulang terhadap tabel
  resmi Kemendagri/BPS sebelum dipakai untuk join ke data harga Bapanas/PIHPS.
- **Deteksi wilayah dari teks berbasis keyword nama kota, bukan NER** — akurasinya terbatas,
  terutama untuk nama kota ambigu (lihat poin 5 di alur kerja). Kalau Role 2/3 butuh deteksi
  lokasi yang lebih akurat, sebaiknya diperkaya dengan NER di tahap pemrosesan lanjutan, bukan
  mengandalkan hasil `wilayah_terdeteksi` dari scraper sebagai kebenaran final.
- **`isi_teks_status`** pada tiap artikel menandakan kualitas ekstraksi isi:
  - `ok` — berhasil pakai selector spesifik situs
  - `fallback` — berhasil pakai heuristik generik (situs belum terdaftar di `SITE_SELECTORS`)
  - `gagal_pakai_summary_rss` — gagal ambil isi lengkap, artikel tetap disimpan dengan ringkasan
    RSS apa adanya supaya data tidak hilang total
- **`SITE_SELECTORS`** di `core/article_fetcher.py` baru mencakup Liputan6, Detik, Bisnis.com,
  dan Kompas. Antara sengaja tidak didaftarkan karena fallback generik terbukti lebih akurat untuk
  situs tersebut — lihat komentar di kode sebelum menambahkan selector baru untuk Antara.
- **Resolver Google News** (`core/gnews_resolver.py`) memakai endpoint internal
  (`batchexecute`) yang tidak resmi didokumentasikan Google, jadi berpotensi berhenti berfungsi
  sewaktu-waktu tanpa pemberitahuan. Kalau resolver ini tiba-tiba banyak gagal, itu tanda skema
  internal Google berubah, bukan bug di kode kita — cek dulu sebelum panik debug.
- **Kolom `sudah_diproses`** di tabel `artikel_mentah` sengaja tidak disentuh oleh upsert scraper
  (lihat `storage/supabase_store.py`). Kolom ini murni milik pipeline NLP/model (Role 2/3) untuk
  menandai artikel yang sudah diproses — scraper hanya pemilik kolom konten.

---

## Troubleshooting Singkat

| Gejala                                                    | Kemungkinan Penyebab                               | Solusi                                                                                                                                                            |
| --------------------------------------------------------- | -------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `test.py` melaporkan "GAGAL" untuk suatu sumber           | RSS down / berubah struktur / rate limit           | Cek URL manual di browser, biarkan `tenacity` retry otomatis handle gangguan sementara                                                                            |
| `testdb.py` error `psycopg2` tidak ketemu                 | Belum install dependencies                         | `pip install -r requirements.txt`                                                                                                                                 |
| `testdb.py` jalan tapi tidak insert apa pun               | `DATABASE_URL` kosong/salah                        | Cek isi `.env`, pastikan credential masih valid di Supabase                                                                                                       |
| Workflow Actions gagal di step `git push`                 | Permission token read-only                         | Cek **Settings > Actions > General > Workflow permissions**, pastikan "Read and write permissions" aktif, atau `permissions: contents: write` di YAML sudah benar |
| Artikel banyak `isi_teks_status: gagal_pakai_summary_rss` | Situs sumber berubah struktur HTML / block scraper | Cek manual, mungkin perlu update `SITE_SELECTORS` atau `HEADERS` User-Agent                                                                                       |
