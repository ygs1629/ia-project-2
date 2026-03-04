"""
app.py — Punto de entrada de la API del asistente financiero.
"""

import sqlite3
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router
from utils import DB_PATH  

def init_db() -> None:
    """
    Crea las tablas si no existen.
    Se ejecuta una sola vez al arrancar el servidor, garantizando
    que el esquema esté listo independientemente de si se han
    ejecutado los scripts de datos o no.

    Nota de diseño — tabla objetivos:
        La aplicación soporta UN único objetivo de ahorro activo.
        La tabla usa id=1 fijo: POST /api/objetivos hace DELETE + INSERT con id=1,
        y GET /api/objetivo devuelve ese registro.
        Se ha eliminado AUTOINCREMENT para reflejar esta semántica explícitamente.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS transacciones (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha     TEXT    NOT NULL,
                concepto  TEXT    NOT NULL,
                importe   REAL    NOT NULL,
                categoria TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS objetivos (
                id               INTEGER PRIMARY KEY,
                nombre           TEXT    NOT NULL UNIQUE,
                importe_objetivo REAL    NOT NULL,
                importe_actual   REAL    NOT NULL DEFAULT 0,
                fecha_limite     DATE    NOT NULL
            );
        """)
        conn.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa la base de datos al arrancar el servidor."""
    init_db()
    yield

app = FastAPI(
    title="Asistente Financiero Virtual",
    description=(
        "API del asistente financiero. "
        "La API Key del usuario se pasa en cada petición y nunca se almacena."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

ORIGENES_PERMITIDOS = [
    "https://martasolerebri.github.io",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGENES_PERMITIDOS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/", tags=["health"])
def health_check():
    """Comprueba que la API está en marcha."""
    return {"status": "ok", "mensaje": "Asistente Financiero API activa."}