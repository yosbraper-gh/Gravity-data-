# -*- coding: utf-8 -*-
"""
Created on Tue Apr 28 09:49:46 2026

@author: Usuario
"""

import pandas as pd
import numpy as np
import boule as bl
import harmonica as hm
import pygmt
import pyproj
from scipy.interpolate import RegularGridInterpolator
import ensaio
import xarray as xr

# =============================================================================
# BLOQUE 1: CARGA "A PRUEBA DE BOMBAS" (TENERIFE - IGN/CSIC)
# =============================================================================
print("1. Cargando y limpiando datos del archivo .txt de Tenerife...")

# Cambia la ruta por la de tu ordenador
ruta_txt = r"C:\Users\Usuario\Gravity-data-\VOLCANES\Canarias\Tenerife\Datos_Tenerife.txt"

# Leemos el archivo. 
# skiprows=14 salta toda la cabecera de texto y los símbolos "==="
# Le damos los nombres exactos a las 9 columnas que vemos en tu imagen
df = pd.read_csv(ruta_txt, sep=r'\s+', skiprows=3, on_bad_lines='skip',
                 names=['EST', 'E_m', 'N_m', 'Lon', 'Lat', 'h', 'Abs', 'BO_ign', 'Error'])

# Convertimos a formato numérico matemático SOLO las columnas que vamos a usar.
# Si hay algún error tipográfico en el TXT, lo convierte a "vacío" (NaN)
for col in ['Lon', 'Lat', 'h', 'Abs']:
    df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')

# Borramos filas que se hayan quedado vacías en esas columnas críticas
df = df.dropna(subset=['Lon', 'Lat', 'h', 'Abs'])

# Filtro básico de seguridad
df = df[(df['Abs'] > 970000) & (df['Abs'] < 990000)]
df = df[(df['h'] > -50) & (df['h'] < 4000)] # El Teide mide 3718m

# Arrays base (Ignoramos la columna BO_ign tal y como pediste)
lon   = df['Lon'].values
lat   = df['Lat'].values
h     = df['h'].values
g_obs = df['Abs'].values

# Definimos la región centrada en Tenerife
region = [-17.0, -16.1, 27.9, 28.65]

print(f" -> Se han cargado {len(g_obs)} estaciones con éxito.")

# =============================================================================
# BLOQUE 2: GRAVEDAD NORMAL Y AIRE LIBRE
# =============================================================================
print("2. Calculando Gravedad Normal y Aire Libre...")
g_n = bl.WGS84.normal_gravity(coordinates=(lon, lat, h))
a_g_l = g_obs - g_n

# =============================================================================
# BLOQUE 3: ANOMALÍA DE BOUGUER SIMPLE Y FILTRO QUIRÚRGICO
# =============================================================================
print("3. Calculando Bouguer Simple y filtrando errores locales...")
# Usamos la densidad clásica de 2.40 g/cm3 (2400 kg/m3) habitual en Tenerife
densidad_base = 2.40
c_bouguer = 0.04193 * densidad_base * h
a_bouguer = a_g_l - c_bouguer

# Filtro para Canarias (eliminamos anomalías sin sentido físico < 150 mGal)
mascara_buenos = a_bouguer > 150
lon = lon[mascara_buenos]
lat = lat[mascara_buenos]
h = h[mascara_buenos]
g_obs = g_obs[mascara_buenos]
g_n = g_n[mascara_buenos]
a_g_l = a_g_l[mascara_buenos]
a_bouguer = a_bouguer[mascara_buenos]
print(f"   -> Se eliminaron {np.sum(~mascara_buenos)} puntos atípicos.")

# =============================================================================
# BLOQUE 4: ANOMALÍA DE BOUGUER COMPLETA (MODELO ENSAIO)
# =============================================================================
print("4. Procesando corrección topográfica 3D (Ensaio)...")

