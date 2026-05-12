# -*- coding: utf-8 -*-
"""
Created on Mon Apr 27 13:44:59 2026

@author: Usuario
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import boule as bl
import harmonica as hm
import pygmt
import pyproj
from scipy.interpolate import RegularGridInterpolator
import xarray as xr

# =============================================================================
# BLOQUE 1: CARGA Y LIMPIEZA DE DATOS (HAWÁI)
# =============================================================================
print("1. Cargando y limpiando datos de Hawái...")
ruta_csv = r"C:\Users\Usuario\Gravity-data-\VOLCANES\Hawaii\Gravity Data for Island of Big Island Hawai`i.csv"

df = pd.read_csv(ruta_csv)

df['ObsGravity'] = pd.to_numeric(df['ObsGravity'], errors='coerce')
df['elevation'] = pd.to_numeric(df['elevation'], errors='coerce')
df['LatitudeWGS84'] = pd.to_numeric(df['LatitudeWGS84'], errors='coerce')
df['LongitudeWGS84'] = pd.to_numeric(df['LongitudeWGS84'], errors='coerce')

df = df.dropna(subset=['ObsGravity', 'LatitudeWGS84', 'elevation'])

df = df[(df['ObsGravity'] > 970000) & (df['ObsGravity'] < 990000)]
df = df[(df['elevation'] > -50) & (df['elevation'] < 4500)]

lat   = df['LatitudeWGS84'].values
lon   = df['LongitudeWGS84'].values
h     = df['elevation'].values
g_obs = df['ObsGravity'].values

region = [-156.3, -154.7, 18.8, 20.4]

# =============================================================================
# BLOQUE 2: GRAVEDAD NORMAL Y AIRE LIBRE
# =============================================================================
print("2. Calculando Gravedad Normal y Aire Libre...")
g_n = bl.WGS84.normal_gravity(coordinates=(lon, lat, h))
a_g_l = g_obs - g_n

# =============================================================================
# BLOQUE 3: ANOMALÍA DE BOUGUER SIMPLE Y FILTRO 
# =============================================================================
print("3. Calculando Bouguer Simple y filtrando errores locales...")
densidad_g_cm3 = 2.60
c_bouguer = 0.04193 * densidad_g_cm3 * h
a_bouguer = a_g_l - c_bouguer

mascara_buenos = a_bouguer > 50
lon = lon[mascara_buenos]
lat = lat[mascara_buenos]
h = h[mascara_buenos]
g_obs = g_obs[mascara_buenos]
g_n = g_n[mascara_buenos]
a_g_l = a_g_l[mascara_buenos]
a_bouguer = a_bouguer[mascara_buenos]
print(f"   -> Se eliminaron {np.sum(~mascara_buenos)} puntos atípicos locales.")

# =============================================================================
# BLOQUE 4: ANOMALÍA DE BOUGUER COMPLETA (SRTM HD PyGMT)
# =============================================================================
print("4. Descargando topografía y batimetría HD (SRTM 15s)...")
# Ampliamos la región para efectos de borde
region_extendida = [region[0] - 0.5, region[1] + 0.5, region[2] - 0.5, region[3] + 0.5]

topo = pygmt.datasets.load_earth_relief(
    resolution="15s", 
    region=region_extendida,
    registration="pixel"
)

topo_lon = topo['lon'].values
topo_lat = topo['lat'].values
topo_z = topo.values  

proyeccion = pyproj.Proj(proj="utm", zone=5, ellps="WGS84")
easting_obs, northing_obs = proyeccion(lon, lat)

lon_corners = np.array([topo_lon.min(), topo_lon.max()])
lat_corners = np.array([topo_lat.min(), topo_lat.max()])
e_corners, n_corners = proyeccion(lon_corners, lat_corners)

n_lon = len(topo_lon)
n_lat = len(topo_lat)
easting_1d  = np.linspace(e_corners[0], e_corners[1], n_lon)
northing_1d = np.linspace(n_corners[0], n_corners[1], n_lat)

# Blindamos el interpolador con fill_value=0
interpolador = RegularGridInterpolator(
    (topo_lat, topo_lon), topo_z, method="linear", bounds_error=False, fill_value=0
)

easting_2d, northing_2d = np.meshgrid(easting_1d, northing_1d)
lon_utm, lat_utm = proyeccion(easting_2d, northing_2d, inverse=True)
elevacion_utm = interpolador((lat_utm, lon_utm))

rho_roca = 2600
rho_agua = 1030  
densidad = np.where(elevacion_utm >= 0, rho_roca, rho_agua - rho_roca)

print("   -> Calculando atracción de los prismas 3D (Esto tardará unos minutos)...")
capa_prismas = hm.prism_layer(
    coordinates=(easting_1d, northing_1d),
    surface=elevacion_utm,
    reference=0,
    properties={"density": densidad}
)

efecto_topografico = capa_prismas.prism_layer.gravity(
    coordinates=(easting_obs, northing_obs, h),
    field="g_z"
)

a_bouguer_completa = a_g_l - efecto_topografico

# =============================================================================
# BLOQUE 5: MAPAS FINALES CON PYGMT (ESCALAS UNIFICADAS)
# =============================================================================
print("5. Generando visualizaciones...")

data = pd.DataFrame({
    "lon": lon, "lat": lat, 
    "g_obs": g_obs, 
    "aire_libre": a_g_l, "bouguer": a_bouguer, "bouguer_completa": a_bouguer_completa
})

# --- MAPA 0: Gravedad Observada ---
fig0 = pygmt.Figure()
fig0.basemap(region=region, projection="M15c", frame=["af", 'WSen+t"Hawai: Gravedad Observada"'])
fig0.coast(shorelines="0.5p,black", land="lightgray", water="lightblue", resolution="f")
pygmt.makecpt(cmap="turbo", series=[data.g_obs.min(), data.g_obs.max()])
fig0.plot(x=data.lon, y=data.lat, style="c0.25c", fill=data.g_obs, cmap=True, pen="0.1p,black")
fig0.colorbar(frame='af+l"mGal"', position="JBC+w10c+h+o0/1c")
fig0.show()

# --- MAPA 1: Anomalía de aire libre ---
fig = pygmt.Figure()
fig.basemap(region=region, projection="M15c", frame=["af", 'WSen+t"Hawai: Anomalia de Aire Libre"'])
fig.coast(shorelines="1/0.8p,black", land="lightgray", water="lightblue", resolution="f")
pygmt.makecpt(cmap="turbo", series=[data.aire_libre.min(), data.aire_libre.max()])
fig.plot(x=data.lon, y=data.lat, style="c0.25c", fill=data.aire_libre, cmap=True, pen="0.1p,black")
fig.colorbar(frame='af+l"mGal"', position="JBC+w10c+h+o0/1c")
fig.show()

# --- EL TRUCO: ESCALA UNIFICADA PARA LAS DOS BOUGUER ---
# Buscamos el mínimo y máximo global entre las dos columnas
min_bouguer_global = min(data.bouguer.min(), data.bouguer_completa.min())
max_bouguer_global = max(data.bouguer.max(), data.bouguer_completa.max())

# --- MAPA 2: Anomalía de Bouguer Simple ---
fig2 = pygmt.Figure()
fig2.basemap(region=region, projection="M15c", frame=["af", 'WSen+t"Hawai: Anomalia de Bouguer Simple"'])
fig2.coast(shorelines="1/0.8p,black", land="lightgray", water="lightblue", resolution="f")
# Usamos la escala global
pygmt.makecpt(cmap="turbo", series=[min_bouguer_global, max_bouguer_global])
fig2.plot(x=data.lon, y=data.lat, style="c0.25c", fill=data.bouguer, cmap=True, pen="0.1p,black")
fig2.colorbar(frame='af+l"mGal"', position="JBC+w10c+h+o0/1c")
fig2.show()

# --- MAPA 3: Anomalía de Bouguer completa ---
fig3 = pygmt.Figure()
fig3.basemap(region=region, projection="M15c", frame=["af", 'WSen+t"Hawai: Anomalia Bouguer Completa"'])
fig3.coast(shorelines="1/0.8p,black", land="lightgray", water="lightblue", resolution="f")
# Usamos la misma escala global
pygmt.makecpt(cmap="turbo", series=[min_bouguer_global, max_bouguer_global])
fig3.plot(x=data.lon, y=data.lat, style="c0.25c", fill=data.bouguer_completa, cmap=True, pen="0.1p,black")
fig3.colorbar(frame='af+l"mGal"', position="JBC+w10c+h+o0/1c")
fig3.show()

# =============================================================================
# BLOQUE 6: EXPORTACIÓN DE RESULTADOS A CSV (Omitimos subplots por rapidez)
# =============================================================================
print("6. Exportando resultados finales a CSV...")
resultados = {
    "Longitude": lon, "Latitude": lat, "Elevation_m": h,
    "ObsGravity_mGal": g_obs, "NormalGravity_mGal": g_n,
    "FreeAir_mGal": a_g_l, "Bouguer_Simple_2.6_mGal": a_bouguer,
    "Bouguer_Completa_2.6_mGal": a_bouguer_completa
}

df_final = pd.DataFrame(resultados)
nombre_archivo = r"C:\Users\Usuario\Gravity-data-\VOLCANES\Hawaii\Tablas obtenidas\Tabla_Hawaii_HD.csv"
df_final.to_csv(nombre_archivo, index=False, sep=',', encoding='utf-8')

print(f"--- ¡Éxito! Se guardaron {len(df_final)} estaciones en: {nombre_archivo} ---")