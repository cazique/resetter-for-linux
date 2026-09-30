"""Extractor de facturas/tickets con IA de visión (Gemini o GPT-4o-mini) + validación Pydantic.

Flujo:
    1. `cargar_documento()`   -> normaliza la imagen (rotación EXIF, tamaño) o pasa el PDF tal cual
                                 y estima la nitidez para detectar fotos borrosas.
    2. `VisionProvider`       -> el modelo devuelve JSON *estricto* según `FacturaExtraidaLLM`
                                 (structured outputs: el SDK obliga al modelo a cumplir el esquema).
    3. `validar_extraccion()` -> reglas deterministas en Python: NIF con dígito de control,
                                 fecha y trimestre, base x tipo = cuota, base+IVA-IRPF = total...
    4. Si los importes no cuadran, 2ª pasada indicando al modelo qué revisar (autocorrección).
    5. `ResultadoOCR`         -> datos normalizados + confianza + alertas + `requiere_revision`.
                                 `.a_factura_create()` genera el `FacturaCreate` para el CRUD.

Uso:
    from app.ocr_service import OCRService
    resultado = OCRService().extraer("factura.jpg")
    if resultado.requiere_revision: ...
"""
from __future__ import annotations

import base64
import io
import logging
import mimetypes
import re
import time
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Literal, Protocol

from pydantic import BaseModel, Field

from .config import Settings, get_settings
from .fiscal import (
    CENTIMO,
    TIPOS_IVA_ES,
    TIPOS_RECARGO_EQ,
    a_dinero,
    etiqueta_trimestre,
    normalizar_nif,
    trimestre_de,
    validar_nif,
)

log = logging.getLogger(__name__)

MIME_SOPORTADOS = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
LADO_MAX_PX = 2048  # suficiente para leer tickets; reduce coste y latencia
UMBRAL_NITIDEZ = 60.0  # varianza de bordes; por debajo la foto suele estar borrosa
TOL = Decimal("0.02")


# ======================================================================
# 1. Esquema que DEBE devolver el modelo (JSON estricto)
# ======================================================================
# Nota: tipos simples (str/float/None, sin valores por defecto) para que el esquema sea
# compatible con el modo estricto de OpenAI y con `response_schema` de Gemini.
# Las fechas llegan como texto y los importes como float: Python los normaliza después.
class LineaIVAExtraida(BaseModel):
    tipo_iva: float | None = Field(description="Porcentaje de IVA de esta línea, p.ej. 21, 10, 4, 0")
    base_imponible: float | None = Field(description="Base imponible sujeta a este tipo")
    cuota_iva: float | None = Field(description="Importe del IVA de este tipo")
    recargo_equivalencia: float | None = Field(description="Importe de recargo de equivalencia si aparece, si no null")


class FacturaExtraidaLLM(BaseModel):
    proveedor_nombre: str | None = Field(description="Razón social del EMISOR (quien vende), no del cliente")
    proveedor_nif: str | None = Field(description="CIF/NIF/NIE del EMISOR tal como aparece")
    numero_factura: str | None = Field(description="Número o serie+número de factura/ticket")
    fecha_emision: str | None = Field(description="Fecha de emisión en formato YYYY-MM-DD")
    lineas_iva: list[LineaIVAExtraida] = Field(description="Una entrada por cada tipo de IVA distinto")
    base_imponible_total: float | None = Field(description="Suma de bases imponibles")
    cuota_iva_total: float | None = Field(description="Suma de cuotas de IVA")
    irpf_porcentaje: float | None = Field(description="% de retención IRPF si existe (p.ej. 15, 7), si no null")
    irpf_importe: float | None = Field(description="Importe retenido de IRPF (positivo), si no null")
    total: float | None = Field(description="Total a pagar de la factura")
    moneda: str | None = Field(description="Código ISO de moneda, normalmente EUR")
    es_ticket_simplificado: bool = Field(description="true si es factura simplificada / ticket de caja")
    categoria_sugerida: str | None = Field(
        description="Una de: Combustible, Dietas y restauración, Material, Suministros, "
        "Herramientas, Servicios profesionales, Transporte, Alojamiento, Telefonía, Alquiler, Otros"
    )
    calidad_imagen: Literal["buena", "aceptable", "mala"] = Field(description="Legibilidad del documento")
    confianza: float = Field(description="Tu confianza global en la extracción, de 0.0 a 1.0")
    campos_dudosos: list[str] = Field(description="Nombres de campos que no se leen con claridad")
    observaciones: str | None = Field(description="Cualquier anomalía relevante, o null")


