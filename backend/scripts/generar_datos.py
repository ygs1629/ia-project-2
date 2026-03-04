"""
generar_datos.py — Script de uso único.
"""

import pandas as pd
import numpy as np
import random
from datetime import date, timedelta
from pathlib import Path

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

FECHA_FIN    = date(2026, 3, 5)
FECHA_INICIO = (FECHA_FIN - timedelta(days=18 * 30)).replace(day=1)

OUTPUT_PATH = Path(__file__).parent.parent / "data" / "transacciones_sucias.csv"
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

SUPERMERCADOS = [
    ("TPV MERCADONA {n:03d}",    -1, "supermercado",  30,  85),
    ("COMPRA CARREFOUR {n:03d}", -1, "supermercado",  25,  70),
    ("LIDL ES {n:04d}",          -1, "supermercado",  15,  55),
    ("ALDI SUPERMERCADOS",        -1, "supermercado",  15,  50),
    ("CONSUM COOP {n:03d}",      -1, "supermercado",  20,  65),
    ("AMAZON FRESH ES",           -1, "supermercado",  25,  60),
]

RESTAURANTES = [
    ("TPV BAR RESTAURANTE {n:04d}", -1, "restaurante",  8, 28),
    ("GLOVO ES {n:06d}",            -1, "restaurante", 10, 28),
    ("UBER EATS *ES {n:5d}",        -1, "restaurante", 10, 28),
    ("JUST EAT SPAIN",              -1, "restaurante",  9, 25),
    ("MCDONALDS {ciudad}",          -1, "restaurante",  5, 14),
    ("STARBUCKS {n:04d} ES",        -1, "restaurante",  4,  9),
    ("CAFETERIA {n:04d}",           -1, "restaurante",  2,  8),
]

OCIO = [
    ("CINES ODEON {n:03d}",      -1, "ocio",  7, 18),
    ("STEAM PURCHASE",           -1, "ocio",  3, 25),
    ("TICKETMASTER ES",          -1, "ocio", 18, 70),
    ("FNAC SPAIN {n:04d}",       -1, "ocio", 10, 45),
    ("PAYPAL *GAMING {n:8d}",    -1, "ocio",  4, 20),
    ("AMAZON MARKETPLACE ES",    -1, "ocio", 10, 60),
]

TRANSPORTE = [
    ("REPSOL {n:04d}",           -1, "transporte", 35, 65),
    ("BP ESTACION {n:04d}",      -1, "transporte", 35, 60),
    ("RENFE INTERNET {n:8d}",    -1, "transporte", 12, 55),
    ("EMT MADRID RECARGA",       -1, "transporte", 10, 20),
    ("CABIFY VIAJE {n:8d}",      -1, "transporte",  6, 18),
    ("PARKING {n:04d} ES",       -1, "transporte",  2, 12),
    ("AUTOPISTA PEAJE {n:04d}",  -1, "transporte",  2,  8),
]

SUMINISTROS = [
    ("RECIBO ENDESA {mes}",          -1, "suministros", 50, 100),
    ("RECIBO IBERDROLA {mes}",       -1, "suministros", 45,  95),
    ("RECIBO NATURGY GAS {mes}",     -1, "suministros", 30,  75),
    ("TELEFONICA MOVISTAR {mes}",    -1, "suministros", 28,  55),
    ("ORANGE SPAIN {mes}",           -1, "suministros", 18,  45),
    ("RECIBO AGUA CANAL {mes}",      -1, "suministros", 15,  40),
]

SUSCRIPCIONES = [
    ("NETFLIX.COM {n:8d}",       -1, "suscripcion", 12.99, 12.99),
    ("SPOTIFY AB {n:8d}",        -1, "suscripcion",  9.99,  9.99),
    ("AMAZON PRIME ES",          -1, "suscripcion",  4.99,  4.99),
    ("HBO MAX ES {n:6d}",        -1, "suscripcion",  8.99,  8.99),
    ("DISNEY PLUS ES",           -1, "suscripcion",  6.99,  6.99),
    ("ADOBE INC {n:8d}",         -1, "suscripcion", 24.19, 24.19),
    ("GOOGLE ONE STORAGE",       -1, "suscripcion",  2.99,  2.99),
    ("MICROSOFT 365 {n:8d}",     -1, "suscripcion",  9.99,  9.99),
]

SALUD = [
    ("FARMACIA {n:04d}",         -1, "salud",  6, 35),
    ("CLINICA DENTAL {n:04d}",   -1, "salud", 40, 180),
    ("SANITAS SEGUROS {mes}",    -1, "salud", 40,  65),
    ("GIMNASIO {n:04d}",         -1, "salud", 25,  45),
]

CIUDADES = ["MADRID", "BCN", "VLNC", "SEVLL", "BILBAO"]

def fmt_concepto(template: str, fecha: date) -> str:
    return template.format(
        n=random.randint(0, 9999),
        mes=fecha.strftime("%m/%Y"),
        ciudad=random.choice(CIUDADES),
    )

