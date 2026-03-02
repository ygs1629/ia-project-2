
import pandas as pd
import numpy as np
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from prophet import Prophet
import logging
from src.utils.config import FORECAST_SETTINGS, FORECAST_HORIZONS
logging.getLogger('cmdstanpy').setLevel(logging.WARNING)

class TimeForecaster:
    def __init__(self, series: pd.Series, modelo_asignado: str, eda_payload: dict = None):
        """
        Recibe la serie temporal limpia, el modelo asignado y el EDA
        para calcular la fiabilidad cruzada.
        """
        self.series = series
        self.modelo_asignado = modelo_asignado
        # Extraemos el horizonte dinámicamente según la clave ("ets", "prophet_corto", etc.)
        self.horizonte = FORECAST_HORIZONS.get(modelo_asignado, 12)
        self.eda_payload = eda_payload or {}

    def _calculate_final_score(self, estabilidad_modelo: float) -> dict:
        """
        Fusiona la certidumbre del EDA con la precisión matemática del modelo,
        aplicando los techos de riesgo definidos por negocio.
        """
        gobernanza = self.eda_payload.get("gobernanza_incertidumbre", {})
        techo = gobernanza.get("techo_fiabilidad_maxima", 1.0)
        
        analisis = self.eda_payload.get("analisis", {})
        tipo_analisis = analisis.get("tipo_analisis", "BASICO")
        
        if tipo_analisis == "COMPLEJO":
            score_patron = analisis.get("descomposicion_stl", {}).get("estabilidad_patron", {}).get("score", 0.5)
        else:
            score_patron = 0.5 

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

    def _forecast_ets(self) -> dict:
        """Modelo ETS (Error, Trend, Seasonality)."""
        modelo = ExponentialSmoothing(
            self.series,
            trend="add",
            seasonal="add",
            seasonal_periods=FORECAST_SETTINGS.get("ets_seasonal_periods", 4),
            initialization_method="estimated"
        ).fit()

        prediccion = modelo.forecast(self.horizonte)
        valores_predichos = np.maximum(0, prediccion.values)

        fiabilidad = self._calculate_final_score(estabilidad_modelo=0.5)

        return {
            "modelo_usado": "ETS",
            "fechas": prediccion.index.strftime('%Y-%m-%d').tolist(),
            "prediccion_puntual": [round(float(v), 2) for v in valores_predichos],
            "limite_inferior": None,
            "limite_superior": None,
            "fiabilidad": fiabilidad
        }

    def _forecast_prophet(self) -> dict:
        """Modelo Prophet con MCMC, festivos locales y changepoints agresivos."""
        df_prophet = self.series.reset_index()
        df_prophet.columns = ['ds', 'y']

        

        modelo = Prophet(
            interval_width=FORECAST_SETTINGS.get("prophet_intervalo_confianza", 0.80),
            weekly_seasonality=False,
            daily_seasonality=False,
            yearly_seasonality=False,
            changepoint_prior_scale=0.15, # Aumentado de 0.05 a 0.15 para mayor sensibilidad a cambios de tendencia
            mcmc_samples=50             # Activa inferencia Montecarlo 
        )
        
        # Incorporación nativa del calendario de festivos
        modelo.add_country_holidays(country_name='ES')
        modelo.add_seasonality(name='mensual', period=30.5, fourier_order=5)
        modelo.fit(df_prophet)

        futuro = modelo.make_future_dataframe(periods=self.horizonte, freq='W-MON')
        forecast = modelo.predict(futuro)
        predicciones_futuras = forecast.tail(self.horizonte)

        valores_puntuales = np.maximum(0, predicciones_futuras['yhat'].values)
        limites_inf = np.maximum(0, predicciones_futuras['yhat_lower'].values)
        limites_sup = np.maximum(0, predicciones_futuras['yhat_upper'].values)

        anchuras = limites_sup - limites_inf
        anchuras_relativas = anchuras / (valores_puntuales + 1)
        estabilidades_semanales = np.maximum(0.0, 1.0 - anchuras_relativas)
        estabilidad_media = np.mean(estabilidades_semanales)

        fiabilidad = self._calculate_final_score(estabilidad_modelo=estabilidad_media)

        return {
            "modelo_usado": self.modelo_asignado.upper(),
            "fechas": predicciones_futuras['ds'].dt.strftime('%Y-%m-%d').tolist(),
            "prediccion_puntual": [round(float(v), 2) for v in valores_puntuales],
            "limite_inferior": [round(float(v), 2) for v in limites_inf],
            "limite_superior": [round(float(v), 2) for v in limites_sup],
            "fiabilidad": fiabilidad
        }

    def run_forecast(self) -> dict:
        try:
            if self.modelo_asignado == "ets":
                return self._forecast_ets()
            elif self.modelo_asignado in ["prophet_corto", "prophet_largo"]:
                return self._forecast_prophet()
            else:
                return {"error": f"Modelo '{self.modelo_asignado}' no implementado."}
        except Exception as e:
            return {"error": str(e)}