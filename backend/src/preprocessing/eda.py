import pandas as pd
import numpy as np
import warnings
from statsmodels.tsa.stattools import adfuller, kpss, zivot_andrews
from statsmodels.tsa.seasonal import STL
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tools.sm_exceptions import InterpolationWarning

from src.utils.config import ANALYSIS_SETTINGS, MIN_DENSITY_PCT, MIN_WEEKS_FOR_EDA

warnings.filterwarnings("ignore", category=UserWarning, module="statsmodels")
warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", category=InterpolationWarning)

class SeriesAnalyzer:
    def __init__(self, series: pd.Series):
        self.series = series.astype(float)

    def _check_density(self) -> dict:
        if self.series.empty:
            return {"is_dense": False, "density_pct": 0.0, "total_weeks": 0}
        
        total_weeks = len(self.series)
        dense_weeks = int((self.series > 0).sum())
        density_pct = float(dense_weeks / total_weeks)
        
        return {
            "is_dense": bool(density_pct >= MIN_DENSITY_PCT),
            "density_pct": round(density_pct, 4),
            "total_weeks": total_weeks
        }

    def _basic_eda(self) -> dict:
        s = self.series
        s_activa = s[s > 0] if (s > 0).any() else s

        return {
            "tipo_analisis": "BASICO",
            "metricas": {
                "mediana": round(float(s_activa.median()), 2),
                "media": round(float(s_activa.mean()), 2),
                "desviacion_estandar": round(float(s_activa.std()), 2) if len(s_activa) > 1 else 0.0,
                "minimo": round(float(s_activa.min()), 2),
                "maximo": round(float(s_activa.max()), 2),
                "coeficiente_variacion": round(float(s_activa.std() / s_activa.mean()), 2) if s_activa.mean() != 0 else 0.0
            }
        }

    def _complex_eda(self) -> dict:
        s = self.series
        resultados = {"tipo_analisis": "COMPLEJO"}

        # 1. Tests de Estacionariedad
        resultados_est = {}
        try:
            adf_stat, adf_p, _, _, _, _ = adfuller(s, autolag='AIC')
            kpss_stat, kpss_p, _, _ = kpss(s, regression='c', nlags="auto")
            resultados_est["adf_pvalue"] = round(float(adf_p), 4)
            resultados_est["kpss_pvalue"] = round(float(kpss_p), 4)
            resultados_est["es_estacionaria"] = bool(adf_p < 0.05 and kpss_p > 0.05)
        except Exception as e:
            resultados_est["error_basico"] = str(e)
            resultados_est["es_estacionaria"] = False

        try:
            za_stat, za_p, _, _, _ = zivot_andrews(s)
            za_p_val = float(za_p)
            resultados_est["zivot_andrews_pvalue"] = round(za_p_val, 4)
            # Detectamos shock si el p-valor es significativo (rechaza raíz unitaria con quiebre)
            shock_detectado = bool(za_p_val < 0.05)
            resultados_est["shock_estructural"] = shock_detectado
        except Exception:
            resultados_est["zivot_andrews_pvalue"] = None 
            resultados_est["shock_estructural"] = False

        resultados["estacionariedad"] = resultados_est

        # 2. Descomposición STL Robusta
        try:
            periodo = ANALYSIS_SETTINGS.get("stl_period", 4)
            umbral_p = 0.05
            
            stl = STL(s, period=periodo, robust=True).fit()
            T = stl.trend
            S = stl.seasonal
            R = stl.resid
            
            lb_test = acorr_ljungbox(R, lags=[periodo], return_df=True)
            lb_pvalue = float(lb_test['lb_pvalue'].iloc[0])
            
            var_R = np.var(R)
            var_TR = np.var(T + R)
            var_SR = np.var(S + R)
            var_Y = np.var(s)
            
            f_tendencia = max(0, 1 - var_R / var_TR) if var_TR > 0 else 0
            f_estacionalidad = max(0, 1 - var_R / var_SR) if var_SR > 0 else 0
            f_residuo = var_R / var_Y if var_Y > 0 else 0
            
            # --- EVALUACIÓN DE ESTABILIDAD DEL PATRÓN ---
            es_fiable_ljung_box = bool(lb_pvalue > umbral_p)
            exceso_ruido = bool(f_residuo > 0.30)
            tiene_shock = resultados_est.get("shock_estructural", False)
            
            # Cálculo de un sub-score interno (0 a 1) para la pureza del patrón
            score_patron = max(0.0, 1.0 - f_residuo)
            
            if not es_fiable_ljung_box:
                score_patron *= 0.5 # Fuerte penalización si hay autocorrelación en residuos
                
            if tiene_shock:
                score_patron *= 0.7 # Penalización adicional del 30% por inestabilidad/cambio estructural

            resultados["descomposicion_stl"] = {
                "fuerza_tendencia": round(float(f_tendencia), 4),
                "fuerza_estacionalidad": round(float(f_estacionalidad), 4),
                "fuerza_residuo": round(float(f_residuo), 4),
                "ljung_box_pvalue": round(lb_pvalue, 4),
                "estabilidad_patron": {
                    "es_estable": bool(es_fiable_ljung_box and not exceso_ruido and not tiene_shock),
                    "score": round(float(score_patron), 4),
                    "flags": {
                        "exceso_ruido": exceso_ruido,
                        "falla_ljung_box": not es_fiable_ljung_box,
                        "shock_estructural": tiene_shock
                    }
                }
            }
        except Exception as e:
            resultados["descomposicion_stl"] = {"error": str(e)}

        return resultados

    def run_analysis(self) -> dict:
        density_info = self._check_density()
        
        if not density_info["is_dense"]:
            return {
                "valido_para_prediccion": False,
                "motivo": f"Serie poco densa. Actividad en {density_info['density_pct']*100:.1f}% de las semanas.",
                "datos_serie": density_info,
                "analisis": None
            }

        total_semanas = density_info["total_weeks"]
        
        techo_fiabilidad = 1.0 if total_semanas >= MIN_WEEKS_FOR_EDA else 0.7

        payload = {
            "valido_para_prediccion": True,
            "datos_serie": density_info,
            "gobernanza_incertidumbre": {
                "techo_fiabilidad_maxima": techo_fiabilidad,
                "penalizacion_por_historial_corto": bool(total_semanas < 24)
            }
        }

        if total_semanas >= MIN_WEEKS_FOR_EDA:
            payload["analisis"] = self._complex_eda()
        else:
            payload["analisis"] = self._basic_eda()

        return payload