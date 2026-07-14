import ee
import geemap
import os
import pandas as pd
import warnings

# ==========================================================
# 1. CONFIGURACIÓN Y CONEXIÓN
# ==========================================================
warnings.filterwarnings("ignore")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Cambio de nombre de la carpeta para reflejar que ahora es NDVI
OUTPUT_DIR = os.path.join(BASE_DIR, "NDVI")
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

ee.Initialize(project='silken-period-402313')

CRS_TARGET = 'EPSG:32719' 
SCALE = 30 

datos_metadatos = []

# --- POLÍGONO DE ESTUDIO ACTUALIZADO ---
roi_urbano = ee.Geometry.Polygon([[
    [-71.181944, -32.962222], # Punto 1
    [-71.548056, -32.962222], # Punto 2
    [-71.548056, -33.171389], # Punto 3
    [-71.181944, -33.171389], # Punto 4
    [-71.181944, -32.962222]  # Cierre del polígono
]])

# ==========================================================
# 2. FECHAS OBJETIVO (Extraídas de la imagen adjunta)
# ==========================================================
# Se han convertido del formato DD-MM-YYYY al YYYY-MM-DD requerido por GEE
fechas_objetivo = [
    {"año": 2000, "estacion": "Verano",   "fecha": "2000-01-11"},
    {"año": 2000, "estacion": "Invierno", "fecha": "2000-07-12"},
    {"año": 2005, "estacion": "Verano",   "fecha": "2005-01-16"},
    {"año": 2005, "estacion": "Invierno", "fecha": "2005-06-25"},
    {"año": 2010, "estacion": "Verano",   "fecha": "2010-01-14"},
    {"año": 2010, "estacion": "Invierno", "fecha": "2010-08-26"},
    {"año": 2015, "estacion": "Verano",   "fecha": "2015-01-12"},
    {"año": 2015, "estacion": "Invierno", "fecha": "2015-07-23"},
    {"año": 2020, "estacion": "Verano",   "fecha": "2020-01-10"},
    {"año": 2020, "estacion": "Invierno", "fecha": "2020-06-25"},
    {"año": 2025, "estacion": "Verano",   "fecha": "2025-12-24"},
    {"año": 2025, "estacion": "Invierno", "fecha": "2025-07-17"},
    {"año": 2026, "estacion": "Verano",   "fecha": "2026-01-17"}
]

# ==========================================================
# 3. FUNCIONES NDVI Y FILTROS EXACTOS
# ==========================================================

# Para Landsat 8 y 9: NDVI = (NIR - Red) / (NIR + Red) -> Bandas 5 y 4
def add_ndvi_l89(img):
    ndvi = img.normalizedDifference(['SR_B5', 'SR_B4']).rename('NDVI')
    return img.addBands(ndvi)

# Para Landsat 5 y 7: NDVI = (NIR - Red) / (NIR + Red) -> Bandas 4 y 3
def add_ndvi_l57(img):
    ndvi = img.normalizedDifference(['SR_B4', 'SR_B3']).rename('NDVI')
    return img.addBands(ndvi)

def obtener_imagen_por_fecha(fecha_str):
    # Se crea un filtro de 1 día exactamente para la fecha requerida
    start = ee.Date(fecha_str)
    end = start.advance(1, 'day')
    filtro_fecha = ee.Filter.date(start, end)
    
    # Se consultan todas las colecciones para esa fecha específica
    l8 = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2").filterBounds(roi_urbano).filter(filtro_fecha).map(add_ndvi_l89)
    l9 = ee.ImageCollection("LANDSAT/LC09/C02/T1_L2").filterBounds(roi_urbano).filter(filtro_fecha).map(add_ndvi_l89)
    l5 = ee.ImageCollection("LANDSAT/LT05/C02/T1_L2").filterBounds(roi_urbano).filter(filtro_fecha).map(add_ndvi_l57)
    l7 = ee.ImageCollection("LANDSAT/LE07/C02/T1_L2").filterBounds(roi_urbano).filter(filtro_fecha).map(add_ndvi_l57)
    
    # Se fusionan para encontrar la imagen disponible de esa fecha
    col_final = l8.merge(l9).merge(l5).merge(l7)
    return col_final

# ==========================================================
# 4. BUCLE DE PROCESAMIENTO
# ==========================================================
print("Iniciando extracción de NDVI para fechas exactas...")

for item in fechas_objetivo:
    year = item['año']
    estacion = item['estacion']
    fecha_exacta = item['fecha']
    
    print(f"\n--- Buscando imagen para {fecha_exacta} ({estacion} {year}) ---")
    
    col = obtener_imagen_por_fecha(fecha_exacta)
    
    try:
        if col.size().getInfo() > 0:
            # Tomamos la primera imagen (ya está filtrada por ese día exacto)
            best_img = col.first()
            propiedades = best_img.toDictionary().getInfo()
            
            # Extracción de metadatos
            satelite = propiedades.get('SPACECRAFT_ID', 'N/A')
            sol_elev = propiedades.get('SUN_ELEVATION', 'N/A')
            sol_azimuth = propiedades.get('SUN_AZIMUTH', 'N/A')
            hora = best_img.date().format('HH:mm:ss').getInfo()

            datos_metadatos.append({
                'Año_Estudio': year,
                'Estacion': estacion,
                'Satelite': satelite,
                'Fecha': fecha_exacta,
                'Hora_UTC': hora,
                'Elevacion_Sol': sol_elev,
                'Acimut_Sol': sol_azimuth,
                'Nubosidad': propiedades.get('CLOUD_COVER', 0)
            })

            # Exportación de la banda NDVI
            img_ndvi = best_img.select('NDVI').clip(roi_urbano)
            
            # Formato de nombre que mantendrá coherencia con tu análisis posterior
            filename = os.path.join(OUTPUT_DIR, f"NDVI_{year}_{estacion}_{fecha_exacta}.tif")
            
            print(f"Exportando NDVI satélite {satelite}...")
            geemap.ee_export_image(img_ndvi, filename=filename, scale=SCALE, region=roi_urbano, crs=CRS_TARGET)
        else:
            print(f"ATENCIÓN: No se encontraron datos para la fecha {fecha_exacta}.")
    except Exception as e:
        print(f"Error procesando la fecha {fecha_exacta}: {e}")

# ==========================================================
# 5. GENERACIÓN DEL REPORTE FINAL
# ==========================================================
if datos_metadatos:
    df = pd.DataFrame(datos_metadatos)
    reporte_path = os.path.join(OUTPUT_DIR, "Metadatos_NDVI.csv")
    df.to_csv(reporte_path, index=False, encoding='utf-8-sig', sep=';')
    print(f"\n¡Proceso finalizado! Imágenes y reporte guardados en: {OUTPUT_DIR}")