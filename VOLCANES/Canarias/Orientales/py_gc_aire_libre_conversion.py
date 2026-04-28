# -*- coding: utf-8 -*-
"""
Created on Wed Apr 15 13:33:46 2026

@author: Usuario
"""

import geopandas as gpd
import numpy as np
from shapely.geometry import Point

# 1. Cargar tu archivo de líneas calcadas de QGIS
# (Python lee el .gpkg o .geojson directamente con todas sus columnas)


gdf_lineas = gpd.read_file('capa_ptos_medida_gran_canaria.gpkg')

# 2. Preparar una lista para guardar nuestros nuevos puntos automáticos

puntos_generados = []

# 3. Definir la distancia de muestreo
# IMPORTANTE: Como el mapa EPSG:4326 está en GRADOS, esta distancia son grados.
# 0.05 grados son aprox 5 km. Ajusta este número según la resolución que quieras.


distancia_muestreo = 0.001

# 4. El motor que extrae los puntos

for index, fila in gdf_lineas.iterrows():
    linea = fila.geometry
   
    # 1. CAMBIAMOS EL NOMBRE AQUÍ
    valor_anomalia = fila['Fa (mGal)']
   
    distancias = np.arange(0, linea.length, distancia_muestreo)
   
    for d in distancias:
        nuevo_punto = linea.interpolate(d)
       
        # 2. Y TAMBIÉN LO CAMBIAMOS AQUÍ (para que la nueva tabla se llame igual)
        puntos_generados.append({
            'geometry': nuevo_punto,
            'Fa (mGal)': valor_anomalia
        })
# 5. Convertimos la lista de puntos de vuelta a un formato espacial

gdf_puntos = gpd.GeoDataFrame(puntos_generados, crs=gdf_lineas.crs)

# 6. Sacamos las columnas X e Y para pasárselas a Harmonica / Verde

gdf_puntos['longitude'] = gdf_puntos.geometry.x
gdf_puntos['latitude'] = gdf_puntos.geometry.y

print(f"¡Éxito! De unas pocas líneas se han generado {len(gdf_puntos)} puntos equiespaciados.")

# Ahora ya le pasarías (longitude, latitude) y (Bouguer_mG) a Harmonica.


# --- GUARDAR LOS DATOS A UN ARCHIVO ---

# 1. Seleccionamos solo las 3 columnas numéricas puras que necesita Harmonica
# (Ignoramos la columna 'geometry' porque el CSV no entiende de formas espaciales)

df_final = gdf_puntos[['longitude', 'latitude', 'Fa (mGal)']]

# 2. Exportamos la tabla a un archivo CSV
df_final.to_csv('Puntos_Gran_Canaria_Completos_Fa.csv', index=False)

print("¡Archivo 'Puntos_Gran_Canarias_Completos_Fa.csv' guardado con éxito en tu carpeta!")