import streamlit as st
import ezdxf
from ezdxf import recover
import simplekml
from pyproj import Transformer
from pathlib import Path
import random
import io

# --- CONFIGURACIÓN DE MARCA TIGO ---
TIGO_BLUE = "#00338D"
TIGO_YELLOW = "#FFF000"

st.set_page_config(
    page_title="Tigo Network Converter",
    page_icon="📡",
    layout="wide"
)

# CSS para una interfaz moderna y corporativa
st.markdown(f"""
    <style>
    .main {{ background-color: #f8f9fa; }}
    .stAlert {{ border-left: 5px solid {TIGO_BLUE}; }}
    .stButton>button {{
        background-color: {TIGO_BLUE};
        color: white;
        border-radius: 8px;
        padding: 0.5rem 2rem;
        font-weight: bold;
        border: none;
        transition: 0.3s;
    }}
    .stButton>button:hover {{
        background-color: #00266e;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
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

# --- MOTOR DE CONVERSIÓN ---
transformer = Transformer.from_crs("EPSG:32719", "EPSG:4326", always_xy=True)

def get_random_color():
    return simplekml.Color.rgb(random.randint(50,255), random.randint(50,255), random.randint(50,255))

def get_icon_url(name, layer):
    text = f"{name} {layer}".upper()
    icons = {
        "POSTE": "0", "CAMARA": "1", "MUFA": "2",
        "FIBRA": "3", "F.O": "3", "DUCTO": "4", "NODO": "5"
    }
    for key, val in icons.items():
        if key in text:
            return f"http://googleusercontent.com/maps.google.com/{val}"
    return "http://maps.google.com/mapfiles/kml/shapes/placemark_square.png"

# --- INTERFAZ ---
col1, col2 = st.columns([1, 4])
with col1:
    st.image("https://upload.wikimedia.org/wikipedia/commons/b/b0/Tigo.svg", width=120)

with col2:
    st.title("Network Engineering Converter")
    st.write("Herramienta de automatización para Red Externa")

st.markdown('<div class="tigo-card">', unsafe_allow_html=True)
st.subheader("🛰️ Configuración de Conversión")
st.info("Sistema configurado para: **EPSG:32719 (WGS 84 / UTM zone 19S)**")
uploaded_file = st.file_uploader("Selecciona el archivo DXF de Tigo", type=["dxf"])
st.markdown('</div>', unsafe_allow_html=True)

if uploaded_file:
    try:
        # Leer datos binarios
        file_bytes = uploaded_file.getvalue()

        with st.status("Procesando cartografía...", expanded=True) as status:
            st.write("Leyendo estructura DXF...")

            # El método 'recover' es el mejor para archivos pesados/dañados
            stream = io.BytesIO(file_bytes)
            doc, auditor = recover.read(stream)

            if auditor.has_errors:
                st.warning(f"Se encontraron {len(auditor.errors)} errores menores en el DXF, procediendo con la recuperación...")

            msp = doc.modelspace()
            entities = list(msp)
            total = len(entities)

            kml = simplekml.Kml()
            folders = {}
            layer_colors = {}

            progress_bar = st.progress(0)

            st.write(f"Convirtiendo {total} elementos a coordenadas GPS...")

            for i, ent in enumerate(entities):
                layer = ent.dxf.layer
                if layer not in folders:
                    folders[layer] = kml.newfolder(name=layer)
                    layer_colors[layer] = get_random_color()

                target = folders[layer]

                # --- LÓGICA POR TIPO ---
                if ent.dxftype() == "INSERT":
                    lon, lat = transformer.transform(ent.dxf.insert.x, ent.dxf.insert.y)
                    p = target.newpoint(name=layer, coords=[(lon, lat)])
                    p.style.iconstyle.icon.href = get_icon_url(ent.dxf.name, layer)
                    p.style.iconstyle.color = layer_colors[layer]
                    p.description = f"Infraestructura Tigo\nBloque: {ent.dxf.name}\nCapa: {layer}"

                elif ent.dxftype() == "LINE":
                    coords = [
                        transformer.transform(ent.dxf.start.x, ent.dxf.start.y),
                        transformer.transform(ent.dxf.end.x, ent.dxf.end.y)
                    ]
                    ls = target.newlinestring(name=layer, coords=coords)
                    ls.style.linestyle.color = layer_colors[layer]
                    ls.style.linestyle.width = 2

                elif ent.dxftype() in ["LWPOLYLINE", "POLYLINE"]:
                    try:
                        points = [transformer.transform(p[0], p[1]) for p in ent.get_points()]
                        if points:
                            ls = target.newlinestring(name=layer, coords=points)
                            ls.style.linestyle.color = layer_colors[layer]
                            ls.style.linestyle.width = 2
                    except: continue

                if i % 200 == 0:
                    progress_bar.progress((i + 1) / total)

            status.update(label="¡Conversión completada con éxito!", state="complete", expanded=False)

        st.balloons()

        # Preparar descarga
        kml_data = kml.kml()

        st.markdown('<div class="tigo-card" style="text-align: center;">', unsafe_allow_html=True)
        st.success(f"Archivo '{uploaded_file.name}' listo para Google Earth.")
        st.download_button(
            label="📥 DESCARGAR KML FINAL",
            data=kml_data,
            file_name=f"{Path(uploaded_file.name).stem}_TIGO_CONVERTED.kml",
            mime="application/vnd.google-earth.kml+xml"
        )
        st.markdown('</div>', unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Error técnico durante el proceso: {str(e)}")
        st.info("Recomendación: Verifica que el DXF no esté abierto en AutoCAD mientras lo subes.")

st.markdown("---")
st.caption("© 2026 Tigo Engineering Dept | Automatización de Redes")
