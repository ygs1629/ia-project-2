# src/models/transformers.py
import pandas as pd
import numpy as np
import logging
from nixtla import NixtlaClient

from src.utils.config import TIMESGPT_TOKEN, FORECAST_SETTINGS, FORECAST_HORIZONS
from src.controllers.selection import TimeForecaster

class TransformerModel:
    """
    Cliente API para Inferencia Zero-Shot en la Nube usando TimeGPT de Nixtla.
    Con Fallback automático a Prophet (Largo Plazo) en caso de error.
    """
    
    def __init__(self, series: pd.Series, eda_payload: dict = None):
        self.series = series
        self.eda_payload = eda_payload or {}
        # Asignamos el horizonte de 52 semanas mapeado en config
        self.horizonte = FORECAST_HORIZONS.get("timegpt", 52)
        
        # Inicializamos el cliente de Nixtla con el token
        self.nixtla_client = None
        if TIMESGPT_TOKEN:
            try:
                self.nixtla_client = NixtlaClient(api_key=TIMESGPT_TOKEN)
            except Exception as e:
                logging.error(f"Error al inicializar NixtlaClient: {e}")
        else:
            logging.warning("No se ha configurado TIMESGPT_TOKEN en el entorno.")

    def _calculate_final_score(self, estabilidad_modelo: float) -> dict:
        """Fusiona la certidumbre del EDA con la dispersión de TimeGPT."""
        gobernanza = self.eda_payload.get("gobernanza_incertidumbre", {})
        techo = gobernanza.get("techo_fiabilidad_maxima", 1.0)
        
        analisis = self.eda_payload.get("analisis", {})
        tipo_analisis = analisis.get("tipo_analisis", "COMPLEJO")
        
        if tipo_analisis == "COMPLEJO":
            score_patron = analisis.get("descomposicion_stl", {}).get("estabilidad_patron", {}).get("score", 0.5)
        else:
            score_patron = 0.5 

        # Fusión (60% Datos, 40% IA)
        score_base = (score_patron * 0.6) + (estabilidad_modelo * 0.4)
        score_final = min(score_base, techo)
        
        if score_final >= 0.80: nivel = "ALTA"
        elif score_final >= 0.60: nivel = "MEDIA"
        else: nivel = "BAJA"

        return {
            "score_final": round(float(score_final), 4),
            "nivel": nivel,
            "desglose": {
                "score_patron_eda": round(float(score_patron), 4),
                "estabilidad_intervalo_modelo": round(float(estabilidad_modelo), 4),
                "techo_aplicado": round(float(techo), 4)
            }
        }

    def _llamar_api(self):
        """Gestiona la petición a TimeGPT usando el NixtlaClient."""
        if not self.nixtla_client:
            return None

        try:
            # TimeGPT espera un DataFrame con columnas estándar: 'ds' (fechas) y 'y' (valores)
            df_in = self.series.reset_index()
            # Aseguramos que la columna de fechas se llame 'ds' y la de valores 'y'
            # (asumiendo que tu pd.Series tiene las fechas en el índice)
            df_in.columns = ['ds', 'y'] 
            
            # Formateamos la fecha a string para evitar problemas de parseo en la API
            df_in['ds'] = df_in['ds'].dt.strftime('%Y-%m-%d')

            # Recuperamos el intervalo de confianza del config y lo convertimos a entero para Nixtla (ej: 0.80 -> 80)
            nivel_confianza = int(FORECAST_SETTINGS.get("prophet_intervalo_confianza", 0.80) * 100)

            # Llamada oficial según la documentación de Nixtla
            fcst_df = self.nixtla_client.forecast(
                df=df_in,
                h=self.horizonte,
                level=[nivel_confianza],
                time_col='ds',
                target_col='y'
            )
            return fcst_df

        except Exception as e:
            logging.error(f"Error durante la inferencia con TimeGPT: {e}")
            return None

    def run_forecast(self) -> dict:
        logging.info("Iniciando inferencia con Transformer (TimeGPT)...")
        fcst_df = self._llamar_api()

        # --- LÓGICA DE FALLBACK (Tolerancia a Fallos) ---
        if fcst_df is None or fcst_df.empty:
            logging.warning("⚠️ Fallo en la API de TimeGPT. Activando FALLBACK a Prophet (Largo Plazo)...")
            # Enrutamos el fallback a prophet_largo para mantener el intento de predicción extendida
            forecaster_fallback = TimeForecaster(self.series, "prophet_largo", eda_payload=self.eda_payload)
            resultado_fallback = forecaster_fallback.run_forecast()
            resultado_fallback["modelo_usado"] = "PROPHET_LARGO (FALLBACK)"
            return resultado_fallback

        # --- PARSEO DEL DATAFRAME DE TIMEGPT ---
        try:
            # Nixtla devuelve columnas: 'ds', 'TimeGPT', 'TimeGPT-lo-XX', 'TimeGPT-hi-XX'
            col_pred = 'TimeGPT'
            
            # Buscamos dinámicamente las columnas de los límites basándonos en los niveles pedidos
            nivel_confianza = int(FORECAST_SETTINGS.get("prophet_intervalo_confianza", 0.80) * 100)
            col_inf = f'TimeGPT-lo-{nivel_confianza}'
            col_sup = f'TimeGPT-hi-{nivel_confianza}'

            valores_crudos = fcst_df[col_pred].values
            inferior_crudo = fcst_df[col_inf].values if col_inf in fcst_df.columns else valores_crudos
            superior_crudo = fcst_df[col_sup].values if col_sup in fcst_df.columns else valores_crudos
            
            # Filtro de seguridad financiera (No-Negatividad)
            valores_puntuales = np.maximum(0, valores_crudos)
            limites_inf = np.maximum(0, inferior_crudo)
            limites_sup = np.maximum(0, superior_crudo)

            # Cálculo de la estabilidad del modelo (Precisión del intervalo)
            anchuras = limites_sup - limites_inf
            anchuras_relativas = anchuras / (valores_puntuales + 1)
            estabilidad_media = np.mean(np.maximum(0.0, 1.0 - anchuras_relativas))
            
            fiabilidad = self._calculate_final_score(estabilidad_modelo=estabilidad_media)
            
            # Extraemos las fechas de la predicción y nos aseguramos de que sean strings
            fechas_futuras = pd.to_datetime(fcst_df['ds']).dt.strftime('%Y-%m-%d').tolist()
            
            return {
                "modelo_usado": "TIMEGPT",
                "fechas": fechas_futuras,
                "prediccion_puntual": [round(float(v), 2) for v in valores_puntuales],
                "limite_inferior": [round(float(v), 2) for v in limites_inf],
                "limite_superior": [round(float(v), 2) for v in limites_sup],
                "fiabilidad": fiabilidad
            }
            
        except Exception as e:
            logging.error(f"Error parseando el DataFrame de TimeGPT: {e}. Activando FALLBACK.")
            forecaster_fallback = TimeForecaster(self.series, "prophet_largo", eda_payload=self.eda_payload)
            resultado_fallback = forecaster_fallback.run_forecast()
            resultado_fallback["modelo_usado"] = "PROPHET_LARGO (FALLBACK PARSEO)"
            return resultado_fallback