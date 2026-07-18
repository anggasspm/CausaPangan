"""
Provider Gemini (primary).

Pakai SDK resmi `google-genai` (bukan `google-generativeai` yang lama):
    pip install google-genai

response_schema langsung diisi pydantic model kita (LLMClassificationOutput),
jadi SDK yang urus JSON schema-nya -> parsing lebih robust dibanding minta
JSON lewat instruksi teks biasa.
"""

from __future__ import annotations

from google import genai
from google.genai import types

from ..schema import LLMClassificationOutput
from .base import LLMProvider


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str, temperature: float) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._temperature = temperature

    def classify(
        self, system_prompt: str, user_prompt: str, timeout: float
    ) -> LLMClassificationOutput:
        response = self._client.models.generate_content(
            model=self._model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=self._temperature,
                response_mime_type="application/json",
                response_schema=LLMClassificationOutput,
                http_options=types.HttpOptions(timeout=int(timeout * 1000)),
            ),
        )
        # response.parsed sudah instance LLMClassificationOutput kalau schema
        # cocok; fallback ke response.text kalau SDK tidak sempat parse otomatis.
        if response.parsed is not None:
            return response.parsed  # type: ignore[return-value]
        return LLMClassificationOutput.model_validate_json(response.text)
