import pandas as pd
import numpy as np
import re
from src.utils.config import MODEL_SETTINGS

class DataQualityEngine:
    def __init__(self, df_transacciones: pd.DataFrame):
        self.df = df_transacciones.copy()
        if not pd.api.types.is_datetime64_any_dtype(self.df['Fecha']):
            self.df['Fecha'] = pd.to_datetime(self.df['Fecha'])
        self.df = self.df.sort_values('Fecha')


    def treat_outliers(self) -> pd.DataFrame:
        percentile = MODEL_SETTINGS.get("outlier_percentile", 0.98)
        max_cv_threshold = 0.15 
        
        # 1. Preparación inicial
        self.df['Importe_Model'] = self.df['Importe']
        mask_gastos = self.df['Importe'] < 0
        
        if not mask_gastos.any():
                return self.df

        # 2. Limpieza de conceptos para agrupar
        # Creamos una serie temporal para el análisis de varianza
        temp_df = self.df[mask_gastos].copy()
        temp_df['Concepto_Limpio'] = temp_df['Concepto'].str.replace(r'[0-9/]', '', regex=True).str.strip()
        temp_df['Importe_Abs'] = temp_df['Importe'].abs()

        # 3. Identificación de recuerrencia por conteo
        stats = temp_df.groupby('Concepto_Limpio')['Importe_Abs'].agg(['count', 'mean', 'std']).fillna(0)
        
        # Calculamos el CV
        stats['cv'] = stats['std'] / stats['mean']
        
        # Gasto estructural >=3 veces y cv <=15%
        conceptos_estructurales = stats[
                (stats['count'] >= 3) & 
                (stats['cv'] <= max_cv_threshold)].index

        mask_es_estructural = temp_df['Concepto_Limpio'].isin(conceptos_estructurales)
        
        # Los gastos para calcular el límite de winsorización son:
        # Todos los que NO son estructurales
        gastos_para_limite = temp_df.loc[~mask_es_estructural, 'Importe_Abs']
        
        if gastos_para_limite.empty:
                upper_limit = temp_df['Importe_Abs'].max()
        else:
                upper_limit = gastos_para_limite.quantile(percentile)

        # 5. Aplicación de la Winsorización
        conceptos_a_winsorizar = temp_df.loc[
                (~mask_es_estructural) & (temp_df['Importe_Abs'] > upper_limit), 
                'Concepto_Limpio'].unique()

        mask_final_winsorizar = (
                (self.df['Importe'] < 0) & 
                (self.df['Concepto'].str.replace(r'[0-9/]', '', regex=True).str.strip().isin(conceptos_a_winsorizar)) &
                (self.df['Importe'].abs() > upper_limit))
        
        self.df.loc[mask_final_winsorizar, 'Importe_Model'] = -upper_limit
        
        return self.df

    def get_resampled_series(self) -> pd.Series:
        """
        Agrupación semanal y relleno con ceros
        """
        if 'Importe_Model' not in self.df.columns:
            self.treat_outliers()
            
        df_gastos = self.df[self.df['Importe'] < 0].copy()
        freq = MODEL_SETTINGS.get("resample_freq", "W-MON")
        
        series = df_gastos.set_index('Fecha')['Importe_Model'].abs().resample(freq).sum().fillna(0)
        
        return series
        
