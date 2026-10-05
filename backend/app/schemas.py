"""Schemas Marshmallow: validación de entrada y serialización de salida."""
from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from marshmallow import (
    EXCLUDE,
    Schema,
    ValidationError,
    fields,
    post_load,
    pre_load,
    validate,
    validates,
    validates_schema,
)
from marshmallow_sqlalchemy import SQLAlchemySchema, auto_field

from .models import Category, Contact, ContactType, Document, DocumentStatus, User, UserRole

# NIF/NIE/CIF españoles (validación de formato, no de dígito de control)
TAX_ID_REGEX = re.compile(r"^([0-9]{8}[A-Z]|[XYZ][0-9]{7}[A-Z]|[ABCDEFGHJNPQRSUVW][0-9]{7}[0-9A-J])$")
PHONE_REGEX = re.compile(r"^\+?[0-9 ()\-]{6,20}$")
MONEY = {"as_string": False, "places": 2}


def _strip_strings(data: Any) -> Any:
    """Recorta espacios y convierte cadenas vacías en None."""
    if not isinstance(data, dict):
        return data
    cleaned: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, str):
            value = value.strip()
            cleaned[key] = value or None
        else:
            cleaned[key] = value
    return cleaned


class BaseInputSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    @pre_load
    def strip(self, data: Any, **_: Any) -> Any:
        return _strip_strings(data)


# --------------------------------------------------------------------------- #
# Auth / User
# --------------------------------------------------------------------------- #
class RegisterSchema(BaseInputSchema):
    email = fields.Email(required=True, validate=validate.Length(max=255))
    password = fields.String(required=True, load_only=True, validate=validate.Length(min=8, max=128))
    full_name = fields.String(load_default=None, validate=validate.Length(max=150))
    role = fields.Enum(UserRole, by_value=True, load_default=UserRole.EMPLOYEE)

    @post_load
    def normalize_email(self, data: dict[str, Any], **_: Any) -> dict[str, Any]:
        data["email"] = data["email"].lower()
        return data


class LoginSchema(BaseInputSchema):
    email = fields.Email(required=True)
    password = fields.String(required=True, load_only=True)

    @post_load
    def normalize_email(self, data: dict[str, Any], **_: Any) -> dict[str, Any]:
        data["email"] = data["email"].lower()
        return data


class UserSchema(SQLAlchemySchema):
    class Meta:
        model = User

    id = auto_field(dump_only=True)
    email = auto_field(dump_only=True)
    full_name = auto_field(dump_only=True)
    role = fields.Enum(UserRole, by_value=True, dump_only=True)
    is_active = auto_field(dump_only=True)
    created_at = auto_field(dump_only=True)


# --------------------------------------------------------------------------- #
# Category
# --------------------------------------------------------------------------- #
class CategorySchema(SQLAlchemySchema):
    class Meta:
        model = Category

    id = auto_field(dump_only=True)
    name = auto_field(dump_only=True)
    color_hex = auto_field(dump_only=True)
    is_active = auto_field(dump_only=True)


# --------------------------------------------------------------------------- #
# Contact
# --------------------------------------------------------------------------- #
class ContactInputSchema(BaseInputSchema):
    name = fields.String(required=True, validate=validate.Length(min=1, max=200))
    type = fields.Enum(ContactType, by_value=True, required=True)
    phone = fields.String(load_default=None, validate=validate.Regexp(PHONE_REGEX, error="Teléfono no válido."))
    email = fields.Email(load_default=None, validate=validate.Length(max=255))
    tax_id = fields.String(load_default=None)
    address = fields.String(load_default=None, validate=validate.Length(max=2000))
    notes = fields.String(load_default=None, validate=validate.Length(max=5000))

    @pre_load
    def upper_tax_id(self, data: Any, **_: Any) -> Any:
        if isinstance(data, dict) and isinstance(data.get("tax_id"), str):
            data["tax_id"] = data["tax_id"].replace("-", "").replace(" ", "").upper() or None
        return data

    @validates("tax_id")
    def validate_tax_id(self, value: str | None, **_: Any) -> None:
        if value is not None and not TAX_ID_REGEX.match(value):
            raise ValidationError("NIF/CIF con formato no válido.")


class ContactSchema(SQLAlchemySchema):
    class Meta:
        model = Contact

    id = auto_field(dump_only=True)
    name = auto_field()
    type = fields.Enum(ContactType, by_value=True)
    phone = auto_field()
    email = auto_field()
    tax_id = auto_field()
    address = auto_field()
    notes = auto_field()
    created_at = auto_field(dump_only=True)
    updated_at = auto_field(dump_only=True)


class ContactSummarySchema(Schema):
    id = fields.UUID()
    name = fields.String()
    type = fields.Enum(ContactType, by_value=True)


