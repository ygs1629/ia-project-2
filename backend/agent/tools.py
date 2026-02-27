"""
tools.py — Herramientas que el agente LangGraph puede invocar.
Todas realizan únicamente consultas SELECT sobre finanzas.db.
El LLM NUNCA calcula: recibe los números ya calculados y solo redacta.
"""

import sqlite3
from datetime import date, timedelta
from pathlib import Path

from langchain_core.tools import tool

DB_PATH = Path(__file__).parent.parent / "data" / "finanzas.db"


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@tool
def get_gastos_periodo(periodo: str, anio: int = None) -> dict:
    """
    Devuelve el total gastado (negativo = gasto) agrupado por categoría
    para el periodo indicado.

    Parámetros:
        periodo: 'semana' | 'mes' | 'trimestre' | 'semestre' | 'anual'
        anio:    Año de referencia (por defecto el año actual).

    Devuelve un dict {categoria: importe_total} con importes positivos
    (ya invertidos para facilitar la lectura).
    """
    if anio is None:
        anio = date.today().year

    hoy = date.today()

    if periodo == "semana":
        inicio = hoy - timedelta(days=hoy.weekday())  
    elif periodo == "mes":
        inicio = hoy.replace(day=1)
    elif periodo == "trimestre":
        mes_inicio = ((hoy.month - 1) // 3) * 3 + 1
        inicio = hoy.replace(month=mes_inicio, day=1)
    elif periodo == "semestre":
        mes_inicio = 1 if hoy.month <= 6 else 7
        inicio = hoy.replace(month=mes_inicio, day=1)
    elif periodo == "anual":
        inicio = hoy.replace(month=1, day=1)
    else:
        return {"error": f"Periodo desconocido: {periodo}"}

    sql = """
        SELECT categoria, ROUND(ABS(SUM(importe)), 2) AS total
        FROM transacciones
        WHERE fecha >= ? AND fecha <= ? AND importe < 0
        GROUP BY categoria
        ORDER BY total DESC
    """
    with _get_conn() as conn:
        rows = conn.execute(sql, (inicio.isoformat(), hoy.isoformat())).fetchall()

    return {row["categoria"]: row["total"] for row in rows}

@tool
def get_evolucion_categoria(categoria: str, meses: int = 6) -> list[dict]:
    """
    Devuelve la serie temporal de gasto mensual de una categoría concreta
    para los últimos N meses.

    Parámetros:
        categoria: nombre exacto de la categoría (ej. 'Supermercado')
        meses:     número de meses hacia atrás (por defecto 6)

    Devuelve una lista de dicts [{"mes": "2024-11", "total": 234.50}, ...]
    ordenada de más antiguo a más reciente.
    """
    hoy = date.today()
    mes_offset = hoy.month - meses
    anio_inicio = hoy.year + (mes_offset - 1) // 12
    mes_inicio = ((mes_offset - 1) % 12) + 1
    inicio = date(anio_inicio, mes_inicio, 1)

    sql = """
        SELECT strftime('%Y-%m', fecha) AS mes,
               ROUND(ABS(SUM(importe)), 2) AS total
        FROM transacciones
        WHERE categoria = ?
          AND fecha >= ?
          AND importe < 0
        GROUP BY mes
        ORDER BY mes ASC
    """
    with _get_conn() as conn:
        rows = conn.execute(sql, (categoria, inicio.isoformat())).fetchall()

    return [{"mes": row["mes"], "total": row["total"]} for row in rows]

@tool
def get_resumen_ingresos_vs_gastos(periodo: str) -> dict:
    """
    Devuelve el balance del periodo: ingresos totales, gastos totales y
    ahorro neto (ingresos - gastos).

    Parámetros:
        periodo: 'semana' | 'mes' | 'trimestre' | 'semestre' | 'anual'

    Devuelve {"ingresos": x, "gastos": y, "ahorro": z}
    """
    hoy = date.today()

    if periodo == "semana":
        inicio = hoy - timedelta(days=hoy.weekday())
    elif periodo == "mes":
        inicio = hoy.replace(day=1)
    elif periodo == "trimestre":
        mes_inicio = ((hoy.month - 1) // 3) * 3 + 1
        inicio = hoy.replace(month=mes_inicio, day=1)
    elif periodo == "semestre":
        mes_inicio = 1 if hoy.month <= 6 else 7
        inicio = hoy.replace(month=mes_inicio, day=1)
    elif periodo == "anual":
        inicio = hoy.replace(month=1, day=1)
    else:
        return {"error": f"Periodo desconocido: {periodo}"}

    sql = """
        SELECT
            ROUND(SUM(CASE WHEN importe > 0 THEN importe ELSE 0 END), 2) AS ingresos,
            ROUND(ABS(SUM(CASE WHEN importe < 0 THEN importe ELSE 0 END)), 2) AS gastos
        FROM transacciones
        WHERE fecha >= ? AND fecha <= ?
    """
    with _get_conn() as conn:
        row = conn.execute(sql, (inicio.isoformat(), hoy.isoformat())).fetchone()

    ingresos = row["ingresos"] or 0.0
    gastos = row["gastos"] or 0.0
    return {
        "ingresos": ingresos,
        "gastos": gastos,
        "ahorro": round(ingresos - gastos, 2),
    }

@tool
def get_progreso_objetivo(nombre: str = "") -> dict:
    """
    Devuelve el estado actual del objetivo de ahorro activo.
    Solo existe un objetivo a la vez; el parámetro nombre se ignora.

    Devuelve un dict con:
        - nombre, importe_objetivo, importe_actual, fecha_limite
        - falta: cuánto queda por ahorrar
        - dias_restantes: días hasta la fecha límite
        - porcentaje: % completado
    """
    sql = """
        SELECT nombre, importe_objetivo, importe_actual, fecha_limite
        FROM objetivos
        LIMIT 1
    """
    with _get_conn() as conn:
        row = conn.execute(sql).fetchone()

    if row is None:
        return {"error": "No hay ningún objetivo definido todavía."}

    hoy = date.today()
    fecha_limite = date.fromisoformat(row["fecha_limite"])
    dias_restantes = (fecha_limite - hoy).days
    falta = round(row["importe_objetivo"] - row["importe_actual"], 2)
    porcentaje = round(row["importe_actual"] / row["importe_objetivo"] * 100, 1) if row["importe_objetivo"] else 0

    return {
        "nombre": row["nombre"],
        "importe_objetivo": row["importe_objetivo"],
        "importe_actual": row["importe_actual"],
        "fecha_limite": row["fecha_limite"],
        "falta": falta,
        "dias_restantes": dias_restantes,
        "porcentaje": porcentaje,
    }

@tool
def get_top_gastos(periodo: str, n: int = 5) -> list[dict]:
    """
    Devuelve los N conceptos individuales más caros del periodo.

    Parámetros:
        periodo: 'semana' | 'mes' | 'trimestre' | 'semestre' | 'anual'
        n:       cuántos resultados devolver (por defecto 5)

    Devuelve lista de dicts [{"concepto": ..., "importe": ..., "fecha": ..., "categoria": ...}]
    """
    hoy = date.today()

    if periodo == "semana":
        inicio = hoy - timedelta(days=hoy.weekday())
    elif periodo == "mes":
        inicio = hoy.replace(day=1)
    elif periodo == "trimestre":
        mes_inicio = ((hoy.month - 1) // 3) * 3 + 1
        inicio = hoy.replace(month=mes_inicio, day=1)
    elif periodo == "semestre":
        mes_inicio = 1 if hoy.month <= 6 else 7
        inicio = hoy.replace(month=mes_inicio, day=1)
    elif periodo == "anual":
        inicio = hoy.replace(month=1, day=1)
    else:
        return [{"error": f"Periodo desconocido: {periodo}"}]

    sql = """
        SELECT concepto, ROUND(ABS(importe), 2) AS importe, fecha, categoria
        FROM transacciones
        WHERE fecha >= ? AND fecha <= ? AND importe < 0
        ORDER BY ABS(importe) DESC
        LIMIT ?
    """
    with _get_conn() as conn:
        rows = conn.execute(sql, (inicio.isoformat(), hoy.isoformat(), n)).fetchall()

    return [
        {
            "concepto": row["concepto"],
            "importe": row["importe"],
            "fecha": row["fecha"],
            "categoria": row["categoria"],
        }
        for row in rows
    ]

ALL_TOOLS = [
    get_gastos_periodo,
    get_evolucion_categoria,
    get_resumen_ingresos_vs_gastos,
    get_progreso_objetivo,
    get_top_gastos,
]