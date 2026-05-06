import streamlit as st
import ezdxf
from ezdxf import recover
import simplekml
from pyproj import Transformer
import random
import io
from pathlib import Path

# --- CONFIGURACIÓN DE MARCA TIGO ---
TIGO_BLUE = "#00338D"
TIGO_YELLOW = "#FFF000"

st.set_page_config(
    page_title="Tigo Network Converter",
    page_icon="📡",
    layout="wide"
)

# CSS para interfaz moderna
st.markdown(f"""
    <style>
    .main {{ background-color: #f8f9fa; }}
    .stButton>button {{
        background-color: {TIGO_BLUE};
        color: white;
        border-radius: 8px;
        width: 100%;
        font-weight: bold;
        border: none;
    }}
    .tigo-card {{
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        border-top: 4px solid {TIGO_BLUE};
    }}
    </style>
    """, unsafe_allow_html=True)

def auto_detect_utm(x):
    """Detecta automáticamente la zona basado en la coordenada Este (X)"""
    if x < 350000: # Umbral típico para zona 18S en Chile
        return "EPSG:32718", "18S (Norte / Costa)"
    else:
        return "EPSG:32719", "19S (Centro / Sur)"

def get_random_color():
    return simplekml.Color.rgb(random.randint(50,255), random.randint(50,255), random.randint(50,255))

def get_icon_url(name, layer):
    text = f"{name} {layer}".upper()
    icons = {"POSTE": "0", "CAMARA": "1", "MUFA": "2", "FIBRA": "3", "F.O": "3", "DUCTO": "4", "NODO": "5"}
    for key, val in icons.items():
        if key in text:
            return f"http://googleusercontent.com/maps.google.com/{val}"
    return "http://maps.google.com/mapfiles/kml/shapes/placemark_square.png"

# --- INTERFAZ ---
col1, col2 = st.columns([1, 4])
with col1:
    st.image("https://upload.wikimedia.org/wikipedia/commons/b/b0/Tigo.svg", width=150)
with col2:
    st.title("Network Engineering Converter")
    st.write("Herramienta con Auto-Detección de Zona UTM")

st.markdown('<div class="tigo-card">', unsafe_allow_html=True)
uploaded_file = st.file_uploader("Cargar archivo DXF de Red Externa", type=["dxf"])
st.markdown('</div>', unsafe_allow_html=True)

if uploaded_file:
    try:
        file_bytes = uploaded_file.getvalue()
        stream = io.BytesIO(file_bytes)

        with st.status("Analizando cartografía...", expanded=True) as status:
            doc, auditor = recover.read(stream)
            msp = doc.modelspace()
            entities = list(msp)

            if not entities:
                st.error("El archivo no contiene entidades válidas.")
                st.stop()

            # --- LÓGICA DE DETECCIÓN ---
            # Buscamos el primer punto con coordenadas X válidas
            sample_x = 0
            for ent in entities[:50]: # Revisamos los primeros 50 elementos
                if ent.dxftype() == "INSERT":
                    sample_x = ent.dxf.insert.x
                    break
                elif hasattr(ent.dxf, 'start'):
                    sample_x = ent.dxf.start.x
                    break

            epsg_sugerido, nombre_zona = auto_detect_utm(sample_x)

            st.write(f"Coordenada X detectada: `{sample_x:.2f}`")

            col_z1, col_z2 = st.columns(2)
            with col_z1:
                st.info(f"📍 **Zona sugerida:** {nombre_zona}")
            with col_z2:
                seleccion = st.selectbox(
                    "Confirmar zona para la conversión:",
                    ["Usar sugerida", "Forzar 18S (Norte/Costa)", "Forzar 19S (Centro/Sur)"]
                )

            # Definir EPSG final
            if "18S" in seleccion: final_epsg = "EPSG:32718"
            elif "19S" in seleccion: final_epsg = "EPSG:32719"
            else: final_epsg = epsg_sugerido

            # --- PROCESAMIENTO KML ---
            transformer = Transformer.from_crs(final_epsg, "EPSG:4326", always_xy=True)
            kml = simplekml.Kml()
            folders = {}
            layer_colors = {}

            st.write(f"Iniciando conversión en {final_epsg}...")
            prog_bar = st.progress(0)

            for i, ent in enumerate(entities):
                layer = ent.dxf.layer
                if layer not in folders:
                    folders[layer] = kml.newfolder(name=layer)
                    layer_colors[layer] = get_random_color()

                target = folders[layer]

                if ent.dxftype() == "INSERT":
                    lon, lat = transformer.transform(ent.dxf.insert.x, ent.dxf.insert.y)
                    p = target.newpoint(name=layer, coords=[(lon, lat)])
                    p.style.iconstyle.icon.href = get_icon_url(ent.dxf.name, layer)
                    p.style.iconstyle.color = layer_colors[layer]

                elif ent.dxftype() == "LINE":
                    c1 = transformer.transform(ent.dxf.start.x, ent.dxf.start.y)
                    c2 = transformer.transform(ent.dxf.end.x, ent.dxf.end.y)
                    ls = target.newlinestring(name=layer, coords=[c1, c2])
                    ls.style.linestyle.color = layer_colors[layer]

                elif ent.dxftype() in ["LWPOLYLINE", "POLYLINE"]:
                    try:
                        pts = [transformer.transform(p[0], p[1]) for p in ent.get_points()]
                        if pts:
                            ls = target.newlinestring(name=layer, coords=pts)
                            ls.style.linestyle.color = layer_colors[layer]
                    except: continue

                if i % 500 == 0:
                    prog_bar.progress((i + 1) / len(entities))

            status.update(label="✅ Conversión finalizada", state="complete")

        st.success(f"Archivo procesado en {final_epsg}")
        st.download_button(
            label="📥 DESCARGAR KML FINAL",
            data=kml.kml(),
            file_name=f"{Path(uploaded_file.name).stem}_KML.kml",
            mime="application/vnd.google-earth.kml+xml"
        )

    except Exception as e:
        st.error(f"Error técnico: {e}")

st.markdown("---")
st.caption("© 2026 Tigo Network Automation | Chile Multi-Zone Support")

