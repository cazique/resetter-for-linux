"""Gestión de Costes · punto de entrada Flet (Web, Android y escritorio).

Desarrollo:
    flet run main.py                     # ventana de escritorio
    flet run --android main.py           # QR para abrir en el móvil con la app "Flet"
    flet run --web --host "*" -p 8550 main.py   # navegador del móvil en la misma Wi-Fi
APK:
    flet build apk
"""
from __future__ import annotations

import logging

import flet as ft

from app import crud
from app.config import actualizar_settings, directorio_datos, get_settings
from app.database import get_session, init_db
from app.ui.comunes import aviso, opciones
from app.ui.consultas import ConsultasView
from app.ui.dashboard import DashboardView
from app.ui.escaneo import EscaneoView
from app.ui.parte import ParteView

logging.basicConfig(level=logging.INFO)
PREF_PROVIDER, PREF_GEMINI, PREF_OPENAI = "gc.ocr_provider", "gc.gemini_key", "gc.openai_key"


async def main(page: ft.Page):
    page.title = "Gestión de Costes"
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.INDIGO)
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.padding = 12
    page.locale_configuration = ft.LocaleConfiguration(
        supported_locales=[ft.Locale("es", "ES")], current_locale=ft.Locale("es", "ES")
    )

    init_db()
    with get_session() as s:
        crud.sembrar_datos_iniciales(s)

    # --- API keys guardadas en el dispositivo (SharedPreferences / localStorage en web)
    prefs = ft.SharedPreferences()

    async def cargar_preferencias():
        try:
            provider = await prefs.get(PREF_PROVIDER)
            gemini = await prefs.get(PREF_GEMINI)
            openai = await prefs.get(PREF_OPENAI)
        except Exception:  # noqa: BLE001 - sin preferencias disponibles
            return
        s = get_settings()
        actualizar_settings(
            ocr_provider=provider or s.ocr_provider,
            gemini_api_key=gemini or s.gemini_api_key,
            openai_api_key=openai or s.openai_api_key,
        )

    await cargar_preferencias()

    # --- vistas
    cuerpo = ft.Container(expand=True)

    def ir_a(indice: int):
        page.navigation_bar.selected_index = indice
        vista = vistas[indice]
        vista.refrescar()
        cuerpo.content = vista.control
        page.update()

    vistas = [DashboardView(page, ir_a), EscaneoView(page), ConsultasView(page), ParteView(page)]

    # --- ajustes
    def abrir_ajustes(_e):
        s = get_settings()
        provider = ft.Dropdown(label="Motor de IA", value=s.ocr_provider,
                               options=opciones([("gemini", "Google Gemini"), ("openai", "OpenAI GPT-4o-mini")]))
        gemini = ft.TextField(label="GEMINI_API_KEY", value=s.gemini_api_key or "", password=True,
                              can_reveal_password=True)
        openai = ft.TextField(label="OPENAI_API_KEY", value=s.openai_api_key or "", password=True,
                              can_reveal_password=True)

        async def guardar(_e):
            actualizar_settings(ocr_provider=provider.value, gemini_api_key=gemini.value.strip(),
                                openai_api_key=openai.value.strip())
            try:
                await prefs.set(PREF_PROVIDER, provider.value)
                await prefs.set(PREF_GEMINI, gemini.value.strip())
                await prefs.set(PREF_OPENAI, openai.value.strip())
            except Exception:  # noqa: BLE001
                pass
            page.pop_dialog()
            aviso(page, "Ajustes guardados" + ("" if get_settings().ocr_configurado else " (OCR sin API key)"))

        page.show_dialog(ft.AlertDialog(
            title=ft.Text("Ajustes"),
            content=ft.Column(tight=True, width=380, controls=[
                provider, gemini, openai,
                ft.Text(f"Datos en: {directorio_datos().resolve()}", size=11, selectable=True,
                        color=ft.Colors.ON_SURFACE_VARIANT),
            ]),
            actions=[ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()),
                     ft.FilledButton("Guardar", on_click=guardar)],
        ))

    page.appbar = ft.AppBar(
        title=ft.Text("Gestión de Costes"),
        actions=[ft.IconButton(ft.Icons.SETTINGS, tooltip="Ajustes", on_click=abrir_ajustes)],
    )
    page.navigation_bar = ft.NavigationBar(
        selected_index=0,
        on_change=lambda e: ir_a(e.control.selected_index),
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.DASHBOARD_OUTLINED, selected_icon=ft.Icons.DASHBOARD,
                                        label="Resumen"),
            ft.NavigationBarDestination(icon=ft.Icons.DOCUMENT_SCANNER_OUTLINED, selected_icon=ft.Icons.DOCUMENT_SCANNER,
                                        label="Escanear"),
            ft.NavigationBarDestination(icon=ft.Icons.TABLE_CHART_OUTLINED, selected_icon=ft.Icons.TABLE_CHART,
                                        label="Consultas"),
            ft.NavigationBarDestination(icon=ft.Icons.MORE_TIME, label="Parte"),
        ],
    )
    page.add(ft.SafeArea(content=cuerpo, expand=True))
    ir_a(0)


if __name__ == "__main__":
    ft.run(main)
