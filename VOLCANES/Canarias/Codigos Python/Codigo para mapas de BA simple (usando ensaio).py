# -*- coding: utf-8 -*-
"""
Created on Mon Apr 27 11:52:04 2026

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
# BLOQUE 1: CARGA DE DATOS DIGITALIZADOS (OAHU)
# =============================================================================
print("1. Cargando datos digitalizados...")

ruta_csv = r"C:\Users\Usuario\Gravity-data-\VOLCANES\Hawaii\Datos_Oahu_Finales.csv"

# Cargamos el CSV (ajusta el separador si es necesario)
df = pd.read_csv(ruta_csv, dtype=str)

# Limpieza de comas y conversión a números
for col in df.columns:
    df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')

df = df.dropna()

# Extraemos las columnas (asegúrate de que los nombres coincidan con tu CSV)
lon = df['X'].values
lat = df['Y'].values
a_bouguer_simple = df['Bouguer_mG'].values

# Definimos la región de Oahu y la proyección UTM 4N
region = [-158.35, -157.60, 21.20, 21.75]
proyeccion = pyproj.Proj(proj="utm", zone=4, ellps="WGS84")

# =============================================================================
# BLOQUE 2: RECUPERACIÓN DE ALTURAS (ENSAIO)
# =============================================================================
print("2. Descargando topografía y rescatando alturas (h)...")

archivo_topo = ensaio.fetch_earth_topography(version=1)
topo_global = xr.load_dataarray(archivo_topo)

# Recorte del modelo alrededor de Oahu
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

# Configuración física
rho_roca = 2670  # Densidad estándar
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
# BLOQUE 4: TRANSFORMACIÓN Y MAPA FINAL
# =============================================================================
print("4. Transformando a Bouguer Completa y generando mapa...")

# Para pasar de Simple a Completa: 
# 1. Recuperamos la Anomalía de Aire Libre teórica (Aire Libre = Simple + Slab)
a_aire_libre_teorica = a_bouguer_simple + (0.04193 * (rho_roca/1000) * h_recuperada)

# 2. Restamos el efecto de los prismas 3D reales
a_bouguer_completa = a_aire_libre_teorica - efecto_topografico

# Dibujamos el mapa con PyGMT
fig = pygmt.Figure()
fig.basemap(region=region, projection="M15c", frame=["af", 'WSen+t"Oahu: Bouguer Completa (de Digitalizado)"'])
fig.coast(shorelines="0.5p,black", water="lightblue", land="lightgray", resolution="f")

pygmt.makecpt(cmap="turbo", series=[a_bouguer_completa.min(), a_bouguer_completa.max()])
fig.plot(x=lon, y=lat, style="c0.3c", fill=a_bouguer_completa, cmap=True, pen="0.1p,black")
fig.colorbar(frame='af+l"mGal"', position="JBC+w10c+h")
fig.show()

# =============================================================================
# BLOQUE 5: EXPORTACIÓN
# =============================================================================
df_final = pd.DataFrame({
    "Lon": lon, "Lat": lat, "H_estimada": h_recuperada,
    "Bouguer_Simple": a_bouguer_simple,
    "Bouguer_Completa": a_bouguer_completa
})
df_final.to_csv("Oahu_Resultados_Completos.csv", index=False)
print("¡Proceso finalizado!")