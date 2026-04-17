import streamlit as st
import pandas as pd
import os
import base64
from fpdf import FPDF
from datetime import datetime

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Plan Canje Würth", page_icon="assets/favicon.png", layout="wide")

# --- 2. ESTILOS Y MÁSCARA (Rescatando la estética anterior) ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            .block-container {padding-top: 2rem;}
            
            /* Reset de sombras nativas de Streamlit */
            div[data-testid="stVerticalBlock"] > div {
                background-color: transparent !important;
                box-shadow: none !important;
                border: none !important;
            }

            [data-testid="stMetricValue"] { font-size: 45px; color: #cc0000; font-weight: bold; }
            
            .stButton>button { 
                width: 100%; 
                border-radius: 5px; 
                height: 3.5em; 
                background-color: #cc0000; 
                color: white; 
                border: none; 
                font-weight: bold; 
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
        border-top: 10px solid #cc0000; /* Línea roja Würth rescatada */
        box-shadow: 0 10px 30px rgba(0,0,0,0.05);
        margin-top: 10px;
    }}
    .explicacion {{
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

# --- 4. CARGA DE DATOS (Detección robusta de columnas) ---
@st.cache_data
def load_data():
    df_p = pd.read_excel("productos.xlsx")
    df_b = pd.read_excel("config_beneficios.xlsx")
    
    # Limpiar nombres
    df_p.columns = [str(c).strip() for c in df_p.columns]
    df_b.columns = [str(c).strip() for c in df_b.columns]
    
    # Mapeo inteligente (Busca palabras clave para evitar el KeyError)
    mapping = {}
    for col in df_b.columns:
        low = col.lower()
        if 'nombre' in low or 'comercial' in low: mapping[col] = 'Comercial'
        elif 'familia' in low: mapping[col] = 'Tecnica'
        elif 'base' in low: mapping[col] = 'Base'
        elif 'unidad' in low: mapping[col] = 'Unidad'
        elif 'tope' in low or 'max' in low: mapping[col] = 'Tope'
    
    df_b = df_b.rename(columns=mapping)
    return df_p, df_b

try:
    df_productos, df_beneficios = load_data()
except Exception as e:
    st.error(f"Error cargando archivos: {e}")
    st.stop()

# --- 5. LÓGICA DE ESTADO ---
if 'carrito' not in st.session_state: st.session_state.carrito = []
if 'paso' not in st.session_state: st.session_state.paso = 1

# --- 6. INTERFAZ ---
st.title("♻️ Plan Canje REDSTRIPE")

st.markdown("""
<div class="explicacion">
    Simulador de descuentos por reciclaje: Entrega tus herramientas viejas para una disposición responsable 
    y accede a <b>beneficios exclusivos</b> en la compra de herramientas nuevas REDSTRIPE de Würth.
</div>
""", unsafe_allow_html=True)

# Desplegable informativo (Punto 5 solicitado)
with st.expander("ℹ️ ¿Cómo funcionan nuestros descuentos?"):
    st.write("""
    - **Descuento Base:** Se otorga por el simple hecho de participar en el plan.
    - **Plus por Unidad:** Por cada herramienta vieja, sumas un porcentaje adicional.
    - **Tope Máximo:** El beneficio total nunca superará el tope de la categoría.
    - **Multicategoría:** Si traes herramientas variadas, aplicamos el **Tope más alto** para toda tu compra.
    """)

st.markdown('<div class="white-card">', unsafe_allow_html=True)

# --- PASO 1: CALCULADORA ---
if st.session_state.paso == 1:
    st.subheader("1. Cálculo de Beneficio")
    col1, col2 = st.columns(2)
    
    with col1:
        cant = st.number_input("Cantidad de herramientas a entregar:", min_value=1, step=1, value=1)
        # Verificamos que 'Comercial' exista tras el mapeo
        if 'Comercial' in df_beneficios.columns:
            opciones = df_beneficios['Comercial'].unique()
            fams_sel = st.multiselect("Tipos de herramientas que entregas:", opciones)
        else:
            st.error("No se encontró la columna de Nombres Comerciales en el Excel.")
            st.stop()
    
    if fams_sel:
        reglas = df_beneficios[df_beneficios['Comercial'].isin(fams_sel)]
        mejor_tope = reglas['Tope'].max()
        mejor_base = reglas['Base'].max()
        mejor_unidad = reglas['Unidad'].max()
        
        dto_calculado = min(mejor_base + (cant * mejor_unidad), mejor_tope)
        
        with col2:
            st.metric("BENEFICIO:", f"{dto_calculado}%")
            st.info(f"Se aplicará el tope de **{mejor_tope}%** basado en tu selección.")
        
        st.write("---")
        if st.button("Confirmar Beneficio y Agregar Productos ➔"):
            st.session_state.temp_dto = dto_calculado
            st.session_state.temp_cant = cant
            st.session_state.paso = 2
            st.rerun()
    else:
        st.warning("Selecciona al menos una categoría para calcular el descuento.")

# --- PASO 2: CARRITO MULTI-PRODUCTO ---
else:
    st.subheader("2. Detalle de Compra (Carrito)")
    
    c_left, c_right = st.columns([1.2, 0.8])
    
    with c_left:
        # Buscador SAP solicitado
        busqueda = st.text_input("🔍 Buscar por Código SAP o Nombre")
        
        df_f = df_productos[
            (df_productos['Código del producto'].astype(str).str.contains(busqueda)) |
            (df_productos['Nombre del producto'].str.contains(busqueda, case=False))
        ] if busqueda else pd.DataFrame()

        if not df_f.empty:
            item = st.selectbox("Seleccione el producto encontrado:", df_f['Nombre del producto'].unique())
            sap_code = df_f[df_f['Nombre del producto'] == item]['Código del producto'].values[0]
            p_lista = st.number_input("Precio de Lista (UYU)", min_value=0.0, step=1.0)
            
            if st.button("➕ Añadir al Carrito"):
                dto = st.session_state.temp_dto
                ahorro_item = p_lista * (dto / 100)
                st.session_state.carrito.append({
                    "SAP": sap_code, "Producto": item, "Lista": p_lista, "Ahorro": ahorro_item, "Final": p_lista - ahorro_item
                })
                st.success(f"Agregado: {item}")
        elif busqueda:
            st.error("No se encontraron coincidencias.")

    with c_right:
        st.write("### Resumen")
        if st.session_state.carrito:
            df_car = pd.DataFrame(st.session_state.carrito)
            st.table(df_car[['Producto', 'Final']])
            t_final = df_car['Final'].sum()
            t_ahorro = df_car['Ahorro'].sum()
            
            st.metric("TOTAL A PAGAR", f"${t_final:,.2f}")
            st.write(f"🎁 Ahorro Total: **${t_ahorro:,.2f}**")
            
            if st.button("🗑️ Vaciar Carrito"):
                st.session_state.carrito = []
                st.rerun()

    st.divider()
    b_col1, b_col2 = st.columns(2)
    with b_col1:
        if st.button("⬅ Volver al Simulador"):
            st.session_state.paso = 1
            st.session_state.carrito = []
            st.rerun()
    with b_col2:
        if st.button("📥 Generar Ticket PDF"):
            # Aquí se puede expandir la lógica del PDF para listar todos los items del carrito
            st.success("Ticket listo (Simulación)")

st.markdown('</div>', unsafe_allow_html=True)
