# Gestión de Costes (Facturas · Partes de trabajo · OCR con IA)

App CRUD multiplataforma (Web + Android con Flet) para control de costes,
facturas de proveedores y partes de trabajo de empleados.

## Estado

| Paso | Contenido | Estado |
|------|-----------|--------|
| 1 | Modelos SQLAlchemy + esquemas Pydantic (`app/models.py`, `app/schemas.py`, `app/fiscal.py`) | ✅ |
| 2 | Extractor OCR/IA (`app/ocr_service.py`) | ✅ |
| 3 | CRUD, consultas y exportación Excel | pendiente |
| 4 | Interfaz Flet (`main.py`) | pendiente |
| 5 | Despliegue Web / APK | pendiente |

## Puesta en marcha

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # añade GEMINI_API_KEY u OPENAI_API_KEY
python -c "from app.database import init_db; init_db()"
pytest -q
```

Prueba rápida del OCR:

```python
from app.ocr_service import OCRService
r = OCRService().extraer("factura.jpg")
print(r.model_dump_json(indent=2, exclude={"bruto"}))
```
