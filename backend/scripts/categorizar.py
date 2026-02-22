"""
categorizar.py — Script de uso único.
Lee data/transacciones_sucias.csv, clasifica cada Concepto_Bancario
con la API de Gemini (en batches de 20) y puebla finanzas.db.
"""

import os
import json
import sqlite3
import textwrap
from pathlib import Path

import pandas as pd
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

BASE_DIR  = Path(__file__).parent.parent 
CSV_PATH  = BASE_DIR / "data" / "transacciones_sucias.csv"
DB_PATH   = BASE_DIR / "data" / "finanzas.db"

CATEGORIAS = [
    "Vivienda",
    "Supermercado",
    "Restaurantes",
    "Ocio",
    "Transporte",
    "Suministros",
    "Salud",
    "Suscripciones",
    "Ingresos",
    "Otros",
]

SYSTEM_PROMPT = textwrap.dedent(f"""
    Eres un clasificador bancario. Tu única tarea es asignar cada concepto bancario
    a UNA de estas categorías exactas (respeta mayúsculas/minúsculas):

    {json.dumps(CATEGORIAS, ensure_ascii=False)}

    Reglas:
    - Los conceptos con importe positivo que parezcan nóminas, transferencias recibidas
      o ingresos → categoría "Ingresos".
    - Alquiler, hipoteca, comunidad de vecinos → "Vivienda".
    - Supermercados (Mercadona, Carrefour, Lidl, Aldi…) → "Supermercado".
    - Bares, restaurantes, delivery (Glovo, Uber Eats, Just Eat) → "Restaurantes".
    - Cine, juegos, entretenimiento, Amazon compras discrecionales → "Ocio".
    - Gasolineras, transporte público, taxis, peajes → "Transporte".
    - Luz, gas, agua, teléfono, internet → "Suministros".
    - Farmacias, médicos, seguros de salud, gimnasio → "Salud".
    - Netflix, Spotify, Adobe, Microsoft 365, subscripciones recurrentes → "Suscripciones".
    - Si no encaja en ninguna categoría → "Otros".

    Recibirás un array JSON con objetos {{\"id\": N, \"concepto\": \"...\"}}.
    Responde SOLO con un array JSON de objetos {{\"id\": N, \"categoria\": \"...\"}}.
    Sin texto adicional, sin bloques de código, solo el JSON puro.
""").strip()

def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS transacciones (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha     TEXT    NOT NULL,
            concepto  TEXT    NOT NULL,
            importe   REAL    NOT NULL,
            categoria TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS objetivos (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre           TEXT    NOT NULL,
            importe_objetivo REAL    NOT NULL,
            importe_actual   REAL    NOT NULL DEFAULT 0,
            fecha_limite     DATE    NOT NULL
        );
    """)
    conn.commit()
    print("Tablas creadas o ya existían.")

def clasificar_batch(
    llm: ChatGoogleGenerativeAI,
    batch: list[dict],          
    intento: int = 0,
) -> dict[int, str]:
    """Llama al LLM y devuelve {id: categoria}."""
    payload = json.dumps(batch, ensure_ascii=False)
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=payload),
    ]

    response = llm.invoke(messages)
    raw = response.content.strip()

    # Limpieza defensiva: quitar ```json ... ```
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        resultados = json.loads(raw)
    except json.JSONDecodeError as e:
        if intento < 2:
            print(f"JSON inválido en intento {intento + 1}, reintentando...")
            return clasificar_batch(llm, batch, intento + 1)
        raise ValueError(f"No se pudo parsear la respuesta del LLM: {e}\nRaw: {raw[:300]}")

    # Normalizar: asegurarse de que la categoría es válida
    resultado_map = {}
    for item in resultados:
        cat = item.get("categoria", "Otros")
        if cat not in CATEGORIAS:
            cat = "Otros"
        resultado_map[item["id"]] = cat

    return resultado_map

def main() -> None:
    api_key = os.environ.get("GOOGLE_API_KEY", "").strip()
    if not api_key:
        raise EnvironmentError(
            "GOOGLE_API_KEY no encontrada. Ejecuta:\n"
            "  export GOOGLE_API_KEY=AIza..."
        )

    # Cargar CSV
    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"No se encontró el CSV en {CSV_PATH}.\n"
            "Ejecuta primero: python scripts/generar_datos.py"
        )

    print(f"Cargando {CSV_PATH}...")
    df = pd.read_csv(CSV_PATH, parse_dates=["Fecha"])
    print(f"{len(df)} transacciones cargadas.")

    # Inicializar SQLite
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    # Preguntar si reemplazar si ya hay datos
    count = conn.execute("SELECT COUNT(*) FROM transacciones").fetchone()[0]
    if count > 0:
        print(f"\nLa tabla 'transacciones' ya tiene {count} filas.")
        respuesta = input("¿Vaciar y reemplazar? [s/N]: ").strip().lower()
        if respuesta == "s":
            conn.execute("DELETE FROM transacciones")
            conn.commit()
            print("Tabla vaciada.")
        else:
            print("Cancelado.")
            conn.close()
            return

    # Inicializar LLM
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0,
        google_api_key=api_key,
    )

    # Preparar items para clasificar
    items = [
        {"id": int(idx), "concepto": row["Concepto_Bancario"]}
        for idx, row in df.iterrows()
    ]

    BATCH_SIZE = 20
    total      = len(items)
    categorias_map: dict[int, str] = {}

    print(f"\n Clasificando {total} conceptos en batches de {BATCH_SIZE}...")
    for start in range(0, total, BATCH_SIZE):
        batch = items[start : start + BATCH_SIZE]
        batch_num = start // BATCH_SIZE + 1
        total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE

        print(f"Batch {batch_num}/{total_batches} ({start + 1}–{min(start + BATCH_SIZE, total)})...", end=" ", flush=True)
        result = clasificar_batch(llm, batch)
        categorias_map.update(result)

    # Insertar en SQLite
    print("\n Insertando en finanzas.db...")
    filas = []
    for idx, row in df.iterrows():
        categoria = categorias_map.get(int(idx), "Otros")
        filas.append((
            row["Fecha"].strftime("%Y-%m-%d"),
            row["Concepto_Bancario"],
            float(row["Importe"]),
            categoria,
        ))

    conn.executemany(
        "INSERT INTO transacciones (fecha, concepto, importe, categoria) VALUES (?, ?, ?, ?)",
        filas,
    )
    conn.commit()

    # Resumen
    total_insertadas = conn.execute("SELECT COUNT(*) FROM transacciones").fetchone()[0]
    print(f"\n{total_insertadas} transacciones insertadas en {DB_PATH}")

    print("\nDistribución por categoría:")
    for cat, cnt in conn.execute(
        "SELECT categoria, COUNT(*) as n FROM transacciones GROUP BY categoria ORDER BY n DESC"
    ).fetchall():
        print(f"{cat:<15} {cnt:>4} transacciones")

    conn.close()
    print("\nCategorización completada.")


if __name__ == "__main__":
    main()