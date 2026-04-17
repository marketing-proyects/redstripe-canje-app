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
    [data-testid="stMetricValue"] { font-size: 40px; color: #cc0000; font-weight: bold; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3.5em; background-color: #cc0000; color: white; border: none; font-weight: bold; }
    .stButton>button:hover { background-color: #a30000; color: white; border: none; }
    .white-card { background-color: #ffffff; padding: 40px; border-radius: 0px 0px 15px 15px; border-top: 10px solid #cc0000; box-shadow: 0 10px 30px rgba(0,0,0,0.05); margin-top: 10px; }
    .dto-banner { background-color: #f8f9fa; padding: 15px; border-left: 5px solid #cc0000; margin-bottom: 20px; border-radius: 5px; }
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
    # Mapeo robusto por posición
    df_b = df_b.rename(columns={df_b.columns[0]: 'Comercial', df_b.columns[2]: 'Base', df_b.columns[3]: 'Unidad', df_b.columns[4]: 'Tope'})
    return df_p, df_b

try:
    df_productos, df_beneficios = load_data()
except Exception as e:
    st.error(f"Error cargando archivos: {e}")
    st.stop()

# Estado de la App
if 'carrito' not in st.session_state: st.session_state.carrito = []
if 'paso' not in st.session_state: st.session_state.paso = 1

# --- 5. INTERFAZ ---
st.title("♻️ Plan Canje REDSTRIPE")

st.markdown('<div class="white-card">', unsafe_allow_html=True)

# --- FASE 1: CALCULADORA ---
if st.session_state.paso == 1:
    st.subheader("1. Detalle de herramientas a entregar")
    col_in, col_res = st.columns([1.2, 0.8])
    
    with col_in:
        cats_selec = st.multiselect("Categorías que entrega el cliente:", df_beneficios['Comercial'].unique())
        total_u = 0
        if cats_selec:
            for cat in cats_selec:
                c = st.number_input(f"Cantidad de '{cat}':", min_value=1, step=1, value=1, key=f"n_{cat}")
                total_u += c
    
    if cats_selec:
        reglas = df_beneficios[df_beneficios['Comercial'].isin(cats_selec)]
        m_base, m_unidad, m_tope = reglas['Base'].max(), reglas['Unidad'].max(), reglas['Tope'].max()
        dto_calc = min(m_base + (total_u * m_unidad), m_tope)
        
        with col_res:
            st.metric("DESCUENTO OBTENIDO", f"{dto_calc}%")
            st.markdown(f"**Resumen:**\n* Total herramientas: {total_u}\n* Tope aplicado: {m_tope}%")
        
        if st.button("Confirmar Beneficio ➔"):
            st.session_state.temp_dto = dto_calc
            st.session_state.temp_cant_total = total_u
            st.session_state.paso = 2
            st.rerun()
    else:
        st.info("Selecciona las categorías para calcular el beneficio.")

# --- FASE 2: CARRITO Y CIERRE ---
else:
    # Banner de descuento traído de Fase 1
    st.markdown(f"""
    <div class="dto-banner">
        <h4 style="margin:0; color:#cc0000;">Bonificación Activa: {st.session_state.temp_dto}%</h4>
        <p style="margin:0; color:#666;">Basado en la entrega de {st.session_state.temp_cant_total} herramientas viejas.</p>
    </div>
    """, unsafe_allow_html=True)

    st.subheader("2. Identificación y Selección de Productos")
    
    # Datos del Cliente
    c_cli1, c_cli2 = st.columns(2)
    with c_cli1:
        cliente_nombre = st.text_input("Nombre / Razón Social", placeholder="Ej: Juan Pérez o Empresa S.A.")
    with c_cli2:
        cliente_id = st.text_input("RUT / Cédula de Identidad")

    st.divider()

    c_selec, c_resumen = st.columns([1.1, 0.9])
    
    with c_selec:
        busq = st.text_input("🔍 Buscar por Código SAP o Nombre")
        df_filtrado = df_productos[
            (df_productos['Código del producto'].astype(str).str.contains(busq)) |
            (df_productos['Nombre del producto'].str.contains(busq, case=False))
        ] if busq else df_productos

        modelos_az = sorted(df_filtrado['Nombre del modelo'].dropna().unique())
        if modelos_az:
            mod_sel = st.selectbox("Navegar por Modelo (A-Z):", modelos_az)
            variantes = df_filtrado[df_filtrado['Nombre del modelo'] == mod_sel]
            prod_final = st.selectbox("Variante / Medida:", variantes['Nombre del producto'].unique())
            sap_final = variantes[variantes['Nombre del producto'] == prod_final]['Código del producto'].values[0]
            
            p_lista = st.number_input("Precio de Lista Unitario (UYU)", min_value=0.0, step=1.0)
            
            if st.button("➕ Agregar al Carrito"):
                dto = st.session_state.temp_dto
                ahorro = p_lista * (dto / 100)
                st.session_state.carrito.append({
                    "SAP": sap_final, "Producto": prod_final, "Lista": p_lista, "Ahorro": ahorro, "Final": p_lista - ahorro
                })
                st.rerun()
        else:
            st.warning("No hay productos con ese nombre/código.")

    with c_resumen:
        st.write("### Detalle de la Compra")
        if st.session_state.carrito:
            df_c = pd.DataFrame(st.session_state.carrito)
            st.dataframe(df_c[['Producto', 'Final']], use_container_width=True, hide_index=True)
            
            total_lista = df_c['Lista'].sum()
            total_ahorro = df_c['Ahorro'].sum()
            total_pagar = df_c['Final'].sum()
            
            st.metric("TOTAL A PAGAR", f"${total_pagar:,.2f}")
            st.write(f"📉 Ahorro total aplicado: **${total_ahorro:,.2f}**")
            
            if st.button("🗑️ Vaciar Carrito"):
                st.session_state.carrito = []
                st.rerun()
        else:
            st.write("El carrito está vacío.")

    st.divider()
    b_back, b_pdf = st.columns(2)
    with b_back:
        if st.button("⬅ Volver a Recalcular"):
            st.session_state.paso = 1
            st.session_state.carrito = []
            st.rerun()
    with b_pdf:
        if st.session_state.carrito and cliente_nombre and cliente_id:
            # Lógica de Generación de PDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.set_text_color(204, 0, 0)
            pdf.cell(0, 10, "PLAN CANJE WÜRTH URUGUAY - REDSTRIPE", ln=True, align='C')
            pdf.ln(10)
            
            pdf.set_font("Arial", '', 10)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(0, 6, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
            pdf.cell(0, 6, f"Cliente / Razón Social: {cliente_nombre}", ln=True)
            pdf.cell(0, 6, f"RUT / CI: {cliente_id}", ln=True)
            pdf.ln(5)
            pdf.cell(0, 6, f"Herramientas entregadas para reciclaje: {st.session_state.temp_cant_total}", ln=True)
            pdf.ln(5)
            
            # Tabla de productos
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(100, 8, "Producto", 1)
            pdf.cell(40, 8, "P. Lista", 1)
            pdf.cell(40, 8, "P. Final", 1, ln=True)
            
            pdf.set_font("Arial", '', 9)
            for item in st.session_state.carrito:
                pdf.cell(100, 8, str(item['Producto'])[:50], 1)
                pdf.cell(40, 8, f"${item['Lista']:,.2f}", 1)
                pdf.cell(40, 8, f"${item['Final']:,.2f}", 1, ln=True)
            
            pdf.ln(10)
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, f"TOTAL AHORRADO: ${total_ahorro:,.2f}", ln=True, align='R')
            pdf.set_text_color(204, 0, 0)
            pdf.cell(0, 10, f"TOTAL NETO A PAGAR: ${total_pagar:,.2f}", ln=True, align='R')
            
            pdf_output = pdf.output(dest='S').encode('latin-1')
            st.download_button(
                label="📥 DESCARGAR TICKET DE CANJE",
                data=pdf_output,
                file_name=f"Canje_Wurth_{cliente_id}.pdf",
                mime="application/pdf"
            )
        else:
            st.warning("Completa los datos del cliente y agrega productos para habilitar el Ticket.")

st.markdown('</div>', unsafe_allow_html=True)
