"""
utils.py — Funciones compartidas entre agent/tools.py y api/routes.py.
"""

from datetime import date, timedelta
from dateutil.relativedelta import relativedelta


PERIODOS_VALIDOS = {"semana", "mes", "trimestre", "semestre", "anual"}


def fecha_inicio(periodo: str) -> date:
    """
    Devuelve la fecha de inicio del periodo como ventana deslizante
    hacia atrás desde hoy (rolling window).

    Esto garantiza que cada periodo siempre muestre datos distintos
    y que nunca queden vacíos por estar al inicio del mes/año.

        semana    → últimos 7 días
        mes       → últimos 30 días
        trimestre → últimos 3 meses
        semestre  → últimos 6 meses
        anual     → últimos 12 meses

    Lanza ValueError si el periodo no es válido.
    """
    if periodo not in PERIODOS_VALIDOS:
        raise ValueError(
            f"Periodo inválido: '{periodo}'. "
            f"Usa uno de: {', '.join(sorted(PERIODOS_VALIDOS))}"
        )

    hoy = date.today()

    if periodo == "semana":
        return hoy - timedelta(weeks=1)
    elif periodo == "mes":
        return hoy - relativedelta(months=1)
    elif periodo == "trimestre":
        return hoy - relativedelta(months=3)
    elif periodo == "semestre":
        return hoy - relativedelta(months=6)
    else:  
        return hoy - relativedelta(years=1)