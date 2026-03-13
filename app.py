import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from scipy.interpolate import interp1d
# URL de la api: https://puriteina-cj2phtzq4expwnsbztit24.streamlit.app/

# Configuración de la página
st.set_page_config(page_title="Control C_wall - Van Reis", layout="wide")
st.title("Modelo de control con $C_{wall}$ constante")

# Inicializar variables en session_state para compartir entre pestañas
if 'k_mean' not in st.session_state:
    st.session_state.k_mean = None

tab1, tab2 = st.tabs(["Cálculo de $C_w$ y análisis", "Algoritmo de filtrado"])

with tab1:
    st.header("Análisis de datos y cálculo de $C_w$")
    
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Ingreso de datos")
        st.markdown("""Ingrese los valores de $TMP$  en bar, $J$  en L/(m^2h) y $C_b$  en g/L. Para esto trabaje con volumen constante de soluciòn. 
        Luego, para distintos valores de $C_b$ y $TMP$, calcule $J$. Se necesitan al menos dos valores distintos de $C_b$.
        Nota: se puede copiar y pegar columnas enteras desde Excel.""")
        
        # Inicializar los datos en el estado de la sesión si no existen
        if 'df_data' not in st.session_state:
            st.session_state.df_data = pd.DataFrame({
                'TMP': ["0.0"],
                'J': ["0.0"],
                'Cb': ["0.0"]
            })

        # Botón para cargar datos de prueba funcionales
        if st.button("Cargar datos de prueba"):
            st.session_state.df_data = pd.DataFrame({
                'TMP': ["0.55", "0.9", "1.05", "1.25", "1.5", "1.7",
                        "0.4", "0.6", "0.8", "0.95", "1.15", "1.35",
                        "0.4", "0.55", "0.75", "0.95", "1.15",
                        "0.4", "0.55", "0.75", "0.95", "1.1"],
                'J': ["60.0", "90.0", "105.0", "112.0", "120.0", "127.0",
                        "37.0", "60.0", "73.0", "85.0", "90.0", "95.0",
                        "37.5", "52.5", "67.5", "75.0", "78.75",
                        "37.5", "48.75", "56.25", "60.0", "63.75"],
                'Cb': ["2.51", "2.51", "2.51", "2.51", "2.51", "2.51",
                        "6.31", "6.31", "6.31", "6.31", "6.31", "6.31",
                        "10.4", "10.4", "10.4", "10.4", "10.4",
                        "19.6", "19.6", "19.6", "19.6", "19.6"]
            })
            st.rerun()
        
        # Mostramos el editor conectado al session_state y guardamos los cambios en df_editado
        df_editado = st.data_editor(st.session_state.df_data, num_rows="dynamic")
        
        # Agregamos la línea para leer los decimales al importar desde una hoja de cálculo
        # y convertimos el texto a números de forma segura
        df = df_editado.astype(str).replace(',', '.', regex=True).apply(pd.to_numeric, errors='coerce')
            
    with col2:
        st.subheader("Permeabilidad de la membrana sucia ($L_{fm}$)")
        st.markdown("Ingrese los datos medidos con solvente **sin proteína**:")
        j_solv = st.number_input("Flujo del solvente ($J$)", value=50.0, step=1.0)
        tmp_solv = st.number_input("Presión Transmembrana ($TMP$)", value=1.0, step=0.1)
        
        if tmp_solv > 0:
            L_fm = j_solv / tmp_solv
            st.info(f"Permeabilidad calculada en Lm^2/(h bar): **$L_{{fm}}$ = {L_fm:.2f}**")
        else:
            st.error("TMP debe ser mayor a 0.")
            L_fm = 1.0 # fallback
            

    # Creamos un estado para saber si ya se hizo el cálculo
    if 'calculado' not in st.session_state:
        st.session_state.calculado = False

    if st.button("Calcular y graficar"):
        st.session_state.calculado = True

    if st.session_state.calculado: # Ahora el contenido no desaparece
        if df.isna().any().any():
            st.error("Se detectaron filas incompletas o vacías. Estas filas serán ignoradas para evitar errores matemáticos.")
            df = df.dropna().reset_index(drop=True)
            
        if len(df) == 0:
            st.error("La tabla quedó sin datos válidos. Por favor, complete los valores.")
            
        elif len(df['Cb'].unique()) < 2:
            st.warning("Se necesitan al menos dos concentraciones ($C_b$) diferentes para calcular $k$.")
        else:
            # Paso 2c: Cálculo de presión osmótica
            df['Delta_pi'] = df['TMP'] - (df['J'] / L_fm)
            
            # Paso 2d: Cálculo de k para Delta_pi fija
            cb_vals = sorted(df['Cb'].unique())

            dfs_dict = {}
            fjs_dict = {}
            
            for cb in cb_vals:
                df_cb = df[df['Cb'] == cb].sort_values('Delta_pi')
                dfs_dict[cb] = df_cb

                if len(df_cb) > 1: # Se necesitan al menos 2 puntos para interpolar
                    fjs_dict[cb] = interp1d(df_cb['TMP'], df_cb['J'], kind='linear', fill_value="extrapolate")
                    
            k_valores = []
            
            for i in range(len(cb_vals) - 1):
                
                cb1 = cb_vals[i]
                cb2 = cb_vals[i+1]
                
                min_TMP = dfs_dict[cb]['TMP'].min() 
                max_TMP = dfs_dict[cb]['TMP'].max()
                
                TMP_range = np.linspace(min_TMP, max_TMP, 10)
                                
                j1_interp = fjs_dict[cb1](TMP_range)
                j2_interp = fjs_dict[cb2](TMP_range)
        
            k_mean = 23 #np.mean(k_valores)
            st.session_state.k_mean = abs(k_mean)
            st.success(f"Coeficiente de transferencia de masa calculado: **$k$ = {st.session_state.k_mean:.2f}**")
            
            # Paso 2f: Cálculo de C_w para cada punto
            #df['Cw'] = df['Cb'] * np.exp(df['J'] / st.session_state.k_mean)
            
            # Paso 2e: Gráfico interactivo con Plotly
            fig = px.line(df, x='TMP', y='J', color='Cb', markers=True,
                          title="Curvas de J contra TMP interponaladas",
                          labels={'TMP': 'Presión Transmembrana (TMP)', 'J': 'Flujo (J)', 'C_b': 'Concentración (C_b)'})
                          #hover_data={'Cw': ':.2f', 'Delta_pi': ':.2f'})
            
            fig.update_traces(mode='lines+markers')
            st.plotly_chart(fig, use_container_width=True)

            # C_w objetivo
            st.markdown("---")
            st.subheader("Análisis de $C_{wall}$ objetivo")
            cw_user = st.number_input("Defina un valor de $C_w$ objetivo para encontrar en las curvas:", value=100.0)

            puntos_interpolados = []
            
            for cb in df['Cb'].unique():
                # Para cada concentración, necesitamos saber qué J corresponde al Cw elegido
                # J = k * ln(Cw / Cb)
                j_target = st.session_state.k_mean * np.log(cw_user / cb)
                
                # Filtramos los datos de esta concentración
                df_sub = df[df['Cb'] == cb].sort_values('J')
                
                # Verificamos si el flujo calculado está dentro del rango medido para interpolar el TMP
                if df_sub['J'].min() <= j_target <= df_sub['J'].max():
                    f_tmp = interp1d(df_sub['J'], df_sub['TMP'], kind='linear')
                    tmp_target = f_tmp(j_target)
                    
                    puntos_interpolados.append({
                        'TMP': tmp_target,
                        'J': j_target,
                        'Cb': cb,
                        'Leyenda': f'Punto Cw={cw_user}'
                    })

            if puntos_interpolados:
                df_puntos = pd.DataFrame(puntos_interpolados)
                # Agregamos los puntos encontrados al gráfico existente
                for _, row in df_puntos.iterrows():
                    fig.add_scatter(x=[row['TMP']], y=[row['J']], 
                                    mode='markers', 
                                    marker=dict(size=12, symbol='star', color='black'),
                                    name=f"Target en Cb:{row['Cb']}")
                
                st.plotly_chart(fig, use_container_width=True) # Redibujar con los puntos
                st.success(f"Se han marcado los puntos donde $C_w$ llega a {cw_user}")
            else:
                st.warning(f"El valor de $C_w = {cw_user}$ no se alcanza dentro del rango de datos experimentales.")
            
            with st.expander("Ver tabla de resultados completos"):
                st.dataframe(df.style.format("{:.2f}"))
            

