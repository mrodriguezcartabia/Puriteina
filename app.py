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

tab1, tab2 = st.tabs(["Cálculo de C_w y análisis", "Algoritmo de filtrado"])

with tab1:
    st.header("Análisis de datos y cálculo de $C_w$")
    
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Ingreso de datos")
        st.markdown("""Ingrese los valores de $TMP$, $J$ y $C_b$. Para esto trabaje con volumen constante de soluciòn. 
        Luego, para distintos valores de $C_b$ y $TMP$, calcule $J$. Se necesitan al menos dos valores distintos de $C_b$.
        Nota: se puede copiar y pegar columnas enteras desde Excel.""")
        
        # Datos por defecto para que la app funcione de entrada
        default_data = pd.DataFrame({
            'TMP': [1.0, 1.0],
            'J': [1.0, 1.0],
            'Cb': [1.0, 1.0]
        })
        
        df = st.data_editor(default_data, num_rows="dynamic")
            
    with col2:
        st.subheader("Permeabilidad de la membrana sucia ($L_{fm}$)")
        st.markdown("Ingrese los datos medidos con solvente **sin proteína**:")
        j_solv = st.number_input("Flujo del solvente ($J$)", value=50.0, step=1.0)
        tmp_solv = st.number_input("Presión Transmembrana ($TMP$)", value=1.0, step=0.1)
        
        if tmp_solv > 0:
            L_fm = j_solv / tmp_solv
            st.info(f"Permeabilidad calculada: **$L_{{fm}}$ = {L_fm:.2f}**")
        else:
            st.error("TMP debe ser mayor a 0.")
            L_fm = 1.0 # fallback
            

    if st.button("Calcular y graficar"):
        if len(df['Cb'].unique()) < 2:
            st.warning("Se necesitan al menos dos concentraciones ($C_b$) diferentes para calcular $k$.")
        else:
            # Paso 2c: Cálculo de presión osmótica
            df['Delta_pi'] = df['TMP'] - (df['J'] / L_fm)
            
            # Paso 2d: Cálculo de k para Delta_pi fija
            cb_vals = sorted(df['Cb'].unique())
            cb1, cb2 = cb_vals[0], cb_vals[-1] # Tomamos los extremos para mayor claridad
            
            df1 = df[df['Cb'] == cb1].sort_values('Delta_pi')
            df2 = df[df['Cb'] == cb2].sort_values('Delta_pi')
            
            # Funciones de interpolación para J en función de Delta_pi
            f_j1 = interp1d(df1['Delta_pi'], df1['J'], kind='linear', fill_value="extrapolate")
            f_j2 = interp1d(df2['Delta_pi'], df2['J'], kind='linear', fill_value="extrapolate")
            
            # Crear un rango común de Delta_pi superpuesto para evaluar
            min_pi = max(df1['Delta_pi'].min(), df2['Delta_pi'].min())
            max_pi = min(df1['Delta_pi'].max(), df2['Delta_pi'].max())
            
            if min_pi < max_pi:
                pi_range = np.linspace(min_pi, max_pi, 10)
                j1_interp = f_j1(pi_range)
                j2_interp = f_j2(pi_range)
                
                # k = (J1 - J2) / (ln(Cb2) - ln(Cb1))
                k_array = (j1_interp - j2_interp) / (np.log(cb2) - np.log(cb1))
                k_mean = np.mean(k_array)
                st.session_state.k_mean = abs(k_mean) # Guardar en session_state
                
                st.success(f"Coeficiente de transferencia de masa calculado: **$k$ = {st.session_state.k_mean:.2f}**")
                
                # Paso 2f: Cálculo de C_w para cada punto
                df['Cw'] = df['Cb'] * np.exp(df['J'] / st.session_state.k_mean)
                
                # Paso 2e: Gráfico interactivo con Plotly
                fig = px.line(df, x='TMP', y='J', color='Cb', markers=True,
                              title="Curvas de $J$ contra $TMP$ interponaladas",
                              labels={'TMP': 'Presión Transmembrana (TMP)', 'J': 'Flujo (J)', 'C_b': 'Concentración (C_b)'},
                              hover_data={'C_w': ':.2f', 'Delta_pi': ':.2f'})
                
                fig.update_traces(mode='lines+markers')
                st.plotly_chart(fig, use_container_width=True)
                
                with st.expander("Ver tabla de resultados completos"):
                    st.dataframe(df.style.format("{:.2f}"))
            else:
                st.error("No hay superposición suficiente en los valores de Presión Osmótica para interpolar y calcular k.")

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
