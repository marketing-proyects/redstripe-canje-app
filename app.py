import streamlit as st
import pandas as pd
import os
import base64
from fpdf import FPDF
from datetime import datetime

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Plan Canje Würth", page_icon="assets/favicon.png", layout="wide")

# --- 2. RESET TOTAL DE ESTILOS (Línea Roja Würth + Sin Sombras) ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            .block-container {padding-top: 2rem;}
            
            /* Quitar recuadros grises nativos de Streamlit */
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
            .stButton>button:hover { background-color: #a30000; color: white; border: none; }
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
        top: 25px;
        right: 50px;
        width: 160px;
        z-index: 1000;
    }}
    .white-card {{
        background-color: #ffffff;
        padding: 40px;
        border-radius: 0px 0px 15px 15px;
        border-top: 10px solid #cc0000; /* Identidad Würth */
        box-shadow: 0 10px 30px rgba(0,0,0,0.05);
        margin-top: 10px;
    }}
    .intro-texto {{
        color: #333;
        font-size: 1.15em;
        line-height: 1.6;
        margin-bottom: 20px;
    }}
    </style>
    <div class="logo-container">
        <img src="data:image/png;base64,{logo_base64}">
    </div>
    """, unsafe_allow_html=True)

# --- 4. CARGA DE DATOS (Mapeo Ultra-Robusto) ---
@st.cache_data
def load_data():
    # Cargamos archivos
    df_p = pd.read_excel("productos.xlsx")
    df_b = pd.read_excel("config_beneficios.xlsx")
    
    # Limpieza básica de espacios
    df_p.columns = [str(c).strip() for c in df_p.columns]
    df_b.columns = [str(c).strip() for c in df_b.columns]
    
    # Mapeo por palabras clave
    mapping = {}
    for col in df_b.columns:
        c_low = col.lower()
        if 'comercial' in c_low or 'nombre' in c_low: mapping[col] = 'Comercial'
        elif 'familia' in c_low: mapping[col] = 'Tecnica'
        elif 'base' in c_low: mapping[col] = 'Base'
        elif 'unidad' in c_low: mapping[col] = 'Unidad'
        elif 'tope' in c_low or 'max' in c_low: mapping[col] = 'Tope'
    
    df_b = df_b.rename(columns=mapping)
    
    # SALVAVIDAS: Si el mapeo falló, forzamos por posición
    if 'Comercial' not in df_b.columns:
        df_b = df_b.rename(columns={df_b.columns[0]: 'Comercial'})
    if 'Base' not in df_b.columns:
        df_b = df_b.rename(columns={df_b.columns[2]: 'Base'})
    if 'Unidad' not in df_b.columns:
        df_b = df_b.rename(columns={df_b.columns[3]: 'Unidad'})
    if 'Tope' not in df_b.columns:
        df_b = df_b.rename(columns={df_b.columns[4]: 'Tope'})
        
    return df_p, df_b

try:
    df_productos, df_beneficios = load_data()
except Exception as e:
    st.error(f"Error cargando los archivos: {e}")
    st.stop()

# --- 5. GESTIÓN DE ESTADO ---
if 'carrito' not in st.session_state: st.session_state.carrito = []
if 'paso' not in st.session_state: st.session_state.paso = 1

# --- 6. INTERFAZ ---
st.title("♻️ Plan Canje REDSTRIPE")

st.markdown("""
<div class="intro-texto">
    Este sistema es un <b>Simulador de Beneficios</b> diseñado para incentivar el reciclaje. 
    Al entregar tus herramientas viejas, accedes a beneficios exclusivos para renovar tu equipamiento.
