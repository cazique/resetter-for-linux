"""Application factory."""
from __future__ import annotations

import logging
import os
from pathlib import Path

import click
from flask import Flask
from flask.wrappers import Response

from .config import CONFIG_BY_NAME, ProductionConfig
from .extensions import cors, db, jwt, migrate


def create_app(config_name: str | None = None) -> Flask:
    config_name = config_name or os.getenv("FLASK_ENV", "development")
    config_cls = CONFIG_BY_NAME.get(config_name)
    if config_cls is None:
        raise ValueError(f"Entorno de configuración desconocido: {config_name}")
    if config_cls is ProductionConfig:
        ProductionConfig.validate()

    app = Flask(__name__)
    app.config.from_object(config_cls)
    _configure_logging(app)
    _ensure_upload_dirs(app)

    # Extensiones
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
        expose_headers=["Content-Disposition"],
        supports_credentials=False,
    )
    _register_jwt_callbacks()

    from . import models  # noqa: F401  (registra modelos para Flask-Migrate)
    from .routes import register_blueprints, register_error_handlers

    register_blueprints(app)
    register_error_handlers(app)
    _register_cli(app)
    return app


def _configure_logging(app: Flask) -> None:
    level = logging.DEBUG if app.debug else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")


def _ensure_upload_dirs(app: Flask) -> None:
    root = Path(app.config["UPLOAD_FOLDER"])
    for sub in ("images", "pdfs"):
        (root / sub).mkdir(parents=True, exist_ok=True)


def _register_jwt_callbacks() -> None:
    from .routes import error

    @jwt.expired_token_loader
    def expired(_header: dict, _payload: dict) -> tuple[Response, int]:
        return error("El token ha expirado.", 401)

    @jwt.invalid_token_loader
    def invalid(reason: str) -> tuple[Response, int]:
        return error(f"Token no válido: {reason}", 401)

    @jwt.unauthorized_loader
    def missing(reason: str) -> tuple[Response, int]:
        return error(f"Autenticación requerida: {reason}", 401)

    @jwt.revoked_token_loader
    def revoked(_header: dict, _payload: dict) -> tuple[Response, int]:
        return error("El token ha sido revocado.", 401)


def _register_cli(app: Flask) -> None:
    from .models import User, UserRole, seed_default_categories

    @app.cli.command("seed")
    def seed() -> None:
        """Crea las categorías predefinidas."""
        created = seed_default_categories()
        click.echo(f"Categorías creadas: {created}")

    @app.cli.command("create-admin")
    @click.option("--email", prompt=True)
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    @click.option("--full-name", default="Administrador")
    def create_admin(email: str, password: str, full_name: str) -> None:
        """Crea un usuario administrador."""
        email = email.strip().lower()
        if db.session.scalar(db.select(User).filter_by(email=email)):
            raise click.ClickException("Ya existe un usuario con ese email.")
        if len(password) < 8:
            raise click.ClickException("La contraseña debe tener al menos 8 caracteres.")
        user = User(email=email, full_name=full_name, role=UserRole.ADMIN)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Administrador creado: {email}")