PROMPT_SISTEMA = """Eres un experto contable español especializado en digitalizar facturas y tickets.
Extrae los datos del documento con precisión absoluta y devuélvelos en el esquema JSON indicado.

Reglas:
- El PROVEEDOR es el EMISOR de la factura (cabecera/logo), nunca el cliente o destinatario.
- Copia NIF/CIF y número de factura carácter a carácter. No confundas O/0, I/1, S/5, B/8.
- Fecha en formato YYYY-MM-DD. Las fechas españolas son DD/MM/AAAA.
- Importes con punto decimal y sin símbolo de moneda ("1.234,56 €" -> 1234.56).
- Si hay varios tipos de IVA (21%, 10%, 4%...), crea una línea por tipo con su base y su cuota.
- En tickets con "IVA incluido" sin desglose, calcula base = total / (1 + tipo/100) si el tipo aparece.
- La retención de IRPF resta del total; indícala en positivo.
- NUNCA inventes datos: si un campo no es legible o no aparece, devuelve null y añádelo a campos_dudosos.
- Si el documento está borroso, cortado o no es una factura, refléjalo en calidad_imagen, confianza y observaciones.
"""

PROMPT_USUARIO = "Extrae los datos de esta factura o ticket."


# ======================================================================
# 2. Resultado validado que consume la aplicación
# ======================================================================
class Alerta(BaseModel):
    nivel: Literal["info", "aviso", "error"]
    campo: str | None = None
    mensaje: str


class LineaIVANormalizada(BaseModel):
    tipo: Decimal
    base: Decimal
    cuota: Decimal
    recargo_equivalencia: Decimal | None = None


class ResultadoOCR(BaseModel):
    proveedor_nombre: str | None = None
    proveedor_nif: str | None = None
    nif_valido: bool = False
    numero_factura: str | None = None
    fecha_emision: date | None = None
    trimestre: int | None = None
    anio: int | None = None
    trimestre_label: str | None = None
    lineas_iva: list[LineaIVANormalizada] = []
    base_imponible: Decimal | None = None
    cuota_iva: Decimal | None = None
    irpf_porcentaje: Decimal = Decimal("0")
    irpf_importe: Decimal = Decimal("0")
    total: Decimal | None = None
    es_ticket: bool = False
    categoria_sugerida: str | None = None

    confianza: float = Field(ge=0, le=1)
    requiere_revision: bool
    alertas: list[Alerta] = []
    modelo: str | None = None
    intentos: int = 1
    bruto: FacturaExtraidaLLM | None = None  # respuesta original, para auditoría

    @property
    def errores(self) -> list[Alerta]:
        return [a for a in self.alertas if a.nivel == "error"]

    def a_factura_create(self, **extra):
        """Convierte a `FacturaCreate` para guardar tras la revisión del usuario.

        Lanza `pydantic.ValidationError` si faltan datos obligatorios o no cuadran:
        la UI debe mostrar el formulario precargado para completarlos.
        """
        from .schemas import FacturaCreate

        datos = {
            "numero": self.numero_factura,
            "fecha_emision": self.fecha_emision,
            "lineas_iva": [l.model_dump() for l in self.lineas_iva],
            "irpf_porcentaje": self.irpf_porcentaje,
            "irpf_importe": self.irpf_importe,
            "total": self.total,
            "ocr_confianza": round(self.confianza, 3),
            "requiere_revision": self.requiere_revision,
            "proveedor": {"nombre": self.proveedor_nombre, "nif": self.proveedor_nif},
        }
        datos.update(extra)
        return FacturaCreate.model_validate(datos)


