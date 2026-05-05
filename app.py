import streamlit as st
import ezdxf
import simplekml
from pyproj import Transformer
from pathlib import Path
import random
import io

# --- CONFIGURACIÓN DE MARCA TIGO ---
TIGO_BLUE = "#00338D"
TIGO_YELLOW = "#FFF000"

st.set_page_config(
    page_title="Tigo - Convertidor DXF a KML",
    page_icon="📡",
    layout="centered"
)

# CSS Personalizado para la identidad visual de Tigo
st.markdown(f"""
    <style>
    .stApp {{
        background-color: #f4f4f4;
    }}
    .stButton>button {{
        background-color: {TIGO_BLUE};
        color: white;
        border-radius: 5px;
        border: none;
        height: 3em;
        width: 100%;
        font-weight: bold;
    }}
    .stButton>button:hover {{
        background-color: #00266e;
        color: {TIGO_YELLOW};
    }}
    h1 {{
        color: {TIGO_BLUE};
        font-family: 'Arial Black', sans-serif;
    }}
    .stProgress > div > div > div > div {{
        background-color: {TIGO_BLUE};
    }}
    </style>
    """, unsafe_allow_html=True)

# --- LÓGICA DE CONVERSIÓN ---
transformer = Transformer.from_crs("EPSG:32719", "EPSG:4326", always_xy=True)

def convertir_a_wgs84(x, y):
    lon, lat = transformer.transform(x, y)
    return lat, lon

def color_kml_random():
    # Colores aleatorios pero vibrantes para las capas
    r, g, b = random.randint(50,255), random.randint(50,255), random.randint(50,255)
    return simplekml.Color.rgb(r, g, b)

def obtener_icono_por_bloque(nombre_bloque, layer):
    texto = f"{nombre_bloque} {layer}".upper()
    if "POSTE" in texto: return "http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png"
    elif "CAMARA" in texto: return "http://maps.google.com/mapfiles/kml/shapes/camera.png"
    elif "MUFA" in texto: return "http://maps.google.com/mapfiles/kml/shapes/target.png"
    elif "F.O" in texto or "FIBRA" in texto: return "http://maps.google.com/mapfiles/kml/shapes/placemark_circle_highlight.png"
    elif "DUCTO" in texto: return "http://maps.google.com/mapfiles/kml/shapes/line.png"
    elif "NODO" in texto: return "http://maps.google.com/mapfiles/kml/shapes/square.png"
    else: return "http://maps.google.com/mapfiles/kml/shapes/placemark_square.png"

# --- INTERFAZ ---
st.image("https://upload.wikimedia.org/wikipedia/commons/4/42/Tigo_logo.svg", width=120)
st.title("Convertidor de Red Externa")
st.subheader("Herramienta de conversión DXF a KML (WGS84)")

st.info("📌 Sistema configurado para coordenadas **EPSG:32719**.")

uploaded_file = st.file_uploader("Arrastra aquí tu archivo DXF", type=["dxf"])

if uploaded_file is not None:
    try:
        # Procesamiento
        with st.spinner('Procesando cartografía...'):
            content = uploaded_file.read().decode("utf-8", errors="ignore")
            doc = ezdxf.readstr(content)
            msp = doc.modelspace()

            kml = simplekml.Kml()
            folders = {}
            colores = {}

            entities = list(msp)
            total = len(entities)
            progress_bar = st.progress(0)

            for i, entity in enumerate(entities):
                layer = entity.dxf.layer
                if layer not in folders:
                    folders[layer] = kml.newfolder(name=layer)
                    colores[layer] = color_kml_random()

                folder = folders[layer]

                if entity.dxftype() == "INSERT":
                    p = folder.newpoint(name=layer)
                    lat, lon = convertir_a_wgs84(entity.dxf.insert.x, entity.dxf.insert.y)
                    p.coords = [(lon, lat)]
                    p.style.iconstyle.icon.href = obtener_icono_por_bloque(entity.dxf.name, layer)
                    p.style.iconstyle.color = colores[layer]
                    p.description = f"Tigo Infraestructura\nLayer: {layer}\nBloque: {entity.dxf.name}"

                elif entity.dxftype() == "LINE":
                    lat1, lon1 = convertir_a_wgs84(entity.dxf.start.x, entity.dxf.start.y)
                    lat2, lon2 = convertir_a_wgs84(entity.dxf.end.x, entity.dxf.end.y)
                    ls = folder.newlinestring(name=layer, coords=[(lon1, lat1), (lon2, lat2)])
                    ls.style.linestyle.color = colores[layer]
                    ls.style.linestyle.width = 2

                elif entity.dxftype() in ["LWPOLYLINE", "POLYLINE"]:
                    puntos = []
                    try:
                        for p_coord in entity.get_points():
                            lat, lon = convertir_a_wgs84(p_coord[0], p_coord[1])
                            puntos.append((lon, lat))
                        if puntos:
                            ls = folder.newlinestring(name=layer, coords=puntos)
                            ls.style.linestyle.color = colores[layer]
                            ls.style.linestyle.width = 2
                    except: continue

                if i % 100 == 0:
                    progress_bar.progress((i + 1) / total)

            # Generar salida
            kml_output = kml.kml()

        st.success(f"Archivo '{uploaded_file.name}' procesado con éxito.")

        # El botón de descarga ahora resalta con los colores de Tigo
        st.download_button(
            label="📥 DESCARGAR ARCHIVO KML",
            data=kml_output,
            file_name=f"{Path(uploaded_file.name).stem}_TIGO.kml",
            mime="application/vnd.google-earth.kml+xml"
        )

    except Exception as e:
        st.error(f"Se produjo un error al procesar el archivo: {e}")

st.markdown("---")
st.caption("© 2024 Tigo Network Engineering - Herramienta Interna")
