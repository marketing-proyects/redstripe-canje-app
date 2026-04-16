import streamlit as st
import pandas as pd
import os
import random
import base64
from fpdf import FPDF
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Plan Canje REDSTRIPE", page_icon="assets/favicon.png", layout="wide")

# --- FUNCIONES DE SOPORTE ---
def get_base64(file_path):
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

def get_random_bg():
    bg_dir = "assets/fondos"
    if os.path.exists(bg_dir):
        fondos = [f for f in os.listdir(bg_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        if fondos:
            return os.path.join(bg_dir, random.choice(fondos))
    return None

# --- CARGA DE DATOS ---
@st.cache_data
def load_data():
    # Cargar productos
    df_prod = pd.read_excel("productos.xlsx")
    # Cargar beneficios
    df_ben = pd.read_excel("config_beneficios.xlsx")
    return df_prod, df_ben

try:
    df_productos, df_beneficios = load_data()
except Exception as e:
    st.error(f"Error cargando archivos: {e}. Revisa que productos.xlsx y config_beneficios.xlsx estén en la raíz.")
    st.stop()

# --- ESTILOS CSS ---
bg_image = get_random_bg()
bg_base64 = get_base64(bg_image) if bg_image else ""

st.markdown(f"""
    <style>
    .stApp {{
        background-image: url("data:image/png;base64,{bg_base64}");
        background-size: cover;
        background-attachment: fixed;
    }}
    .main-card {{
        background-color: rgba(255, 255, 255, 0.9);
        padding: 20px;
        border-radius: 15px;
        border-left: 5px solid #cc0000;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- INTERFAZ ---
st.title("♻️ Plan Canje REDSTRIPE")
st.subheader("Calculadora de Beneficios para Reciclaje")

with st.container():
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        nro_cliente = st.text_input("Número de Cliente")
        nombre_comprador = st.text_input("Nombre del Comprador")
    
    with col2:
        cant_viejas = st.number_input("Herramientas entregadas para reciclaje", min_value=1, step=1)
        # Aquí filtramos las familias únicas del excel de beneficios
        familia_sel = st.selectbox("Familia de producto a comprar", df_beneficios['Familia'].unique())

    st.divider()

    # Lógica de Selección de Producto
    # Asumimos que en productos.xlsx hay una forma de vincular con la Familia. 
    # Si no hay columna familia, filtramos por modelo.
    modelos_filtrados = df_productos['Nombre del modelo'].unique()
    modelo_sel = st.selectbox("Seleccione el Modelo", modelos_filtrados)
    
    productos_finales = df_productos[df_productos['Nombre del modelo'] == modelo_sel]
    producto_sel = st.selectbox("Variante específica", productos_finales['Nombre del producto'].unique())
    
    row_prod = productos_finales[productos_finales['Nombre del producto'] == producto_sel].iloc[0]
    codigo_prod = row_prod['Código del producto']
    
    st.info(f"**Código seleccionado:** {codigo_prod}")

    # --- CÁLCULO DE DESCUENTO ---
    datos_ben = df_beneficios[df_beneficios['Familia'] == familia_sel].iloc[0]
    dto_base = datos_ben['Dto. Base (%)']
    dto_unidad = datos_ben['Dto. por Unidad (%)']
    tope_max = datos_ben['Tope Máximo (%)']
    
    # Cálculo: Base + (Unidades * Incremento)
    dto_calculado = dto_base + (cant_viejas * dto_unidad)
    dto_final = min(dto_calculado, tope_max)

    st.metric(label="Descuento Total Aplicable", value=f"{dto_final}%", delta=f"Tope máximo: {tope_max}%")

    if st.button("Generar Comprobante de Canje"):
        # Lógica PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, "COMPROBANTE PLAN CANJE REDSTRIPE", ln=True, align='C')
        pdf.ln(10)
        
        pdf.set_font("Arial", '', 12)
        pdf.cell(0, 10, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
        pdf.cell(0, 10, f"Cliente: {nro_cliente} - {nombre_comprador}", ln=True)
        pdf.ln(5)
        
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "Detalle del Canje:", ln=True)
        pdf.set_font("Arial", '', 12)
        pdf.cell(0, 10, f"- Unidades entregadas para reciclaje: {cant_viejas}", ln=True)
        pdf.cell(0, 10, f"- Familia beneficiada: {familia_sel}", ln=True)
        pdf.cell(0, 10, f"- Producto a adquirir: {producto_sel}", ln=True)
        pdf.cell(0, 10, f"- Codigo: {codigo_prod}", ln=True)
        
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 14)
        pdf.set_text_color(204, 0, 0)
        pdf.cell(0, 10, f"DESCUENTO OTORGADO: {dto_final}%", ln=True, align='C')
        
        pdf_output = pdf.output(dest='S').encode('latin-1')
        b64_pdf = base64.b64encode(pdf_output).decode('utf-8')
        href = f'<a href="data:application/octet-stream;base64,{b64_pdf}" download="Canje_{codigo_prod}.pdf">Descargar Ticket de Canje</a>'
        st.markdown(href, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
