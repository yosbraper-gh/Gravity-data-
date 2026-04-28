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
import ensaio
import xarray as xr

# =============================================================================
# BLOQUE 1: CARGA Y LIMPIEZA DE DATOS (HAWÁI)
# =============================================================================
print("1. Cargando y limpiando datos de Hawái...")
# Pon la ruta exacta de tu archivo
ruta_csv = r"C:\Users\Usuario\Gravity-data-\VOLCANES\Hawaii\Gravity Data for Island of Big Island Hawai`i.csv"

# Leemos el archivo. (Asegúrate de que es un CSV separado por comas)
df = pd.read_csv(ruta_csv)

# Convertimos a números las columnas exactas de tu imagen
df['ObsGravity'] = pd.to_numeric(df['ObsGravity'], errors='coerce')
df['elevation'] = pd.to_numeric(df['elevation'], errors='coerce')
df['LatitudeWGS84'] = pd.to_numeric(df['LatitudeWGS84'], errors='coerce')
df['LongitudeWGS84'] = pd.to_numeric(df['LongitudeWGS84'], errors='coerce')

# Borramos filas que tengan datos en blanco
df = df.dropna(subset=['ObsGravity', 'LatitudeWGS84', 'elevation'])

# FILTRO 1: Valores absurdos
df = df[(df['ObsGravity'] > 970000) & (df['ObsGravity'] < 990000)]
# ¡CUIDADO AQUÍ! Subimos el límite a 4500m para no borrar el Mauna Kea ni el Mauna Loa
df = df[(df['elevation'] > -50) & (df['elevation'] < 4500)]

# Arrays base
lat   = df['LatitudeWGS84'].values
lon   = df['LongitudeWGS84'].values
h     = df['elevation'].values
g_obs = df['ObsGravity'].values

# Definimos la región (Caja de coordenadas para la Isla Grande de Hawái)
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
# Las rocas basálticas de Hawái son densas, usamos 2600 kg/m3 (2.6 g/cm3)
densidad_g_cm3 = 2.60
c_bouguer = 0.04193 * densidad_g_cm3 * h
a_bouguer = a_g_l - c_bouguer

# Filtro quirúrgico adaptado a Hawái (Las anomalías allí son muy positivas)
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
# BLOQUE 4: ANOMALÍA DE BOUGUER COMPLETA (MODELO ENSAIO)
# =============================================================================
print("4. Procesando topografía y batimetría con Ensaio (10 arc-min)...")
archivo_topo = ensaio.fetch_earth_topography(version=1)
topo_global = xr.load_dataarray(archivo_topo)

topo = topo_global.sel(
    longitude=slice(region[0] - 0.5, region[1] + 0.5),
    latitude=slice(region[2] - 0.5, region[3] + 0.5)
)

topo_lon = topo.longitude.values
topo_lat = topo.latitude.values
topo_z = topo.values  

#  Proyecciones a metros en UTM Zona 5N (Hawái)
proyeccion = pyproj.Proj(proj="utm", zone=5, ellps="WGS84")
easting_obs, northing_obs = proyeccion(lon, lat)

lon_corners = np.array([topo_lon.min(), topo_lon.max()])
lat_corners = np.array([topo_lat.min(), topo_lat.max()])
e_corners, n_corners = proyeccion(lon_corners, lat_corners)

n_lon = len(topo_lon)
n_lat = len(topo_lat)
easting_1d  = np.linspace(e_corners[0], e_corners[1], n_lon)
northing_1d = np.linspace(n_corners[0], n_corners[1], n_lat)

interpolador = RegularGridInterpolator(
    (topo_lat, topo_lon), topo_z, method="linear", bounds_error=False, fill_value=None
)

easting_2d, northing_2d = np.meshgrid(easting_1d, northing_1d)
lon_utm, lat_utm = proyeccion(easting_2d, northing_2d, inverse=True)
elevacion_utm = interpolador((lat_utm, lon_utm))

rho_roca = 2600
rho_agua = 1030  
densidad = np.where(elevacion_utm >= 0, rho_roca, rho_agua - rho_roca)

print("   -> Calculando atracción de los prismas 3D...")
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
# BLOQUE 5: MAPAS FINALES CON PYGMT
# =============================================================================
print("5. Generando visualizaciones...")

# Añadimos 'g_obs' al DataFrame para que PyGMT lo pueda leer fácilmente
data = pd.DataFrame({
    "lon": lon, "lat": lat, 
    "g_obs": g_obs,  # <--- AQUÍ AÑADIMOS LA GRAVEDAD OBSERVADA
    "aire_libre": a_g_l, "bouguer": a_bouguer, "bouguer_completa": a_bouguer_completa
})

# --- 0. Gravedad Observada (Datos Crudos) ---
fig0 = pygmt.Figure()
fig0.basemap(region=region, projection="M15c", frame=["af", 'WSen+t"Lanzarote: Gravedad Observada"'])
fig0.coast(shorelines="0.5p,black", land="lightgray", water="lightblue", resolution="f")
# Escala de colores adaptada a la gravedad absoluta (que ronda los 979,000 mGal)
pygmt.makecpt(cmap="turbo", series=[data.g_obs.min(), data.g_obs.max()])
fig0.plot(x=data.lon, y=data.lat, style="c0.25c", fill=data.g_obs, cmap=True, pen="0.1p,black")
fig0.colorbar(frame='af+l"mGal"', position="JBC+w10c+h+o0/1c")
fig0.show()


