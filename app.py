import streamlit as st
import pandas as pd
import os
import base64
from fpdf import FPDF
from datetime import datetime

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Plan Canje Würth", page_icon="assets/favicon.png", layout="wide")

# --- 2. ESTILOS (Identidad Würth) ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .block-container {padding-top: 2rem;}
    div[data-testid="stVerticalBlock"] > div { background-color: transparent !important; box-shadow: none !important; border: none !important; }
    [data-testid="stMetricValue"] { font-size: 45px; color: #cc0000; font-weight: bold; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3.5em; background-color: #cc0000; color: white; border: none; font-weight: bold; }
    .stButton>button:hover { background-color: #a30000; color: white; border: none; }
    .white-card { background-color: #ffffff; padding: 40px; border-radius: 0px 0px 15px 15px; border-top: 10px solid #cc0000; box-shadow: 0 10px 30px rgba(0,0,0,0.05); margin-top: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- 3. LOGO ---
def get_base64(file_path):
    if file_path and os.path.exists(file_path):
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

logo_base64 = get_base64("logo_wurth.png")
st.markdown(f'<div style="position:fixed; top:25px; right:50px; width:160px; z-index:1000;"><img src="data:image/png;base64,{logo_base64}"></div>', unsafe_allow_html=True)

# --- 4. CARGA DE DATOS ---
@st.cache_data
def load_data():
    df_p = pd.read_excel("productos.xlsx")
    df_b = pd.read_excel("config_beneficios.xlsx")
    df_p.columns = [str(c).strip() for c in df_p.columns]
    df_b.columns = [str(c).strip() for c in df_b.columns]
    # Mapeo por posición para evitar errores de nombre
    df_b = df_b.rename(columns={df_b.columns[0]: 'Comercial', df_b.columns[2]: 'Base', df_b.columns[3]: 'Unidad', df_b.columns[4]: 'Tope'})
    return df_p, df_b

try:
    df_productos, df_beneficios = load_data()
except Exception as e:
    st.error(f"Error: {e}")
    st.stop()

if 'carrito' not in st.session_state: st.session_state.carrito = []
if 'paso' not in st.session_state: st.session_state.paso = 1

# --- 5. INTERFAZ ---
st.title("♻️ Plan Canje REDSTRIPE")
st.markdown('<p style="color:#333; font-size:1.15em;">Simulador de beneficios por reciclaje de herramientas.</p>', unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="white-card">', unsafe_allow_html=True)

    # --- PASO 1: CALCULADORA DETALLADA ---
    if st.session_state.paso == 1:
        st.subheader("1. Detalle de herramientas a entregar")
        col_input, col_result = st.columns([1.2, 0.8])
        
        with col_input:
            categorias_sel = st.multiselect("¿Qué tipos de herramientas trae el cliente?", df_beneficios['Comercial'].unique())
            
            cantidades = {}
            total_unidades = 0
            if categorias_sel:
                st.write("---")
                # Generamos un input por cada categoría seleccionada
                for cat in categorias_sel:
                    cant = st.number_input(f"Cantidad de '{cat}':", min_value=1, step=1, value=1, key=f"q_{cat}")
                    cantidades[cat] = cant
                    total_unidades += cant
            
        if categorias_sel:
            # Lógica: Tomar el mejor set de reglas de las categorías presentes
            reglas = df_beneficios[df_beneficios['Comercial'].isin(categorias_sel)]
            m_base = reglas['Base'].max()
            m_unidad = reglas['Unidad'].max()
            m_tope = reglas['Tope'].max()
            
            # Cálculo final
            dto_preliminar = m_base + (total_unidades * m_unidad)
            dto_final = min(dto_preliminar, m_tope)
            
            with col_result:
                st.metric("BENEFICIO", f"{dto_final}%")
                # Detalle del cálculo para transparencia
                st.markdown(f"""
                **Desglose del cálculo:**
                * Unidades totales: **{total_unidades}**
                * Descuento Base: **{m_base}%**
                * Plus por unidades: **{total_unidades * m_unidad}%**
                * Tope máximo aplicado: **{m_tope}%**
                
                ---
                _Se aplicó la regla más favorable según las categorías entregadas._
                """)
            
            if st.button("Confirmar y Pasar a la Compra ➔"):
                st.session_state.temp_dto = dto_final
                st.session_state.temp_cant = total_unidades
                st.session_state.paso = 2
                st.rerun()
        else:
            st.info("Selecciona las categorías para comenzar el cálculo.")

    # --- PASO 2: CARRITO MULTI-PRODUCTO ---
    else:
        st.subheader("2. Armado de la Compra")
        c_search, c_cart = st.columns([1.1, 0.9])
        
        with c_search:
            busq = st.text_input("🔍 Buscar por Código SAP o Nombre")
            df_res = df_productos[
                (df_productos['Código del producto'].astype(str).str.contains(busq)) |
                (df_productos['Nombre del producto'].str.contains(busq, case=False))
            ] if busq else pd.DataFrame()

            if not df_res.empty:
                item_n = st.selectbox("Producto:", df_res['Nombre del producto'].unique())
                sap_c = df_res[df_res['Nombre del producto'] == item_n]['Código del producto'].values[0]
                p_lista = st.number_input("Precio de Lista (UYU)", min_value=0.0, step=1.0)
                
                if st.button("➕ Agregar al Pedido"):
                    d = st.session_state.temp_dto
                    ahorro = p_lista * (d / 100)
                    st.session_state.carrito.append({"SAP": sap_c, "Producto": item_n, "Lista": p_lista, "Ahorro": ahorro, "Final": p_lista - ahorro})
                    st.success("¡Agregado!")
            elif busq: st.error("Sin resultados.")

        with c_cart:
            if st.session_state.carrito:
                df_c = pd.DataFrame(st.session_state.carrito)
                st.dataframe(df_c[['Producto', 'Final']], use_container_width=True, hide_index=True)
                st.metric("TOTAL A PAGAR", f"${df_c['Final'].sum():,.2f}")
                if st.button("🗑️ Vaciar Carrito"):
                    st.session_state.carrito = []
                    st.rerun()
            else: st.write("Carrito vacío.")

        st.divider()
        b1, b2 = st.columns(2)
        with b1:
            if st.button("⬅ Volver"):
                st.session_state.paso = 1
                st.session_state.carrito = []
                st.rerun()
        with b2:
            if st.button("📥 Generar Ticket"): st.success("PDF generado.")

    st.markdown('</div>', unsafe_allow_html=True)
