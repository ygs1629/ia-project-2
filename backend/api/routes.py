"""
routes.py — Endpoints de la API del asistente financiero.

Endpoints que consume el frontend (api.js):
    GET  /api/dashboard                     → gastos_por_categoria
    GET  /api/resumen?periodo=X             → { ingresos, gastos, ahorro }
    GET  /api/top-gastos?periodo=X&n=5      → lista de los N gastos más altos
    GET  /api/objetivo                      → objetivo de ahorro
    POST /api/chat                          → mensaje al agente LangGraph
    POST /api/objetivos                     → crear o actualizar el objetivo
"""

import sqlite3
from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from agent.graph import build_graph
from utils import fecha_inicio, PERIODOS_VALIDOS

DB_PATH = Path(__file__).parent.parent / "data" / "finanzas.db"

MAX_MENSAJE_CHARS = 4_000     

router = APIRouter(prefix="/api")

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _validar_periodo(periodo: str) -> None:
    if periodo not in PERIODOS_VALIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"Periodo inválido. Usa uno de: {', '.join(sorted(PERIODOS_VALIDOS))}",
        )

def _extract_api_key(authorization: Optional[str] = Header(None)) -> str:
    """Extrae la API Key del header Authorization: Bearer <key>."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="API Key requerida. Incluye el header: Authorization: Bearer <tu-api-key>",
        )
    key = authorization.removeprefix("Bearer ").strip()
    if not key:
        raise HTTPException(status_code=401, detail="API Key vacía.")
    return key

def _objetivo_dict(row, hoy: date) -> dict:
    """Construye el dict de un objetivo desde una fila SQLite."""
    falta = round(row["importe_objetivo"] - row["importe_actual"], 2)
    porcentaje = (
        round(row["importe_actual"] / row["importe_objetivo"] * 100, 1)
        if row["importe_objetivo"]
        else 0
    )
    dias_restantes = (date.fromisoformat(row["fecha_limite"]) - hoy).days
    return {
        "id":               row["id"],
        "nombre":           row["nombre"],
        "importe_objetivo": row["importe_objetivo"],
        "importe_actual":   row["importe_actual"],
        "fecha_limite":     row["fecha_limite"],
        "falta":            falta,
        "porcentaje":       porcentaje,
        "dias_restantes":   dias_restantes,
    }

class MensajeChat(BaseModel):
    mensaje: str
    user_id: str

class ObjetivoIn(BaseModel):
    nombre: str
    importe_objetivo: float
    importe_actual: float = 0.0
    fecha_limite: str  

# GET /api/dashboard

@router.get("/dashboard")
def get_dashboard(periodo: str = Query(default="mes")):
    """
    Devuelve gastos por categoría del periodo.
    El frontend usa este endpoint SOLO para el gráfico donut.
    El balance y el top de gastos tienen endpoints propios.
    """
    _validar_periodo(periodo)
    hoy = date.today()
    inicio = fecha_inicio(periodo)

    with _get_conn() as conn:
        rows = conn.execute(
            """
            SELECT categoria, ROUND(ABS(SUM(importe)), 2) AS total
            FROM transacciones
            WHERE fecha >= ? AND fecha <= ? AND importe < 0
            GROUP BY categoria ORDER BY total DESC
            """,
            (inicio.isoformat(), hoy.isoformat()),
        ).fetchall()

    gastos_por_categoria = {row["categoria"]: row["total"] for row in rows}

    return {
        "periodo":              periodo,
        "gastos_por_categoria": gastos_por_categoria,
    }

# GET /api/resumen?periodo=X

@router.get("/resumen")
def get_resumen(periodo: str = Query(default="mes")):
    """Balance ingresos vs gastos del periodo."""
    _validar_periodo(periodo)
    hoy = date.today()
    inicio = fecha_inicio(periodo)

    with _get_conn() as conn:
        row = conn.execute(
            """
            SELECT
                ROUND(SUM(CASE WHEN importe > 0 THEN importe ELSE 0 END), 2) AS ingresos,
                ROUND(ABS(SUM(CASE WHEN importe < 0 THEN importe ELSE 0 END)), 2) AS gastos
            FROM transacciones
            WHERE fecha >= ? AND fecha <= ?
            """,
            (inicio.isoformat(), hoy.isoformat()),
        ).fetchone()

    ingresos = row["ingresos"] or 0.0
    gastos   = row["gastos"]   or 0.0
    return {
        "ingresos": ingresos,
        "gastos":   gastos,
        "ahorro":   round(ingresos - gastos, 2),
    }

# GET /api/top-gastos?periodo=X&n=5

@router.get("/top-gastos")
def get_top_gastos(
    periodo: str = Query(default="mes"),
    n: int = Query(default=5, ge=1, le=20),
):
    """Los N conceptos individuales más caros del periodo."""
    _validar_periodo(periodo)
    hoy = date.today()
    inicio = fecha_inicio(periodo)

    with _get_conn() as conn:
        rows = conn.execute(
            """
            SELECT concepto, ROUND(ABS(importe), 2) AS importe, fecha, categoria
            FROM transacciones
            WHERE fecha >= ? AND fecha <= ? AND importe < 0
            ORDER BY ABS(importe) DESC
            LIMIT ?
            """,
            (inicio.isoformat(), hoy.isoformat(), n),
        ).fetchall()

    return [
        {
            "concepto":  row["concepto"],
            "importe":   row["importe"],
            "fecha":     row["fecha"],
            "categoria": row["categoria"],
        }
        for row in rows
    ]

# GET /api/objetivo

@router.get("/objetivo")
def get_objetivo():
    """Devuelve el primer objetivo de ahorro. El frontend solo renderiza uno."""
    hoy = date.today()
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT id, nombre, importe_objetivo, importe_actual, fecha_limite FROM objetivos LIMIT 1"
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="No hay objetivos definidos.")

    return _objetivo_dict(row, hoy)

# POST /api/objetivos

@router.post("/objetivos", status_code=201)
def post_objetivo(objetivo: ObjetivoIn):
    """Reemplaza el único objetivo de ahorro. Siempre hay como máximo 1."""
    try:
        date.fromisoformat(objetivo.fecha_limite)
    except ValueError:
        raise HTTPException(status_code=400, detail="fecha_limite debe ser YYYY-MM-DD.")

    if objetivo.importe_objetivo <= 0:
        raise HTTPException(status_code=400, detail="importe_objetivo debe ser mayor que 0.")

    hoy = date.today()
    with _get_conn() as conn:
        conn.execute("DELETE FROM objetivos")
        conn.execute(
            """
            INSERT INTO objetivos (id, nombre, importe_objetivo, importe_actual, fecha_limite)
            VALUES (1, :nombre, :importe_objetivo, :importe_actual, :fecha_limite)
            """,
            objetivo.model_dump(),
        )
        conn.commit()
        row = conn.execute(
            "SELECT id, nombre, importe_objetivo, importe_actual, fecha_limite FROM objetivos WHERE id = 1",
        ).fetchone()

    return _objetivo_dict(row, hoy)

# POST /api/chat

@router.post("/chat")
def post_chat(
    body: MensajeChat,
    api_key: str = Depends(_extract_api_key),
):
    """
    Recibe el mensaje del usuario e invoca el grafo LangGraph.
    El historial de conversación lo gestiona LangGraph automáticamente
    mediante MemorySaver, usando user_id como thread_id.
    """
    if len(body.mensaje) > MAX_MENSAJE_CHARS:
        raise HTTPException(
            status_code=422,
            detail=f"El mensaje supera el límite de {MAX_MENSAJE_CHARS} caracteres.",
        )

    config = {"configurable": {"thread_id": body.user_id}}

    try:
        graph = build_graph(api_key)
        result = graph.invoke({"messages": [HumanMessage(content=body.mensaje)]}, config)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Error del agente: {str(exc)}")

    respuesta = result["messages"][-1].content

    tool_usada = None
    for msg in reversed(result["messages"]):
        if hasattr(msg, "name") and msg.name:
            tool_usada = msg.name
            break

    return {
        "respuesta":  respuesta,
        "tool_usada": tool_usada,
    }