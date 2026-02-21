import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from PIL import Image
import os

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

# Estilos CSS mejorados
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
    .card {
        background: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
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
    .badge {
        background: #3498db;
        color: white;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.8em;
        display: inline-block;
    }
    .pass {
        background: #d4edda;
        color: #155724;
        padding: 15px;
        border-radius: 8px;
        text-align: center;
        font-weight: bold;
        font-size: 1.2em;
    }
    .fail {
        background: #f8d7da;
        color: #721c24;
        padding: 15px;
        border-radius: 8px;
        text-align: center;
        font-weight: bold;
        font-size: 1.2em;
    }
    .special-note {
        background: #e7f5ff;
        border-left: 4px solid #0369a1;
        padding: 10px 15px;
        border-radius: 4px;
        margin-bottom: 15px;
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
    .metric-container {
        background: white;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #e0e7ef;
        text-align: center;
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
    final_pontoon_weight_kN = (final_pontoon_weight * GRAVITY) / 1000
    
    numerator_final = 1.2 * final_pontoon_weight_kN + 1.6 * (CV * area_ring)
    columns_needed = int(np.ceil(numerator_final / assembly_capacity_kN))
    final_columns = max(final_pontoons, columns_needed)
    
    if final_columns > final_pontoons:
        final_pontoons = final_columns
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
        source_message = f"⚠️ User input ({user_pontoons}) < minimum required ({min_required_pontoons}) - using minimum: {final_pontoons}"
    elif user_pontoons > min_required_pontoons:
        source_message = f"✓ User input ({user_pontoons}) > minimum required ({min_required_pontoons}) - using user value: {final_pontoons}"
    else:
        source_message = f"✓ User input matches minimum required: {final_pontoons}"
    
    results = {
        'tank_tag': inputs['tank_tag'],
        'project': inputs['project'],
        'client': inputs['client'],
        'droof': droof,
        'ddeck': ddeck,
        'user_pontoons': user_pontoons,
        'router': router,
        'rinner': rinner,
        'l': l,
        't_ring_top': inputs['t_ring_top'],
        't_ring_bottom': inputs['t_ring_bottom'],
        't_rext': inputs['t_rext'],
        't_rint': inputs['t_rint'],
        't_compartment': inputs['t_compartment'],
        't_single_deck': inputs['t_single_deck'],
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
        'linear_col': linear_col,
        'linear_sleeve': linear_sleeve,
        'min_required_pontoons': min_required_pontoons,
        'iterations': iterations,
        'Hflot_c1': Hflot_c1,
        'Hflot_c2': Hflot_c2,
        'Wwater': Wwater,
        'Fb1': Fb1,
        'H1_c1': H1_c1,
        'Fb2': Fb2,
        'H1_c2': H1_c2,
        'Vpontoons_flooded': Vpontoons_flooded,
        'Wpontoons_flooded': Wpontoons_flooded,
        'passes_c1': passes_c1,
        'passes_c2': passes_c2,
        'is_small_diameter': is_small_diameter,
        'source_message': source_message,
        'num_flooded': num_flooded,
        'X1': X1,
        'X2': X2,
        'area_ring': area_ring,
        'area_deck': area_deck,
        'area_compartment': area_compartment,
        'g': g,
        'column_length': column_length,
        'sleeve_length': sleeve_length
    }
    return results, None

def export_to_excel(results):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        total_plates_6mm = round(results['w_ring_top'] + results['w_ring_bottom'])
        total_plates_5mm = round(results['w_rext'] + results['w_rint'] + results['final_compartments'] + results['w_deck'])
        total_plates = total_plates_6mm + total_plates_5mm
        
        total_cols = round((results['final_pontoons'] + results['n_columns_deck']) * results['linear_col'] * results['column_length'])
        total_sleeves = round((results['final_pontoons'] + results['n_columns_deck']) * results['linear_sleeve'] * results['sleeve_length'])
        total_pipes = total_cols + total_sleeves
        
        mto_data = [
            ["MATERIAL TAKE-OFF (MTO)"],
            [],
            [f"Tank Tag: {results['tank_tag']}", f"Project: {results['project']}", f"Client: {results['client']}"],
            [],
            ["PLATES"],
            ["Item", "Description", "Thickness (mm)", "Weight (kg)"],
            [1, f"Carbon steel plate, {results['t_ring_top']} mm thick", results['t_ring_top'], total_plates_6mm],
            [2, f"Carbon steel plate, {results['t_rext']} mm thick", results['t_rext'], total_plates_5mm],
            [3, "", "", ""],
            [4, "", "", ""],
            ["", "", "TOTAL PLATES", total_plates],
            [],
            ["PIPES (COLUMNS)"],
            ["Item", "Description", "Qty", "Unit Weight (kg)", "Total Weight (kg)"],
            [5, f'Pipe NPS 2", Sch 80, Carbon steel ({results["column_length"]} m)', results['final_pontoons'] + results['n_columns_deck'], round(results['linear_col'] * results['column_length'], 2), total_cols],
            [6, f'Pipe NPS 3", Sch 40, Carbon steel ({results["sleeve_length"]} m)', results['final_pontoons'] + results['n_columns_deck'], round(results['linear_sleeve'] * results['sleeve_length'], 2), total_sleeves],
            [7, "", "", "", ""],
            [8, "", "", "", ""],
            ["", "", "", "TOTAL PIPES", total_pipes],
            [],
            ["GRAND TOTAL"],
            ["Total Plates", total_plates],
            ["Total Pipes", total_pipes],
            ["TOTAL ROOF WEIGHT (kg)", total_plates + total_pipes],
            [],
            [f"Date: {datetime.now().strftime('%Y-%m-%d')}"]
        ]
        
        df_mto = pd.DataFrame(mto_data)
        df_mto.to_excel(writer, sheet_name='MTO', index=False, header=False)
    
    st.download_button(
        "📥 Export MTO to Excel",
        output.getvalue(),
        f"MTO_{results['tank_tag']}_{datetime.now().strftime('%Y%m%d')}.xlsx"
    )

def export_to_pdf(results):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#2c3e50'),
        alignment=1,
        spaceAfter=20
    )
    
    elements = []
    
    # Título
    elements.append(Paragraph("STORAGE TANK ROOF FLOTATION CALCULATION REPORT", title_style))
    
    # Información del proyecto
    data = [
        [f"Tank Tag: {results['tank_tag']}", f"Project: {results['project']}", f"Client: {results['client']}"],
        [f"Date: {datetime.now().strftime('%Y-%m-%d')}", "", ""]
    ]
    table = Table(data, colWidths=[180, 180, 180])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2c3e50')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dddddd'))
    ]))
    elements.append(table)
    elements.append(Spacer(1, 12))
    
    # Total roof weight
    elements.append(Paragraph(f"🏗️ TOTAL ROOF WEIGHT: {results['w_roof_kg']:,.0f} kg ({results['w_roof_kN']:.1f} kN)", 
                              ParagraphStyle('Total', parent=styles['Heading2'], textColor=colors.HexColor('#2980b9'))))
    elements.append(Spacer(1, 12))
    
    # Weight Breakdown
    elements.append(Paragraph("⚙️ Weight Breakdown", styles['Heading2']))
    weight_data = [
        ["Component", "Weight (kg)"],
        [f"WRingTop ({results['t_ring_top']} mm)", f"{results['w_ring_top']:,.1f}"],
        [f"WRingBottom ({results['t_ring_bottom']} mm)", f"{results['w_ring_bottom']:,.1f}"],
        [f"WRext ({results['t_rext']} mm)", f"{results['w_rext']:,.1f}"],
        [f"WRint ({results['t_rint']} mm)", f"{results['w_rint']:,.1f}"],
        [f"WCompartment ({results['final_pontoons']} units)", f"{results['final_compartments']:,.1f}"],
        [f"WDeck ({results['t_single_deck']} mm)", f"{results['w_deck']:,.1f}"],
        [f"WColumns ({results['final_pontoons']} pont + {results['n_columns_deck']} deck)", f"{results['w_columns_pontoon'] + results['w_columns_deck']:,.1f}"],
        ["", ""],
        ["TOTAL Wroof:", f"{results['w_roof_kg']:,.1f} kg"]
    ]
    table = Table(weight_data, colWidths=[300, 150])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -2), 1, colors.HexColor('#eeeeee')),
        ('BACKGROUND', (-2, -1), (-1, -1), colors.HexColor('#f0f0f0')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 12))
    
    # Column & Pontoon Summary
    elements.append(Paragraph("📊 Column & Pontoon Summary", styles['Heading2']))
    col_data = [
        ["Parameter", "Value"],
        ["Columns in Pontoons", str(results['final_pontoons'])],
        ["Number of Pontoons", str(results['final_pontoons'])],
        ["Columns in Deck", str(results['n_columns_deck'])],
        ["Unit Weight per Column", f"{results['w_unit']:.1f} kg"],
        ["Minimum Required", str(results['min_required_pontoons'])],
        ["Assembly Capacity", f"{results['assembly_capacity']} kg ({results['assembly_capacity_kN']:.1f} kN)"],
        ["Status", results['source_message']]
    ]
    table = Table(col_data, colWidths=[250, 200])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#eeeeee')),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 12))
    
    if results['is_small_diameter']:
        elements.append(Paragraph("⚠️ Since roof diameter is ≤ 6 m, API 650 Annex C requires considering 1 flooded compartment instead of 2.",
                                  ParagraphStyle('Note', parent=styles['Italic'], textColor=colors.HexColor('#e67e22'))))
        elements.append(Spacer(1, 12))
    
    # Criterion 1
    elements.append(Paragraph("💧 CRITERION 1: Roof + Water", styles['Heading2']))
    crit1_data = [
        ["Parameter", "Value"],
        ["Water weight on deck", f"{results['Wwater']:.2f} kN"],
        ["Required buoyancy force", f"{results['Fb1']:.2f} kN"],
        ["Submerged depth H₁", f"{results['H1_c1']:.3f} m"],
        ["Flotation height (freeboard)", f"{results['Hflot_c1']:.3f} m"]
    ]
    table = Table(crit1_data, colWidths=[250, 200])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#eeeeee')),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 12))
    
    # Criterion 2
    elements.append(Paragraph(f"⚠️ CRITERION 2: Roof + {results['num_flooded']} adjacent pontoon{'s' if results['num_flooded'] > 1 else ''} flooded", styles['Heading2']))
    crit2_data = [
        ["Parameter", "Value"],
        [f"Volume of {results['num_flooded']} pontoon{'s' if results['num_flooded'] > 1 else ''}", f"{results['Vpontoons_flooded']:.2f} m³"],
        ["Fluid weight", f"{results['Wpontoons_flooded']:.2f} kN"],
        ["Required buoyancy force", f"{results['Fb2']:.2f} kN"],
        ["Submerged depth H₁", f"{results['H1_c2']:.3f} m"],
        ["Flotation height (freeboard)", f"{results['Hflot_c2']:.3f} m"]
    ]
    table = Table(crit2_data, colWidths=[250, 200])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#eeeeee')),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 12))
    
    # Conclusion
    if results['passes_c1'] and results['passes_c2']:
        elements.append(Paragraph("✅ ROOF FLOTATION REQUIREMENTS SATISFIED",
                                  ParagraphStyle('Pass', parent=styles['Heading3'], textColor=colors.HexColor('#27ae60'), alignment=1)))
    else:
        elements.append(Paragraph("❌ ROOF DOES NOT MEET FLOTATION REQUIREMENTS",
                                  ParagraphStyle('Fail', parent=styles['Heading3'], textColor=colors.HexColor('#e74c3c'), alignment=1)))
    elements.append(Spacer(1, 12))
    
    # Geometry note
    elements.append(Paragraph(f"Geometry: X₁ = {results['X1']:.3f} m | X₂ = {results['X2']:.3f} m | Compartments = {results['final_pontoons']} | θ for {results['num_flooded']} comp = {((results['num_flooded'] * 360) / results['final_pontoons']):.1f}°",
                              ParagraphStyle('Geo', parent=styles['Italic'], fontSize=8)))
    
    doc.build(elements)
    buffer.seek(0)
    
    st.download_button(
        "📥 Export Report to PDF",
        buffer,
        f"Report_{results['tank_tag']}_{datetime.now().strftime('%Y%m%d')}.pdf"
    )

