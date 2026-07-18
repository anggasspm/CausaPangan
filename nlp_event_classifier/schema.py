"""
Skema data classifier.

`LLMClassificationOutput` = bentuk mentah yang diminta dari LLM (dipakai sebagai
response_schema/structured output).

`ClassificationResult` = hasil akhir setelah divalidasi ulang di sisi kita
(defense-in-depth terhadap LLM yang tidak strict), plus metadata provider.

CATATAN PENTING soal field `confidence`:
Field `confidence` di API_CONTRACT.md §3.1 adalah confidence untuk PREDIKSI HARGA
SECARA KESELURUHAN (dimiliki hasil forecasting/time series, bukan output
classifier ini). Classifier ini TIDAK mengisi field `confidence` tsb.
`llm_certainty` di bawah ini murni internal (self-assessment dari LLM, untuk
logging/silver-label quality saja) — jangan sampai tertukar/ikut dikirim
sebagai field `confidence` pada response API.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from .enums import Penyebab


class LLMClassificationOutput(BaseModel):
    """Bentuk JSON yang WAJIB dikembalikan oleh LLM (structured output)."""

    penyebab: Penyebab | None = Field(
        default=None,
        description=(
            "Salah satu dari 7 kategori enum, atau null jika teks berita TIDAK "
            "secara jelas menunjukkan satu kategori penyebab spesifik."
        ),
    )
    penyebab_detail: str | None = Field(
        default=None,
        description=(
            "Penjelasan singkat (1 kalimat, Bahasa Indonesia, maks ~200 karakter) "
            "kenapa kategori tsb dipilih, mengambil konteks langsung dari teks. "
            "Wajib null jika `penyebab` null."
        ),
        max_length=500,
    )
    llm_certainty: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Self-assessment internal LLM soal seberapa eksplisit/jelas sinyal "
            "dalam teks (0=sangat ambigu, 1=sangat eksplisit). BUKAN field "
            "`confidence` di API_CONTRACT — field ini murni untuk logging & "
            "silver-label quality filtering di sisi kita."
        ),
    )

    @model_validator(mode="after")
    def _enforce_null_pairing(self) -> "LLMClassificationOutput":
        # Defense-in-depth: paksa konsistensi sesuai API_CONTRACT.md §4,
        # walau seharusnya LLM sudah mengikuti instruksi prompt.
        if self.penyebab is None and self.penyebab_detail is not None:
            self.penyebab_detail = None
        return self


class ClassificationResult(BaseModel):
    """Hasil akhir yang dipakai pipeline (bukan langsung field API response)."""

    penyebab: Penyebab | None
    penyebab_detail: str | None
    llm_certainty: float
    provider_used: str
    model_used: str
    raw_article_excerpt: str = Field(
        description="200 karakter pertama teks input, untuk keperluan audit/log."
    )

    @model_validator(mode="after")
    def _enforce_null_pairing(self) -> "ClassificationResult":
        if self.penyebab is None and self.penyebab_detail is not None:
            self.penyebab_detail = None
        return self
