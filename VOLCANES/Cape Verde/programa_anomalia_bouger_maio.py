# -*- coding: utf-8 -*-
"""
Created on Tue Apr 28 13:29:24 2026

@author: Usuario
"""

import pandas as pd
import numpy as np
import pygmt

# =============================================================================
# BLOQUE 1: CARGAR DATOS DIGITALIZADOS
# =============================================================================
print("1. Cargando datos del mapa digitalizado...")

# Cambia esto por la ruta de tu nuevo archivo CSV
ruta_csv = r"C:\Users\Usuario\Gravity-data-\VOLCANES\Cape Verde\datos_maio_competos_bouguer.csv"
df = pd.read_csv(ruta_csv)

# ⚠️ ATENCIÓN AQUÍ: Cambia estos nombres por los nombres EXACTOS
# de las columnas que tengas en tu archivo Excel/CSV
columna_lon = 'Longitud'     # (Asegúrate de que están en formato decimal, ej: -16.5)
columna_lat = 'Latitud'      # (Formato decimal, ej: 28.2)
columna_anomalia = 'AB (mGal)'

# Limpiamos filas vacías por si acaso el Excel tiene errores
df = df.dropna(subset=[columna_lon, columna_lat, columna_anomalia])

# Arrays base
lon = df[columna_lon].values
lat = df[columna_lat].values
a_bouguer_digi = df[columna_anomalia].values

# Ajusta la región según la isla del mapa que hayas digitalizado
region = [-23.25, -22.95, 15.10, 15.35] # Ejemplo: Maio

# =============================================================================
# BLOQUE 2: REPRESENTACIÓN DEL MAPA DIGITALIZADO CON PYGMT
# =============================================================================
print("2. Generando mapa comparativo...")

fig = pygmt.Figure()

# Configuramos el marco del mapa
fig.basemap(region=region, projection="M15c", frame=["af", 'WSen+t"Isla  Maio: Anomalía de Bouguer Completa Digitalizado"'])

# Dibujamos costa y fondo
fig.coast(shorelines="1/0.8p,black", land="lightgray", water="lightblue", resolution="f")

# Creamos la escala de color ajustada a TUS DATOS digitalizados
vmin = float(np.nanmin(a_bouguer_digi))
vmax = float(np.nanmax(a_bouguer_digi))
pygmt.makecpt(cmap="turbo", series=[vmin, vmax], continuous=True)

# Pintamos los puntos que has extraído del mapa
fig.plot(x=(lon-0.007), y=lat, style="c0.35c", fill=a_bouguer_digi, cmap=True, pen="0.1p,black")

# Barra de color inferior
fig.colorbar(frame='af+l"Anomalia de Bouguer Completa (mGal)"', position="JBC+w10c+h+o0/1c")

# Mostramos el resultado
fig.show()

print("¡Mapa renderizado con éxito!")