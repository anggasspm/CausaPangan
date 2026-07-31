from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from .classifier_signal import load_valid_signal_set
from .config import (
    CLASSIFIER_SIGNAL_CONFIDENCE_BOOST,
    KOMODITAS_LIST,
    SATUAN_PER_KOMODITAS,
    engine,
)
from .forecaster import forecast_series

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def load_kota_list() -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT kode_wilayah, tier_data FROM wilayah")).mappings().all()
    return [dict(r) for r in rows]


def load_harga_series(kode_wilayah: str, kode_komoditas: str) -> pd.Series:
    query = text("""
        SELECT bulan, harga FROM riwayat_harga
        WHERE kode_wilayah = :kw AND kode_komoditas = :kk AND harga IS NOT NULL
        ORDER BY bulan ASC
    """)
    with engine.connect() as conn:
        rows = conn.execute(query, {"kw": kode_wilayah, "kk": kode_komoditas}).fetchall()
    if not rows:
        return pd.Series(dtype=float)
    df = pd.DataFrame(rows, columns=["bulan", "harga"])
    df["bulan"] = pd.to_datetime(df["bulan"])
    df["harga"] = pd.to_numeric(df["harga"], errors="coerce")   # <-- BARIS BARU: paksa Decimal -> float64
    return df.set_index("bulan")["harga"].asfreq("MS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/hasil_forecasting/latest.json")
    args = parser.parse_args()

    kota_list = load_kota_list()
    signal_set = load_valid_signal_set()
    logger.info(
        "Memuat %d kota, %d kombinasi kota x komoditas punya sinyal berita valid.",
        len(kota_list), len(signal_set),
    )

    results = []
    for kota in kota_list:
        for kode_komoditas in KOMODITAS_LIST:
            series = load_harga_series(kota["kode_wilayah"], kode_komoditas)
            if series.empty:
                logger.warning(
                    "Tidak ada data riwayat_harga untuk %s x %s, dilewati.",
                    kota["kode_wilayah"], kode_komoditas,
                )
                continue

            result = forecast_series(
                kode_wilayah=kota["kode_wilayah"],
                kode_komoditas=kode_komoditas,
                tier_data=kota["tier_data"],
                satuan=SATUAN_PER_KOMODITAS[kode_komoditas],
                harga_bulanan=series,
            )

            if (kota["kode_wilayah"], kode_komoditas) in signal_set:
                result.confidence = min(0.95, result.confidence + CLASSIFIER_SIGNAL_CONFIDENCE_BOOST)
                result.catatan = f"{result.catatan or ''} (confidence di-boost, ada sinyal berita valid)".strip()

            results.append(result.model_dump())
            logger.info(
                "%s x %s -> %s (%.2f%%, conf=%.2f, %s)",
                kota["kode_wilayah"], kode_komoditas, result.arah,
                result.persentase_perubahan, result.confidence, result.metode,
            )

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Selesai. %d hasil forecasting ditulis ke %s", len(results), out_path)


if __name__ == "__main__":
    main()