"""
generar_datos.py — Script de uso único.
Genera 18 meses de transacciones bancarias ficticias y las guarda en:
  data/transacciones_sucias.csv
"""

import pandas as pd
import numpy as np
import random
from datetime import date, timedelta
from pathlib import Path

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

FECHA_FIN   = date.today().replace(day=1) - timedelta(days=1)   # fin = último día del mes anterior
FECHA_INICIO = (FECHA_FIN - timedelta(days=18 * 30)).replace(day=1)

OUTPUT_PATH = Path(__file__).parent.parent / "data" / "transacciones_sucias.csv"
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

SUPERMERCADOS = [
    ("TPV MERCADONA {n:03d}", -1, "supermercado", 40, 130),
    ("COMPRA CARREFOUR {n:03d}", -1, "supermercado", 30, 110),
    ("LIDL ES {n:04d}", -1, "supermercado", 20, 80),
    ("ALDI SUPERMERCADOS", -1, "supermercado", 20, 75),
    ("CONSUM COOP {n:03d}", -1, "supermercado", 25, 90),
    ("AMAZON FRESH ES", -1, "supermercado", 30, 100),
]

RESTAURANTES = [
    ("TPV BAR RESTAURANTE {n:04d}", -1, "restaurante", 8, 45),
    ("GLOVO ES {n:06d}", -1, "restaurante", 12, 40),
    ("UBER EATS *ES {n:5d}", -1, "restaurante", 12, 40),
    ("JUST EAT SPAIN", -1, "restaurante", 10, 35),
    ("MCDONALDS {ciudad}", -1, "restaurante", 6, 20),
    ("STARBUCKS {n:04d} ES", -1, "restaurante", 4, 12),
    ("CAFETERIA {n:04d}", -1, "restaurante", 3, 15),
]

OCIO = [
    ("CINES ODEON {n:03d}", -1, "ocio", 8, 25),
    ("STEAM PURCHASE", -1, "ocio", 5, 60),
    ("TICKETMASTER ES", -1, "ocio", 20, 120),
    ("FNAC SPAIN {n:04d}", -1, "ocio", 15, 80),
    ("PAYPAL *GAMING {n:8d}", -1, "ocio", 5, 50),
    ("AMAZON MARKETPLACE ES", -1, "ocio", 10, 150),
]

TRANSPORTE = [
    ("REPSOL {n:04d}", -1, "transporte", 40, 90),
    ("BP ESTACION {n:04d}", -1, "transporte", 40, 85),
    ("RENFE INTERNET {n:8d}", -1, "transporte", 15, 80),
    ("EMT MADRID RECARGA", -1, "transporte", 10, 20),
    ("CABIFY VIAJE {n:8d}", -1, "transporte", 8, 35),
    ("PARKING {n:04d} ES", -1, "transporte", 3, 25),
    ("AUTOPISTA PEAJE {n:04d}", -1, "transporte", 3, 20),
]

SUMINISTROS = [
    ("RECIBO ENDESA {mes}", -1, "suministros", 55, 130),
    ("RECIBO IBERDROLA {mes}", -1, "suministros", 50, 120),
    ("RECIBO NATURGY GAS {mes}", -1, "suministros", 35, 90),
    ("TELEFONICA MOVISTAR {mes}", -1, "suministros", 30, 70),
    ("ORANGE SPAIN {mes}", -1, "suministros", 20, 60),
    ("RECIBO AGUA CANAL {mes}", -1, "suministros", 20, 60),
]

SUSCRIPCIONES = [
    ("NETFLIX.COM {n:8d}", -1, "suscripcion", 12.99, 12.99),
    ("SPOTIFY AB {n:8d}", -1, "suscripcion", 9.99, 9.99),
    ("AMAZON PRIME ES", -1, "suscripcion", 4.99, 4.99),
    ("HBO MAX ES {n:6d}", -1, "suscripcion", 8.99, 8.99),
    ("DISNEY PLUS ES", -1, "suscripcion", 8.99, 8.99),
    ("ADOBE INC {n:8d}", -1, "suscripcion", 24.19, 24.19),
    ("GOOGLE ONE STORAGE", -1, "suscripcion", 2.99, 2.99),
    ("MICROSOFT 365 {n:8d}", -1, "suscripcion", 9.99, 9.99),
]

SALUD = [
    ("FARMACIA {n:04d}", -1, "salud", 8, 60),
    ("CLINICA DENTAL {n:04d}", -1, "salud", 50, 300),
    ("SANITAS SEGUROS {mes}", -1, "salud", 45, 75),
    ("GIMNASIO {n:04d}", -1, "salud", 25, 55),
]

CIUDADES = ["MADRID", "BCN", "VLNC", "SEVLL", "BILBAO"]

def fmt_concepto(template: str, fecha: date) -> str:
    return template.format(
        n=random.randint(0, 9999),
        mes=fecha.strftime("%m/%Y"),
        ciudad=random.choice(CIUDADES),
    )

def importe_fijo(lo, hi):
    """Importe fijo (para suscripciones con lo == hi)."""
    return round(lo, 2)

