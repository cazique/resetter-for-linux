"""Modelos ORM (SQLAlchemy 2.0) del sistema de gestión de costes.

Diagrama relacional:

    Proveedor 1───* Factura *───1 CategoriaGasto
                      │  └──* LineaIVA          (varios tipos de IVA por factura)
                      └──────*───1 Proyecto 1───* ParteTrabajo *───1 Empleado
                                                     └──* GastoParte (comida, parking...)

`Proyecto` es el eje de imputación de costes: facturas + horas + dietas.
Los importes usan Numeric(12,2) -> Decimal (nunca float para dinero).
"""
from __future__ import annotations

import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from .database import Base
from .fiscal import CENTIMO, etiqueta_trimestre, normalizar_nif, trimestre_de

Dinero = Numeric(12, 2)
Porcentaje = Numeric(5, 2)


class EstadoPago(str, enum.Enum):
    PENDIENTE = "pendiente"
    PAGADO = "pagado"


class TipoGasto(str, enum.Enum):
    COMIDA = "comida"
    DIETA = "dieta"
    PARKING = "parking"
    PEAJE = "peaje"
    TRANSPORTE = "transporte"
    ALOJAMIENTO = "alojamiento"
    COMBUSTIBLE = "combustible"
    OTRO = "otro"


class TimestampMixin:
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ======================================================================
# A. PROVEEDORES Y FACTURAS
# ======================================================================
class Proveedor(TimestampMixin, Base):
    __tablename__ = "proveedores"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200), index=True)
    nif: Mapped[str] = mapped_column(String(15), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(120))
    telefono: Mapped[str | None] = mapped_column(String(30))
    # Categoría que se propone por defecto al escanear facturas de este proveedor
    categoria_defecto_id: Mapped[int | None] = mapped_column(ForeignKey("categorias_gasto.id"))

    facturas: Mapped[list[Factura]] = relationship(back_populates="proveedor")
    categoria_defecto: Mapped[CategoriaGasto | None] = relationship()

    @validates("nif")
    def _normaliza_nif(self, _key, valor: str) -> str:
        return normalizar_nif(valor) or valor

    def __repr__(self) -> str:
        return f"<Proveedor {self.nif} {self.nombre!r}>"


class CategoriaGasto(Base):
    __tablename__ = "categorias_gasto"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80), unique=True)
    # Cuenta del Plan General Contable (p.ej. 628 Suministros) -> útil para la gestoría
    cuenta_contable: Mapped[str | None] = mapped_column(String(10))


class Proyecto(TimestampMixin, Base):
    """Proyecto / Cliente / Sitio al que se imputan costes."""

    __tablename__ = "proyectos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(150), unique=True)
    cliente: Mapped[str | None] = mapped_column(String(150), index=True)
    ubicacion: Mapped[str | None] = mapped_column(String(200))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)

    facturas: Mapped[list[Factura]] = relationship(back_populates="proyecto")
    partes: Mapped[list[ParteTrabajo]] = relationship(back_populates="proyecto")


