"""Configuración centralizada leída de variables de entorno / fichero .env."""
from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # python-dotenv es opcional
    pass


@dataclass(frozen=True)
class Settings:
    database_url: str
    ocr_provider: str
    gemini_api_key: str | None
    gemini_model: str
    openai_api_key: str | None
    openai_model: str
    ocr_umbral_confianza: float
    tarifa_km_defecto: Decimal


@lru_cache
def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv("DATABASE_URL", "sqlite:///./gestion_costes.db"),
        ocr_provider=os.getenv("OCR_PROVIDER", "gemini").lower(),
        gemini_api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        ocr_umbral_confianza=float(os.getenv("OCR_UMBRAL_CONFIANZA", "0.80")),
        tarifa_km_defecto=Decimal(os.getenv("TARIFA_KM_DEFECTO", "0.26")),
    )
