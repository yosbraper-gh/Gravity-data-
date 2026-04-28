# -*- coding: utf-8 -*-
"""
Created on Tue Apr 28 10:18:27 2026

@author: Usuario
"""

import pandas as pd
import numpy as np
import pyproj
import ensaio
import xarray as xr
import harmonica as hm
import pygmt
from scipy.interpolate import RegularGridInterpolator

# =============================================================================
# BLOQUE 1: CARGA DE DATOS DIGITALIZADOS (FAIAL) Y CORRECCIÓN
# =============================================================================
print("1. Cargando datos digitalizados de Faial...")

ruta_csv = r"C:\Users\Usuario\Gravity-data-\VOLCANES\Azores\Faial\datos_completos_faial.csv"

# Cargamos el CSV
df = pd.read_csv(ruta_csv)

# Limpiamos posibles filas vacías basándonos en las columnas reales de Faial
df = df.dropna(subset=['Longitud(º)', 'Latitud(º)', 'AB (mGal)'])

# Extraemos las columnas y APLICAMOS LA DIVISIÓN ENTRE 1000
lon = df['Longitud(º)'].values / 1000.0
lat = df['Latitud(º)'].values / 1000.0
a_bouguer_simple = df['AB (mGal)'].values

# Definimos la región de Faial y la proyección UTM ZONA 26N (Azores)
region = [-28.90, -28.50, 38.50, 38.70]
proyeccion = pyproj.Proj(proj="utm", zone=26, ellps="WGS84")

print(f" -> Se cargaron {len(lon)} puntos con coordenadas corregidas.")

# =============================================================================
# BLOQUE 2: RECUPERACIÓN DE ALTURAS (ENSAIO)
# =============================================================================
print("2. Descargando topografía y rescatando alturas (h)...")

archivo_topo = ensaio.fetch_earth_topography(version=1)
topo_global = xr.load_dataarray(archivo_topo)

# Recorte del modelo alrededor de Faial
topo = topo_global.sel(
    longitude=slice(region[0] - 0.5, region[1] + 0.5),
    latitude=slice(region[2] - 0.5, region[3] + 0.5)
)

topo_lon, topo_lat, topo_z = topo.longitude.values, topo.latitude.values, topo.values

# Interpolador para "adivinar" la altura h de tus puntos digitalizados
interpolador_h = RegularGridInterpolator(
    (topo_lat, topo_lon), topo_z, method="linear", bounds_error=False, fill_value=None
)
h_recuperada = interpolador_h((lat, lon))

# =============================================================================
# BLOQUE 3: CÁLCULO DE LA CORRECCIÓN TOPOGRÁFICA 3D
# =============================================================================
print("3. Calculando prismas 3D (Topografía + Batimetría)...")

# Proyecciones a metros
easting_obs, northing_obs = proyeccion(lon, lat)
e_corners, n_corners = proyeccion(np.array([topo_lon.min(), topo_lon.max()]), 
                                  np.array([topo_lat.min(), topo_lat.max()]))

easting_1d = np.linspace(e_corners[0], e_corners[1], len(topo_lon))
northing_1d = np.linspace(n_corners[0], n_corners[1], len(topo_lat))
easting_2d, northing_2d = np.meshgrid(easting_1d, northing_1d)
lon_utm, lat_utm = proyeccion(easting_2d, northing_2d, inverse=True)
elevacion_utm = interpolador_h((lat_utm, lon_utm))

# Configuración física (Azores suele usar 2600 kg/m3)
rho_roca = 2600  
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

# 1. Recuperamos la Anomalía de Aire Libre teórica (Aire Libre = Simple + Slab)
a_aire_libre_teorica = a_bouguer_simple + (0.04193 * (rho_roca/1000) * h_recuperada)

# 2. Restamos el efecto de los prismas 3D reales
a_bouguer_completa = a_aire_libre_teorica - efecto_topografico


# =============================================================================
# BLOQUE 5: FILTRO PANDAS, MAPAS Y EXPORTACIÓN
# =============================================================================
print("5. Filtrando datos atípicos y generando mapas...")

# Metemos todos los resultados en un DataFrame ANTES de dibujar
df_final = pd.DataFrame({
    "Lon_DD": lon, 
    "Lat_DD": lat, 
    "H_estimada_m": h_recuperada,
    "Bouguer_Simple": a_bouguer_simple,
    "Bouguer_Completa": a_bouguer_completa
})

# --- ¡AQUÍ ESTÁ TU FILTRO ESTILO PANDAS! ---
# Borramos cualquier fila donde la Bouguer Completa sea una locura (>400 o <0)
df_final = df_final[(df_final['Bouguer_Completa'] < 400) & (df_final['Bouguer_Completa'] > 0)]

print(f" -> Puntos válidos listos para dibujar: {len(df_final)}")

# --- MAPA 1: BOUGUER SIMPLE ---
fig1 = pygmt.Figure()
fig1.basemap(region=region, projection="M15c", frame=["af", 'WSen+t"Faial: Bouguer Simple"'])
fig1.coast(shorelines="0.5p,black", water="lightblue", land="lightgray", resolution="f")
pygmt.makecpt(cmap="turbo", series=[df_final['Bouguer_Simple'].min(), df_final['Bouguer_Simple'].max()])
fig1.plot(x=df_final['Lon_DD'], y=df_final['Lat_DD'], style="c0.3c", fill=df_final['Bouguer_Simple'], cmap=True, pen="0.1p,black")
fig1.colorbar(frame='af+l"mGal"', position="JBC+w10c+h")
fig1.show()

# --- MAPA 2: BOUGUER COMPLETA ---
fig2 = pygmt.Figure()
fig2.basemap(region=region, projection="M15c", frame=["af", 'WSen+t"Faial: Bouguer Completa (Calculada 3D)"'])
fig2.coast(shorelines="0.5p,black", water="lightblue", land="lightgray", resolution="f")
pygmt.makecpt(cmap="turbo", series=[df_final['Bouguer_Completa'].min(), df_final['Bouguer_Completa'].max()])
fig2.plot(x=df_final['Lon_DD'], y=df_final['Lat_DD'], style="c0.3c", fill=df_final['Bouguer_Completa'], cmap=True, pen="0.1p,black")
fig2.colorbar(frame='af+l"mGal"', position="JBC+w10c+h")
fig2.show()

# =============================================================================
# BLOQUE 6: EXPORTACIÓN
# =============================================================================
nombre_archivo = r"C:\Users\Usuario\Gravity-data-\VOLCANES\Azores\Tablas generadas\Tabla_Faial_ensaio.csv"
# Guardamos el DataFrame que YA está filtrado y limpio
df_final.to_csv(nombre_archivo, index=False)
print(f"¡Proceso finalizado! Archivo limpio guardado en: {nombre_archivo}")