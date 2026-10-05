"""Blueprints de la API v1 y utilidades compartidas por las rutas."""
from __future__ import annotations

import uuid
from typing import Any

from flask import Blueprint, Flask, jsonify
from flask_jwt_extended import get_jwt_identity
from flask.wrappers import Response
from marshmallow import ValidationError
from werkzeug.exceptions import HTTPException, NotFound, Unauthorized

from ..extensions import db
from ..models import User

API_PREFIX = "/api/v1"


# --------------------------------------------------------------------------- #
# Respuestas JSON consistentes
# --------------------------------------------------------------------------- #
def success(data: Any = None, status: int = 200, message: str | None = None, **meta: Any) -> tuple[Response, int]:
    body: dict[str, Any] = {"success": True, "data": data}
    if message:
        body["message"] = message
    if meta:
        body["meta"] = meta
    return jsonify(body), status


def error(message: str, status: int, errors: Any = None) -> tuple[Response, int]:
    body: dict[str, Any] = {"success": False, "message": message}
    if errors:
        body["errors"] = errors
    return jsonify(body), status


def pagination_meta(pagination: Any) -> dict[str, int]:
    return {
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "pages": pagination.pages,
    }


def parse_uuid(value: str, label: str = "recurso") -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError) as exc:
        raise NotFound(f"{label.capitalize()} no encontrado.") from exc


def current_user() -> User:
    """Devuelve el usuario autenticado activo (requiere @jwt_required)."""
    identity = get_jwt_identity()
    try:
        user = db.session.get(User, uuid.UUID(str(identity)))
    except (ValueError, TypeError):
        user = None
    if user is None or not user.is_active:
        raise Unauthorized("Usuario no válido o desactivado.")
    return user


# --------------------------------------------------------------------------- #
# Registro de blueprints y manejadores de error
# --------------------------------------------------------------------------- #
def register_blueprints(app: Flask) -> None:
    from .auth import auth_bp
    from .contacts import contacts_bp
    from .documents import documents_bp
    from .exports import exports_bp

    api_v1 = Blueprint("api_v1", __name__, url_prefix=API_PREFIX)
    api_v1.register_blueprint(auth_bp)
    api_v1.register_blueprint(contacts_bp)
    api_v1.register_blueprint(documents_bp)
    api_v1.register_blueprint(exports_bp)

    @api_v1.get("/health")
    def health() -> tuple[Response, int]:
        return success({"status": "ok"})

    app.register_blueprint(api_v1)


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ValidationError)
    def handle_validation(err: ValidationError) -> tuple[Response, int]:
        return error("Datos no válidos.", 422, err.messages)

    @app.errorhandler(HTTPException)
    def handle_http(err: HTTPException) -> tuple[Response, int]:
        messages = {
            413: "El archivo supera el tamaño máximo permitido.",
            405: "Método no permitido.",
        }
        message = messages.get(err.code or 500, err.description or err.name)
        return error(message, err.code or 500)

    @app.errorhandler(Exception)
    def handle_unexpected(err: Exception) -> tuple[Response, int]:
        db.session.rollback()
        app.logger.exception("Error no controlado: %s", err)
        return error("Error interno del servidor.", 500)