def generar_transacciones() -> pd.DataFrame:
    rows = []

    current = FECHA_INICIO
    while current <= FECHA_FIN:
        year, month = current.year, current.month

        if month == 12:
            ultimo_dia = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            ultimo_dia = date(year, month + 1, 1) - timedelta(days=1)

        def rand_date(from_day=1, to_day=None):
            to_day = to_day or ultimo_dia.day
            day = random.randint(from_day, to_day)
            return date(year, month, min(day, ultimo_dia.day))

        es_paga_extra = month in (6, 12)
        nomina_base = round(random.gauss(2100, 40), 2)
        if es_paga_extra:
            nomina_base += round(random.gauss(1800, 60), 2)  
        rows.append({
            "Fecha": date(year, month, min(28, ultimo_dia.day)),
            "Concepto_Bancario": f"TRANSFERENCIA NOMINA EMPRESA SL {month:02d}/{year}",
            "Importe": nomina_base,
        })

        if random.random() < 0.20:
            rows.append({
                "Fecha": rand_date(),
                "Concepto_Bancario": f"BIZUM RECIBIDO {random.randint(10000000, 99999999)}",
                "Importe": round(random.uniform(15, 120), 2),
            })

        alquiler = round(random.gauss(750, 8), 2)
        rows.append({
            "Fecha": rand_date(1, 5),
            "Concepto_Bancario": f"RECIBO ALQUILER {month:02d}/{year} INMOBILIARIA",
            "Importe": -alquiler,
        })

        for _ in range(random.randint(3, 5)):
            tpl = random.choice(SUPERMERCADOS)
            rows.append({
                "Fecha": rand_date(),
                "Concepto_Bancario": fmt_concepto(tpl[0], current),
                "Importe": -round(random.uniform(tpl[3], tpl[4]), 2),
            })

        for _ in range(random.randint(2, 5)):
            tpl = random.choice(RESTAURANTES)
            rows.append({
                "Fecha": rand_date(),
                "Concepto_Bancario": fmt_concepto(tpl[0], current),
                "Importe": -round(random.uniform(tpl[3], tpl[4]), 2),
            })

        for _ in range(random.randint(1, 3)):
            tpl = random.choice(OCIO)
            rows.append({
                "Fecha": rand_date(),
                "Concepto_Bancario": fmt_concepto(tpl[0], current),
                "Importe": -round(random.uniform(tpl[3], tpl[4]), 2),
            })

        for _ in range(random.randint(1, 3)):
            tpl = random.choice(TRANSPORTE)
            rows.append({
                "Fecha": rand_date(),
                "Concepto_Bancario": fmt_concepto(tpl[0], current),
                "Importe": -round(random.uniform(tpl[3], tpl[4]), 2),
            })

        for tpl in random.sample(SUMINISTROS, random.randint(2, 3)):
            rows.append({
                "Fecha": rand_date(1, 10),
                "Concepto_Bancario": fmt_concepto(tpl[0], current),
                "Importe": -round(random.uniform(tpl[3], tpl[4]), 2),
            })

        for tpl in random.sample(SUSCRIPCIONES, random.randint(2, 4)):
            rows.append({
                "Fecha": rand_date(),
                "Concepto_Bancario": fmt_concepto(tpl[0], current),
                "Importe": -tpl[3],
            })

        for _ in range(random.randint(0, 2)):
            tpl = random.choice(SALUD)
            rows.append({
                "Fecha": rand_date(),
                "Concepto_Bancario": fmt_concepto(tpl[0], current),
                "Importe": -round(random.uniform(tpl[3], tpl[4]), 2),
            })

        if random.random() < 0.15:
            conceptos_grandes = [
                "EL CORTE INGLES {n:04d}",
                "IKEA SPAIN {n:04d}",
                "VUELING AIRLINES {n:8d}",
                "BOOKING.COM {n:8d}",
                "MEDIAMARKT {n:04d}",
            ]
            rows.append({
                "Fecha": rand_date(),
                "Concepto_Bancario": fmt_concepto(random.choice(conceptos_grandes), current),
                "Importe": -round(random.uniform(80, 350), 2),
            })

        if month == 12:
            current = date(year + 1, 1, 1)
        else:
            current = date(year, month + 1, 1)

    df = pd.DataFrame(rows)
    df["Fecha"] = pd.to_datetime(df["Fecha"])
    df = df.sort_values("Fecha").reset_index(drop=True)
    return df


if __name__ == "__main__":
    df = generar_transacciones()
    df.to_csv(OUTPUT_PATH, index=False)

    n_filas     = len(df)
    n_meses     = df["Fecha"].dt.to_period("M").nunique()
    total_ingr  = df[df["Importe"] > 0]["Importe"].sum()
    total_gasto = df[df["Importe"] < 0]["Importe"].sum()
    balance     = total_ingr + total_gasto

    print(f"\n CSV generado en: {OUTPUT_PATH}")
    print(f"   Filas:     {n_filas}")
    print(f"   Meses:     {n_meses}")
    print(f"   Ingresos:  {total_ingr:,.2f} €")
    print(f"   Gastos:    {total_gasto:,.2f} €")
    print(f"   Balance:   {balance:,.2f} €  (~{balance/n_meses:,.0f} €/mes de ahorro)")
    print("\nPrimeras filas:")
    print(df.head(10).to_string(index=False))