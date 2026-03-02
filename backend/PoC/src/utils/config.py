# src/utils/config.py
import os
from pathlib import Path
from dotenv import load_dotenv
import logging

# from dotenv import load_dotenv, find_dotenv
# import logging

# env_path = find_dotenv(usecwd=True)
# if env_path:
#     load_dotenv(env_path)
#     logging.info(f"Archivo .env cargado desde: {env_path}")
# else:
#     logging.warning("⚠️ No se encontró el archivo .env")

# 1. Obtenemos el directorio donde se está ejecutando el script (suele ser la raíz del proyecto)
# En lugar de usar relative parents que se rompen fácil, buscamos hacia arriba hasta encontrar el .env
current_dir = Path(__file__).resolve().parent

# Buscamos el .env subiendo niveles hasta llegar a la raíz
env_path = None
while current_dir != current_dir.parent:
    potential_env = current_dir / ".env"
    if potential_env.exists():
        env_path = potential_env
        break
    current_dir = current_dir.parent

# Si lo encuentra, lo carga. Si no, avisa.
if env_path:
    load_dotenv(dotenv_path=env_path)
    logging.info(f"Archivo .env cargado desde: {env_path}")
else:
    logging.warning("⚠️ No se encontró el archivo .env en el árbol de directorios.")

# --- RUTAS ---
# Ahora definimos BASE_DIR de forma segura basada en donde encontramos el .env
BASE_DIR = env_path.parent if env_path else Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "finanzas.db"

# --- API KEYS ---
# Usamos un valor por defecto vacío para evitar errores si la key no está
TIMESGPT_TOKEN = os.getenv("TIMESGPT_TOKEN", "") 

# --- REGLAS DE GOBERNANZA ---
MIN_WEEKS_FOR_EDA = 24
MIN_DENSITY_PCT = 0.80  

# --- PREPROCESADO ---
MODEL_SETTINGS = {
    "outlier_percentile": 0.98,
    "resample_freq": "W-MON"
}

ANALYSIS_SETTINGS = {
    "stl_period": 4,         
    "stl_seasonal_window": 7
}

MODEL_ROUTING_WEEKS = {
    "min_ets": 12,       
    "min_prophet": 24,   
    "min_timesgpt": 52 
}

# --- HORIZONTES DE PREDICCIÓN SEGÚN MODELO (En semanas) ---
FORECAST_HORIZONS = {
    "ets": 4,             # 1 mes
    "prophet_corto": 12,  # 3 meses
    "prophet_largo": 24,  # 6 meses
    "timesgpt": 52        # 12 meses
}

# --- PARÁMETROS DE PREDICCIÓN ADICIONALES ---
FORECAST_SETTINGS = {
    "ets_seasonal_periods": 4,          # Ciclo mensual para el suavizado
    "prophet_intervalo_confianza": 0.80 # 80% de confianza para bandas superior/inferior
}
