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
OUTPUT_DIR = os.path.join(BASE_DIR, "LST")
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

ee.Initialize(project='silken-period-402313')

# Años de estudio
YEARS_TO_ANALYZE = [2000, 2005, 2010, 2015, 2020, 2025, 2026]
CRS_TARGET = 'EPSG:32719' 
SCALE = 30 

datos_metadatos = []

# --- POLÍGONO DE ESTUDIO ACTUALIZADO ---
roi_urbano = ee.Geometry.Polygon([[
    [-71.181944, -32.962222], # Punto 1
    [-71.548056, -32.962222], # Punto 2
    [-71.548056, -33.171389], # Punto 3
    [-71.181944, -33.171389], # Punto 4
    [-71.181944, -32.962222]  # Cierre del polígono (repite Punto 1)
]])

# ==========================================================
# 2. FUNCIONES LST Y FILTROS
# ==========================================================
def prep_lst_l89(img):
    lst = img.select('ST_B10').multiply(0.00341802).add(149.0).subtract(273.15).rename('LST')
    return img.addBands(lst)

def prep_lst_l57(img):
    lst = img.select('ST_B6').multiply(0.00341802).add(149.0).subtract(273.15).rename('LST')
    return img.addBands(lst)

def obtener_coleccion(year, filtro_estacion):
    colecciones = []
    if year >= 2013:
        l8 = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2").filterBounds(roi_urbano).filter(ee.Filter.calendarRange(year, year, 'year')).filter(filtro_estacion).map(prep_lst_l89)
        colecciones.append(l8)
        if year >= 2022:
            l9 = ee.ImageCollection("LANDSAT/LC09/C02/T1_L2").filterBounds(roi_urbano).filter(ee.Filter.calendarRange(year, year, 'year')).filter(filtro_estacion).map(prep_lst_l89)
            colecciones.append(l9)
    if year <= 2011:
        l5 = ee.ImageCollection("LANDSAT/LT05/C02/T1_L2").filterBounds(roi_urbano).filter(ee.Filter.calendarRange(year, year, 'year')).filter(filtro_estacion).map(prep_lst_l57)
        colecciones.append(l5)
    if year <= 2002:
        l7 = ee.ImageCollection("LANDSAT/LE07/C02/T1_L2").filterBounds(roi_urbano).filter(ee.Filter.calendarRange(year, year, 'year')).filter(filtro_estacion).map(prep_lst_l57)
        colecciones.append(l7)
    
    if not colecciones: return ee.ImageCollection([])
    col_final = colecciones[0]
    for col in colecciones[1:]: col_final = col_final.merge(col)
    return col_final.filter(ee.Filter.lt('CLOUD_COVER', 15))

# Filtros estacionales para la zona central de Chile
filtro_verano = ee.Filter.Or(ee.Filter.dayOfYear(350, 365), ee.Filter.dayOfYear(1, 25))
filtro_invierno = ee.Filter.dayOfYear(167, 207)

# ==========================================================
# 3. BUCLE DE PROCESAMIENTO
# ==========================================================
estaciones_config = [('Verano', filtro_verano), ('Invierno', filtro_invierno)]

for year in YEARS_TO_ANALYZE:
    print(f"\n--- Analizando año {year} ---")
    
    for nombre_est, filtro in estaciones_config:
        col = obtener_coleccion(year, filtro)
        
        try:
            if col.size().getInfo() > 0:
                best_img = col.sort('CLOUD_COVER').first()
                propiedades = best_img.toDictionary().getInfo()
                
                # Extracción de metadatos solicitados
                fecha = best_img.date().format('YYYY-MM-dd').getInfo()
                hora = best_img.date().format('HH:mm:ss').getInfo()
                sol_elev = propiedades.get('SUN_ELEVATION', 'N/A')
                sol_azimuth = propiedades.get('SUN_AZIMUTH', 'N/A')
                satelite = propiedades.get('SPACECRAFT_ID', 'N/A')

                # Inclusión en la lista de metadatos
                datos_metadatos.append({
                    'Año_Estudio': year,
                    'Estacion': nombre_est,
                    'Satelite': satelite,
                    'Fecha': fecha,
                    'Hora_UTC': hora,           
                    'Elevacion_Sol': sol_elev,   
                    'Acimut_Sol': sol_azimuth,    
                    'Nubosidad': propiedades.get('CLOUD_COVER', 0)
                })

                # Exportación de la mejor imagen LST
                img_lst = best_img.select('LST').clip(roi_urbano)
                filename = os.path.join(OUTPUT_DIR, f"LST_{year}_{nombre_est}_{fecha}.tif")
                
                print(f"Exportando {nombre_est} ({fecha}) - Elevación Sol: {sol_elev}")
                geemap.ee_export_image(img_lst, filename=filename, scale=SCALE, region=roi_urbano, crs=CRS_TARGET)
            else:
                print(f"Sin datos para {year} en {nombre_est}.")
        except Exception as e:
            print(f"Error en {year} {nombre_est}: {e}")

# ==========================================================
# 4. GENERACIÓN DEL REPORTE FINAL
# ==========================================================
if datos_metadatos:
    df = pd.DataFrame(datos_metadatos)
    reporte_path = os.path.join(OUTPUT_DIR, "MetadatosLST.csv")
    df.to_csv(reporte_path, index=False, encoding='utf-8-sig', sep=';')
    print(f"\n¡Reporte actualizado con datos solares generado en: {reporte_path}")