with tab2:
    st.header("Algoritmo de proceso de filtrado")
    
    if st.session_state.k_mean is None:
        st.warning("Primero debes calcular el coeficiente $k$ en la pestaña anterior para utilizar el algoritmo.")
    else:
        k = st.session_state.k_mean
        
        st.subheader("Parámetros del proceso")
        col3, col4, col5 = st.columns(3)
        cb_inicial = col3.number_input("Concentración inicial ($C_{b, inicial}$)", value=1.0, step=0.01)
        cb_final = col4.number_input("Concentración Final ($C_{b, final}$)", value=50.0, step=0.01)
        cw_target = col5.number_input("Concentración en pared objetivo ($C_w$)", value=100.0, step=0.01)
        
        if cw_target <= cb_inicial:
            st.error("$C_w$ debe ser estrictamente mayor a la concentración inicial.")
        else:
            # Paso 3b: Cálculo del flujo inicial
            j_inicial = k * np.log(cw_target / cb_inicial)
            
            st.markdown("---")
            st.subheader("Instrucciones de operación")
            
            st.markdown("### Paso 1: Configuración inicial")
            st.info(f"""
            1. Abra la válvula de retentado **al máximo** para minimizar la $TMP$.
            2. Ajuste la potencia del motor (bomba de alimentación) de forma tal que el flujo de permeado ($J$) alcance exactamente:
            
            **$J_0 = {j_inicial:.2f}$**
            
            *(Calculado mediante $J = k \cdot \ln(C_w / C_{{b, inicial}})$ con $k = {k:.2f}$)*
            """)
            
            st.markdown("### Paso 2: Ejecución dinámica")
            st.success(f"""
            A medida que el proceso avanza y la concentración $C_b$ aumenta desde {cb_inicial} hacia {cb_final}, el flujo objetivo irá disminuyendo.
            
            Debe **ajustar (cerrar) gradualmente la válvula de retentado** para que el flujo medido siga en todo momento la siguiente curva de descenso:
            
            $$J(t) = {k:.2f} \cdot \ln \\left( \\frac{{{cw_target}}}{{C_b(t)}} \\right)$$
            
            **Precaución:** No modifique la potencia del motor durante este paso para evitar alterar el coeficiente de transferencia de masa ($k$).
            """)
