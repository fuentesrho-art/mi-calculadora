import streamlit as st
import math
from PIL import Image

# ======================
# CONFIG STREAMLIT
# ======================
st.set_page_config(page_title="API 650 Floating Roof", layout="wide")

# ======================
# CONSTANTES
# ======================
FT_TO_M = 0.3048
M_TO_FT = 3.28084
KG_TO_LB = 2.20462
IN_TO_M = 0.0254
M_TO_IN = 39.37

# ======================
# ESTADO
# ======================
if "lang" not in st.session_state:
    st.session_state.lang = "ES"

if "paid" not in st.session_state:
    st.session_state.paid = False

if "calculate" not in st.session_state:
    st.session_state.calculate = False

# ======================
# IDIOMA
# ======================
lang = st.selectbox("Idioma:", ["ES", "EN"], index=0 if st.session_state.lang=="ES" else 1)
prev_lang = st.session_state.lang
st.session_state.lang = lang

# ======================
# TÍTULO
# ======================
st.markdown(
    f"""
    <h3 style="text-align:center;">
    {"TECHO FLOTANTE EXTERNO DE CUBIERTA SIMPLE POR API 650" if lang=="ES"
     else "API 650 SINGLE DECK EXTERNAL FLOATING ROOF"}
    </h3>
    """,
    unsafe_allow_html=True
)

# ======================
# DATOS INICIALES
# ======================
if "inputs" not in st.session_state:
    st.session_state.inputs = {
        "Dtecho": 6.0,
        "DsingleDeck": 4.0,
        "Wtech": 10000.0,
        "G": 0.7,
        "Rext": 0.7,
        "Rint": 0.3,
        "L": 0.15,
        "nPontoons": 4
    }

# ======================
# CONVERSIÓN AUTOMÁTICA
# ======================
def convert_units(to_lang):
    i = st.session_state.inputs
    if to_lang == "EN":
        i["Dtecho"] *= M_TO_FT
        i["DsingleDeck"] *= M_TO_FT
        i["Wtech"] *= KG_TO_LB
        i["Rext"] *= M_TO_IN
        i["Rint"] *= M_TO_IN
        i["L"] *= M_TO_IN
    else:
        i["Dtecho"] *= FT_TO_M
        i["DsingleDeck"] *= FT_TO_M
        i["Wtech"] /= KG_TO_LB
        i["Rext"] *= IN_TO_M
        i["Rint"] *= IN_TO_M
        i["L"] *= IN_TO_M

if prev_lang != lang:
    convert_units(lang)

# ======================
# LAYOUT INPUTS + IMAGEN
# ======================
col_inputs, col_img = st.columns([1.2, 1])

with col_inputs:
    st.markdown("### Datos de entrada")
    i = st.session_state.inputs

    i["Dtecho"] = st.number_input(f"Droof [{'m' if lang=='ES' else 'ft'}]", value=i["Dtecho"])
    i["DsingleDeck"] = st.number_input(f"DsingleDeck [{'m' if lang=='ES' else 'ft'}]", value=i["DsingleDeck"])
    i["Wtech"] = st.number_input(f"Wroof [{'kg' if lang=='ES' else 'lb'}]", value=i["Wtech"])
    i["G"] = st.number_input("G [-]", value=i["G"])
    i["Rext"] = st.number_input(f"Rext [{'m' if lang=='ES' else 'in'}]", value=i["Rext"])
    i["Rint"] = st.number_input(f"Rint [{'m' if lang=='ES' else 'in'}]", value=i["Rint"])
    i["L"] = st.number_input(f"L [{'m' if lang=='ES' else 'in'}]", value=i["L"])
    i["nPontoons"] = st.number_input("nPontoons [-]", value=i["nPontoons"], step=1)

with col_img:
    img = Image.open("Designer (5).png")
    st.image(img, use_container_width=True)

# ======================
# BOTÓN CALCULAR
# ======================
if st.button("CALCULAR" if lang=="ES" else "CALCULATE"):
    st.session_state.calculate = True

# ======================
# BLOQUEO POR DIÁMETRO
# ======================
D_limit = 10 if lang=="ES" else 32.808
blocked = i["Dtecho"] > D_limit and not st.session_state.paid

