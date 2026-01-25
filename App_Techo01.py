import streamlit as st
from PIL import Image
import math

# ----------------------
# CONFIGURACIÓN
# ----------------------
st.set_page_config(layout="wide")
lang = st.selectbox("Idioma / Language:", ["ES", "EN"])

# ----------------------
# TÍTULO DINÁMICO
# ----------------------
if lang == "ES":
    st.markdown("<h2 style='text-align:center;'>TECHO FLOTANTE EXTERNO DE CUBIERTA SIMPLE POR API 650</h2>", unsafe_allow_html=True)
else:
    st.markdown("<h2 style='text-align:center;'>API 650 SINGLE DECK EXTERNAL FLOATING ROOF</h2>", unsafe_allow_html=True)

# ----------------------
# DATOS POR DEFECTO
# ----------------------
Dtecho = 6.0
DsingleDeck = 4.0
Wtech = 10000.0
G = 0.7
Rext = 0.7
Rint = 0.3
L = 0.15
hagua = 0.25
nPontoons = 4

# ----------------------
# LAYOUT: DATOS + IMAGEN
# ----------------------
col1, col2 = st.columns([1, 1])

with col1:
    # Inputs
    Dtecho_val = st.number_input("Droof [m]:" if lang=="ES" else "Droof [ft]:", value=Dtecho)
    DsingleDeck_val = st.number_input("DsingleDeck [m]:" if lang=="ES" else "DsingleDeck [ft]:", value=DsingleDeck)
    Wtech_val = st.number_input("Wroof [kg]:" if lang=="ES" else "Wroof [lb]:", value=Wtech)
    G_val = st.number_input("G [-]:", value=G)
    Rext_val = st.number_input("Rext [m]:" if lang=="ES" else "Rext [in]:", value=Rext)
    Rint_val = st.number_input("Rint [m]:" if lang=="ES" else "Rint [in]:", value=Rint)
    L_val = st.number_input("L [m]:" if lang=="ES" else "L [in]:", value=L)
    nPontoons_val = st.number_input("nPontoons [-]:", value=nPontoons)
    btn = st.button("CALCULAR")

with col2:
    # Imagen permanente, más grande
    st.image("Designer (5).png", width=500)

# ----------------------
# CONVERSIÓN DE UNIDADES AUTOMÁTICA
# ----------------------
def to_m(valor, tipo):
    if lang=="EN":
        if tipo=="length":
            return valor * 0.3048
        elif tipo=="weight":
            return valor / 2.20462
        elif tipo=="inch":
            return valor / 39.37
    return valor

def to_user(valor, tipo):
    if lang=="EN":
        if tipo=="length":
            return valor * 3.28084
        elif tipo=="weight":
            return valor * 2.20462
        elif tipo=="inch":
            return valor * 39.37
    return valor

# ----------------------
# CÁLCULOS
# ----------------------
if btn:
    # Bloqueo si Droof > 10 m o 33 ft
    droof_m = Dtecho_val if lang=="ES" else Dtecho_val * 0.3048
    if (lang=="ES" and Dtecho_val > 10) or (lang=="EN" and Dtecho_val > 33):
        st.warning("Esta sección está bloqueada hasta que realices el pago." if lang=="ES" else "This section is locked until payment is made.")
    else:
        # Conversión a metros/kg para cálculos
        Dtecho_m = to_m(Dtecho_val, "length")
        DsingleDeck_m = to_m(DsingleDeck_val, "length")
        Wtech_kg = to_m(Wtech_val, "weight")
        Rext_m = to_m(Rext_val, "inch")
        Rint_m = to_m(Rint_val, "inch")
        L_m = to_m(L_val, "inch")

        Wtech_kN = Wtech_kg * 9.81 / 1000
        gammaAgua = 9.81
        gammaFluido = G_val * gammaAgua
        X1 = DsingleDeck_m / 2
        X2 = Dtecho_m / 2

        Vagua = math.pi * X1**2 * hagua
        Wagua = gammaAgua * Vagua
        Fb1 = Wtech_kN + Wagua
        numeradorH1_1 = Fb1/(gammaFluido*math.pi) - ((DsingleDeck_m**2/4 - (2*X1**2 - X1*X2 - X2**2)/3)*(L_m-(Rext_m-Rint_m)))
        denominadorH1_1 = DsingleDeck_m**2/4 - X1**2 + X2**2
        H1_1 = numeradorH1_1 / denominadorH1_1
        Hflot1 = Rext_m - H1_1

        pontoons_considered = 2 if ((lang=="ES" and Dtecho_m>6.0) or (lang=="EN" and Dtecho_val>20)) else 1
        theta = 2*math.pi / nPontoons_val
        Vpontones = pontoons_considered * (Rint_m+Rext_m)/2*(X2-X1)*theta*(X1 + ((X2-X1)*(2*Rext_m+Rint_m)/(3*(Rint_m+Rext_m))))
        Wpontones = gammaFluido * Vpontones
        Fb2 = Wtech_kN + Wpontones
        numeradorH1_2 = Fb2/(gammaFluido*math.pi) - ((DsingleDeck_m**2/4 - (2*X1**2 - X1*X2 - X2**2)/3)*(L_m-(Rext_m-Rint_m)))
        H1_2 = numeradorH1_2 / denominadorH1_1
        Hflot2 = Rext_m - H1_2

        factor = 39.37 if lang=="EN" else 1
        unidad = "in" if lang=="EN" else "m"

        st.markdown("---")
        st.markdown(f"""
        <div style='background-color:#f0f4f8; font-weight:bold; line-height:2em; padding:15px; border-radius:10px;'>

        <div style='border:2px solid #004466; padding:10px; border-radius:5px;'>
        {"Criterio 1: Agua sobre cubierta" if lang=="ES" else "Criterion 1: Water over deck"}<br>
        H1 = {H1_1*factor:.3f} {unidad}<br>
        Hflot = {Hflot1*factor:.3f} {unidad}<br>
        {'✅ El techo flota' if Hflot1>0 else '❌ El techo no flota' if lang=="ES" else '✅ The roof floats' if Hflot1>0 else '❌ The roof does not float'}
        </div><br>

        <div style='border:2px solid #004466; padding:10px; border-radius:5px;'>
        {"Criterio 2: Pontones perforados/inundados" if lang=="ES" else "Criterion 2: Perforated/flooded pontoons"}<br>
        {"Número de pontones considerados:" if lang=="ES" else "Number of pontoons considered:"} {pontoons_considered}<br>
        {(
            "Nota: Como el diámetro del techo es > 6 m, se consideran 2 pontones adyacentes inundados según API 650 Anexo C." if pontoons_considered==2 else
            "Nota: Como el diámetro del techo es ≤ 6 m, se considera 1 pontón inundado según API 650 Anexo C."
        ) if lang=="ES" else (
            "Note: As roof diameter is > 20 ft, 2 adjacent pontoons are considered flooded according to API 650 Annex C." if pontoons_considered==2 else
            "Note: As roof diameter is ≤ 20 ft, 1 pontoon is considered flooded according to API 650 Annex C."
        )}<br>
        H1 = {H1_2*factor:.3f} {unidad}<br>
        Hflot = {Hflot2*factor:.3f} {unidad}<br>
        {'✅ El techo flota' if Hflot2>0 else '❌ El techo no flota' if lang=="ES" else '✅ The roof floats' if Hflot2>0 else '❌ The roof does not float'}
        </div>
        </div>
        """, unsafe_allow_html=True)
