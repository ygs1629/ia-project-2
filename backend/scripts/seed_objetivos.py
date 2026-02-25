import sqlite3
from pathlib import Path
from datetime import date, timedelta

DB_PATH = Path("./backend/data/finanzas.db")

def seed():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    hoy = date.today()
    objetivos_ejemplo = [
        ("Vacaciones de verano", 2500.0, 1200.0, (hoy + timedelta(days=120)).isoformat())
    ]

    cursor.executemany("""
        INSERT OR REPLACE INTO objetivos (nombre, importe_objetivo, importe_actual, fecha_limite)
        VALUES (?, ?, ?, ?)
    """, objetivos_ejemplo)

    conn.commit()
    conn.close()
    print(f"Se han cargado {len(objetivos_ejemplo)} objetivos en {DB_PATH}")

if __name__ == "__main__":
    seed()