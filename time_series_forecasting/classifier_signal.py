from __future__ import annotations

import json
from pathlib import Path


def load_valid_signal_set(path: str | Path = "data/hasil_klasifikasi/latest.json") -> set[tuple[str, str]]:
    p = Path(path)
    if not p.exists():
        return set()

    articles = json.loads(p.read_text(encoding="utf-8"))
    signal_set: set[tuple[str, str]] = set()
    for art in articles:
        if not art.get("penyebab"):
            continue
        for kw in art.get("wilayah_terdeteksi") or []:
            for kk in art.get("komoditas_terdeteksi") or []:
                signal_set.add((kw, kk))
    return signal_set