import streamlit as st
import pandas as pd
import os
import base64
from fpdf import FPDF
from datetime import datetime

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Plan Canje Würth", page_icon="assets/favicon.png", layout="wide")

# --- 2. ESTILOS (Identidad Würth & Eliminación de Sombras) ---
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
    # Mapeo robusto por posición para evitar errores de nombres en el Excel
    df_b = df_b.rename(columns={df_b.columns[0]: 'Comercial', df_b.columns[2]: 'Base', df_b.columns[3]: 'Unidad', df_b.columns[4]: 'Tope'})
    return df_p, df_b

try:
    df_productos, df_beneficios = load_data()
except Exception as e:
    st.error(f"Error cargando archivos: {e}")
    st.stop()

# Gestión de Carrito y Navegación
if 'carrito' not in st.session_state: st.session_state.carrito = []
if 'paso' not in st.session_state: st.session_state.paso = 1

# --- 5. INTERFAZ PRINCIPAL ---
st.title("♻️ Plan Canje REDSTRIPE")

with st.expander("ℹ️ ¿Cómo funcionan nuestros descuentos acumulativos?"):
    st.write("""
    - **Base:** Descuento inicial por participar.
    - **Unidad:** Por cada herramienta vieja, sumamos un % extra.
    - **Tope Máximo:** El beneficio total no superará el tope de la categoría.
    - **Multicategoría:** Si traes distintas herramientas, aplicamos el **Tope más alto** entre ellas.
    """)

st.markdown('<div class="white-card">', unsafe_allow_html=True)

# --- FASE 1: CALCULADORA DETALLADA ---
if st.session_state.paso == 1:
    st.subheader("1. Detalle de herramientas a entregar")
    col_in, col_res = st.columns([1.2, 0.8])
    
    with col_in:
        cats_selec = st.multiselect("Categorías que entrega el cliente:", df_beneficios['Comercial'].unique())
        
        total_u = 0
        if cats_selec:
            st.write("---")
            for cat in cats_selec:
                c = st.number_input(f"Cantidad de '{cat}':", min_value=1, step=1, value=1, key=f"n_{cat}")
                total_u += c
    
    if cats_selec:
        reglas = df_beneficios[df_beneficios['Comercial'].isin(cats_selec)]
        m_base, m_unidad, m_tope = reglas['Base'].max(), reglas['Unidad'].max(), reglas['Tope'].max()
        
        dto_calc = min(m_base + (total_u * m_unidad), m_tope)
        
        with col_res:
            st.metric("DESCUENTO TOTAL", f"{dto_calc}%")
            st.markdown(f"**Resumen del beneficio:**\n* Unidades: {total_u}\n* Base: {m_base}%\n* Tope Aplicado: {m_tope}%")
        
        if st.button("Confirmar y Pasar a la Compra ➔"):
            st.session_state.temp_dto = dto_calc
            st.session_state.paso = 2
            st.rerun()
    else:
        st.info("Selecciona qué herramientas entrega el cliente para calcular el beneficio.")

# --- FASE 2: CARRITO CON BUSCADOR Y MENÚ ALFABÉTICO ---
else:
    st.subheader("2. Selección de Productos (Menú A-Z)")
    
    c_selec, c_resumen = st.columns([1.1, 0.9])
    
    with c_selec:
        # 1. Buscador (opcional para filtrar la lista)
        busq = st.text_input("🔍 Buscar por Código SAP o Nombre (Opcional)")
        
        # Filtrar el dataframe según la búsqueda
        if busq:
            df_filtrado = df_productos[
                (df_productos['Código del producto'].astype(str).str.contains(busq)) |
                (df_productos['Nombre del producto'].str.contains(busq, case=False)) |
                (df_productos['Nombre del modelo'].str.contains(busq, case=False))
            ]
        else:
            df_filtrado = df_productos

        # 2. Menú Desplegable Alfabético de Modelos
        modelos_az = sorted(df_filtrado['Nombre del modelo'].dropna().unique())
        
        if modelos_az:
            mod_sel = st.selectbox("Seleccione el Modelo (Orden A-Z):", modelos_az)
            
            # 3. Menú de Variantes del modelo elegido
            variantes = df_filtrado[df_filtrado['Nombre del modelo'] == mod_sel]
            prod_final = st.selectbox("Producto / Medida específica:", variantes['Nombre del producto'].unique())
            
            sap_final = variantes[variantes['Nombre del producto'] == prod_final]['Código del producto'].values[0]
            st.write(f"**Código SAP:** `{sap_final}`")
            
            precio_l = st.number_input("Precio de Lista (UYU)", min_value=0.0, step=1.0)
            
            if st.button("➕ Agregar al Carrito"):
                d = st.session_state.temp_dto
                ahorro = precio_l * (d / 100)
                st.session_state.carrito.append({
                    "SAP": sap_final, "Producto": prod_final, "Lista": precio_l, "Ahorro": ahorro, "Final": precio_l - ahorro
                })
                st.success(f"¡Agregado!")
        else:
            st.error("No se encontraron coincidencias en el catálogo.")

    with c_resumen:
        st.write("### Detalle de Compra")
        if st.session_state.carrito:
            df_c = pd.DataFrame(st.session_state.carrito)
            st.dataframe(df_c[['Producto', 'Final']], use_container_width=True, hide_index=True)
            st.metric("TOTAL A PAGAR", f"${df_c['Final'].sum():,.2f}")
            st.write(f"🎁 Ahorro Total: **${df_c['Ahorro'].sum():,.2f}**")
            if st.button("🗑️ Vaciar Carrito"):
                st.session_state.carrito = []
                st.rerun()
        else:
            st.write("El carrito está vacío.")

    st.divider()
    b_back, b_pdf = st.columns(2)
    with b_back:
        if st.button("⬅ Volver al Simulador"):
            st.session_state.paso = 1
            st.session_state.carrito = []
            st.rerun()
    with b_pdf:
        if st.button("📥 Generar Ticket PDF"): st.success("Ticket generado correctamente.")

st.markdown('</div>', unsafe_allow_html=True)
