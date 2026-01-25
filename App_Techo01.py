import streamlit as st
from PIL import Image
import math

# ----------------------
# Configuración inicial
# ----------------------
if 'lang' not in st.session_state:
    st.session_state.lang = 'ES'

if 'lock_inputs' not in st.session_state:
    st.session_state.lock_inputs = False

# ----------------------
# Valores por defecto
# ----------------------
default_vals = {
    'Dtecho': 6.0,
    'DsingleDeck': 4.0,
    'Wtech': 10000.0,
    'G': 0.7,
    'Rext': 0.7,
    'Rint': 0.3,
    'L': 0.15,
    'hagua': 0.25,
    'nPontoons': 4
}

# ----------------------
# Función para convertir unidades
# ----------------------
def convert_input(val, from_unit, to_unit):
    if from_unit == to_unit:
        return val
    # m <-> ft
    if from_unit=='m' and to_unit=='ft':
        return val*3.28084
    if from_unit=='ft' and to_unit=='m':
        return val/3.28084
    # kg <-> lb
    if from_unit=='kg' and to_unit=='lb':
        return val*2.20462
    if from_unit=='lb' and to_unit=='kg':
        return val/2.20462
    # m <-> in
    if from_unit=='m' and to_unit=='in':
        return val*39.37
    if from_unit=='in' and to_unit=='m':
        return val/39.37
    return val

# ----------------------
# Título dinámico
# ----------------------
st.sidebar.selectbox("Idioma", ["ES", "EN"], index=0, key='lang')
lang = st.session_state.lang

titulo = "TECHO FLOTANTE EXTERNO DE CUBIERTA SIMPLE POR API 650" if lang=="ES" else "API 650 SINGLE DECK EXTERNAL FLOATING ROOF"
st.markdown(f"## {titulo}")

# ----------------------
# Imagen en la tarjeta de datos
# ----------------------
img = Image.open("/content/Designer (5).png")
st.image(img, use_column_width=True)

# ----------------------
# Bloqueo de inputs
# ----------------------
lock = st.checkbox("Bloquear inputs", value=st.session_state.lock_inputs, key='lock_inputs')

# ----------------------
# Inputs de datos de entrada
# ----------------------
unit_length = 'm' if lang=="ES" else 'ft'
unit_weight = 'kg' if lang=="ES" else 'lb'

col1, col2 = st.columns(2)

with col1:
    Droof = st.number_input(f"Droof [{unit_length}]:", 
                            value=convert_input(default_vals['Dtecho'], 'm', unit_length), 
                            disabled=lock)
    DsingleDeck = st.number_input(f"DsingleDeck [{unit_length}]:", 
                                  value=convert_input(default_vals['DsingleDeck'], 'm', unit_length), 
                                  disabled=lock)
    Wroof = st.number_input(f"Wroof [{unit_weight}]:", 
                            value=convert_input(default_vals['Wtech'], 'kg', unit_weight), 
                            disabled=lock)
    G = st.number_input(f"G [-]:", value=default_vals['G'], disabled=lock)

with col2:
    Rext = st.number_input(f"Rext [{unit_length}]:", value=convert_input(default_vals['Rext'], 'm', unit_length), disabled=lock)
    Rint = st.number_input(f"Rint [{unit_length}]:", value=convert_input(default_vals['Rint'], 'm', unit_length), disabled=lock)
    L = st.number_input(f"L [{unit_length}]:", value=convert_input(default_vals['L'], 'm', unit_length), disabled=lock)
    nPontoons = st.number_input(f"nPontoons [-]:", value=default_vals['nPontoons'], disabled=lock)

