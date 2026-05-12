# -*- coding: utf-8 -*-
"""
Created on Tue Apr 28 11:15:13 2026

@author: Usuario
"""

import pandas as pd
import numpy as np
import pyproj
import xarray as xr
import harmonica as hm
import pygmt
from scipy.interpolate import RegularGridInterpolator

# =============================================================================
# BLOQUE 1: CARGA DE DATOS (PICO) Y CORRECCIÓN AUTOMÁTICA
# =============================================================================
print("1. Cargando datos digitalizados de Pico...")

ruta_csv = r"C:\Users\Usuario\Gravity-data-\VOLCANES\Azores\Pico\Datos_completos_Pico.csv"

# Cargamos el CSV y limpiamos filas vacías
df = pd.read_csv(ruta_csv)
df = df.dropna(subset=['Longitud', 'Latitud', 'AB (mGal)'])

# --- LÓGICA INTELIGENTE DE COORDENADAS ---
lon_raw = df['Longitud'].values
lat_raw = df['Latitud'].values

if np.abs(np.nanmean(lon_raw)) > 1000:
    print(" -> Detectadas coordenadas sin decimales. Dividiendo por 1000...")
    lon = lon_raw / 1000.0
    lat = lat_raw / 1000.0
else:
    print(" -> Detectadas coordenadas correctas. Usando valores directos...")
    lon = lon_raw
    lat = lat_raw

a_bouguer_simple = df['AB (mGal)'].values

# Definimos la región de Pico y la proyección UTM ZONA 26N (Azores)
region = [-28.65, -28.05, 38.35, 38.65]
proyeccion = pyproj.Proj(proj="utm", zone=26, ellps="WGS84")

print(f" -> [DIAGNÓSTICO] Rango Longitud REAL: {lon.min():.3f} a {lon.max():.3f}")
print(f" -> [DIAGNÓSTICO] Rango Latitud REAL: {lat.min():.3f} a {lat.max():.3f}")

# =============================================================================
# BLOQUE 2: RECUPERACIÓN DE ALTURAS (PyGMT Alta Resolución SRTM15+ / GEBCO)
# =============================================================================
print("2. Descargando topografía/batimetría de alta resolución (15s)...")

# Ampliamos la región 0.5 grados para los efectos de borde
region_extendida = [region[0] - 0.5, region[1] + 0.5, region[2] - 0.5, region[3] + 0.5]

# Descargamos la topografía+batimetría integrada (usamos pixel para evitar el error IGPP)
topo = pygmt.datasets.load_earth_relief(
    resolution="15s", 
    region=region_extendida,
    registration="pixel"
)

topo_lon = topo['lon'].values
topo_lat = topo['lat'].values
topo_z = topo.values

# BLINDAJE: fill_value=0 asume que si algo cae fuera del mapa, está a nivel del mar.
interpolador_h = RegularGridInterpolator(
    (topo_lat, topo_lon), topo_z, method="linear", bounds_error=False, fill_value=0
)
h_recuperada = interpolador_h((lat, lon))

print(f" -> [DIAGNÓSTICO] Altura (h) recuperada: {h_recuperada.min():.1f}m a {h_recuperada.max():.1f}m")

# =============================================================================
# BLOQUE 3: CÁLCULO DE LA CORRECCIÓN TOPOGRÁFICA 3D
# =============================================================================
print("3. Calculando prismas 3D (Topografía + Batimetría HD)...")
print("   -> (Esto tardará un poco más al usar alta resolución. Paciencia...)")

# Proyecciones a metros
easting_obs, northing_obs = proyeccion(lon, lat)
e_corners, n_corners = proyeccion(np.array([topo_lon.min(), topo_lon.max()]), 
                                  np.array([topo_lat.min(), topo_lat.max()]))

easting_1d = np.linspace(e_corners[0], e_corners[1], len(topo_lon))
northing_1d = np.linspace(n_corners[0], n_corners[1], len(topo_lat))
easting_2d, northing_2d = np.meshgrid(easting_1d, northing_1d)
lon_utm, lat_utm = proyeccion(easting_2d, northing_2d, inverse=True)
elevacion_utm = interpolador_h((lat_utm, lon_utm))

