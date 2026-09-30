from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.database import Base
from app.fiscal import parse_trimestre, rango_trimestre, trimestre_de, validar_nif
from app.models import Empleado, Factura, GastoParte, LineaIVA, ParteTrabajo, Proveedor, Proyecto
from app.schemas import FacturaCreate, FiltroFacturas, GastoParteCreate, ParteTrabajoCreate


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def test_nif():
    assert validar_nif("12345678Z")      # DNI
    assert validar_nif("X1234567L")      # NIE
    assert validar_nif("B12345674")      # CIF dígito
    assert validar_nif("ESA58818501")    # NIF-IVA
    assert not validar_nif("B12345678")
    assert not validar_nif("12345678A")


def test_trimestres():
    assert trimestre_de(date(2025, 11, 3)) == (4, 2025)
    assert rango_trimestre(1, 2024) == (date(2024, 1, 1), date(2024, 3, 31))
    assert parse_trimestre("3T 2025") == parse_trimestre("2025-Q3") == (3, 2025)


def test_factura_multi_iva_y_coherencia():
    f = FacturaCreate(
        numero="F-001", fecha_emision=date(2025, 5, 10),
        proveedor={"nombre": "Suministros SL", "nif": "b-12345674"},
        lineas_iva=[{"tipo": 21, "base": "100,00"}, {"tipo": 10, "base": 50}],
        irpf_porcentaje=15, total="153,50",
    )
    assert f.cuota_iva == Decimal("26.00") and f.irpf_importe == Decimal("22.50")
    assert (f.trimestre, f.anio, f.proveedor.nif) == (2, 2025, "B12345674")
    with pytest.raises(ValidationError, match="no cuadra"):
        FacturaCreate(numero="F", fecha_emision=date(2025, 5, 10), proveedor_id=1,
                      lineas_iva=[{"tipo": 21, "base": 100}], total=130)


def test_filtro_rango():
    f = FiltroFacturas(trimestre=2, anio=2025, fecha_desde=date(2025, 5, 1))
    assert f.rango_efectivo() == (date(2025, 5, 1), date(2025, 6, 30))


def test_gasto_texto_libre_y_parte():
    g = GastoParteCreate.model_validate("Comida 20€")
    assert (g.tipo.value, g.concepto, g.importe) == ("comida", "Comida", Decimal("20.00"))
    p = ParteTrabajoCreate(empleado_id=1, proyecto_id=1, fecha=date(2025, 6, 2), horas=8, km=40,
                           gastos=["Parking 5,50", "Dieta media 26.67"])
    assert [x.tipo.value for x in p.gastos] == ["parking", "dieta"]


def test_orm_trimestre_y_totales(db):
    prov = Proveedor(nombre="Ferretería", nif="b12345674")
    fac = Factura(proveedor=prov, numero="A1", fecha_emision=date(2025, 8, 20), total=Decimal("0"),
                  lineas_iva=[LineaIVA(tipo=Decimal("21"), base=Decimal("200"), cuota=Decimal("42"))])
    fac.recalcular_totales()
    obra = Proyecto(nombre="Obra Calle Mayor")
    emp = Empleado(nombre="Ana", coste_hora=Decimal("18"))
    parte = ParteTrabajo(empleado=emp, proyecto=obra, fecha=date(2025, 8, 21), horas=Decimal("8"),
                         km=Decimal("50"), tarifa_km=Decimal("0.26"), coste_hora=emp.coste_hora,
                         gastos=[GastoParte(tipo="comida", concepto="Menú", importe=Decimal("20"))])
    parte.recalcular_totales()
    db.add_all([fac, parte]); db.commit()
    f = db.scalar(select(Factura))
    assert (f.trimestre, f.anio, f.trimestre_label, f.total, prov.nif) == (3, 2025, "2025-Q3", Decimal("242.00"), "B12345674")
    assert (parte.importe_km, parte.total_gastos, parte.coste_horas, parte.coste_total) == (
        Decimal("13.00"), Decimal("33.00"), Decimal("144.00"), Decimal("177.00"))
