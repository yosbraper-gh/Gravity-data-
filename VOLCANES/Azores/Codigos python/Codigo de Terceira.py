# -*- coding: utf-8 -*-
"""
Created on Tue Apr 28 12:46:10 2026

@author: Usuario
"""

import pandas as pd
import numpy as np
import pygmt

# =============================================================================
# BLOQUE 1: CARGA DE DATOS (TERCEIRA) Y REPARACIÓN DE COMAS
# =============================================================================
print("1. Cargando datos de Terceira...")

# ¡Cambia esto por tu ruta real!
ruta_csv = r"C:\Users\Usuario\Gravity-data-\VOLCANES\Azores\Terceira\Datos_Terceira_completos_2.0.csv"

# Leemos el archivo como texto puro para evitar que Pandas se líe con las comas
df = pd.read_csv(ruta_csv, dtype=str)

# Limpiamos espacios en blanco invisibles en los títulos de las columnas por si acaso
df.columns = df.columns.str.strip()

# Nombres exactos de las columnas según tu imagen
col_lon = 'LONGITUD'
col_lat = 'LATITUD'
col_bouguer = 'AB' 

# --- EL TRUCO PARA LAS COMAS ESPAÑOLAS ---
# Buscamos la coma, la cambiamos por un punto y convertimos a número.
for col in [col_lon, col_lat, col_bouguer]:
    df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')

# Borramos filas que hayan podido quedar vacías tras la limpieza
df = df.dropna(subset=[col_lon, col_lat, col_bouguer])

# Extraemos los datos limpios (¡Sin dividir por 1000, como bien dedujiste!)
lon = df[col_lon].values
lat = df[col_lat].values
a_bouguer_completa = df[col_bouguer].values

print(f" -> [DIAGNÓSTICO] Rango Longitud: {lon.min():.3f} a {lon.max():.3f}")
print(f" -> [DIAGNÓSTICO] Rango Latitud: {lat.min():.3f} a {lat.max():.3f}")
print(f" -> [DIAGNÓSTICO] Rango Anomalía: {a_bouguer_completa.min():.2f} a {a_bouguer_completa.max():.2f} mGal")

# =============================================================================
# BLOQUE 2: FILTRO DE OUTLIERS
# =============================================================================
# Metemos los datos limpios en un nuevo DataFrame para filtrar y pintar
df_limpio = pd.DataFrame({
    'lon': lon,
    'lat': lat,
    'bouguer': a_bouguer_completa
})

# Filtro geofísico de seguridad
df_limpio = df_limpio[(df_limpio['bouguer'] < 500) & (df_limpio['bouguer'] > 0)]

print(f" -> Puntos a representar tras filtrar: {len(df_limpio)}")

# =============================================================================
# BLOQUE 3: MAPA CON PYGMT
# =============================================================================
print("3. Generando mapa de Terceira...")

# Región exacta para enmarcar Terceira
region = [-27.15, -27.05, 38.63, 38.70]

fig = pygmt.Figure()

# Configuración del mapa base
fig.basemap(region=region, projection="M15c", frame=["af", 'WSen+t"Terceira: Anomalía de Bouguer Completa"'])

# Dibujar la costa y el mar
fig.coast(shorelines="0.5p,black", water="lightblue", land="lightgray", resolution="f")

# Crear la escala de color ajustada exactamente a los valores de Terceira
pygmt.makecpt(cmap="turbo", series=[df_limpio['bouguer'].min(), df_limpio['bouguer'].max()])

# Dibujar los puntos del gravímetro
fig.plot(
    x=df_limpio['lon'], 
    y=df_limpio['lat'], 
    style="c0.3c", 
    fill=df_limpio['bouguer'], 
    cmap=True, 
    pen="0.1p,black"
)

# Añadir la barra de color
fig.colorbar(frame='af+l"mGal"', position="JBC+w10c+h")

fig.show()

print("¡Proceso completado con éxito!")