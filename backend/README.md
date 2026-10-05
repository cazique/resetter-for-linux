# Gestor Documental — Backend (Flask)

API REST (`/api/v1`) para documentos, facturas, tickets y contactos.

## Puesta en marcha

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # configura DATABASE_URL (PostgreSQL), secretos, CORS...
flask --app run.py db upgrade   # aplica migrations/
flask --app run.py seed         # categorías predefinidas
flask --app run.py create-admin # usuario administrador
flask --app run.py run --debug  # http://localhost:5000/api/v1/health
```

Producción: `FLASK_ENV=production gunicorn -w 4 -b 0.0.0.0:5000 "run:app"`
(arranca solo si `SECRET_KEY`, `JWT_SECRET_KEY` y `DATABASE_URL` están definidos).

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/auth/register` | Registro (el primer usuario es Admin; solo un Admin asigna roles) |
| POST | `/auth/login` | `access_token` + `refresh_token` |
| POST | `/auth/refresh` | Nuevo access token (enviar refresh token como Bearer) |
| GET | `/auth/me` | Perfil del usuario |
| GET | `/categories` | Categorías activas |
| GET/POST | `/contacts` | Listado (`search`, `type`, `page`, `per_page`) / alta |
| GET/PUT/PATCH/DELETE | `/contacts/<uuid>` | CRUD |
| POST | `/documents` | Alta multipart: `image`, `category_id`, `contact_id`, `title`, `amount`, `tax_amount`, `date`, `notes` |
| GET | `/documents` | Filtros `start_date`, `end_date`, `category_id`, `contact_id`, `status`, `search`, `page`, `per_page` |
| GET/PATCH/DELETE | `/documents/<uuid>` | Detalle / actualización parcial / borrado lógico |
| GET | `/documents/<uuid>/image`, `/thumbnail` | Imagen procesada y miniatura |
| GET | `/exports/pdf` | Informe PDF (mismos filtros + `include_images`, `download`) |
| GET | `/exports/pdf/<filename>` | Descarga de un informe guardado con `download=false` |

Respuestas: `{"success": true, "data": ..., "meta": {...}}` o
`{"success": false, "message": "...", "errors": {"campo": ["..."]}}`.

Permisos: Admin y Accountant ven todos los documentos; Employee solo los suyos.

> `requirements.txt` añade fijaciones de `numpy<2`, `marshmallow<4` y
> `SQLAlchemy<2.1`: sin ellas, `opencv-python-headless==4.9.0.80` y
> `marshmallow-sqlalchemy==1.0.0` no funcionan con las versiones actuales.
