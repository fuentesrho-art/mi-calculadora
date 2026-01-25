import streamlit as st
from PIL import Image
import math

# ----------------------
# CONFIGURACIÓN
# ----------------------
lang = st.selectbox("Idioma:", ["ES", "EN"])

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
# UNIDADES AUTOMÁTICAS
# ----------------------
def convertir_unidades(lang, Dtecho, DsingleDeck, Wtech, Rext, Rint, L):
    if lang=="EN":
        return (Dtecho*3.28084, DsingleDeck*3.28084, Wtech*2.20462, Rext*39.37, Rint*39.37, L*39.37)
    else:
        return (Dtecho, DsingleDeck, Wtech, Rext, Rint, L)

Droof_val, DsingleDeck_val, Wroof_val, Rext_val, Rint_val, L_val = convertir_unidades(lang, Dtecho, DsingleDeck, Wtech, Rext, Rint, L)

# ----------------------
# ETIQUETAS CON UNIDAD
# ----------------------
droof_label = "Droof [ft]:" if lang=="EN" else "Droof [m]:"
dsingle_label = "DsingleDeck [ft]:" if lang=="EN" else "DsingleDeck [m]:"
wroof_label = "Wroof [lb]:" if lang=="EN" else "Wroof [kg]:"
rext_label = "Rext [in]:" if lang=="EN" else "Rext [m]:"
rint_label = "Rint [in]:" if lang=="EN" else "Rint [m]:"
l_label = "L [in]:" if lang=="EN" else "L [m]:"

# ----------------------
# CASILLAS DE ENTRADA MÁS CORTAS
# ----------------------
col1, col2 = st.columns([1,1])  # datos a la izquierda, imagen a la derecha
with col1:
    Droof = st.number_input(droof_label, value=Droof_val, step=0.1, format="%.3f")
    DsingleDeck_input = st.number_input(dsingle_label, value=DsingleDeck_val, step=0.1, format="%.3f")
    Wroof_input = st.number_input(wroof_label, value=Wroof_val, step=10.0, format="%.1f")
    G_input = st.number_input("G [-]:", value=G, step=0.01, format="%.2f")
    Rext_input = st.number_input(rext_label, value=Rext_val, step=0.01, format="%.3f")
    Rint_input = st.number_input(rint_label, value=Rint_val, step=0.01, format="%.3f")
    L_input = st.number_input(l_label, value=L_val, step=0.01, format="%.3f")
    nPontoons_input = st.number_input("nPontoons [-]:", value=nPontoons, step=1)

    # ----------------------
    # BOTÓN CALCULAR
    # ----------------------
    calcular_btn = st.button("CALCULAR")

    # ----------------------
    # BLOQUEO: si Droof > 10 m o su equivalente en ft
    # ----------------------
    if (lang=="ES" and Droof>10.0) or (lang=="EN" and Droof>32.8084):
        st.warning("🚫 Debes pagar para calcular este techo.")
        # BOTÓN DE PAGO SIMULADO
        if st.button("Paga aquí"):
            st.success("✅ Pago confirmado (simulado). Ahora puedes calcular.")
            bloqueado = False
        else:
            bloqueado = True
    else:
        bloqueado = False

# ----------------------
# IMAGEN AL LADO
# ----------------------
with col2:
    image = Image.open("Designer (5).png")
    st.image(image, use_column_width=True)

# ----------------------
# FUNCIONES DE CÁLCULO
# ----------------------
def calcular_techo(Dtecho_val, DsingleDeck_val, Wtech_val, G_val, Rext_val, Rint_val, L_val, nPontoons_val, lang):
    # convertir todo a metros/kg si está en EN
    if lang=="EN":
        Dtecho_m = Dtecho_val*0.3048
        DsingleDeck_m = DsingleDeck_val*0.3048
        Wtech_kg = Wtech_val/2.20462
        Rext_m = Rext_val/39.37
        Rint_m = Rint_val/39.37
        L_m = L_val/39.37
    else:
        Dtecho_m = Dtecho_val
        DsingleDeck_m = DsingleDeck_val
        Wtech_kg = Wtech_val
        Rext_m = Rext_val
        Rint_m = Rint_val
        L_m = L_val

    Wtech_kN = Wtech_kg*9.81/1000
    gammaAgua = 9.81
    gammaFluido = G_val*gammaAgua
    X1 = DsingleDeck_m/2
    X2 = Dtecho_m/2
    Vagua = math.pi*X1**2*hagua
    Wagua = gammaAgua*Vagua
    Fb1 = Wtech_kN + Wagua
    numeradorH1_1 = Fb1/(gammaFluido*math.pi) - ((DsingleDeck_m**2/4 - (2*X1**2 - X1*X2 - X2**2)/3)*(L_m-(Rext_m-Rint_m)))
    denominadorH1_1 = DsingleDeck_m**2/4 - X1**2 + X2**2
    H1_1 = numeradorH1_1 / denominadorH1_1
    Hflot1 = Rext_m - H1_1

    pontoons_considered = 2 if ((lang=="ES" and Dtecho_m>6.0) or (lang=="EN" and Dtecho_val>20)) else 1
    theta = 2*math.pi/nPontoons_val
    Vpontones = pontoons_considered*(Rint_m+Rext_m)/2*(X2-X1)*theta*(X1 + ((X2-X1)*(2*Rext_m+Rint_m)/(3*(Rint_m+Rext_m))))
    Wpontones = gammaFluido*Vpontones
    Fb2 = Wtech_kN + Wpontones
    numeradorH1_2 = Fb2/(gammaFluido*math.pi) - ((DsingleDeck_m**2/4 - (2*X1**2 - X1*X2 - X2**2)/3)*(L_m-(Rext_m-Rint_m)))
    H1_2 = numeradorH1_2/denominadorH1_1
    Hflot2 = Rext_m - H1_2

    # resultado en unidad original
    factor = 3.28084 if lang=="EN" else 1
    unidad = "ft" if lang=="EN" else "m"

    return (H1_1*factor, Hflot1*factor, H1_2*factor, Hflot2*factor, pontoons_considered, unidad)

# ----------------------
# MOSTRAR RESULTADOS
# ----------------------
if calcular_btn and not bloqueado:
    H1_1, Hflot1, H1_2, Hflot2, pontoons_considered, unidad = calcular_techo(
        Droof, DsingleDeck_input, Wroof_input, G_input, Rext_input, Rint_input, L_input, nPontoons_input, lang
    )

    st.markdown("### Resultados")
    st.markdown(f"**Criterio 1: Agua sobre cubierta**\n\nH1 = {H1_1:.3f} {unidad}\nHflot = {Hflot1:.3f} {unidad}\n" +
                ("✅ El techo flota" if Hflot1>0 else "❌ El techo no flota"))
    st.markdown(f"**Criterio 2: Pontones perforados/inundados**\n\nNúmero de pontones considerados: {pontoons_considered}\n" +
                ("Nota: Como el diámetro del techo es > 6 m, se consideran 2 pontones adyacentes inundados según API 650 Anexo C." if pontoons_considered==2 else
                 "Nota: Como el diámetro del techo es ≤ 6 m, se considera 1 pontón inundado según API 650 Anexo C.") +
                f"\nH1 = {H1_2:.3f} {unidad}\nHflot = {Hflot2:.3f} {unidad}\n" +
                ("✅ El techo flota" if Hflot2>0 else "❌ El techo no flota"))
