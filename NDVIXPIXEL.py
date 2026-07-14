from qgis.core import QgsProject
from osgeo import gdal
import numpy as np
import csv
import os

def analizar_ndvi_capas_qgis():
    print("=" * 60)
    print("🔍 Iniciando análisis de NDVI (Formato Vertical)...")
    print("=" * 60)

    # 1. Definir los rangos de NDVI, sus etiquetas y colores asociados
    # Se utiliza float('-inf') y float('inf') para los rangos abiertos en los extremos
    rangos_ndvi = [
        (float('-inf'), 0.2, '< 0,2', '#f7fcf5'),
        (0.2, 0.4, '0,2 - 0,4', '#c9eac2'),
        (0.4, 0.6, '0,4 - 0,6', '#7bc77c'),
        (0.6, 0.8, '0,6 - 0,8', '#2a924b'),
        (0.8, float('inf'), '> 0,8', '#00441b')
    ]

    # 2. Lista exacta de capas NDVI a analizar (según tu panel de capas)
    capas_a_analizar = [
        "NDVI2000I", "NDVI2000V", 
        "NDVI2005I", "NDVI2005V", 
        "NDVI2010I", "NDVI2010V", 
        "NDVI2015I", "NDVI2015V", 
        "NDVI2020I", "NDVI2020V", 
        "NDVI2025I", "NDVI2025V"
    ]

    # 3. Preparar encabezados para el CSV
    encabezados = ['Nombre_Capa', 'Rango_NDVI', 'Color_Hex', 'Cantidad_Pixeles', '% Pixeles']
    datos_totales = []

    # 4. Procesar cada capa
    for nombre_capa in capas_a_analizar:
        capas = QgsProject.instance().mapLayersByName(nombre_capa)
        
        if not capas:
            print(f"❌ Error: No se encontró la capa '{nombre_capa}'. Saltando...")
            continue
            
        capa = capas[0]
        ruta_raster = capa.source()
        ds = gdal.Open(ruta_raster)
        
        if ds is None:
            print(f"❌ Error al intentar abrir los datos de '{nombre_capa}'.")
            continue
            
        # Leer matriz de datos
        banda = ds.GetRasterBand(1)
        valor_nodata = banda.GetNoDataValue()
        matriz = banda.ReadAsArray()
        
        # Identificar píxeles nulos (NoData o NaN)
        if valor_nodata is not None:
            if np.isnan(valor_nodata):
                mascara_nodata = np.isnan(matriz)
            else:
                mascara_nodata = (matriz == valor_nodata) | np.isnan(matriz)
        else:
            mascara_nodata = np.isnan(matriz)
            
        pixeles_nodata = np.sum(mascara_nodata)
        pixeles_validos = matriz.size - pixeles_nodata
        
        print(f"📄 Procesando: {nombre_capa} | Píxeles Válidos: {pixeles_validos:,}")
        
        # Filtrar solo los datos numéricos reales
        datos_validos = matriz[~mascara_nodata]
        
        # Conteo por rangos de NDVI
        for min_v, max_v, etiqueta_rango, color in rangos_ndvi:
            
            # Lógica para contar según los límites del rango
            if min_v == float('-inf'):
                conteo = np.sum(datos_validos < max_v)
            elif max_v == float('inf'):
                conteo = np.sum(datos_validos > min_v)
            elif max_v == 0.8:
                # El rango de 0.6 a 0.8 es inclusivo al final
                conteo = np.sum((datos_validos >= min_v) & (datos_validos <= max_v))
            else:
                # Los rangos intermedios excluyen el límite superior para no duplicar conteos
                conteo = np.sum((datos_validos >= min_v) & (datos_validos < max_v))
                
            # Calcular porcentaje
            if pixeles_validos > 0:
                porcentaje = (conteo / pixeles_validos) * 100
            else:
                porcentaje = 0.0
                
            # Formatear el porcentaje para Excel (coma en lugar de punto y símbolo %)
            porcentaje_str = f"{porcentaje:.2f}%".replace('.', ',')
            
            # Guardar la fila en la tabla maestra
            datos_totales.append([
                nombre_capa,
                etiqueta_rango,
                color,
                int(conteo),
                porcentaje_str
            ])

    # 5. Exportar a CSV en la ruta específica solicitada
    if datos_totales:
        carpeta_destino = r'C:\Users\claudia\Downloads\Npolígono'
        os.makedirs(carpeta_destino, exist_ok=True)
            
        archivo_csv = os.path.join(carpeta_destino, 'resultados_NDVI_FormatoVertical.csv')
        
        try:
            # encoding='utf-8-sig' asegura que las tildes y símbolos se lean bien en Excel
            with open(archivo_csv, mode='w', newline='', encoding='utf-8-sig') as archivo:
                escritor_csv = csv.writer(archivo, delimiter=';')
                escritor_csv.writerow(encabezados)
                escritor_csv.writerows(datos_totales)
                
            print(f"\n✅ ¡PROCESO TERMINADO EXITOSAMENTE!")
            print(f"📊 El archivo CSV estructurado se guardó en:\n{archivo_csv}")
            
        except Exception as e:
            print(f"\n❌ ERROR al intentar guardar el archivo CSV:\n{e}")
    else:
        print("\n⚠️ No se generaron datos para exportar.")

# ==========================================
# LLAMADA DIRECTA A LA FUNCIÓN
# ==========================================
analizar_ndvi_capas_qgis()