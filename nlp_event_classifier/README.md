# Event Classifier — Role 2 (NLP & ML)

Klasifikasi teks berita ke 7 kategori `penyebab` (API_CONTRACT.md §5.1), dengan
fallback 3 provider LLM: **Gemini → Grok (xAI) → OpenRouter**.

## Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # isi minimal 1 API key
```

## Pakai cepat

```python
from nlp_event_classifier.classifier import EventClassifier
from nlp_event_classifier.ingest import load_seed_articles

clf = EventClassifier()
articles = load_seed_articles("scraper/seed_data/latest.json")

for article in articles:
    result = clf.classify_article(article)
    print(article.judul, "->", result.penyebab, "|", result.penyebab_detail)
```

Atau jalankan langsung ke seluruh seed data:

```bash
python -m nlp_event_classifier.examples.run_on_seed_data \
    --input scraper/seed_data/latest.json \
    --output out/classified_latest.json
```

## Struktur

```
nlp_event_classifier/
  enums.py          # enum `penyebab` (7 kategori) — Role 2 adalah OWNER
  schema.py          # LLMClassificationOutput (raw dari LLM) & ClassificationResult
  ingest.py           # Article schema — WAJIB match scraper/seed_data/latest.json
  prompts.py         # system prompt + few-shot examples
  config.py           # kredensial & model dari env var
  exceptions.py     # ProviderError vs AllProvidersFailedError
  classifier.py       # EventClassifier — orchestrate fallback chain
  providers/
    base.py
    gemini_provider.py
    openai_compatible_provider.py  # dipakai Grok & OpenRouter
  examples/run_on_seed_data.py
```

## Keputusan desain penting

- **Null berarti "tidak ada sinyal jelas"**, bukan error. Kalau semua 3
  provider gagal (network/quota/parse), classifier raise
  `AllProvidersFailedError` — TIDAK pernah diam-diam dikembalikan sebagai
  `penyebab: null`. Ini krusial karena `penyebab: null` di API_CONTRACT
  punya makna spesifik ("tidak ada sinyal berita relevan dalam 14 hari").
  Kalau infra-fail disamakan dengan itu, data yang tersimpan salah makna.
- Field `llm_certainty` (self-assessment LLM) **BUKAN** field `confidence`
  di API_CONTRACT §3.1 — jangan tertukar. `confidence` API_CONTRACT itu
  milik hasil forecasting/time series (di luar scope modul ini).
- Filter "berita dalam 14 hari terakhir" (aturan null API_CONTRACT §4)
  **tidak** dicek di modul ini — itu keputusan yang harus diambil di level
  pipeline/orkestrasi (siapa yang decide artikel mana yang "masih relevan"
  sebelum masuk ke classifier). Lihat "Perlu dikomunikasikan" di bawah.

## ⚠️ Perlu dikomunikasikan ke tim

1. **Ke Role 1 (scraper/NER)**: `wilayah_terdeteksi` kosong di 9 dari 10
   artikel contoh (`latest.json`). Kalau ini representatif kondisi asli,
   perlu didiskusikan siapa yang menutup gap ini — karena pipeline butuh
   `kode_wilayah` untuk tahu artikel ini relevan untuk kota mana.
2. **Ke Role 1**: makna `isi_teks_status: "fallback"` (8 dari 10 artikel
   contoh) saya asumsikan = scraper gagal ambil isi lengkap, pakai
   snippet/meta-description sebagai gantinya. Classifier saat ini tetap
   memproses artikel `fallback` (dengan catatan tambahan di prompt supaya
   LLM lebih konservatif ke arah `null` kalau teksnya kelihatan terpotong).
   Perlu dikonfirmasi apakah asumsi ini benar.
3. **Ke Role 1 & Role 3 (siapapun yang bangun orchestrator/pipeline)**:
   siapa yang bertanggung jawab menerapkan aturan **"14 hari terakhir"**
   (API_CONTRACT §4) — apakah filter dilakukan sebelum artikel dikirim ke
   classifier ini, atau classifier yang perlu terima parameter tanggal
   referensi? Saat ini classifier mengasumsikan semua teks yang diterima
   sudah lolos filter relevansi waktu.
4. **Ke Role 1**: ditemukan artikel duplikat/near-duplikat di seed data
   (2 artikel "Kuningan tambah luasan tanam padi 5.671 hektare" beda URL,
   isi mirip) — perlu dedup di level scraper atau boleh diabaikan (karena
   toh diproses independen per URL)?
5. **Ke Role 1**: satu artikel bisa punya >1 `komoditas_terdeteksi`.
   Implementasi saat ini mengklasifikasi SATU KALI per artikel dan hasilnya
   dianggap berlaku untuk semua komoditas di artikel itu. Ini simplifikasi
   yang mungkin salah kalau ada artikel yang membahas penyebab berbeda
   untuk komoditas berbeda dalam satu teks — perlu didiskusikan apakah
   perlu classify per (artikel, komoditas) pair sebagai gantinya.
6. **Ke seluruh tim**: `AllProvidersFailedError` (poin desain di atas)
   perlu ditangani eksplisit oleh siapapun yang bangun scheduled job
   (GitHub Actions) — artikel yang gagal total harus di-retry/log,
   bukan silently dilewati.

## Belum sempat diuji end-to-end

Sandbox saya tidak punya akses internet untuk `pip install` maupun panggilan
API sungguhan, jadi kode ini sudah lolos `py_compile` (sintaks valid & semua
import antar-modul benar), tapi **belum saya jalankan dengan API key asli**.
Tolong jalankan `run_on_seed_data.py` di environment kamu begitu API key
sudah terisi, dan kabari kalau ada error runtime (terutama seputar SDK
`google-genai` yang APInya cukup sering berubah).