# Configuración física (2520 kg/m3 para Pico)
rho_roca = 2520  
rho_agua = 1030
densidad_prismas = np.where(elevacion_utm >= 0, rho_roca, rho_agua - rho_roca)

# Creación de la capa de prismas
capa_prismas = hm.prism_layer(
    coordinates=(easting_1d, northing_1d),
    surface=elevacion_utm, reference=0,
    properties={"density": densidad_prismas}
)

# Calculamos la atracción gravitatoria 3D
efecto_topografico = capa_prismas.prism_layer.gravity(
    coordinates=(easting_obs, northing_obs, h_recuperada), field="g_z"
)

# =============================================================================
# BLOQUE 4: TRANSFORMACIÓN A BOUGUER COMPLETA
# =============================================================================
print("4. Transformando a Bouguer Completa...")

a_aire_libre_teorica = a_bouguer_simple + (0.04193 * (rho_roca/1000) * h_recuperada)
a_bouguer_completa = a_aire_libre_teorica - efecto_topografico

# =============================================================================
# BLOQUE 5: FILTRO, ESTADÍSTICAS Y MAPAS UNIFICADOS
# =============================================================================
print("5. Analizando datos y generando mapas con escalas unificadas...")

df_final = pd.DataFrame({
    "Lon_DD": lon, 
    "Lat_DD": lat, 
    "H_estimada_m": h_recuperada,
    "Bouguer_Simple": a_bouguer_simple,
    "Bouguer_Completa": a_bouguer_completa
})

# Filtro abierto de seguridad
df_final = df_final[(df_final['Bouguer_Completa'] < 800) & (df_final['Bouguer_Completa'] > 0)]

print(f" -> Puntos válidos listos para dibujar tras filtro: {len(df_final)}")

if len(df_final) == 0:
    raise ValueError("¡Fallo crítico! El filtro ha borrado todo. Revisa los valores en consola.")

# --- EL TRUCO: ESCALA UNIFICADA ---
min_bouguer_global = min(df_final['Bouguer_Simple'].min(), df_final['Bouguer_Completa'].min())
max_bouguer_global = max(df_final['Bouguer_Simple'].max(), df_final['Bouguer_Completa'].max())

print(f" -> Escala de color fijada entre {min_bouguer_global:.1f} y {max_bouguer_global:.1f} mGal")

# --- MAPA 1: BOUGUER SIMPLE ---
fig1 = pygmt.Figure()
fig1.basemap(region=region, projection="M15c", frame=["af", 'WSen+t"Pico: Bouguer Simple"'])
fig1.coast(shorelines="0.5p,black", water="lightblue", land="lightgray", resolution="f")
pygmt.makecpt(cmap="turbo", series=[min_bouguer_global, max_bouguer_global])
fig1.plot(x=df_final['Lon_DD'], y=df_final['Lat_DD'], style="c0.3c", fill=df_final['Bouguer_Simple'], cmap=True, pen="0.1p,black")
fig1.colorbar(frame='af+l"mGal"', position="JBC+w10c+h")
fig1.show()

# --- MAPA 2: BOUGUER COMPLETA ---
fig2 = pygmt.Figure()
fig2.basemap(region=region, projection="M15c", frame=["af", 'WSen+t"Pico: Bouguer Completa (HD 3D)"'])
fig2.coast(shorelines="0.5p,black", water="lightblue", land="lightgray", resolution="f")
pygmt.makecpt(cmap="turbo", series=[min_bouguer_global, max_bouguer_global])
fig2.plot(x=df_final['Lon_DD'], y=df_final['Lat_DD'], style="c0.3c", fill=df_final['Bouguer_Completa'], cmap=True, pen="0.1p,black")
fig2.colorbar(frame='af+l"mGal"', position="JBC+w10c+h")
fig2.show()

# =============================================================================
# BLOQUE 6: EXPORTACIÓN
# =============================================================================
nombre_archivo = r"C:\Users\Usuario\Gravity-data-\VOLCANES\Azores\Tablas generadas\Tabla_Pico_HD.csv"
df_final.to_csv(nombre_archivo, index=False)
print(f"¡Exportación finalizada en: {nombre_archivo}")