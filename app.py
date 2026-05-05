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
   page_title="Tigo - Convertidor de Archivos",
   page_icon="📡",
   layout="centered"
)

# Estilo personalizado para mejorar la interfaz y soportar carga de datos
st.markdown(f"""
   <style>
   .stApp {{ background-color: #f4f4f4; }}
   .stButton>button {{
       background-color: {TIGO_BLUE};
       color: white;
       border-radius: 5px;
       font-weight: bold;
       width: 100%;
   }}
   h1, h2, h3 {{ color: {TIGO_BLUE}; font-family: 'Arial', sans-serif; }}
   .stProgress > div > div > div > div {{ background-color: {TIGO_YELLOW}; }}
   </style>
   """, unsafe_allow_html=True)

# --- LÓGICA DE CONVERSIÓN OPTIMIZADA ---
# Definimos el transformador una sola vez fuera del bucle para ganar velocidad
transformer = Transformer.from_crs("EPSG:32719", "EPSG:4326", always_xy=True)

def color_kml_random():
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

# --- INTERFAZ DE USUARIO ---
st.image("https://upload.wikimedia.org/wikipedia/commons/b/b0/Tigo.svg", width=150)
st.title("Convertidor de Red Externa")
st.info("🚀 Optimizado para archivos de ingeniería pesados (EPSG:32719)")

# Aumentamos el límite de carga de archivos por si acaso (Streamlit por defecto tiene 200MB)
uploaded_file = st.file_uploader("Subir archivo DXF", type=["dxf"])

if uploaded_file is not None:
   try:
       # 1. LEER ARCHIVO COMO BYTES (Solución al error anterior)
       bytes_data = uploaded_file.getvalue()

       with st.spinner('Cargando geometría en memoria...'):
           # Usamos readbytes para evitar errores de 'utf-8' o 'cp1252'
           doc = ezdxf.readbytes(bytes_data)
           msp = doc.modelspace()
           entities = list(msp)
           total = len(entities)

       kml = simplekml.Kml()
       folders = {}
       colores = {}

       st.write(f"Procesando **{total}** entidades...")
       progress_bar = st.progress(0)

       # 2. PROCESAMIENTO POR ENTIDAD
       for i, entity in enumerate(entities):
           layer = entity.dxf.layer
           if layer not in folders:
               folders[layer] = kml.newfolder(name=layer)
               colores[layer] = color_kml_random()

           folder = folders[layer]

           # Inserción de Bloques (Postes, Cámaras, etc.)
           if entity.dxftype() == "INSERT":
               x, y = entity.dxf.insert.x, entity.dxf.insert.y
               lon, lat = transformer.transform(x, y)
               p = folder.newpoint(name=layer, coords=[(lon, lat)])
               p.style.iconstyle.icon.href = obtener_icono_por_bloque(entity.dxf.name, layer)
               p.style.iconstyle.color = colores[layer]
               p.description = f"Infraestructura Tigo\nBloque: {entity.dxf.name}\nCapa: {layer}"

           # Líneas Simples
           elif entity.dxftype() == "LINE":
               x1, y1 = entity.dxf.start.x, entity.dxf.start.y
               x2, y2 = entity.dxf.end.x, entity.dxf.end.y
               lon1, lat1 = transformer.transform(x1, y1)
               lon2, lat2 = transformer.transform(x2, y2)
               ls = folder.newlinestring(name=layer, coords=[(lon1, lat1), (lon2, lat2)])
               ls.style.linestyle.color = colores[layer]
               ls.style.linestyle.width = 2

           # Polilíneas (Ductos, Cables, Trazados largos)
           elif entity.dxftype() in ["LWPOLYLINE", "POLYLINE"]:
               try:
                   puntos_proyecto = []
                   for p_coord in entity.get_points():
                       lon, lat = transformer.transform(p_coord[0], p_coord[1])
                       puntos_proyecto.append((lon, lat))
                   if puntos_proyecto:
                       ls = folder.newlinestring(name=layer, coords=puntos_proyecto)
                       ls.style.linestyle.color = colores[layer]
                       ls.style.linestyle.width = 2
               except:
                   continue

           # Actualizar barra de progreso cada 200 entidades para no saturar la web
           if i % 200 == 0:
               progress_bar.progress((i + 1) / total)

       # 3. GENERACIÓN DEL KML
       progress_bar.progress(1.0)
       st.success("¡Conversión exitosa!")

       output = io.StringIO()
       output.write(kml.kml())

       st.download_button(
           label="💾 DESCARGAR KML FINAL",
           data=output.getvalue(),
           file_name=f"{Path(uploaded_file.name).stem}_PROCESADO.kml",
           mime="application/vnd.google-earth.kml+xml"
       )

   except Exception as e:
       st.error(f"Error crítico durante el proceso: {e}")

st.markdown("---")
st.caption("Herramienta de Ingeniería - Tigo Network Automation")
