import streamlit as st
import ezdxf
import simplekml
from pyproj import Transformer
from pathlib import Path
import random
import io

# --- CONFIGURACIÓN DE MARCA ---
# Usando la paleta oficial para la interfaz
COLOR_PRIMARIO = "#00338D"  # Azul Institucional
COLOR_ACENTO = "#FFF000"    # Dorado/Amarillo

st.set_page_config(
    page_title="Convertidor Archivos",
    page_icon="📡",
    layout="centered"
)

# Inyección de Estilo para forzar los colores
st.markdown(f"""
    <style>
    /* Fondo de la app */
    .stApp {{
        background-color: #f8f9fa;
    }}
    /* Título Principal */
    h1 {{
        color: {COLOR_PRIMARIO} !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-weight: 800;
        text-align: center;
    }}
    /* Botón de carga y descarga */
    .stButton>button {{
        background-color: {COLOR_PRIMARIO};
        color: white !important;
        border-radius: 8px;
        border: none;
        font-weight: bold;
    }}
    .stButton>button:hover {{
        border: 2px solid {COLOR_ACENTO};
        color: {COLOR_ACENTO} !important;
    }}
    /* Etiquetas y textos */
    .stMarkdown p {{
        color: #333333;
    }}
    /* Barra de progreso */
    .stProgress > div > div > div > div {{
        background-color: {COLOR_PRIMARIO};
    }}
    </style>
    """, unsafe_allow_html=True)

# --- LÓGICA DE CONVERSIÓN ---
transformer = Transformer.from_crs("EPSG:32719", "EPSG:4326", always_xy=True)

def convertir_a_wgs84(x, y):
    lon, lat = transformer.transform(x, y)
    return lat, lon

def color_kml_random():
    r, g, b = random.randint(50,255), random.randint(50,255), random.randint(50,255)
    return simplekml.Color.rgb(r, g, b)

# --- INTERFAZ ---
# Logo (usando un placeholder oficial si el anterior falló)
st.image("https://upload.wikimedia.org/wikipedia/commons/b/b0/Tigo.svg", width=150)
st.title("Convertidor Archivos")
st.subheader("Ingeniería de Red - Conversión DXF a KML")

st.warning("📍 Coordenadas configuradas: **EPSG:32719 (WGS 84 / UTM zone 19S)**")

uploaded_file = st.file_uploader("Arrastra aquí el archivo DXF para procesar", type=["dxf"])

if uploaded_file is not None:
    try:
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
                    p.style.iconstyle.color = colores[layer]
                    p.description = f"Infraestructura\nLayer: {layer}"

                elif entity.dxftype() in ["LINE", "LWPOLYLINE", "POLYLINE"]:
                    puntos = []
                    try:
                        if entity.dxftype() == "LINE":
                            p1 = convertir_a_wgs84(entity.dxf.start.x, entity.dxf.start.y)
                            p2 = convertir_a_wgs84(entity.dxf.end.x, entity.dxf.end.y)
                            puntos = [(p1[1], p1[0]), (p2[1], p2[0])]
                        else:
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

            kml_output = kml.kml()

        st.success(f"Procesamiento de '{uploaded_file.name}' terminado.")

        st.download_button(
            label="📥 DESCARGAR KML",
            data=kml_output,
            file_name=f"{Path(uploaded_file.name).stem}_Convertido.kml",
            mime="application/vnd.google-earth.kml+xml"
        )

    except Exception as e:
        st.error(f"Error técnico: {e}")

st.markdown("---")
st.caption("Herramienta de Automatización de Redes")
