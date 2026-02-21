import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from PIL import Image

# Constantes fijas
RHO = 7850  # kg/m³
CV = 1.2  # kN/m²
GRAVITY = 9.81  # m/s²
H_WATER = 0.25  # m
GAMMA_WATER = 9.81  # kN/m³

# Pesos lineales fijos (kg/m)
LINEAR_WEIGHTS = {
    '2-Sch80': 7.48,
    '3-Sch80': 16.08,
    '3-Sch40': 11.29,
    '4-Sch40': 16.07
}

# Capacidad de ensamblaje (kg)
ASSEMBLY_CAPACITY = {
    '2x3': 4500,
    '3x4': 6500
}

st.set_page_config(page_title="Tank Roof Calculator", page_icon="⚓", layout="wide")

# Estilos CSS
st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(90deg, #2c3e50 0%, #3498db 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 20px;
    }
    .result-box {
        background: #f8faff;
        border-radius: 10px;
        padding: 20px;
        border-left: 5px solid #3498db;
        margin-bottom: 20px;
    }
    .result-item {
        display: flex;
        justify-content: space-between;
        padding: 8px 0;
        border-bottom: 1px dashed #e0e7ef;
    }
    .result-label {
        font-weight: 600;
        color: #2c3e50;
    }
    .result-value {
        font-family: monospace;
        font-weight: 600;
        color: #2980b9;
    }
    .pass {
        background: #d4edda;
        color: #155724;
        padding: 15px;
        border-radius: 8px;
        text-align: center;
        font-weight: bold;
    }
    .fail {
        background: #f8d7da;
        color: #721c24;
        padding: 15px;
        border-radius: 8px;
        text-align: center;
        font-weight: bold;
    }
    .stButton > button {
        background: linear-gradient(90deg, #3498db, #2980b9);
        color: white;
        font-weight: bold;
        font-size: 1.2em;
        padding: 10px 30px;
        border: none;
        border-radius: 5px;
        width: 100%;
    }
    </style>
""", unsafe_allow_html=True)

def calculate_all(inputs):
    droof = inputs['droof']
    ddeck = inputs['ddeck']
    user_pontoons = inputs['num_pontoons']
    router = inputs['router']
    rinner = inputs['rinner']
    l = inputs['l']
    
    t_ring_top_m = inputs['t_ring_top'] / 1000
    t_ring_bottom_m = inputs['t_ring_bottom'] / 1000
    t_rext_m = inputs['t_rext'] / 1000
    t_rint_m = inputs['t_rint'] / 1000
    t_compartment_m = inputs['t_compartment'] / 1000
    t_single_deck_m = inputs['t_single_deck'] / 1000
    
    wothers_pontoon = inputs['wothers_pontoon']
    wothers_deck = inputs['wothers_deck']
    
    column_type = inputs['column_type']
    column_length = inputs['column_length']
    sleeve_length = inputs['sleeve_length']
    g = min(inputs['g'], 0.7)
    
    if droof == 0 or ddeck == 0 or user_pontoons < 4 or router == 0:
        return None, "Please enter valid values"
    
    is_small_diameter = droof <= 6.0
    X1 = ddeck / 2
    X2 = droof / 2
    
    area_ring = (np.pi / 4) * (droof**2 - ddeck**2)
    area_compartment = ((router + rinner) / 2) * ((droof - ddeck) / 2)
    area_deck = (np.pi / 4) * (ddeck**2)
    
    w_ring_top = area_ring * t_ring_top_m * RHO
    w_ring_bottom = area_ring * t_ring_bottom_m * RHO
    w_rext = np.pi * droof * router * t_rext_m * RHO
    w_rint = np.pi * ddeck * rinner * t_rint_m * RHO
    w_single_deck = area_deck * t_single_deck_m * RHO
    
    w_pontoon_base = w_ring_top + w_ring_bottom + w_rext + w_rint + wothers_pontoon
    w_deck = w_single_deck + wothers_deck
    
    if column_type == '2x3':
        linear_col = LINEAR_WEIGHTS['2-Sch80']
        linear_sleeve = LINEAR_WEIGHTS['3-Sch40']
        w_unit = (linear_col * column_length) + (linear_sleeve * sleeve_length)
        assembly_capacity = ASSEMBLY_CAPACITY['2x3']
    else:
        linear_col = LINEAR_WEIGHTS['3-Sch80']
        linear_sleeve = LINEAR_WEIGHTS['4-Sch40']
        w_unit = (linear_col * column_length) + (linear_sleeve * sleeve_length)
        assembly_capacity = ASSEMBLY_CAPACITY['3x4']
    
    assembly_capacity_kN = (assembly_capacity * GRAVITY) / 1000
    
    min_required_pontoons = 0
    min_required_pontoons_prev = -1
    iterations = 0
    test_pontoons = user_pontoons
    test_compartments = area_compartment * t_compartment_m * RHO * test_pontoons
    test_pontoon_weight = w_pontoon_base + test_compartments
    
    while min_required_pontoons != min_required_pontoons_prev and iterations < 20:
        min_required_pontoons_prev = min_required_pontoons
        test_pontoon_weight_kN = (test_pontoon_weight * GRAVITY) / 1000
        numerator = 1.2 * test_pontoon_weight_kN + 1.6 * (CV * area_ring)
        min_required_pontoons = int(np.ceil(numerator / assembly_capacity_kN))
        test_pontoons = min_required_pontoons
        test_compartments = area_compartment * t_compartment_m * RHO * test_pontoons
        test_pontoon_weight = w_pontoon_base + test_compartments
        iterations += 1
    
    final_pontoons = max(user_pontoons, min_required_pontoons)
    final_compartments = area_compartment * t_compartment_m * RHO * final_pontoons
    final_pontoon_weight = w_pontoon_base + final_compartments
    
    w_deck_kN = (w_deck * GRAVITY) / 1000
    numerator_deck = 1.2 * w_deck_kN + 1.6 * (CV * area_deck)
    n_columns_deck = int(np.ceil(numerator_deck / assembly_capacity_kN))
    
    w_columns_pontoon = final_pontoons * w_unit
    w_columns_deck = n_columns_deck * w_unit
    w_roof_kg = final_pontoon_weight + w_deck + w_columns_pontoon + w_columns_deck
    w_roof_kN = (w_roof_kg * GRAVITY) / 1000
    
    gamma_fluid = g * GRAVITY
    Vwater = np.pi * X1**2 * H_WATER
    Wwater = GAMMA_WATER * Vwater
    
    termA = (ddeck**2) / 4
    termB = (2*X1**2 - X1*X2 - X2**2) / 3
    denominator = termA - X1**2 + X2**2
    height_factor = l - (router - rinner)
    const_term_num = (termA - termB) * height_factor
    
    Fb1 = w_roof_kN + Wwater
    termPi1 = Fb1 / (gamma_fluid * np.pi)
    numerator1 = termPi1 - const_term_num
    H1_c1 = numerator1 / denominator
    Hflot_c1 = router - H1_c1
    
    num_flooded = 2 if not is_small_diameter else 1
    theta = num_flooded * (2 * np.pi / final_pontoons)
    avg_height = (rinner + router) / 2
    radial_width = X2 - X1
    correction_term = (radial_width * (2*router + rinner)) / (3 * (rinner + router))
    corrected_mean_radius = X1 + correction_term
    
    Vpontoons_flooded = theta * avg_height * radial_width * corrected_mean_radius
    Wpontoons_flooded = gamma_fluid * Vpontoons_flooded
    
    Fb2 = w_roof_kN + Wpontoons_flooded
    termPi2 = Fb2 / (gamma_fluid * np.pi)
    numerator2 = termPi2 - const_term_num
    H1_c2 = numerator2 / denominator
    Hflot_c2 = router - H1_c2
    
    passes_c1 = Hflot_c1 > 0.01
    passes_c2 = Hflot_c2 > 0.01
    
    if user_pontoons < min_required_pontoons:
        source = f"⚠️ Usando mínimo: {final_pontoons} (usuario puso {user_pontoons})"
    else:
        source = f"✓ Usando: {final_pontoons}"
    
    results = {
        'tank_tag': inputs['tank_tag'],
        'project': inputs['project'],
        'client': inputs['client'],
        'w_roof_kg': w_roof_kg,
        'w_roof_kN': w_roof_kN,
        'w_ring_top': w_ring_top,
        'w_ring_bottom': w_ring_bottom,
        'w_rext': w_rext,
        'w_rint': w_rint,
        'final_compartments': final_compartments,
        'w_deck': w_deck,
        'w_columns_pontoon': w_columns_pontoon,
        'w_columns_deck': w_columns_deck,
        'final_pontoons': final_pontoons,
        'n_columns_deck': n_columns_deck,
        'assembly_capacity': assembly_capacity,
        'assembly_capacity_kN': assembly_capacity_kN,
        'w_unit': w_unit,
        'min_required_pontoons': min_required_pontoons,
        'Hflot_c1': Hflot_c1,
        'Hflot_c2': Hflot_c2,
        'Wwater': Wwater,
        'Vpontoons_flooded': Vpontoons_flooded,
        'passes_c1': passes_c1,
        'passes_c2': passes_c2,
        'is_small_diameter': is_small_diameter,
        'num_flooded': num_flooded,
        'X1': X1,
        'X2': X2,
        'source': source,
        't_ring_top': inputs['t_ring_top'],
        't_ring_bottom': inputs['t_ring_bottom'],
        't_rext': inputs['t_rext'],
        't_rint': inputs['t_rint'],
        't_compartment': inputs['t_compartment'],
        't_single_deck': inputs['t_single_deck'],
        'column_length': column_length,
        'sleeve_length': sleeve_length,
        'linear_col': linear_col,
        'linear_sleeve': linear_sleeve,
        'router': router,
        'rinner': rinner,
        'l': l,
        'droof': droof,
        'ddeck': ddeck,
        'g': g,
        'iterations': iterations
    }
    return results, None

def export_to_excel(results):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # MTO
        df = pd.DataFrame({
            'Item': ['1', '2', '3', '4', '5', '6', '7'],
            'Description': [
                f"Ring Top ({results['t_ring_top']} mm)",
                f"Ring Bottom ({results['t_ring_bottom']} mm)",
                f"Outer Rim ({results['t_rext']} mm)",
                f"Inner Rim ({results['t_rint']} mm)",
                f"Compartments ({results['final_pontoons']} units)",
                "Deck Plate",
                f"Columns ({results['final_pontoons'] + results['n_columns_deck']} units)"
            ],
            'Weight (kg)': [
                round(results['w_ring_top']),
                round(results['w_ring_bottom']),
                round(results['w_rext']),
                round(results['w_rint']),
                round(results['final_compartments']),
                round(results['w_deck']),
                round(results['w_columns_pontoon'] + results['w_columns_deck'])
            ]
        })
        df.to_excel(writer, sheet_name='MTO', index=False)
        
        # Resumen
        summary = pd.DataFrame({
            'Description': ['TOTAL ROOF WEIGHT'],
            'kg': [round(results['w_roof_kg'])],
            'kN': [round(results['w_roof_kN'], 1)]
        })
        summary.to_excel(writer, sheet_name='Summary', index=False)
    
    st.download_button(
        "📥 Export MTO to Excel",
        output.getvalue(),
        f"MTO_{results['tank_tag']}_{datetime.now().strftime('%Y%m%d')}.xlsx"
    )

def export_to_pdf(results):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []
    
    # Título
    elements.append(Paragraph("STORAGE TANK ROOF FLOTATION REPORT", styles['Title']))
    elements.append(Spacer(1, 12))
    
    # Información del proyecto
    data = [
        [f"Tank: {results['tank_tag']}", f"Project: {results['project']}", f"Client: {results['client']}"],
        [f"Date: {datetime.now().strftime('%Y-%m-%d')}", "", ""]
    ]
    table = Table(data, colWidths=[180, 180, 180])
    table.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 1, colors.grey)]))
    elements.append(table)
    elements.append(Spacer(1, 12))
    
    # Peso total
    elements.append(Paragraph(f"TOTAL ROOF WEIGHT: {results['w_roof_kg']:,.0f} kg ({results['w_roof_kN']:.1f} kN)", styles['Heading2']))
    elements.append(Spacer(1, 12))
    
    # Weight Breakdown
    data = [['Component', 'Weight (kg)']]
    data.append(['Ring Top', f"{results['w_ring_top']:,.1f}"])
    data.append(['Ring Bottom', f"{results['w_ring_bottom']:,.1f}"])
    data.append(['Outer Rim', f"{results['w_rext']:,.1f}"])
    data.append(['Inner Rim', f"{results['w_rint']:,.1f}"])
    data.append(['Compartments', f"{results['final_compartments']:,.1f}"])
    data.append(['Deck', f"{results['w_deck']:,.1f}"])
    data.append(['Columns', f"{results['w_columns_pontoon'] + results['w_columns_deck']:,.1f}"])
    
    table = Table(data)
    table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 1, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke)
    ]))
    elements.append(table)
    elements.append(Spacer(1, 12))
    
    # Column Summary
    elements.append(Paragraph(f"Columns: {results['final_pontoons']} pont + {results['n_columns_deck']} deck", styles['Normal']))
    elements.append(Paragraph(f"Assembly Capacity: {results['assembly_capacity']} kg", styles['Normal']))
    elements.append(Spacer(1, 12))
    
    # Flotation
    elements.append(Paragraph(f"Criterion 1 Freeboard: {results['Hflot_c1']:.3f} m", styles['Normal']))
    elements.append(Paragraph(f"Criterion 2 Freeboard: {results['Hflot_c2']:.3f} m", styles['Normal']))
    elements.append(Spacer(1, 12))
    
    # Verdict
    if results['passes_c1'] and results['passes_c2']:
        elements.append(Paragraph("✅ FLOTATION REQUIREMENTS SATISFIED", styles['Heading3']))
    else:
        elements.append(Paragraph("❌ FLOTATION REQUIREMENTS NOT SATISFIED", styles['Heading3']))
    
    doc.build(elements)
    buffer.seek(0)
    
    st.download_button(
        "📥 Export Report to PDF",
        buffer,
        f"Report_{results['tank_tag']}_{datetime.now().strftime('%Y%m%d')}.pdf"
    )

def main():
    st.markdown('<div class="main-header"><h1>⚓ STORAGE TANK ROOF FLOTATION CALCULATOR</h1></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1.2, 1])
    
    with col1:
        with st.expander("📋 Project Information", expanded=True):
            tank_tag = st.text_input("Tank Tag", "TK-101")
            project = st.text_input("Project", "Refinery Expansion")
            client = st.text_input("Client", "Oil & Gas Corp")
        
        with st.expander("📐 Geometry", expanded=True):
            try:
                st.image("Designer (5).png", caption="Tank Geometry")
            except:
                st.info("Geometry diagram")
            
            droof = st.number_input("Roof diameter (Droof) - m", 52.0, step=0.1)
            ddeck = st.number_input("Deck diameter (Ddeck) - m", 47.0, step=0.1)
            num_pontoons = st.number_input("Number of Pontoons", 12, 4)
            router = st.number_input("Outer height (Router) - m", 0.90, step=0.01)
            rinner = st.number_input("Inner height (Rinner) - m", 0.40, step=0.01)
            l = st.number_input("Inclined side (L) - m", 0.25, step=0.01)
        
        with st.expander("⚖️ Weights", expanded=True):
            try:
                st.image("Roof_Weight.jpeg", caption="Roof Weight")
            except:
                pass
            
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                t_ring_top = st.number_input("t_RingTop (mm)", 6.0, step=0.1)
                t_ring_bottom = st.number_input("t_RingBottom (mm)", 6.0, step=0.1)
                t_rext = st.number_input("t_Rext (mm)", 5.0, step=0.1)
                t_rint = st.number_input("t_Rint (mm)", 5.0, step=0.1)
            with col_t2:
                t_compartment = st.number_input("t_Compartment (mm)", 5.0, step=0.1)
                t_single_deck = st.number_input("t_SingleDeck (mm)", 5.0, step=0.1)
            
            col_w1, col_w2 = st.columns(2)
            with col_w1:
                wothers_pontoon = st.number_input("Wothers pontoon (kg)", 0)
            with col_w2:
                wothers_deck = st.number_input("Wothers deck (kg)", 0)
        
        with st.expander("🔧 Columns", expanded=True):
            try:
                st.image("Column.jpeg", caption="Column")
            except:
                pass
            
            column_type = st.selectbox("Column Type", ['2x3', '3x4'])
            column_length = st.number_input("Column Length (m)", 2.5, step=0.1)
            sleeve_length = st.number_input("Sleeve Length (m)", 1.5, step=0.1)
        
        with st.expander("💧 Fluid", expanded=True):
            g = st.number_input("Relative density G (max 0.7)", 0.7, 0.0, 0.7, 0.01)
    
    with col2:
        inputs = {
            'tank_tag': tank_tag, 'project': project, 'client': client,
            'droof': droof, 'ddeck': ddeck, 'num_pontoons': num_pontoons,
            'router': router, 'rinner': rinner, 'l': l,
            't_ring_top': t_ring_top, 't_ring_bottom': t_ring_bottom,
            't_rext': t_rext, 't_rint': t_rint,
            't_compartment': t_compartment, 't_single_deck': t_single_deck,
            'wothers_pontoon': wothers_pontoon, 'wothers_deck': wothers_deck,
            'column_type': column_type, 'column_length': column_length,
            'sleeve_length': sleeve_length, 'g': g
        }
        
        if st.button("📊 CALCULATE", use_container_width=True):
            results, error = calculate_all(inputs)
            
            if error:
                st.error(error)
            else:
                st.markdown(f"""
                    <div style="background:#edf2f7; padding:15px; border-radius:8px; margin-bottom:15px">
                        <h3 style="margin:0">🏗️ TOTAL WEIGHT</h3>
                        <h2 style="color:#2980b9; margin:0">{results['w_roof_kg']:,.0f} kg ({results['w_roof_kN']:.1f} kN)</h2>
                    </div>
                """, unsafe_allow_html=True)
                
                with st.expander("⚙️ Weight Breakdown", expanded=True):
                    st.markdown(f"""
                        <div class="result-item"><span class="result-label">WRingTop:</span> <span class="result-value">{results['w_ring_top']:,.1f} kg</span></div>
                        <div class="result-item"><span class="result-label">WRingBottom:</span> <span class="result-value">{results['w_ring_bottom']:,.1f} kg</span></div>
                        <div class="result-item"><span class="result-label">WRext:</span> <span class="result-value">{results['w_rext']:,.1f} kg</span></div>
                        <div class="result-item"><span class="result-label">WRint:</span> <span class="result-value">{results['w_rint']:,.1f} kg</span></div>
                        <div class="result-item"><span class="result-label">WCompartment ({results['final_pontoons']}):</span> <span class="result-value">{results['final_compartments']:,.1f} kg</span></div>
                        <div class="result-item"><span class="result-label">WDeck:</span> <span class="result-value">{results['w_deck']:,.1f} kg</span></div>
                        <div class="result-item"><span class="result-label">WColumns:</span> <span class="result-value">{results['w_columns_pontoon'] + results['w_columns_deck']:,.1f} kg</span></div>
                    """, unsafe_allow_html=True)
                
                st.markdown(f"""
                    <div class="result-box">
                        <h4>📊 Columns: {results['final_pontoons']} pont + {results['n_columns_deck']} deck</h4>
                        <h4>⚡ Assembly cap: {results['assembly_capacity']} kg ({results['assembly_capacity_kN']:.1f} kN)</h4>
                        <h4>📌 {results['source']}</h4>
                    </div>
                """, unsafe_allow_html=True)
                
                if results['is_small_diameter']:
                    st.info("⚠️ Droof ≤ 6m: Usando 1 compartimento inundado")
                
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    st.metric("Criterion 1 Freeboard", f"{results['Hflot_c1']:.3f} m")
                with col_c2:
                    st.metric("Criterion 2 Freeboard", f"{results['Hflot_c2']:.3f} m")
                
                if results['passes_c1'] and results['passes_c2']:
                    st.markdown('<div class="pass">✅ FLOTATION REQUIREMENTS SATISFIED</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="fail">❌ FLOTATION REQUIREMENTS NOT SATISFIED</div>', unsafe_allow_html=True)
                
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    export_to_excel(results)
                with col_e2:
                    export_to_pdf(results)

if __name__ == "__main__":
    main()