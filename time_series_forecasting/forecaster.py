from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from .config import BACKTEST_HOLDOUT_MONTHS, MIN_MONTHS_REQUIRED, STABIL_THRESHOLD_PCT
from .schema import ForecastResult

warnings.filterwarnings("ignore", category=UserWarning, module="statsmodels")
warnings.filterwarnings("ignore", category=FutureWarning, module="statsmodels")

def _arah_dari_pct(pct: float) -> str:
    if abs(pct) <= STABIL_THRESHOLD_PCT:
        return "stabil"
    return "naik" if pct > 0 else "turun"


def _mape(actual: np.ndarray, forecast: np.ndarray) -> float:
    actual = np.asarray(actual, dtype=float)
    forecast = np.asarray(forecast, dtype=float)
    mask = actual != 0
    if not mask.any():
        return 1.0  # tidak bisa dihitung -> anggap error 100%, confidence rendah
    return float(np.mean(np.abs((actual[mask] - forecast[mask]) / actual[mask])))


def _confidence_from_mape(mape: float) -> float:
    conf = 0.95 - (mape / 0.40) * 0.85
    return float(np.clip(conf, 0.1, 0.95))


def _fit_holt_winters(series: pd.Series, seasonal_periods: int = 12) -> ExponentialSmoothing:
    return ExponentialSmoothing(
        series,
        trend="add",
        seasonal="add" if len(series) >= 2 * seasonal_periods else None,
        seasonal_periods=seasonal_periods if len(series) >= 2 * seasonal_periods else None,
        initialization_method="estimated",
    ).fit(optimized=True)


def forecast_series(
    kode_wilayah: str,
    kode_komoditas: str,
    tier_data: str,
    satuan: str,
    harga_bulanan: pd.Series,  # index = periode bulanan (datetime), value = harga, urut naik
) -> ForecastResult:
    harga_bulanan = harga_bulanan.dropna()
    n = len(harga_bulanan)
    harga_terakhir = float(harga_bulanan.iloc[-1])

    if n < MIN_MONTHS_REQUIRED:
        if n >= 2:
            pct = round((harga_terakhir - float(harga_bulanan.iloc[-2])) / float(harga_bulanan.iloc[-2]) * 100, 2)
        else:
            pct = 0.0
        return ForecastResult(
            kode_wilayah=kode_wilayah,
            kode_komoditas=kode_komoditas,
            harga_terakhir=harga_terakhir,
            satuan=satuan,
            persentase_perubahan=pct,
            arah=_arah_dari_pct(pct),
            confidence=0.2,
            tier_data=tier_data,
            metode="naive_fallback",
            catatan=f"Data historis cuma {n} bulan (< {MIN_MONTHS_REQUIRED}), Holt-Winters butuh lebih banyak.",
        )

    try:
        train = harga_bulanan.iloc[:-BACKTEST_HOLDOUT_MONTHS]
        test = harga_bulanan.iloc[-BACKTEST_HOLDOUT_MONTHS:]
        model_bt = _fit_holt_winters(train)
        forecast_bt = model_bt.forecast(len(test))
        mape = _mape(test.values, forecast_bt.values)
        confidence = _confidence_from_mape(mape)

        model_full = _fit_holt_winters(harga_bulanan)
        forecast_next = float(model_full.forecast(1).iloc[0])

        pct = round((forecast_next - harga_terakhir) / harga_terakhir * 100, 2)
        return ForecastResult(
            kode_wilayah=kode_wilayah,
            kode_komoditas=kode_komoditas,
            harga_terakhir=harga_terakhir,
            satuan=satuan,
            persentase_perubahan=pct,
            arah=_arah_dari_pct(pct),
            confidence=confidence,
            tier_data=tier_data,
            metode="holt_winters",
            catatan=f"Backtest MAPE {mape:.1%} atas {BACKTEST_HOLDOUT_MONTHS} bulan terakhir.",
        )
    except Exception as exc:  # noqa: BLE001
        return ForecastResult(
            kode_wilayah=kode_wilayah,
            kode_komoditas=kode_komoditas,
            harga_terakhir=harga_terakhir,
            satuan=satuan,
            persentase_perubahan=0.0,
            arah="stabil",
            confidence=0.15,
            tier_data=tier_data,
            metode="naive_fallback",
            catatan=f"Holt-Winters gagal fit: {exc!r}",
        )