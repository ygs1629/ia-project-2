"""
utils.py — Funciones compartidas entre agent/tools.py y api/routes.py.
"""

from datetime import date, timedelta


PERIODOS_VALIDOS = {"semana", "mes", "trimestre", "semestre", "anual"}


def fecha_inicio(periodo: str) -> date:
    """
    Devuelve la fecha de inicio del periodo relativa a hoy.

    Parámetros:
        periodo: 'semana' | 'mes' | 'trimestre' | 'semestre' | 'anual'

    Lanza ValueError si el periodo no es válido.
    """
    if periodo not in PERIODOS_VALIDOS:
        raise ValueError(
            f"Periodo inválido: '{periodo}'. "
            f"Usa uno de: {', '.join(sorted(PERIODOS_VALIDOS))}"
        )

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
