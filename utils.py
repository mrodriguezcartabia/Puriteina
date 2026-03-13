import numpy as np
from scipy.interpolate import interp1d
from itertools import combinations
import pandas as pd

def procesar_data (df, L_fm):
    df['Delta_pi'] = df['TMP'] - (df['J'] / L_fm)
    # Obtener todos los Delta_pi únicos del dataframe global
    all_delta_pi = np.sort(df['Delta_pi'].unique())
    cb_vals = sorted(df['Cb'].unique())

    df_vacio = pd.DataFrame(columns=['TMP' ,'J', 'Cb', 'Delta_Pi'])

    for cb in cb_vals:
        subset = df[df['Cb'] == cb].sort_values('Delta_pi')
        x = subset['Delta_pi'].values
        y = subset['J'].values
        z = subset['TMP'].values

        # Crear la función de interpolación
        f = interp1d(x, y, kind='linear')
        g = interp1d(x, z, kind='linear')

        # Filtrar los Delta_pi globales que están dentro del rango de este Cb específico
        x_interp = all_delta_pi[(all_delta_pi >= x.min()) & (all_delta_pi <= x.max())]
        y_interp = f(x_interp)
        z_interp = g(x_interp)

        df2 = pd.DataFrame({'TMP': z_interp,'J': y_interp, 'Delta_Pi': x_interp, 'Cb': np.full(len(y_interp), cb)})
        df_vacio = pd.concat([df_vacio, df2], ignore_index=True)
    
    counts = df_vacio['Delta_Pi'].value_counts()
    valid_delta_pi = counts[counts >= 2].index
    df_filtered = df_vacio[df_vacio['Delta_Pi'].isin(valid_delta_pi)].sort_values(['Delta_Pi', 'Cb'])

    results_k = []

    # Agrupar por cada Delta_Pi único
    for dp, group in df_filtered.groupby('Delta_Pi'):
        js = group['J'].values
        cbs = group['Cb'].values

        indices = range(len(group))
        k_list_for_dp = []

        for i, j in combinations(indices, 2):
            j1, j2 = js[i], js[j]
            cb1, cb2 = cbs[i], cbs[j]

            if cb1 > 0 and cb2 > 0 and cb1 != cb2:
                k_val = np.abs((j1 - j2) / (np.log(cb1) - np.log(cb2)))
                k_list_for_dp.append(k_val)

        if k_list_for_dp:
            results_k.append({
                'Delta_Pi': dp,
                'k_lista_original': k_list_for_dp,
                'k_promedio': np.mean(k_list_for_dp),
                'k_std/k_promedio': np.std(k_list_for_dp)/np.mean(k_list_for_dp)
            })

    df_k_summary = pd.DataFrame(results_k)


    # Limpiamos df_filtered de la columna 'k' anterior si existe para evitar duplicados en el merge
    if 'k' in df_filtered.columns:
        df_filtered = df_filtered.drop(columns=['k'])

    # Unimos con los nuevos datos estadísticos
    df_filtered = df_filtered.merge(df_k_summary, on='Delta_Pi', how='left')

    # Renombramos k_promedio a k para mantener compatibilidad con tus celdas siguientes
    df_filtered = df_filtered.rename(columns={'k_promedio': 'k'})

    df_filtered = df_filtered[df_filtered['k'] > 10]
    # Se reemplaza 'and' por '&' y se agregan paréntesis para comparación elemento a elemento
    df_filtered = df_filtered[(df_filtered['k_std/k_promedio'] > 0.001) & (df_filtered['k_std/k_promedio'] < 0.2)]

    df_filtered['Cw'] = df_filtered['Cb'] * np.exp(df_filtered['J'] / df_filtered['k'])

    return np.mean(df_filtered['k'])

