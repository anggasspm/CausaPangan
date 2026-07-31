from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv(Path(__file__).resolve().parent / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL belum di-set. Copy .env.example ke .env dan isi "
        "connection string Supabase (Session Pooler), sama seperti backend/.env"
    )

if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

KOMODITAS_LIST = ["beras", "cabai_rawit_merah", "cabai_merah_keriting", "bawang_merah", "minyak_goreng"]

SATUAN_PER_KOMODITAS = {
    "beras": "Rp/kg",
    "cabai_rawit_merah": "Rp/kg",
    "cabai_merah_keriting": "Rp/kg",
    "bawang_merah": "Rp/kg",
    "minyak_goreng": "Rp/liter",
}

MIN_MONTHS_REQUIRED = 24
BACKTEST_HOLDOUT_MONTHS = 6
STABIL_THRESHOLD_PCT = 2.0 
CLASSIFIER_SIGNAL_CONFIDENCE_BOOST = 0.10