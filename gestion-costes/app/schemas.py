"""Esquemas Pydantic v2: validación de entrada (Create/Update), salida (Read) y filtros.

Regla: toda la lógica de coherencia (IVA, totales, trimestre, NIF) se valida aquí,
antes de tocar la base de datos, para que la UI, la API y el OCR compartan reglas.
"""
from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
    model_validator,
)

from .fiscal import (
    CENTIMO,
    a_dinero,
    etiqueta_trimestre,
    normalizar_nif,
    rango_trimestre,
    trimestre_de,
    validar_nif,
)
from .models import EstadoPago, TipoGasto

# Decimal con 2 decimales; acepta 12.5, "12,50", "1.234,56 €"
Dinero = Annotated[Decimal, BeforeValidator(a_dinero)]
DineroOpt = Annotated[Decimal | None, BeforeValidator(a_dinero)]
TOLERANCIA = Decimal("0.02")  # diferencias de redondeo admitidas
_PREFIJOS_UE = {
    "AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "EL", "FI", "FR", "HR", "HU", "IE",
    "IT", "LT", "LU", "LV", "MT", "NL", "PL", "PT", "RO", "SE", "SI", "SK", "XI",
}


class _Base(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, from_attributes=True)


# ----------------------------------------------------------------- Proveedor
class ProveedorBase(_Base):
    nombre: str = Field(min_length=2, max_length=200)
    nif: str = Field(description="CIF/NIF/NIE; se admite NIF-IVA 'ESB12345678'")
    email: str | None = None
    telefono: str | None = None
    categoria_defecto_id: int | None = None

    @field_validator("nif")
    @classmethod
    def _nif(cls, v: str) -> str:
        n = normalizar_nif(v)
        if validar_nif(n):
            return n
        # Proveedores UE: NIF-IVA con prefijo de país (p.ej. 'IE6388047V', 'DE123456789')
        if n and n[:2] in _PREFIJOS_UE and re.fullmatch(r"[A-Z0-9+*]{2,13}", n[2:]):
            return n
        raise ValueError(f"NIF/CIF no válido: {v}")


class ProveedorCreate(ProveedorBase):
    pass


class ProveedorRead(ProveedorBase):
    id: int


# ----------------------------------------------------------------- Catálogos
class CategoriaCreate(_Base):
    nombre: str = Field(min_length=2, max_length=80)
    cuenta_contable: str | None = Field(default=None, max_length=10)


class CategoriaRead(CategoriaCreate):
    id: int


class ProyectoCreate(_Base):
    nombre: str = Field(min_length=2, max_length=150)
    cliente: str | None = None
    ubicacion: str | None = None
    activo: bool = True


class ProyectoRead(ProyectoCreate):
    id: int


# ----------------------------------------------------------------- Facturas
class LineaIVACreate(_Base):
    tipo: Decimal = Field(ge=0, le=100, description="Porcentaje: 21, 10, 4, 0...")
    base: Dinero
    cuota: DineroOpt = None  # si falta se calcula
    recargo_equivalencia: DineroOpt = None

    @model_validator(mode="after")
    def _cuota(self) -> LineaIVACreate:
        esperado = (self.base * self.tipo / 100).quantize(CENTIMO)
        if self.cuota is None:
            self.cuota = esperado
        elif abs(self.cuota - esperado) > TOLERANCIA:
            raise ValueError(
                f"Cuota IVA {self.cuota} no corresponde al {self.tipo}% de {self.base} (≈{esperado})"
            )
        return self


class LineaIVARead(_Base):
    id: int
    tipo: Decimal
    base: Decimal
    cuota: Decimal
    recargo_equivalencia: Decimal | None = None


