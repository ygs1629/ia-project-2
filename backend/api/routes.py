"""
routes.py — Endpoints de la API del asistente financiero.

Endpoints que consume el frontend (api.js):
    GET  /api/dashboard                     → gastos_por_categoria + alerta
    GET  /api/resumen?periodo=X             → { ingresos, gastos, ahorro }
    GET  /api/top-gastos?periodo=X&n=5      → lista de los N gastos más altos
    GET  /api/objetivo                      → primer objetivo (el frontend solo renderiza uno)
    POST /api/chat                          → mensaje al agente LangGraph
    POST /api/objetivos                     → crear o actualizar un objetivo
"""

import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from langchain_core.messages import HumanMessage, AIMessage
from pydantic import BaseModel

from agent.graph import build_graph

DB_PATH = Path(__file__).parent.parent / "data" / "finanzas.db"
PERIODOS_VALIDOS = {"semana", "mes", "trimestre", "semestre", "anual"}

router = APIRouter(prefix="/api")

# Funciones útiles internas

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _fecha_inicio(periodo: str) -> date:
    """Devuelve la fecha de inicio del periodo relativa a hoy."""
    hoy = date.today()
    if periodo == "semana":
        return hoy - timedelta(days=hoy.weekday())
    elif periodo == "mes":
        return hoy.replace(day=1)
    elif periodo == "trimestre":
        mes = ((hoy.month - 1) // 3) * 3 + 1
        return hoy.replace(month=mes, day=1)
    elif periodo == "semestre":
        mes = 1 if hoy.month <= 6 else 7
        return hoy.replace(month=mes, day=1)
    else:  # anual
        return hoy.replace(month=1, day=1)

def _validar_periodo(periodo: str):
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
        if row["importe_objetivo"] else 0
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

# Modelos Pydantic

class MensajeChat(BaseModel):
    mensaje: str
    historial: list[dict] = []  
    user_id: str = ""           

class ObjetivoIn(BaseModel):
    nombre: str
    importe_objetivo: float
    importe_actual: float = 0.0
    fecha_limite: str  # ISO: "2025-12-31"

# GET /api/dashboard

@router.get("/dashboard")
def get_dashboard(periodo: str = Query(default="mes")):
    """
    Devuelve gastos por categoría del periodo y el estado de alerta.
    El frontend usa este endpoint SOLO para el gráfico donut y la alerta.
    El balance y el top de gastos tienen endpoints propios.
    """
    _validar_periodo(periodo)
    hoy = date.today()
    inicio = _fecha_inicio(periodo)

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

    # alertas desactivadas (alertas.py eliminado)
    alerta = {"activa": False, "mensaje": None}

    return {
        "periodo":              periodo,
        "gastos_por_categoria": gastos_por_categoria,
        "alerta":               alerta,
    }

# GET /api/resumen?periodo=X

@router.get("/resumen")
def get_resumen(periodo: str = Query(default="mes")):
    """Balance ingresos vs gastos del periodo."""
    _validar_periodo(periodo)
    hoy = date.today()
    inicio = _fecha_inicio(periodo)

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
    inicio = _fecha_inicio(periodo)

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

# GET /api/objetivo  (singular)

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

# POST /api/objetivos  — crear o actualizar (todavía no implementado en el frontend)

@router.post("/objetivos", status_code=201)
def post_objetivo(objetivo: ObjetivoIn):
    """Crea o actualiza un objetivo (upsert por nombre)."""
    try:
        date.fromisoformat(objetivo.fecha_limite)
    except ValueError:
        raise HTTPException(status_code=400, detail="fecha_limite debe ser YYYY-MM-DD.")

    if objetivo.importe_objetivo <= 0:
        raise HTTPException(status_code=400, detail="importe_objetivo debe ser mayor que 0.")

    hoy = date.today()
    with _get_conn() as conn:
        conn.execute(
            """
            INSERT INTO objetivos (nombre, importe_objetivo, importe_actual, fecha_limite)
            VALUES (:nombre, :importe_objetivo, :importe_actual, :fecha_limite)
            ON CONFLICT(nombre) DO UPDATE SET
                importe_objetivo = excluded.importe_objetivo,
                importe_actual   = excluded.importe_actual,
                fecha_limite     = excluded.fecha_limite
            """,
            objetivo.model_dump(),
        )
        conn.commit()
        row = conn.execute(
            "SELECT id, nombre, importe_objetivo, importe_actual, fecha_limite FROM objetivos WHERE nombre = ?",
            (objetivo.nombre,),
        ).fetchone()

    return _objetivo_dict(row, hoy)

# POST /api/chat

@router.post("/chat")
def post_chat(
    body: MensajeChat,
    api_key: str = Depends(_extract_api_key),
):
    """
    Recibe el mensaje del usuario y el historial en formato {rol, texto}
    (el formato que usa app.js), lo convierte a mensajes LangChain,
    invoca el grafo y devuelve { respuesta, tool_usada }.
    """
    mensajes = []
    for entry in body.historial:
        rol   = entry.get("rol", "usuario")
        texto = entry.get("texto", "")
        if rol == "usuario":
            mensajes.append(HumanMessage(content=texto))
        elif rol == "agente":
            mensajes.append(AIMessage(content=texto))

    mensajes.append(HumanMessage(content=body.mensaje))

    try:
        graph = build_graph(api_key)
        result = graph.invoke({"messages": mensajes})
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