# --------------------------------------------------------------------------- #
# Document
# --------------------------------------------------------------------------- #
class DocumentCreateSchema(BaseInputSchema):
    """Campos de formulario multipart que acompañan a la imagen."""

    category_id = fields.Integer(required=True, strict=False, validate=validate.Range(min=1))
    contact_id = fields.UUID(load_default=None)
    title = fields.String(required=True, validate=validate.Length(min=1, max=200))
    amount = fields.Decimal(required=True, places=2, validate=validate.Range(min=Decimal("0")))
    tax_amount = fields.Decimal(load_default=Decimal("0"), places=2, validate=validate.Range(min=Decimal("0")))
    date = fields.Date(required=True, format="%Y-%m-%d")
    notes = fields.String(load_default=None, validate=validate.Length(max=5000))

    @validates_schema
    def tax_not_greater_than_amount(self, data: dict[str, Any], **_: Any) -> None:
        amount = data.get("amount")
        tax = data.get("tax_amount")
        if amount is not None and tax is not None and tax > amount:
            raise ValidationError("El IVA no puede superar el importe total.", field_name="tax_amount")


class DocumentUpdateSchema(BaseInputSchema):
    """PATCH parcial: todos los campos opcionales."""

    category_id = fields.Integer(strict=False, validate=validate.Range(min=1))
    contact_id = fields.UUID(allow_none=True)
    title = fields.String(validate=validate.Length(min=1, max=200))
    amount = fields.Decimal(places=2, validate=validate.Range(min=Decimal("0")))
    tax_amount = fields.Decimal(places=2, validate=validate.Range(min=Decimal("0")))
    date = fields.Date(format="%Y-%m-%d")
    status = fields.Enum(DocumentStatus, by_value=True)
    # Nota: BaseInputSchema convierte "" en None, por lo que enviar contact_id=""
    # o notes="" en un PATCH borra el valor.
    notes = fields.String(allow_none=True, validate=validate.Length(max=5000))


class DocumentFilterSchema(BaseInputSchema):
    """Parámetros de consulta compartidos por /documents y /exports/pdf."""

    start_date = fields.Date(format="%Y-%m-%d", load_default=None)
    end_date = fields.Date(format="%Y-%m-%d", load_default=None)
    category_id = fields.Integer(strict=False, load_default=None, validate=validate.Range(min=1))
    contact_id = fields.UUID(load_default=None)
    status = fields.Enum(DocumentStatus, by_value=True, load_default=None)
    search = fields.String(load_default=None, validate=validate.Length(max=200))

    @validates_schema
    def valid_range(self, data: dict[str, Any], **_: Any) -> None:
        start, end = data.get("start_date"), data.get("end_date")
        if start and end and start > end:
            raise ValidationError("start_date no puede ser posterior a end_date.", field_name="start_date")


class PaginationSchema(BaseInputSchema):
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Integer(load_default=20, validate=validate.Range(min=1, max=100))


class DocumentListQuerySchema(DocumentFilterSchema, PaginationSchema):
    pass


class ContactListQuerySchema(PaginationSchema):
    search = fields.String(load_default=None, validate=validate.Length(max=200))
    type = fields.Enum(ContactType, by_value=True, load_default=None)


class ExportQuerySchema(DocumentFilterSchema):
    download = fields.Boolean(load_default=True)
    include_images = fields.Boolean(load_default=True)


class DocumentSchema(SQLAlchemySchema):
    class Meta:
        model = Document

    id = auto_field(dump_only=True)
    user_id = auto_field(dump_only=True)
    contact_id = auto_field(dump_only=True)
    category_id = auto_field(dump_only=True)
    title = auto_field(dump_only=True)
    amount = fields.Decimal(dump_only=True, **MONEY)
    tax_amount = fields.Decimal(dump_only=True, **MONEY)
    date = auto_field(dump_only=True)
    status = fields.Enum(DocumentStatus, by_value=True, dump_only=True)
    notes = auto_field(dump_only=True)
    image_path = auto_field(dump_only=True)
    thumbnail_path = auto_field(dump_only=True)
    pdf_path = auto_field(dump_only=True)
    created_at = auto_field(dump_only=True)
    updated_at = auto_field(dump_only=True)
    category = fields.Nested(CategorySchema, dump_only=True)
    contact = fields.Nested(ContactSummarySchema, dump_only=True, allow_none=True)
    image_url = fields.Method("get_image_url", dump_only=True)
    thumbnail_url = fields.Method("get_thumbnail_url", dump_only=True)

    def get_image_url(self, obj: Document) -> str:
        return f"/api/v1/documents/{obj.id}/image"

    def get_thumbnail_url(self, obj: Document) -> str | None:
        return f"/api/v1/documents/{obj.id}/thumbnail" if obj.thumbnail_path else None
