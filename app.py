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
            .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #cc0000; color: white; }
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- 3. FUNCIONES ---
def get_base64(file_path):
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

def get_random_bg():
    bg_dir = "assets/fondos"
    search_dir = bg_dir if os.path.exists(bg_dir) else "."
    fondos = [f for f in os.listdir(search_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    return os.path.join(search_dir, random.choice(fondos)) if fondos else None

# Elementos Visuales
bg_image = get_random_bg()
bg_base64 = get_base64(bg_image)
logo_base64 = get_base64("logo_wurth.png") # Asegúrate de que esté en la raíz

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
    .instrucciones {{
        color: #444;
        font-size: 1.1em;
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
    # Mapeo flexible por si cambian los nombres en el Excel
    nuevos = {}
    for c in df_b.columns:
        if 'familia' in c.lower(): nuevos[c] = 'Familia'
        elif 'base' in c.lower(): nuevos[c] = 'Base'
        elif 'unidad' in c.lower(): nuevos[c] = 'Unidad'
        elif 'tope' in c.lower() or 'max' in c.lower(): nuevos[c] = 'Tope'
    df_b = df_b.rename(columns=nuevos)
    return df_p, df_b

df_productos, df_beneficios = load_data()

# --- 5. LÓGICA DE ESTADO ---
if 'paso' not in st.session_state:
    st.session_state.paso = 1

# --- 6. INTERFAZ ---
st.title("♻️ Plan Canje REDSTRIPE")

# Texto explicativo (reemplaza el rectángulo gris)
st.markdown("""
<div class="instrucciones">
Este sistema es un <b>Simulador de Descuentos por Reciclaje</b>. Incentivamos a nuestros clientes a entregar 
sus herramientas viejas para asegurar un proceso de disposición responsable, otorgando a cambio 
<b>descuentos exclusivos</b> para la renovación por herramientas nuevas de la línea REDSTRIPE de Würth.
</div>
""", unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    
    # PASO 1: CALCULADORA DE SUEÑOS
    if st.session_state.paso == 1:
        st.subheader("1. Calcula tu beneficio")
        col1, col2 = st.columns([1, 1])
        
        with col1:
            cant_viejas = st.number_input("Cantidad de herramientas a entregar:", min_value=1, step=1, value=1)
            fam_sel = st.selectbox("Familia de herramientas que quieres comprar:", df_beneficios['Familia'].unique())
        
        regla = df_beneficios[df_beneficios['Familia'] == fam_sel].iloc[0]
        dto_calculado = min(regla['Base'] + (cant_viejas * regla['Unidad']), regla['Tope'])
        
        with col2:
            st.metric("Bonificación:", f"{dto_calculado}%")
            st.write(f"✅ Por entregar **{cant_viejas}** herramientas, aplicas el beneficio máximo para la familia **{fam_sel}**.")
        
        st.write("")
        if st.button("Aplicar descuento y seleccionar productos ➔"):
            st.session_state.temp_dto = dto_calculado
            st.session_state.temp_cant = cant_viejas
            st.session_state.temp_fam = fam_sel
            st.session_state.paso = 2
            st.rerun()

    # PASO 2: CIERRE DE VENTA
    else:
        st.subheader("2. Detalle de la Operación")
        col3, col4 = st.columns(2)
        
        with col3:
            nro_cliente = st.text_input("Nro. Cliente / RUT")
            nombre = st.text_input("Nombre del Comprador")
            modelo_sel = st.selectbox("Modelo REDSTRIPE", sorted(df_productos['Nombre del modelo'].unique()))
            prods = df_productos[df_productos['Nombre del modelo'] == modelo_sel]
            prod_sel = st.selectbox("Variante específica", prods['Nombre del producto'].unique())
            codigo_sap = prods[prods['Nombre del producto'] == prod_sel]['Código del producto'].values[0]
            st.info(f"Código SAP: {codigo_sap}")
            
        with col4:
            # Aquí es donde ocurre la magia comercial
            precio_lista = st.number_input("Precio de Lista Unitario (UYU)", min_value=0.0, step=1.0)
            dto = st.session_state.temp_dto
            ahorro = precio_lista * (dto / 100)
            precio_final = precio_lista - ahorro
            
            st.markdown(f"### Precio Final: <span style='color:#cc0000;'>${precio_final:,.2f}</span>", unsafe_allow_html=True)
            st.write(f"🎁 Ahorro por reciclaje: **${ahorro:,.2f}**")
            st.write(f"📊 Descuento aplicado: **{dto}%**")

        st.divider()
        c_btn1, c_btn2 = st.columns(2)
        with c_btn1:
            if st.button("⬅ Volver a calcular"):
                st.session_state.paso = 1
                st.rerun()
        with c_btn2:
            if st.button("📥 Generar Ticket de Canje PDF"):
                # LÓGICA PDF
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", 'B', 16)
                pdf.set_text_color(204, 0, 0)
                pdf.cell(0, 10, "TICKET DE BENEFICIO - PLAN CANJE WURTH", ln=True, align='C')
                pdf.ln(10)
                pdf.set_font("Arial", '', 11)
                pdf.set_text_color(0,0,0)
                pdf.cell(0, 8, f"Cliente: {nro_cliente} - {nombre}", ln=True)
                pdf.cell(0, 8, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
                pdf.ln(5)
                pdf.cell(0, 8, f"Producto: {prod_sel} (Cod: {codigo_sap})", ln=True)
                pdf.cell(0, 8, f"Unidades entregadas para reciclaje: {st.session_state.temp_cant}", ln=True)
                pdf.ln(5)
                pdf.set_font("Arial", 'B', 12)
                pdf.cell(0, 10, f"Precio de Lista: ${precio_lista:,.2f}", ln=True)
                pdf.cell(0, 10, f"Bonificación ({dto}%): -${ahorro:,.2f}", ln=True)
                pdf.set_text_color(204, 0, 0)
                pdf.cell(0, 10, f"PRECIO FINAL A PAGAR: ${precio_final:,.2f}", ln=True)
                
                pdf_bytes = pdf.output(dest='S').encode('latin-1')
                b64 = base64.b64encode(pdf_bytes).decode()
                st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="Canje_{codigo_sap}.pdf" style="display:block; text-align:center; padding:10px; background-color:#28a745; color:white; border-radius:5px; text-decoration:none;">¡PDF LISTO! CLIC AQUÍ PARA DESCARGAR</a>', unsafe_allow_html=True)
                
    st.markdown('</div>', unsafe_allow_html=True)