class FacturaBase(_Base):
    numero: str = Field(min_length=1, max_length=60)
    fecha_emision: date
    lineas_iva: list[LineaIVACreate] = Field(min_length=1)
    irpf_porcentaje: Decimal = Field(default=Decimal("0"), ge=0, le=50)
    irpf_importe: DineroOpt = None
    total: DineroOpt = None  # si llega (OCR/usuario) se contrasta con el cálculo
    categoria_id: int | None = None
    proyecto_id: int | None = None
    estado_pago: EstadoPago = EstadoPago.PENDIENTE
    fecha_pago: date | None = None
    archivo_url: str | None = None
    ocr_confianza: float | None = Field(default=None, ge=0, le=1)
    requiere_revision: bool = False
    notas: str | None = None

    @field_validator("lineas_iva")
    @classmethod
    def _tipos_unicos(cls, v: list[LineaIVACreate]) -> list[LineaIVACreate]:
        tipos = [l.tipo for l in v]
        if len(tipos) != len(set(tipos)):
            raise ValueError("Hay tipos de IVA repetidos: agrupa las bases por tipo")
        return v

    @computed_field
    @property
    def base_imponible(self) -> Decimal:
        return sum((l.base for l in self.lineas_iva), Decimal("0"))

    @computed_field
    @property
    def cuota_iva(self) -> Decimal:
        return sum((l.cuota + (l.recargo_equivalencia or 0) for l in self.lineas_iva), Decimal("0"))

    @computed_field
    @property
    def trimestre(self) -> int:
        return trimestre_de(self.fecha_emision)[0]

    @computed_field
    @property
    def anio(self) -> int:
        return self.fecha_emision.year

    @model_validator(mode="after")
    def _coherencia(self) -> FacturaBase:
        irpf_calc = (self.base_imponible * self.irpf_porcentaje / 100).quantize(CENTIMO)
        if self.irpf_importe is None:
            self.irpf_importe = irpf_calc
        elif self.irpf_porcentaje and abs(self.irpf_importe - irpf_calc) > TOLERANCIA:
            raise ValueError(f"Retención IRPF {self.irpf_importe} ≠ {self.irpf_porcentaje}% de la base")
        calculado = self.base_imponible + self.cuota_iva - self.irpf_importe
        if self.total is None:
            self.total = calculado
        elif abs(self.total - calculado) > TOLERANCIA * max(1, len(self.lineas_iva)):
            raise ValueError(f"El total {self.total} no cuadra con base+IVA-IRPF = {calculado}")
        if self.estado_pago is EstadoPago.PAGADO and self.fecha_pago is None:
            self.fecha_pago = date.today()
        if self.fecha_emision > date.today():
            raise ValueError("La fecha de emisión no puede ser futura")
        return self


class FacturaCreate(FacturaBase):
    """Alta de factura. Proveedor por id o por datos (se crea si no existe su NIF)."""

    proveedor_id: int | None = None
    proveedor: ProveedorCreate | None = None

    @model_validator(mode="after")
    def _proveedor(self) -> FacturaCreate:
        if self.proveedor_id is None and self.proveedor is None:
            raise ValueError("Indica proveedor_id o los datos del proveedor")
        return self


class FacturaUpdate(_Base):
    """Actualización parcial (p.ej. marcar como pagada o asignar proyecto)."""

    categoria_id: int | None = None
    proyecto_id: int | None = None
    estado_pago: EstadoPago | None = None
    fecha_pago: date | None = None
    requiere_revision: bool | None = None
    notas: str | None = None


class FacturaRead(_Base):
    id: int
    proveedor: ProveedorRead
    numero: str
    fecha_emision: date
    trimestre: int
    anio: int
    base_imponible: Decimal
    cuota_iva: Decimal
    irpf_porcentaje: Decimal
    irpf_importe: Decimal
    total: Decimal
    lineas_iva: list[LineaIVARead]
    categoria: CategoriaRead | None = None
    proyecto_id: int | None = None
    estado_pago: EstadoPago
    fecha_pago: date | None = None
    archivo_url: str | None = None
    ocr_confianza: float | None = None
    requiere_revision: bool
    notas: str | None = None

    @computed_field
    @property
    def trimestre_label(self) -> str:
        return etiqueta_trimestre(self.trimestre, self.anio)


class FiltroFacturas(_Base):
    """Criterios combinables para consultas y exportación a gestoría."""

    trimestre: int | None = Field(default=None, ge=1, le=4)
    anio: int | None = None
    fecha_desde: date | None = None
    fecha_hasta: date | None = None
    proveedor_id: int | None = None
    nif: str | None = None
    texto: str | None = None  # busca en nombre de proveedor o número de factura
    categoria_id: int | None = None
    proyecto_id: int | None = None
    estado_pago: EstadoPago | None = None
    solo_revision: bool = False

    @field_validator("nif")
    @classmethod
    def _nif(cls, v: str | None) -> str | None:
        return normalizar_nif(v)

    @model_validator(mode="after")
    def _rango(self) -> FiltroFacturas:
        if self.trimestre and not self.anio:
            raise ValueError("Para filtrar por trimestre indica también el año")
        if self.fecha_desde and self.fecha_hasta and self.fecha_desde > self.fecha_hasta:
            raise ValueError("fecha_desde es posterior a fecha_hasta")
        return self

    def rango_efectivo(self) -> tuple[date | None, date | None]:
        """Intersección entre trimestre y rango de fechas explícito."""
        desde, hasta = self.fecha_desde, self.fecha_hasta
        if self.trimestre and self.anio:
            q_ini, q_fin = rango_trimestre(self.trimestre, self.anio)
            desde = max(filter(None, [desde, q_ini]))
            hasta = min(filter(None, [hasta, q_fin]))
        return desde, hasta