# ======================================================================
# 3. Carga y preprocesado del documento
# ======================================================================
@dataclass
class Documento:
    datos: bytes
    mime: str
    nombre: str = "documento"
    nitidez: float | None = None  # solo imágenes

    @property
    def b64(self) -> str:
        return base64.b64encode(self.datos).decode()


def _detectar_mime(datos: bytes, nombre: str) -> str:
    if datos[:5] == b"%PDF-":
        return "application/pdf"
    if datos[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if datos[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if datos[:4] == b"RIFF" and datos[8:12] == b"WEBP":
        return "image/webp"
    return mimetypes.guess_type(nombre)[0] or "application/octet-stream"


def estimar_nitidez(imagen) -> float:
    """Varianza de la imagen de bordes (análogo a la varianza del Laplaciano, solo Pillow)."""
    from PIL import ImageFilter, ImageStat

    gris = imagen.convert("L")
    gris.thumbnail((1024, 1024))
    bordes = gris.filter(ImageFilter.FIND_EDGES)
    return float(ImageStat.Stat(bordes).var[0])


def cargar_documento(origen: str | Path | bytes, nombre: str | None = None) -> Documento:
    """Lee una imagen/PDF desde ruta o bytes y lo prepara para el modelo."""
    if isinstance(origen, (str, Path)):
        ruta = Path(origen)
        datos, nombre = ruta.read_bytes(), nombre or ruta.name
    else:
        datos, nombre = origen, nombre or "documento"

    mime = _detectar_mime(datos, nombre)
    if mime == "application/pdf":
        return Documento(datos, mime, nombre)

    try:
        from PIL import Image, ImageOps
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("Instala Pillow para procesar imágenes: pip install pillow") from e

    try:
        img = Image.open(io.BytesIO(datos))
        img = ImageOps.exif_transpose(img)  # fotos de móvil giradas
    except Exception as e:
        raise ValueError(f"Formato no soportado ({mime}). Usa JPG, PNG, WEBP o PDF.") from e

    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    img.thumbnail((LADO_MAX_PX, LADO_MAX_PX))
    nitidez = estimar_nitidez(img)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90, optimize=True)
    return Documento(buf.getvalue(), "image/jpeg", nombre, nitidez)


# ======================================================================
# 4. Proveedores de IA de visión
# ======================================================================
class VisionProvider(Protocol):
    modelo: str

    def extraer(self, doc: Documento, instrucciones_extra: str = "") -> FacturaExtraidaLLM: ...


class GeminiProvider:
    """Google Gemini (Flash) con `response_schema` Pydantic. PDFs e imágenes nativos."""

    def __init__(self, api_key: str, modelo: str = "gemini-2.5-flash"):
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self.modelo = modelo

    def extraer(self, doc: Documento, instrucciones_extra: str = "") -> FacturaExtraidaLLM:
        from google.genai import types

        resp = self._client.models.generate_content(
            model=self.modelo,
            contents=[
                types.Part.from_bytes(data=doc.datos, mime_type=doc.mime),
                PROMPT_USUARIO + instrucciones_extra,
            ],
            config=types.GenerateContentConfig(
                system_instruction=PROMPT_SISTEMA,
                response_mime_type="application/json",
                response_schema=FacturaExtraidaLLM,
                temperature=0,
            ),
        )
        if isinstance(resp.parsed, FacturaExtraidaLLM):
            return resp.parsed
        return FacturaExtraidaLLM.model_validate_json(resp.text)


class OpenAIProvider:
    """OpenAI GPT-4o-mini con Structured Outputs (`response_format` = modelo Pydantic)."""

    def __init__(self, api_key: str, modelo: str = "gpt-4o-mini"):
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)
        self.modelo = modelo

    def extraer(self, doc: Documento, instrucciones_extra: str = "") -> FacturaExtraidaLLM:
        if doc.mime == "application/pdf":
            adjunto = {
                "type": "file",
                "file": {"filename": doc.nombre, "file_data": f"data:application/pdf;base64,{doc.b64}"},
            }
        else:
            adjunto = {
                "type": "image_url",
                "image_url": {"url": f"data:{doc.mime};base64,{doc.b64}", "detail": "high"},
            }
        completion = self._client.chat.completions.parse(
            model=self.modelo,
            temperature=0,
            response_format=FacturaExtraidaLLM,
            messages=[
                {"role": "system", "content": PROMPT_SISTEMA},
                {"role": "user", "content": [{"type": "text", "text": PROMPT_USUARIO + instrucciones_extra}, adjunto]},
            ],
        )
        msg = completion.choices[0].message
        if msg.refusal:
            raise RuntimeError(f"El modelo rechazó la petición: {msg.refusal}")
        return msg.parsed


