"""Vista 4 · Registro de parte de trabajo (horas, km, dietas) pensado para el móvil."""
from __future__ import annotations

from datetime import date

import flet as ft

from .. import crud
from ..database import get_session
from ..schemas import EmpleadoCreate, FiltroPartes, GastoParteCreate, ParteTrabajoCreate, ProyectoCreate
from .comunes import CampoFecha, aviso, campo_numero, eur, fecha_es, mensaje_error, num, opciones

ATAJOS_GASTO = ["Comida 20€", "Dieta completa 53,34€", "Media dieta 26,67€", "Parking 5€"]


class ParteView:
    def __init__(self, page: ft.Page):
        self.page = page
        self.gastos: list[GastoParteCreate] = []

        self.empleado = ft.Dropdown(label="Trabajador", dense=True, expand=True)
        self.proyecto = ft.Dropdown(label="Proyecto / Cliente / Sitio", dense=True, expand=True)
        self.fecha = CampoFecha(page, "Fecha", date.today(), col={"xs": 12, "sm": 4})
        self.horas = campo_numero("Horas", "8", col={"xs": 4, "sm": 3}, sufijo="h")
        self.km = campo_numero("Km", "0", col={"xs": 4, "sm": 3}, sufijo="km")
        self.comisiones = campo_numero("Comisión", "0", col={"xs": 4, "sm": 2}, sufijo="€")
        self.nuevo_gasto = ft.TextField(label="Gasto (ej: Comida 20€)", dense=True, expand=True,
                                        on_submit=self._anadir_gasto)
        self.chips = ft.Row(wrap=True, spacing=6)
        self.total_gastos = ft.Text()
        self.descripcion = ft.TextField(label="Trabajo realizado (opcional)", dense=True, multiline=True)
        self.recientes = ft.Column(spacing=0)

        self.control = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            spacing=12,
            controls=[
                ft.Row([self.empleado, ft.IconButton(ft.Icons.PERSON_ADD, tooltip="Nuevo trabajador",
                                                     on_click=self._dialogo_empleado)]),
                ft.Row([self.proyecto, ft.IconButton(ft.Icons.ADD_LOCATION_ALT, tooltip="Nuevo proyecto",
                                                     on_click=self._dialogo_proyecto)]),
                ft.ResponsiveRow(spacing=8, run_spacing=8,
                                 controls=[self.fecha.control, self.horas, self.km, self.comisiones]),
                ft.Text("Gastos / dietas", weight=ft.FontWeight.BOLD),
                ft.Row([self.nuevo_gasto, ft.IconButton(ft.Icons.ADD_CIRCLE, on_click=self._anadir_gasto)]),
                ft.Row(wrap=True, spacing=6, controls=[
                    ft.OutlinedButton(t, on_click=lambda e, t=t: self._anadir_texto(t)) for t in ATAJOS_GASTO
                ]),
                self.chips,
                self.total_gastos,
                ft.ResponsiveRow([self.descripcion]),
                ft.FilledButton("Guardar parte", icon=ft.Icons.SAVE, on_click=self._guardar),
                ft.Divider(),
                ft.Text("Últimos partes", weight=ft.FontWeight.BOLD),
                self.recientes,
            ],
        )

    # ------------------------------------------------------------ datos
    def refrescar(self) -> None:
        with get_session() as s:
            self.empleado.options = opciones((e.id, e.nombre) for e in crud.listar_empleados(s))
            self.proyecto.options = opciones(
                (p.id, f"{p.nombre}" + (f" · {p.cliente}" if p.cliente else "")) for p in crud.listar_proyectos(s)
            )
            partes = crud.listar_partes(s, FiltroPartes(), limite=10)
            filas = [(p.id, p.fecha, p.empleado.nombre, p.proyecto.nombre, p.horas, p.total_gastos) for p in partes]
        if not self.empleado.value and len(self.empleado.options) == 1:
            self.empleado.value = self.empleado.options[0].key
        self.recientes.controls = [
            ft.ListTile(
                dense=True,
                title=ft.Text(f"{fecha_es(f)} · {emp} · {num(h)} h"),
                subtitle=ft.Text(f"{proy} · gastos {eur(g)}"),
                trailing=ft.IconButton(ft.Icons.DELETE_OUTLINE, tooltip="Eliminar",
                                       on_click=lambda e, pid=pid: self._eliminar(pid)),
            )
            for pid, f, emp, proy, h, g in filas
        ] or [ft.Text("Aún no hay partes", color=ft.Colors.ON_SURFACE_VARIANT)]
        self._pintar_gastos()

    # ------------------------------------------------------------ gastos
    def _anadir_gasto(self, _e):
        if self._anadir_texto(self.nuevo_gasto.value):
            self.nuevo_gasto.value = ""
            self.page.update()

    def _anadir_texto(self, texto: str) -> bool:
        try:
            self.gastos.append(GastoParteCreate.model_validate(texto))
        except Exception as exc:  # noqa: BLE001
            aviso(self.page, mensaje_error(exc), error=True)
            return False
        self._pintar_gastos()
        self.page.update()
        return True

    def _pintar_gastos(self):
        self.chips.controls = [
            ft.Chip(label=ft.Text(f"{g.concepto} {eur(g.importe)}"), on_delete=lambda e, i=i: self._quitar(i))
            for i, g in enumerate(self.gastos)
        ]
        total = sum((g.importe for g in self.gastos), 0)
        self.total_gastos.value = f"Total gastos: {eur(total)}" if self.gastos else ""

    def _quitar(self, i: int):
        self.gastos.pop(i)
        self._pintar_gastos()
        self.page.update()

    # ------------------------------------------------------------ guardar
    def _guardar(self, _e):
        try:
            if not self.proyecto.value:
                raise ValueError("Elige un proyecto (o créalo con el botón +)")
            datos = ParteTrabajoCreate(
                empleado_id=self.empleado.value,
                proyecto_id=self.proyecto.value,
                fecha=self.fecha.valor,
                horas=(self.horas.value or "0").replace(",", "."),
                km=(self.km.value or "0").replace(",", "."),
                comisiones=self.comisiones.value or "0",
                gastos=self.gastos,
                descripcion=self.descripcion.value or None,
            )
            with get_session() as s:
                p = crud.crear_parte(s, datos)
                msg = f"Parte guardado: {num(p.horas)} h · gastos {eur(p.total_gastos)}"
        except Exception as exc:  # noqa: BLE001
            aviso(self.page, mensaje_error(exc), error=True)
            return
        self.gastos.clear()
        self.km.value, self.comisiones.value, self.descripcion.value = "0", "0", ""
        aviso(self.page, msg)
        self.refrescar()
        self.page.update()

    def _eliminar(self, parte_id: int):
        with get_session() as s:
            crud.eliminar_parte(s, parte_id)
        self.refrescar()
        self.page.update()

    # ------------------------------------------------------------ altas rápidas
    def _dialogo(self, titulo: str, campos: list[ft.Control], al_guardar):
        def guardar(_e):
            try:
                with get_session() as s:
                    nuevo_id = al_guardar(s)
            except Exception as exc:  # noqa: BLE001
                aviso(self.page, mensaje_error(exc), error=True)
                return
            self.page.pop_dialog()
            self.refrescar()
            return nuevo_id

        self.page.show_dialog(ft.AlertDialog(
            title=ft.Text(titulo),
            content=ft.Column(campos, tight=True, width=360),
            actions=[ft.TextButton("Cancelar", on_click=lambda e: self.page.pop_dialog()),
                     ft.FilledButton("Guardar", on_click=guardar)],
        ))

    def _dialogo_empleado(self, _e):
        nombre = ft.TextField(label="Nombre", autofocus=True)
        coste = campo_numero("Coste empresa / hora", "0", sufijo="€")
        tarifa = campo_numero("€/km (vacío = 0,26)", "")

        def crear(s):
            e = crud.crear_empleado(s, EmpleadoCreate(nombre=nombre.value, coste_hora=coste.value or "0",
                                                      tarifa_km=(tarifa.value or "").replace(",", ".") or None))
            self.empleado.value = str(e.id)

        self._dialogo("Nuevo trabajador", [nombre, coste, tarifa], crear)

    def _dialogo_proyecto(self, _e):
        nombre = ft.TextField(label="Proyecto / Obra", autofocus=True)
        cliente = ft.TextField(label="Cliente")
        ubicacion = ft.TextField(label="Ubicación / Sitio")

        def crear(s):
            p = crud.crear_proyecto(s, ProyectoCreate(nombre=nombre.value, cliente=cliente.value or None,
                                                      ubicacion=ubicacion.value or None))
            self.proyecto.value = str(p.id)

        self._dialogo("Nuevo proyecto", [nombre, cliente, ubicacion], crear)