# ----------------------------------------------------------------- Empleados
class EmpleadoCreate(_Base):
    nombre: str = Field(min_length=2, max_length=150)
    nif: str | None = None
    email: str | None = None
    coste_hora: Dinero = Decimal("0")
    tarifa_km: Decimal | None = Field(default=None, ge=0, le=5)
    activo: bool = True

    @field_validator("nif")
    @classmethod
    def _nif(cls, v: str | None) -> str | None:
        if v and not validar_nif(v):
            raise ValueError(f"NIF/NIE no válido: {v}")
        return normalizar_nif(v)


class EmpleadoRead(EmpleadoCreate):
    id: int


# ----------------------------------------------------------------- Partes de trabajo
_PALABRAS_TIPO = {
    TipoGasto.COMIDA: ("comida", "almuerzo", "cena", "desayuno", "menú", "menu", "restaurante"),
    TipoGasto.DIETA: ("dieta",),
    TipoGasto.PARKING: ("parking", "aparcamiento", "zona azul", "ora"),
    TipoGasto.PEAJE: ("peaje", "autopista"),
    TipoGasto.TRANSPORTE: ("taxi", "tren", "bus", "metro", "vuelo", "avión", "uber", "cabify"),
    TipoGasto.ALOJAMIENTO: ("hotel", "hostal", "alojamiento", "pernocta"),
    TipoGasto.COMBUSTIBLE: ("gasolina", "gasoil", "diésel", "diesel", "combustible", "repostaje"),
}
_RE_IMPORTE = re.compile(r"(\d+(?:[.,]\d{1,2})?)\s*(?:€|eur|euros)?\s*$", re.IGNORECASE)


def inferir_tipo_gasto(concepto: str) -> TipoGasto:
    c = concepto.lower()
    for tipo, palabras in _PALABRAS_TIPO.items():
        if any(re.search(rf"\b{re.escape(p)}\b", c) for p in palabras):
            return tipo
    return TipoGasto.OTRO


class GastoParteCreate(_Base):
    """Admite objeto completo o texto libre: "Comida 20€", "Parking 5,50"."""

    tipo: TipoGasto | None = None
    concepto: str = Field(min_length=1, max_length=200)
    importe: Dinero = Field(ge=0)
    ticket_url: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _desde_texto(cls, data):
        if isinstance(data, str):
            m = _RE_IMPORTE.search(data.strip())
            if not m:
                raise ValueError(f"No encuentro el importe en {data!r} (ej: 'Comida 20€')")
            concepto = data[: m.start()].strip(" :-") or data.strip()
            return {"concepto": concepto, "importe": m.group(1)}
        return data

    @model_validator(mode="after")
    def _tipo(self) -> GastoParteCreate:
        if self.tipo is None:
            self.tipo = inferir_tipo_gasto(self.concepto)
        return self


class GastoParteRead(_Base):
    id: int
    tipo: TipoGasto
    concepto: str
    importe: Decimal
    ticket_url: str | None = None


class ParteTrabajoCreate(_Base):
    empleado_id: int
    proyecto_id: int
    fecha: date
    horas: Decimal = Field(ge=0, le=24, decimal_places=2)
    km: Decimal = Field(default=Decimal("0"), ge=0, le=5000)
    comisiones: Dinero = Field(default=Decimal("0"), ge=0)
    gastos: list[GastoParteCreate] = Field(default_factory=list)
    descripcion: str | None = None

    @field_validator("fecha")
    @classmethod
    def _no_futuro(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("No se pueden registrar partes con fecha futura")
        return v

    @model_validator(mode="after")
    def _algo_que_registrar(self) -> ParteTrabajoCreate:
        if self.horas == 0 and self.km == 0 and not self.gastos and self.comisiones == 0:
            raise ValueError("El parte está vacío: indica horas, km o algún gasto")
        return self


class ParteTrabajoRead(_Base):
    id: int
    empleado: EmpleadoRead
    proyecto: ProyectoRead
    fecha: date
    horas: Decimal
    km: Decimal
    tarifa_km: Decimal
    importe_km: Decimal
    comisiones: Decimal
    importe_dietas: Decimal
    total_gastos: Decimal
    coste_horas: Decimal
    coste_total: Decimal
    gastos: list[GastoParteRead]
    descripcion: str | None = None


class FiltroPartes(_Base):
    empleado_id: int | None = None
    proyecto_id: int | None = None
    fecha_desde: date | None = None
    fecha_hasta: date | None = None