def main():
    st.markdown('<div class="main-header"><h1>⚓ STORAGE TANK ROOF FLOTATION CALCULATOR</h1></div>', unsafe_allow_html=True)
    
    with st.form("input_form"):
        col1, col2 = st.columns([1.2, 1])
        
        with col1:
            with st.expander("📋 Project Information", expanded=True):
                tank_tag = st.text_input("Tank Tag", "TK-101")
                project = st.text_input("Project", "Refinery Expansion")
                client = st.text_input("Client", "Oil & Gas Corp")
            
            with st.expander("📐 Geometry", expanded=True):
                if os.path.exists("Designer (5).png"):
                    st.image("Designer (5).png", caption="Tank Geometry")
                
                droof = st.number_input("Roof diameter (Droof) - m", value=52.0, step=0.1, format="%.2f")
                ddeck = st.number_input("Deck diameter (Ddeck) - m", value=47.0, step=0.1, format="%.2f")
                num_pontoons = st.number_input("Number of Pontoons", value=12, min_value=4, step=1)
                router = st.number_input("Outer height (Router) - m", value=0.90, step=0.01, format="%.2f")
                rinner = st.number_input("Inner height (Rinner) - m", value=0.40, step=0.01, format="%.2f")
                l = st.number_input("Inclined side (L) - m", value=0.25, step=0.01, format="%.2f")
            
            with st.expander("⚖️ Weights", expanded=True):
                if os.path.exists("Roof_Weight.jpeg"):
                    st.image("Roof_Weight.jpeg", caption="Roof Weight")
                
                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    t_ring_top = st.number_input("t_RingTop (mm)", value=6.0, step=0.1, format="%.1f")
                    t_ring_bottom = st.number_input("t_RingBottom (mm)", value=6.0, step=0.1, format="%.1f")
                    t_rext = st.number_input("t_Rext (mm)", value=5.0, step=0.1, format="%.1f")
                    t_rint = st.number_input("t_Rint (mm)", value=5.0, step=0.1, format="%.1f")
                with col_t2:
                    t_compartment = st.number_input("t_Compartment (mm)", value=5.0, step=0.1, format="%.1f")
                    t_single_deck = st.number_input("t_SingleDeck (mm)", value=5.0, step=0.1, format="%.1f")
                
                col_w1, col_w2 = st.columns(2)
                with col_w1:
                    wothers_pontoon = st.number_input("Wothers pontoon (kg)", value=0, step=1)
                with col_w2:
                    wothers_deck = st.number_input("Wothers deck (kg)", value=0, step=1)
            
            with st.expander("🔧 Columns", expanded=True):
                if os.path.exists("Column.jpeg"):
                    st.image("Column.jpeg", caption="Column")
                
                column_type = st.selectbox("Column Type", ['2x3', '3x4'])
                column_length = st.number_input("Column Length (m)", value=2.5, step=0.1, format="%.1f")
                sleeve_length = st.number_input("Sleeve Length (m)", value=1.5, step=0.1, format="%.1f")
            
            with st.expander("💧 Fluid", expanded=True):
                g = st.number_input("Relative density G (max 0.7)", value=0.7, min_value=0.0, max_value=0.7, step=0.01, format="%.2f")
            
            st.markdown("""
                <div style="background:#eef2f7; border-radius:6px; padding:15px; margin-top:15px">
                    <p style="margin:0; color:#27ae60; font-weight:500">🔒 FIXED VALUES:</p>
                    <p style="margin:5px 0">Water height on deck: <strong>0.25 m</strong></p>
                    <p style="margin:5px 0">Specific weight of water: <strong>9.81 kN/m³</strong></p>
                </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("### 📊 LIVE RESULTS")
            st.caption("All values update automatically")
            submitted = st.form_submit_button("📊 CALCULATE", use_container_width=True)
    
    if submitted:
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
        
        results, error = calculate_all(inputs)
        
        if error:
            st.error(error)
        else:
            st.markdown(f"""
                <div style="background:#edf2f7; padding:15px; border-radius:8px; margin-bottom:15px">
                    <span style="font-size:1.2em; font-weight:bold">🏗️ TOTAL ROOF WEIGHT</span>
                    <div style="display:flex; justify-content:space-between; margin-top:8px">
                        <span>Wroof =</span>
                        <span style="font-weight:bold; color:#2980b9">{results['w_roof_kg']:,.0f} kg ({results['w_roof_kN']:.1f} kN)</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            with st.expander("⚙️ Weight Breakdown", expanded=True):
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    st.markdown(f"<div class='result-item'><span class='result-label'>WRingTop:</span> <span class='result-value'>{results['w_ring_top']:,.1f} kg</span></div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='result-item'><span class='result-label'>WRingBottom:</span> <span class='result-value'>{results['w_ring_bottom']:,.1f} kg</span></div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='result-item'><span class='result-label'>WRext:</span> <span class='result-value'>{results['w_rext']:,.1f} kg</span></div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='result-item'><span class='result-label'>WRint:</span> <span class='result-value'>{results['w_rint']:,.1f} kg</span></div>", unsafe_allow_html=True)
                with col_b2:
                    st.markdown(f"<div class='result-item'><span class='result-label'>WCompartment ({results['final_pontoons']}):</span> <span class='result-value'>{results['final_compartments']:,.1f} kg</span></div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='result-item'><span class='result-label'>WDeck:</span> <span class='result-value'>{results['w_deck']:,.1f} kg</span></div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='result-item'><span class='result-label'>WColumns:</span> <span class='result-value'>{results['w_columns_pontoon'] + results['w_columns_deck']:,.1f} kg</span></div>", unsafe_allow_html=True)
                
                st.markdown(f"""
                    <div class='result-item' style='border-top:2px solid #3498db; margin-top:5px; padding-top:8px'>
                        <span class='result-label'>TOTAL Wroof:</span>
                        <span class='result-value' style='font-size:1.1em'>{results['w_roof_kg']:,.1f} kg</span>
                    </div>
                """, unsafe_allow_html=True)
            
            st.markdown(f"""
                <div class="result-box">
                    <div style="display:flex; align-items:center; gap:10px; margin-bottom:15px">
                        <h3 style="margin:0">📊 Column & Pontoon Summary</h3>
                        <span class="badge">Assembly cap: {results['assembly_capacity']} kg ({results['assembly_capacity_kN']:.1f} kN)</span>
                    </div>
                    <div class="result-item"><span class="result-label">Columns in Pontoons:</span> <span class="result-value">{results['final_pontoons']}</span></div>
                    <div class="result-item"><span class="result-label">Number of Pontoons:</span> <span class="result-value">{results['final_pontoons']}</span></div>
                    <div class="result-item"><span class="result-label">Columns in Deck:</span> <span class="result-value">{results['n_columns_deck']}</span></div>
                    <div class="result-item"><span class="result-label">Unit Weight per Column:</span> <span class="result-value">{results['w_unit']:.1f} kg</span></div>
                    <div class="result-item"><span class="result-label">Minimum Required:</span> <span class="result-value">{results['min_required_pontoons']}</span></div>
                    <div class="result-item"><span class="result-label">Iterations:</span> <span class="result-value">{results['iterations']}</span></div>
                    <div class="result-item" style="border-top:1px dashed #3498db; margin-top:5px; padding-top:8px; color:#e67e22">
                        <span class="result-label">Status:</span>
                        <span class="result-value">{results['source_message']}</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            if results['is_small_diameter']:
                st.markdown("""
                    <div class="special-note">
                        ⚠️ Since roof diameter is ≤ 6 m, API 650 Annex C requires considering <strong>1 flooded compartment</strong> instead of 2.
                    </div>
                """, unsafe_allow_html=True)
            
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                st.markdown(f"""
                    <div class="result-box">
                        <h3 style="margin-top:0">💧 CRITERION 1: Roof + Water</h3>
                        <div class="result-item"><span class="result-label">Water weight:</span> <span class="result-value">{results['Wwater']:.2f} kN</span></div>
                        <div class="result-item"><span class="result-label">Buoyancy force:</span> <span class="result-value">{results['Fb1']:.2f} kN</span></div>
                        <div class="result-item"><span class="result-label">Submerged depth H₁:</span> <span class="result-value">{results['H1_c1']:.3f} m</span></div>
                        <div class="result-item" style="font-weight:bold">
                            <span class="result-label">Freeboard:</span>
                            <span class="result-value" style="color:{'#27ae60' if results['Hflot_c1'] > 0 else '#e74c3c'}">{results['Hflot_c1']:.3f} m</span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            
            with col_c2:
                st.markdown(f"""
                    <div class="result-box">
                        <h3 style="margin-top:0">⚠️ CRITERION 2: Roof + {results['num_flooded']} adjacent pontoon{'s' if results['num_flooded'] > 1 else ''} flooded</h3>
                        <div class="result-item"><span class="result-label">Volume flooded:</span> <span class="result-value">{results['Vpontoons_flooded']:.2f} m³</span></div>
                        <div class="result-item"><span class="result-label">Fluid weight:</span> <span class="result-value">{results['Wpontoons_flooded']:.2f} kN</span></div>
                        <div class="result-item"><span class="result-label">Buoyancy force:</span> <span class="result-value">{results['Fb2']:.2f} kN</span></div>
                        <div class="result-item"><span class="result-label">Submerged depth H₁:</span> <span class="result-value">{results['H1_c2']:.3f} m</span></div>
                        <div class="result-item" style="font-weight:bold">
                            <span class="result-label">Freeboard:</span>
                            <span class="result-value" style="color:{'#27ae60' if results['Hflot_c2'] > 0 else '#e74c3c'}">{results['Hflot_c2']:.3f} m</span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            
            if results['passes_c1'] and results['passes_c2']:
                st.markdown('<div class="pass">✅ ROOF FLOTATION REQUIREMENTS SATISFIED</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="fail">❌ ROOF DOES NOT MEET FLOTATION REQUIREMENTS</div>', unsafe_allow_html=True)
            
            st.markdown(f"""
                <div style="background:#eef2f7; border-radius:6px; padding:10px; margin-top:15px; font-family:monospace; font-size:0.9em">
                    Geometry: X₁ = {results['X1']:.3f} m | X₂ = {results['X2']:.3f} m | Compartments = {results['final_pontoons']} | θ for {results['num_flooded']} comp = {((results['num_flooded'] * 360) / results['final_pontoons']):.1f}°
                </div>
            """, unsafe_allow_html=True)
            
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                export_to_excel(results)
            with col_e2:
                export_to_pdf(results)
    
    st.markdown("""
        <div style="text-align:center; margin-top:30px; padding-top:15px; border-top:1px solid #dee2e6; color:#6c757d; font-size:0.9em">
            ⚡ Based on API 650 • CV = 1.2 kN/m² • ρ = 7850 kg/m³ • G max = 0.7 • CORRECTED UNITS
        </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()