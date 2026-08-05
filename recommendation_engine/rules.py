"""
Recommendation engine -- pemetaan statis (penyebab + arah + confidence) -> rekomendasi
aksi spesifik per aktor. PRD §7.2: "pemetaan dari (prediksi + kategori penyebab)
menjadi rekomendasi aksi spesifik per aktor, termasuk logika null saat confidence rendah."

DEFENSE IN DEPTH: fungsi ini SENDIRI menegakkan ulang aturan null API_CONTRACT §4
(confidence < 0.5 ATAU penyebab None -> None), walau pemanggil (sync_prediksi.py)
seharusnya sudah tidak memanggil fungsi ini kalau syaratnya gak terpenuhi. Sama pola
dengan apply_null_rules() di backend/app/models.py -- berlapis, bukan percaya 1 titik saja.

CATATAN: modul ini SENGAJA tidak import apapun dari nlp_event_classifier atau
time_series_forecasting (decoupled, konsisten dengan pola integrasi lain di
project ini yang cuma nyambung lewat data terstruktur, bukan import antar modul).
"""

from __future__ import annotations

from .schema import RecommendationResult

CONFIDENCE_NULL_THRESHOLD = 0.5  # API_CONTRACT §4

# Target aktor per kategori penyebab -- siapa yang paling punya kendali untuk
# bertindak atas penyebab ini. Lihat README untuk penjelasan tiap keputusan.
_TARGET_PER_PENYEBAB: dict[str, str] = {
    "cuaca_gagal_panen": "pedagang",
    "gangguan_distribusi": "distributor",
    "penimbunan_spekulasi": "distributor",
    "kenaikan_biaya_input": "pedagang",
    "lonjakan_permintaan_musiman": "pedagang",
    "kebijakan_pemerintah": "distributor",
    "faktor_global": "distributor",
}

# Template aksi per kategori, per target, per arah. Semua teks final, tidak perlu
# isi placeholder lokasi -- dibuat generik biar berlaku ke 13 kota tanpa perlu
# nama_kota dilempar ke modul ini.
_AKSI_TEMPLATES: dict[str, dict[str, dict[str, str]]] = {
    "cuaca_gagal_panen": {
        "pedagang": {
            "naik": "Segera tambah stok sebelum harga naik lebih jauh, dan cari pemasok dari wilayah yang tidak terdampak cuaca ekstrem.",
            "turun": "Panen kembali normal, harga berpotensi turun -- tunda restock besar sampai harga stabil di titik terendah.",
            "stabil": "Kondisi cuaca masih perlu dipantau, belum ada perubahan stok signifikan yang perlu dilakukan sekarang.",
        }
    },
    "gangguan_distribusi": {
        "distributor": {
            "naik": "Alihkan rute pasokan ke sentra produksi alternatif di luar wilayah yang terdampak gangguan distribusi.",
            "turun": "Jalur distribusi mulai pulih -- evaluasi apakah rute alternatif sementara masih perlu dipertahankan.",
            "stabil": "Pantau perkembangan jalur distribusi, belum perlu perubahan rute pasokan.",
        }
    },
    "penimbunan_spekulasi": {
        "distributor": {
            "naik": "Waspadai indikasi penahanan stok di rantai pasok -- pertimbangkan sumber pasokan alternatif dan laporkan temuan mencurigakan ke pihak berwenang.",
            "turun": "Tekanan spekulasi mereda -- pasokan berpotensi kembali normal, tetap pantau perkembangan harga.",
            "stabil": "Belum ada indikasi kuat penimbunan berdampak ke harga, cukup dipantau berkala.",
        }
    },
    "kenaikan_biaya_input": {
        "pedagang": {
            "naik": "Sesuaikan harga jual secara bertahap mengikuti kenaikan biaya produksi, dan informasikan ke pelanggan tetap lebih awal.",
            "turun": "Biaya input mulai melandai -- ini peluang menjaga margin tanpa perlu menaikkan harga jual.",
            "stabil": "Biaya produksi relatif stabil, belum perlu penyesuaian harga jual.",
        }
    },
    "lonjakan_permintaan_musiman": {
        "pedagang": {
            "naik": "Tambah stok menjelang periode permintaan tinggi, dan pertimbangkan penyesuaian harga sesuai pola musiman.",
            "turun": "Permintaan musiman mulai mereda -- kurangi volume stok secara bertahap untuk menghindari kelebihan pasokan.",
            "stabil": "Belum ada lonjakan permintaan musiman signifikan yang perlu diantisipasi saat ini.",
        }
    },
    "kebijakan_pemerintah": {
        "distributor": {
            "naik": "Ikuti perkembangan kebijakan pemerintah terkait dan manfaatkan program distribusi resmi (mis. subsidi/FDP) yang tersedia untuk wilayah terdampak.",
            "turun": "Kebijakan yang berlaku berdampak menurunkan harga -- manfaatkan momentum untuk memperkuat stok dengan harga lebih rendah.",
            "stabil": "Pantau perkembangan kebijakan pemerintah, belum ada dampak signifikan ke harga saat ini.",
        }
    },
    "faktor_global": {
        "distributor": {
            "naik": "Evaluasi ulang kontrak dengan pemasok untuk komoditas impor, pertimbangkan lindung nilai (hedging) jika memungkinkan.",
            "turun": "Harga komoditas global melandai -- momentum baik untuk negosiasi ulang kontrak pasokan jangka panjang.",
            "stabil": "Fluktuasi harga global masih dalam rentang wajar, belum perlu tindakan khusus.",
        }
    },
}


def _hitung_urgensi(persentase_perubahan: float, confidence: float, arah: str) -> str:
    """
    Aturan statis (bukan ML) -- sesuai rulebook §4.2 "parameter statis saat demo".
    Threshold ini bisa didiskusikan ulang ke tim kalau hasil di lapangan kurang pas.
    """
    if arah == "stabil":
        return "rendah"

    abs_pct = abs(persentase_perubahan)
    if abs_pct >= 15 and confidence >= 0.7:
        return "tinggi"
    if abs_pct >= 5 or confidence >= 0.6:
        return "sedang"
    return "rendah"


def generate_recommendation(
    penyebab: str | None,
    arah: str,
    persentase_perubahan: float,
    confidence: float,
) -> RecommendationResult | None:
    """
    Return None kalau syarat null API_CONTRACT §4 gak terpenuhi (confidence < 0.5
    ATAU penyebab None), atau kalau penyebab-nya di luar 7 kategori yang dikenal
    (harusnya gak pernah terjadi kalau classifier jalan benar, tapi dijaga di sini
    juga -- defense in depth, bukan asumsi input selalu bersih).
    """
    if penyebab is None or confidence < CONFIDENCE_NULL_THRESHOLD:
        return None

    target = _TARGET_PER_PENYEBAB.get(penyebab)
    templates = _AKSI_TEMPLATES.get(penyebab)
    if target is None or templates is None:
        return None  # penyebab tidak dikenal -- jangan karang rekomendasi

    aksi = templates.get(target, {}).get(arah)
    if aksi is None:
        return None  # kombinasi arah tidak dikenal (harusnya cuma naik/turun/stabil)

    urgensi = _hitung_urgensi(persentase_perubahan, confidence, arah)

    return RecommendationResult(target=target, aksi=aksi, urgensi=urgensi)