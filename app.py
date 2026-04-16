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

# --- 2. OCULTAR MENÚ Y MARCAS DE STREAMLIT (MÁSCARA) ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            /* Esto elimina el espacio superior sobrante */
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
    if os.path.exists(bg_dir):
        fondos = [f for f in os.listdir(bg_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        if fondos:
            return os.path.join(bg_dir, random.choice(fondos))
    return None

# Aplicar fondo aleatorio
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
        background-color: rgba(255, 255, 255, 0.92);
        padding: 30px;
        border-radius: 15px;
        border-left: 8px solid #cc0000;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 4. CARGA DE DATOS ---
@st.cache_data
def load_data():
    # Carga de archivos definidos por el usuario
    df_prod = pd.read_excel("productos.xlsx")
    df_ben = pd.read_excel("config_beneficios.xlsx")
    return df_prod, df_ben

try:
    df_productos, df_beneficios = load_data()
except Exception as e:
    st.error("Error: Asegúrate de que 'productos.xlsx' y 'config_beneficios.xlsx' estén en la raíz del repo.")
    st.stop()

# --- 5. INTERFAZ DE USUARIO ---
st.title("♻️ Plan Canje REDSTRIPE")
st.markdown("### Herramienta Oficial de Reciclaje y Beneficios")

with st.container():
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    
    # Fila 1: Datos del Cliente
    col_a, col_b = st.columns(2)
    with col_a:
        nro_cliente = st.text_input("Número de Cliente / RUT")
        nombre_comprador = st.text_input("Nombre del Comprador")
    with col_b:
        cant_viejas = st.number_input("Cantidad de herramientas entregadas (Reciclaje)", min_value=1, step=1, value=1)
        familia_sel = st.selectbox("Familia para aplicar descuento", df_beneficios['Familia'].unique())

    st.divider()

    # Fila 2: Selección de Producto Nuevo
    col_c, col_d = st.columns(2)
    with col_c:
        modelos_disponibles = sorted(df_productos['Nombre del modelo'].unique())
        modelo_sel = st.selectbox("Seleccione el Modelo REDSTRIPE", modelos_disponibles)
    
    with col_d:
        productos_filtrados = df_productos[df_productos['Nombre del modelo'] == modelo_sel]
        producto_sel = st.selectbox("Variante / Medida específica", productos_filtrados['Nombre del producto'].unique())
        
        # Extraer código
        codigo_final = productos_filtrados[productos_filtrados['Nombre del producto'] == producto_sel]['Código del producto'].values[0]
        st.caption(f"Código SAP: **{codigo_final}**")

    # --- 6. LÓGICA DE CÁLCULO ---
    datos_regla = df_beneficios[df_beneficios['Familia'] == familia_sel].iloc[0]
    
    base_dto = datos_regla['Dto. Base (%)']
    plus_unidad = datos_regla['Dto. por Unidad (%)']
    maximo = datos_regla['Tope Máximo (%)']
    
    # Fórmula de éxito
    total_dto = base_dto + (cant_viejas * plus_unidad)
    dto_aplicado = min(total_dto, maximo)

    # Visualización del resultado
    st.divider()
    res_1, res_2 = st.columns(2)
    with res_1:
        st.metric(label="DESCUENTO TOTAL", value=f"{dto_aplicado}%")
    with res_2:
        if total_dto > maximo:
            st.warning(f"Se ha alcanzado el tope máximo de {maximo}% para esta familia.")
        else:
            st.info(f"Cálculo: {base_dto}% base + {cant_viejas} unid. x {plus_unidad}%")

    # --- 7. GENERACIÓN DE COMPROBANTE PDF ---
    if st.button("Finalizar y Generar Ticket de Canje"):
        if not nro_cliente or not nombre_comprador:
            st.error("Por favor, completa los datos del cliente.")
        else:
            pdf = FPDF()
            pdf.add_page()
            
            # Cabezal
            pdf.set_font("Arial", 'B', 16)
            pdf.set_text_color(204, 0, 0) # Rojo Würth
            pdf.cell(200, 10, "COMPROBANTE PLAN CANJE REDSTRIPE", ln=True, align='C')
            
            pdf.ln(10)
            pdf.set_font("Arial", '', 11)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(0, 8, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
            pdf.cell(0, 8, f"Cliente ID: {nro_cliente}", ln=True)
            pdf.cell(0, 8, f"Nombre: {nombre_comprador}", ln=True)
            
            pdf.ln(5)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)
            
            # Detalle
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, "Resumen del Beneficio:", ln=True)
            pdf.set_font("Arial", '', 11)
            pdf.cell(0, 8, f"- Herramientas recibidas para reciclaje: {cant_viejas}", ln=True)
            pdf.cell(0, 8, f"- Producto seleccionado: {producto_sel}", ln=True)
            pdf.cell(0, 8, f"- Codigo SAP: {codigo_final}", ln=True)
            pdf.cell(0, 8, f"- Familia de descuento: {familia_sel}", ln=True)
            
            pdf.ln(10)
            pdf.set_font("Arial", 'B', 14)
            pdf.set_fill_color(240, 240, 240)
            pdf.cell(0, 12, f"DESCUENTO A APLICAR EN CAJA: {dto_aplicado}%", ln=True, align='C', fill=True)
            
            pdf.ln(15)
            pdf.set_font("Arial", 'I', 9)
            pdf.multi_cell(0, 5, "Este documento certifica la entrega de herramientas viejas para su correcto reciclaje y otorga un beneficio de compra inmediata. Valido unicamente para el dia de la fecha.")

            # Descarga
            pdf_bytes = pdf.output(dest='S').encode('latin-1')
            b64 = base64.b64encode(pdf_bytes).decode()
            filename = f"Canje_{nro_cliente}_{datetime.now().strftime('%Y%m%d')}.pdf"
            href = f'<a href="data:application/octet-stream;base64,{b64}" download="{filename}" style="text-decoration: none; padding: 10px 20px; background-color: #cc0000; color: white; border-radius: 5px;">📥 DESCARGAR COMPROBANTE PDF</a>'
            st.markdown(href, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
