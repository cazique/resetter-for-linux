"""Utilidades de interfaz compartidas por todas las vistas."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import flet as ft
from pydantic import ValidationError

from ..crud import ErrorNegocio


def refrescar_control(control: ft.Control) -> None:
    """update() que no falla si el control aún no está montado en la página."""
    try:
        control.update()
    except RuntimeError:
        pass


def eur(valor: Decimal | float | None) -> str:
    """1234.5 -> '1.234,50 €'"""
    if valor is None:
        return "-"
    return f"{Decimal(valor):,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def num(valor: Decimal | float | None, decimales: int = 2) -> str:
    if valor is None:
        return ""
    return f"{Decimal(valor):.{decimales}f}".replace(".", ",")


def fecha_es(d: date | None) -> str:
    return d.strftime("%d/%m/%Y") if d else ""


def parse_fecha_es(texto: str | None) -> date | None:
    if not texto or not texto.strip():
        return None
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(texto.strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Fecha no válida: '{texto}' (usa dd/mm/aaaa)")


_NOMBRES_CAMPO = {
    "proveedor.nombre": "Proveedor", "proveedor.nif": "CIF/NIF", "proveedor": "Proveedor",
    "numero": "Nº factura", "fecha_emision": "Fecha", "lineas_iva": "Desglose IVA",
    "lineas_iva.base": "Base", "lineas_iva.tipo": "IVA %", "lineas_iva.cuota": "Cuota IVA",
    "total": "Total", "irpf_porcentaje": "IRPF %", "importe_pagado": "Pagado",
    "empleado_id": "Trabajador", "proyecto_id": "Proyecto", "fecha": "Fecha", "horas": "Horas",
    "km": "Km", "comisiones": "Comisión", "nombre": "Nombre", "coste_hora": "Coste/hora",
}
_MENSAJES_TIPO = {
    "missing": "obligatorio",
    "string_too_short": "obligatorio",
    "string_type": "obligatorio",
    "int_type": "elige una opción",
    "int_parsing": "elige una opción",
    "too_short": "indica al menos una base imponible",
    "decimal_parsing": "número no válido",
    "decimal_type": "número no válido",
    "greater_than_equal": "no puede ser negativo",
    "less_than_equal": "valor demasiado alto",
    "date_type": "fecha no válida",
}


def mensaje_error(exc: Exception) -> str:
    """Convierte errores de validación/negocio en un texto corto para el usuario."""
    if isinstance(exc, ValidationError):
        partes = []
        for e in exc.errors()[:3]:
            ruta = ".".join(str(x) for x in e["loc"] if not isinstance(x, int))
            campo = _NOMBRES_CAMPO.get(ruta, ruta)
            msg = _MENSAJES_TIPO.get(e["type"]) or e["msg"].removeprefix("Value error, ")
            partes.append(f"{campo}: {msg}" if campo else msg)
        return " · ".join(partes)
    if isinstance(exc, (ErrorNegocio, ValueError)):
        return str(exc)
    return f"Error inesperado: {exc}"


def aviso(page: ft.Page, texto: str, error: bool = False) -> None:
    page.show_dialog(
        ft.SnackBar(
            content=ft.Text(texto, color=ft.Colors.ON_ERROR_CONTAINER if error else None),
            bgcolor=ft.Colors.ERROR_CONTAINER if error else None,
            duration=ft.Duration(seconds=5 if error else 3),
        )
    )


def campo_numero(label: str, valor: str = "", sufijo: str | None = None, **kw) -> ft.TextField:
    return ft.TextField(
        label=label,
        value=valor,
        keyboard_type=ft.KeyboardType.NUMBER,
        suffix=sufijo,
        dense=True,
        **kw,
    )


class CampoFecha:
    """TextField dd/mm/aaaa + botón de calendario."""

    def __init__(self, page: ft.Page, label: str, valor: date | None = None, col=None, on_change=None):
        self.page = page
        self._on_change = on_change
        self.texto = ft.TextField(
            label=label,
            value=fecha_es(valor),
            hint_text="dd/mm/aaaa",
            keyboard_type=ft.KeyboardType.DATETIME,
            dense=True,
            expand=True,
            on_submit=lambda e: self._notificar(),
            suffix=ft.IconButton(ft.Icons.CALENDAR_MONTH, on_click=self._abrir, tooltip="Calendario"),
        )
        self.control = ft.Container(self.texto, col=col) if col else self.texto

    def _abrir(self, _e):
        try:
            actual = self.valor or date.today()
        except ValueError:
            actual = date.today()
        self.page.show_dialog(
            ft.DatePicker(
                value=datetime(actual.year, actual.month, actual.day),
                first_date=datetime(2015, 1, 1),
                last_date=datetime(date.today().year + 1, 12, 31),
                on_change=self._elegida,
            )
        )

    def _elegida(self, e):
        v = e.control.value
        if v:
            self.texto.value = fecha_es(v.date() if isinstance(v, datetime) else v)
            refrescar_control(self.texto)
            self._notificar()

    def _notificar(self):
        if self._on_change:
            self._on_change()

    @property
    def valor(self) -> date | None:
        return parse_fecha_es(self.texto.value)

    @valor.setter
    def valor(self, d: date | None) -> None:
        self.texto.value = fecha_es(d)


def tarjeta_metrica(titulo: str, valor: str, icono, color, subtitulo: str = "") -> ft.Container:
    return ft.Container(
        col={"xs": 6, "md": 3},
        padding=14,
        border_radius=14,
        bgcolor=ft.Colors.with_opacity(0.10, color),
        content=ft.Column(
            spacing=4,
            controls=[
                ft.Row([ft.Icon(icono, color=color, size=20), ft.Text(titulo, size=12, expand=True)]),
                ft.Text(valor, size=20, weight=ft.FontWeight.BOLD),
                ft.Text(subtitulo, size=11, color=ft.Colors.ON_SURFACE_VARIANT) if subtitulo else ft.Container(),
            ],
        ),
    )


def opciones(pares) -> list[ft.DropdownOption]:
    return [ft.DropdownOption(key=str(k), text=t) for k, t in pares]
