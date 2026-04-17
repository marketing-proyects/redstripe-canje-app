import streamlit as st
import pandas as pd
import os
import base64
from fpdf import FPDF
from datetime import datetime

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Plan Canje Würth", page_icon="assets/favicon.png", layout="wide")

# --- 2. MÁSCARA Y ELIMINACIÓN DE SOMBRAS NATIVAS ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            .block-container {padding-top: 1rem;}
            
            /* Quitar sombras de contenedores de Streamlit */
            div[data-testid="stVerticalBlock"] > div {
                background-color: transparent !important;
                box-shadow: none !important;
                border: none !important;
            }

            [data-testid="stMetricValue"] { font-size: 45px; color: #cc0000; font-weight: bold; }
            
            .stButton>button { 
                width: 100%; 
                border-radius: 5px; 
                height: 3em; 
                background-color: #cc0000; 
                color: white; 
                border: none; 
                font-weight: bold; 
            }
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- 3. LOGO Y TEXTO EXPLICATIVO ---
def get_base64(file_path):
    if file_path and os.path.exists(file_path):
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

logo_base64 = get_base64("logo_wurth.png")

st.markdown(f"""
    <style>
    .logo-container {{
        position: fixed;
        top: 25px;
        right: 50px;
        width: 160px;
        z-index: 1000;
    }}
    .custom-card {{
        background-color: #ffffff;
        padding: 35px;
        border-radius: 12px;
        border-top: 6px solid #cc0000;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08); /* Sombra controlada y sutil */
        margin-top: 10px;
    }}
    .explicacion-texto {{
        color: #333;
        font-size: 1.1em;
        line-height: 1.6;
        margin-bottom: 20px;
        padding: 10px 0;
    }}
    </style>
    <div class="logo-container">
        <img src="data:image/png;base64,{logo_base64}">
    </div>
    """, unsafe_allow_html=True)

# --- 4. CARGA DE DATOS ---
@st.cache_data
def load_data():
    df_p = pd.read_excel("productos.xlsx")
    df_b = pd.read_excel("config_beneficios.xlsx")
    df_p.columns = [str(c).strip() for c in df_p.columns]
    df_b.columns = [str(c).strip() for c in df_b.columns]
    nuevos = {}
    for c in df_b.columns:
        low = c.lower()
        if 'familia' in low: nuevos[c] = 'Familia'
        elif 'base' in low: nuevos[c] = 'Base'
        elif 'unidad' in low: nuevos[c] = 'Unidad'
        elif 'tope' in low or 'max' in low: nuevos[c] = 'Tope'
    df_b = df_b.rename(columns=nuevos)
    return df_p, df_b

df_productos, df_beneficios = load_data()

if 'paso' not in st.session_state:
    st.session_state.paso = 1

# --- 5. INTERFAZ ---
st.title("♻️ Plan Canje REDSTRIPE")

# Texto explicativo limpio (reemplaza cualquier bloque sombreado anterior)
st.markdown("""
<div class="explicacion-texto">
    Este sistema es un <b>Simulador de Descuentos para Reciclaje</b>. Incentivamos a nuestros clientes a entregar 
    sus herramientas viejas para asegurar un proceso de disposición responsable, otorgando a cambio 
    <b>beneficios exclusivos</b> en la compra de herramientas nuevas Würth.
</div>
""", unsafe_allow_html=True)

# Contenedor principal con nuestra clase CSS personalizada
st.markdown('<div class="custom-card">', unsafe_allow_html=True)

if st.session_state.paso == 1:
    st.subheader("1. Cálculo de Beneficio por Entrega")
    col1, col2 = st.columns(2)
    
    with col1:
        cant = st.number_input("Cantidad de herramientas a entregar:", min_value=1, step=1, value=1)
        fam = st.selectbox("Familia del producto nuevo:", df_beneficios['Familia'].unique())
    
    regla = df_beneficios[df_beneficios['Familia'] == fam].iloc[0]
    dto = min(regla['Base'] + (cant * regla['Unidad']), regla['Tope'])
    
    with col2:
        st.metric("DESCUENTO:", f"{dto}%")
        st.write(f"Al entregar **{cant}** unidades, accedes al beneficio para la familia **{fam}**.")
    
    if st.button("Continuar a selección de productos ➔"):
        st.session_state.temp_dto = dto
        st.session_state.temp_cant = cant
        st.session_state.paso = 2
        st.rerun()

else:
    st.subheader("2. Detalle de Compra y Ahorro")
    c3, c4 = st.columns(2)
    
    with c3:
        nro = st.text_input("Nro. Cliente / RUT")
        nom = st.text_input("Nombre del Cliente")
        mod = st.selectbox("Modelo REDSTRIPE", sorted(df_productos['Nombre del modelo'].unique()))
        items = df_productos[df_productos['Nombre del modelo'] == mod]
        prod = st.selectbox("Producto específico", items['Nombre del producto'].unique())
        sap = items[items['Nombre del producto'] == prod]['Código del producto'].values[0]
        st.write(f"**Código SAP:** `{sap}`")
        
    with c4:
        precio = st.number_input("Precio de Lista (UYU)", min_value=0.0, step=1.0)
        final = precio * (1 - st.session_state.temp_dto / 100)
        ahorro = precio - final
        
        st.markdown(f"### Precio Final: <span style='color:#cc0000;'>${final:,.2f}</span>", unsafe_allow_html=True)
        st.write(f"💰 Ahorro total: **${ahorro:,.2f}**")

    st.divider()
    b1, b2 = st.columns(2)
    with b1:
        if st.button("⬅ Volver"):
            st.session_state.paso = 1
            st.rerun()
    with b2:
        if st.button("📥 Generar Ticket"):
            # Generar PDF (Lógica simplificada para el ejemplo)
            st.success("Ticket listo para descarga (Simulado)")

st.markdown('</div>', unsafe_allow_html=True)
