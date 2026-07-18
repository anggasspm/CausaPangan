"""
Exception khusus.

DESAIN PENTING (wajib dikomunikasikan ke Role 1 — lihat README):
`penyebab: null` di API_CONTRACT punya makna spesifik: "tidak ada sinyal berita
relevan". Itu HARUS dibedakan dari "classifier gagal karena semua provider LLM
error/down". Kalau kedua kondisi ini disamakan jadi null begitu saja, pipeline
bisa diam-diam menulis data yang salah maknanya ke database (dianggap "memang
tidak ada penyebab" padahal sebenarnya "belum sempat diproses").

Karena itu:
- Tidak ada sinyal jelas di teks -> ClassificationResult dengan penyebab=None
  (ini SUKSES, bukan error).
- Semua provider gagal (network/quota/parse error) -> AllProvidersFailedError
  di-raise. Pipeline pemanggil (punya Role 1) WAJIB menangani ini secara
  terpisah: retry di run berikutnya / skip & log, JANGAN ditulis sebagai
  penyebab=null ke database.
"""

from __future__ import annotations


class ProviderError(Exception):
    """Satu provider LLM gagal (network, auth, quota, parse response, dll)."""

    def __init__(self, provider_name: str, original_error: Exception) -> None:
        self.provider_name = provider_name
        self.original_error = original_error
        super().__init__(f"[{provider_name}] {original_error!r}")


class AllProvidersFailedError(Exception):
    """Semua provider di fallback chain gagal untuk satu request klasifikasi."""

    def __init__(self, errors: list[ProviderError]) -> None:
        self.errors = errors
        detail = "; ".join(str(e) for e in errors)
        super().__init__(f"Semua provider LLM gagal. Detail: {detail}")
