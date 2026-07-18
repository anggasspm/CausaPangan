"""
Skema input artikel — WAJIB match persis dengan output scraper Role 1
(`scraper/seed_data/latest.json`).

Kalau Role 1 mengubah struktur file ini (nama field, tipe, dsb), Article di
bawah akan gagal validasi saat load -> itu sengaja, supaya ketahuan cepat
alih-alih silent bug di tengah pipeline. Kalau terjadi, WAJIB dikomunikasikan
dua arah (bukan cuma Role 2 yang nyesuaikan diam-diam), karena field yang
sama (judul/url/sumber_media/tanggal_terbit) juga dipakai untuk membangun
`sumber_berita` di response API sesuai API_CONTRACT.md §3.1.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, TypeAdapter


class Article(BaseModel):
    judul: str
    url: str
    sumber_media: str
    tanggal_terbit: datetime
    isi_teks: str
    komoditas_terdeteksi: list[str] = []
    wilayah_terdeteksi: list[str] = []  # kode kabupaten/kota Kemendagri
    isi_teks_status: Literal["ok", "fallback", "gagal_pakai_summary_rss"]


_ArticleList = TypeAdapter(list[Article])


def load_seed_articles(path: str | Path) -> list[Article]:
    raw = Path(path).read_text(encoding="utf-8")
    return _ArticleList.validate_python(json.loads(raw))
