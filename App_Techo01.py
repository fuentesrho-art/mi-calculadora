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
        background: linear-gradient(90deg, #27ae60, #219a52);
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
        't_ring_top': inputs['t_ring_top']
    }
    return results, None

def export_to_excel(results):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df = pd.DataFrame({
            'Component': ['Ring Top', 'Ring Bottom', 'Rext', 'Rint', 'Compartments', 'Deck', 'Columns'],
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
    st.download_button("📥 Download Excel", output.getvalue(), f"MTO_{results['tank_tag']}.xlsx")

def main():
    st.markdown('<div class="main-header"><h1>⚓ STORAGE TANK ROOF CALCULATOR</h1></div>', unsafe_allow_html=True)
    
    with st.form("input_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📋 Project")
            tank_tag = st.text_input("Tank Tag", "TK-101")
            project = st.text_input("Project", "Refinery Expansion")
            client = st.text_input("Client", "Oil & Gas Corp")
            
            st.subheader("📐 Geometry")
            droof = st.number_input("Droof (m)", 52.0)
            ddeck = st.number_input("Ddeck (m)", 47.0)
            num_pontoons = st.number_input("Pontoons", 12, 4)
            router = st.number_input("Router (m)", 0.90, format="%.2f")
            rinner = st.number_input("Rinner (m)", 0.40, format="%.2f")
            l = st.number_input("L (m)", 0.25, format="%.2f")
        
        with col2:
            st.subheader("⚖️ Thicknesses (mm)")
            t_ring_top = st.number_input("t_RingTop", 6.0)
            t_ring_bottom = st.number_input("t_RingBottom", 6.0)
            t_rext = st.number_input("t_Rext", 5.0)
            t_rint = st.number_input("t_Rint", 5.0)
            t_compartment = st.number_input("t_Compartment", 5.0)
            t_single_deck = st.number_input("t_SingleDeck", 5.0)
            
            st.subheader("🔧 Columns")
            column_type = st.selectbox("Type", ['2x3', '3x4'])
            column_length = st.number_input("Column Length (m)", 2.5)
            sleeve_length = st.number_input("Sleeve Length (m)", 1.5)
            
            st.subheader("💧 Fluid")
            g = st.number_input("G (max 0.7)", 0.7, 0.0, 0.7, 0.01)
        
        st.form_submit_button("📊 CALCULATE", use_container_width=True)
    
    inputs = {
        'tank_tag': tank_tag, 'project': project, 'client': client,
        'droof': droof, 'ddeck': ddeck, 'num_pontoons': num_pontoons,
        'router': router, 'rinner': rinner, 'l': l,
        't_ring_top': t_ring_top, 't_ring_bottom': t_ring_bottom,
        't_rext': t_rext, 't_rint': t_rint,
        't_compartment': t_compartment, 't_single_deck': t_single_deck,
        'wothers_pontoon': 0, 'wothers_deck': 0,
        'column_type': column_type, 'column_length': column_length,
        'sleeve_length': sleeve_length, 'g': g
    }
    
    results, error = calculate_all(inputs)
    
    if error:
        st.error(error)
    else:
        st.markdown(f"""
            <div class="result-box">
                <h3>🏗️ TOTAL ROOF WEIGHT</h3>
                <h2>{results['w_roof_kg']:,.0f} kg ({results['w_roof_kN']:.1f} kN)</h2>
            </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Pontoons", results['final_pontoons'])
            st.metric("Deck Columns", results['n_columns_deck'])
        with col2:
            st.metric("Assembly Capacity", f"{results['assembly_capacity']} kg")
        
        st.markdown(f"""
            <div class="result-box">
                <h4>💧 Criterion 1 Freeboard: {results['Hflot_c1']:.3f} m</h4>
                <h4>⚠️ Criterion 2 Freeboard: {results['Hflot_c2']:.3f} m</h4>
            </div>
        """, unsafe_allow_html=True)
        
        if results['passes_c1'] and results['passes_c2']:
            st.markdown('<div class="pass">✅ REQUIREMENTS SATISFIED</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="fail">❌ REQUIREMENTS NOT SATISFIED</div>', unsafe_allow_html=True)
        
        export_to_excel(results)

if __name__ == "__main__":
    main()