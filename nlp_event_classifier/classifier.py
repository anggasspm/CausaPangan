"""
EventClassifier — entry point utama modul ini.

Contoh pakai:
    from nlp_event_classifier.classifier import EventClassifier
    from nlp_event_classifier.ingest import load_seed_articles

    clf = EventClassifier()
    articles = load_seed_articles("scraper/seed_data/latest.json")
    for article in articles:
        result = clf.classify_article(article)
        print(result)
"""

from __future__ import annotations

import logging
import time

from .config import ClassifierConfig
from .exceptions import AllProvidersFailedError, ProviderError
from .ingest import Article
from .prompts import build_system_prompt, build_user_prompt
from .providers.base import LLMProvider
from .providers.gemini_provider import GeminiProvider
from .providers.openai_compatible_provider import OpenAICompatibleProvider
from .schema import ClassificationResult, LLMClassificationOutput

logger = logging.getLogger("nlp_event_classifier")


class EventClassifier:
    def __init__(self, config: ClassifierConfig | None = None) -> None:
        self.config = config or ClassifierConfig()
        self._system_prompt = build_system_prompt()
        self._providers = self._build_provider_chain()

        if not self._providers:
            raise RuntimeError(
                "Tidak ada provider LLM yang terkonfigurasi. Set minimal salah "
                "satu dari GEMINI_API_KEY, XAI_API_KEY, OPENROUTER_API_KEY di "
                "environment / file .env."
            )

    def _build_provider_chain(self) -> list[LLMProvider]:
        chain: list[LLMProvider] = []
        c = self.config

        if c.gemini_api_key:
            chain.append(
                GeminiProvider(
                    api_key=c.gemini_api_key,
                    model=c.gemini_model,
                    temperature=c.temperature,
                )
            )
        if c.grok_api_key:
            chain.append(
                OpenAICompatibleProvider(
                    name="grok",
                    api_key=c.grok_api_key,
                    base_url=c.grok_base_url,
                    model=c.grok_model,
                    temperature=c.temperature,
                )
            )
        if c.openrouter_api_key:
            chain.append(
                OpenAICompatibleProvider(
                    name="openrouter",
                    api_key=c.openrouter_api_key,
                    base_url=c.openrouter_base_url,
                    model=c.openrouter_model,
                    temperature=c.temperature,
                )
            )

        missing = [
            n
            for n, k in [
                ("gemini", c.gemini_api_key),
                ("grok", c.grok_api_key),
                ("openrouter", c.openrouter_api_key),
            ]
            if not k
        ]
        if missing:
            logger.warning(
                "Provider tanpa API key (dilewati dari fallback chain): %s",
                ", ".join(missing),
            )
        return chain

    def classify_article(self, article: Article) -> ClassificationResult:
        """Klasifikasi satu Article (format latest.json)."""
        user_prompt = build_user_prompt(
            judul=article.judul,
            isi_teks=article.isi_teks,
            komoditas_hint=article.komoditas_terdeteksi,
            isi_teks_status=article.isi_teks_status,
        )
        return self._classify_text(user_prompt, excerpt=article.isi_teks[:200])

    def classify_raw_text(self, judul: str, isi_teks: str) -> ClassificationResult:
        """Klasifikasi teks bebas (di luar format Article), mis. untuk testing manual."""
        user_prompt = build_user_prompt(judul=judul, isi_teks=isi_teks)
        return self._classify_text(user_prompt, excerpt=isi_teks[:200])

    def _classify_text(self, user_prompt: str, excerpt: str) -> ClassificationResult:
        errors: list[ProviderError] = []

        for provider in self._providers:
            last_error: ProviderError | None = None
            for attempt in range(1, self.config.max_retries_per_provider + 1):
                try:
                    llm_output: LLMClassificationOutput = provider.classify(
                        system_prompt=self._system_prompt,
                        user_prompt=user_prompt,
                        timeout=self.config.request_timeout_seconds,
                    )
                    return ClassificationResult(
                        penyebab=llm_output.penyebab,
                        penyebab_detail=llm_output.penyebab_detail,
                        llm_certainty=llm_output.llm_certainty,
                        provider_used=provider.name,
                        model_used=self._model_name_of(provider),
                        raw_article_excerpt=excerpt,
                    )
                except Exception as exc:  # noqa: BLE001 - sengaja luas, lihat base.py
                    is_rate_limit = "429" in str(exc) or "RESOURCE_EXHAUSTED" in str(exc)
                    logger.warning(
                        "Provider %s gagal (percobaan %d/%d): %r",
                        provider.name,
                        attempt,
                        self.config.max_retries_per_provider,
                        exc,
                    )
                    last_error = ProviderError(provider.name, exc)
                    if is_rate_limit:
                        break  # rate limit -> langsung pindah provider, retry di sini percuma
                    if attempt < self.config.max_retries_per_provider:
                        time.sleep(1.5 * attempt)
            if last_error is not None:
                errors.append(last_error)
            logger.info("Pindah ke provider berikutnya setelah %s gagal total.", provider.name)

        # Semua provider gagal -> JANGAN diam-diam dianggap "penyebab: null".
        # Lihat exceptions.py untuk alasan lengkap.
        raise AllProvidersFailedError(errors)

    @staticmethod
    def _model_name_of(provider: LLMProvider) -> str:
        return getattr(provider, "_model", "unknown")
