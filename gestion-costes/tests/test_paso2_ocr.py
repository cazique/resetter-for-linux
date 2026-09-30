import io
from datetime import date
from decimal import Decimal

from PIL import Image, ImageDraw, ImageFilter

from app.ocr_service import (FacturaExtraidaLLM, LineaIVAExtraida, OCRService, cargar_documento,
                             validar_extraccion)

HOY = date(2025, 9, 30)


def llm(**kw):
    base = dict(proveedor_nombre="Suministros SL", proveedor_nif="B12345674", numero_factura="F-77",
                fecha_emision="2025-07-15",
                lineas_iva=[LineaIVAExtraida(tipo_iva=21, base_imponible=100, cuota_iva=21, recargo_equivalencia=None),
                            LineaIVAExtraida(tipo_iva=10, base_imponible=50, cuota_iva=5, recargo_equivalencia=None)],
                base_imponible_total=150, cuota_iva_total=26, irpf_porcentaje=None, irpf_importe=None,
                total=176, moneda="EUR", es_ticket_simplificado=False, categoria_sugerida="Material",
                calidad_imagen="buena", confianza=0.95, campos_dudosos=[], observaciones=None)
    base.update(kw)
    return FacturaExtraidaLLM(**base)


def test_extraccion_correcta():
    r = validar_extraccion(llm(), hoy=HOY)
    assert not r.requiere_revision and r.trimestre_label == "2025-Q3"
    assert r.total == Decimal("176.00") and len(r.lineas_iva) == 2
    fc = r.a_factura_create(categoria_id=3)
    assert fc.base_imponible == Decimal("150.00") and fc.categoria_id == 3


def test_falta_total_y_fecha_borrosa():
    r = validar_extraccion(llm(total=None, fecha_emision=None, calidad_imagen="mala"), nitidez=10, hoy=HOY)
    assert r.requiere_revision
    assert {a.campo for a in r.errores} == {"total", "fecha_emision"}
    assert r.confianza < 0.5


def test_importes_no_cuadran_dispara_segunda_pasada():
    class Fake:
        modelo = "fake"
        def __init__(self): self.llamadas = []
        def extraer(self, doc, extra=""):
            self.llamadas.append(extra)
            return llm(total=180) if len(self.llamadas) == 1 else llm(fecha_emision="15/07/2025")

    fake = Fake()
    img = io.BytesIO(); Image.new("RGB", (50, 50), "white").save(img, "PNG")
    r = OCRService(provider=fake, umbral_confianza=0.8).extraer(img.getvalue())
    assert r.intentos == 2 and "no cuadran" in fake.llamadas[1]
    assert r.total == Decimal("176.00") and not r.errores


def test_nitidez_detecta_borrosa():
    img = Image.new("RGB", (800, 600), "white")
    d = ImageDraw.Draw(img)
    for y in range(20, 580, 30):
        d.text((20, y), "FACTURA 123 TOTAL 176,00 EUR IVA 21%" * 2, fill="black")
    nitida, borrosa = io.BytesIO(), io.BytesIO()
    img.save(nitida, "PNG"); img.filter(ImageFilter.GaussianBlur(6)).save(borrosa, "PNG")
    assert cargar_documento(nitida.getvalue()).nitidez > cargar_documento(borrosa.getvalue()).nitidez * 5
