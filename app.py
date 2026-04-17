import streamlit as st
import pandas as pd
import os
import base64
from fpdf import FPDF
from datetime import datetime

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Plan Canje Würth", page_icon="assets/favicon.png", layout="wide")

# --- 2. ESTILOS Y MÁSCARA ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stMetricValue { font-size: 45px !important; color: #cc0000 !important; }
    .stButton>button { width: 100%; border-radius: 4px; height: 3em; background-color: #cc0000; color: white; font-weight: bold; }
    .white-card { background-color: #ffffff; padding: 30px; border-radius: 10px; border-top: 8px solid #cc0000; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

# --- 3. CARGA DE DATOS ---
@st.cache_data
def load_data():
    df_p = pd.read_excel("productos.xlsx")
    df_b = pd.read_excel("config_beneficios.xlsx")
    df_p.columns = [str(c).strip() for c in df_p.columns]
    df_b.columns = [str(c).strip() for c in df_b.columns]
    # Mapeo flexible
    mapping = {'Nombre Comercial': 'Comercial', 'Familia': 'Tecnica', 'Dto. Base': 'Base', 'Dto. por Unidad': 'Unidad', 'Tope': 'Tope'}
    df_b = df_b.rename(columns=lambda x: mapping.get(x, x))
    return df_p, df_b

df_productos, df_beneficios = load_data()

# --- 4. GESTIÓN DE CARRITO Y PASOS ---
if 'carrito' not in st.session_state: st.session_state.carrito = []
if 'paso' not in st.session_state: st.session_state.paso = 1

# --- 5. INTERFAZ ---
st.title("♻️ Plan Canje REDSTRIPE")

# PUNTO 5: Desplegable Informativo
with st.expander("ℹ️ ¿Cómo funcionan nuestros descuentos?"):
    st.write("""
    1. **Beneficio Inicial:** Cada categoría tiene un descuento base por participar.
    2. **Premio al Reciclaje:** Por cada herramienta vieja que entregues, sumamos un porcentaje adicional.
    3. **Tope de Seguridad:** El descuento total no superará el tope máximo definido para la familia de productos.
    4. **Múltiples Categorías:** Si entregas herramientas de distintos tipos, te otorgamos el **Tope de Descuento más alto** disponible.
    """)

st.markdown('<div class="white-card">', unsafe_allow_html=True)

# PASO 1: CALCULADORA COMERCIAL
if st.session_state.paso == 1:
    st.subheader("1. Simulador de Beneficio")
    c1, c2 = st.columns(2)
    
    with c1:
        cant = st.number_input("Cantidad total de herramientas a entregar:", min_value=1, value=1)
        # Permitimos seleccionar múltiples para aplicar la regla del Tope más alto
        fams_selecionadas = st.multiselect("Tipos de herramientas que entregas:", df_beneficios['Comercial'].unique())
    
    if fams_selecionadas:
        reglas = df_beneficios[df_beneficios['Comercial'].isin(fams_selecionadas)]
        
        # Lógica Punto 4: Tomar el Tope más alto
        mejor_tope = reglas['Tope'].max()
        mejor_base = reglas['Base'].max()
        mejor_unidad = reglas['Unidad'].max()
        
        dto_final = min(mejor_base + (cant * mejor_unidad), mejor_tope)
        
        with c2:
            st.metric("BENEFICIO HABILITADO", f"{dto_final}%")
            st.info(f"Aplicando el tope máximo de beneficio ({mejor_tope}%) de las categorías seleccionadas.")
        
        if st.button("Siguiente: Armar Pedido ➔"):
            st.session_state.temp_dto = dto_final
            st.session_state.temp_cant = cant
            st.session_state.paso = 2
            st.rerun()
    else:
        st.warning("Selecciona al menos una categoría para calcular el beneficio.")

# PASO 2: CARRITO DE COMPRAS MULTI-PRODUCTO
else:
    st.subheader("2. Selección de Productos (Punto de Venta)")
    
    col_a, col_b = st.columns([1.2, 0.8])
    
    with col_a:
        busqueda = st.text_input("🔍 Buscar por Código SAP o Nombre")
        df_filt = df_productos[
            df_productos['Código del producto'].astype(str).str.contains(busqueda) | 
            df_productos['Nombre del producto'].str.contains(busqueda, case=False)
        ] if busqueda else df_productos.head(0)
        
        if not df_filt.empty:
            item_sel = st.selectbox("Resultado de búsqueda:", df_filt['Nombre del producto'].unique())
            codigo_sap = df_filt[df_filt['Nombre del producto'] == item_sel]['Código del producto'].values[0]
            precio_l = st.number_input("Precio de Lista (UYU)", min_value=0.0, step=10.0)
            
            if st.button("➕ Agregar al Carrito"):
                dto_item = st.session_state.temp_dto
                ahorro = precio_l * (dto_item / 100)
                st.session_state.carrito.append({
                    "SAP": codigo_sap, "Producto": item_sel, "Lista": precio_l, "Dto": dto_item, "Ahorro": ahorro, "Final": precio_l - ahorro
                })
        elif busqueda:
            st.error("No se encontró el producto.")

    with col_b:
        st.write("### Resumen de Compra")
        if st.session_state.carrito:
            df_car = pd.DataFrame(st.session_state.carrito)
            st.table(df_car[['Producto', 'Final']])
            total_ahorro = df_car['Ahorro'].sum()
            total_pagar = df_car['Final'].sum()
            
            st.metric("TOTAL A PAGAR", f"${total_pagar:,.2f}")
            st.write(f"🎁 Ahorro Total: **${total_ahorro:,.2f}**")
            
            if st.button("🗑️ Vaciar Carrito"):
                st.session_state.carrito = []
                st.rerun()

    st.divider()
    if st.button("⬅ Volver a Recalcular"):
        st.session_state.paso = 1
        st.session_state.carrito = []
        st.rerun()

st.markdown('</div>', unsafe_allow_html=True)
