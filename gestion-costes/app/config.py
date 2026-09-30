"""Configuración centralizada leída de variables de entorno / fichero .env."""
from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # python-dotenv es opcional
    pass


def directorio_datos() -> Path:
    """Carpeta escribible para la BD y las fotos de facturas.

    En el APK, Flet define FLET_APP_STORAGE_DATA (almacenamiento privado de la app);
    en PC/servidor se usa ./datos.
    """
    base = os.getenv("GESTION_DATA_DIR") or os.getenv("FLET_APP_STORAGE_DATA") or "datos"
    ruta = Path(base)
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


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

    @property
    def ocr_configurado(self) -> bool:
        return bool(self.gemini_api_key if self.ocr_provider == "gemini" else self.openai_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv("DATABASE_URL")
        or f"sqlite:///{(directorio_datos() / 'gestion_costes.db').as_posix()}",
        ocr_provider=os.getenv("OCR_PROVIDER", "gemini").lower(),
        gemini_api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        ocr_umbral_confianza=float(os.getenv("OCR_UMBRAL_CONFIANZA", "0.80")),
        tarifa_km_defecto=Decimal(os.getenv("TARIFA_KM_DEFECTO", "0.26")),
    )


def actualizar_settings(**valores: str | None) -> Settings:
    """Cambia ajustes en caliente (p.ej. la API key introducida desde la app)."""
    for clave, valor in valores.items():
        if valor:
            os.environ[clave.upper()] = valor
        else:
            os.environ.pop(clave.upper(), None)
    get_settings.cache_clear()
    return get_settings()
