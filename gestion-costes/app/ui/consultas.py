"""Vista 3 · Consultas y reportes: tabla filtrable + exportación Excel/CSV."""
from __future__ import annotations

from datetime import date

import flet as ft

from .. import crud
from ..database import get_session
from ..export import costes_a_excel, facturas_a_csv, facturas_a_excel
from ..models import EstadoPago
from ..schemas import FacturaUpdate, FiltroFacturas, FiltroPartes
from .comunes import CampoFecha, aviso, eur, fecha_es, mensaje_error, num, opciones, refrescar_control

MODOS = [("facturas", "Facturas"), ("trabajadores", "Por trabajador"), ("proyectos", "Por proyecto")]


def _celda(texto, derecha: bool = False, negrita: bool = False, color=None) -> ft.DataCell:
    return ft.DataCell(ft.Text(texto, text_align=ft.TextAlign.RIGHT if derecha else None,
                               weight=ft.FontWeight.BOLD if negrita else None, color=color))


class ConsultasView:
    def __init__(self, page: ft.Page):
        self.page = page
        self.picker = ft.FilePicker()
        anio = date.today().year
        self.modo = ft.Dropdown(label="Ver", value="facturas", dense=True, col={"xs": 12, "sm": 4},
                                options=opciones(MODOS), on_select=lambda e: self.refrescar())
        self.texto = ft.TextField(label="Buscar proveedor / CIF / nº", dense=True, col={"xs": 12, "sm": 8},
                                  prefix_icon=ft.Icons.SEARCH, on_submit=lambda e: self.refrescar())
        self.anio = ft.Dropdown(label="Año", dense=True, value=str(anio), col={"xs": 4, "sm": 2},
                                options=opciones([("", "Todos")] + [(a, a) for a in range(anio, anio - 6, -1)]),
                                on_select=lambda e: self.refrescar())
        self.trim = ft.Dropdown(label="Trimestre", dense=True, value="", col={"xs": 4, "sm": 2},
                                options=opciones([("", "Todos"), (1, "1T"), (2, "2T"), (3, "3T"), (4, "4T")]),
                                on_select=lambda e: self.refrescar())
        self.estado = ft.Dropdown(label="Estado", dense=True, value="", col={"xs": 4, "sm": 2},
                                  options=opciones([("", "Todos")] + [(e.value, e.value.capitalize()) for e in EstadoPago]),
                                  on_select=lambda e: self.refrescar())
        self.desde = CampoFecha(page, "Desde", col={"xs": 6, "sm": 3}, on_change=self.refrescar)
        self.hasta = CampoFecha(page, "Hasta", col={"xs": 6, "sm": 3}, on_change=self.refrescar)

        self.tabla = ft.DataTable(columns=[ft.DataColumn(ft.Text("-"))], column_spacing=18,
                                  horizontal_margin=8, heading_row_height=40, data_row_min_height=36)
        self.totales = ft.Text(weight=ft.FontWeight.BOLD)
        self.control = ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.ResponsiveRow(
                    spacing=8, run_spacing=8,
                    controls=[self.modo, self.texto, self.anio, self.trim, self.estado,
                              self.desde.control, self.hasta.control],
                ),
                ft.Row(
                    wrap=True,
                    controls=[
                        ft.FilledTonalButton("Filtrar", icon=ft.Icons.FILTER_ALT, on_click=lambda e: self.refrescar()),
                        ft.FilledButton("Exportar Excel", icon=ft.Icons.DOWNLOAD, on_click=self._exportar_excel),
                        ft.OutlinedButton("CSV", icon=ft.Icons.TABLE_VIEW, on_click=self._exportar_csv),
                    ],
                ),
                self.totales,
                ft.Row([self.tabla], scroll=ft.ScrollMode.AUTO),  # scroll horizontal en móvil
            ],
        )

    # ------------------------------------------------------------ filtros
    def _filtro(self) -> FiltroFacturas:
        return FiltroFacturas(
            anio=int(self.anio.value) if self.anio.value else None,
            trimestre=int(self.trim.value) if self.trim.value and self.anio.value else None,
            texto=self.texto.value or None,
            estado_pago=self.estado.value or None,
            fecha_desde=self.desde.valor,
            fecha_hasta=self.hasta.valor,
        )

    def _rango(self) -> tuple[date | None, date | None]:
        f = self._filtro()
        if f.anio and not f.trimestre and not (f.fecha_desde or f.fecha_hasta):
            return date(f.anio, 1, 1), date(f.anio, 12, 31)
        return f.rango_efectivo()

    def _periodo(self) -> str:
        d, h = self._rango()
        return f"{fecha_es(d) or '…'} – {fecha_es(h) or '…'}"

    # ------------------------------------------------------------ tabla
    def refrescar(self) -> None:
        try:
            {"facturas": self._tabla_facturas, "trabajadores": self._tabla_trabajadores,
             "proyectos": self._tabla_proyectos}[self.modo.value]()
        except Exception as exc:  # noqa: BLE001
            aviso(self.page, mensaje_error(exc), error=True)
        refrescar_control(self.control)

    def _tabla_facturas(self):
        with get_session() as s:
            filtro = self._filtro()
            facturas = crud.listar_facturas(s, filtro, limite=500)
            r = crud.resumen_facturas(s, filtro)
        self.tabla.columns = [ft.DataColumn(ft.Text(t), numeric=n) for t, n in [
            ("Fecha", False), ("Proveedor", False), ("Nº", False), ("Base", True), ("IVA", True),
            ("Total", True), ("Estado", False), ("", False)]]
        self.tabla.rows = [
            ft.DataRow(
                on_select_change=lambda e, fid=f.id: self._detalle(fid),
                cells=[
                    _celda(fecha_es(f.fecha_emision)),
                    _celda(f.proveedor.nombre[:28]),
                    _celda(f.numero),
                    _celda(eur(f.base_imponible), True),
                    _celda(eur(f.cuota_iva), True),
                    _celda(eur(f.total), True, True),
                    _celda(f.estado_pago.value, color={EstadoPago.PAGADO: ft.Colors.GREEN, EstadoPago.PARCIAL: ft.Colors.BLUE}.get(
                        f.estado_pago, ft.Colors.ORANGE)),
                    _celda("⚠️" if f.requiere_revision else ""),
                ],
            )
            for f in facturas
        ]
        self.totales.value = (f"{r.n} facturas · Base {eur(r.base)} · IVA {eur(r.iva)} · IRPF {eur(r.irpf)} · "
                              f"Total {eur(r.total)} · Pendiente {eur(r.pendiente_pago)}")

    def _tabla_trabajadores(self):
        with get_session() as s:
            filas = crud.desglose_por_trabajador(s, *self._rango())
        self.tabla.columns = [ft.DataColumn(ft.Text(t), numeric=n) for t, n in [
            ("Empleado", False), ("Horas", True), ("Coste horas", True), ("Km", True), ("Dietas", True),
            ("Comisiones", True), ("Coste total", True)]]
        self.tabla.rows = [
            ft.DataRow(cells=[_celda(c.empleado), _celda(num(c.horas), True), _celda(eur(c.coste_horas), True),
                              _celda(f"{num(c.km, 0)} ({eur(c.importe_km)})", True), _celda(eur(c.dietas), True),
                              _celda(eur(c.comisiones), True), _celda(eur(c.coste_total), True, True)])
            for c in filas
        ]
        self.totales.value = (f"{len(filas)} trabajadores · {num(sum(c.horas for c in filas))} h · "
                              f"Coste {eur(sum(c.coste_total for c in filas))} · {self._periodo()}")

    def _tabla_proyectos(self):
        with get_session() as s:
            filas = crud.coste_por_proyecto(s, *self._rango())
        self.tabla.columns = [ft.DataColumn(ft.Text(t), numeric=n) for t, n in [
            ("Proyecto", False), ("Horas", True), ("Mano obra", True), ("Dietas/km", True),
            ("Facturas", True), ("Coste total", True)]]
        self.tabla.rows = [
            ft.DataRow(cells=[_celda(c.proyecto), _celda(num(c.horas), True), _celda(eur(c.mano_obra), True),
                              _celda(eur(c.gastos_personal), True), _celda(f"{eur(c.facturas)} ({c.n_facturas})", True),
                              _celda(eur(c.coste_total), True, True)])
            for c in filas
        ]
        self.totales.value = f"Coste imputado total {eur(sum(c.coste_total for c in filas))} · {self._periodo()}"

    # ------------------------------------------------------------ detalle factura
    def _detalle(self, factura_id: int):
        with get_session() as s:
            f = crud.obtener_factura(s, factura_id)
            lineas = "\n".join(f"  IVA {num(l.tipo, 0)}%: base {eur(l.base)} · cuota {eur(l.cuota)}" for l in f.lineas_iva)
            texto = (f"{f.proveedor.nombre} ({f.proveedor.nif})\nFactura {f.numero} · {fecha_es(f.fecha_emision)} · "
                     f"{f.trimestre}T {f.anio}\n{lineas}\nIRPF: {eur(f.irpf_importe)}\nTOTAL: {eur(f.total)}\n"
                     f"Categoría: {f.categoria.nombre if f.categoria else '-'}\nEstado: {f.estado_pago.value}"
                     f"{' (' + fecha_es(f.fecha_pago) + ')' if f.fecha_pago else ''}"
                     f"{' · pagado ' + eur(f.importe_pagado) + ' · pendiente ' + eur(f.pendiente) if f.estado_pago is EstadoPago.PARCIAL else ''}\n"
                     f"Archivo: {f.archivo_url or '-'}\n{f.notas or ''}")
            pagada = f.estado_pago is EstadoPago.PAGADO
            revisar = f.requiere_revision

        def accion(fn):
            def _h(_e):
                try:
                    with get_session() as s:
                        fn(s)
                except Exception as exc:  # noqa: BLE001
                    aviso(self.page, mensaje_error(exc), error=True)
                self.page.pop_dialog()
                self.refrescar()
            return _h

        acciones = [
            ft.TextButton("Eliminar", icon=ft.Icons.DELETE, style=ft.ButtonStyle(color=ft.Colors.ERROR),
                          on_click=accion(lambda s: crud.eliminar_factura(s, factura_id))),
        ]
        if revisar:
            acciones.append(ft.TextButton("Revisada ✓", on_click=accion(
                lambda s: crud.actualizar_factura(s, factura_id, FacturaUpdate(requiere_revision=False)))))
        acciones.append(ft.TextButton(
            "Marcar pendiente" if pagada else "Marcar pagada",
            on_click=accion(lambda s: crud.actualizar_factura(s, factura_id, FacturaUpdate(
                estado_pago=EstadoPago.PENDIENTE if pagada else EstadoPago.PAGADO)))))
        acciones.append(ft.TextButton("Cerrar", on_click=lambda e: self.page.pop_dialog()))
        self.page.show_dialog(ft.AlertDialog(title=ft.Text("Factura"), content=ft.Text(texto, selectable=True),
                                             actions=acciones))

    # ------------------------------------------------------------ exportación
    async def _guardar(self, nombre: str, datos: bytes):
        try:
            await self.picker.save_file(dialog_title="Guardar exportación", file_name=nombre, src_bytes=datos)
        except Exception as exc:  # noqa: BLE001
            aviso(self.page, mensaje_error(exc), error=True)

    def _sufijo(self) -> str:
        f = self._filtro()
        if f.trimestre:
            return f"{f.anio}_{f.trimestre}T"
        return str(f.anio) if f.anio else date.today().isoformat()

    async def _exportar_excel(self, _e):
        try:
            with get_session() as s:
                if self.modo.value == "facturas":
                    filtro = self._filtro()
                    datos = facturas_a_excel(crud.listar_facturas(s, filtro), crud.resumen_facturas(s, filtro),
                                             self._periodo())
                    nombre = f"facturas_{self._sufijo()}.xlsx"
                else:
                    d, h = self._rango()
                    datos = costes_a_excel(crud.desglose_por_trabajador(s, d, h), crud.coste_por_proyecto(s, d, h),
                                           self._periodo(),
                                           crud.listar_partes(s, FiltroPartes(fecha_desde=d, fecha_hasta=h)))
                    nombre = f"costes_{self._sufijo()}.xlsx"
        except Exception as exc:  # noqa: BLE001
            aviso(self.page, mensaje_error(exc), error=True)
            return
        await self._guardar(nombre, datos)

    async def _exportar_csv(self, _e):
        with get_session() as s:
            datos = facturas_a_csv(crud.listar_facturas(s, self._filtro()))
        await self._guardar(f"facturas_{self._sufijo()}.csv", datos)
