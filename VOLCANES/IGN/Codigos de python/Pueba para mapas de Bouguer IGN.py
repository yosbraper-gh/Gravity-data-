# -*- coding: utf-8 -*-
"""
Created on Thu Apr 23 15:11:56 2026

@author: Usuario
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import boule as bl
import harmonica as hm
import pygmt


# =============================================================================
#                      CARGA Y LIMPIEZA DE DATOS
# =============================================================================

df = pd.read_csv('Datos_IGN_Completos_Filtrados_Lanzarote - copia.csv', dtype=str)

def dms_to_dd_vector(col):
    col = col.str.replace(',', '.', regex=False)
    d = col.str.extract(r'(\d+)[^\d]+(\d+)[^\d]+(\d+\.?\d*)')
    d = d.astype(float)
    dd = d[0] + d[1]/60 + d[2]/3600
    dd[col.str.contains('W|-', na=False)] *= -1
    return dd

df['lat_dd'] = dms_to_dd_vector(df['Latitud'])
df['lon_dd']  = dms_to_dd_vector(df['Longitud'])

df['Gravedad_mGal']   = pd.to_numeric(df['Gravedad_mGal'],   errors='coerce')
df['Alt_Ortometrica'] = pd.to_numeric(df['Alt_Ortometrica'], errors='coerce')

df = df.dropna(subset=['Gravedad_mGal', 'lat_dd', 'Alt_Ortometrica'])

# Arrays base
lat   = df['lat_dd'].values
lon   = df['lon_dd'].values
h     = df['Alt_Ortometrica'].values
g_obs = df['Gravedad_mGal'].values
print(h)
# =============================================================================
#  DEFINICIÓN DE LA REGIÓN (MUÉVELO AQUÍ)
# =============================================================================
margin = 0.05
region = [lon.min()-margin, lon.max()+margin,
          lat.min()-margin, lat.max()+margin]


#           ANOMALÍA DE BOUGUER COMPLETA (CORRECCIÓN TOPOGRÁFICA)
# =============================================================================

# tiene en cuenta el relieve real: resta el efecto de las montañas que "tiran"
# del gravímetro hacia arriba y suma el efecto de los valles (huecos de masa)
# que están por debajo.

# 1. Definir un Modelo Digital de Elevaciones (DEM).
# 2. Convertir ese relieve en prismas de densidad constante.
# 3. Calcular la atracción gravitatoria de todos esos prismas en cada uno de tus puntos de medida.


# =============================================================================
#   ANOMALÍA DE BOUGUER COMPLETA (CORRECCIÓN TOPOGRÁFICA)
# =============================================================================
import pyproj  # transforma coordenadas entre sistemas de referencia, convertimos
#                de (lon/lat en grados) a cartesianas metros
from scipy.interpolate import RegularGridInterpolator  #para proyectar la topografía
                                                       # a la nueva malla en metros.

# 1. Cargar topografía: descarga del modelo digital de elevación global, igpp
topo = pygmt.datasets.load_earth_relief(resolution="15s", region=region)

# 2. Proyección UTM zona 28N (Lanzarote)
proyeccion = pyproj.Proj(proj="utm", zone=28, ellps="WGS84")

# 3. Proyectar los puntos de observación: convierte mis coordenadas en grados a metros
easting_obs, northing_obs = proyeccion(lon, lat)

# 4. Proyectar las esquinas de la región para definir la malla UTM, para empezar a definir
# el mallado que vamos a usar.

lon_corners = np.array([topo.lon.values.min(), topo.lon.values.max()])
lat_corners = np.array([topo.lat.values.min(), topo.lat.values.max()])
e_corners, n_corners = proyeccion(lon_corners, lat_corners)

# 5. Crear malla regular en UTM con el mismo número de puntos que la topografía
n_lon = len(topo.lon.values)
n_lat = len(topo.lat.values)

easting_1d  = np.linspace(e_corners[0], e_corners[1], n_lon)
northing_1d = np.linspace(n_corners[0], n_corners[1], n_lat)

# 6. Re-interpolar la elevación a la nueva malla UTM regular
#    Primero creamos el interpolador sobre la malla original lon/lat
interpolador = RegularGridInterpolator(
    (topo.lat.values, topo.lon.values),  # ejes originales
    topo.values,                          # elevación 2D
    method="linear",
    bounds_error=False,
    fill_value=None
)

# Crear malla 2D UTM y convertir de vuelta a lon/lat para interpolar
easting_2d, northing_2d = np.meshgrid(easting_1d, northing_1d)
lon_utm, lat_utm = proyeccion(easting_2d, northing_2d, inverse=True)

# Interpolar elevación en los puntos de la malla UTM
elevacion_utm = interpolador((lat_utm, lon_utm))

# 7. Definir densidades
rho_roca = 2480
rho_agua = 1030
densidad = np.where(elevacion_utm >= 0, rho_roca, rho_agua - rho_roca)

# 8. Crear capa de prismas sobre malla UTM regular
capa_prismas = hm.prism_layer(
    coordinates=(easting_1d, northing_1d),  # arrays 1D uniformes en metros
    surface=elevacion_utm,
    reference=0,
    properties={"density": densidad}
)

# 9. Calcular efecto gravitatorio en los puntos de observación
efecto_topografico = capa_prismas.prism_layer.gravity(
    coordinates=(easting_obs, northing_obs, h),
    field="g_z"
)

# 10. Anomalía de Bouguer Completa
a_bouguer_completa = a_g_l - efecto_topografico

print('Anomalia de Bouguer Completa calculada con exito!')
print('Min:', a_bouguer_completa.min(), 'Max:', a_bouguer_completa.max())



# =============================================================================
#                     REPRESENTACIÓN CON PYGMT
# =============================================================================

data = pd.DataFrame({
    "lon":        lon,
    "lat":        lat,
    "aire_libre": a_g_l,
    "bouguer":    a_bouguer
})

# --- Mapa Anomalía Aire Libre ---
fig = pygmt.Figure()

fig.basemap(region=region, projection="M15c", frame=["af", "WSen"])
fig.coast(shorelines="1/0.8p,black", land="lightgray",
          water="lightblue", resolution="f")

vmin, vmax = a_g_l.min(), a_g_l.max()
pygmt.makecpt(cmap="turbo", series=[vmin, vmax])

fig.plot(x=data.lon, y=data.lat, style="c0.5c", fill=data.aire_libre, cmap=True)
fig.colorbar(frame='af+l"Anomalía de Aire Libre (mGal)"', position="JBC+w10c+h")
fig.show()


# --- Mapa Anomalía de Bouguer ---
fig2 = pygmt.Figure()


fig2.basemap(region=region, projection="M15c", frame=["af", "WSen"])
fig2.coast(shorelines="1/0.8p,black", land="lightgray",
           water="lightblue", resolution="f")

vmin_b, vmax_b = a_bouguer.min(), a_bouguer.max()
pygmt.makecpt(cmap="turbo", series=[vmin_b, vmax_b])

fig2.plot(x=data.lon, y=data.lat, style="c0.5c", fill=data.bouguer, cmap=True)
fig2.colorbar(frame='af+l"Anomalía de Bouguer Simple (mGal)"', position="JBC+w10c+h")
fig2.show()
#fig2.show('method external')


# --- Mapa Anomalía de Bouguer Completa---


# Añadir al DataFrame
data["bouguer_completa"] = a_bouguer_completa

fig4 = pygmt.Figure()

fig4.basemap(region=region,projection="M15c",frame=["af", "WSen"])
fig4.coast(shorelines="1/0.8p,black",land="lightgray",water="lightblue",resolution="f")

vmin_bc = float(a_bouguer_completa.min())
vmax_bc = float(a_bouguer_completa.max())
pygmt.makecpt(cmap="turbo", series=[vmin_bc, vmax_bc])

fig4.plot(x=data.lon,y=data.lat,style="c0.5c",fill=data.bouguer_completa,cmap=True)

fig4.colorbar(frame="af+lAnomalia de Bouguer Completa (mGal)",position="JBC+w10c+h")
fig4.show()
# =============================================================================
#           EXPORTACIÓN DE RESULTADOS A CSV
# =============================================================================

# Creamos un diccionario con todas las variables calculadas
resultados = {
    "Longitud_DD": lon,
    "Latitud_DD": lat,
    "Elevacion_m": h,
    "Gravedad_Obs_mGal": g_obs,
    "Gravedad_Normal_mGal": g_n,
    "Anomalia_Aire_Libre_mGal": a_g_l,
    "Anomalia_Bouguer_Simple_mGal": a_bouguer,
    "Anomalia_Bouguer_Completa_mGal": a_bouguer_completa
}

# Convertimos el diccionario a un DataFrame de Pandas
df_final = pd.DataFrame(resultados)

# Guardamos el archivo CSV en la misma carpeta donde está tu script
nombre_archivo = "Resultados_Gravimetria_Lanzarote.csv"
df_final.to_csv(nombre_archivo, index=False, sep=',', encoding='utf-8')

print(f"--- Exportación completada ---")
print(f"Los resultados se han guardado en: Resultados_Gravimetría_Lanzarote")
