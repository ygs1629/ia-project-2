"""
tools.py — Herramientas que el agente LangGraph puede invocar.
"""

import sqlite3
from datetime import date,timedelta
from pathlib import Path

from dateutil.relativedelta import relativedelta

from langchain_core.tools import tool

from utils import fecha_inicio

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
        anio:    Año de referencia (reservado para uso futuro).

    Devuelve un dict {categoria: importe_total} con importes positivos
    (ya invertidos para facilitar la lectura).
    """
    try:
        inicio = fecha_inicio(periodo)
    except ValueError as e:
        return {"error": str(e)}

    hoy = date.today()
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
    
    inicio = date(hoy.year, hoy.month, 1) - relativedelta(months=meses)

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
    try:
        inicio = fecha_inicio(periodo)
    except ValueError as e:
        return {"error": str(e)}

    hoy = date.today()
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
def get_progreso_objetivo() -> dict:
    """
    Devuelve el estado actual del objetivo de ahorro activo.
    Solo existe un objetivo a la vez.

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
    porcentaje = (
        round(row["importe_actual"] / row["importe_objetivo"] * 100, 1)
        if row["importe_objetivo"]
        else 0
    )

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
    try:
        inicio = fecha_inicio(periodo)
    except ValueError as e:
        return [{"error": str(e)}]

    hoy = date.today()
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

@tool
def get_ratio_endeudamiento(meses: int = 1) -> dict:
    """
    Calcula el ratio de endeudamiento y esfuerzo financiero del usuario (Vivienda + Deudas / Ingresos).
    Argumentos:
    - meses (int): El número de meses hacia atrás para calcular el ratio (ej: 1 para un mes, 3 para un trimestre, 6 para semestre, 12 para un año). Por defecto es 1.
    """
    try:
        hoy = date.today()
        dias_retroceso = 30 * meses
        fecha_inicio_periodo = hoy - timedelta(days=dias_retroceso)
        
        with _get_conn() as conn:
            row_ingresos = conn.execute(
                "SELECT SUM(importe) AS total FROM transacciones WHERE importe > 0 AND fecha >= ?", 
                (fecha_inicio_periodo.isoformat(),)
            ).fetchone()
            ingresos = float(row_ingresos["total"]) if row_ingresos["total"] else 0.0
            
            sql_deudas = """
                SELECT ABS(SUM(importe)) AS total 
                FROM transacciones 
                WHERE importe < 0 
                AND fecha >= ? 
                AND (
                    categoria = 'Vivienda' 
                    OR LOWER(concepto) LIKE '%préstamo%' 
                    OR LOWER(concepto) LIKE '%prestamo%' 
                    OR LOWER(concepto) LIKE '%tarjeta%'
                    OR LOWER(concepto) LIKE '%crédito%'
                    OR LOWER(concepto) LIKE '%credito%'
                    OR LOWER(concepto) LIKE '%aplazado%'
                )
            """
            row_deudas = conn.execute(sql_deudas, (fecha_inicio_periodo.isoformat(),)).fetchone()
            deudas = float(row_deudas["total"]) if row_deudas["total"] else 0.0

        if ingresos == 0:
            return {
                "error": f"No hay ingresos registrados en los últimos {meses} meses para calcular el ratio.",
                "gastos_vivienda_y_deuda": deudas
            }

        ratio = (deudas / ingresos) * 100
        estado = "SALUDABLE" if ratio <= 35 else "PELIGRO"
        
        return {
            "periodo_analizado_meses": meses,
            "ingresos_estimados": round(ingresos, 2),
            "gastos_vivienda_y_deudas": round(deudas, 2),
            "ratio_endeudamiento_pct": round(ratio, 2),
            "limite_recomendado_pct": 35.0,
            "estado_financiero": estado,
            "directriz_para_el_agente": (
                f"En los últimos {meses} meses, el ratio de esfuerzo financiero es del {round(ratio, 2)}%. "
                f"Límite sano: 35%. "
                f"Si es SALUDABLE, felicítalo. Si es PELIGRO, adviértele del sobreendeudamiento."
            )
        }
    except Exception as e:
        return {"error": f"Error interno al calcular la deuda: {str(e)}"}
    
@tool
def evaluar_presupuesto_50_30_20(meses: int = 1) -> dict:
    """
    Evalúa las finanzas del usuario usando la regla del 50/30/20.
    Argumentos:
    - meses (int): Periodo de meses a evaluar (ej: 1 para el último mes, 12 para el último año). Por defecto es 1.
    """
    try:
        hoy = date.today()
        dias_retroceso = 30 * meses
        fecha_inicio_periodo = hoy - timedelta(days=dias_retroceso)
        
        with _get_conn() as conn:
            row_ingresos = conn.execute(
                "SELECT SUM(importe) AS total FROM transacciones WHERE importe > 0 AND fecha >= ?", 
                (fecha_inicio_periodo.isoformat(),)
            ).fetchone()
            ingresos = float(row_ingresos["total"]) if row_ingresos["total"] else 0.0
            
            if ingresos == 0:
                return {"error": f"No hay ingresos en los últimos {meses} meses para evaluar el presupuesto."}

            sql_necesidades = """
                SELECT ABS(SUM(importe)) AS total FROM transacciones 
                WHERE importe < 0 AND fecha >= ? 
                AND categoria IN ('Vivienda', 'Supermercado', 'Transporte', 'Suministros', 'Salud')
            """
            row_nec = conn.execute(sql_necesidades, (fecha_inicio_periodo.isoformat(),)).fetchone()
            gastos_necesidades = float(row_nec["total"]) if row_nec["total"] else 0.0

            sql_deseos = """
                SELECT ABS(SUM(importe)) AS total FROM transacciones 
                WHERE importe < 0 AND fecha >= ? 
                AND categoria IN ('Restaurantes', 'Ocio', 'Suscripciones', 'Otros')
            """
            row_des = conn.execute(sql_deseos, (fecha_inicio_periodo.isoformat(),)).fetchone()
            gastos_deseos = float(row_des["total"]) if row_des["total"] else 0.0

        ahorro_real = ingresos - (gastos_necesidades + gastos_deseos)
        pct_necesidades = (gastos_necesidades / ingresos) * 100
        pct_deseos = (gastos_deseos / ingresos) * 100
        pct_ahorro = (ahorro_real / ingresos) * 100

        return {
            "periodo_analizado_meses": meses,
            "tu_distribucion_real": {
                "necesidades_pct": round(pct_necesidades, 2),
                "deseos_pct": round(pct_deseos, 2),
                "ahorro_pct": round(pct_ahorro, 2)
            },
            "importes_reales_euros": {
                "ingresos": round(ingresos, 2),
                "necesidades": round(gastos_necesidades, 2),
                "deseos": round(gastos_deseos, 2),
                "ahorro": round(ahorro_real, 2)
            },
            "directriz_para_el_agente": (
                f"Menciona que este análisis corresponde a los últimos {meses} meses. "
                f"Su distribución es {round(pct_necesidades, 1)}% / {round(pct_deseos, 1)}% / {round(pct_ahorro, 1)}% "
                f"(vs ideal 50/30/20). Dale un diagnóstico."
            )
        }
    except Exception as e:
        return {"error": f"Error interno al calcular el presupuesto: {str(e)}"}

ALL_TOOLS = [
    get_gastos_periodo,
    get_evolucion_categoria,
    get_resumen_ingresos_vs_gastos,
    get_progreso_objetivo,
    get_top_gastos,
    get_ratio_endeudamiento,
    evaluar_presupuesto_50_30_20
]