def crear_provider(settings: Settings | None = None) -> VisionProvider:
    s = settings or get_settings()
    if s.ocr_provider == "gemini":
        if not s.gemini_api_key:
            raise RuntimeError("Falta GEMINI_API_KEY en el entorno/.env")
        return GeminiProvider(s.gemini_api_key, s.gemini_model)
    if s.ocr_provider == "openai":
        if not s.openai_api_key:
            raise RuntimeError("Falta OPENAI_API_KEY en el entorno/.env")
        return OpenAIProvider(s.openai_api_key, s.openai_model)
    raise ValueError(f"OCR_PROVIDER desconocido: {s.ocr_provider!r} (usa 'gemini' u 'openai')")


# ======================================================================
# 5. Validación determinista y cálculo de confianza
# ======================================================================
_FORMATOS_FECHA = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%y", "%d-%m-%y")


def _parse_fecha(texto: str | None) -> date | None:
    if not texto:
        return None
    t = texto.strip()
    for fmt in _FORMATOS_FECHA:
        try:
            return datetime.strptime(t, fmt).date()
        except ValueError:
            continue
    m = re.search(r"\d{4}-\d{2}-\d{2}", t)
    return _parse_fecha(m.group()) if m and m.group() != t else None


def _dec(valor) -> Decimal | None:
    try:
        return a_dinero(valor)
    except Exception:
        return None


