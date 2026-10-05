"""Modelos SQLAlchemy de la plataforma de gestión documental.

Se usa el tipo genérico `Uuid` de SQLAlchemy 2.x, que se mapea a `UUID` nativo
en PostgreSQL y a `CHAR(32)` en otros motores (útil para tests con SQLite).
"""
from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
    func,
    select,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


# --------------------------------------------------------------------------- #
# Enumeraciones
# --------------------------------------------------------------------------- #
class UserRole(str, enum.Enum):
    ADMIN = "Admin"
    EMPLOYEE = "Employee"
    ACCOUNTANT = "Accountant"


class ContactType(str, enum.Enum):
    PROVEEDOR = "Proveedor"
    CLIENTE = "Cliente"
    TRABAJADOR = "Trabajador"


class DocumentStatus(str, enum.Enum):
    PENDIENTE = "Pendiente"
    PROCESADO = "Procesado"
    ARCHIVADO = "Archivado"


def _enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    """Persiste el *valor* del enum (p.ej. "Proveedor") en lugar del nombre."""
    return [member.value for member in enum_cls]


# Categorías predefinidas: nombre -> color corporativo
DEFAULT_CATEGORIES: dict[str, str] = {
    "Factura Proveedor": "#1E88E5",
    "Factura Cliente": "#43A047",
    "Ticket Comida": "#FB8C00",
    "Ticket Gasolina": "#E53935",
    "Varios": "#8E24AA",
}


class TimestampMixin:
    """Columnas de auditoría comunes."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )


# --------------------------------------------------------------------------- #
# Modelos
# --------------------------------------------------------------------------- #
class User(TimestampMixin, db.Model):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(150))
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", values_callable=_enum_values),
        nullable=False,
        default=UserRole.EMPLOYEE,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    documents: Mapped[list["Document"]] = relationship(back_populates="user", lazy="dynamic")

    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    @property
    def can_see_all_documents(self) -> bool:
        """Admin y Contable ven todos los documentos; Empleado solo los suyos."""
        return self.role in (UserRole.ADMIN, UserRole.ACCOUNTANT)

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role.value})>"


class Category(db.Model):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    color_hex: Mapped[str] = mapped_column(String(7), nullable=False, default="#607D8B")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    documents: Mapped[list["Document"]] = relationship(back_populates="category", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Category {self.name}>"


class Contact(TimestampMixin, db.Model):
    __tablename__ = "contacts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    type: Mapped[ContactType] = mapped_column(
        Enum(ContactType, name="contact_type", values_callable=_enum_values), nullable=False
    )
    phone: Mapped[Optional[str]] = mapped_column(String(30))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    tax_id: Mapped[Optional[str]] = mapped_column(String(20), index=True)  # NIF/CIF
    address: Mapped[Optional[str]] = mapped_column(Text)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    documents: Mapped[list["Document"]] = relationship(back_populates="contact", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Contact {self.name} ({self.type.value})>"


class Document(TimestampMixin, db.Model):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    contact_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    title: Mapped[Optional[str]] = mapped_column(String(200))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0"), server_default="0"
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    image_path: Mapped[str] = mapped_column(String(500), nullable=False)
    pdf_path: Mapped[Optional[str]] = mapped_column(String(500))
    thumbnail_path: Mapped[Optional[str]] = mapped_column(String(500))
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status", values_callable=_enum_values),
        nullable=False,
        default=DocumentStatus.PENDIENTE,
        index=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text)
    # Borrado lógico: los documentos con deleted_at no aparecen en listados ni informes.
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)

    user: Mapped[User] = relationship(back_populates="documents")
    contact: Mapped[Optional[Contact]] = relationship(back_populates="documents")
    category: Mapped[Category] = relationship(back_populates="documents")

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def __repr__(self) -> str:
        return f"<Document {self.id} {self.title!r}>"


def seed_default_categories() -> int:
    """Inserta las categorías predefinidas que falten. Devuelve cuántas se crearon."""
    existing = set(db.session.scalars(select(Category.name)).all())
    created = 0
    for name, color in DEFAULT_CATEGORIES.items():
        if name not in existing:
            db.session.add(Category(name=name, color_hex=color, is_active=True))
            created += 1
    if created:
        db.session.commit()
    return created
