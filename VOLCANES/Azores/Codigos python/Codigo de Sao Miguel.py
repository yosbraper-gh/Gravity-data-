# -*- coding: utf-8 -*-
"""
Created on Tue Apr 28 11:45:55 2026

@author: Usuario
"""

import pandas as pd
import numpy as np
import pygmt

# =============================================================================
# BLOQUE 1: CARGA Y LIMPIEZA DE COORDENADAS
# =============================================================================
print("1. Cargando datos de São Miguel...")

# Cambia la ruta a tu archivo de São Miguel
ruta_csv = r"C:\Users\Usuario\Gravity-data-\VOLCANES\Azores\Sao Miguel\datos_sao_miguel_completos.csv"
df = pd.read_csv(ruta_csv)

# Nombres de columnas (ajústalos si en tu CSV se llaman distinto, ej: 'BO (mGal)')
col_lon = 'Longitud'
col_lat = 'Latitud'
col_bouguer = 'AB' 

df = df.dropna(subset=[col_lon, col_lat, col_bouguer])

# --- LÓGICA INTELIGENTE DE COORDENADAS ---
lon_raw = df[col_lon].values
lat_raw = df[col_lat].values

if np.abs(np.nanmean(lon_raw)) > 1000:
    print(" -> Detectadas coordenadas enteras. Arreglando...")
    lon = lon_raw / 1000.0
    lat = lat_raw / 1000.0
else:
    print(" -> Coordenadas correctas detectadas.")
    lon = lon_raw
    lat = lat_raw

# Actualizamos el DataFrame con las coordenadas buenas
df['lon_fix'] = lon
df['lat_fix'] = lat

print(f" -> [DIAGNÓSTICO] Rango Longitud: {lon.min():.3f} a {lon.max():.3f}")
print(f" -> [DIAGNÓSTICO] Rango Latitud: {lat.min():.3f} a {lat.max():.3f}")

# =============================================================================
# BLOQUE 2: FILTRO DE OUTLIERS
# =============================================================================
# Aplicamos un filtro para que la escala de colores no se rompa
# (Ajusta los límites si ves que el mapa sale vacío)
df_limpio = df[(df[col_bouguer] < 500) & (df[col_bouguer] > 0)].copy()

print(f" -> Puntos a representar tras filtrar: {len(df_limpio)}")

# =============================================================================
# BLOQUE 3: MAPA CON PYGMT
# =============================================================================
region = [-25.95, -25.10, 37.65, 37.95]

fig = pygmt.Figure()

# Configuración del mapa
fig.basemap(region=region, projection="M15c", frame=["af", 'WSen+t"São Miguel: Anomalía de Bouguer Completa"'])

# Costa y mar
fig.coast(shorelines="0.5p,black", water="lightblue", land="lightgray", resolution="f")

# Escala de color automática basada en tus datos filtrados
pygmt.makecpt(cmap="turbo", series=[df_limpio[col_bouguer].min(), df_limpio[col_bouguer].max()])

# Dibujar los puntos
fig.plot(
    x=df_limpio['lon_fix'], 
    y=df_limpio['lat_fix'], 
    style="c0.3c", 
    fill=df_limpio[col_bouguer], 
    cmap=True, 
    pen="0.1p,black"
)

# Barra de color
fig.colorbar(frame='af+l"mGal"', position="JBC+w10c+h")

fig.show()

print("¡Mapa de São Miguel generado!")