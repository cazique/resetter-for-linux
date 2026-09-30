"""Motor SQLAlchemy y gestión de sesiones (SQLite en dev, PostgreSQL en prod)."""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


def crear_engine(url: str | None = None) -> Engine:
    url = url or get_settings().database_url
    es_sqlite = url.startswith("sqlite")
    engine = create_engine(
        url,
        # Flet ejecuta callbacks en varios hilos: SQLite debe permitirlo
        connect_args={"check_same_thread": False} if es_sqlite else {},
        pool_pre_ping=not es_sqlite,
    )
    if es_sqlite:
        @event.listens_for(engine, "connect")
        def _sqlite_pragmas(dbapi_conn, _):  # pragma: no cover - trivial
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")  # SQLite no las aplica por defecto
            cur.execute("PRAGMA journal_mode=WAL")
            cur.close()
    return engine


engine = crear_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@contextmanager
def get_session() -> Iterator[Session]:
    """Sesión transaccional: commit al salir, rollback si hay excepción."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(bind: Engine | None = None) -> None:
    """Crea las tablas. En producción usa migraciones Alembic en su lugar."""
    from . import models  # noqa: F401  (registra los modelos en Base.metadata)

    Base.metadata.create_all(bind=bind or engine)
