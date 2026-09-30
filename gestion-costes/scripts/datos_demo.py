"""Carga datos de ejemplo para probar la app: python scripts/datos_demo.py"""
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import crud  # noqa: E402
from app.database import get_session, init_db  # noqa: E402
from app.schemas import EmpleadoCreate, FacturaCreate, ParteTrabajoCreate, ProyectoCreate  # noqa: E402

init_db()
hoy = date.today()
with get_session() as s:
    crud.sembrar_datos_iniciales(s)
    if crud.listar_empleados(s):
        sys.exit("Ya hay datos; borra datos/gestion_costes.db si quieres empezar de cero.")
    ana = crud.crear_empleado(s, EmpleadoCreate(nombre="Ana López", coste_hora=22))
    luis = crud.crear_empleado(s, EmpleadoCreate(nombre="Luis Pérez", coste_hora=18))
    obra = crud.crear_proyecto(s, ProyectoCreate(nombre="Reforma C/ Mayor 12", cliente="Comunidad Mayor"))
    nave = crud.crear_proyecto(s, ProyectoCreate(nombre="Nave Polígono Sur", cliente="Logística Sur SL"))
    mat, comb = crud.categoria_por_nombre(s, "Material"), crud.categoria_por_nombre(s, "Combustible")
    crud.crear_factura(s, FacturaCreate(
        numero="F25-0412", fecha_emision=hoy - timedelta(days=5),
        proveedor={"nombre": "Ferretería Industrial Pepe SL", "nif": "B12345674"},
        lineas_iva=[{"tipo": 21, "base": "412,30"}], categoria_id=mat.id, proyecto_id=obra.id,
        estado_pago="parcial", importe_pagado="200"))
    crud.crear_factura(s, FacturaCreate(
        numero="T-88213", fecha_emision=hoy - timedelta(days=2),
        proveedor={"nombre": "Gasolinera Km 12 SA", "nif": "A58818501"},
        lineas_iva=[{"tipo": 21, "base": "57,85"}], categoria_id=comb.id, estado_pago="pagado",
        requiere_revision=True, ocr_confianza=0.62))
    crud.crear_factura(s, FacturaCreate(
        numero="2025/331", fecha_emision=hoy - timedelta(days=12),
        proveedor={"nombre": "Restaurante El Cruce", "nif": "X1234567L"},
        lineas_iva=[{"tipo": 10, "base": "36,36"}, {"tipo": 21, "base": "8,26"}], proyecto_id=nave.id))
    for d, e, p, h, km, g in [
        (1, ana, obra, 8, 42, ["Comida 12,50€"]),
        (1, luis, obra, 8, 0, []),
        (3, ana, nave, 6, 120, ["Media dieta 26,67€", "Parking 4,20€"]),
        (4, luis, nave, 9, 95, ["Comida 14€"]),
    ]:
        crud.crear_parte(s, ParteTrabajoCreate(empleado_id=e.id, proyecto_id=p.id, fecha=hoy - timedelta(days=d),
                                               horas=h, km=km, gastos=g))
print("Datos de ejemplo cargados ✔")
