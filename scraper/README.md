# Scraper — Sistem Peringatan Dini & Rekomendasi Aksi Harga Pangan

Modul ini adalah bagian **Scraper Berita** dari pipeline data (Role: NLP & ML Engineer).
Tugasnya: mengambil berita ekonomi/pangan dari sumber RSS, memfilter yang relevan
dengan komoditas prioritas, mengambil isi artikel lengkap, lalu menyimpannya dalam
format terstruktur untuk dikonsumsi tahap **NER & Event Classifier** berikutnya.

Alur lengkap sistem: `Scraper Berita → NLP (NER + Event Classifier) → Model Time Series
→ Recommendation Engine → API → Dashboard` (lihat PRD Bagian 5.1).

---

## 1. Struktur Folder

```
scraper/
├── config/
│   ├── komoditas.py       # daftar komoditas prioritas + sinonim untuk filtering
│   ├── wilayah.py         # daftar provinsi/kota target (kode Kemendagri)
│   └── sumber.py          # daftar sumber RSS berita
├── core/
│   ├── fetcher.py         # fetch RSS feed
│   ├── parser.py          # deteksi relevansi (komoditas & wilayah)
│   ├── normalizer.py      # normalisasi entry RSS ke schema kontrak
│   └── article_fetcher.py # fetch isi artikel lengkap dari halaman berita
├── pipeline/
│   ├── run_scraper.py     # orchestrator utama
|   └── scheduler.py       # automasi
├── storage/
│   └── local_store.py     # simpan hasil ke JSON lokal (seed data)
├── seed_data/              # output JSON, dipakai Role 1 untuk seed Firestore
├── requirements.txt
└── README.md               # dokumen ini
```

---

## 2. Setup

```bash
cd scraper
python -m venv venv
source venv/Scripts/activate      # Windows Git Bash
# source venv/bin/activate        # macOS/Linux

pip install -r requirements.txt
```

Dependency utama: `feedparser`, `requests`, `beautifulsoup4`, `lxml`, `tenacity`,
`python-dateutil`, `pytz`.

---

## 3. Cara Menjalankan

Jalankan **sebagai module** dari root folder `scraper/` (bukan langsung
`python pipeline/run_scraper.py`, karena akan menyebabkan `ModuleNotFoundError`):

```bash
python -m pipeline.run_scraper
```

Mode debug (menampilkan semua judul yang diproses beserta hasil deteksi komoditasnya):

```python
# di pipeline/run_scraper.py
if __name__ == "__main__":
    run(debug=True)
```

Untuk menonaktifkan fetch isi artikel lengkap (lebih cepat, hanya pakai summary RSS —
berguna saat testing filter tanpa menunggu proses fetch satu-per-satu):

```python
run(debug=True, fetch_isi_lengkap=False)
```

---

## 4. Output

Setiap run menghasilkan dua file di `seed_data/`:

- `berita_YYYYMMDD_HHMM.json` — snapshot per-run (untuk histori/debug)
- `latest.json` — snapshot terbaru (dipakai Role 1 untuk seed Firestore/Docker Compose,
  dan oleh Role 2 lain untuk mulai NER)

### Struktur tiap artikel

```json
{
  "judul": "Harga pangan Senin ini, cabai rawit Rp57.250/kg dan telur ayam Rp28.600/kg",
  "url": "https://jatim.antaranews.com/berita/1081408/...",
  "sumber_media": "Antara Jatim - Ekonomi",
  "tanggal_terbit": "2026-07-12T20:53:31Z",
  "isi_teks": "Jakarta (ANTARA) - Pusat Informasi Harga Pangan Strategis ...",
  "komoditas_terdeteksi": ["cabai_rawit_merah"],
  "wilayah_terdeteksi": [],
  "isi_teks_status": "fallback"
}
```

Field `judul`, `url`, `sumber_media`, `tanggal_terbit` **wajib match** dengan schema
`sumber_berita` di `API_CONTRACT.md` (Bagian 3.1). Timestamp selalu ISO 8601 UTC.

Field tambahan (internal, tidak masuk API response akhir, tapi dipakai tahap NLP berikutnya):

| Field | Keterangan |
|---|---|
| `isi_teks` | Isi artikel lengkap (bukan cuma cuplikan RSS), sudah dibersihkan dari boilerplate |
| `komoditas_terdeteksi` | Hasil deteksi keyword komoditas, list kosong jika tidak ada match |
| `wilayah_terdeteksi` | Hasil deteksi keyword nama kota, **saat ini masih kasar** (lihat Known Issues) |
| `isi_teks_status` | `"ok"` = selector spesifik situs berhasil, `"fallback"` = pakai heuristik generik, `"gagal_pakai_summary_rss"` = gagal fetch artikel penuh, isi_teks masih summary RSS pendek |

