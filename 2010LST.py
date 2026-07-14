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
OUTPUT_DIR = os.path.join(BASE_DIR, "Tesis_LST_Export_QVA")
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

ee.Initialize(project='silken-period-402313')

# Años de estudio (Landsat 5 opera hasta 2011/2012)
YEARS_TO_ANALYZE = [2010]
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
# 2. FUNCIONES LST Y FILTROS (SOLO LANDSAT 5)
# ==========================================================
def prep_lst_l5(img):
    # Landsat 5 usa la banda ST_B6 para temperatura superficial
    lst = img.select('ST_B6').multiply(0.00341802).add(149.0).subtract(273.15).rename('LST')
    return img.addBands(lst)

def obtener_coleccion(year, filtro_estacion, max_clouds):
    # Colección exclusiva de Landsat 5
    l5 = ee.ImageCollection("LANDSAT/LT05/C02/T1_L2") \
        .filterBounds(roi_urbano) \
        .filter(ee.Filter.calendarRange(year, year, 'year')) \
        .filter(filtro_estacion) \
        .map(prep_lst_l5) \
        .filter(ee.Filter.lt('CLOUD_COVER', max_clouds))
    
    return l5

filtro_verano = ee.Filter.Or(ee.Filter.dayOfYear(1, 60), ee.Filter.dayOfYear(335, 366))
filtro_invierno = ee.Filter.dayOfYear(100, 280)

# ==========================================================
# 3. BUCLE DE PROCESAMIENTO (CON UMBRAL DINÁMICO)
# ==========================================================
estaciones_config = [('Verano', filtro_verano), ('Invierno', filtro_invierno)]

for year in YEARS_TO_ANALYZE:
    print(f"\n--- Analizando año {year} con Landsat 5 ---")
    
    for nombre_est, filtro in estaciones_config:
        
        # Umbrales progresivos de nubosidad
        umbrales_nubes = [15, 30, 50, 60, 70, 80, 90] 
        imagen_encontrada = False
        
        for umbral in umbrales_nubes:
            col = obtener_coleccion(year, filtro, max_clouds=umbral)
            
            try:
                if col.size().getInfo() > 0:
                    best_img = col.sort('CLOUD_COVER').first()
                    propiedades = best_img.toDictionary().getInfo()
                    
                    fecha = best_img.date().format('YYYY-MM-dd').getInfo()
                    hora = best_img.date().format('HH:mm:ss').getInfo()
                    sol_elev = propiedades.get('SUN_ELEVATION', 'N/A')
                    sol_azimuth = propiedades.get('SUN_AZIMUTH', 'N/A')
                    satelite = propiedades.get('SPACECRAFT_ID', 'N/A')
                    nubes_reales = propiedades.get('CLOUD_COVER', 0)

                    # Inclusión en la lista de metadatos
                    datos_metadatos.append({
                        'Año_Estudio': year,
                        'Estacion': nombre_est,
                        'Satelite': satelite,
                        'Fecha': fecha,
                        'Hora_UTC': hora,           
                        'Elevacion_Sol': sol_elev,   
                        'Acimut_Sol': sol_azimuth,    
                        'Nubosidad': nubes_reales
                    })

                    # Exportación de la mejor imagen LST
                    img_lst = best_img.select('LST').clip(roi_urbano)
                    filename = os.path.join(OUTPUT_DIR, f"LST_{year}_{nombre_est}_{fecha}_L5.tif")
                    
                    print(f"Exportando {nombre_est} ({fecha}) - Elevación Sol: {sol_elev:.2f} - Nubes: {nubes_reales:.1f}%")
                    geemap.ee_export_image(img_lst, filename=filename, scale=SCALE, region=roi_urbano, crs=CRS_TARGET)
                    
                    imagen_encontrada = True
                    break 
                    
            except Exception as e:
                pass
                
        if not imagen_encontrada:
             print(f"Sin datos aptos para {year} en {nombre_est}, ni siquiera con 90% de nubosidad.")

# ==========================================================
# 4. GENERACIÓN DEL REPORTE FINAL
# ==========================================================
if datos_metadatos:
    df = pd.DataFrame(datos_metadatos)
    reporte_path = os.path.join(OUTPUT_DIR, "Reporte_Metadatos_Tesis_L5.csv")
    df.to_csv(reporte_path, index=False, encoding='utf-8-sig', sep=';')
    print(f"\n¡Reporte actualizado generado en: {reporte_path}")
else:
    print("\nNo se extrajeron datos para el reporte.")