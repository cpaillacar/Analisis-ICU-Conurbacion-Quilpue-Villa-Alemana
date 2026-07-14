from qgis.core import QgsProject
from osgeo import gdal
import numpy as np
import csv
import os

def analizar_temperatura_capas_qgis():
    print("=" * 60)
    print("🔍 Iniciando análisis térmico (Formato Vertical)...")
    print("=" * 60)

    # 1. Definir los rangos de temperatura y sus colores asociados
    rangos_termicos = [
        (0, 5, '#30123b'),
        (5, 10, '#4662d8'),
        (10, 15, '#35abf8'),
        (15, 20, '#1be5b5'),
        (20, 25, '#74fe5d'),
        (25, 30, '#c9ef34'),
        (30, 35, '#fbb938'),
        (35, 40, '#f56918'),
        (40, 45, '#c92903'),
        (45, 50, '#7a0403')
    ]

    # 2. Lista exacta de capas a analizar
    capas_a_analizar = [
        "LST2000I", "LST2000V", 
        "LST2005I", "LST2005V", 
        "LST2010I", "LST2010V", 
        "LST2015I", "LST2015V", 
        "LST2020I", "LST2020V", 
        "LST2025I", "LST2025V"
    ]

    # 3. Preparar encabezados para el CSV (Formato idéntico a tu imagen)
    encabezados = ['Nombre_Capa', 'Rango_Termico', 'Color_Hex', 'Cantidad_Pixeles', '% Pixeles']
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
        
        # Conteo por rangos térmicos (Generamos una fila individual por cada rango)
        for min_t, max_t, color in rangos_termicos:
            # Lógica inclusiva al final
            if max_t == 50:
                conteo = np.sum((datos_validos >= min_t) & (datos_validos <= max_t))
            else:
                conteo = np.sum((datos_validos >= min_t) & (datos_validos < max_t))
                
            # Calcular porcentaje
            if pixeles_validos > 0:
                porcentaje = (conteo / pixeles_validos) * 100
            else:
                porcentaje = 0.0
                
            # Crear etiqueta del rango (Ej: "05 - 10")
            if min_t == 0:
                rango_str = "0 - 5"
            elif min_t == 5:
                rango_str = "05 - 10"
            else:
                rango_str = f"{min_t} - {max_t}"
                
            # Formatear el porcentaje para Excel (coma en lugar de punto y símbolo %)
            porcentaje_str = f"{porcentaje:.2f}%".replace('.', ',')
            
            # Guardar la fila en la tabla maestra
            datos_totales.append([
                nombre_capa,
                rango_str,
                color,
                int(conteo),
                porcentaje_str
            ])

    # 5. Exportar a CSV en la ruta específica
    if datos_totales:
        carpeta_destino = r'C:\Users\claudia\Downloads\Npolígono'
        os.makedirs(carpeta_destino, exist_ok=True)
            
        archivo_csv = os.path.join(carpeta_destino, 'resultados_LST_FormatoVertical.csv')
        
        try:
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
analizar_temperatura_capas_qgis()