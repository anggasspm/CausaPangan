# Recommendation Engine

Pure mapping function, TANPA database/API eksternal -- sesuai PRD §7.2 &
rulebook §4.2 (parameter statis saat demo).

## Cara pakai (oleh Role 1, di dalam sync_prediksi.py)

```python
from recommendation_engine import generate_recommendation

rekomendasi = generate_recommendation(
    penyebab=penyebab,                          # dari classifier, bisa None
    arah=forecast["arah"],                       # dari forecasting
    persentase_perubahan=forecast["persentase_perubahan"],
    confidence=forecast["confidence"],
)

# rekomendasi is None -> tulis NULL, NULL, NULL ke kolom rekomendasi_*
# rekomendasi is RecommendationResult -> tulis rekomendasi.target, .aksi, .urgensi
```

## Keputusan desain: 1 target per kategori penyebab
Tabel `prediksi` cuma punya 1 kolom `rekomendasi_target` (bukan array), jadi
tiap kategori penyebab di-assign SATU target aktor default berdasarkan siapa
paling punya kendali untuk bertindak:
- distributor: gangguan_distribusi, penimbunan_spekulasi, kebijakan_pemerintah, faktor_global
- pedagang: cuaca_gagal_panen, kenaikan_biaya_input, lonjakan_permintaan_musiman

Ini keputusan yang bisa didebat -- kalau tim/mentor punya pandangan beda,
gampang diubah di `_TARGET_PER_PENYEBAB`.