def validar_extraccion(
    bruto: FacturaExtraidaLLM,
    nitidez: float | None = None,
    umbral_confianza: float = 0.80,
    hoy: date | None = None,
) -> ResultadoOCR:
    """Aplica reglas fiscales/aritméticas y decide si la factura necesita revisión manual."""
    hoy = hoy or date.today()
    alertas: list[Alerta] = []

    def alerta(nivel, campo, mensaje):
        alertas.append(Alerta(nivel=nivel, campo=campo, mensaje=mensaje))

    # --- Calidad de imagen
    if bruto.calidad_imagen == "mala":
        alerta("aviso", None, "El modelo indica que el documento es poco legible")
    if nitidez is not None and nitidez < UMBRAL_NITIDEZ:
        alerta("aviso", None, f"La foto parece borrosa (nitidez {nitidez:.0f}); repítela si puedes")
    for campo in bruto.campos_dudosos:
        alerta("aviso", campo, f"Lectura dudosa del campo '{campo}'")

    # --- Proveedor
    nif = normalizar_nif(bruto.proveedor_nif)
    nif_ok = validar_nif(nif)
    if not nif:
        alerta("aviso", "proveedor_nif", "No se ha detectado el CIF/NIF del proveedor")
    elif not nif_ok:
        alerta("aviso", "proveedor_nif", f"El CIF/NIF '{nif}' no supera el dígito de control")
    if not bruto.proveedor_nombre:
        alerta("aviso", "proveedor_nombre", "No se ha detectado el nombre del proveedor")
    if not bruto.numero_factura:
        alerta("aviso", "numero_factura", "No se ha detectado el número de factura")

    # --- Fecha y trimestre (obligatoria)
    fecha = _parse_fecha(bruto.fecha_emision)
    trimestre = anio = None
    if fecha is None:
        alerta("error", "fecha_emision", "Falta la fecha de emisión o no es legible")
    else:
        trimestre, anio = trimestre_de(fecha)
        if fecha > hoy:
            alerta("error", "fecha_emision", f"Fecha {fecha} futura: posible lectura errónea")
        elif (hoy - fecha).days > 4 * 365:
            alerta("aviso", "fecha_emision", f"Fecha {fecha} con más de 4 años de antigüedad")

    # --- Líneas de IVA: completar datos derivables y comprobar base x tipo = cuota
    lineas: list[LineaIVANormalizada] = []
    for i, l in enumerate(bruto.lineas_iva, 1):
        tipo, base, cuota = _dec(l.tipo_iva), _dec(l.base_imponible), _dec(l.cuota_iva)
        if tipo is None and base and cuota is not None:
            tipo = (cuota / base * 100).quantize(Decimal("0.1")).normalize()
        if tipo is None or (base is None and cuota is None):
            alerta("aviso", "lineas_iva", f"Línea de IVA {i} incompleta; se ha descartado")
            continue
        if base is None:
            base = (cuota * 100 / tipo).quantize(CENTIMO) if tipo else Decimal("0")
        if cuota is None:
            cuota = (base * tipo / 100).quantize(CENTIMO)
        esperado = (base * tipo / 100).quantize(CENTIMO)
        if abs(cuota - esperado) > TOL:
            alerta("error", "lineas_iva", f"IVA {tipo}%: cuota {cuota} ≠ {esperado} esperado sobre base {base}")
        if tipo in TIPOS_RECARGO_EQ:  # probablemente ha leído el recargo como si fuera un tipo de IVA
            alerta("aviso", "lineas_iva", f"{tipo}% parece un recargo de equivalencia, no un tipo de IVA")
        elif tipo not in TIPOS_IVA_ES:
            alerta("info", "lineas_iva", f"Tipo {tipo}% no habitual en IVA peninsular (¿IGIC/IPSI?)")
        recargo = _dec(l.recargo_equivalencia)
        lineas.append(LineaIVANormalizada(tipo=tipo, base=base, cuota=cuota, recargo_equivalencia=recargo))

    # Agrupar tipos repetidos (algunos tickets desglosan por artículo)
    agrupadas: dict[Decimal, LineaIVANormalizada] = {}
    for l in lineas:
        if l.tipo in agrupadas:
            g = agrupadas[l.tipo]
            g.base += l.base
            g.cuota += l.cuota
            if l.recargo_equivalencia:
                g.recargo_equivalencia = (g.recargo_equivalencia or Decimal("0")) + l.recargo_equivalencia
        else:
            agrupadas[l.tipo] = l.model_copy()
    lineas = list(agrupadas.values())

    base = sum((l.base for l in lineas), Decimal("0")) if lineas else _dec(bruto.base_imponible_total)
    cuota = (
        sum((l.cuota + (l.recargo_equivalencia or 0) for l in lineas), Decimal("0"))
        if lineas
        else _dec(bruto.cuota_iva_total)
    )
    base_declarada = _dec(bruto.base_imponible_total)
    if lineas and base_declarada is not None and abs(base_declarada - base) > TOL * len(lineas):
        alerta("aviso", "base_imponible", f"La base total impresa ({base_declarada}) no coincide con la suma de líneas ({base})")
    if not lineas:
        alerta("aviso", "lineas_iva", "No se ha detectado desglose de IVA")

    # --- IRPF
    irpf_pct = _dec(bruto.irpf_porcentaje) or Decimal("0")
    irpf_imp = abs(_dec(bruto.irpf_importe) or Decimal("0"))
    if irpf_pct and not irpf_imp and base:
        irpf_imp = (base * irpf_pct / 100).quantize(CENTIMO)
    elif irpf_imp and not irpf_pct and base:
        irpf_pct = (irpf_imp / base * 100).quantize(CENTIMO)

    # --- Total (obligatorio) y cuadre aritmético
    total = _dec(bruto.total)
    if total is None:
        alerta("error", "total", "Falta el total de la factura o no es legible")
    elif base is not None and cuota is not None:
        calculado = base + cuota - irpf_imp
        tolerancia = TOL * max(1, len(lineas))
        if abs(total - calculado) > tolerancia:
            alerta("error", "total", f"Los importes no cuadran: base {base} + IVA {cuota} - IRPF {irpf_imp} = {calculado} ≠ total {total}")
    if total is not None and total <= 0:
        alerta("aviso", "total", "Total cero o negativo (¿factura rectificativa?)")
    if bruto.moneda and bruto.moneda.upper() not in ("EUR", "€"):
        alerta("aviso", "moneda", f"Moneda {bruto.moneda}: convertir a EUR antes de contabilizar")

    # --- Confianza combinada: la del modelo penalizada por las comprobaciones objetivas
    confianza = min(max(bruto.confianza, 0.0), 1.0)
    for a in alertas:
        confianza -= {"error": 0.25, "aviso": 0.07, "info": 0.0}[a.nivel]
    if nif_ok and fecha and total is not None and not any(a.nivel == "error" for a in alertas):
        confianza += 0.05  # todo lo verificable ha cuadrado
    confianza = round(min(max(confianza, 0.0), 1.0), 3)

    requiere = (
        any(a.nivel == "error" for a in alertas)
        or confianza < umbral_confianza
        or bruto.calidad_imagen == "mala"
    )
    return ResultadoOCR(
        proveedor_nombre=bruto.proveedor_nombre,
        proveedor_nif=nif,
        nif_valido=nif_ok,
        numero_factura=bruto.numero_factura,
        fecha_emision=fecha,
        trimestre=trimestre,
        anio=anio,
        trimestre_label=etiqueta_trimestre(trimestre, anio) if fecha else None,
        lineas_iva=lineas,
        base_imponible=base,
        cuota_iva=cuota,
        irpf_porcentaje=irpf_pct,
        irpf_importe=irpf_imp,
        total=total,
        es_ticket=bruto.es_ticket_simplificado,
        categoria_sugerida=bruto.categoria_sugerida,
        confianza=confianza,
        requiere_revision=requiere,
        alertas=alertas,
        bruto=bruto,
    )


