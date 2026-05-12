# -*- coding: utf-8 -*-
"""
Created on Mon Apr 27 11:20:11 2026

@author: Usuario
"""
import pandas as pd
import numpy as np
import pygmt
import os

# =============================================================================
# BLOQUE 1: CARGAR DATOS DIGITALIZADOS
# =============================================================================
print("1. Cargando datos del mapa digitalizado de La Gomera...")

# Ajusta esta ruta si el nombre del archivo o carpeta varía ligeramente
ruta_csv = r"C:\Users\Usuario\Gravity-data-\VOLCANES\Canarias\La_Gomera\Datos_La_Gomera_Finales.csv"
df = pd.read_csv(ruta_csv)

# ⚠️ ATENCIÓN AQUÍ: Nombres de las columnas
columna_lon = 'X'      # (Formato decimal)
columna_lat = 'Y'      # (Formato decimal)
columna_anomalia = 'Bouguer_mG'

# Limpiamos filas vacías
df = df.dropna(subset=[columna_lon, columna_lat, columna_anomalia])

# Arrays base
lon = df[columna_lon].values
lat = df[columna_lat].values
a_bouguer_digi = df[columna_anomalia].values

# Ajuste de la región a LA GOMERA
# Longitud Min, Longitud Max, Latitud Min, Latitud Max
region = [-17.40, -17.00, 27.95, 28.25]

# =============================================================================
# BLOQUE 2: REPRESENTACIÓN DEL MAPA DIGITALIZADO CON PYGMT
# =============================================================================
print("2. Generando mapa comparativo...")

fig = pygmt.Figure()

# Configuramos el marco del mapa con el título de La Gomera
fig.basemap(region=region, projection="M15c", frame=["af", 'WSen+t"Mapa de Bouguer Digitalizado - La Gomera"'])

# Dibujamos costa y fondo
fig.coast(shorelines="1/0.8p,black", land="lightgray", water="lightblue", resolution="f")

# Creamos la escala de color ajustada a los datos específicos de La Gomera
vmin = float(np.nanmin(a_bouguer_digi))
vmax = float(np.nanmax(a_bouguer_digi))
pygmt.makecpt(cmap="turbo", series=[vmin, vmax], continuous=True)

# Pintamos los puntos extraídos del mapa
fig.plot(x=lon, y=lat, style="c0.35c", fill=a_bouguer_digi, cmap=True, pen="0.1p,black")

# Barra de color inferior
fig.colorbar(frame='af+l"Anomalia de Bouguer (mGal)"', position="JBC+w10c+h+o0/1c")

# Mostramos el resultado
fig.show()

print("¡Mapa renderizado con éxito!")

# =============================================================================
# BLOQUE 3: EXPORTAR DATOS A CSV
# =============================================================================
print("3. Exportando datos procesados a un nuevo CSV...")

# Definimos la ruta de salida para La Gomera en la carpeta de Tablas generadas
ruta_salida = r"C:\Users\Usuario\Gravity-data-\Volcanes\Canarias\Tablas generadas\datos_la_gomera_procesados.csv"

# Guardamos el DataFrame en el nuevo CSV
df.to_csv(ruta_salida, index=False)

print(f"¡Archivo guardado con éxito en: {ruta_salida}!")
