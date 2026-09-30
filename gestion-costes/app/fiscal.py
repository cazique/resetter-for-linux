"""Utilidades fiscales españolas: trimestres, NIF/CIF/NIE y redondeo monetario."""
from __future__ import annotations

import re
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

CENTIMO = Decimal("0.01")

# Tipos de IVA vigentes (general, reducido, superreducido, 5% temporal y exento).
# Recargo de equivalencia e IGIC (Canarias) se aceptan pero generan aviso informativo.
TIPOS_IVA_ES = {Decimal("21"), Decimal("10"), Decimal("5"), Decimal("4"), Decimal("0")}
TIPOS_RECARGO_EQ = {Decimal("5.2"), Decimal("1.4"), Decimal("1.75"), Decimal("0.5"), Decimal("0.62")}

_LETRAS_DNI = "TRWAGMYFPDXBNJZSQVHLCKE"
_LETRAS_CONTROL_CIF = "JABCDEFGHI"


def a_dinero(valor) -> Decimal | None:
    """Convierte a Decimal con 2 decimales (redondeo comercial). Acepta '1.234,56'."""
    if valor is None or valor == "":
        return None
    if isinstance(valor, str):
        v = valor.strip().replace("€", "").replace("EUR", "").replace(" ", "")
        if "," in v and "." in v:  # formato español 1.234,56
            v = v.replace(".", "").replace(",", ".")
        else:
            v = v.replace(",", ".")
        valor = v
    try:
        return Decimal(str(valor)).quantize(CENTIMO, rounding=ROUND_HALF_UP)
    except InvalidOperation:
        raise ValueError(f"Importe no válido: {valor!r}") from None


# ---------------------------------------------------------------- trimestres
def trimestre_de(fecha: date) -> tuple[int, int]:
    """Devuelve (trimestre 1-4, año) de una fecha."""
    return (fecha.month - 1) // 3 + 1, fecha.year


def etiqueta_trimestre(trimestre: int, anio: int) -> str:
    return f"{anio}-Q{trimestre}"


def rango_trimestre(trimestre: int, anio: int) -> tuple[date, date]:
    """Primer y último día del trimestre (ambos inclusive)."""
    if trimestre not in (1, 2, 3, 4):
        raise ValueError("El trimestre debe ser 1, 2, 3 o 4")
    mes_inicio = 3 * (trimestre - 1) + 1
    inicio = date(anio, mes_inicio, 1)
    fin = date(anio + 1, 1, 1) if trimestre == 4 else date(anio, mes_inicio + 3, 1)
    return inicio, date.fromordinal(fin.toordinal() - 1)


def parse_trimestre(texto: str) -> tuple[int, int]:
    """Admite '2025-Q3', 'Q3 2025', '3T2025', '3T 2025'."""
    t = texto.upper().replace(" ", "")
    m = re.fullmatch(r"(\d{4})-?Q([1-4])", t) or re.fullmatch(r"Q([1-4])-?(\d{4})", t)
    if m is None:
        m = re.fullmatch(r"([1-4])T-?(\d{4})", t)
    if m is None:
        raise ValueError(f"Trimestre no reconocido: {texto!r}")
    a, b = m.groups()
    return (int(b), int(a)) if len(a) == 4 else (int(a), int(b))


# ---------------------------------------------------------------- NIF / CIF
def normalizar_nif(valor: str | None) -> str | None:
    if not valor:
        return None
    v = re.sub(r"[\s.\-/]", "", valor.upper())
    if v.startswith("ES") and len(v) == 11:  # NIF-IVA intracomunitario
        v = v[2:]
    return v or None


def _dni_ok(numero: str, letra: str) -> bool:
    return numero.isdigit() and _LETRAS_DNI[int(numero) % 23] == letra


def _cif_ok(cif: str) -> bool:
    letra, cuerpo, control = cif[0], cif[1:8], cif[8]
    if not cuerpo.isdigit():
        return False
    suma = 0
    for i, c in enumerate(cuerpo):
        n = int(c)
        if i % 2 == 0:  # posiciones impares (1ª, 3ª, 5ª, 7ª): doblar y sumar dígitos
            n *= 2
            n = n // 10 + n % 10
        suma += n
    digito = (10 - suma % 10) % 10
    letra_ctrl = _LETRAS_CONTROL_CIF[digito]
    if letra in "KPQRSNW":
        return control == letra_ctrl
    if letra in "ABEH":
        return control == str(digito)
    return control in (str(digito), letra_ctrl)


def validar_nif(valor: str | None) -> bool:
    """Valida DNI, NIE y CIF españoles (incluido dígito/letra de control)."""
    v = normalizar_nif(valor)
    if not v or len(v) != 9:
        return False
    if re.fullmatch(r"\d{8}[A-Z]", v):
        return _dni_ok(v[:8], v[8])
    if re.fullmatch(r"[XYZ]\d{7}[A-Z]", v):
        return _dni_ok(str("XYZ".index(v[0])) + v[1:8], v[8])
    if re.fullmatch(r"[ABCDEFGHJKLMNPQRSUVW]\d{7}[0-9A-J]", v):
        return _cif_ok(v)
    return False
