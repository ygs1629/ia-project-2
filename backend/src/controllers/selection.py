from src.utils.config import MODEL_ROUTING_WEEKS

# Importamos las clases de inferencia
from src.models.short_mid_term import TimeForecaster
from src.models.long_term import TransformerModel

class ModelRouter:
    def __init__(self, eda_payload: dict):
        """
        Recibe el JSON (diccionario) generado por SeriesAnalyzer.run_analysis()
        """
        self.payload = eda_payload

    def determine_architecture(self) -> dict:
        """
        Evalúa la densidad y la longitud de la serie para asignar el modelo óptimo.
        Devuelve un diccionario con flags.
        """
        # 1. Filtro de Densidad (Gobernanza de Calidad)
        if not self.payload.get("valido_para_prediccion", False):
            return {
                "aplica_prediccion": False,
                "modelo_asignado": None,
                "motivo_rechazo": self.payload.get("motivo", "Rechazado en fase EDA por falta de densidad.")
            }

        datos_serie = self.payload.get("datos_serie", {})
        semanas_totales = datos_serie.get("total_weeks", 0)

        # --- EXTRACCIÓN DE MÉTRICAS DE ESTABILIDAD (ZIVOT-ANDREWS) ---
        analisis = self.payload.get("analisis", {})
        estacionariedad = analisis.get("estacionariedad", {})
        stl = analisis.get("descomposicion_stl", {})
        estabilidad = stl.get("estabilidad_patron", {})
        
        shock_estructural = estacionariedad.get("shock_estructural", False)
        score_patron = estabilidad.get("score", 1.0)

        # 2. Filtro de Longitud Mínima
        min_ets = MODEL_ROUTING_WEEKS.get("min_ets", 12)
        if semanas_totales < min_ets:
            return {
                "aplica_prediccion": False,
                "modelo_asignado": None,
                "motivo_rechazo": f"Serie densa, pero historial insuficiente. {semanas_totales} semanas disponibles (Requerido: >= {min_ets})."
            }

        # 3. Lógica de Fallback por Rotura Estructural
        if shock_estructural:
            modelo = "ets"  # Forzamos modelo reactivo a corto plazo
            msg = f"FALLBACK: Rotura estructural detectada (Score: {score_patron}). Ignorando historial largo por inestabilidad."
            return {
                "aplica_prediccion": True,
                "modelo_asignado": modelo,
                "motivo_rechazo": None,
                "info_ruta": msg,
                "shock_detectado": True
            }

        # 4. Enrutamiento por Tramos (Comportamiento Estándar)
        min_prophet = MODEL_ROUTING_WEEKS.get("min_prophet", 24)
        min_timesgpt = MODEL_ROUTING_WEEKS.get("min_timesgpt", 52)

        if semanas_totales < min_prophet:
            modelo = "ets"
            msg = "Historial corto/medio detectado."
        elif semanas_totales < min_timesgpt:
            modelo = "prophet_largo"  
            msg = "Historial medio/largo detectado. Apto para Prophet."
        else:
            modelo = "timesgpt" 
            msg = "Historial completo (>1 año) detectado. Apto para Zero-Shot."

        return {
            "aplica_prediccion": True,
            "modelo_asignado": modelo,
            "motivo_rechazo": None,
            "info_ruta": f"Asignado {modelo.upper()}: {msg} ({semanas_totales} semanas)",
            "shock_detectado": False
        }

    def get_forecaster(self, series):
        """
        Instancia y devuelve el modelo predictivo correspondiente basándose
        en la decisión de arquitectura.
        """
        routing_info = self.determine_architecture()
        
        if not routing_info["aplica_prediccion"]:
            return None
            
        modelo_asignado = routing_info["modelo_asignado"]
        
        # Si hubo shock, recortamos la serie para que el modelo sea puramente reactivo al post-shock
        if routing_info.get("shock_detectado", False):
            series_input = series.tail(12) if len(series) > 12 else series
        else:
            series_input = series
        
        if modelo_asignado == "timesgpt": 
            return TransformerModel(series_input, eda_payload=self.payload)
        else:
            return TimeForecaster(series_input, modelo_asignado, eda_payload=self.payload)