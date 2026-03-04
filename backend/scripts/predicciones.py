import sqlite3
from datetime import date, timedelta

from utils import DB_PATH  

class GastosPredictor:
    """
    Servicio de predicción ligero para el MVP.
    Utiliza una Media Móvil Simple (SMA) basada en el último mes de transacciones.
    """

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def predecir_proxima_semana(self) -> dict:
        """
        Calcula el gasto acumulado esperado para los próximos 7 días.
        Fórmula: (Total gastado últimos 30 días / 30) * 7
        """
        hoy = date.today()
        hace_un_mes = hoy - timedelta(days=30)
        
        sql = """
            SELECT SUM(importe) as gasto_total
            FROM transacciones
            WHERE fecha >= ? AND fecha <= ? AND importe < 0
        """
        
        with self._get_conn() as conn:
            row = conn.execute(sql, (hace_un_mes.isoformat(), hoy.isoformat())).fetchone()
            
        # valor absoluto del gasto
        gasto_total_mes = abs(row["gasto_total"]) if row["gasto_total"] else 0.0
        
        # media móvil
        gasto_diario_promedio = gasto_total_mes / 30.0
        prediccion_proxima_semana = gasto_diario_promedio * 7.0
        
        return {
            "modelo_usado": "Simple Moving Average (SMA 30 días)",
            "gasto_ultimo_mes": round(gasto_total_mes, 2),
            "prediccion_proxima_semana": round(prediccion_proxima_semana, 2),
            "rango_esperado": {
                "minimo": round(prediccion_proxima_semana * 0.85, 2),  # margen de error del 15%
                "maximo": round(prediccion_proxima_semana * 1.15, 2)
            }
        }

# para probar que funciona en terminal
if __name__ == "__main__":
    predictor = GastosPredictor()
    resultado = predictor.predecir_proxima_semana()
    print("Resultado de la predicción MVP:")
    print(resultado)