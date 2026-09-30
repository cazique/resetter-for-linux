# Gestión de Costes (Facturas · Partes de trabajo · OCR con IA)

App CRUD multiplataforma (Web + Android con Flet 1.0) para control de costes,
facturas de proveedores y partes de trabajo de empleados.

| Paso | Contenido | Archivos |
|------|-----------|----------|
| 1 | Modelos SQLAlchemy + esquemas Pydantic | `app/models.py`, `app/schemas.py`, `app/fiscal.py` |
| 2 | Extractor OCR con IA (Gemini / GPT-4o-mini) | `app/ocr_service.py` |
| 3 | CRUD, consultas y exportación Excel/CSV | `app/crud.py`, `app/export.py` |
| 4 | Interfaz Flet (4 vistas) | `main.py`, `app/ui/` |
| 5 | Probar en el móvil / generar APK | este README |

---

## 1. Instalar en tu PC (una sola vez)

Necesitas **Python 3.10 o superior** y **git**.

```bash
git clone https://github.com/cazique/resetter-for-linux.git
cd resetter-for-linux
git checkout ccr-71bc2faf-bo1mwp
cd gestion-costes

python -m venv .venv
# Windows:      .venv\Scripts\activate
# Mac / Linux:  source .venv/bin/activate
pip install -r requirements.txt

python scripts/datos_demo.py     # opcional: carga datos de ejemplo
pytest -q                        # opcional: comprueba que todo va bien
```

**API key para la lectura automática de facturas** (opcional, la app funciona sin ella
rellenando a mano): crea una gratis en <https://aistudio.google.com/apikey> y ponla en la app
(icono ⚙ → Ajustes) o en un fichero `.env` (copia `.env.example`).

## 2. Probar en el móvil Android

### Opción A · App "Flet" + tu PC (la más rápida para ir probando)
El código se ejecuta en tu PC y el móvil muestra la app nativa. Cada vez que guardas un
archivo, la app se recarga sola.

1. Móvil y PC **en la misma Wi-Fi**.
2. En el PC: `flet run --android main.py`
3. Aparece un **código QR** en la terminal: escanéalo con la cámara del móvil. Te abrirá
   (o te pedirá instalar) la app **Flet** de Google Play, que carga tu aplicación.
4. Si no conecta, permite el puerto en el cortafuegos del PC (Windows te lo pregunta la primera vez).

### Opción B · Navegador del móvil
1. En el PC: `flet run --web --host "*" --port 8550 main.py`
2. Averigua la IP del PC (`ipconfig` en Windows, `ip a` en Linux, Ajustes de red en Mac),
   por ejemplo `192.168.1.40`.
3. En Chrome del móvil abre `http://192.168.1.40:8550`.
   El botón "Foto / Galería" te deja usar la cámara. Menú ⋮ → *Añadir a pantalla de inicio*
   para tenerla como un icono.

> En las opciones A y B los datos (base de datos y fotos) se guardan en el PC, en `datos/`.

### Opción C0 · Solo con el móvil (sin PC): APK compilado por GitHub
Cada cambio en `gestion-costes/` compila el APK automáticamente (GitHub Actions) y lo publica aquí:

**https://github.com/cazique/resetter-for-linux/releases/download/apk-latest/gestion-costes.apk**

Ábrelo en el navegador del móvil → descargar → abrir → permitir *instalar apps de origen desconocido*.
(Móviles antiguos de 32 bits: `gestion-costes-32bits.apk` en la misma release.)
Estado de la compilación: pestaña **Actions** del repositorio (tarda unos 15-25 min).

### Opción C · Instalar el APK en el móvil (app independiente)
```bash
flet build apk
```
* La primera vez descarga Flutter, el JDK y el SDK de Android: tarda un buen rato y ocupa varios GB.
  Si algo falla, instalar Android Studio suele resolverlo.
* El APK queda en `build/apk/`. Pásalo al móvil (cable USB, Drive, Telegram…) y ábrelo;
  Android te pedirá permitir *instalar apps de origen desconocido*.
  Con el móvil conectado por USB y depuración activada también vale `adb install build/apk/*.apk`.
* Abre la app → ⚙ Ajustes → pega tu API key de Gemini.
* Los datos se guardan **dentro del móvil** (no se comparten con el PC).

## 3. Qué hace cada pantalla
* **Resumen**: gasto e IVA del trimestre, horas, dietas + km, pendiente de pago, facturas por revisar.
* **Escanear**: foto o PDF → la IA rellena el formulario → revisas → guardar. Sin nº de factura
  (tickets) se genera uno `SN-…`. Admite estado *parcial* con importe pagado.
* **Consultas**: facturas filtradas por texto/CIF, año, trimestre, estado y fechas; desglose de costes
  por trabajador y por proyecto; exportación a Excel (con hoja de IVA por tipo y hoja de partes
  detallados) y CSV.
* **Parte**: trabajador, proyecto, horas, km, comisiones y gastos en texto libre ("Comida 20€").

## Notas
* Producción con varios usuarios/dispositivos compartiendo datos: PostgreSQL (`DATABASE_URL`) +
  un backend; es el siguiente paso natural.
* No incluyas tu API key dentro del APK si lo vas a distribuir: introdúcela en Ajustes.
