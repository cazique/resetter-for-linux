"""Configuración por entornos (Development / Production / Testing).

Todos los valores sensibles se leen de variables de entorno (ver `.env.example`).
"""
from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR: Path = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _int_env(name: str, default: int) -> int:
    """Lee un entero de entorno con valor por defecto seguro."""
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _list_env(name: str, default: str = "") -> list[str]:
    """Lee una lista separada por comas, descartando elementos vacíos."""
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


class BaseConfig:
    """Configuración común a todos los entornos."""

    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-key")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=_int_env("JWT_ACCESS_TOKEN_EXPIRES", 900))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(seconds=_int_env("JWT_REFRESH_TOKEN_EXPIRES", 2_592_000))
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_ERROR_MESSAGE_KEY = "message"

    SQLALCHEMY_DATABASE_URI: str = os.getenv(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'dev.sqlite3'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # Subida de ficheros
    UPLOAD_FOLDER: str = str((BASE_DIR / os.getenv("UPLOAD_FOLDER", "uploads")).resolve())
    MAX_CONTENT_LENGTH: int = _int_env("MAX_CONTENT_LENGTH_MB", 15) * 1024 * 1024
    ALLOWED_IMAGE_EXTENSIONS: frozenset[str] = frozenset({"jpg", "jpeg", "png"})
    ALLOWED_IMAGE_FORMATS: frozenset[str] = frozenset({"JPEG", "PNG"})
    THUMBNAIL_SIZE: int = 300

    # CORS: la app Android nativa no envía cabecera Origin, pero se restringe
    # igualmente para clientes web/emuladores que sí la envían.
    CORS_ORIGINS: list[str] = _list_env("CORS_ORIGINS", "http://localhost:3000")

    # Paginación
    DEFAULT_PER_PAGE: int = 20
    MAX_PER_PAGE: int = 100

    # Informe PDF
    COMPANY_NAME: str = os.getenv("COMPANY_NAME", "Gestor Documental")
    COMPANY_LOGO_PATH: str = os.getenv("COMPANY_LOGO_PATH", "")

    JSON_SORT_KEYS = False


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS: dict = {}


class ProductionConfig(BaseConfig):
    DEBUG = False

    @classmethod
    def validate(cls) -> None:
        """Impide arrancar en producción con secretos por defecto o sin PostgreSQL."""
        insecure = {"dev-secret-key", "dev-jwt-secret-key", "change-me", "change-me-too"}
        if cls.SECRET_KEY in insecure or cls.JWT_SECRET_KEY in insecure:
            raise RuntimeError("SECRET_KEY/JWT_SECRET_KEY deben definirse en producción.")
        if not os.getenv("DATABASE_URL"):
            raise RuntimeError("DATABASE_URL (PostgreSQL) es obligatoria en producción.")


CONFIG_BY_NAME: dict[str, type[BaseConfig]] = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
