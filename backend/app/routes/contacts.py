"""CRUD de contactos (proveedores, clientes y trabajadores)."""
from __future__ import annotations

from flask import Blueprint, request
from flask.wrappers import Response
from flask_jwt_extended import jwt_required
from sqlalchemy import or_, select
from werkzeug.exceptions import NotFound

from ..extensions import db
from ..models import Contact
from ..schemas import ContactInputSchema, ContactListQuerySchema, ContactSchema
from . import current_user, error, pagination_meta, parse_uuid, success

contacts_bp = Blueprint("contacts", __name__, url_prefix="/contacts")

contact_schema = ContactSchema()
contacts_schema = ContactSchema(many=True)
contact_input_schema = ContactInputSchema()
contact_partial_schema = ContactInputSchema(partial=True)
list_query_schema = ContactListQuerySchema()


def _get_contact_or_404(contact_id: str) -> Contact:
    contact = db.session.get(Contact, parse_uuid(contact_id, "contacto"))
    if contact is None:
        raise NotFound("Contacto no encontrado.")
    return contact


@contacts_bp.get("")
@jwt_required()
def list_contacts() -> tuple[Response, int]:
    current_user()
    params = list_query_schema.load(request.args)
    stmt = select(Contact)
    if params["type"]:
        stmt = stmt.where(Contact.type == params["type"])
    if params["search"]:
        pattern = f"%{params['search']}%"
        stmt = stmt.where(
            or_(Contact.name.ilike(pattern), Contact.tax_id.ilike(pattern), Contact.email.ilike(pattern))
        )
    stmt = stmt.order_by(Contact.name.asc())
    page = db.paginate(stmt, page=params["page"], per_page=params["per_page"], error_out=False)
    return success(contacts_schema.dump(page.items), **pagination_meta(page))


@contacts_bp.post("")
@jwt_required()
def create_contact() -> tuple[Response, int]:
    current_user()
    data = contact_input_schema.load(request.get_json(silent=True) or {})
    contact = Contact(**data)
    db.session.add(contact)
    db.session.commit()
    return success(contact_schema.dump(contact), 201, "Contacto creado.")


@contacts_bp.get("/<contact_id>")
@jwt_required()
def get_contact(contact_id: str) -> tuple[Response, int]:
    current_user()
    return success(contact_schema.dump(_get_contact_or_404(contact_id)))


@contacts_bp.route("/<contact_id>", methods=["PUT", "PATCH"])
@jwt_required()
def update_contact(contact_id: str) -> tuple[Response, int]:
    current_user()
    contact = _get_contact_or_404(contact_id)
    schema = contact_input_schema if request.method == "PUT" else contact_partial_schema
    data = schema.load(request.get_json(silent=True) or {})
    if not data:
        return error("No se ha enviado ningún campo para actualizar.", 400)
    for key, value in data.items():
        setattr(contact, key, value)
    db.session.commit()
    return success(contact_schema.dump(contact), message="Contacto actualizado.")


@contacts_bp.delete("/<contact_id>")
@jwt_required()
def delete_contact(contact_id: str) -> tuple[Response, int]:
    current_user()
    contact = _get_contact_or_404(contact_id)
    # Los documentos asociados conservan sus datos; contact_id pasa a NULL.
    for document in contact.documents:
        document.contact_id = None
    db.session.delete(contact)
    db.session.commit()
    return success(None, message="Contacto eliminado.")