---

## 5. Sumber Berita yang Digunakan

| Sumber | RSS URL | Status |
|---|---|---|
| Antara - Ekonomi | `antaranews.com/rss/ekonomi.xml` | Aktif |
| Antara - Bisnis | `antaranews.com/rss/ekonomi-bisnis.xml` | Aktif |
| Antara Jabar - Ekonomi | `jabar.antaranews.com/rss/ekonomi.xml` | Aktif |
| Antara Jatim - Ekonomi | `jatim.antaranews.com/rss/ekonomi.xml` | Aktif |
| Antara Jateng - Ekonomi | `jateng.antaranews.com/rss/ekonomi.xml` | Aktif |
| Liputan6 - News | `feed.liputan6.com/rss/news` | Aktif (general news, noise lebih tinggi) |
| Kompas - Bisnis Keuangan | `kompas.com/getrss/bisniskeuangan` | **Tidak aktif**, dieksklusi |

> Tambahkan sumber RSS regional Antara lain (Jabar/Jatim/Jateng/dst) sesuai provinsi
> final yang dipilih tim (PRD Bagian 13, keputusan terbuka #10).

---

## 6. Filter Relevansi

Artikel dianggap relevan jika judul/summary-nya mengandung salah satu sinonim
komoditas prioritas (lihat `config/komoditas.py`). Filter **tidak** mewajibkan
deteksi wilayah — karena judul berita jarang eksplisit menyebut nama kota, dan
deteksi wilayah presisi didelegasikan ke tahap NER berikutnya.

Komoditas yang sudah terverifikasi ter-capture dari sumber saat ini: **beras,
cabai rawit merah, bawang merah**. Komoditas lain (cabai merah keriting, minyak
goreng) belum ada di sample harian — sinonim di `komoditas.py` perlu ditinjau
ulang secara berkala.

---

## 7. Fetch Isi Artikel Lengkap

`core/article_fetcher.py` mengambil isi artikel penuh dari halaman berita
(bukan cuma cuplikan 1-2 kalimat dari RSS), supaya NER & event classifier
punya teks yang lebih kaya.

Strategi:
1. Coba CSS selector spesifik per situs (`SITE_SELECTORS`) — paling akurat.
2. Kalau situs belum terdaftar atau selector gagal match, fallback ke heuristik
   generik (ambil container dengan jumlah `<p>` terbanyak).
3. Bersihkan boilerplate (byline "Pewarta:", "Copyright ©", disclaimer,
   "Baca juga:") dari kedua jalur ekstraksi.

Ada delay 1.5 detik antar-request ke situs sumber untuk menghindari rate-limit/block.

> **Catatan:** selector khusus untuk `antaranews.com` sengaja tidak didaftarkan.
> Struktur HTML situs ini tidak match dengan selector `div.post-content.clearfix`
> yang umum dipakai, sementara fallback generik justru terbukti menghasilkan
> ekstraksi bersih dan akurat. Semua artikel Antara di sample saat ini berstatus
> `isi_teks_status: "fallback"` — ini bukan bug, melainkan keputusan desain.

---

## 8. Known Issues

- **Kompas RSS tidak aktif** per Juli 2026, dieksklusi dari daftar sumber.
- **`wilayah_terdeteksi` sebagian besar kosong** karena deteksi keyword nama kota
  di judul/summary jarang match. Ini didelegasikan ke NER (bukan scope scraper).
- **RSS Antara regional kadang mengembalikan field `link` kosong** — sudah
  ditangani dengan fallback ke field `id` di `normalizer.py`.
- **Liputan6 - News memiliki noise tinggi** (general news, bukan khusus ekonomi),
  sebagian besar entry tidak relevan dan ter-filter otomatis. Pertimbangkan
  mengganti dengan kanal ekonomi spesifik Liputan6 jika tersedia RSS-nya.

---

## 9. Untuk Role 1 (Data & Infrastructure Engineer)

File `seed_data/latest.json` adalah output yang siap dikonsumsi untuk seed
Firestore / Docker Compose (sesuai API_CONTRACT.md Bagian 6). Struktur field
`judul`, `url`, `sumber_media`, `tanggal_terbit` sudah match schema `sumber_berita`.

## 10. Untuk Role 2 (NER & Event Classifier)

Field `isi_teks` di tiap artikel adalah input utama untuk NER dan event
classifier (kategorisasi ke 7 kategori `penyebab` sesuai API_CONTRACT.md
Bagian 5.1). Perhatikan field `isi_teks_status` — kalau bernilai
`"gagal_pakai_summary_rss"`, teksnya pendek dan hasil ekstraksi entitas
mungkin kurang kaya untuk artikel tersebut.