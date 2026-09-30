"""PASO 3 · Lógica CRUD y consultas de negocio.

Todas las funciones reciben una `Session` (ver `database.get_session()`), de modo que la
interfaz Flet, una futura API REST o los tests reutilizan exactamente la misma lógica.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy import Select, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config import get_settings
from .fiscal import normalizar_nif, rango_trimestre, trimestre_de
from .models import (
    CategoriaGasto,
    Empleado,
    EstadoPago,
    Factura,
    GastoParte,
    LineaIVA,
    ParteTrabajo,
    Proveedor,
    Proyecto,
)
from .schemas import (
    CategoriaCreate,
    EmpleadoCreate,
    FacturaCreate,
    FacturaUpdate,
    FiltroFacturas,
    FiltroPartes,
    ParteTrabajoCreate,
    ProveedorCreate,
    ProyectoCreate,
    _normalizar_pago,
)

CERO = Decimal("0")


class ErrorNegocio(Exception):
    """Error comprensible para mostrar directamente al usuario."""


class NoEncontrado(ErrorNegocio):
    pass


class Duplicado(ErrorNegocio):
    pass


CATEGORIAS_INICIALES = [
    ("Combustible", "628"),
    ("Dietas y restauración", "629"),
    ("Material", "602"),
    ("Suministros", "628"),
    ("Herramientas", "602"),
    ("Servicios profesionales", "623"),
    ("Transporte", "624"),
    ("Alojamiento", "629"),
    ("Telefonía", "629"),
    ("Alquiler", "621"),
    ("Reparaciones", "622"),
    ("Otros", "629"),
]


def sembrar_datos_iniciales(s: Session) -> None:
    """Crea las categorías de gasto por defecto si la tabla está vacía."""
    if s.scalar(select(func.count(CategoriaGasto.id))) == 0:
        s.add_all(CategoriaGasto(nombre=n, cuenta_contable=c) for n, c in CATEGORIAS_INICIALES)
        s.flush()


def _obtener(s: Session, modelo, id_: int):
    obj = s.get(modelo, id_)
    if obj is None:
        raise NoEncontrado(f"{modelo.__name__} {id_} no existe")
    return obj


# ======================================================================
# Catálogos: proveedores, categorías, proyectos, empleados
# ======================================================================
def obtener_o_crear_proveedor(s: Session, datos: ProveedorCreate) -> Proveedor:
    """Busca por NIF; si existe lo reutiliza (y completa el nombre si faltaba)."""
    prov = s.scalar(select(Proveedor).where(Proveedor.nif == datos.nif))
    if prov is None:
        prov = Proveedor(**datos.model_dump())
        s.add(prov)
        s.flush()
    return prov


def buscar_proveedores(s: Session, texto: str = "", limite: int = 20) -> list[Proveedor]:
    q = select(Proveedor).order_by(Proveedor.nombre).limit(limite)
    if texto:
        patron = f"%{texto}%"
        q = q.where(or_(Proveedor.nombre.ilike(patron), Proveedor.nif.ilike(f"%{normalizar_nif(texto)}%")))
    return list(s.scalars(q))


def listar_categorias(s: Session) -> list[CategoriaGasto]:
    return list(s.scalars(select(CategoriaGasto).order_by(CategoriaGasto.nombre)))


def crear_categoria(s: Session, datos: CategoriaCreate) -> CategoriaGasto:
    cat = CategoriaGasto(**datos.model_dump())
    s.add(cat)
    s.flush()
    return cat


def categoria_por_nombre(s: Session, nombre: str | None) -> CategoriaGasto | None:
    if not nombre:
        return None
    return s.scalar(select(CategoriaGasto).where(func.lower(CategoriaGasto.nombre) == nombre.lower()))


def listar_proyectos(s: Session, solo_activos: bool = True) -> list[Proyecto]:
    q = select(Proyecto).order_by(Proyecto.nombre)
    if solo_activos:
        q = q.where(Proyecto.activo.is_(True))
    return list(s.scalars(q))


def crear_proyecto(s: Session, datos: ProyectoCreate) -> Proyecto:
    if s.scalar(select(Proyecto).where(Proyecto.nombre == datos.nombre)):
        raise Duplicado(f"Ya existe el proyecto '{datos.nombre}'")
    p = Proyecto(**datos.model_dump())
    s.add(p)
    s.flush()
    return p


def listar_empleados(s: Session, solo_activos: bool = True) -> list[Empleado]:
    q = select(Empleado).order_by(Empleado.nombre)
    if solo_activos:
        q = q.where(Empleado.activo.is_(True))
    return list(s.scalars(q))


def crear_empleado(s: Session, datos: EmpleadoCreate) -> Empleado:
    e = Empleado(**datos.model_dump())
    s.add(e)
    try:
        s.flush()
    except IntegrityError as exc:
        s.rollback()
        raise Duplicado("Ya existe un empleado con ese NIF o email") from exc
    return e


# ======================================================================
# A. Facturas
# ======================================================================
def crear_factura(s: Session, datos: FacturaCreate) -> Factura:
    proveedor = (
        _obtener(s, Proveedor, datos.proveedor_id)
        if datos.proveedor_id
        else obtener_o_crear_proveedor(s, datos.proveedor)
    )
    existente = s.scalar(
        select(Factura.id).where(Factura.proveedor_id == proveedor.id, Factura.numero == datos.numero)
    )
    if existente:
        raise Duplicado(f"La factura {datos.numero} de {proveedor.nombre} ya está registrada (id {existente})")

    campos = datos.model_dump(
        exclude={"proveedor", "proveedor_id", "lineas_iva", "base_imponible", "cuota_iva", "trimestre", "anio"}
    )
    factura = Factura(proveedor=proveedor, **campos)
    factura.lineas_iva = [LineaIVA(**l.model_dump()) for l in datos.lineas_iva]
    if factura.categoria_id is None and proveedor.categoria_defecto_id:
        factura.categoria_id = proveedor.categoria_defecto_id
    factura.recalcular_totales()
    factura.total = datos.total  # respeta el total impreso (ya validado dentro de tolerancia)
    factura.importe_pagado = datos.importe_pagado or Decimal("0")
    s.add(factura)
    s.flush()
    # Aprende la categoría habitual del proveedor para futuras facturas
    if proveedor.categoria_defecto_id is None and factura.categoria_id:
        proveedor.categoria_defecto_id = factura.categoria_id
    return factura


def obtener_factura(s: Session, factura_id: int) -> Factura:
    return _obtener(s, Factura, factura_id)


def actualizar_factura(s: Session, factura_id: int, cambios: FacturaUpdate) -> Factura:
    f = obtener_factura(s, factura_id)
    for campo, valor in cambios.model_dump(exclude_unset=True).items():
        setattr(f, campo, valor)
    try:
        _normalizar_pago(f)
    except ValueError as exc:
        raise ErrorNegocio(str(exc)) from exc
    s.flush()
    return f


def marcar_pagada(s: Session, factura_id: int, fecha_pago: date | None = None) -> Factura:
    return actualizar_factura(
        s, factura_id, FacturaUpdate(estado_pago=EstadoPago.PAGADO, fecha_pago=fecha_pago or date.today())
    )


def eliminar_factura(s: Session, factura_id: int) -> None:
    s.delete(obtener_factura(s, factura_id))
    s.flush()


def _query_facturas(filtro: FiltroFacturas) -> Select:
    q = select(Factura).join(Factura.proveedor)
    desde, hasta = filtro.rango_efectivo()
    if desde:
        q = q.where(Factura.fecha_emision >= desde)
    if hasta:
        q = q.where(Factura.fecha_emision <= hasta)
    if filtro.anio and not filtro.trimestre:
        q = q.where(Factura.anio == filtro.anio)
    if filtro.proveedor_id:
        q = q.where(Factura.proveedor_id == filtro.proveedor_id)
    if filtro.nif:
        q = q.where(Proveedor.nif == filtro.nif)
    if filtro.texto:
        patron = f"%{filtro.texto}%"
        q = q.where(or_(Proveedor.nombre.ilike(patron), Factura.numero.ilike(patron), Proveedor.nif.ilike(patron)))
    if filtro.categoria_id:
        q = q.where(Factura.categoria_id == filtro.categoria_id)
    if filtro.proyecto_id:
        q = q.where(Factura.proyecto_id == filtro.proyecto_id)
    if filtro.estado_pago:
        q = q.where(Factura.estado_pago == filtro.estado_pago)
    if filtro.solo_revision:
        q = q.where(Factura.requiere_revision.is_(True))
    return q


def listar_facturas(
    s: Session, filtro: FiltroFacturas | None = None, limite: int | None = None, offset: int = 0
) -> list[Factura]:
    q = _query_facturas(filtro or FiltroFacturas()).order_by(Factura.fecha_emision.desc(), Factura.id.desc())
    if limite:
        q = q.limit(limite).offset(offset)
    return list(s.scalars(q).unique())


@dataclass
class ResumenFacturas:
    n: int = 0
    base: Decimal = CERO
    iva: Decimal = CERO
    irpf: Decimal = CERO
    total: Decimal = CERO
    pendiente_pago: Decimal = CERO
    por_tipo_iva: dict[Decimal, tuple[Decimal, Decimal]] = field(default_factory=dict)  # tipo -> (base, cuota)


def resumen_facturas(s: Session, filtro: FiltroFacturas | None = None) -> ResumenFacturas:
    """Totales del listado filtrado + desglose por tipo de IVA (para el modelo 303)."""
    sub = _query_facturas(filtro or FiltroFacturas()).with_only_columns(Factura.id).subquery()
    fila = s.execute(
        select(
            func.count(Factura.id),
            func.coalesce(func.sum(Factura.base_imponible), 0),
            func.coalesce(func.sum(Factura.cuota_iva), 0),
            func.coalesce(func.sum(Factura.irpf_importe), 0),
            func.coalesce(func.sum(Factura.total), 0),
        ).where(Factura.id.in_(select(sub.c.id)))
    ).one()
    pendiente = s.scalar(
        select(func.coalesce(func.sum(Factura.total - Factura.importe_pagado), 0)).where(
            Factura.id.in_(select(sub.c.id)), Factura.estado_pago != EstadoPago.PAGADO
        )
    )
    tipos = s.execute(
        select(LineaIVA.tipo, func.sum(LineaIVA.base), func.sum(LineaIVA.cuota))
        .where(LineaIVA.factura_id.in_(select(sub.c.id)))
        .group_by(LineaIVA.tipo)
        .order_by(LineaIVA.tipo.desc())
    ).all()
    d = lambda v: Decimal(str(v or 0)).quantize(Decimal("0.01"))  # noqa: E731 (SQLite devuelve float)
    return ResumenFacturas(
        n=fila[0], base=d(fila[1]), iva=d(fila[2]), irpf=d(fila[3]), total=d(fila[4]),
        pendiente_pago=d(pendiente),
        por_tipo_iva={Decimal(str(t)).normalize(): (d(b), d(c)) for t, b, c in tipos},
    )


# ======================================================================
# B. Partes de trabajo
# ======================================================================
def crear_parte(s: Session, datos: ParteTrabajoCreate) -> ParteTrabajo:
    emp = _obtener(s, Empleado, datos.empleado_id)
    _obtener(s, Proyecto, datos.proyecto_id)
    parte = ParteTrabajo(
        **datos.model_dump(exclude={"gastos"}),
        coste_hora=emp.coste_hora,
        tarifa_km=emp.tarifa_km if emp.tarifa_km is not None else get_settings().tarifa_km_defecto,
    )
    parte.gastos = [GastoParte(**g.model_dump()) for g in datos.gastos]
    parte.recalcular_totales()
    s.add(parte)
    s.flush()
    return parte


def eliminar_parte(s: Session, parte_id: int) -> None:
    s.delete(_obtener(s, ParteTrabajo, parte_id))
    s.flush()


def listar_partes(s: Session, filtro: FiltroPartes | None = None, limite: int | None = None) -> list[ParteTrabajo]:
    f = filtro or FiltroPartes()
    q = select(ParteTrabajo).order_by(ParteTrabajo.fecha.desc(), ParteTrabajo.id.desc())
    if f.empleado_id:
        q = q.where(ParteTrabajo.empleado_id == f.empleado_id)
    if f.proyecto_id:
        q = q.where(ParteTrabajo.proyecto_id == f.proyecto_id)
    if f.fecha_desde:
        q = q.where(ParteTrabajo.fecha >= f.fecha_desde)
    if f.fecha_hasta:
        q = q.where(ParteTrabajo.fecha <= f.fecha_hasta)
    if limite:
        q = q.limit(limite)
    return list(s.scalars(q).unique())


@dataclass
class CosteTrabajador:
    empleado_id: int
    empleado: str
    partes: int = 0
    horas: Decimal = CERO
    coste_horas: Decimal = CERO
    km: Decimal = CERO
    importe_km: Decimal = CERO
    dietas: Decimal = CERO
    comisiones: Decimal = CERO

    @property
    def total_gastos(self) -> Decimal:
        return self.importe_km + self.dietas + self.comisiones

    @property
    def coste_total(self) -> Decimal:
        return self.coste_horas + self.total_gastos


def desglose_por_trabajador(s: Session, desde: date | None = None, hasta: date | None = None) -> list[CosteTrabajador]:
    """Horas y costes por trabajador en un rango de fechas."""
    filas: dict[int, CosteTrabajador] = {}
    for p in listar_partes(s, FiltroPartes(fecha_desde=desde, fecha_hasta=hasta)):
        c = filas.setdefault(p.empleado_id, CosteTrabajador(p.empleado_id, p.empleado.nombre))
        c.partes += 1
        c.horas += p.horas
        c.coste_horas += p.coste_horas
        c.km += p.km
        c.importe_km += p.importe_km
        c.dietas += p.importe_dietas
        c.comisiones += p.comisiones
    return sorted(filas.values(), key=lambda c: c.coste_total, reverse=True)


@dataclass
class CosteProyecto:
    proyecto_id: int
    proyecto: str
    cliente: str | None
    horas: Decimal = CERO
    mano_obra: Decimal = CERO
    gastos_personal: Decimal = CERO  # km + dietas + comisiones
    facturas: Decimal = CERO  # base imponible (el IVA soportado se deduce, no es coste)
    n_facturas: int = 0

    @property
    def coste_total(self) -> Decimal:
        return self.mano_obra + self.gastos_personal + self.facturas


def coste_por_proyecto(s: Session, desde: date | None = None, hasta: date | None = None) -> list[CosteProyecto]:
    """Imputación de costes (horas + dietas + facturas) por Proyecto/Sitio."""
    filas = {p.id: CosteProyecto(p.id, p.nombre, p.cliente) for p in listar_proyectos(s, solo_activos=False)}
    for p in listar_partes(s, FiltroPartes(fecha_desde=desde, fecha_hasta=hasta)):
        c = filas[p.proyecto_id]
        c.horas += p.horas
        c.mano_obra += p.coste_horas
        c.gastos_personal += p.total_gastos
    q = select(Factura.proyecto_id, func.count(Factura.id), func.sum(Factura.base_imponible)).where(
        Factura.proyecto_id.is_not(None)
    )
    if desde:
        q = q.where(Factura.fecha_emision >= desde)
    if hasta:
        q = q.where(Factura.fecha_emision <= hasta)
    for pid, n, base in s.execute(q.group_by(Factura.proyecto_id)):
        filas[pid].n_facturas = n
        filas[pid].facturas = Decimal(str(base or 0)).quantize(Decimal("0.01"))
    return sorted((c for c in filas.values() if c.coste_total or c.horas), key=lambda c: c.coste_total, reverse=True)


# ======================================================================
# Dashboard
# ======================================================================
@dataclass
class MetricasDashboard:
    trimestre_label: str
    gasto_base: Decimal
    gasto_total: Decimal
    iva_soportado: Decimal
    n_facturas: int
    horas: Decimal
    dietas: Decimal
    km_importe: Decimal
    pendiente_pago: Decimal
    pendientes_revision: int


def metricas_dashboard(s: Session, hoy: date | None = None) -> MetricasDashboard:
    hoy = hoy or date.today()
    q, anio = trimestre_de(hoy)
    desde, hasta = rango_trimestre(q, anio)
    r = resumen_facturas(s, FiltroFacturas(trimestre=q, anio=anio))
    partes = listar_partes(s, FiltroPartes(fecha_desde=desde, fecha_hasta=hasta))
    return MetricasDashboard(
        trimestre_label=f"{q}T {anio}",
        gasto_base=r.base,
        gasto_total=r.total,
        iva_soportado=r.iva,
        n_facturas=r.n,
        horas=sum((p.horas for p in partes), CERO),
        dietas=sum((p.importe_dietas for p in partes), CERO),
        km_importe=sum((p.importe_km for p in partes), CERO),
        pendiente_pago=Decimal(str(s.scalar(
            select(func.coalesce(func.sum(Factura.total - Factura.importe_pagado), 0)).where(
                Factura.estado_pago != EstadoPago.PAGADO
            )
        ) or 0)).quantize(Decimal("0.01")),
        pendientes_revision=s.scalar(select(func.count(Factura.id)).where(Factura.requiere_revision.is_(True))) or 0,
    )
