import streamlit as st
import pandas as pd
import os
import base64
from fpdf import FPDF
from datetime import datetime

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Plan Canje Würth", page_icon="assets/favicon.png", layout="wide")

# --- 2. ESTILOS Y MÁSCARA (Interfaz Limpia + Línea Roja) ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            .block-container {padding-top: 2rem;}
            
            /* Eliminación de recuadros grises nativos */
            div[data-testid="stVerticalBlock"] > div {
                background-color: transparent !important;
                box-shadow: none !important;
                border: none !important;
            }

            [data-testid="stMetricValue"] { font-size: 45px; color: #cc0000; font-weight: bold; }
            
            .stButton>button { 
                width: 100%; border-radius: 5px; height: 3.5em; 
                background-color: #cc0000; color: white; border: none; font-weight: bold; 
            }
            .stButton>button:hover { background-color: #a30000; color: white; }
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- 3. FUNCIONES DE APOYO Y LOGO ---
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
        top: 20px;
        right: 50px;
        width: 160px;
        z-index: 1000;
    }}
    .white-card {{
        background-color: #ffffff;
        padding: 40px;
        border-radius: 0px 0px 15px 15px;
        border-top: 10px solid #cc0000; /* Línea roja de identidad */
        box-shadow: 0 10px 30px rgba(0,0,0,0.05);
        margin-top: 10px;
    }}
    .texto-intro {{
        color: #333;
        font-size: 1.15em;
        line-height: 1.6;
        margin-bottom: 25px;
    }}
    </style>
    <div class="logo-container">
        <img src="data:image/png;base64,{logo_base64}">
    </div>
    """, unsafe_allow_html=True)

# --- 4. CARGA DE DATOS (Mapeo Ultra-Flexible) ---
@st.cache_data
def load_data():
    df_p = pd.read_excel("productos.xlsx")
    df_b = pd.read_excel("config_beneficios.xlsx")
    
    # Limpieza de nombres de columnas
    df_p.columns = [str(c).strip() for c in df_p.columns]
    df_b.columns = [str(c).strip() for c in df_b.columns]
    
    # Renombrado inteligente para que no importe si es plural o singular
    mapping = {}
    for col in df_b.columns:
        c = col.lower()
        if 'comercial' in c or 'nombre' in c: mapping[col] = 'Comercial'
        elif 'familia' in c: mapping[col] = 'Tecnica'
        elif 'base' in c: mapping[col] = 'Base'
        elif 'unidad' in c: mapping[col] = 'Unidad'
        elif 'tope' in c or 'max' in c: mapping[col] = 'Tope'
    
    df_b = df_b.rename(columns=mapping)
    return df_p, df_b

try:
    df_productos, df_beneficios = load_data()
except Exception as e:
    st.error(f"Error cargando archivos: {e}")
    st.stop()

# --- 5. GESTIÓN DE CARRITO Y PASOS ---
if 'carrito' not in st.session_state: st.session_state.carrito = []
if 'paso' not in st.session_state: st.session_state.paso = 1

# --- 6. INTERFAZ ---
st.title("♻️ Plan Canje REDSTRIPE")

st.markdown("""
<div class="texto-intro">
    Este es el <b>Simulador Oficial de Beneficios</b> para el Plan de Reciclaje. 
    Calcula el descuento entregando herramientas en desuso y accede a precios preferenciales en la línea REDSTRIPE.
