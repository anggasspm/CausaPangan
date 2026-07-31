from __future__ import annotations

from pydantic import BaseModel, Field


class ForecastResult(BaseModel):
    kode_wilayah: str
    kode_komoditas: str
    harga_terakhir: float
    satuan: str 
    persentase_perubahan: float
    arah: str
    confidence: float = Field(ge=0.0, le=1.0)
    tier_data: str  
    metode: str  
    catatan: str | None = None  