# ======================================================================
# 6. Servicio orquestador
# ======================================================================
class OCRService:
    def __init__(
        self,
        provider: VisionProvider | None = None,
        umbral_confianza: float | None = None,
        max_reintentos_red: int = 2,
    ):
        s = get_settings()
        self.provider = provider or crear_provider(s)
        self.umbral = umbral_confianza if umbral_confianza is not None else s.ocr_umbral_confianza
        self.max_reintentos_red = max_reintentos_red

    def _llamar(self, doc: Documento, extra: str = "") -> FacturaExtraidaLLM:
        for intento in range(self.max_reintentos_red + 1):
            try:
                return self.provider.extraer(doc, extra)
            except Exception as e:  # red, cuota (429), JSON inválido...
                if intento == self.max_reintentos_red:
                    raise RuntimeError(f"Error del servicio de IA ({self.provider.modelo}): {e}") from e
                espera = 2 ** intento
                log.warning("Fallo OCR (%s), reintento en %ss", e, espera)
                time.sleep(espera)
        raise AssertionError("inalcanzable")

    def extraer(self, origen: str | Path | bytes | Documento, nombre: str | None = None) -> ResultadoOCR:
        doc = origen if isinstance(origen, Documento) else cargar_documento(origen, nombre)
        if doc.mime not in MIME_SOPORTADOS:
            raise ValueError(f"Tipo de archivo no soportado: {doc.mime}")

        resultado = validar_extraccion(self._llamar(doc), doc.nitidez, self.umbral)

        # Autocorrección: si hay errores de cuadre (no de ilegibilidad), segunda pasada guiada
        errores_cuadre = [a for a in resultado.errores if a.campo in ("lineas_iva", "total", "fecha_emision")]
        if errores_cuadre and resultado.bruto and resultado.bruto.calidad_imagen != "mala":
            pistas = "\n".join(f"- {a.mensaje}" for a in errores_cuadre)
            extra = (
                "\n\nUna lectura previa tuvo estas incoherencias:\n"
                f"{pistas}\nVuelve a leer con atención los importes, tipos de IVA y la fecha. "
                "Si el documento realmente no cuadra, devuelve lo que ves y explícalo en observaciones."
            )
            segundo = validar_extraccion(self._llamar(doc, extra), doc.nitidez, self.umbral)
            if (len(segundo.errores), -segundo.confianza) < (len(resultado.errores), -resultado.confianza):
                resultado = segundo
            resultado.intentos = 2

        resultado.modelo = self.provider.modelo
        return resultado
