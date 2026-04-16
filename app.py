import streamlit as st
import pandas as pd
import os
import random
import base64
from fpdf import FPDF
from datetime import datetime

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Plan Canje Würth", page_icon="assets/favicon.png", layout="wide")

# --- 2. MÁSCARA PROFESIONAL Y ESTILOS ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            .block-container {padding-top: 1rem;}
            [data-testid="stMetricValue"] { font-size: 45px; color: #cc0000; font-weight: bold; }
            /* Estilo para los botones */
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

def get_random_bg():
    bg_dir = "assets/fondos"
    search_dir = bg_dir if os.path.exists(bg_dir) else "."
    fondos = [f for f in os.listdir(search_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    return os.path.join(search_dir, random.choice(fondos)) if fondos else None

# Carga de recursos visuales
bg_image = get_random_bg()
bg_base64 = get_base64(bg_image)
logo_base64 = get_base64("logo_wurth.png")

# Inyección de Logo y Fondo
st.markdown(f"""
    <style>
    .stApp {{
        background-image: url("data:image/png;base64,{bg_base64}");
        background-size: cover;
        background-attachment: fixed;
    }}
    .logo-container {{
        position: fixed;
        top: 20px;
        right: 40px;
        width: 140px;
        z-index: 1000;
    }}
    .main-card {{
        background-color: rgba(255, 255, 255, 0.98);
        padding: 40px;
        border-radius: 15px;
        border-top: 8px solid #cc0000;
        box-shadow: 0 15px 35px rgba(0,0,0,0.4);
        margin-top: 20px;
    }}
    .explicacion {{
        color: #333;
        font-size: 1.15em;
        line-height: 1.5;
        margin-bottom: 25px;
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
    # Mapeo flexible
    nuevos = {}
    for c in df_b.columns:
        if 'familia' in c.lower(): nuevos[c] = 'Familia'
        elif 'base' in c.lower(): nuevos[c] = 'Base'
        elif 'unidad' in c.lower(): nuevos[c] = 'Unidad'
        elif 'tope' in c.lower() or 'max' in c.lower(): nuevos[c] = 'Tope'
    df_b = df_b.rename(columns=nuevos)
    return df_p, df_b

df_productos, df_beneficios = load_data()

# --- 5. GESTIÓN DE PASOS ---
if 'paso' not in st.session_state:
    st.session_state.paso = 1

# --- 6. INTERFAZ DE USUARIO ---
st.title("♻️ Plan Canje REDSTRIPE")

# Texto explicativo profesional (Sin rectángulo gris)
st.markdown("""
<div class="explicacion">
    Esta herramienta es un <b>Simulador de Descuentos</b> diseñado para incentivar la entrega de herramientas viejas, 
    asegurando su correcto reciclaje. Al participar, accedes a beneficios exclusivos para renovar tu equipamiento 
    con la tecnología y calidad de la línea <b>REDSTRIPE de Würth</b>.
</div>
""", unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    
    # --- PASO 1: CALCULADORA DE DESCUENTO ---
    if st.session_state.paso == 1:
        st.subheader("1. Simulador de Beneficio")
        col1, col2 = st.columns([1.2, 0.8])
        
        with col1:
            cant_viejas = st.number_input("¿Cuántas herramientas vas a entregar para reciclar?", min_value=1, step=1, value=1)
            fam_sel = st.selectbox("Familia de herramientas que quieres comprar hoy:", df_beneficios['Familia'].unique())
        
        regla = df_beneficios[df_beneficios['Familia'] == fam_sel].iloc[0]
        # Cálculo: % Base + (Cant * % Unidad) limitado por el Tope
        dto_calculado = min(regla['Base'] + (cant_viejas * regla['Unidad']), regla['Tope'])
        
        with col2:
            st.metric("BONIFICACIÓN:", f"{dto_calculado}%")
            st.write(f"¡Excelente! Al entregar **{cant_viejas}** herramientas, activas un descuento preferencial para la familia **{fam_sel}**.")
        
        st.write("")
        if st.button("Siguiente: Ver productos y precios ➔"):
            st.session_state.temp_dto = dto_calculado
            st.session_state.temp_cant = cant_viejas
            st.session_state.temp_fam = fam_sel
            st.session_state.paso = 2
            st.rerun()

    # --- PASO 2: CIERRE Y PRECIO FINAL ---
    else:
        st.subheader("2. Resumen de la Operación")
        col3, col4 = st.columns(2)
        
        with col3:
            nro_cliente = st.text_input("Número de Cliente / RUT")
            nombre_comprador = st.text_input("Nombre del Cliente")
            
            modelo_sel = st.selectbox("Modelo REDSTRIPE", sorted(df_productos['Nombre del modelo'].unique()))
            prods = df_productos[df_productos['Nombre del modelo'] == modelo_sel]
            prod_sel = st.selectbox("Producto específico", prods['Nombre del producto'].unique())
            codigo_sap = prods[prods['Nombre del producto'] == prod_sel]['Código del producto'].values[0]
            st.write(f"**Código SAP:** `{codigo_sap}`")
            
        with col4:
            # Aquí se ingresa el precio del sistema de la tienda
            precio_lista = st.number_input("Precio de Lista Unitario (UYU)", min_value=0.0, step=1.0)
            dto = st.session_state.temp_dto
            
            ahorro = precio_lista * (dto / 100)
            precio_final = precio_lista - ahorro
            
            st.markdown(f"### Precio Final: <span style='color:#cc0000;'>${precio_final:,.2f}</span>", unsafe_allow_html=True)
            st.write(f"🎁 **Ahorro por reciclaje:** ${ahorro:,.2f}")
            st.write(f"📊 **Descuento aplicado:** {dto}%")

        st.divider()
        c_btn1, c_btn2 = st.columns(2)
        with c_btn1:
            if st.button("⬅ Volver a calcular"):
                st.session_state.paso = 1
                st.rerun()
        with c_btn2:
            if st.button("📥 Generar Ticket PDF"):
                # Generación del PDF con los datos de precio
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", 'B', 16)
                pdf.set_text_color(204, 0, 0)
                pdf.cell(0, 10, "PLAN CANJE WÜRTH - COMPROBANTE DE BENEFICIO", ln=True, align='C')
                pdf.ln(10)
                pdf.set_font("Arial", '', 11)
                pdf.set_text_color(0,0,0)
                pdf.cell(0, 8, f"Cliente: {nro_cliente} - {nombre_comprador}", ln=True)
                pdf.cell(0, 8, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
                pdf.ln(5)
                pdf.cell(0, 8, f"Producto: {prod_sel} (Cod: {codigo_sap})", ln=True)
                pdf.cell(0, 8, f"Unidades recicladas: {st.session_state.temp_cant}", ln=True)
                pdf.ln(5)
                pdf.set_font("Arial", 'B', 12)
                pdf.cell(0, 10, f"Precio de Lista: ${precio_lista:,.2f}", ln=True)
                pdf.cell(0, 10, f"Descuento ({dto}%): -${ahorro:,.2f}", ln=True)
                pdf.set_text_color(204, 0, 0)
                pdf.cell(0, 10, f"PRECIO FINAL A PAGAR: ${precio_final:,.2f}", ln=True)
                
                pdf_bytes = pdf.output(dest='S').encode('latin-1')
                b64 = base64.b64encode(pdf_bytes).decode()
                st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="Plan_Canje_{codigo_sap}.pdf" style="display:block; text-align:center; padding:12px; background-color:#28a745; color:white; border-radius:5px; text-decoration:none; font-weight:bold;">📥 DESCARGAR COMPROBANTE PDF</a>', unsafe_allow_html=True)
                
    st.markdown('</div>', unsafe_allow_html=True)
