"""Vista 2 · Captura/escaneo: foto o PDF a un lado, formulario precargado por la IA al otro."""
from __future__ import annotations

import asyncio
import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path

import flet as ft

from .. import crud
from ..config import directorio_datos, get_settings
from ..database import get_session
from ..fiscal import trimestre_de
from ..models import EstadoPago
from ..ocr_service import OCRService, ResultadoOCR
from ..schemas import FacturaCreate
from .comunes import CampoFecha, aviso, campo_numero, mensaje_error, num, opciones, refrescar_control

N_LINEAS_IVA = 3
EXTENSIONES = ["jpg", "jpeg", "png", "webp", "pdf"]


class EscaneoView:
    def __init__(self, page: ft.Page):
        self.page = page
        self.picker = ft.FilePicker()  # servicio: se registra solo en la página
        self.archivo: bytes | None = None
        self.nombre_archivo = ""
        self.resultado: ResultadoOCR | None = None

        # ---------------- lado izquierdo: documento
        self.preview = ft.Container(
            height=280,
            border_radius=12,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            alignment=ft.Alignment.CENTER,
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.RECEIPT_LONG, size=64, color=ft.Colors.ON_SURFACE_VARIANT),
                    ft.Text("Haz una foto o sube la factura", color=ft.Colors.ON_SURFACE_VARIANT),
                ],
            ),
        )
        self.estado = ft.Row(visible=False, controls=[ft.ProgressRing(width=18, height=18), ft.Text("Leyendo con IA…")])
        self.alertas = ft.Column(spacing=2)
        izquierda = ft.Column(
            col={"xs": 12, "md": 5},
            controls=[
                ft.Row(
                    wrap=True,
                    controls=[
                        ft.FilledButton("Foto / Galería", icon=ft.Icons.PHOTO_CAMERA, on_click=self._elegir_foto),
                        ft.OutlinedButton("Subir PDF o archivo", icon=ft.Icons.UPLOAD_FILE, on_click=self._elegir_archivo),
                    ],
                ),
                self.preview,
                self.estado,
                self.alertas,
            ],
        )

        # ---------------- lado derecho: formulario
        self.prov_nombre = ft.TextField(label="Proveedor", dense=True, col={"xs": 12, "sm": 7})
        self.prov_nif = ft.TextField(label="CIF/NIF", dense=True, col={"xs": 12, "sm": 5},
                                     capitalization=ft.TextCapitalization.CHARACTERS)
        self.numero = ft.TextField(label="Nº factura", hint_text="vacío = ticket sin nº", dense=True,
                                   col={"xs": 6})
        self.fecha = CampoFecha(page, "Fecha emisión", date.today(), col={"xs": 6}, on_change=self._actualiza_trimestre)
        self.trimestre = ft.Text("", color=ft.Colors.PRIMARY)
        self.lineas = [
            (campo_numero("IVA %", "21" if i == 0 else "", col={"xs": 3}),
             campo_numero("Base", col={"xs": 5}, sufijo="€"),
             campo_numero("Cuota IVA", col={"xs": 4}, sufijo="€"))
            for i in range(N_LINEAS_IVA)
        ]
        for tipo, base, cuota in self.lineas:
            base.on_change = tipo.on_change = lambda e, t=tipo, b=base, c=cuota: self._auto_cuota(t, b, c)
        self.irpf = campo_numero("IRPF %", "0", col={"xs": 4})
        self.total = campo_numero("TOTAL", col={"xs": 8}, sufijo="€")
        self.categoria = ft.Dropdown(label="Categoría", dense=True, expand=True, col={"xs": 12, "sm": 6})
        self.proyecto = ft.Dropdown(label="Proyecto / Sitio", dense=True, expand=True, col={"xs": 12, "sm": 6})
        self.estado_pago = ft.Dropdown(
            label="Estado", dense=True, col={"xs": 6}, value=EstadoPago.PENDIENTE.value,
            options=opciones([(e.value, e.value.capitalize()) for e in EstadoPago]),
            on_select=self._cambia_estado,
        )
        self.pagado = campo_numero("Pagado", col={"xs": 6}, sufijo="€", visible=False)
        self.revisar = ft.Checkbox(label="Marcar para revisar", col={"xs": 6})
        self.notas = ft.TextField(label="Notas", dense=True, multiline=True, col={"xs": 12})

        derecha = ft.Container(
            col={"xs": 12, "md": 7},
            content=ft.ResponsiveRow(
                spacing=8,
                run_spacing=8,
                controls=[
                    self.prov_nombre, self.prov_nif, self.numero, self.fecha.control,
                    ft.Container(self.trimestre, col={"xs": 12}),
                    ft.Text("Desglose de IVA", weight=ft.FontWeight.BOLD, col={"xs": 12}),
                    *[c for linea in self.lineas for c in linea],
                    self.irpf, self.total, self.categoria, self.proyecto, self.estado_pago, self.pagado, self.revisar,
                    self.notas,
                    ft.Row(
                        col={"xs": 12},
                        alignment=ft.MainAxisAlignment.END,
                        controls=[
                            ft.TextButton("Limpiar", on_click=lambda e: self._limpiar()),
                            ft.FilledButton("Guardar factura", icon=ft.Icons.SAVE, on_click=self._guardar),
                        ],
                    ),
                ],
            ),
        )
        self.control = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            controls=[ft.ResponsiveRow(spacing=16, controls=[izquierda, derecha])],
        )
        self._actualiza_trimestre()

    # ------------------------------------------------------------ ciclo de vida
    def refrescar(self) -> None:
        with get_session() as s:
            crud.sembrar_datos_iniciales(s)
            self.categoria.options = opciones((c.id, c.nombre) for c in crud.listar_categorias(s))
            self.proyecto.options = [ft.DropdownOption(key="", text="— Sin proyecto —")] + opciones(
                (p.id, p.nombre) for p in crud.listar_proyectos(s)
            )

    # ------------------------------------------------------------ captura
    async def _elegir_foto(self, _e):
        await self._elegir(ft.FilePickerFileType.IMAGE, None)

    async def _elegir_archivo(self, _e):
        await self._elegir(ft.FilePickerFileType.CUSTOM, EXTENSIONES)

    async def _elegir(self, tipo, extensiones):
        files = await self.picker.pick_files(
            dialog_title="Selecciona la factura",
            file_type=tipo,
            allowed_extensions=extensiones,
            with_data=True,  # necesario en web y Android (no hay ruta de disco)
        )
        if not files:
            return
        f = files[0]
        datos = f.bytes if f.bytes is not None else Path(f.path).read_bytes()
        self.archivo, self.nombre_archivo = datos, f.name
        self._mostrar_preview()
        await self._leer_con_ia()

    def _mostrar_preview(self):
        if self.nombre_archivo.lower().endswith(".pdf"):
            self.preview.content = ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                controls=[ft.Icon(ft.Icons.PICTURE_AS_PDF, size=72, color=ft.Colors.RED),
                          ft.Text(self.nombre_archivo)],
            )
        else:
            self.preview.content = ft.InteractiveViewer(
                content=ft.Image(src=self.archivo, fit=ft.BoxFit.CONTAIN), max_scale=5
            )
        self.page.update()

    async def _leer_con_ia(self):
        self.alertas.controls.clear()
        if not get_settings().ocr_configurado:
            self.alertas.controls.append(
                ft.Text("Lectura automática desactivada: añade tu API key en Ajustes (engranaje, arriba a la derecha). "
                        "Puedes rellenar el formulario a mano.", color=ft.Colors.ON_SURFACE_VARIANT)
            )
            self.page.update()
            return
        self.estado.visible = True
        self.page.update()
        try:
            servicio = OCRService()
            res = await asyncio.to_thread(servicio.extraer, self.archivo, self.nombre_archivo)
        except Exception as exc:  # noqa: BLE001 - se muestra al usuario
            aviso(self.page, f"No se pudo leer: {mensaje_error(exc)}", error=True)
        else:
            self.resultado = res
            self._rellenar(res)
        finally:
            self.estado.visible = False
            self.page.update()

    # ------------------------------------------------------------ formulario
    def _rellenar(self, r: ResultadoOCR):
        self.prov_nombre.value = r.proveedor_nombre or ""
        self.prov_nif.value = r.proveedor_nif or ""
        self.numero.value = r.numero_factura or ""
        self.fecha.valor = r.fecha_emision
        for i, (tipo, base, cuota) in enumerate(self.lineas):
            l = r.lineas_iva[i] if i < len(r.lineas_iva) else None
            tipo.value = num(l.tipo, 2).rstrip("0").rstrip(",") if l else ""
            base.value, cuota.value = (num(l.base), num(l.cuota)) if l else ("", "")
        self.irpf.value = num(r.irpf_porcentaje)
        self.total.value = num(r.total)
        self.revisar.value = r.requiere_revision
        with get_session() as s:
            cat = crud.categoria_por_nombre(s, r.categoria_sugerida)
            if r.proveedor_nif:  # si ya conocemos al proveedor, su categoría habitual manda
                prov = next((p for p in crud.buscar_proveedores(s, r.proveedor_nif, 1) if p.nif == r.proveedor_nif), None)
                if prov and prov.categoria_defecto_id:
                    cat = prov.categoria_defecto
            self.categoria.value = str(cat.id) if cat else None
        self._actualiza_trimestre()

        color = ft.Colors.GREEN if not r.requiere_revision else ft.Colors.ORANGE
        self.alertas.controls = [
            ft.Text(f"Confianza {r.confianza:.0%} · {r.modelo} · {r.intentos} lectura(s)", color=color,
                    weight=ft.FontWeight.BOLD)
        ] + [
            ft.Text(("⛔ " if a.nivel == "error" else "⚠️ " if a.nivel == "aviso" else "ℹ️ ") + a.mensaje, size=12)
            for a in r.alertas
        ]

    def _auto_cuota(self, tipo: ft.TextField, base: ft.TextField, cuota: ft.TextField):
        """Al teclear base y tipo, propone la cuota (solo si el usuario no la ha escrito)."""
        try:
            t, b = Decimal(tipo.value.replace(",", ".")), Decimal(base.value.replace(",", "."))
        except Exception:  # noqa: BLE001
            return
        if not cuota.value or cuota.data == "auto":
            cuota.value, cuota.data = num((b * t / 100).quantize(Decimal("0.01"))), "auto"
            refrescar_control(cuota)

    def _cambia_estado(self, _e=None):
        self.pagado.visible = self.estado_pago.value == EstadoPago.PARCIAL.value
        refrescar_control(self.pagado)

    def _actualiza_trimestre(self):
        try:
            f = self.fecha.valor
            self.trimestre.value = "Trimestre fiscal: {}T {}".format(*trimestre_de(f)) if f else ""
        except ValueError as exc:
            self.trimestre.value = str(exc)
        refrescar_control(self.trimestre)

    def _limpiar(self):
        self.archivo, self.resultado = None, None
        self.estado_pago.value, self.pagado.visible = EstadoPago.PENDIENTE.value, False
        for c in [self.prov_nombre, self.prov_nif, self.numero, self.total, self.notas, self.pagado,
                  *[c for linea in self.lineas for c in linea]]:
            c.value, c.data = "", None
        self.lineas[0][0].value = "21"
        self.irpf.value = "0"
        self.fecha.valor = date.today()
        self.revisar.value = False
        self.alertas.controls.clear()
        self.preview.content = ft.Text("Haz una foto o sube la factura", color=ft.Colors.ON_SURFACE_VARIANT)
        self.page.update()

    def _guardar_archivo(self, fecha: date) -> str | None:
        if not self.archivo:
            return None
        q, anio = trimestre_de(fecha)
        ext = Path(self.nombre_archivo).suffix.lower() or ".jpg"
        rel = Path("facturas") / str(anio) / f"Q{q}" / f"{uuid.uuid4().hex[:12]}{ext}"
        destino = directorio_datos() / rel
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(self.archivo)
        return rel.as_posix()

    def _guardar(self, _e):
        ruta = None
        try:
            fecha = self.fecha.valor
            lineas = [
                {"tipo": t.value.replace(",", "."), "base": b.value, "cuota": c.value or None}
                for t, b, c in self.lineas
                if b.value.strip()
            ]
            datos = FacturaCreate.model_validate({
                "numero": self.numero.value,
                "fecha_emision": fecha,
                "proveedor": {"nombre": self.prov_nombre.value, "nif": self.prov_nif.value},
                "lineas_iva": lineas,
                "irpf_porcentaje": (self.irpf.value or "0").replace(",", "."),
                "total": self.total.value or None,
                "categoria_id": self.categoria.value or None,
                "proyecto_id": self.proyecto.value or None,
                "estado_pago": self.estado_pago.value,
                "importe_pagado": self.pagado.value or None,
                "requiere_revision": bool(self.revisar.value),
                "ocr_confianza": self.resultado.confianza if self.resultado else None,
                "notas": self.notas.value or None,
            })
            ruta = self._guardar_archivo(datos.fecha_emision)
            datos.archivo_url = ruta
            with get_session() as s:
                f = crud.crear_factura(s, datos)
                msg = f"Factura {f.numero} guardada ({f.trimestre}T {f.anio})"
        except Exception as exc:  # noqa: BLE001
            if ruta:
                (directorio_datos() / ruta).unlink(missing_ok=True)
            aviso(self.page, mensaje_error(exc), error=True)
            return
        aviso(self.page, msg)
        self._limpiar()
