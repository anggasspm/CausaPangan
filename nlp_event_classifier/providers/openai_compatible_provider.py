"""
Provider generik untuk endpoint yang OpenAI-compatible.

Dipakai untuk DUA provider sekaligus (Grok/xAI dan OpenRouter) karena
keduanya menerima request lewat schema chat.completions milik OpenAI —
cukup beda base_url, api_key, dan model.

Grok & OpenRouter tidak selalu strict-support `response_format:
json_schema` untuk semua model, jadi dipakai `json_object` mode (lebih luas
didukung) + instruksi schema eksplisit di system_prompt, lalu divalidasi
manual pakai pydantic di sisi kita. Kalau parse/validasi gagal -> exception,
provider berikutnya dicoba (lihat classifier.py).
"""

from __future__ import annotations

from openai import OpenAI

from ..schema import LLMClassificationOutput
from .base import LLMProvider


class OpenAICompatibleProvider(LLMProvider):
    def __init__(
        self,
        name: str,
        api_key: str,
        base_url: str,
        model: str,
        temperature: float,
    ) -> None:
        self.name = name
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model
        self._temperature = temperature

    def classify(
        self, system_prompt: str, user_prompt: str, timeout: float
    ) -> LLMClassificationOutput:
        response = self._client.chat.completions.create(
            model=self._model,
            temperature=self._temperature,
            timeout=timeout,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = response.choices[0].message.content
        if content is None:
            raise ValueError(f"[{self.name}] response content kosong")
        return LLMClassificationOutput.model_validate_json(content)
