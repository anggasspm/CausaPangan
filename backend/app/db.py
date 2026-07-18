"""
Koneksi database. DATABASE_URL diambil dari environment variable
(diisi lewat .env lokal, atau env var asli di Render saat deploy).
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL belum di-set. Copy .env.example ke .env dan isi "
        "connection string dari Supabase Project Settings > Database."
    )

# Supabase kasih connection string dengan skema "postgresql://" (default psycopg2).
# Kita pakai driver psycopg (v3) supaya install lebih robust di Windows -- perlu
# skema "postgresql+psycopg://" biar SQLAlchemy pilih driver yang benar.
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()