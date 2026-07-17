"""
Model data sesuai API_CONTRACT.md v1.0.

PENTING: enum `Penyebab` dimiliki Role NLP & ML (Role 2). Kalau ada
perubahan/penambahan value, WAJIB update API_CONTRACT.md dulu sebelum
ubah di sini (lihat API_CONTRACT §5.1 dan §7).
"""
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enum tetap (API_CONTRACT §5)
# ---------------------------------------------------------------------------

class Penyebab(str, Enum):
    cuaca_gagal_panen = "cuaca_gagal_panen"
    gangguan_distribusi = "gangguan_distribusi"
    penimbunan_spekulasi = "penimbunan_spekulasi"
    kenaikan_biaya_input = "kenaikan_biaya_input"
    lonjakan_permintaan_musiman = "lonjakan_permintaan_musiman"
    kebijakan_pemerintah = "kebijakan_pemerintah"
    faktor_global = "faktor_global"


class RekomendasiTarget(str, Enum):
    distributor = "distributor"
    pedagang = "pedagang"


class Urgensi(str, Enum):
    rendah = "rendah"
    sedang = "sedang"
    tinggi = "tinggi"


class Arah(str, Enum):
    naik = "naik"
    turun = "turun"
    stabil = "stabil"


class TierData(str, Enum):
    solid = "solid"
    estimasi = "estimasi"


# ---------------------------------------------------------------------------
# Sub-objek
# ---------------------------------------------------------------------------

class SumberBerita(BaseModel):
    judul: str
    url: str
    sumber_media: str
    tanggal_terbit: str  # ISO 8601 UTC


class Rekomendasi(BaseModel):
    target: RekomendasiTarget
    aksi: str
    urgensi: Urgensi


# ---------------------------------------------------------------------------
# Response utama
# ---------------------------------------------------------------------------

class Wilayah(BaseModel):
    kode_wilayah: str
    nama_kota: str
    kode_provinsi: str
    nama_provinsi: str


class PrediksiDetail(BaseModel):
    """GET /api/v1/prediksi — API_CONTRACT §3.1"""
    kode_wilayah: str
    nama_kota: str
    kode_provinsi: str
    nama_provinsi: str
    kode_komoditas: str
    nama_komoditas: str
    harga_terakhir: int
    satuan: str
    persentase_perubahan: float
    arah: Arah
    confidence: float = Field(ge=0, le=1)
    tier_data: TierData
    penyebab: Optional[Penyebab] = None
    penyebab_detail: Optional[str] = None
    rekomendasi: Optional[Rekomendasi] = None
    sumber_berita: List[SumberBerita] = Field(default_factory=list)
    terakhir_diperbarui: str  # ISO 8601 UTC


class PrediksiRingkasan(BaseModel):
    """GET /api/v1/prediksi/ringkasan — API_CONTRACT §3.2 (payload ringan)"""
    kode_wilayah: str
    kode_komoditas: str
    persentase_perubahan: float
    arah: Arah
    confidence: float = Field(ge=0, le=1)
    tier_data: TierData


def apply_null_rules(record: dict) -> dict:
    """
    Menegakkan aturan null API_CONTRACT §4, terlepas dari apa yang ada
    di storage. Ini jaring pengaman terakhir sebelum data keluar lewat API
    — supaya kalau ada bug di pipeline Role 2 (mis. lupa null-kan
    rekomendasi saat confidence rendah), response tetap patuh kontrak.

    Aturan:
    - rekomendasi WAJIB null (seluruh objek) jika confidence < 0.5 ATAU
      penyebab null.
    - penyebab_detail WAJIB null jika penyebab null.
    - sumber_berita WAJIB [] jika penyebab null (tidak pernah null).
    """
    record = dict(record)
    penyebab_null = record.get("penyebab") is None
    confidence = record.get("confidence", 0)

    if penyebab_null:
        record["penyebab_detail"] = None
        record["sumber_berita"] = []

    if confidence < 0.5 or penyebab_null:
        record["rekomendasi"] = None

    if record.get("sumber_berita") is None:
        record["sumber_berita"] = []

    return record