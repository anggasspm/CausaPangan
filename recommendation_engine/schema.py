"""Skema output recommendation engine -- subset field `rekomendasi` di API_CONTRACT §3.1."""

from __future__ import annotations

from pydantic import BaseModel


class RecommendationResult(BaseModel):
    target: str  # "distributor" | "pedagang" -- API_CONTRACT §5.2
    aksi: str
    urgensi: str  # "tinggi" | "sedang" | "rendah" -- sesuai models.py Urgensi enum