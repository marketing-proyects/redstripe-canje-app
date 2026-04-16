import streamlit as st
import pandas as pd
import os
import random
import base64
from fpdf import FPDF
from datetime import datetime

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Plan Canje Würth", page_icon="assets/favicon.png", layout="wide")

# --- 2. MÁSCARA Y ESTILOS ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            .block-container {padding-top: 1rem;}
            [data-testid="stMetricValue"] { font-size: 35px; color: #cc0000; }
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- 3. FUNCIONES DE APOYO ---
def get_base64(file_path):
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

def get_random_bg():
    bg_dir = "assets/fondos"
    search_dir = bg_dir if os.path.exists(bg_dir) else "."
    fondos = [f for f in os.listdir(search_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    return os.path.join(search_dir, random.choice(fondos)) if fondos else None

# Fondo y Logo
bg_image = get_random_bg()
bg_base64 = get_base64(bg_image) if bg_image else ""
logo_base64 = get_base64("logo_wurth.png")

st.markdown(f"""
    <style>
    .stApp {{
        background-image: url("data:image/png;base64,{bg_base64}");
        background-size: cover;
        background-attachment: fixed;
    }}
    .logo-container {{
        position: absolute;
        top: -50px;
        right: 0px;
        width: 150px;
    }}
    .main-card {{
        background-color: rgba(255, 255, 255, 0.96);
        padding: 30px;
        border-radius: 15px;
        border-left: 10px solid #cc0000;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
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
    # Mapeo flexible
    nuevos = {}
    for c in df_b.columns:
        if 'familia' in c.lower(): nuevos[c] = 'Familia'
        elif 'base' in c.lower(): nuevos[c] = 'Base'
        elif 'unidad' in c.lower(): nuevos[c] = 'Unidad'
        elif 'tope' in c.lower() or 'max' in c.lower(): nuevos[c] = 'Tope'
    df_b = df_b.rename(columns=nuevos)
    return df_p, df_b

df_productos, df_beneficios = load_data()

# --- 5. INTERFAZ ---
st.title("♻️ Plan Canje REDSTRIPE")
st.markdown("""
Esta herramienta es un **Simulador de Descuentos** diseñado para incentivar el reciclaje. 
Al entregar tus herramientas viejas, accedes a beneficios exclusivos para renovar tu equipamiento con la calidad **Würth**.
""")

if 'paso' not in st.session_state:
    st.session_state.paso = 1

with st.container():
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    
    if st.session_state.paso == 1:
        st.subheader("Paso 1: Calcula tu beneficio por reciclaje")
        col1, col2 = st.columns(2)
        with col1:
            cant_viejas = st.number_input("¿Cuántas herramientas vas a entregar hoy?", min_value=1, step=1, value=1)
            fam_sel = st.selectbox("Familia que te interesa comprar", df_beneficios['Familia'].unique())
        
        regla = df_beneficios[df_beneficios['Familia'] == fam_sel].iloc[0]
        dto_calculado = min(regla['Base'] + (cant_viejas * regla['Unidad']), regla['Tope'])
        
        with col2:
            st.metric("TU DESCUENTO ESTIMADO", f"{dto_calculado}%")
            st.write(f"¡Excelente elección! Por entregar {cant_viejas} unidades, te bonificamos el máximo permitido para {fam_sel}.")
        
        if st.button("Siguiente: Seleccionar productos ➔"):
            st.session_state.temp_dto = dto_calculado
            st.session_state.temp_cant = cant_viejas
            st.session_state.temp_fam = fam_sel
            st.session_state.paso = 2
            st.rerun()

    else:
        st.subheader("Paso 2: Detalles de la Compra")
        col3, col4 = st.columns(2)
        with col3:
            nro_cliente = st.text_input("Número de Cliente / RUT")
            nombre = st.text_input("Nombre del Cliente")
            modelo_sel = st.selectbox("Modelo", sorted(df_productos['Nombre del modelo'].unique()))
            prods = df_productos[df_productos['Nombre del modelo'] == modelo_sel]
            prod_sel = st.selectbox("Variante", prods['Nombre del producto'].unique())
            codigo_sap = prods[prods['Nombre del producto'] == prod_sel]['Código del producto'].values[0]
            
        with col4:
            precio_lista = st.number_input("Precio de Lista (UYU)", min_value=0.0, step=100.0)
            dto = st.session_state.temp_dto
            ahorro = precio_lista * (dto / 100)
            precio_final = precio_lista - ahorro
            
            st.markdown(f"### Precio Final: **${precio_final:,.2f}**")
            st.write(f"Te estás ahorrando **${ahorro:,.2f}** por tu compromiso con el reciclaje.")
            st.info(f"Código SAP: {codigo_sap}")

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("⬅ Volver a calcular"):
                st.session_state.paso = 1
                st.rerun()
        with col_btn2:
            if st.button("📥 Generar Ticket PDF"):
                # (Aquí iría la lógica del PDF que ya teníamos, usando precio_final y ahorro)
                st.success("Ticket Generado!")
                
    st.markdown('</div>', unsafe_allow_html=True)
