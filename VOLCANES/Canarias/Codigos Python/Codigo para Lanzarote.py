# -*- coding: utf-8 -*-
"""
Created on Mon Apr 27 14:20:27 2026

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
# BLOQUE 1: CARGA "INTELIGENTE" Y LIMPIEZA (LANZAROTE)
# =============================================================================
print("1. Cargando y transformando datos de Lanzarote...")

# Pon la ruta exacta de tu archivo de texto/dat
ruta_archivo = r"C:\Users\Usuario\Gravity-data-\VOLCANES\Canarias\Lanzarote\Datos_Lanzarote.txt"

datos_limpios = []

# Leemos el archivo línea por línea para evitar el problema de los nombres con espacios
with open(ruta_archivo, 'r') as f:
    for linea in f:
        partes = linea.split()
        # Si la línea tiene suficientes datos y no es una cabecera de guiones
        if len(partes) >= 7 and "---" not in linea and "Station" not in linea:
            try:
                # Contamos desde el final (derecha a izquierda) porque los números están alineados
                easting = float(partes[-7])
                northing = float(partes[-6])
                elevacion = float(partes[-3])
                gravedad_ugal = float(partes[-2])
                
                # Convertimos microGales a miliGales (mGal)
                gravedad_mgal = gravedad_ugal / 1000.0
                
                datos_limpios.append([easting, northing, elevacion, gravedad_mgal])
            except ValueError:
                pass # Ignoramos las cabeceras de texto

# Creamos el DataFrame
df = pd.DataFrame(datos_limpios, columns=['X_utm', 'Y_utm', 'H', 'Gravedad_mGal'])

# FILTRO 1: Valores absurdos
df = df[(df['Gravedad_mGal'] > 970000) & (df['Gravedad_mGal'] < 990000)]
df = df[(df['H'] > -20) & (df['H'] < 1000)] # El punto más alto de Lanzarote (Peñas del Chache) tiene ~670m

# --- DE METROS (UTM 28N) A GRADOS (LAT/LON) ---
proyeccion = pyproj.Proj(proj="utm", zone=28, ellps="WGS84")
lon_dd, lat_dd = proyeccion(df['X_utm'].values, df['Y_utm'].values, inverse=True)

# Arrays base
lon   = lon_dd
lat   = lat_dd
h     = df['H'].values
g_obs = df['Gravedad_mGal'].values

# Definimos la región de Lanzarote
region = [-14.05, -13.30, 28.80, 29.30] 

print(f" -> Se han cargado {len(g_obs)} puntos correctamente en mGal.")

# =============================================================================
# BLOQUE 2: GRAVEDAD NORMAL Y AIRE LIBRE
# =============================================================================
print("2. Calculando Gravedad Normal y Aire Libre...")
g_n = bl.WGS84.normal_gravity(coordinates=(lon, lat, h))
a_g_l = g_obs - g_n

# =============================================================================
# BLOQUE 3: ANOMALÍA DE BOUGUER SIMPLE Y FILTRO QUIRÚRGICO
# =============================================================================
print("3. Calculando Bouguer Simple y filtrando errores...")
# Usamos 2.6 g/cm3 como base para basalto
densidad_base = 2.60
c_bouguer = 0.04193 * densidad_base * h
a_bouguer = a_g_l - c_bouguer

# Filtro quirúrgico para Canarias (eliminamos errores instrumentales de < 150 mGal)
mascara_buenos = a_bouguer > 150
lon = lon[mascara_buenos]
lat = lat[mascara_buenos]
h = h[mascara_buenos]
g_obs = g_obs[mascara_buenos]
g_n = g_n[mascara_buenos]
a_g_l = a_g_l[mascara_buenos]
a_bouguer = a_bouguer[mascara_buenos]
print(f"   -> Se eliminaron {np.sum(~mascara_buenos)} puntos anómalos.")

# =============================================================================
# BLOQUE 4: ANOMALÍA DE BOUGUER COMPLETA (ENSAIO + VARIAS DENSIDADES)
# =============================================================================
print("4. Procesando topografía y batimetría (Ensaio)...")
archivo_topo = ensaio.fetch_earth_topography(version=1)
topo_global = xr.load_dataarray(archivo_topo)
topo = topo_global.sel(
    longitude=slice(region[0] - 0.5, region[1] + 0.5),
    latitude=slice(region[2] - 0.5, region[3] + 0.5)
)

topo_lon, topo_lat, topo_z = topo.longitude.values, topo.latitude.values, topo.values

# Preparamos la malla y la interpolación
easting_obs, northing_obs = proyeccion(lon, lat)
e_corners, n_corners = proyeccion(np.array([topo_lon.min(), topo_lon.max()]), 
                                  np.array([topo_lat.min(), topo_lat.max()]))

easting_1d = np.linspace(e_corners[0], e_corners[1], len(topo_lon))
northing_1d = np.linspace(n_corners[0], n_corners[1], len(topo_lat))

interpolador = RegularGridInterpolator((topo_lat, topo_lon), topo_z, 
                                        method="linear", bounds_error=False, fill_value=None)
easting_2d, northing_2d = np.meshgrid(easting_1d, northing_1d)
lon_utm, lat_utm = proyeccion(easting_2d, northing_2d, inverse=True)
elevacion_utm = interpolador((lat_utm, lon_utm))

# Bucle de densidades (Lanzarote tiene corteza oceánica antigua y lavas recientes)
densidades_estudio = [2300, 2500, 2600, 2700] 
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

# Guardamos la anomalía principal (2.6 g/cm3)
a_bouguer_completa = resultados_bc_multi[2600]

# =============================================================================
# BLOQUE 5: MAPAS INDIVIDUALES Y SUBPLOTS
# =============================================================================
# =============================================================================
# BLOQUE 5: MAPAS INDIVIDUALES Y SUBPLOTS
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
# --- 1. Anomalía de Aire Libre ---
fig1 = pygmt.Figure()
fig1.basemap(region=region, projection="M15c", frame=["af", 'WSen+t"Lanzarote: Anomalia de Aire Libre"'])
fig1.coast(shorelines="0.5p,black", land="lightgray", water="lightblue", resolution="f")
pygmt.makecpt(cmap="turbo", series=[a_g_l.min(), a_g_l.max()])
fig1.plot(x=data.lon, y=data.lat, style="c0.25c", fill=data.aire_libre, cmap=True, pen="0.1p,black")
fig1.colorbar(frame='af+l"mGal"', position="JBC+w10c+h+o0/1c")
fig1.show()

# --- 2. Anomalía de Bouguer Simple ---
fig2 = pygmt.Figure()
fig2.basemap(region=region, projection="M15c", frame=["af", 'WSen+t"Lanzarote: Anomalia Bouguer Simple"'])
fig2.coast(shorelines="0.5p,black", land="lightgray", water="lightblue", resolution="f")
pygmt.makecpt(cmap="turbo", series=[a_bouguer.min(), a_bouguer.max()])
fig2.plot(x=data.lon, y=data.lat, style="c0.25c", fill=data.bouguer, cmap=True, pen="0.1p,black")
fig2.colorbar(frame='af+l"mGal"', position="JBC+w10c+h+o0/1c")
fig2.show()

# --- 3. Anomalía de Bouguer Completa (2.6 g/cm3) ---
fig3 = pygmt.Figure()
fig3.basemap(region=region, projection="M15c", frame=["af", 'WSen+t"Lanzarote: Bouguer Completa (2.6 g/cm3)"'])
fig3.coast(shorelines="0.5p,black", land="lightgray", water="lightblue", resolution="f")
pygmt.makecpt(cmap="turbo", series=[a_bouguer_completa.min(), a_bouguer_completa.max()])
fig3.plot(x=data.lon, y=data.lat, style="c0.25c", fill=data.bouguer_completa, cmap=True, pen="0.1p,black")
fig3.colorbar(frame='af+l"mGal"', position="JBC+w10c+h+o0/1c")
fig3.show()

# --- 4. SUBPLOTS COMPARATIVOS ---
fig_sub = pygmt.Figure()
with fig_sub.subplot(nrows=2, ncols=2, figsize=("22c", "22c"), frame="lrtb", 
                     margins=["1.5c", "2.5c"], title="Lanzarote: Comparativa de Densidades"):
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
    "FreeAir_mGal": a_g_l, "Bouguer_Simple_2.6_mGal": a_bouguer,
    "Bouguer_Completa_2.6_mGal": a_bouguer_completa
}

for rho in densidades_estudio:
    resultados[f"Bouguer_Completa_{rho/1000}_mGal"] = resultados_bc_multi[rho]

df_final = pd.DataFrame(resultados)
nombre_archivo = r"C:\Users\Usuario\Gravity-data-\VOLCANES\Canarias\Tablas generadas\Tabla_Lanzarote_ensaio.csv"
df_final.to_csv(nombre_archivo, index=False, sep=',', encoding='utf-8')

print(f"--- ¡Éxito! Se guardaron {len(df_final)} estaciones limpias en: {nombre_archivo} ---")