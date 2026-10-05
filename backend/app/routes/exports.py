"""Exportación de informes PDF consolidados."""
from __future__ import annotations

import io
import re
import time
import uuid
from datetime import date
from pathlib import Path

from flask import Blueprint, current_app, request, send_file
from flask.wrappers import Response
from flask_jwt_extended import jwt_required
from reportlab.platypus.doctemplate import LayoutError
from sqlalchemy import func, select
from werkzeug.exceptions import NotFound

from ..extensions import db
from ..models import Category, Contact, Document
from ..schemas import ExportQuerySchema
from ..services.pdf_generator import PdfReportGenerator, ReportFilters, ReportItem
from . import current_user, error, success
from .documents import build_document_query

exports_bp = Blueprint("exports", __name__, url_prefix="/exports")

export_query_schema = ExportQuerySchema()

MAX_DOCUMENTS_PER_REPORT = 2000
TEMP_PDF_TTL_SECONDS = 24 * 3600
SAVED_PDF_REGEX = re.compile(r"informe_\d{8}_[0-9a-f]{8}\.pdf")


def _cleanup_old_pdfs(folder: Path) -> None:
    """Elimina informes temporales con más de 24 h de antigüedad."""
    threshold = time.time() - TEMP_PDF_TTL_SECONDS
    for pdf in folder.glob("informe_*.pdf"):
        try:
            if pdf.stat().st_mtime < threshold:
                pdf.unlink(missing_ok=True)
        except OSError:
            current_app.logger.warning("No se pudo eliminar el PDF temporal %s", pdf)


@exports_bp.get("/pdf")
@jwt_required()
def export_pdf() -> Response | tuple[Response, int]:
    """Genera el informe bajo demanda.

    Query params: start_date, end_date, category_id, contact_id, status, search,
    include_images (bool, defecto true) y download (bool, defecto true).
    Con download=false se guarda en uploads/pdfs/ y se devuelve la ruta en JSON.
    """
    user = current_user()
    params = export_query_schema.load(request.args)

    category_name: str | None = None
    if params["category_id"]:
        category = db.session.get(Category, params["category_id"])
        if category is None:
            return error("Datos no válidos.", 422, {"category_id": ["La categoría no existe."]})
        category_name = category.name

    contact_name: str | None = None
    if params["contact_id"]:
        contact = db.session.get(Contact, params["contact_id"])
        if contact is None:
            return error("Datos no válidos.", 422, {"contact_id": ["El contacto no existe."]})
        contact_name = contact.name

    stmt = build_document_query(params, user)
    count = db.session.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    if count > MAX_DOCUMENTS_PER_REPORT:
        return error(
            f"El informe incluiría {count} documentos (máximo {MAX_DOCUMENTS_PER_REPORT}). "
            "Acota el rango de fechas o aplica más filtros.",
            422,
        )

    documents = db.session.scalars(stmt.order_by(Document.date.asc())).unique().all()
    items = [ReportItem.from_document(doc) for doc in documents]
    filters = ReportFilters(
        start_date=params["start_date"],
        end_date=params["end_date"],
        category_name=category_name,
        contact_name=contact_name,
        status=params["status"].value if params["status"] else None,
        search=params["search"],
    )

    cfg = current_app.config
    generator = PdfReportGenerator(
        company_name=cfg["COMPANY_NAME"],
        upload_root=cfg["UPLOAD_FOLDER"],
        logo_path=cfg.get("COMPANY_LOGO_PATH") or None,
    )
    try:
        pdf_bytes = generator.generate_bytes(items, filters, include_images=params["include_images"])
    except LayoutError:
        current_app.logger.exception("Error de maquetación generando el PDF")
        return error("No se pudo maquetar el informe. Prueba sin imágenes (include_images=false).", 500)

    filename = f"informe_{date.today():%Y%m%d}_{uuid.uuid4().hex[:8]}.pdf"

    if not params["download"]:
        folder = Path(cfg["UPLOAD_FOLDER"]) / "pdfs"
        folder.mkdir(parents=True, exist_ok=True)
        _cleanup_old_pdfs(folder)
        (folder / filename).write_bytes(pdf_bytes)
        return success(
            {"filename": filename, "pdf_path": f"pdfs/{filename}",
             "download_url": f"/api/v1/exports/pdf/{filename}", "documents": len(items),
             "size_bytes": len(pdf_bytes)},
            201,
            "Informe generado.",
        )

    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
        max_age=0,
    )


@exports_bp.get("/pdf/<filename>")
@jwt_required()
def download_saved_pdf(filename: str) -> Response:
    """Descarga un informe guardado previamente con download=false (válido 24 h)."""
    current_user()
    if not SAVED_PDF_REGEX.fullmatch(filename):
        raise NotFound("Informe no encontrado.")
    path = (Path(current_app.config["UPLOAD_FOLDER"]) / "pdfs" / filename).resolve()
    if not path.is_file():
        raise NotFound("Informe no encontrado.")
    return send_file(path, mimetype="application/pdf", as_attachment=True, download_name=filename, max_age=0)