# ----------------------
# Botón calcular
# ----------------------
if st.button("CALCULAR"):
    # Convertir inputs a unidades internas para cálculo
    if lang=="EN":
        Dtecho_m = convert_input(Droof, 'ft', 'm')
        DsingleDeck_m = convert_input(DsingleDeck, 'ft', 'm')
        Wtech_kg = convert_input(Wroof, 'lb', 'kg')
        Rext_m = convert_input(Rext, 'in', 'm') if Rext>10 else convert_input(Rext, 'ft', 'm')
        Rint_m = convert_input(Rint, 'in', 'm') if Rint>10 else convert_input(Rint, 'ft', 'm')
        L_m = convert_input(L, 'in', 'm') if L>10 else convert_input(L, 'ft', 'm')
    else:
        Dtecho_m = Droof
        DsingleDeck_m = DsingleDeck
        Wtech_kg = Wroof
        Rext_m = Rext
        Rint_m = Rint
        L_m = L

    gammaAgua = 9.81
    gammaFluido = G*gammaAgua
    Wtech_kN = Wtech_kg*9.81/1000
    X1 = DsingleDeck_m/2
    X2 = Dtecho_m/2

    # Criterio 1
    Vagua = math.pi*X1**2*default_vals['hagua']
    Wagua = gammaAgua*Vagua
    Fb1 = Wtech_kN + Wagua
    numeradorH1_1 = Fb1/(gammaFluido*math.pi) - ((DsingleDeck_m**2/4 - (2*X1**2 - X1*X2 - X2**2)/3)*(L_m-(Rext_m-Rint_m)))
    denominadorH1_1 = DsingleDeck_m**2/4 - X1**2 + X2**2
    H1_1 = numeradorH1_1 / denominadorH1_1
    Hflot1 = Rext_m - H1_1

    # Criterio 2
    pontoons_considered = 2 if ((lang=="ES" and Dtecho_m>6.0) or (lang=="EN" and Droof>20)) else 1
    theta = 2*math.pi/nPontoons
    Vpontones = pontoons_considered*(Rint_m+Rext_m)/2*(X2-X1)*theta*(X1 + ((X2-X1)*(2*Rext_m+Rint_m)/(3*(Rint_m+Rext_m))))
    Wpontones = gammaFluido*Vpontones
    Fb2 = Wtech_kN + Wpontones
    numeradorH1_2 = Fb2/(gammaFluido*math.pi) - ((DsingleDeck_m**2/4 - (2*X1**2 - X1*X2 - X2**2)/3)*(L_m-(Rext_m-Rint_m)))
    H1_2 = numeradorH1_2/denominadorH1_1
    Hflot2 = Rext_m - H1_2

    # ----------------------
    # Mostrar resultados
    # ----------------------
    unit_display = 'in' if lang=="EN" else 'm'
    factor = 39.37 if lang=="EN" else 1

    st.markdown("### Resultados")
    st.markdown(f"**{('Criterio 1: Agua sobre cubierta' if lang=='ES' else 'Criterion 1: Water over deck')}**  \n"
                f"H1 = {H1_1*factor:.3f} {unit_display}  \n"
                f"Hflot = {Hflot1*factor:.3f} {unit_display}  \n"
                f"{'✅ El techo flota' if Hflot1>0 else '❌ El techo no flota' if lang=='ES' else '✅ The roof floats' if Hflot1>0 else '❌ The roof does not float'}  \n\n"
                f"**{('Criterio 2: Pontones perforados/inundados' if lang=='ES' else 'Criterion 2: Perforated/flooded pontoons')}**  \n"
                f"{('Número de pontones considerados:' if lang=='ES' else 'Number of pontoons considered:')} {pontoons_considered}  \n"
                f"{('Nota: Como el diámetro del techo es > 6 m, se consideran 2 pontones adyacentes inundados según API 650 Anexo C.' if pontoons_considered==2 else 'Nota: Como el diámetro del techo es ≤ 6 m, se considera 1 pontón inundado según API 650 Anexo C.') if lang=='ES' else ('Note: As roof diameter is > 20 ft, 2 adjacent pontoons are considered flooded according to API 650 Annex C.' if pontoons_considered==2 else 'Note: As roof diameter is ≤ 20 ft, 1 pontoon is considered flooded according to API 650 Annex C.')}  \n"
                f"H1 = {H1_2*factor:.3f} {unit_display}  \n"
                f"Hflot = {Hflot2*factor:.3f} {unit_display}  \n"
                f"{'✅ El techo flota' if Hflot2>0 else '❌ El techo no flota' if lang=='ES' else '✅ The roof floats' if Hflot2>0 else '❌ The roof does not float'}")
