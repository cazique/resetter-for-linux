"""Gestión de documentos (facturas, tickets...) y catálogo de categorías."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from flask import Blueprint, current_app, request, send_file
from flask.wrappers import Response
from flask_jwt_extended import jwt_required
from sqlalchemy import Select, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload
from werkzeug.exceptions import BadRequest, Forbidden, NotFound

from ..extensions import db
from ..models import Category, Contact, Document, User, UserRole
from ..schemas import (
    CategorySchema,
    DocumentCreateSchema,
    DocumentListQuerySchema,
    DocumentSchema,
    DocumentUpdateSchema,
)
from ..services.image_processing import ImageProcessingError, ImageProcessor
from . import current_user, error, pagination_meta, parse_uuid, success

documents_bp = Blueprint("documents", __name__)

document_schema = DocumentSchema()
documents_schema = DocumentSchema(many=True)
create_schema = DocumentCreateSchema()
update_schema = DocumentUpdateSchema()
list_query_schema = DocumentListQuerySchema()
categories_schema = CategorySchema(many=True)


# --------------------------------------------------------------------------- #
# Helpers reutilizados también por exports.py
# --------------------------------------------------------------------------- #
def get_image_processor() -> ImageProcessor:
    cfg = current_app.config
    return ImageProcessor(
        upload_root=cfg["UPLOAD_FOLDER"],
        allowed_extensions=cfg["ALLOWED_IMAGE_EXTENSIONS"],
        allowed_formats=cfg["ALLOWED_IMAGE_FORMATS"],
        thumbnail_size=cfg["THUMBNAIL_SIZE"],
    )


def build_document_query(filters: dict[str, Any], user: User) -> Select[tuple[Document]]:
    """Construye la consulta filtrada (sin paginar) de documentos visibles para `user`."""
    stmt = (
        select(Document)
        .options(joinedload(Document.category), joinedload(Document.contact))
        .where(Document.deleted_at.is_(None))
    )
    if not user.can_see_all_documents:
        stmt = stmt.where(Document.user_id == user.id)
    if filters.get("start_date"):
        stmt = stmt.where(Document.date >= filters["start_date"])
    if filters.get("end_date"):
        stmt = stmt.where(Document.date <= filters["end_date"])
    if filters.get("category_id"):
        stmt = stmt.where(Document.category_id == filters["category_id"])
    if filters.get("contact_id"):
        stmt = stmt.where(Document.contact_id == filters["contact_id"])
    if filters.get("status"):
        stmt = stmt.where(Document.status == filters["status"])
    if filters.get("search"):
        pattern = f"%{filters['search']}%"
        stmt = stmt.where(or_(Document.title.ilike(pattern), Document.notes.ilike(pattern)))
    return stmt


def get_visible_document_or_404(document_id: str, user: User) -> Document:
    document = db.session.get(Document, parse_uuid(document_id, "documento"))
    if document is None or document.is_deleted:
        raise NotFound("Documento no encontrado.")
    if not user.can_see_all_documents and document.user_id != user.id:
        # 404 en lugar de 403 para no revelar la existencia del documento.
        raise NotFound("Documento no encontrado.")
    return document


def _ensure_can_modify(document: Document, user: User) -> None:
    if user.role in (UserRole.ADMIN, UserRole.ACCOUNTANT):
        return
    if document.user_id != user.id:
        raise Forbidden("No tienes permiso para modificar este documento.")


def _validate_relations(category_id: int | None, contact_id: uuid.UUID | None) -> dict[str, list[str]]:
    errors: dict[str, list[str]] = {}
    if category_id is not None:
        category = db.session.get(Category, category_id)
        if category is None or not category.is_active:
            errors["category_id"] = ["La categoría no existe o está inactiva."]
    if contact_id is not None and db.session.get(Contact, contact_id) is None:
        errors["contact_id"] = ["El contacto no existe."]
    return errors


# --------------------------------------------------------------------------- #
# Categorías
# --------------------------------------------------------------------------- #
@documents_bp.get("/categories")
@jwt_required()
def list_categories() -> tuple[Response, int]:
    current_user()
    stmt = select(Category).where(Category.is_active.is_(True)).order_by(Category.name)
    return success(categories_schema.dump(db.session.scalars(stmt).all()))


# --------------------------------------------------------------------------- #
# Documentos
# --------------------------------------------------------------------------- #
@documents_bp.post("/documents")
@jwt_required()
def create_document() -> tuple[Response, int]:
    """Alta de documento vía multipart/form-data (campo `image` obligatorio)."""
    user = current_user()

    image = request.files.get("image")
    if image is None or not image.filename:
        return error("Datos no válidos.", 422, {"image": ["La imagen es obligatoria."]})

    data = create_schema.load(request.form.to_dict())
    relation_errors = _validate_relations(data["category_id"], data["contact_id"])
    if relation_errors:
        return error("Datos no válidos.", 422, relation_errors)

    processor = get_image_processor()
    try:
        processed = processor.process_upload(image.stream, image.filename)
    except ImageProcessingError as exc:
        return error("Datos no válidos.", 422, {"image": [str(exc)]})

    document = Document(
        user_id=user.id,
        category_id=data["category_id"],
        contact_id=data["contact_id"],
        title=data["title"],
        amount=data["amount"],
        tax_amount=data["tax_amount"],
        date=data["date"],
        notes=data["notes"],
        image_path=processed.image_path,
        thumbnail_path=processed.thumbnail_path,
    )
    db.session.add(document)
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        processor.delete_files(processed.image_path, processed.thumbnail_path)
        current_app.logger.exception("Error guardando documento")
        return error("No se pudo guardar el documento.", 500)

    return success(document_schema.dump(document), 201, "Documento creado correctamente.")


@documents_bp.get("/documents")
@jwt_required()
def list_documents() -> tuple[Response, int]:
    user = current_user()
    params = list_query_schema.load(request.args)
    stmt = build_document_query(params, user).order_by(Document.date.desc(), Document.created_at.desc())
    page = db.paginate(stmt, page=params["page"], per_page=params["per_page"], error_out=False)
    return success(documents_schema.dump(page.items), **pagination_meta(page))


@documents_bp.get("/documents/<document_id>")
@jwt_required()
def get_document(document_id: str) -> tuple[Response, int]:
    user = current_user()
    return success(document_schema.dump(get_visible_document_or_404(document_id, user)))


@documents_bp.patch("/documents/<document_id>")
@jwt_required()
def update_document(document_id: str) -> tuple[Response, int]:
    user = current_user()
    document = get_visible_document_or_404(document_id, user)
    _ensure_can_modify(document, user)

    payload = request.get_json(silent=True)
    if payload is None:
        payload = request.form.to_dict()
    data = update_schema.load(payload or {})
    if not data:
        raise BadRequest("No se ha enviado ningún campo para actualizar.")

    relation_errors = _validate_relations(data.get("category_id"), data.get("contact_id"))
    if relation_errors:
        return error("Datos no válidos.", 422, relation_errors)

    if data.get("category_id") is None:
        data.pop("category_id", None)  # la categoría es obligatoria; no se puede anular

    new_amount = data.get("amount", document.amount)
    new_tax = data.get("tax_amount", document.tax_amount)
    if new_tax > new_amount:
        return error("Datos no válidos.", 422, {"tax_amount": ["El IVA no puede superar el importe total."]})

    for key, value in data.items():
        setattr(document, key, value)
    db.session.commit()
    return success(document_schema.dump(document), message="Documento actualizado.")


@documents_bp.delete("/documents/<document_id>")
@jwt_required()
def delete_document(document_id: str) -> tuple[Response, int]:
    """Borrado lógico: se marca deleted_at y se conservan los ficheros."""
    user = current_user()
    document = get_visible_document_or_404(document_id, user)
    if user.role != UserRole.ADMIN and document.user_id != user.id:
        raise Forbidden("No tienes permiso para eliminar este documento.")
    document.deleted_at = datetime.now(timezone.utc)
    db.session.commit()
    return success(None, message="Documento eliminado.")


def _send_document_file(document_id: str, attribute: str) -> Response:
    user = current_user()
    document = get_visible_document_or_404(document_id, user)
    relative = getattr(document, attribute)
    if not relative:
        raise NotFound("Archivo no disponible.")
    try:
        path = get_image_processor().absolute_path(relative)
    except ImageProcessingError as exc:
        raise NotFound("Archivo no disponible.") from exc
    if not path.is_file():
        raise NotFound("Archivo no disponible.")
    response = send_file(path, mimetype="image/jpeg", conditional=True, max_age=3600)
    response.headers["Cache-Control"] = "private, max-age=3600"
    return response


@documents_bp.get("/documents/<document_id>/image")
@jwt_required()
def get_document_image(document_id: str) -> Response:
    return _send_document_file(document_id, "image_path")


@documents_bp.get("/documents/<document_id>/thumbnail")
@jwt_required()
def get_document_thumbnail(document_id: str) -> Response:
    return _send_document_file(document_id, "thumbnail_path")
