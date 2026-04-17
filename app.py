import streamlit as st
import pandas as pd
import os
import base64
from fpdf import FPDF
from datetime import datetime

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Plan Canje Würth", page_icon="assets/favicon.png", layout="wide")

# --- 2. ESTILOS PROFESIONALES ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            .block-container {padding-top: 1rem;}
            [data-testid="stMetricValue"] { font-size: 45px; color: #cc0000; font-weight: bold; }
            .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #cc0000; color: white; border: none; font-weight: bold; }
            .stButton>button:hover { background-color: #a30000; color: white; }
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- 3. FUNCIONES DE APOYO ---
def get_base64(file_path):
    if file_path and os.path.exists(file_path):
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

# Carga del logo (Debe estar en la raíz del repositorio)
logo_base64 = get_base64("logo_wurth.png")

st.markdown(f"""
    <style>
    .logo-container {{
        position: fixed;
        top: 20px;
        right: 40px;
        width: 150px;
        z-index: 1000;
    }}
    .main-card {{
        background-color: #ffffff;
        padding: 40px;
        border-radius: 15px;
        border-top: 8px solid #cc0000;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        margin-top: 20px;
    }}
    .texto-explicativo {{
        color: #444;
        font-size: 1.2em;
        line-height: 1.6;
        margin-bottom: 30px;
    }}
    </style>
    <div class="logo-container">
        <img src="data:image/png;base64,{logo_base64}">
    </div>
    """, unsafe_allow_html=True)

# --- 4. CARGA DE DATOS ---
@st.cache_data
def load_data():
    # Usamos los archivos que ya tienes en el repo
    df_p = pd.read_excel("productos.xlsx")
    df_b = pd.read_excel("config_beneficios.xlsx")
    
    # Limpieza de nombres de columnas
    df_p.columns = [str(c).strip() for c in df_p.columns]
    df_b.columns = [str(c).strip() for c in df_b.columns]
    
    # Mapeo flexible para asegurar que funcione sin importar el nombre exacto
    nuevos = {}
    for c in df_b.columns:
        c_low = c.lower()
        if 'familia' in c_low: nuevos[c] = 'Familia'
        elif 'base' in c_low: nuevos[c] = 'Base'
        elif 'unidad' in c_low: nuevos[c] = 'Unidad'
        elif 'tope' in c_low or 'max' in c_low: nuevos[c] = 'Tope'
    
    df_b = df_b.rename(columns=nuevos)
    return df_p, df_b

try:
    df_productos, df_beneficios = load_data()
except Exception as e:
    st.error(f"Error cargando archivos: {e}")
    st.stop()

# --- 5. LÓGICA DE FLUJO ---
if 'paso' not in st.session_state:
    st.session_state.paso = 1

# --- 6. INTERFAZ ---
st.title("♻️ Plan Canje REDSTRIPE")

# Explicación limpia (reemplaza rectángulos grises anteriores)
st.markdown("""
<div class="texto-explicativo">
    Simulador de descuentos por reciclaje: Entrega tus herramientas viejas para una disposición responsable 
    y accede a <b>beneficios exclusivos</b> en la compra de herramientas nuevas de la línea REDSTRIPE de Würth.
</div>
""", unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    
    # PASO 1: LA CALCULADORA (Argumento de Venta)
    if st.session_state.paso == 1:
        st.subheader("1. Calcula tu Beneficio")
        c1, c2 = st.columns([1, 1])
        
        with c1:
            cant_viejas = st.number_input("Herramientas viejas entregadas:", min_value=1, step=1, value=1)
            fam_sel = st.selectbox("Familia del producto a comprar:", df_beneficios['Familia'].unique())
        
        regla = df_beneficios[df_beneficios['Familia'] == fam_sel].iloc[0]
        dto_calculado = min(regla['Base'] + (cant_viejas * regla['Unidad']), regla['Tope'])
        
        with c2:
            st.metric("BONIFICACIÓN", f"{dto_calculado}%")
            st.write(f"✅ ¡Excelente! Por reciclar {cant_viejas} unidades, tienes un descuento especial en la familia {fam_sel}.")
        
        if st.button("Aplicar descuento y seleccionar productos ➔"):
            st.session_state.temp_dto = dto_calculado
            st.session_state.temp_cant = cant_viejas
            st.session_state.paso = 2
            st.rerun()

    # PASO 2: CIERRE COMERCIAL
    else:
        st.subheader("2. Detalle de la Operación")
        c3, c4 = st.columns(2)
        
        with c3:
            nro_cliente = st.text_input("Nro. Cliente / RUT")
            nombre = st.text_input("Nombre del Cliente")
            
            modelo_sel = st.selectbox("Modelo REDSTRIPE", sorted(df_productos['Nombre del modelo'].unique()))
            prods = df_productos[df_productos['Nombre del modelo'] == modelo_sel]
            prod_sel = st.selectbox("Producto", prods['Nombre del producto'].unique())
            codigo_sap = prods[prods['Nombre del producto'] == prod_sel]['Código del producto'].values[0]
            st.write(f"**Código SAP:** `{codigo_sap}`")
            
        with c4:
            # Entrada de precio para ver el ahorro real
            precio_lista = st.number_input("Precio de Lista Unitario (UYU)", min_value=0.0, step=1.0)
            dto = st.session_state.temp_dto
            
            ahorro = precio_lista * (dto / 100)
            precio_final = precio_lista - ahorro
            
            st.markdown(f"### Precio Final: <span style='color:#cc0000;'>${precio_final:,.2f}</span>", unsafe_allow_html=True)
            st.write(f"🎁 Ahorro por reciclaje: **${ahorro:,.2f}**")
            st.write(f"📊 Descuento aplicado: **{dto}%**")

        st.divider()
        cb1, cb2 = st.columns(2)
        with cb1:
            if st.button("⬅ Volver"):
                st.session_state.paso = 1
                st.rerun()
        with cb2:
            if st.button("📥 Emitir Ticket PDF"):
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", 'B', 16)
                pdf.set_text_color(204, 0, 0)
                pdf.cell(0, 15, "PLAN CANJE WÜRTH - TICKET DE BENEFICIO", ln=True, align='C')
                pdf.ln(5)
                pdf.set_font("Arial", '', 11)
                pdf.set_text_color(0,0,0)
                pdf.cell(0, 8, f"Cliente: {nro_cliente} | Fecha: {datetime.now().strftime('%d/%m/%Y')}", ln=True)
                pdf.cell(0, 8, f"Producto: {prod_sel} (SAP: {codigo_sap})", ln=True)
                pdf.ln(5)
                pdf.set_font("Arial", 'B', 12)
                pdf.cell(0, 10, f"Precio Lista: ${precio_lista:,.2f}", ln=True)
                pdf.cell(0, 10, f"Ahorro Canje ({dto}%): -${ahorro:,.2f}", ln=True)
                pdf.set_text_color(204, 0, 0)
                pdf.cell(0, 10, f"TOTAL A PAGAR: ${precio_final:,.2f}", ln=True)
                
                pdf_bytes = pdf.output(dest='S').encode('latin-1')
                b64 = base64.b64encode(pdf_bytes).decode()
                st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="Canje_Wurth.pdf" style="display:block; text-align:center; padding:10px; background-color:#28a745; color:white; border-radius:5px; text-decoration:none;">📥 DESCARGAR TICKET</a>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