# --- Mapa 1: Anomalía de aire libre ---
fig = pygmt.Figure()
fig.basemap(region=region, projection="M15c", frame=["af", 'WSen+t"Hawai: Anomalia de Aire Libre"'])
fig.coast(shorelines="1/0.8p,black", land="lightgray", water="lightblue", resolution="f")
pygmt.makecpt(cmap="turbo", series=[a_g_l.min(), a_g_l.max()])
fig.plot(x=data.lon, y=data.lat, style="c0.25c", fill=data.aire_libre, cmap=True, pen="0.1p,black")
fig.colorbar(frame='af+l"mGal"', position="JBC+w10c+h+o0/1c")
fig.show()

# --- Mapa 2: Anomalía de Bouguer Simple ---
fig2 = pygmt.Figure()
fig2.basemap(region=region, projection="M15c", frame=["af", 'WSen+t"Hawai: Anomalia de Bouguer Simple"'])
fig2.coast(shorelines="1/0.8p,black", land="lightgray", water="lightblue", resolution="f")
pygmt.makecpt(cmap="turbo", series=[a_bouguer.min(), a_bouguer.max()])
fig2.plot(x=data.lon, y=data.lat, style="c0.25c", fill=data.bouguer, cmap=True, pen="0.1p,black")
fig2.colorbar(frame='af+l"mGal"', position="JBC+w10c+h+o0/1c")
fig2.show()


# --- Mapa 3: Anomalía de Bouguer completa ---
fig3 = pygmt.Figure()
fig3.basemap(region=region, projection="M15c", frame=["af", 'WSen+t"Hawai: Anomalia Bouguer Completa"'])
fig3.coast(shorelines="1/0.8p,black", land="lightgray", water="lightblue", resolution="f")
pygmt.makecpt(cmap="turbo", series=[a_bouguer_completa.min(), a_bouguer_completa.max()])
fig3.plot(x=data.lon, y=data.lat, style="c0.25c", fill=data.bouguer_completa, cmap=True, pen="0.1p,black")
fig3.colorbar(frame='af+l"mGal"', position="JBC+w10c+h+o0/1c")
fig3.show()

# =============================================================================
#        NUEVO: SUBPLOTS DE ANOMALÍA DE BOUGUER COMPLETA (VARIAS DENSIDADES)
# =============================================================================
print("Calculando Bouguer Completa para varias densidades...")
# Usamos densidades típicas de basaltos densos hawaianos
densidades_completas = [2300, 2600, 2800, 2900] 
resultados_bc_multi = {}

for rho in densidades_completas:
    densidad_bucle = np.where(elevacion_utm >= 0, rho, rho_agua - rho)
    capa_bucle = hm.prism_layer(
        coordinates=(easting_1d, northing_1d),
        surface=elevacion_utm, reference=0,
        properties={"density": densidad_bucle}
    )
    efecto_bucle = capa_bucle.prism_layer.gravity(
        coordinates=(easting_obs, northing_obs, h), field="g_z"
    )
    resultados_bc_multi[rho] = a_g_l - efecto_bucle

print("Generando subplots...")
fig5 = pygmt.Figure()
with fig5.subplot(nrows=2, ncols=2, figsize=("22c", "22c"), frame="lrtb", 
                  margins=["1.5c", "2.5c"], title="Hawai: Bouguer COMPLETA segun Densidad"):
    for i, rho in enumerate(densidades_completas):
        with fig5.set_panel(panel=i):
            val_bc = resultados_bc_multi[rho]
            fig5.basemap(region=region, projection="M?", frame=["af", f'WSen+t"Densidad {rho/1000} g/cm3"'])
            fig5.coast(shorelines="0.5p,black", land="lightgray", water="lightblue", resolution="f")
            pygmt.makecpt(cmap="turbo", series=[float(val_bc.min()), float(val_bc.max())], continuous=True)
            fig5.plot(x=lon, y=lat, style="c0.2c", fill=val_bc, cmap=True, pen="0.1p,black")
            fig5.colorbar(frame='af+l"mGal"', position="JMR+o0.8c/0c+w4c")
fig5.show()

# =============================================================================
# BLOQUE 6: EXPORTACIÓN DE RESULTADOS A CSV
# =============================================================================
print("6. Exportando resultados finales a CSV...")
resultados = {
    "Longitude": lon, "Latitude": lat, "Elevation_m": h,
    "ObsGravity_mGal": g_obs, "NormalGravity_mGal": g_n,
    "FreeAir_mGal": a_g_l, "Bouguer_Simple_2.6_mGal": a_bouguer,
    "Bouguer_Completa_2.6_mGal": a_bouguer_completa
}

for rho in densidades_completas:
    resultados[f"Bouguer_Completa_{rho/1000}_mGal"] = resultados_bc_multi[rho]

df_final = pd.DataFrame(resultados)
nombre_archivo = r"C:\Users\Usuario\Gravity-data-\VOLCANES\Hawaii\Tablas obtenidas\Tabla_Hawaii_ensaio.csv"
df_final.to_csv(nombre_archivo, index=False, sep=',', encoding='utf-8')

print(f"--- ¡Éxito! Se guardaron {len(df_final)} estaciones limpias en: {nombre_archivo} ---")