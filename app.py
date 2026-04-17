import streamlit as st
import pandas as pd
import os
import base64
from fpdf import FPDF
from datetime import datetime

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Plan Canje Würth", page_icon="assets/favicon.png", layout="wide")

# --- 2. RESET TOTAL DE ESTILOS (ADIÓS RECUADROS GRISES) ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            .block-container {padding-top: 1rem;}

            /* Eliminación radical de sombras y fondos automáticos de Streamlit */
            div[data-testid="stVerticalBlock"] > div {
                background-color: transparent !important;
                box-shadow: none !important;
                border: none !important;
            }
            
            .stMarkdown div {
                background-color: transparent !important;
                box-shadow: none !important;
            }

            /* Estilo de métricas (Descuento) */
            [data-testid="stMetricValue"] { font-size: 50px; color: #cc0000; font-weight: bold; }
            
            /* Botones estilo Würth */
            .stButton>button { 
                width: 100%; 
                border-radius: 4px; 
                height: 3.5em; 
                background-color: #cc0000; 
                color: white; 
                border: none; 
                font-weight: bold; 
                font-size: 16px;
            }
            .stButton>button:hover { background-color: #a30000; color: white; border: none; }
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- 3. LOGO Y CONTENEDOR VISUAL ---
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
        border-radius: 0px 0px 12px 12px;
        border-top: 10px solid #cc0000; /* La línea roja que nos gusta */
        box-shadow: 0 10px 25px rgba(0,0,0,0.05);
        margin-top: 5px;
    }}
    .intro-text {{
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

# --- 4. CARGA DE DATOS ---
@st.cache_data
def load_data():
    df_p = pd.read_excel("productos.xlsx")
    df_b = pd.read_excel("config_beneficios.xlsx")
    df_p.columns = [str(c).strip() for c in df_p.columns]
    df_b.columns = [str(c).strip() for c in df_b.columns]
    
    mapping = {}
    for c in df_b.columns:
        low = c.lower()
        if 'familia' in low: mapping[c] = 'Familia'
        elif 'base' in low: mapping[c] = 'Base'
        elif 'unidad' in low: mapping[c] = 'Unidad'
        elif 'tope' in low or 'max' in low: mapping[c] = 'Tope'
    df_b = df_b.rename(columns=mapping)
    return df_p, df_b

df_productos, df_beneficios = load_data()

if 'paso' not in st.session_state:
    st.session_state.paso = 1

# --- 5. INTERFAZ ---
st.title("♻️ Plan Canje REDSTRIPE")

# Explicación limpia (sin recuadros)
st.markdown("""
<div class="intro-text">
    Este sistema es un <b>Simulador de Descuentos por Reciclaje</b>. Incentivamos a nuestros clientes a entregar 
    sus herramientas viejas para asegurar un proceso de disposición responsable, otorgando a cambio 
    <b>beneficios exclusivos</b> en la compra de nuevas herramientas Würth.
</div>
""", unsafe_allow_html=True)

# Inicio de la tarjeta blanca Würth
st.markdown('<div class="white-card">', unsafe_allow_html=True)

if st.session_state.paso == 1:
    st.subheader("1. Cálculo de Beneficio")
    col1, col2 = st.columns(2)
    
    with col1:
        cant = st.number_input("Herramientas viejas entregadas:", min_value=1, step=1, value=1)
        fam = st.selectbox("Familia del producto a adquirir:", df_beneficios['Familia'].unique())
    
    regla = df_beneficios[df_beneficios['Familia'] == fam].iloc[0]
    dto = min(regla['Base'] + (cant * regla['Unidad']), regla['Tope'])
    
    with col2:
        st.metric("TU DESCUENTO:", f"{dto}%")
        st.write(f"Al entregar **{cant}** herramientas, activas el beneficio máximo para la familia **{fam}**.")
    
    st.write("")
    if st.button("Aplicar beneficio y ver productos ➔"):
        st.session_state.temp_dto = dto
        st.session_state.temp_cant = cant
        st.session_state.paso = 2
        st.rerun()

else:
    st.subheader("2. Detalle de Compra y Ahorro")
    c3, c4 = st.columns(2)
    
    with c3:
        nro = st.text_input("Nro. Cliente / RUT")
        nom = st.text_input("Nombre del Comprador")
        mod = st.selectbox("Modelo REDSTRIPE", sorted(df_productos['Nombre del modelo'].unique()))
        items = df_productos[df_productos['Nombre del modelo'] == mod]
        prod = st.selectbox("Producto específico", items['Nombre del producto'].unique())
        sap = items[items['Nombre del producto'] == prod]['Código del producto'].values[0]
        st.write(f"**Código SAP:** `{sap}`")
        
    with c4:
        # El vendedor ingresa el precio del sistema para cerrar la venta
        precio_l = st.number_input("Precio de Lista Unitario (UYU)", min_value=0.0, step=1.0)
        final = precio_l * (1 - st.session_state.temp_dto / 100)
        ahorro = precio_l - final
        
        st.markdown(f"### Precio Final: <span style='color:#cc0000;'>${final:,.2f}</span>", unsafe_allow_html=True)
        st.write(f"💰 Ahorro total por reciclaje: **${ahorro:,.2f}**")
        st.write(f"📊 Bonificación aplicada: **{st.session_state.temp_dto}%**")

    st.write("---")
    b1, b2 = st.columns(2)
    with b1:
        if st.button("⬅ Volver a calcular"):
            st.session_state.paso = 1
            st.rerun()
    with b2:
        if st.button("📥 Generar Ticket PDF"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.set_text_color(204, 0, 0)
            pdf.cell(0, 15, "PLAN CANJE WÜRTH - TICKET DE BENEFICIO", ln=True, align='C')
            pdf.ln(5)
            pdf.set_font("Arial", '', 11)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(0, 8, f"Cliente: {nro} | Fecha: {datetime.now().strftime('%d/%m/%Y')}", ln=True)
            pdf.cell(0, 8, f"Producto: {prod} (SAP: {sap})", ln=True)
            pdf.cell(0, 8, f"Unidades entregadas para reciclaje: {st.session_state.temp_cant}", ln=True)
            pdf.ln(5)
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, f"Precio Lista: ${precio_l:,.2f}", ln=True)
            pdf.cell(0, 10, f"Ahorro Plan Canje ({st.session_state.temp_dto}%): -${ahorro:,.2f}", ln=True)
            pdf.set_text_color(204, 0, 0)
            pdf.cell(0, 15, f"TOTAL A PAGAR: ${final:,.2f}", ln=True)
            
            pdf_bytes = pdf.output(dest='S').encode('latin-1')
            b64 = base64.b64encode(pdf_bytes).decode()
            st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="Canje_Wurth.pdf" style="display:block; text-align:center; padding:12px; background-color:#28a745; color:white; border-radius:4px; text-decoration:none; font-weight:bold;">📥 DESCARGAR COMPROBANTE</a>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