class Factura(TimestampMixin, Base):
    __tablename__ = "facturas"
    __table_args__ = (
        UniqueConstraint("proveedor_id", "numero", name="uq_factura_proveedor_numero"),
        Index("ix_factura_periodo", "anio", "trimestre"),
        CheckConstraint("trimestre BETWEEN 1 AND 4", name="ck_factura_trimestre"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    proveedor_id: Mapped[int] = mapped_column(ForeignKey("proveedores.id"), index=True)
    numero: Mapped[str] = mapped_column(String(60))
    fecha_emision: Mapped[date] = mapped_column(Date, index=True)
    # Derivados de fecha_emision (se rellenan solos); persistidos para filtrar/indexar
    trimestre: Mapped[int] = mapped_column(SmallInteger)
    anio: Mapped[int] = mapped_column(SmallInteger)

    base_imponible: Mapped[Decimal] = mapped_column(Dinero, default=Decimal("0"))
    cuota_iva: Mapped[Decimal] = mapped_column(Dinero, default=Decimal("0"))
    irpf_porcentaje: Mapped[Decimal] = mapped_column(Porcentaje, default=Decimal("0"))
    irpf_importe: Mapped[Decimal] = mapped_column(Dinero, default=Decimal("0"))
    total: Mapped[Decimal] = mapped_column(Dinero)

    categoria_id: Mapped[int | None] = mapped_column(ForeignKey("categorias_gasto.id"), index=True)
    proyecto_id: Mapped[int | None] = mapped_column(ForeignKey("proyectos.id"), index=True)
    estado_pago: Mapped[EstadoPago] = mapped_column(
        Enum(EstadoPago, native_enum=False, length=12), default=EstadoPago.PENDIENTE, index=True
    )
    fecha_pago: Mapped[date | None] = mapped_column(Date)

    archivo_url: Mapped[str | None] = mapped_column(String(500))  # ruta local, S3, etc.
    # Trazabilidad del OCR
    ocr_confianza: Mapped[float | None]
    requiere_revision: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    notas: Mapped[str | None] = mapped_column(Text)

    proveedor: Mapped[Proveedor] = relationship(back_populates="facturas", lazy="joined")
    categoria: Mapped[CategoriaGasto | None] = relationship(lazy="joined")
    proyecto: Mapped[Proyecto | None] = relationship(back_populates="facturas")
    lineas_iva: Mapped[list[LineaIVA]] = relationship(
        back_populates="factura", cascade="all, delete-orphan", lazy="selectin"
    )

    @validates("fecha_emision")
    def _asigna_trimestre(self, _key, valor: date) -> date:
        self.trimestre, self.anio = trimestre_de(valor)
        return valor

    @property
    def trimestre_label(self) -> str:
        return etiqueta_trimestre(self.trimestre, self.anio)

    @property
    def tipos_iva(self) -> str:
        """Texto resumen para listados: '21% + 10%'."""
        return " + ".join(f"{l.tipo.normalize():f}%" for l in self.lineas_iva) or "-"

    def recalcular_totales(self) -> None:
        """Recalcula base, IVA, IRPF y total a partir de las líneas de IVA."""
        self.base_imponible = sum((l.base for l in self.lineas_iva), Decimal("0"))
        self.cuota_iva = sum((l.cuota + (l.recargo_equivalencia or 0) for l in self.lineas_iva), Decimal("0"))
        if self.irpf_porcentaje:
            self.irpf_importe = (self.base_imponible * self.irpf_porcentaje / 100).quantize(CENTIMO)
        self.total = self.base_imponible + self.cuota_iva - (self.irpf_importe or Decimal("0"))

    def __repr__(self) -> str:
        return f"<Factura {self.numero} {self.fecha_emision} {self.total}€>"


class LineaIVA(Base):
    """Desglose por tipo impositivo (una factura puede tener 21% + 10% + 4%)."""

    __tablename__ = "lineas_iva"
    __table_args__ = (UniqueConstraint("factura_id", "tipo", name="uq_linea_iva_tipo"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    factura_id: Mapped[int] = mapped_column(ForeignKey("facturas.id", ondelete="CASCADE"), index=True)
    tipo: Mapped[Decimal] = mapped_column(Porcentaje)  # 21.00, 10.00...
    base: Mapped[Decimal] = mapped_column(Dinero)
    cuota: Mapped[Decimal] = mapped_column(Dinero)
    recargo_equivalencia: Mapped[Decimal | None] = mapped_column(Dinero)

    factura: Mapped[Factura] = relationship(back_populates="lineas_iva")


# ======================================================================
# B. EMPLEADOS Y PARTES DE TRABAJO
# ======================================================================
class Empleado(TimestampMixin, Base):
    __tablename__ = "empleados"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(150), index=True)
    nif: Mapped[str | None] = mapped_column(String(15), unique=True)
    email: Mapped[str | None] = mapped_column(String(120), unique=True)
    coste_hora: Mapped[Decimal] = mapped_column(Dinero, default=Decimal("0"))  # coste empresa/hora
    tarifa_km: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))  # None -> tarifa por defecto
    activo: Mapped[bool] = mapped_column(Boolean, default=True)

    partes: Mapped[list[ParteTrabajo]] = relationship(back_populates="empleado")


class ParteTrabajo(TimestampMixin, Base):
    __tablename__ = "partes_trabajo"
    __table_args__ = (
        Index("ix_parte_empleado_fecha", "empleado_id", "fecha"),
        Index("ix_parte_proyecto_fecha", "proyecto_id", "fecha"),
        CheckConstraint("horas >= 0 AND horas <= 24", name="ck_parte_horas"),
        CheckConstraint("km >= 0", name="ck_parte_km"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    empleado_id: Mapped[int] = mapped_column(ForeignKey("empleados.id"))
    proyecto_id: Mapped[int] = mapped_column(ForeignKey("proyectos.id"))
    fecha: Mapped[date] = mapped_column(Date, index=True)
    horas: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    descripcion: Mapped[str | None] = mapped_column(Text)

    km: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=Decimal("0"))
    # Snapshots: si cambia la tarifa del empleado, los partes antiguos no se alteran
    tarifa_km: Mapped[Decimal] = mapped_column(Numeric(6, 3), default=Decimal("0.26"))
    coste_hora: Mapped[Decimal] = mapped_column(Dinero, default=Decimal("0"))
    comisiones: Mapped[Decimal] = mapped_column(Dinero, default=Decimal("0"))

    # Calculados por recalcular_totales()
    importe_km: Mapped[Decimal] = mapped_column(Dinero, default=Decimal("0"))
    importe_dietas: Mapped[Decimal] = mapped_column(Dinero, default=Decimal("0"))
    total_gastos: Mapped[Decimal] = mapped_column(Dinero, default=Decimal("0"))  # km+dietas+comisiones
    coste_horas: Mapped[Decimal] = mapped_column(Dinero, default=Decimal("0"))

    empleado: Mapped[Empleado] = relationship(back_populates="partes", lazy="joined")
    proyecto: Mapped[Proyecto] = relationship(back_populates="partes", lazy="joined")
    gastos: Mapped[list[GastoParte]] = relationship(
        back_populates="parte", cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def coste_total(self) -> Decimal:
        """Coste imputable al proyecto: mano de obra + gastos asociados."""
        return (self.coste_horas or Decimal("0")) + (self.total_gastos or Decimal("0"))

    def recalcular_totales(self) -> None:
        self.importe_km = (Decimal(self.km or 0) * Decimal(self.tarifa_km or 0)).quantize(CENTIMO)
        self.importe_dietas = sum((g.importe for g in self.gastos), Decimal("0"))
        self.total_gastos = self.importe_km + self.importe_dietas + (self.comisiones or Decimal("0"))
        self.coste_horas = (Decimal(self.horas or 0) * Decimal(self.coste_hora or 0)).quantize(CENTIMO)


class GastoParte(Base):
    """Gasto adicional de un parte: 'Comida 20€', 'Parking 5€', 'Dieta completa'..."""

    __tablename__ = "gastos_parte"
    __table_args__ = (CheckConstraint("importe >= 0", name="ck_gasto_importe"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    parte_id: Mapped[int] = mapped_column(ForeignKey("partes_trabajo.id", ondelete="CASCADE"), index=True)
    tipo: Mapped[TipoGasto] = mapped_column(Enum(TipoGasto, native_enum=False, length=15))
    concepto: Mapped[str] = mapped_column(String(200))
    importe: Mapped[Decimal] = mapped_column(Dinero)
    ticket_url: Mapped[str | None] = mapped_column(String(500))  # foto del ticket (opcional)

    parte: Mapped[ParteTrabajo] = relationship(back_populates="gastos")