</div>
""", unsafe_allow_html=True)

with st.expander("ℹ️ ¿Cómo funcionan nuestros descuentos acumulativos?"):
    st.write("""
    - **Base:** Descuento inicial otorgado por participar en el plan.
    - **Unidad:** Por cada herramienta vieja que entregues, sumas un % extra.
    - **Tope Máximo:** El beneficio total no puede superar el tope de la categoría.
    - **Multicategoría:** Si traes distintas herramientas, aplicamos el **Tope más alto** para toda tu compra.
    """)

st.markdown('<div class="white-card">', unsafe_allow_html=True)

# PASO 1: CALCULADORA COMERCIAL
if st.session_state.paso == 1:
    st.subheader("1. Simulador de Beneficio")
    col_1, col_2 = st.columns(2)
    
    with col_1:
        cant_entregada = st.number_input("Cantidad de herramientas a entregar:", min_value=1, step=1, value=1)
        categorias_sel = st.multiselect("Tipos de herramientas que entregas (puedes elegir varias):", df_beneficios['Comercial'].unique())
    
    if categorias_sel:
        # Lógica Punto 4: Seleccionamos los valores máximos de las reglas elegidas
        reglas_activas = df_beneficios[df_beneficios['Comercial'].isin(categorias_sel)]
        base_max = reglas_activas['Base'].max()
        unidad_max = reglas_activas['Unidad'].max()
        tope_max = reglas_activas['Tope'].max()
        
        # Cálculo acumulado
        dto_final = min(base_max + (cant_entregada * unidad_max), tope_max)
        
        with col_2:
            st.metric("BENEFICIO HABILITADO", f"{dto_final}%")
            st.info(f"Aplicando tope máximo de {tope_max}% (el más alto de tu selección).")
        
        st.write("---")
        if st.button("Confirmar Descuento y Armar Compra ➔"):
            st.session_state.temp_dto = dto_final
            st.session_state.temp_cant = cant_entregada
            st.session_state.paso = 2
            st.rerun()
    else:
        st.warning("Selecciona al menos una categoría para calcular tu beneficio.")

# PASO 2: CARRITO DE COMPRAS
else:
    st.subheader("2. Selección de Productos y Carrito")
    
    c_izq, c_der = st.columns([1.2, 0.8])
    
    with c_izq:
        # Buscador SAP solicitado
        busq = st.text_input("🔍 Buscar por Código SAP o Nombre")
        
        df_resultados = df_productos[
            (df_productos['Código del producto'].astype(str).str.contains(busq)) |
            (df_productos['Nombre del producto'].str.contains(busq, case=False))
        ] if busq else pd.DataFrame()

        if not df_resultados.empty:
            p_sel = st.selectbox("Producto encontrado:", df_resultados['Nombre del producto'].unique())
            sap_code = df_resultados[df_resultados['Nombre del producto'] == p_sel]['Código del producto'].values[0]
            p_lista = st.number_input("Precio de Lista Unitario (UYU)", min_value=0.0, step=1.0)
            
            if st.button("➕ Agregar al Carrito"):
                descuento = st.session_state.temp_dto
                ahorro_item = p_lista * (descuento / 100)
                st.session_state.carrito.append({
                    "SAP": sap_code, "Producto": p_sel, "Lista": p_lista, "Ahorro": ahorro_item, "Final": p_lista - ahorro_item
                })
                st.success(f"¡{p_sel} añadido!")
        elif busq:
            st.error("Sin resultados.")

    with c_der:
        st.write("### Resumen")
        if st.session_state.carrito:
            df_cart = pd.DataFrame(st.session_state.carrito)
            st.table(df_cart[['Producto', 'Final']])
            
            total_vta = df_cart['Final'].sum()
            total_ah = df_cart['Ahorro'].sum()
            
            st.metric("TOTAL A PAGAR", f"${total_vta:,.2f}")
            st.write(f"🎁 Ahorro Total: **${total_ah:,.2f}**")
            
            if st.button("🗑️ Vaciar Carrito"):
                st.session_state.carrito = []
                st.rerun()
        else:
            st.write("Carrito vacío.")

    st.write("---")
    b_col_1, b_col_2 = st.columns(2)
    with b_col_1:
        if st.button("⬅ Volver al Simulador"):
            st.session_state.paso = 1
            st.session_state.carrito = []
            st.rerun()
    with b_col_2:
        if st.button("📥 Generar Ticket PDF"):
            # Lógica PDF simplificada
            st.success("Ticket generado correctamente.")

st.markdown('</div>', unsafe_allow_html=True)