if blocked:
    st.error(
        "🔒 Diámetro mayor al permitido. Debe pagar para continuar."
        if lang=="ES"
        else "🔒 Roof diameter exceeds free limit. Payment required."
    )
    st.link_button(
        "💳 Pagar y desbloquear" if lang=="ES" else "💳 Pay to unlock",
        url="https://buy.stripe.com/test_XXXXXXXXXX"
    )
    st.stop()

# ======================
# CÁLCULOS (INTOCADOS)
# ======================
if st.session_state.calculate:

    Dtecho = i["Dtecho"] * (FT_TO_M if lang=="EN" else 1)
    DsingleDeck = i["DsingleDeck"] * (FT_TO_M if lang=="EN" else 1)
    Wtech = i["Wtech"] / KG_TO_LB if lang=="EN" else i["Wtech"]
    Rext = i["Rext"] * IN_TO_M if lang=="EN" else i["Rext"]
    Rint = i["Rint"] * IN_TO_M if lang=="EN" else i["Rint"]
    L = i["L"] * IN_TO_M if lang=="EN" else i["L"]
    nP = i["nPontoons"]

    hagua = 0.25
    gammaAgua = 9.81
    gammaFluido = i["G"] * gammaAgua
    Wtech_kN = Wtech * 9.81 / 1000

    X1 = DsingleDeck / 2
    X2 = Dtecho / 2

    Vagua = math.pi * X1**2 * hagua
    Wagua = gammaAgua * Vagua

    Fb1 = Wtech_kN + Wagua
    den = DsingleDeck**2/4 - X1**2 + X2**2
    num1 = Fb1/(gammaFluido*math.pi) - ((DsingleDeck**2/4 - (2*X1**2 - X1*X2 - X2**2)/3)*(L-(Rext-Rint)))
    H1_1 = num1 / den
    Hflot1 = Rext - H1_1

    pontoons = 2 if ((lang=="ES" and Dtecho>6) or (lang=="EN" and i["Dtecho"]>20)) else 1
    theta = 2*math.pi/nP
    Vpont = pontoons*(Rint+Rext)/2*(X2-X1)*theta*(X1 + ((X2-X1)*(2*Rext+Rint)/(3*(Rint+Rext))))
    Wpont = gammaFluido * Vpont

    Fb2 = Wtech_kN + Wpont
    num2 = Fb2/(gammaFluido*math.pi) - ((DsingleDeck**2/4 - (2*X1**2 - X1*X2 - X2**2)/3)*(L-(Rext-Rint)))
    H1_2 = num2 / den
    Hflot2 = Rext - H1_2

    factor = M_TO_IN if lang=="EN" else 1
    unit = "in" if lang=="EN" else "m"

    st.markdown("### Resultados")

    st.markdown(f"""
    **{"Criterio 1: Agua sobre cubierta" if lang=="ES" else "Criterion 1: Water over deck"}**  
    H1 = {H1_1*factor:.3f} {unit}  
    Hflot = {Hflot1*factor:.3f} {unit}  
    {"❌ El techo no flota" if Hflot1<=0 else "✅ El techo flota"}
    """)

    st.markdown("---")

    st.markdown(f"""
    **{"Criterio 2: Pontones perforados/inundados" if lang=="ES" else "Criterion 2: Perforated/flooded pontoons"}**  
    {"Número de pontones considerados" if lang=="ES" else "Number of pontoons considered"}: {pontoons}  

    {"Nota: Como el diámetro del techo es ≤ 6 m, se considera 1 pontón inundado según API 650 Anexo C."
     if lang=="ES" and pontoons==1 else
     "Nota: Como el diámetro del techo es > 6 m, se consideran 2 pontones adyacentes inundados según API 650 Anexo C."
     if lang=="ES" else
     "Note: As roof diameter is ≤ 20 ft, 1 pontoon is considered flooded according to API 650 Annex C."
     if pontoons==1 else
     "Note: As roof diameter is > 20 ft, 2 adjacent pontoons are considered flooded according to API 650 Annex C."
    }

    H1 = {H1_2*factor:.3f} {unit}  
    Hflot = {Hflot2*factor:.3f} {unit}  
    {"❌ El techo no flota" if Hflot2<=0 else "✅ El techo flota"}
    """)
