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

# --- 2. MÁSCARA PROFESIONAL (OCULTAR INTERFAZ ST) ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            .block-container {padding-top: 1.5rem;} 
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- 3. ESTÉTICA Y FONDOS ---
def get_base64(file_path):
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

def get_random_bg():
    bg_dir = "assets/fondos"
    # Si no existe la carpeta, busca en raíz para no fallar
    search_dir = bg_dir if os.path.exists(bg_dir) else "."
    fondos = [f for f in os.listdir(search_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    return os.path.join(search_dir, random.choice(fondos)) if fondos else None

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
        background-color: rgba(255, 255, 255, 0.96);
        padding: 30px;
        border-radius: 15px;
        border-left: 10px solid #cc0000;
        box-shadow: 0 12px 30px rgba(0,0,0,0.4);
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 4. CARGA DE DATOS CON LIMPIEZA ---
@st.cache_data
def load_data():
    # Productos
    df_p = pd.read_excel("productos.xlsx")
    df_p.columns = [str(c).strip() for c in df_p.columns]
    
    # Beneficios
    df_b = pd.read_excel("config_beneficios.xlsx")
    df_b.columns = [str(c).strip() for c in df_b.columns]
    
    return df_p, df_b

try:
    df_productos, df_beneficios = load_data()
    
    # Verificación de columnas para evitar el KeyError
    req_cols = ['Familia', 'Dto. Base (%)', 'Dto. por Unidad (%)', 'Tope Máximo (%)']
    for col in req_cols:
        if col not in df_beneficios.columns:
            st.error(f"⚠️ Error: No encuentro la columna '{col}' en config_beneficios.xlsx. Revisa el nombre exacto.")
            st.stop()
except Exception as e:
    st.error(f"❌ Error al cargar archivos: {e}")
    st.stop()

# --- 5. INTERFAZ DE USUARIO ---
st.title("♻️ Plan Canje REDSTRIPE")
st.markdown("##### Gestión de Beneficios - Punto de Venta")

with st.container():
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        nro_cliente = st.text_input("Número de Cliente / RUT")
        nombre_comprador = st.text_input("Nombre del Comprador")
    with c2:
        cant_viejas = st.number_input("Cantidad de herramientas entregadas", min_value=1, step=1, value=1)
        familia_sel = st.selectbox("Familia del producto nuevo", df_beneficios['Familia'].unique())

    st.divider()

    c3, c4 = st.columns(2)
    with c3:
        # Usamos 'Nombre del modelo' para filtrar macro
        modelos = sorted(df_productos['Nombre del modelo'].dropna().unique())
        mod_sel = st.selectbox("Seleccione el Modelo", modelos)
    with c4:
        prods_filt = df_productos[df_productos['Nombre del modelo'] == mod_sel]
        prod_sel = st.selectbox("Variante del producto", prods_filt['Nombre del producto'].unique())
        
        # Obtener código SAP
        codigo_sap = prods_filt[prods_filt['Nombre del producto'] == prod_sel]['Código del producto'].values[0]
        st.info(f"Código SAP: **{codigo_sap}**")

    # --- 6. LÓGICA DE DESCUENTO ---
    regla = df_beneficios[df_beneficios['Familia'] == familia_sel].iloc[0]
    
    base = regla['Dto. Base (%)']
    plus = regla['Dto. por Unidad (%)']
    tope = regla['Tope Máximo (%)']
    
    calc_dto = base + (cant_viejas * plus)
    dto_final = min(calc_dto, tope)

    st.divider()
    res1, res2 = st.columns(2)
    with res1:
        st.metric("DESCUENTO TOTAL", f"{dto_final}%")
    with res2:
        if calc_dto > tope:
            st.warning(f"Se aplicó el tope máximo permitido de {tope}%")
        else:
            st.success(f"Cálculo: {base}% base + ({cant_viejas} x {plus}%) por reciclaje.")

    # --- 7. EMISIÓN DE TICKET ---
    if st.button("Finalizar y Emitir Ticket"):
        if not nro_cliente or not nombre_comprador:
            st.error("Debe completar los datos del cliente.")
        else:
            pdf = FPDF()
            pdf.add_page()
            
            # Encabezado con estética Würth
            pdf.set_font("Arial", 'B', 16)
            pdf.set_text_color(204, 0, 0)
            pdf.cell(0, 15, "WÜRTH URUGUAY - PLAN CANJE REDSTRIPE", ln=True, align='C')
            
            pdf.ln(5)
            pdf.set_font("Arial", '', 10)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(0, 8, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
            pdf.cell(0, 8, f"Cliente: {nro_cliente} | Nombre: {nombre_comprador}", ln=True)
            
            pdf.ln(5)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(10)
            
            # Detalle comercial
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, "RESUMEN DE BENEFICIO OTORGADO:", ln=True)
            pdf.set_font("Arial", '', 11)
            pdf.cell(0, 8, f"- Unidades recibidas para reciclaje: {cant_viejas}", ln=True)
            pdf.cell(0, 8, f"- Familia aplicada: {familia_sel}", ln=True)
            pdf.cell(0, 8, f"- Producto seleccionado: {prod_sel}", ln=True)
            pdf.cell(0, 8, f"- Codigo SAP: {codigo_sap}", ln=True)
            
            pdf.ln(10)
            pdf.set_font("Arial", 'B', 14)
            pdf.set_fill_color(240, 240, 240)
            pdf.cell(0, 15, f"DESCUENTO A APLICAR: {dto_final}%", ln=True, align='C', fill=True)
            
            pdf.ln(15)
            pdf.set_font("Arial", 'I', 8)
            pdf.multi_cell(0, 5, "Este comprobante certifica la entrega de material para reciclaje y otorga un beneficio de descuento inmediato para la compra de herramientas nuevas REDSTRIPE. Valido unicamente por el dia de hoy.")

            # Descarga del PDF
            pdf_bytes = pdf.output(dest='S').encode('latin-1')
            b64 = base64.b64encode(pdf_bytes).decode()
            filename = f"Canje_{nro_cliente}.pdf"
            
            href = f'<a href="data:application/octet-stream;base64,{b64}" download="{filename}" style="display:inline-block;padding:12px 24px;background-color:#cc0000;color:white;text-decoration:none;border-radius:6px;font-weight:bold;">📥 DESCARGAR COMPROBANTE PDF</a>'
            st.markdown(href, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
