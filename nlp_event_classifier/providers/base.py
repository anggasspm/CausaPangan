"""Interface umum yang wajib diimplementasikan tiap provider LLM."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..schema import LLMClassificationOutput


class LLMProvider(ABC):
    name: str

    @abstractmethod
    def classify(
        self, system_prompt: str, user_prompt: str, timeout: float
    ) -> LLMClassificationOutput:
        """
        Panggil LLM dan kembalikan output yang SUDAH tervalidasi sebagai
        LLMClassificationOutput.

        Wajib raise Exception apapun (network error, timeout, JSON tidak valid,
        pydantic ValidationError, dll) jika gagal — jangan menelan error dan
        mengembalikan nilai default. Pemanggil (classifier.py) yang bertanggung
        jawab membungkusnya jadi ProviderError dan mencoba provider berikutnya.
        """
        raise NotImplementedError
