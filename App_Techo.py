import ipywidgets as widgets
from ipywidgets import HBox, VBox, Button, Output, HTML, FloatText, Dropdown
from IPython.display import display
from PIL import Image
import math

# ----------------------
# CONFIGURACIÓN
# ----------------------
lang_dd = Dropdown(options=["ES","EN"], value="ES", description="Idioma:")

# ----------------------
# TÍTULO DINÁMICO (ÚNICA ADICIÓN)
# ----------------------
title_html = HTML(
    "<h2 style='text-align:center;'>TECHO FLOTANTE EXTERNO DE CUBIERTA SIMPLE POR API 650</h2>"
)

def actualizar_titulo(change):
    if change["new"] == "ES":
        title_html.value = "<h2 style='text-align:center;'>TECHO FLOTANTE EXTERNO DE CUBIERTA SIMPLE POR API 650</h2>"
    else:
        title_html.value = "<h2 style='text-align:center;'>API 650 SINGLE DECK EXTERNAL FLOATING ROOF</h2>"

lang_dd.observe(actualizar_titulo, names="value")

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
# WIDGETS DE ENTRADA
# ----------------------
Dtecho_w = FloatText(value=Dtecho, description="Droof [m]:")
DsingleDeck_w = FloatText(value=DsingleDeck, description="DsingleDeck [m]:")
Wtech_w = FloatText(value=Wtech, description="Wroof [kg]:")  # COSMÉTICO
G_w = FloatText(value=G, description="G [-]:")
Rext_w = FloatText(value=Rext, description="Rext [m]:")
Rint_w = FloatText(value=Rint, description="Rint [m]:")
L_w = FloatText(value=L, description="L [m]:")
nPontoons_w = FloatText(value=nPontoons, description="nPontoons [-]:")
btn = Button(description="CALCULAR", button_style='info')
out = Output()

# ----------------------
# IMAGEN EN TARJETA DE ENTRADA
# ----------------------
img_path = "/content/Designer (5).png"
img_widget = widgets.Image(
    value=open(img_path, "rb").read(),
    format='png',
    layout=widgets.Layout(width="350px", height="auto")
)

# ----------------------
# TARJETA DE ENTRADA (MISMA + TÍTULO ARRIBA)
# ----------------------
input_card = VBox([
    title_html,
    Dtecho_w, DsingleDeck_w, Wtech_w, G_w, Rext_w, Rint_w, L_w, nPontoons_w
], layout=widgets.Layout(
    border="2px solid #004466",
    padding="15px",
    border_radius="10px",
    background_color="#e6f2ff",
    width="450px"
))

# ----------------------
# CONVERSIÓN DE UNIDADES AL CAMBIAR IDIOMA
# ----------------------
def actualizar_unidades(change):
    lang = change['new']
    if lang=="EN":
        Dtecho_w.value *= 3.28084
        DsingleDeck_w.value *= 3.28084
        Wtech_w.value *= 2.20462
        Rext_w.value *= 39.37
        Rint_w.value *= 39.37
        L_w.value *= 39.37
        Dtecho_w.description = "Droof [ft]:"
        DsingleDeck_w.description = "DsingleDeck [ft]:"
        Wtech_w.description = "Wroof [lb]:"
        Rext_w.description = "Rext [in]:"
        Rint_w.description = "Rint [in]:"
        L_w.description = "L [in]:"
    else:
        Dtecho_w.value /= 3.28084
        DsingleDeck_w.value /= 3.28084
        Wtech_w.value /= 2.20462
        Rext_w.value /= 39.37
        Rint_w.value /= 39.37
        L_w.value /= 39.37
        Dtecho_w.description = "Droof [m]:"
        DsingleDeck_w.description = "DsingleDeck [m]:"
        Wtech_w.description = "Wroof [kg]:"
        Rext_w.description = "Rext [m]:"
        Rint_w.description = "Rint [m]:"
        L_w.description = "L [m]:"

lang_dd.observe(actualizar_unidades, names='value')

# ----------------------
# FUNCIONES DE CÁLCULO (SIN TOCAR)
# ----------------------
def calcular(b):
    lang = lang_dd.value

    Dtecho_val = Dtecho_w.value
    DsingleDeck_val = DsingleDeck_w.value
    Wtech_val = Wtech_w.value
    G_val = G_w.value
    Rext_val = Rext_w.value
    Rint_val = Rint_w.value
    L_val = L_w.value
    nPontoons_val = nPontoons_w.value

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

    with out:
        out.clear_output()
        factor = 39.37 if lang=="EN" else 1
        unidad = "in" if lang=="EN" else "m"

        html_text = f"""
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
        """
        display(HTML(html_text))

# ----------------------
# EVENTOS Y DISPLAY
# ----------------------
btn.on_click(calcular)

display(VBox([
    lang_dd,
    HBox([input_card, img_widget]),
    btn,
    HTML("<h3>Resultados</h3>"),
    out
]))