archivo_topo = ensaio.fetch_earth_topography(version=1)
topo_global = xr.load_dataarray(archivo_topo)
topo = topo_global.sel(
    longitude=slice(region[0] - 0.5, region[1] + 0.5),
    latitude=slice(region[2] - 0.5, region[3] + 0.5)
)

topo_lon, topo_lat, topo_z = topo.longitude.values, topo.latitude.values, topo.values

# Proyección a Metros (UTM Zona 28N para Canarias)
proyeccion = pyproj.Proj(proj="utm", zone=28, ellps="WGS84")
easting_obs, northing_obs = proyeccion(lon, lat)

# Generación de la malla interpolada
e_corners, n_corners = proyeccion(np.array([topo_lon.min(), topo_lon.max()]), 
                                  np.array([topo_lat.min(), topo_lat.max()]))
easting_1d = np.linspace(e_corners[0], e_corners[1], len(topo_lon))
northing_1d = np.linspace(n_corners[0], n_corners[1], len(topo_lat))

interpolador = RegularGridInterpolator((topo_lat, topo_lon), topo_z, 
                                        method="linear", bounds_error=False, fill_value=None)
easting_2d, northing_2d = np.meshgrid(easting_1d, northing_1d)
lon_utm, lat_utm = proyeccion(easting_2d, northing_2d, inverse=True)
elevacion_utm = interpolador((lat_utm, lon_utm))

# --- BUCLE DE DENSIDADES COMPLETA ---
densidades_estudio = [2200, 2400, 2500, 2700] 
rho_agua = 1030
resultados_bc_multi = {}

for rho in densidades_estudio:
    print(f"   -> Calculando atracción 3D para densidad: {rho} kg/m3...")
    densidad_prismas = np.where(elevacion_utm >= 0, rho, rho_agua - rho)
    
    capa_prismas = hm.prism_layer(
        coordinates=(easting_1d, northing_1d),
        surface=elevacion_utm, reference=0,
        properties={"density": densidad_prismas}
    )
    
    efecto_topo = capa_prismas.prism_layer.gravity(
        coordinates=(easting_obs, northing_obs, h), field="g_z"
    )
    
    resultados_bc_multi[rho] = a_g_l - efecto_topo

# Guardamos la anomalía principal (2.40 g/cm3) para el mapa individual
a_bouguer_completa = resultados_bc_multi[2400]

# =============================================================================
# BLOQUE 5: MAPAS INDIVIDUALES Y SUBPLOTS CON PYGMT
# =============================================================================
print("5. Generando visualizaciones...")

data = pd.DataFrame({
    "lon": lon, "lat": lat, "g_obs": g_obs,
    "aire_libre": a_g_l, "bouguer": a_bouguer, "bouguer_completa": a_bouguer_completa
})

# --- MAPA 0: Gravedad Observada ---
fig0 = pygmt.Figure()
fig0.basemap(region=region, projection="M15c", frame=["af", 'WSen+t"Tenerife: Gravedad Observada (Absoluta)"'])
fig0.coast(shorelines="0.5p,black", land="lightgray", water="lightblue", resolution="f")
pygmt.makecpt(cmap="turbo", series=[data.g_obs.min(), data.g_obs.max()])
fig0.plot(x=data.lon, y=data.lat, style="c0.25c", fill=data.g_obs, cmap=True, pen="0.1p,black")
fig0.colorbar(frame='af+l"mGal"', position="JBC+w10c+h+o0/1c")
fig0.show()

# --- MAPA 1: Anomalía de Aire Libre ---
fig1 = pygmt.Figure()
fig1.basemap(region=region, projection="M15c", frame=["af", 'WSen+t"Tenerife: Anomalia de Aire Libre"'])
fig1.coast(shorelines="0.5p,black", land="lightgray", water="lightblue", resolution="f")
pygmt.makecpt(cmap="turbo", series=[a_g_l.min(), a_g_l.max()])
fig1.plot(x=data.lon, y=data.lat, style="c0.25c", fill=data.aire_libre, cmap=True, pen="0.1p,black")
fig1.colorbar(frame='af+l"mGal"', position="JBC+w10c+h+o0/1c")
fig1.show()