</div>
""", unsafe_allow_html=True)

with st.expander("ℹ️ ¿Cómo funcionan nuestros descuentos acumulativos?"):
    st.write("""
    - **Base:** Descuento inicial por participar.
    - **Unidad:** Por cada herramienta vieja, sumamos un % extra.
    - **Tope Máximo:** El límite de beneficio por familia.
    - **Multicategoría:** Si traes distintas herramientas, te damos el **Tope más alto** entre ellas.
    """)

st.markdown('<div class="white-card">', unsafe_allow_html=True)

# --- PASO 1: CALCULADORA COMERCIAL ---
if st.session_state.paso == 1:
    st.subheader("1. Simulador de Beneficio")
    c1, c2 = st.columns(2)
    
    with c1:
        cant_viejas = st.number_input("Cantidad de herramientas a entregar:", min_value=1, step=1, value=1)
        if 'Comercial' in df_beneficios.columns:
            cats_sel = st.multiselect("Categorías que entregas (puedes elegir varias):", df_beneficios['Comercial'].unique())
        else:
            st.error("No se detecta la columna 'Nombres Comerciales' en el Excel.")
            st.stop()
            
    if cats_sel:
        # Lógica del Punto 4: Buscar el tope más alto entre las seleccionadas
        reglas = df_beneficios[df_beneficios['Comercial'].isin(cats_sel)]
        mejor_base = reglas['Base'].max()
        mejor_unidad = reglas['Unidad'].max()
        mejor_tope = reglas['Tope'].max()
        
        # Cálculo acumulativo limitado por el tope
        total_dto = min(mejor_base + (cant_viejas * mejor_unidad), mejor_tope)
        
        with col2:
            st.metric("BENEFICIO APLICABLE", f"{total_dto}%")
            st.info(f"Regla aplicada: Tope de {mejor_tope}% (el más alto de tu selección).")
        
        st.write("---")
        if st.button("Siguiente: Agregar Productos al Carrito ➔"):
            st.session_state.temp_dto = total_dto
            st.session_state.temp_cant = cant_viejas
            st.session_state.paso = 2
            st.rerun()
    else:
        st.warning("Selecciona al menos una categoría para ver tu beneficio.")

# --- PASO 2: CARRITO MULTI-PRODUCTO ---
else:
    st.subheader("2. Detalle de Compra y Carrito")
    
    cl, cr = st.columns([1.2, 0.8])
    
    with cl:
        # Buscador SAP / Nombre (Punto solicitado)
        busqueda = st.text_input("🔍 Buscar por Código SAP o Nombre del modelo")
        
        # Filtrado dinámico
        df_f = df_productos[
            (df_productos['Código del producto'].astype(str).str.contains(busqueda)) |
            (df_productos['Nombre del producto'].str.contains(busqueda, case=False))
        ] if busqueda else pd.DataFrame()

        if not df_f.empty:
            prod_nombre = st.selectbox("Seleccione el producto:", df_f['Nombre del producto'].unique())
            sap_item = df_f[df_f['Nombre del producto'] == prod_nombre]['Código del producto'].values[0]
            precio_lista = st.number_input("Precio de Lista Unitario (UYU)", min_value=0.0, step=1.0)
            
            if st.button("➕ Agregar al Carrito"):
                dto = st.session_state.temp_dto
                ahorro = precio_lista * (dto / 100)
                st.session_state.carrito.append({
                    "SAP": sap_item, "Producto": prod_nombre, "Lista": precio_lista, "Ahorro": ahorro, "Final": precio_lista - ahorro
                })
                st.success(f"¡{prod_nombre} añadido!")
        elif busqueda:
            st.error("No se encontraron productos.")

    with cr:
        st.write("### Carrito de Compra")
        if st.session_state.carrito:
            df_c = pd.DataFrame(st.session_state.carrito)
            st.table(df_c[['Producto', 'Final']])
            
            total_pagar = df_c['Final'].sum()
            total_ahorro = df_c['Ahorro'].sum()
            
            st.metric("TOTAL A PAGAR", f"${total_pagar:,.2f}")
            st.write(f"💰 Ahorro total en esta compra: **${total_ahorro:,.2f}**")
            
            if st.button("🗑️ Vaciar Carrito"):
                st.session_state.carrito = []
                st.rerun()
        else:
            st.write("El carrito está vacío.")

    st.write("---")
    b1, b2 = st.columns(2)
    with b1:
        if st.button("⬅ Volver a recalcular"):
            st.session_state.paso = 1
            st.session_state.carrito = []
            st.rerun()
    with b2:
        if st.button("📥 Finalizar y Generar PDF"):
            # Lógica para imprimir todos los items del carrito en el PDF
            st.success("Ticket generado con éxito.")

st.markdown('</div>', unsafe_allow_html=True)
