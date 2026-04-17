import streamlit as st
import pandas as pd
import os
import base64
from fpdf import FPDF
from datetime import datetime

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Plan Canje Würth", page_icon="assets/favicon.png", layout="wide")

# --- 2. ESTILOS (Identidad Würth) ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .block-container {padding-top: 2rem;}
    div[data-testid="stVerticalBlock"] > div { background-color: transparent !important; box-shadow: none !important; border: none !important; }
    [data-testid="stMetricValue"] { font-size: 40px !important; color: #cc0000 !important; font-weight: bold; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3.5em; background-color: #cc0000; color: white; border: none; font-weight: bold; }
    .stButton>button:hover { background-color: #a30000; color: white; border: none; }
    .white-card { background-color: #ffffff; padding: 40px; border-radius: 0px 0px 15px 15px; border-top: 10px solid #cc0000; box-shadow: 0 10px 30px rgba(0,0,0,0.05); margin-top: 10px; }
    .dto-banner { background-color: #fff5f5; padding: 20px; border-left: 6px solid #cc0000; margin-bottom: 25px; border-radius: 4px; }
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
    # Mapeo por posición (Col 0: Comercial, 2: Base, 3: Unidad, 4: Tope)
    df_b = df_b.rename(columns={df_b.columns[0]: 'Comercial', df_b.columns[2]: 'Base', df_b.columns[3]: 'Unidad', df_b.columns[4]: 'Tope'})
    return df_p, df_b

try:
    df_productos, df_beneficios = load_data()
except Exception as e:
    st.error(f"Error: {e}")
    st.stop()

if 'carrito' not in st.session_state: st.session_state.carrito = []
if 'paso' not in st.session_state: st.session_state.paso = 1

# --- 5. INTERFAZ ---
st.title("♻️ Plan Canje REDSTRIPE")

with st.expander("ℹ️ ¿Cómo funcionan nuestros descuentos por reciclaje?"):
    st.write("""
    - **Por Unidad:** Cada herramienta vieja que entregas suma un porcentaje específico de descuento según su categoría.
    - **Tope Máximo:** El beneficio total acumulado tiene un límite máximo definido por la categoría más alta de lo que entregas.
    - **Multicategoría:** Si traes herramientas de distintos tipos, sumamos los puntos de cada una y aplicamos el **Tope de descuento más alto** disponible.
    """)

st.markdown('<div class="white-card">', unsafe_allow_html=True)

# --- FASE 1: CALCULADORA ACUMULATIVA ---
if st.session_state.paso == 1:
    st.subheader("1. Detalle de herramientas a entregar")
    col_in, col_res = st.columns([1.2, 0.8])
    
    with col_in:
        cats_selec = st.multiselect("¿Qué tipos de herramientas trae el cliente?", df_beneficios['Comercial'].unique())
        
        cantidades_entrega = {}
        if cats_selec:
            st.write("---")
            for cat in cats_selec:
                c = st.number_input(f"Cantidad de '{cat}':", min_value=1, step=1, value=1, key=f"q_{cat}")
                cantidades_entrega[cat] = c
    
    if cats_selec:
        # Filtrar las reglas de las categorías elegidas
        reglas = df_beneficios[df_beneficios['Comercial'].isin(cats_selec)]
        
        # 1. Sumatoria individual (Cant * %Unidad)
        puntos_acumulados = 0
        for cat in cats_selec:
            valor_unidad = reglas[reglas['Comercial'] == cat]['Unidad'].values[0]
            puntos_acumulados += cantidades_entrega[cat] * valor_unidad
        
        # 2. Base y Tope (tomamos los más altos de la selección)
        mejor_base = reglas['Base'].max()
        mejor_tope = reglas['Tope'].max()
        
        # 3. Cálculo Final
        dto_preliminar = mejor_base + puntos_acumulados
        dto_final = min(dto_preliminar, mejor_tope)
        
        with col_res:
            st.metric("BENEFICIO TOTAL", f"{dto_final}%")
            st.markdown(f"**Desglose del cálculo:**")
            for cat in cats_selec:
                val_u = reglas[reglas['Comercial'] == cat]['Unidad'].values[0]
                st.write(f"* {cantidades_entrega[cat]}x {cat}: **+{cantidades_entrega[cat]*val_u}%**")
            
            if mejor_base > 0:
                st.write(f"* Ajuste Base: **+{mejor_base}%**")
                
            st.write(f"---")
            st.write(f"Suma: {dto_preliminar}% | **Tope: {mejor_tope}%**")
        
        if st.button("Confirmar Beneficio y Ver Productos ➔"):
            st.session_state.temp_dto = dto_final
            st.session_state.temp_cant_total = sum(cantidades_entrega.values())
            st.session_state.paso = 2
            st.rerun()
    else:
        st.info("Selecciona las categorías para comenzar el cálculo.")

# --- FASE 2: CARRITO Y CIERRE ---
else:
    st.markdown(f"""
    <div class="dto-banner">
        <h3 style="margin:0; color:#cc0000;">Bonificación Activa: {st.session_state.temp_dto}%</h3>
        <p style="margin:0; color:#444;">Por la entrega de {st.session_state.temp_cant_total} herramientas para reciclaje.</p>
    </div>
    """, unsafe_allow_html=True)

    st.subheader("2. Datos del Cliente y Selección de Productos")
    c_cli1, c_cli2 = st.columns(2)
    with c_cli1:
        c_nombre = st.text_input("Nombre / Razón Social")
    with c_cli2:
        c_id = st.text_input("RUT / Cédula de Identidad")

    st.divider()

    c_search, c_cart = st.columns([1.1, 0.9])
    
    with c_search:
        busq = st.text_input("🔍 Buscar por Código SAP o Nombre")
        df_f = df_productos[
            (df_productos['Código del producto'].astype(str).str.contains(busq)) |
            (df_productos['Nombre del producto'].str.contains(busq, case=False))
        ] if busq else df_productos

        modelos = sorted(df_f['Nombre del modelo'].dropna().unique())
        if modelos:
            m_sel = st.selectbox("Modelo (A-Z):", modelos)
            variantes = df_f[df_f['Nombre del modelo'] == m_sel]
            p_final_nombre = st.selectbox("Variante:", variantes['Nombre del producto'].unique())
            sap_val = variantes[variantes['Nombre del producto'] == p_final_nombre]['Código del producto'].values[0]
            
            p_lista = st.number_input("Precio de Lista Unitario (UYU)", min_value=0.0, step=1.0)
            
            if st.button("➕ Agregar al Carrito"):
                d_val = st.session_state.temp_dto
                ahorro_i = p_lista * (d_val / 100)
                st.session_state.carrito.append({
                    "SAP": sap_val, "Producto": p_final_nombre, "Lista": p_lista, "Ahorro": ahorro_i, "Final": p_lista - ahorro_i
                })
                st.rerun()

    with c_cart:
        if st.session_state.carrito:
            df_res = pd.DataFrame(st.session_state.carrito)
            st.dataframe(df_res[['Producto', 'Final']], use_container_width=True, hide_index=True)
            t_pagar = df_res['Final'].sum()
            st.metric("TOTAL A PAGAR", f"${t_pagar:,.2f}")
            if st.button("🗑️ Vaciar Carrito"):
                st.session_state.carrito = []
                st.rerun()
        else:
            st.write("Carrito vacío.")

    st.divider()
    b_vol, b_pdf = st.columns(2)
    with b_vol:
        if st.button("⬅ Volver al Simulador"):
            st.session_state.paso = 1
            st.session_state.carrito = []
            st.rerun()
    with b_pdf:
        if st.session_state.carrito and c_nombre and c_id:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.set_text_color(204, 0, 0)
            pdf.cell(0, 10, "PLAN CANJE WÜRTH URUGUAY", ln=True, align='C')
            pdf.ln(10)
            pdf.set_font("Arial", '', 11); pdf.set_text_color(0, 0, 0)
            pdf.cell(0, 7, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
            pdf.cell(0, 7, f"Cliente: {c_nombre} | Doc: {c_id}", ln=True)
            pdf.ln(5)
            
            # Tabla PDF
            pdf.set_font("Arial", 'B', 10); pdf.set_fill_color(240, 240, 240)
            pdf.cell(100, 8, " Producto", 1, 0, 'L', True)
            pdf.cell(40, 8, " P. Lista", 1, 0, 'C', True)
            pdf.cell(40, 8, " P. Final", 1, 1, 'C', True)
            
            pdf.set_font("Arial", '', 9)
            for item in st.session_state.carrito:
                pdf.cell(100, 8, str(item['Producto'])[:55], 1)
                pdf.cell(40, 8, f"${item['Lista']:,.2f}", 1, 0, 'C')
                pdf.cell(40, 8, f"${item['Final']:,.2f}", 1, 1, 'C')
            
            pdf.ln(5)
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, f"TOTAL NETO A PAGAR: ${t_pagar:,.2f}", ln=True, align='R')
            
            pdf_out = pdf.output(dest='S').encode('latin-1')
            st.download_button(label="📥 DESCARGAR TICKET", data=pdf_out, file_name=f"Canje_{c_id}.pdf", mime="application/pdf")

st.markdown('</div>', unsafe_allow_html=True)