def importe_variable(lo, hi):
    return round(random.uniform(lo, hi), 2)

def generar_transacciones() -> pd.DataFrame:
    rows = []

    current = FECHA_INICIO
    while current <= FECHA_FIN:
        year, month = current.year, current.month
        # Último día del mes
        if month == 12:
            ultimo_dia = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            ultimo_dia = date(year, month + 1, 1) - timedelta(days=1)

        def rand_date(from_day=1, to_day=None):
            to_day = to_day or ultimo_dia.day
            day = random.randint(from_day, to_day)
            return date(year, month, min(day, ultimo_dia.day))

        # Nómina fija (~1800€) entre día 28 y último día
        nomina = round(random.gauss(1800, 30), 2)
        rows.append({
            "Fecha": date(year, month, min(28, ultimo_dia.day)),
            "Concepto_Bancario": f"TRANSFERENCIA NOMINA EMPRESA SL {month:02d}/{year}",
            "Importe": nomina,
        })

        # Ingreso extra esporádico (~25% probabilidad)
        if random.random() < 0.25:
            rows.append({
                "Fecha": rand_date(),
                "Concepto_Bancario": f"BIZUM RECIBIDO {random.randint(10000000, 99999999)}",
                "Importe": round(random.uniform(20, 300), 2),
            })

        # Vivienda (alquiler fijo el día 1-3) 
        alquiler = round(random.gauss(750, 10), 2)
        rows.append({
            "Fecha": rand_date(1, 5),
            "Concepto_Bancario": f"RECIBO ALQUILER {month:02d}/{year} INMOBILIARIA",
            "Importe": -alquiler,
        })

        # Supermercados (4-8 visitas/mes) 
        for _ in range(random.randint(4, 8)):
            tpl = random.choice(SUPERMERCADOS)
            rows.append({
                "Fecha": rand_date(),
                "Concepto_Bancario": fmt_concepto(tpl[0], current),
                "Importe": -importe_variable(tpl[3], tpl[4]),
            })

        # Restaurantes (3-8 salidas/mes) 
        for _ in range(random.randint(3, 8)):
            tpl = random.choice(RESTAURANTES)
            rows.append({
                "Fecha": rand_date(),
                "Concepto_Bancario": fmt_concepto(tpl[0], current),
                "Importe": -importe_variable(tpl[3], tpl[4]),
            })

        # Ocio (1-4 compras/mes) 
        for _ in range(random.randint(1, 4)):
            tpl = random.choice(OCIO)
            rows.append({
                "Fecha": rand_date(),
                "Concepto_Bancario": fmt_concepto(tpl[0], current),
                "Importe": -importe_variable(tpl[3], tpl[4]),
            })

        # Transporte (2-5 veces/mes) 
        for _ in range(random.randint(2, 5)):
            tpl = random.choice(TRANSPORTE)
            rows.append({
                "Fecha": rand_date(),
                "Concepto_Bancario": fmt_concepto(tpl[0], current),
                "Importe": -importe_variable(tpl[3], tpl[4]),
            })

        # Suministros (facturas mensuales)
        for tpl in random.sample(SUMINISTROS, random.randint(2, 4)):
            rows.append({
                "Fecha": rand_date(1, 10),
                "Concepto_Bancario": fmt_concepto(tpl[0], current),
                "Importe": -importe_variable(tpl[3], tpl[4]),
            })

        # Suscripciones (renovaciones mensuales) 
        for tpl in random.sample(SUSCRIPCIONES, random.randint(3, 6)):
            rows.append({
                "Fecha": rand_date(),
                "Concepto_Bancario": fmt_concepto(tpl[0], current),
                "Importe": -tpl[3],   # importe fijo
            })

        # Salud (0-2 veces/mes) 
        for _ in range(random.randint(0, 2)):
            tpl = random.choice(SALUD)
            rows.append({
                "Fecha": rand_date(),
                "Concepto_Bancario": fmt_concepto(tpl[0], current),
                "Importe": -importe_variable(tpl[3], tpl[4]),
            })

        # Gasto puntual grande (~20% prob/mes)
        if random.random() < 0.20:
            conceptos_grandes = [
                "AMAZON MARKETPLACE ES",
                "EL CORTE INGLES {n:04d}",
                "IKEA SPAIN {n:04d}",
                "VUELING AIRLINES {n:8d}",
                "BOOKING.COM {n:8d}",
                "MEDIAMARKT {n:04d}",
            ]
            rows.append({
                "Fecha": rand_date(),
                "Concepto_Bancario": fmt_concepto(random.choice(conceptos_grandes), current),
                "Importe": -round(random.uniform(150, 600), 2),
            })

        # Avanzar al mes siguiente
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

    print(f"\n CSV generado en: {OUTPUT_PATH}")
    print(f"   Filas:     {n_filas}")
    print(f"   Meses:     {n_meses}")
    print(f"   Ingresos:  {total_ingr:,.2f} €")
    print(f"   Gastos:    {total_gasto:,.2f} €")
    print(f"   Balance:   {(total_ingr + total_gasto):,.2f} €")
    print("\nPrimeras filas:")
    print(df.head(10).to_string(index=False))