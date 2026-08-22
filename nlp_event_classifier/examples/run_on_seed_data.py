"""
Jalankan event classifier di atas scraper/seed_data/latest.json.

Usage:
    python -m nlp_event_classifier.examples.run_on_seed_data \
        --input scraper/seed_data/latest.json \
        --output out/classified_latest.json

Butuh minimal satu API key terisi di .env (GEMINI_API_KEY / XAI_API_KEY /
OPENROUTER_API_KEY).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from nlp_event_classifier.classifier import EventClassifier
from nlp_event_classifier.exceptions import AllProvidersFailedError
from nlp_event_classifier.ingest import load_seed_articles

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

def load_existing_results(path: Path) -> dict[str, dict]:
    """url -> record hasil klasifikasi run-run sebelumnya, buat di-skip."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return {r["url"]: r for r in data if r.get("url")}

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="scraper/seed_data/latest.json")
    parser.add_argument("--output", default="data/hasil_klasifikasi/latest.json")
    parser.add_argument(
        "--max-per-run", type=int, default=150,
        help="Batas artikel BARU yang diproses per run, biar gak timeout CI. "
             "Sisa backlog otomatis kekejar di run berikutnya (tiap 6 jam).",
    )
    args = parser.parse_args()

    out_path = Path(args.output)
    existing = load_existing_results(out_path)

    clf = EventClassifier()
    articles = load_seed_articles(args.input)

    new_articles = [a for a in articles if not a.url or a.url not in existing]
    to_process = new_articles[: args.max_per_run]
    remaining = len(new_articles) - len(to_process)

    logger.info(
        "Total %d artikel, %d sudah pernah diklasifikasi (skip), %d baru "
        "(diproses %d, sisa %d dikejar run berikutnya).",
        len(articles), len(articles) - len(new_articles), len(new_articles),
        len(to_process), remaining,
    )

    results = list(existing.values())
    n_failed = 0
    for i, article in enumerate(to_process, start=1):
        logger.info("[%d/%d baru] %s", i, len(to_process), article.judul[:60])
        try:
            result = clf.classify_article(article)
        except AllProvidersFailedError as e:
            logger.error("Gagal klasifikasi (semua provider error): %s", e)
            n_failed += 1
            continue

        results.append({
            "url": article.url,
            "judul": article.judul,
            "sumber_media": article.sumber_media,
            "tanggal_terbit": article.tanggal_terbit.isoformat(),
            "komoditas_terdeteksi": article.komoditas_terdeteksi,
            "wilayah_terdeteksi": article.wilayah_terdeteksi,
            "penyebab": result.penyebab.value if result.penyebab else None,
            "penyebab_detail": result.penyebab_detail,
            "llm_certainty": result.llm_certainty,
            "provider_used": result.provider_used,
            "model_used": result.model_used,
        })

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    logger.info("Selesai. %d total record tersimpan (termasuk yang lama).", len(results))

    if len(to_process) > 0 and n_failed == len(to_process):
        logger.error("Semua %d artikel baru gagal diklasifikasi. Menandai job sebagai gagal.", n_failed)
        sys.exit(1)
    if n_failed > 0:
        logger.warning(
            "%d dari %d artikel baru gagal (infra-fail per-artikel), akan di-retry run berikutnya.",
            n_failed, len(to_process),
        )


if __name__ == "__main__":
    main()
