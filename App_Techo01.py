import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import io
import base64
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import stripe
import os
from PIL import Image as PILImage

# Configuración de Stripe (usar variables de entorno en producción)
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY', 'sk_test_...')  # Reemplazar en producción

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

# Configuración de la página
st.set_page_config(
    page_title="Storage Tank Roof Calculator",
    page_icon="⚓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos personalizados
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
    .badge {
        background: #3498db;
        color: white;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.8em;
        display: inline-block;
    }
    .special-note {
        background: #e7f5ff;
        border-left: 4px solid #0369a1;
        padding: 10px 15px;
        border-radius: 4px;
        margin-bottom: 15px;
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
    .payment-button {
        background: linear-gradient(90deg, #f39c12, #e67e22) !important;
    }
    .disabled {
        opacity: 0.5;
        pointer-events: none;
    }
    </style>
""", unsafe_allow_html=True)

# Inicializar session state
if 'payment_required' not in st.session_state:
    st.session_state.payment_required = True
if 'payment_completed' not in st.session_state:
    st.session_state.payment_completed = False
if 'show_results' not in st.session_state:
    st.session_state.show_results = False
if 'last_calculation' not in st.session_state:
    st.session_state.last_calculation = None
if 'checkout_session_id' not in st.session_state:
    st.session_state.checkout_session_id = None

def create_checkout_session():
    """Crear sesión de pago con Stripe"""
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card', 'paypal'],
            line_items=[
                {
                    'price_data': {
                        'currency': 'usd',
                        'unit_amount': 4900,  # $49.00 USD
                        'product_data': {
                            'name': 'Tank Roof Calculation Report',
                            'description': 'Complete calculation report with MTO and PDF export',
                        },
                    },
                    'quantity': 1,
                },
            ],
            mode='payment',
            success_url='https://your-app.com/success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='https://your-app.com/cancel',
        )
        return checkout_session.id, checkout_session.url
    except Exception as e:
        st.error(f"Error creating payment session: {e}")
        return None, None

def process_payment():
    """Procesar el pago y mostrar el botón de pago"""
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
            <div style="text-align: center; padding: 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px; color: white;">
                <h3>🔒 Unlock Calculation Results</h3>
                <p style="font-size: 1.2em;">Get access to:</p>
                <ul style="list-style: none; padding: 0;">
                    <li>✓ Complete weight breakdown</li>
                    <li>✓ Flotation analysis (Criterion 1 & 2)</li>
                    <li>✓ Column requirements calculation</li>
                    <li>✓ Export MTO to Excel</li>
                    <li>✓ Export Report to PDF</li>
                </ul>
                <p style="font-size: 2em; font-weight: bold;">$49.00 USD</p>
                <p>One-time payment per report</p>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("💳 CALCULATE & PAY NOW", key="pay_button"):
            session_id, session_url = create_checkout_session()
            if session_url:
                st.session_state.checkout_session_id = session_id
                st.markdown(f'<meta http-equiv="refresh" content="0;url={session_url}">', unsafe_allow_html=True)

def calculate_all(inputs):
    """Función principal de cálculo (idéntica a la original)"""
    
    # Extraer inputs
    droof = inputs['droof']
    ddeck = inputs['ddeck']
    user_pontoons = inputs['num_pontoons']
    router = inputs['router']
    rinner = inputs['rinner']
    l = inputs['l']
    
    # Thicknesses (convert mm to m)
    t_ring_top_m = inputs['t_ring_top'] / 1000
    t_ring_bottom_m = inputs['t_ring_bottom'] / 1000
    t_rext_m = inputs['t_rext'] / 1000
    t_rint_m = inputs['t_rint'] / 1000
    t_compartment_m = inputs['t_compartment'] / 1000
    t_single_deck_m = inputs['t_single_deck'] / 1000
    
    # Additional weights
    wothers_pontoon = inputs['wothers_pontoon']
    wothers_deck = inputs['wothers_deck']
    
    # Column config
    column_type = inputs['column_type']
    column_length = inputs['column_length']
    sleeve_length = inputs['sleeve_length']
    
    # Fluid G
    g = min(inputs['g'], 0.7)  # Enforce max 0.7
    
    # Basic validations
    if droof == 0 or ddeck == 0 or user_pontoons < 4 or router == 0:
        return None, "Please enter valid values in all fields"
    
    # Check if Droof ≤ 6 m for special case
    is_small_diameter = droof <= 6.0
    
    # Radii
    X1 = ddeck / 2
    X2 = droof / 2
    
    # ----- GEOMETRIC AREAS -----
    area_ring = (np.pi / 4) * (droof**2 - ddeck**2)  # m²
    area_compartment = ((router + rinner) / 2) * ((droof - ddeck) / 2)  # m²
    area_deck = (np.pi / 4) * (ddeck**2)  # m²
    
    # ----- WEIGHT CALCULATIONS (kg) -----
    # Ring plates
    w_ring_top = area_ring * t_ring_top_m * RHO
    w_ring_bottom = area_ring * t_ring_bottom_m * RHO
    
    # Outer and inner vertical plates
    w_rext = np.pi * droof * router * t_rext_m * RHO
    w_rint = np.pi * ddeck * rinner * t_rint_m * RHO
    
    # Single deck
    w_single_deck = area_deck * t_single_deck_m * RHO
    
    # Base weights (without compartments)
    w_pontoon_base = w_ring_top + w_ring_bottom + w_rext + w_rint + wothers_pontoon
    w_deck = w_single_deck + wothers_deck
    
    # ----- COLUMN UNIT WEIGHT -----
    if column_type == '2x3':
        linear_col = LINEAR_WEIGHTS['2-Sch80']
        linear_sleeve = LINEAR_WEIGHTS['3-Sch40']
        w_unit = (linear_col * column_length) + (linear_sleeve * sleeve_length)
        assembly_capacity = ASSEMBLY_CAPACITY['2x3']
    else:  # 3x4
        linear_col = LINEAR_WEIGHTS['3-Sch80']
        linear_sleeve = LINEAR_WEIGHTS['4-Sch40']
        w_unit = (linear_col * column_length) + (linear_sleeve * sleeve_length)
        assembly_capacity = ASSEMBLY_CAPACITY['3x4']
    
    # Convert assembly capacity to kN
    assembly_capacity_kN = (assembly_capacity * GRAVITY) / 1000
    
    # ----- STEP 1: Calculate minimum required number of columns/pontoons -----
    min_required_pontoons = 0
    min_required_pontoons_prev = -1
    iterations = 0
    max_iterations = 20
    
    # Start with user input as initial guess
    test_pontoons = user_pontoons
    test_compartments = area_compartment * t_compartment_m * RHO * test_pontoons
    test_pontoon_weight = w_pontoon_base + test_compartments
    
    while min_required_pontoons != min_required_pontoons_prev and iterations < max_iterations:
        min_required_pontoons_prev = min_required_pontoons
        
        # Convert test pontoon weight to kN
        test_pontoon_weight_kN = (test_pontoon_weight * GRAVITY) / 1000
        
        # Calculate required columns
        numerator = 1.2 * test_pontoon_weight_kN + 1.6 * (CV * area_ring)
        min_required_pontoons = int(np.ceil(numerator / assembly_capacity_kN))
        
        # Update test values with new number
        test_pontoons = min_required_pontoons
        test_compartments = area_compartment * t_compartment_m * RHO * test_pontoons
        test_pontoon_weight = w_pontoon_base + test_compartments
        
        iterations += 1
    
    # ----- STEP 2: Apply user vs minimum rule -----
    final_num_pontoons = max(user_pontoons, min_required_pontoons)
    
    # ----- STEP 3: Recalculate all with final number -----
    final_compartments = area_compartment * t_compartment_m * RHO * final_num_pontoons
    final_pontoon_weight = w_pontoon_base + final_compartments
    final_pontoon_weight_kN = (final_pontoon_weight * GRAVITY) / 1000
    
    # Verify columns needed with final weight
    numerator_final = 1.2 * final_pontoon_weight_kN + 1.6 * (CV * area_ring)
    columns_needed = int(np.ceil(numerator_final / assembly_capacity_kN))
    
    # Use the maximum
    final_columns = max(final_num_pontoons, columns_needed)
    
    # If final_columns > final_num_pontoons, recalculate
    final_pontoons = final_num_pontoons
    final_compartments_adj = final_compartments
    final_pontoon_weight_adj = final_pontoon_weight
    
    if final_columns > final_num_pontoons:
        final_pontoons = final_columns
        final_compartments_adj = area_compartment * t_compartment_m * RHO * final_pontoons
        final_pontoon_weight_adj = w_pontoon_base + final_compartments_adj
    
    # ----- DECK COLUMNS -----
    w_deck_kN = (w_deck * GRAVITY) / 1000
    numerator_deck = 1.2 * w_deck_kN + 1.6 * (CV * area_deck)
    n_columns_deck = int(np.ceil(numerator_deck / assembly_capacity_kN))
    
    # ----- COLUMN WEIGHTS (kg) -----
    w_columns_pontoon = final_pontoons * w_unit
    w_columns_deck = n_columns_deck * w_unit
    
    # ----- TOTAL ROOF WEIGHT -----
    w_roof_kg = final_pontoon_weight_adj + w_deck + w_columns_pontoon + w_columns_deck
    w_roof_kN = (w_roof_kg * GRAVITY) / 1000
    
    # ----- FLOTATION CALCULATIONS -----
    gamma_fluid = g * GRAVITY
    
    # Water on deck
    Vwater = np.pi * X1**2 * H_WATER
    Wwater = GAMMA_WATER * Vwater
    
    # Geometric terms for flotation
    termA = (ddeck**2) / 4
    termB = (2*X1**2 - X1*X2 - X2**2) / 3
    denominator = termA - X1**2 + X2**2
    height_factor = l - (router - rinner)
    const_term_num = (termA - termB) * height_factor
    
    # Criterion 1 (no flooding)
    Fb1 = w_roof_kN + Wwater
    termPi1 = Fb1 / (gamma_fluid * np.pi)
    numerator1 = termPi1 - const_term_num
    H1_c1 = numerator1 / denominator
    Hflot_c1 = router - H1_c1
    
    # Criterion 2 (flooded compartments)
    num_flooded_compartments = 2 if not is_small_diameter else 1
    
    theta = num_flooded_compartments * (2 * np.pi / final_pontoons)
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
    
    # Check criteria
    passes_c1 = Hflot_c1 > 0.01
    passes_c2 = Hflot_c2 > 0.01
    
    # Determine source message
    if user_pontoons < min_required_pontoons:
        source_message = f"⚠️ User input ({user_pontoons}) < minimum required ({min_required_pontoons}) - using minimum: {final_pontoons}"
    elif user_pontoons > min_required_pontoons:
        source_message = f"✓ User input ({user_pontoons}) > minimum required ({min_required_pontoons}) - using user value: {final_pontoons}"
    else:
        source_message = f"✓ User input matches minimum required: {final_pontoons}"
    
    # Compilar resultados
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
        'wothers_pontoon': wothers_pontoon,
        'wothers_deck': wothers_deck,
        'column_type': column_type,
        'column_length': column_length,
        'sleeve_length': sleeve_length,
        'g': g,
        'X1': X1,
        'X2': X2,
        'area_ring': area_ring,
        'area_deck': area_deck,
        'area_compartment': area_compartment,
        'w_ring_top': w_ring_top,
        'w_ring_bottom': w_ring_bottom,
        'w_rext': w_rext,
        'w_rint': w_rint,
        'w_single_deck': w_single_deck,
        'w_pontoon_base': w_pontoon_base,
        'w_deck': w_deck,
        'linear_col': linear_col,
        'linear_sleeve': linear_sleeve,
        'w_unit': w_unit,
        'assembly_capacity': assembly_capacity,
        'assembly_capacity_kN': assembly_capacity_kN,
        'min_required_pontoons': min_required_pontoons,
        'iterations': iterations,
        'final_pontoons': final_pontoons,
        'final_compartments_adj': final_compartments_adj,
        'final_pontoon_weight_adj': final_pontoon_weight_adj,
        'w_columns_pontoon': w_columns_pontoon,
        'n_columns_deck': n_columns_deck,
        'w_columns_deck': w_columns_deck,
        'w_roof_kg': w_roof_kg,
        'w_roof_kN': w_roof_kN,
        'Wwater': Wwater,
        'Fb1': Fb1,
        'H1_c1': H1_c1,
        'Hflot_c1': Hflot_c1,
        'theta': theta,
        'Vpontoons_flooded': Vpontoons_flooded,
        'Wpontoons_flooded': Wpontoons_flooded,
        'Fb2': Fb2,
        'H1_c2': H1_c2,
        'Hflot_c2': Hflot_c2,
        'passes_c1': passes_c1,
        'passes_c2': passes_c2,
        'is_small_diameter': is_small_diameter,
        'source_message': source_message,
        'num_flooded_compartments': num_flooded_compartments
    }
    
    return results, None

def display_results(results):
    """Mostrar resultados (igual que el HTML original)"""
    
    format_kg = lambda x: f"{x:,.1f}"
    format_num = lambda x: f"{x:.3f}"
    
    with st.container():
        # Total roof weight
        st.markdown(f"""
            <div style="background: #edf2f7; padding: 12px; border-radius: 8px; margin-bottom: 15px;">
                <span style="font-size: 1.2em; font-weight: bold;">🏗️ TOTAL ROOF WEIGHT</span>
                <div style="display: flex; justify-content: space-between; margin-top: 8px;">
                    <span>Wroof =</span>
                    <span style="font-weight: bold; color: #2980b9;">{format_kg(results['w_roof_kg'])} kg ({format_num(results['w_roof_kN'])} kN)</span>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Weight breakdown
        with st.expander("⚙️ Weight Breakdown", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                    <div class="result-item"><span class="result-label">WRingTop:</span> <span class="result-value">{format_kg(results['w_ring_top'])} kg</span></div>
                    <div class="result-item"><span class="result-label">WRingBottom:</span> <span class="result-value">{format_kg(results['w_ring_bottom'])} kg</span></div>
                    <div class="result-item"><span class="result-label">WRext:</span> <span class="result-value">{format_kg(results['w_rext'])} kg</span></div>
                    <div class="result-item"><span class="result-label">WRint:</span> <span class="result-value">{format_kg(results['w_rint'])} kg</span></div>
                """, unsafe_allow_html=True)
            with col2:
                st.markdown(f"""
                    <div class="result-item"><span class="result-label">WCompartment ({results['final_pontoons']} pontoons):</span> <span class="result-value">{format_kg(results['final_compartments_adj'])} kg</span></div>
                    <div class="result-item"><span class="result-label">WDeck:</span> <span class="result-value">{format_kg(results['w_deck'])} kg</span></div>
                    <div class="result-item"><span class="result-label">WColumns ({results['final_pontoons']} pont + {results['n_columns_deck']} deck):</span> <span class="result-value">{format_kg(results['w_columns_pontoon'] + results['w_columns_deck'])} kg</span></div>
                """, unsafe_allow_html=True)
            st.markdown(f"""
                <div class="result-item" style="border-top: 2px solid #3498db; margin-top: 5px; padding-top: 8px;">
                    <span class="result-label">TOTAL Wroof:</span>
                    <span class="result-value" style="font-size: 1.1em;">{format_kg(results['w_roof_kg'])} kg</span>
                </div>
            """, unsafe_allow_html=True)
        
        # Column & Pontoon Summary
        st.markdown(f"""
            <div class="result-box">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 15px;">
                    <h3 style="margin: 0;">📊 Column & Pontoon Summary</h3>
                    <span class="badge">Assembly cap: {results['assembly_capacity']} kg ({format_num(results['assembly_capacity_kN'])} kN)</span>
                </div>
                <div class="result-item"><span class="result-label">Columns in Pontoons:</span> <span class="result-value">{results['final_pontoons']}</span></div>
                <div class="result-item"><span class="result-label">Number of Pontoons:</span> <span class="result-value">{results['final_pontoons']}</span></div>
                <div class="result-item"><span class="result-label">Columns in Deck:</span> <span class="result-value">{results['n_columns_deck']}</span></div>
                <div class="result-item"><span class="result-label">Unit Weight per Column:</span> <span class="result-value">{format_num(results['w_unit'])} kg</span></div>
                <div class="result-item"><span class="result-label">Minimum Required:</span> <span class="result-value">{results['min_required_pontoons']}</span></div>
                <div class="result-item"><span class="result-label">Iterations:</span> <span class="result-value">{results['iterations']}</span></div>
                <div class="result-item" style="border-top: 1px dashed #3498db; margin-top: 5px; padding-top: 8px; font-size: 0.9em; color: #e67e22;">
                    <span class="result-label">Status:</span>
                    <span class="result-value">{results['source_message']}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Small diameter note if applicable
        if results['is_small_diameter']:
            st.markdown("""
                <div class="special-note">
                    ⚠️ Since roof diameter is ≤ 6 m, API 650 Annex C requires considering <strong>1 flooded compartment</strong> instead of 2.
                </div>
            """, unsafe_allow_html=True)
        
        # Criterion 1
        st.markdown(f"""
            <div class="result-box">
                <h3 style="margin-top: 0;">💧 CRITERION 1: Roof + Water</h3>
                <div class="result-item"><span class="result-label">Water weight on deck:</span> <span class="result-value">{format_num(results['Wwater'])} kN</span></div>
                <div class="result-item"><span class="result-label">Required buoyancy force:</span> <span class="result-value">{format_num(results['Fb1'])} kN</span></div>
                <div class="result-item"><span class="result-label">Submerged depth H₁:</span> <span class="result-value">{format_num(results['H1_c1'])} m</span></div>
                <div class="result-item" style="font-weight: bold;">
                    <span class="result-label">Flotation height (freeboard):</span>
                    <span class="result-value" style="color: {'#27ae60' if results['Hflot_c1'] > 0 else '#e74c3c'};">{format_num(results['Hflot_c1'])} m</span>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Criterion 2
        st.markdown(f"""
            <div class="result-box">
                <h3 style="margin-top: 0;">⚠️ CRITERION 2: Roof + {results['num_flooded_compartments']} adjacent pontoon{'' if results['num_flooded_compartments'] == 1 else 's'} flooded</h3>
                <div class="result-item"><span class="result-label">Volume of {results['num_flooded_compartments']} pontoon{'' if results['num_flooded_compartments'] == 1 else 's'}:</span> <span class="result-value">{format_num(results['Vpontoons_flooded'])} m³</span></div>
                <div class="result-item"><span class="result-label">Fluid weight in pontoon{'' if results['num_flooded_compartments'] == 1 else 's'}:</span> <span class="result-value">{format_num(results['Wpontoons_flooded'])} kN</span></div>
                <div class="result-item"><span class="result-label">Required buoyancy force:</span> <span class="result-value">{format_num(results['Fb2'])} kN</span></div>
                <div class="result-item"><span class="result-label">Submerged depth H₁:</span> <span class="result-value">{format_num(results['H1_c2'])} m</span></div>
                <div class="result-item" style="font-weight: bold;">
                    <span class="result-label">Flotation height (freeboard):</span>
                    <span class="result-value" style="color: {'#27ae60' if results['Hflot_c2'] > 0 else '#e74c3c'};">{format_num(results['Hflot_c2'])} m</span>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Verdict
        if results['passes_c1'] and results['passes_c2']:
            st.markdown('<div class="pass">✅ ROOF FLOTATION REQUIREMENTS SATISFIED</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="fail">❌ ROOF DOES NOT MEET FLOTATION REQUIREMENTS</div>', unsafe_allow_html=True)
        
        # Geometry note
        st.markdown(f"""
            <div style="background: #eef2f7; border-radius: 6px; padding: 10px; margin-top: 15px; font-family: monospace;">
                Geometry: X₁ = {format_num(results['X1'])} m | X₂ = {format_num(results['X2'])} m | Compartments = {results['final_pontoons']} | θ for {results['num_flooded_compartments']} comp = {((results['num_flooded_compartments'] * 360) / results['final_pontoons']):.1f}°
            </div>
        """, unsafe_allow_html=True)
        
        # Botones de exportación (solo visibles después del pago)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📥 Export MTO to Excel", key="excel_btn"):
                export_to_excel(results)
        with col2:
            if st.button("📄 Export Report to PDF", key="pdf_btn"):
                export_to_pdf(results)

def export_to_excel(results):
    """Exportar a Excel (MTO)"""
    # Calcular totales
    total_plates_6mm = round(results['w_ring_top'] + results['w_ring_bottom'])
    total_plates_5mm = round(results['w_rext'] + results['w_rint'] + 
                            results['final_compartments_adj'] + results['w_single_deck'])
    total_plates = total_plates_6mm + total_plates_5mm
    
    total_cols_pont = round((results['final_pontoons'] + results['n_columns_deck']) * 
                           results['linear_col'] * results['column_length'])
    total_sleeves = round((results['final_pontoons'] + results['n_columns_deck']) * 
                         results['linear_sleeve'] * results['sleeve_length'])
    total_pipes = total_cols_pont + total_sleeves
    
    # Crear DataFrame para MTO
    data = {
        'Item': ['1', '2', '', '', '5', '6', '', ''],
        'Description': [
            f"Carbon steel plate, {results['t_ring_top']} mm thick",
            f"Carbon steel plate, {results['t_rext']} mm thick",
            "",
            "",
            f"Pipe NPS 2\", Sch 80, Carbon steel ({results['column_length']} m)",
            f"Pipe NPS 3\", Sch 40, Carbon steel ({results['sleeve_length']} m)",
            "",
            ""
        ],
        'Thickness/Qty': [
            results['t_ring_top'],
            results['t_rext'],
            "",
            "",
            results['final_pontoons'] + results['n_columns_deck'],
            results['final_pontoons'] + results['n_columns_deck'],
            "",
            ""
        ],
        'Unit Weight (kg)': [
            "",
            "",
            "",
            "",
            round(results['linear_col'] * results['column_length'], 2),
            round(results['linear_sleeve'] * results['sleeve_length'], 2),
            "",
            ""
        ],
        'Total Weight (kg)': [
            total_plates_6mm,
            total_plates_5mm,
            "",
            "",
            total_cols_pont,
            total_sleeves,
            "",
            ""
        ]
    }
    
    df = pd.DataFrame(data)
    
    # Crear archivo Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='MTO', index=False)
        
        # Añadir resumen
        summary_df = pd.DataFrame({
            'Description': ['Total Plates', 'Total Pipes', 'TOTAL ROOF WEIGHT (kg)'],
            'Weight': [total_plates, total_pipes, total_plates + total_pipes]
        })
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
    
    # Descargar
    st.download_button(
        label="📥 Download Excel",
        data=output.getvalue(),
        file_name=f"MTO_{results['tank_tag']}_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

def export_to_pdf(results):
    """Exportar a PDF con reportlab"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    elements = []
    
    # Título
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#2c3e50'),
        alignment=1,  # Center
        spaceAfter=20
    )
    elements.append(Paragraph("STORAGE TANK ROOF FLOTATION CALCULATION REPORT", title_style))
    
    # Información del proyecto
    data = [
        [f"Tank Tag: {results['tank_tag']}", f"Project: {results['project']}", f"Client: {results['client']}"],
        [f"Date: {datetime.now().strftime('%Y-%m-%d')}", "", ""]
    ]
    table = Table(data, colWidths=[doc.width/3.0]*3)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2c3e50')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dddddd'))
    ]))
    elements.append(table)
    elements.append(Spacer(1, 12))
    
    # Total roof weight
    data = [["TOTAL ROOF WEIGHT", f"{results['w_roof_kg']:,.1f} kg ({results['w_roof_kN']:.1f} kN)"]]
    table = Table(data, colWidths=[doc.width/3.0, doc.width/1.5])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 12))
    
    # Weight Breakdown
    elements.append(Paragraph("Weight Breakdown", styles['Heading2']))
    weight_data = [
        ["Component", "Weight (kg)"],
        [f"WRingTop ({results['t_ring_top']} mm)", f"{results['w_ring_top']:,.1f}"],
        [f"WRingBottom ({results['t_ring_bottom']} mm)", f"{results['w_ring_bottom']:,.1f}"],
        [f"WRext ({results['t_rext']} mm)", f"{results['w_rext']:,.1f}"],
        [f"WRint ({results['t_rint']} mm)", f"{results['w_rint']:,.1f}"],
        [f"WCompartment ({results['final_pontoons']} units)", f"{results['final_compartments_adj']:,.1f}"],
        [f"WDeck ({results['t_single_deck']} mm)", f"{results['w_single_deck']:,.1f}"],
        [f"WColumns Pontoon ({results['final_pontoons']})", f"{results['w_columns_pontoon']:,.1f}"],
        [f"WColumns Deck ({results['n_columns_deck']})", f"{results['w_columns_deck']:,.1f}"],
        ["", ""],
        ["TOTAL ROOF WEIGHT", f"{results['w_roof_kg']:,.1f}"]
    ]
    table = Table(weight_data, colWidths=[doc.width/1.8, doc.width/3.6])
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
    
    # Column Summary
    elements.append(Paragraph("Column & Pontoon Summary", styles['Heading2']))
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
    table = Table(col_data, colWidths=[doc.width/2.4, doc.width/2.4])
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
    
    # Flotation Analysis
    elements.append(Paragraph("Flotation Analysis", styles['Heading2']))
    
    # Criterion 1
    elements.append(Paragraph("Criterion 1: Roof + Water", styles['Heading3']))
    crit1_data = [
        ["Parameter", "Value"],
        ["Water weight on deck", f"{results['Wwater']:.2f} kN"],
        ["Required buoyancy force", f"{results['Fb1']:.2f} kN"],
        ["Submerged depth H₁", f"{results['H1_c1']:.3f} m"],
        ["Freeboard", f"{results['Hflot_c1']:.3f} m"]
    ]
    table = Table(crit1_data, colWidths=[doc.width/2.4, doc.width/2.4])
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
    elements.append(Spacer(1, 8))
    
    # Criterion 2
    elements.append(Paragraph(f"Criterion 2: Roof + {results['num_flooded_compartments']} adjacent pontoon{'s' if results['num_flooded_compartments'] > 1 else ''} flooded", styles['Heading3']))
    crit2_data = [
        ["Parameter", "Value"],
        [f"Volume of {results['num_flooded_compartments']} pontoon{'s' if results['num_flooded_compartments'] > 1 else ''}", f"{results['Vpontoons_flooded']:.2f} m³"],
        ["Fluid weight", f"{results['Wpontoons_flooded']:.2f} kN"],
        ["Required buoyancy force", f"{results['Fb2']:.2f} kN"],
        ["Submerged depth H₁", f"{results['H1_c2']:.3f} m"],
        ["Freeboard", f"{results['Hflot_c2']:.3f} m"]
    ]
    table = Table(crit2_data, colWidths=[doc.width/2.4, doc.width/2.4])
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
        elements.append(Paragraph("✅ ROOF FLOTATION REQUIREMENTS ARE SATISFIED", 
                                  ParagraphStyle('Conclusion', parent=styles['Heading3'], textColor=colors.HexColor('#27ae60'))))
    else:
        elements.append(Paragraph("❌ ROOF DOES NOT MEET FLOTATION REQUIREMENTS", 
                                  ParagraphStyle('Conclusion', parent=styles['Heading3'], textColor=colors.HexColor('#e74c3c'))))
    
    # Geometry note
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Geometry: X₁ = {results['X1']:.3f} m | X₂ = {results['X2']:.3f} m | Compartments = {results['final_pontoons']} | θ for {results['num_flooded_compartments']} comp = {((results['num_flooded_compartments'] * 360) / results['final_pontoons']):.1f}°", 
                              styles['Italic']))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    
    # Download
    st.download_button(
        label="📥 Download PDF",
        data=buffer,
        file_name=f"Report_{results['tank_tag']}_{datetime.now().strftime('%Y-%m-%d')}.pdf",
        mime="application/pdf"
    )

def main():
    # Header
    st.markdown('<div class="main-header"><h1>⚓ STORAGE TANK ROOF FLOTATION & WEIGHT CALCULATOR</h1></div>', unsafe_allow_html=True)
    
    # Layout
    col1, col2 = st.columns([1.2, 1])
    
    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 📝 INPUT DATA")
        
        # Project Information
        with st.expander("📋 Project Information", expanded=True):
            tank_tag = st.text_input("Tank Tag", value="TK-101")
            project = st.text_input("Project", value="Refinery Expansion")
            client = st.text_input("Client", value="Oil & Gas Corp")
        
        # Geometry
        with st.expander("📐 Geometry", expanded=True):
            # Intentar cargar imágenes (requiere archivos locales)
            try:
                img = PILImage.open("Designer (5).png")
                st.image(img, caption="Tank Geometry Diagram", use_column_width=True)
            except:
                st.info("Geometry diagram would appear here")
            
            droof = st.number_input("Roof diameter (Droof) - m", value=52.0, step=0.1)
            ddeck = st.number_input("Deck diameter (Ddeck) - m", value=47.0, step=0.1)
            num_pontoons = st.number_input("Number of Pontoons (user input)", value=12, step=1, min_value=4)
            router = st.number_input("Outer height (Router) - m", value=0.90, step=0.01)
            rinner = st.number_input("Inner height (Rinner) - m", value=0.40, step=0.01)
            l = st.number_input("Inclined side (L) - m", value=0.25, step=0.01)
        
        # Weight and Column Calculation
        with st.expander("⚖️ Weight and Column Calculation", expanded=True):
            try:
                img = PILImage.open("Roof_Weight.jpeg")
                st.image(img, caption="Roof Weight Diagram", use_column_width=True)
            except:
                st.info("Roof weight diagram would appear here")
            
            st.markdown("**Thicknesses (mm)**")
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                t_ring_top = st.number_input("t_RingTop (mm)", value=6.0, step=0.1)
                t_ring_bottom = st.number_input("t_RingBottom (mm)", value=6.0, step=0.1)
                t_rext = st.number_input("t_Rext (mm)", value=5.0, step=0.1)
                t_rint = st.number_input("t_Rint (mm)", value=5.0, step=0.1)
            with col_t2:
                t_compartment = st.number_input("t_Compartment (mm)", value=5.0, step=0.1)
                t_single_deck = st.number_input("t_SingleDeck (mm)", value=5.0, step=0.1)
            
            st.markdown("**Additional Weights (kg)**")
            col_w1, col_w2 = st.columns(2)
            with col_w1:
                wothers_pontoon = st.number_input("Wothers_pontoon (kg)", value=0, step=1)
            with col_w2:
                wothers_deck = st.number_input("Wothers_deck (kg)", value=0, step=1)
            
            st.markdown("**Column Configuration**")
            try:
                img = PILImage.open("Column.jpeg")
                st.image(img, caption="Column Diagram", use_column_width=True)
            except:
                st.info("Column diagram would appear here")
            
            column_type = st.selectbox("Column Type", options=['2x3', '3x4'], 
                                      format_func=lambda x: f"{x} (Column {x[0]}\" Sch80, Sleeve {x[2]}\" Sch40)")
            column_length = st.number_input("Column Length (m)", value=2.5, step=0.1)
            sleeve_length = st.number_input("Sleeve Length (m)", value=1.5, step=0.1)
            
            st.markdown("""
                <div style="background: #eef2f7; padding: 8px; border-radius: 5px; margin-top: 10px; font-size: 0.9em;">
                    <span style="font-weight: 600;">Fixed internal values:</span> ρ = 7850 kg/m³ | CV = 1.2 kN/m² | g = 9.81 m/s²
                </div>
            """, unsafe_allow_html=True)
        
        # Fluid Properties
        with st.expander("💧 Fluid Properties", expanded=True):
            g = st.number_input("Relative density of fluid (G) - max 0.7", value=0.7, step=0.01, min_value=0.0, max_value=0.7)
        
        # Fixed values note
        st.markdown("""
            <div style="background: #eef2f7; border-radius: 6px; padding: 15px; margin-top: 15px;">
                <p style="margin: 5px 0; color: #27ae60; font-weight: 500;">🔒 FIXED VALUES (cannot be changed):</p>
                <p style="margin: 5px 0;">Water height on deck: <strong>0.25 m</strong></p>
                <p style="margin: 5px 0;">Specific weight of water: <strong>9.81 kN/m³</strong></p>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 📊 RESULTS")
        
        # Recopilar inputs
        inputs = {
            'tank_tag': tank_tag,
            'project': project,
            'client': client,
            'droof': droof,
            'ddeck': ddeck,
            'num_pontoons': num_pontoons,
            'router': router,
            'rinner': rinner,
            'l': l,
            't_ring_top': t_ring_top,
            't_ring_bottom': t_ring_bottom,
            't_rext': t_rext,
            't_rint': t_rint,
            't_compartment': t_compartment,
            't_single_deck': t_single_deck,
            'wothers_pontoon': wothers_pontoon,
            'wothers_deck': wothers_deck,
            'column_type': column_type,
            'column_length': column_length,
            'sleeve_length': sleeve_length,
            'g': g
        }
        
        # Calcular siempre (para tener resultados listos)
        results, error = calculate_all(inputs)
        
        if error:
            st.error(error)
        else:
            # Guardar en session state
            st.session_state.last_calculation = results
            
            # Botón CALCULAR que activa el pago
            if st.button("💳 CALCULATE (requires payment)", key="calculate_btn", use_container_width=True):
                st.session_state.payment_required = True
                st.session_state.show_results = False
                st.rerun()
            
            # Lógica de pago
            if st.session_state.payment_required and not st.session_state.payment_completed:
                process_payment()
                st.info("After payment, you'll be redirected back to see the results.")
            elif st.session_state.payment_completed or not st.session_state.payment_required:
                # Mostrar resultados
                display_results(results)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Footer
    st.markdown("""
        <div style="text-align: center; margin-top: 30px; padding-top: 15px; border-top: 1px solid #dee2e6; color: #6c757d;">
            ⚡ Based on API 650 • CV = 1.2 kN/m² • ρ = 7850 kg/m³ • G max = 0.7 • CORRECTED UNITS
        </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()