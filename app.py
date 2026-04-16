import streamlit as st
import pandas as pd
import os
import random
import base64
from fpdf import FPDF
from datetime import datetime

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Plan Canje REDSTRIPE", 
    page_icon="assets/favicon.png", 
    layout="wide"
)

# --- 2. MÁSCARA PROFESIONAL (OCULTAR MENÚS) ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            .block-container {padding-top: 2rem;} 
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- 3. SOPORTE DE ARCHIVOS Y ESTÉTICA ---
def get_base64(file_path):
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

def get_random_bg():
    bg_dir = "assets/fondos"
    current_dir = bg_dir if os.path.exists(bg_dir) else "."
    fondos = [f for f in os.listdir(current_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    return os.path.join(current_dir, random.choice(fondos)) if fondos else None

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
        background-color: rgba(255, 255, 255, 0.95);
        padding: 30px;
        border-radius: 15px;
        border-left: 10px solid #cc0000;
        box-shadow: 0 10px 25px rgba(0,0,0,0.4);
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 4. CARGA Y LIMPIEZA DE DATOS ---
@st.cache_data
def load_data():
    # Cargar y limpiar productos
    df_p = pd.read_excel("productos.xlsx")
    df_p.columns = [c.strip() for c in df_p.columns]
    
    # Cargar y limpiar beneficios
    df_b = pd.read_excel("config_beneficios.xlsx")
    df_b.columns = [c.strip() for c in df_b.columns]
    
    return df_p, df_b

try:
    df_productos, df_beneficios = load_data()
    
    # Validar columnas críticas para evitar KeyError
    cols_requeridas = ['Familia', 'Dto. Base (%)', 'Dto. por Unidad (%)', 'Tope Máximo (%)']
    for col in cols_requeridas:
        if col not in df_beneficios.columns:
            st.error(f"Error: No se encuentra la columna '{col}' en config_beneficios.xlsx")
            st.stop()
            
except Exception as e:
    st.error(f"Error crítico: {e}")
    st.stop()

# --- 5. INTERFAZ ---
st.title("♻️ Plan Canje REDSTRIPE")
st.markdown("### Sistema de Gestión de Descuentos por Reciclaje")

with st.container():
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        nro_cliente = st.text_input("Número de Cliente / RUT")
        nombre_persona = st.text_input("Nombre de quien realiza la compra")
    with c2:
        cant_viejas = st.number_input("Herramientas viejas entregadas", min_value=1, step=1)
        familia_sel = st.selectbox("Familia del producto nuevo", df_beneficios['Familia'].unique())

    st.divider()

    c3, c4 = st.columns(2)
    with c3:
        modelos = sorted(df_productos['Nombre del modelo'].unique())
        mod_sel = st.selectbox("Modelo REDSTRIPE", modelos)
    with c4:
        prods_filt = df_productos[df_productos['Nombre del modelo'] == mod_sel]
        prod_sel = st.selectbox("Variante específica", prods_filt['Nombre del producto'].unique())
        cod_sap = prods_filt[prods_filt['Nombre del producto'] == prod_sel]['Código del producto'].values[0]
        st.caption(f"Código Identificado: **{cod_sap}**")

    # --- 6. CÁLCULO DE LÓGICA COMERCIAL ---
    regla = df_beneficios[df_beneficios['Familia'] == familia_sel].iloc[0]
    
    calc_dto = regla['Dto. Base (%)'] + (cant_viejas * regla['Dto. por Unidad (%)'])
    dto_final = min(calc_dto, regla['Tope Máximo (%)'])

    st.divider()
    res1, res2 = st.columns(2)
    with res1:
        st.metric("DESCUENTO APLICABLE", f"{dto_final}%")
    with res2:
        st.info(f"Regla aplicada: {regla['Dto. Base (%)']}% inicial + {regla['Dto. por Unidad (%)']}% x cada unidad entregada.")

    # --- 7. TICKET PDF ---
    if st.button("Emitir Comprobante de Beneficio"):
        if not nro_cliente or not nombre_persona:
            st.warning("Debe ingresar los datos del cliente antes de continuar.")
        else:
            pdf = FPDF()
            pdf.add_page()
            
            # Encabezado
            pdf.set_font("Arial", 'B', 16)
            pdf.set_text_color(204, 0, 0)
            pdf.cell(0, 15, "WÜRTH URUGUAY - PLAN CANJE REDSTRIPE", ln=True, align='C')
            
            pdf.set_font("Arial", '', 10)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(0, 8, f"Fecha/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
            pdf.cell(0, 8, f"Cliente: {nro_cliente} | Nombre: {nombre_persona}", ln=True)
            
            pdf.ln(5)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)
            
            # Cuerpo
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, "Detalles del Beneficio:", ln=True)
            pdf.set_font("Arial", '', 11)
            pdf.cell(0, 8, f"- Cantidad entregada para reciclaje: {cant_viejas} unidades", ln=True)
            pdf.cell(0, 8, f"- Familia beneficiada: {familia_sel}", ln=True)
            pdf.cell(0, 8, f"- Producto a retirar: {prod_sel}", ln=True)
            pdf.cell(0, 8, f"- Código SAP: {cod_sap}", ln=True)
            
            pdf.ln(10)
            pdf.set_font("Arial", 'B', 14)
            pdf.set_fill_color(230, 230, 230)
            pdf.cell(0, 15, f"DESCUENTO TOTAL: {dto_final}%", ln=True, align='C', fill=True)
            
            pdf.ln(10)
            pdf.set_font("Arial", 'I', 8)
            pdf.multi_cell(0, 5, "Este ticket valida el descuento otorgado por la entrega de herramientas en desuso. El descuento se aplica sobre el precio de lista vigente en el momento de la compra.")

            # Descarga
            pdf_bytes = pdf.output(dest='S').encode('latin-1')
            b64 = base64.b64encode(pdf_bytes).decode()
            filename = f"Ticket_Canje_{nro_cliente}.pdf"
            st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="{filename}" style="display:inline-block;padding:0.6em 1.2em;background-color:#cc0000;color:white;text-decoration:none;border-radius:5px;">📥 DESCARGAR TICKET DE DESCUENTO</a>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
