"""
Serving layer -- 4 endpoint sesuai API_CONTRACT.md §2.

Sengaja TIDAK error kalau tabel `prediksi` masih kosong (Role 2 belum
selesai) -- endpoint tetap merespons normal dengan list kosong, supaya
Role 3 (Frontend) bisa mulai integrasi sekarang juga tanpa nunggu.
"""
from typing import Optional
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import store
from .db import SessionLocal
from .models import Wilayah, PrediksiDetail, PrediksiRingkasan, apply_null_rules

app = FastAPI(
    title="API Peringatan Dini & Rekomendasi Aksi Harga Pangan",
    version="1.1",
)

# CORS terbuka untuk dev -- persempit ke domain Render/frontend asli saat production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/api/v1/wilayah", response_model=list[Wilayah])
def get_wilayah():
    db = SessionLocal()
    try:
        return store.list_wilayah(db)
    finally:
        db.close()


@app.get("/api/v1/prediksi")
def get_prediksi(
    kota: str = Query(..., description="kode_wilayah, wajib"),
    komoditas: Optional[str] = Query(None, description="kode_komoditas, opsional"),
):
    db = SessionLocal()
    try:
        rows = store.list_prediksi(db, kota, komoditas)
        # tegakkan aturan null §4 di sini, jaring pengaman terakhir
        return [PrediksiDetail(**apply_null_rules(r)) for r in rows]
    finally:
        db.close()


@app.get("/api/v1/prediksi/ringkasan", response_model=list[PrediksiRingkasan])
def get_ringkasan():
    db = SessionLocal()
    try:
        return store.list_ringkasan(db)
    finally:
        db.close()


@app.get("/health")
def health():
    """Bukan bagian API_CONTRACT -- dipakai internal buat cek container/deploy hidup."""
    return {"status": "ok"}