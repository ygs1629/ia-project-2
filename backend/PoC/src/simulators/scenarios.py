# src/simulators/montecarlo.py
import numpy as np

class MonteCarloSimulator:
    def __init__(self, resultados_prediccion: dict, meta_ahorro: float, ingreso_semanal: float, iteraciones: int = 10000):
        self.predicciones = resultados_prediccion
        self.meta = meta_ahorro
        self.ingreso = ingreso_semanal
        self.iteraciones = iteraciones
        
        # Z-score para un intervalo de confianza del 80% (1.28)
        self.z_score_80 = 1.28 

    def _calcular_desviacion_tipica(self, media: list, limite_inf: list, limite_sup: list) -> np.ndarray:
        """
        Extrae la desviación típica implícita de los intervalos del modelo.
        Si un modelo no devuelve límites (ej. ETS básico), se asume una desviación conservadora del 15%.
        """
        sigma_list = []
        for i in range(len(media)):
            mu = media[i]
            if limite_inf and limite_sup and limite_inf[i] is not None and limite_sup[i] is not None:
                # Calculamos sigma a partir de la amplitud del intervalo del 80%
                rango = limite_sup[i] - limite_inf[i]
                sigma = rango / (2 * self.z_score_80)
            else:
                # Fallback: Si no hay límites, asumimos un 15% de varianza sobre la media
                sigma = mu * 0.15 
            
            sigma_list.append(sigma)
            
        return np.array(sigma_list)

    def ejecutar_simulacion(self) -> dict:
        """
        Cruza los ingresos fijos con el gasto estocástico para obtener las probabilidades de éxito.
        """
        # 1. Extraer los datos crudos del JSON de predicción
        medias = self.predicciones.get("prediccion_puntual", [])
        limites_inf = self.predicciones.get("limite_inferior", [])
        limites_sup = self.predicciones.get("limite_superior", [])
        
        if not medias:
            return {"error": "No hay datos de predicción para simular."}

        num_semanas = len(medias)
        medias_np = np.array(medias)
        sigmas_np = self._calcular_desviacion_tipica(medias, limites_inf, limites_sup)

        # 2. Generar matriz de simulación de gastos (Iteraciones x Semanas)
        # Usamos una distribución normal parametrizada con la Media y Sigma extraídas
        gastos_simulados = np.random.normal(loc=medias_np, scale=sigmas_np, size=(self.iteraciones, num_semanas))
        
        # Filtro de seguridad: los gastos no pueden ser negativos
        gastos_simulados = np.maximum(0, gastos_simulados)

        # 3. Calcular el Ahorro Neto (Ingresos - Gastos)
        # Como asumimos ingreso fijo, se lo restamos al gasto simulado de cada semana
        ahorro_semanal_simulado = self.ingreso - gastos_simulados

        # 4. Calcular el Ahorro Acumulado (Suma acumulada por filas)
        ahorro_acumulado = np.cumsum(ahorro_semanal_simulado, axis=1)

        # 5. Evaluar el éxito (¿Supera la meta en la última semana?)
        ahorro_final_por_escenario = ahorro_acumulado[:, -1]
        casos_exito = np.sum(ahorro_final_por_escenario >= self.meta)
        probabilidad_exito = (casos_exito / self.iteraciones) * 100

        # 6. Calcular métricas extra de negocio (Percentiles)
        ahorro_pesimista_p10 = np.percentile(ahorro_final_por_escenario, 10)
        ahorro_esperado_p50 = np.percentile(ahorro_final_por_escenario, 50)
        ahorro_optimista_p90 = np.percentile(ahorro_final_por_escenario, 90)

        # 7. Empaquetar el resultado
        return {
            "meta_objetivo_euros": self.meta,
            "ingreso_fijo_asumido": self.ingreso,
            "iteraciones_montecarlo": self.iteraciones,
            "probabilidad_exito_pct": round(probabilidad_exito, 2),
            "proyeccion_final": {
                "escenario_pesimista": round(float(ahorro_pesimista_p10), 2),
                "escenario_central": round(float(ahorro_esperado_p50), 2),
                "escenario_optimista": round(float(ahorro_optimista_p90), 2)
            }
        }