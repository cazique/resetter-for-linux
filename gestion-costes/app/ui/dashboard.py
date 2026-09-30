"""Vista 1 · Dashboard de resumen del trimestre actual."""
from __future__ import annotations

from collections.abc import Callable

import flet as ft

from .. import crud
from ..database import get_session
from ..schemas import FiltroFacturas
from .comunes import eur, fecha_es, num, tarjeta_metrica


class DashboardView:
    def __init__(self, page: ft.Page, ir_a: Callable[[int], None]):
        self.page = page
        self.ir_a = ir_a
        self.metricas = ft.ResponsiveRow(spacing=10, run_spacing=10)
        self.revision = ft.Column(spacing=0)
        self.control = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            spacing=16,
            controls=[
                ft.Row(
                    wrap=True,
                    controls=[
                        ft.FilledButton("Escanear factura", icon=ft.Icons.DOCUMENT_SCANNER, on_click=lambda e: ir_a(1)),
                        ft.OutlinedButton("Nuevo parte", icon=ft.Icons.MORE_TIME, on_click=lambda e: ir_a(3)),
                    ],
                ),
                self.metricas,
                ft.Text("Facturas pendientes de revisión", size=16, weight=ft.FontWeight.BOLD),
                self.revision,
            ],
        )

    def refrescar(self) -> None:
        with get_session() as s:
            m = crud.metricas_dashboard(s)
            pendientes = crud.listar_facturas(s, FiltroFacturas(solo_revision=True), limite=8)
            filas = [(f.proveedor.nombre, f.numero, f.fecha_emision, f.total) for f in pendientes]

        self.metricas.controls = [
            tarjeta_metrica(f"Gastos {m.trimestre_label}", eur(m.gasto_base), ft.Icons.RECEIPT_LONG,
                            ft.Colors.INDIGO, f"{m.n_facturas} facturas · {eur(m.gasto_total)} con IVA"),
            tarjeta_metrica("IVA soportado", eur(m.iva_soportado), ft.Icons.PERCENT, ft.Colors.TEAL,
                            "deducible en el 303"),
            tarjeta_metrica("Horas imputadas", num(m.horas, 1) + " h", ft.Icons.SCHEDULE, ft.Colors.ORANGE,
                            m.trimestre_label),
            tarjeta_metrica("Dietas + km", eur(m.dietas + m.km_importe), ft.Icons.RESTAURANT, ft.Colors.PINK,
                            f"dietas {eur(m.dietas)} · km {eur(m.km_importe)}"),
            tarjeta_metrica("Pendiente de pago", eur(m.pendiente_pago), ft.Icons.PAYMENTS, ft.Colors.RED,
                            "todas las facturas"),
            tarjeta_metrica("Por revisar", str(m.pendientes_revision), ft.Icons.WARNING_AMBER, ft.Colors.AMBER,
                            "lecturas OCR dudosas"),
        ]
        self.revision.controls = [
            ft.ListTile(
                leading=ft.Icon(ft.Icons.WARNING_AMBER, color=ft.Colors.AMBER),
                title=ft.Text(f"{prov} · {numero}"),
                subtitle=ft.Text(f"{fecha_es(fecha)} · {eur(total)}"),
                dense=True,
                on_click=lambda e: self.ir_a(2),
            )
            for prov, numero, fecha, total in filas
        ] or [ft.Text("Nada pendiente 👍", color=ft.Colors.ON_SURFACE_VARIANT)]