# --- MAPA 2: Anomalía de Bouguer Simple ---
fig2 = pygmt.Figure()
fig2.basemap(region=region, projection="M15c", frame=["af", 'WSen+t"Tenerife: Anomalia Bouguer Simple (2.4 g/cm3)"'])
fig2.coast(shorelines="0.5p,black", land="lightgray", water="lightblue", resolution="f")
pygmt.makecpt(cmap="turbo", series=[a_bouguer.min(), a_bouguer.max()])
fig2.plot(x=data.lon, y=data.lat, style="c0.25c", fill=data.bouguer, cmap=True, pen="0.1p,black")
fig2.colorbar(frame='af+l"mGal"', position="JBC+w10c+h+o0/1c")
fig2.show()

# --- MAPA 3: Anomalía de Bouguer Completa ---
fig3 = pygmt.Figure()
fig3.basemap(region=region, projection="M15c", frame=["af", 'WSen+t"Tenerife: Bouguer Completa (2.4 g/cm3)"'])
fig3.coast(shorelines="0.5p,black", land="lightgray", water="lightblue", resolution="f")
pygmt.makecpt(cmap="turbo", series=[a_bouguer_completa.min(), a_bouguer_completa.max()])
fig3.plot(x=data.lon, y=data.lat, style="c0.25c", fill=data.bouguer_completa, cmap=True, pen="0.1p,black")
fig3.colorbar(frame='af+l"mGal"', position="JBC+w10c+h+o0/1c")
fig3.show()

# --- MAPA 4: SUBPLOTS COMPARATIVOS (DENSIDADES) ---
fig_sub = pygmt.Figure()
with fig_sub.subplot(nrows=2, ncols=2, figsize=("22c", "22c"), frame="lrtb", 
                     margins=["1.5c", "2.5c"], title="Tenerife: Comparativa Bouguer Completa"):
    for i, rho in enumerate(densidades_estudio):
        with fig_sub.set_panel(panel=i):
            val = resultados_bc_multi[rho]
            fig_sub.basemap(region=region, projection="M?", frame=["af", f'WSen+t"{rho/1000} g/cm3"'])
            fig_sub.coast(shorelines="0.5p,black", land="lightgray", water="lightblue", resolution="f")
            pygmt.makecpt(cmap="turbo", series=[float(val.min()), float(val.max())])
            fig_sub.plot(x=lon, y=lat, style="c0.2c", fill=val, cmap=True, pen="0.1p,black")
            fig_sub.colorbar(frame='af+l"mGal"', position="JMR+o0.8c/0c+w4c")
fig_sub.show()

# =============================================================================
# BLOQUE 6: EXPORTACIÓN DE RESULTADOS A CSV
# =============================================================================
print("6. Exportando resultados finales a CSV...")
resultados = {
    "Longitude": lon, "Latitude": lat, "Elevation_m": h,
    "ObsGravity_mGal": g_obs, "NormalGravity_mGal": g_n,
    "FreeAir_mGal": a_g_l, "Bouguer_Simple_2.4_mGal": a_bouguer,
    "Bouguer_Completa_2.4_mGal": a_bouguer_completa
}

for rho in densidades_estudio:
    resultados[f"Bouguer_Completa_{rho/1000}_mGal"] = resultados_bc_multi[rho]

df_final = pd.DataFrame(resultados)
nombre_archivo = r"C:\Users\Usuario\Gravity-data-\VOLCANES\Canarias\Tenerife\Tabla_Tenerife_ensaio.csv"
df_final.to_csv(nombre_archivo, index=False, sep=',', encoding='utf-8')

print(f"--- ¡Éxito! Se guardaron {len(df_final)} estaciones en: {nombre_archivo} ---")