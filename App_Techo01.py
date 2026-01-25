import streamlit as st
from PIL import Image
import math

# ----------------------
# CONFIGURACIÓN
# ----------------------
lang = st.selectbox("Idioma / Language:", ["ES", "EN"])

# ----------------------
# TÍTULO DINÁMICO
# ----------------------
if lang == "ES":
    st.markdown("<h2 style='text-align:center;'>TECHO FLOTANTE EXTERNO DE CUBIERTA SIMPLE POR API 650</h2>", unsafe_allow_html=True)
else:
    st.markdown("<h2 style='text-align:center;'>API 650 SINGLE DECK EXTERNAL FLOATING ROOF</h2>", unsafe_allow_html=True)

# ----------------------
# DATOS DE ENTRADA POR DEFECTO
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
# ENTRADAS STREAMLIT
# ----------------------
Dtecho_val = st.number_input("Droof [m]:" if lang=="ES" else "Droof [ft]:", value=Dtecho)
DsingleDeck_val = st.number_input("DsingleDeck [m]:" if lang=="ES" else "DsingleDeck [ft]:", value=DsingleDeck)
Wtech_val = st.number_input("Wroof [kg]:" if lang=="ES" else "Wroof [lb]:", value=Wtech)
G_val = st.number_input("G [-]:", value=G)
Rext_val = st.number_input("Rext [m]:" if lang=="ES" else "Rext [in]:", value=Rext)
Rint_val = st.number_input("Rint [m]:" if lang=="ES" else "Rint [in]:", value=Rint)
L_val = st.number_input("L [m]:" if lang=="ES" else "L [in]:", value=L)
nPontoons_val = st.number_input("nPontoons [-]:", value=nPontoons)

# ----------------------
# IMAGEN
# ----------------------
st.image("Designer (5).png", width=350)

# ----------------------
# CONVERSIÓN DE UNIDADES
# ----------------------
if lang=="EN":
    Dtecho_m = Dtecho_val * 0.3048
    DsingleDeck_m = DsingleDeck_val * 0.3048
    Wtech_kg = Wtech_val / 2.20462
    Rext_m = Rext_val / 39.37
    Rint_m = Rint_val / 39.37
    L_m = L_val / 39.37
else:
    Dtecho_m = Dtecho_val
    DsingleDeck_m = DsingleDeck_val
    Wtech_kg = Wtech_val
    Rext_m = Rext_val
    Rint_m = Rint_val
    L_m = L_val

# ----------------------
# BLOQUEO SI Droof > 10m o 33ft
# ----------------------
bloqueado = (lang=="ES" and Dtecho_val > 10) or (lang=="EN" and Dtecho_val > 33)
if bloqueado:
    st.warning("Esta sección está bloqueada hasta que realices el pago." if lang=="ES" else "This section is locked until payment is made.")
    if st.button("Pagar ahora" if lang=="ES" else "Pay now"):
        pago = True
        st.success("Pago realizado. Puedes ver la sección ahora." if lang=="ES" else "Payment completed. You can now view the section.")
    else:
        pago = False
else:
    pago = True

# ----------------------
# CÁLCULOS
# ----------------------
if pago:
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
