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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="scraper/seed_data/latest.json")
    parser.add_argument("--output", default="out/classified_latest.json")
    args = parser.parse_args()

    clf = EventClassifier()
    articles = load_seed_articles(args.input)
    logger.info("Memuat %d artikel dari %s", len(articles), args.input)

    results = []
    n_failed = 0
    for i, article in enumerate(articles, start=1):
        logger.info("[%d/%d] %s", i, len(articles), article.judul[:60])
        try:
            result = clf.classify_article(article)
        except AllProvidersFailedError as e:
            # PENTING: ini kegagalan infra (bukan "tidak ada penyebab").
            # Di pipeline produksi nanti, artikel ini harus di-retry di run
            # berikutnya, BUKAN ditulis sebagai penyebab=null ke database.
            logger.error("Gagal klasifikasi (semua provider error): %s", e)
            n_failed += 1
            continue

        results.append(
            {
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
            }
        )

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    logger.info(
        "Selesai. %d berhasil diklasifikasi, %d gagal (infra). Output: %s",
        len(results),
        n_failed,
        out_path,
    )
    if len(articles) > 0 and n_failed == len(articles):
        logger.error(
            "Semua %d artikel gagal diklasifikasi (kemungkinan semua provider "
            "LLM down/quota habis). Menandai job sebagai gagal.",
            n_failed,
        )
        sys.exit(1)

    if n_failed > 0:
        logger.warning(
            "%d dari %d artikel gagal diklasifikasi (infra-fail per-artikel). "
            "Artikel ini TIDAK ditulis sebagai penyebab=null -- perlu di-retry "
            "run berikutnya.",
            n_failed,
            len(articles),
        )


if __name__ == "__main__":
    main()
