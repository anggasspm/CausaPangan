from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass


@dataclass
class ClassifierConfig:
    # --- Gemini ---
    gemini_api_key: str | None = field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY")
    )
    # Alias "-latest" sengaja dipakai (bukan versi spesifik) supaya otomatis
    # ikut model stable terbaru dari Google tanpa perlu update kode tiap rilis.
    # Override lewat env var kalau tim mau pin ke versi tertentu.
    gemini_model: str = field(
        default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-flash-latest")
    )

    # --- Grok (xAI) — OpenAI-compatible endpoint ---
    grok_api_key: str | None = field(default_factory=lambda: os.getenv("XAI_API_KEY"))
    grok_base_url: str = "https://api.x.ai/v1"
    grok_model: str = field(
        default_factory=lambda: os.getenv("GROK_MODEL", "grok-4-1-fast-non-reasoning")
    )

    # --- OpenRouter — OpenAI-compatible endpoint, banyak model tersedia ---
    openrouter_api_key: str | None = field(
        default_factory=lambda: os.getenv("OPENROUTER_API_KEY")
    )
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    # PENTING: cek model yang tersedia & harganya di openrouter.ai/models
    # sebelum submit — default di bawah ini bisa berubah ketersediaannya.
    openrouter_model: str = field(
        default_factory=lambda: os.getenv(
            "OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free"
        )
    )

    # --- Perilaku umum ---
    request_timeout_seconds: float = 30.0
    max_retries_per_provider: int = 2  # percobaan ulang SEBELUM pindah ke provider berikutnya
    temperature: float = 0.1  # rendah -> output lebih konsisten untuk klasifikasi

    def configured_providers(self) -> list[str]:
        """Provider mana saja yang API key-nya tersedia, sesuai urutan fallback."""
        available = []
        if self.gemini_api_key:
            available.append("gemini")
        if self.grok_api_key:
            available.append("grok")
        if self.openrouter_api_key:
            available.append("openrouter")
        return available
