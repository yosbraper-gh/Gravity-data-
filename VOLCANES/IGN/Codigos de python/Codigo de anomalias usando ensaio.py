# -*- coding: utf-8 -*-
"""
Created on Fri Apr 24 12:37:07 2026

@author: Usuario
"""
# -*- coding: utf-8 -*-
"""
Created on Fri Apr 24 11:59:23 2026

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
# BLOQUE 1: CARGA Y LIMPIEZA EXTREMA DE DATOS
# =============================================================================
print("1. Cargando y limpiando datos...")
# Cambia la ruta por la tuya exacta si hace falta
ruta_csv = r"C:\Users\Usuario\Desktop\IGN\Lineas de Canarias\Tenerife\Tenerife_Base_Datos_Limpia.csv"
df = pd.read_csv(ruta_csv, dtype=str)

# Función para pasar grados, minutos, segundos a decimales
def dms_to_dd_vector(col):
    col = col.str.replace(',', '.', regex=False)
    d = col.str.extract(r'(\d+)[^\d]+(\d+)[^\d]+(\d+\.?\d*)')
    d = d.astype(float)
    dd = d[0] + d[1]/60 + d[2]/3600
    dd[col.str.contains('W|-', na=False)] *= -1
    return dd

df['lat_dd'] = dms_to_dd_vector(df['Latitud'])
df['lon_dd']  = dms_to_dd_vector(df['Longitud'])

# Convertimos a números y forzamos puntos en lugar de comas
df['Gravedad_mGal']   = pd.to_numeric(df['Gravedad_mGal'].astype(str).str.replace(',', '.'), errors='coerce')
df['Alt_Ortometrica'] = pd.to_numeric(df['Alt_Ortometrica'].astype(str).str.replace(',', '.'), errors='coerce')
df = df.dropna(subset=['Gravedad_mGal', 'lat_dd', 'Alt_Ortometrica'])

# FILTRO 1: Valores absurdos (Ej: el punto de 1.000.000.000 mGal)
df = df[(df['Gravedad_mGal'] > 970000) & (df['Gravedad_mGal'] < 990000)]
df = df[(df['Alt_Ortometrica'] > -50) & (df['Alt_Ortometrica'] < 4000)]

# Arrays base
lat   = df['lat_dd'].values
lon   = df['lon_dd'].values
h     = df['Alt_Ortometrica'].values
g_obs = df['Gravedad_mGal'].values

# Definimos la región 
region = [-17.0, -16.1, 27.9, 28.65] # Tenerife

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
# Densidad en g/cm3 para la fórmula de Bouguer Simple
densidad_g_cm3 = 2.40
c_bouguer = 0.04193 * densidad_g_cm3 * h
a_bouguer = a_g_l - c_bouguer

# FILTRO 2: Filtro quirúrgico (Quitamos los puntos oscuros sin sentido físico < 150 mGal)
mascara_buenos = a_bouguer > 150
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
# Descarga y carga del modelo global
archivo_topo = ensaio.fetch_earth_topography(version=1)
topo_global = xr.load_dataarray(archivo_topo)

# RECORTAMOS el modelo global a nuestra región para que el PC no colapse
topo = topo_global.sel(
    longitude=slice(region[0] - 0.5, region[1] + 0.5),
    latitude=slice(region[2] - 0.5, region[3] + 0.5)
)

topo_lon = topo.longitude.values
topo_lat = topo.latitude.values
topo_z = topo.values  # Alturas (+) y profundidades (-)

# Proyecciones a metros (UTM 28N)
proyeccion = pyproj.Proj(proj="utm", zone=28, ellps="WGS84")
easting_obs, northing_obs = proyeccion(lon, lat)

lon_corners = np.array([topo_lon.min(), topo_lon.max()])
lat_corners = np.array([topo_lat.min(), topo_lat.max()])
e_corners, n_corners = proyeccion(lon_corners, lat_corners)

# Mallado e interpolación
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

# Definimos las densidades de la roca y el agua (kg/m3)
rho_roca = 2400
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
print("5. Generando mapas de alta calidad...")

# DataFrame final para PyGMT
data = pd.DataFrame({
    "lon": lon, "lat": lat, 
    "aire_libre": a_g_l, "bouguer": a_bouguer, "bouguer_completa": a_bouguer_completa
})

# --- Mapa 1: Anomalía de Aire Libre ---
fig = pygmt.Figure()
fig.basemap(region=region, projection="M15c", frame=["af", 'WSen+t"Anomalia de Aire Libre"'])
fig.coast(shorelines="1/0.8p,black", land="lightgray", water="lightblue", resolution="f")
pygmt.makecpt(cmap="turbo", series=[a_g_l.min(), a_g_l.max()])
fig.plot(x=data.lon, y=data.lat, style="c0.35c", fill=data.aire_libre, cmap=True, pen="0.1p,black")
fig.colorbar(frame='af+l"mGal"', position="JBC+w10c+h+o0/1c")
fig.show()

# --- Mapa 2: Anomalía de Bouguer Simple ---
fig2 = pygmt.Figure()
fig2.basemap(region=region, projection="M15c", frame=["af", 'WSen+t"Anomalia de Bouguer Simple"'])
fig2.coast(shorelines="1/0.8p,black", land="lightgray", water="lightblue", resolution="f")
pygmt.makecpt(cmap="turbo", series=[a_bouguer.min(), a_bouguer.max()])
fig2.plot(x=data.lon, y=data.lat, style="c0.35c", fill=data.bouguer, cmap=True, pen="0.1p,black")
fig2.colorbar(frame='af+l"mGal"', position="JBC+w10c+h+o0/1c")
fig2.show()

# --- Mapa 3: Anomalía de Bouguer Completa ---
fig3 = pygmt.Figure()
fig3.basemap(region=region, projection="M15c", frame=["af", 'WSen+t"Anomalia de Bouguer Completa (Topografia + Batimetria)"'])
fig3.coast(shorelines="1/0.8p,black", land="lightgray", water="lightblue", resolution="f")
pygmt.makecpt(cmap="turbo", series=[a_bouguer_completa.min(), a_bouguer_completa.max()])
fig3.plot(x=data.lon, y=data.lat, style="c0.35c", fill=data.bouguer_completa, cmap=True, pen="0.1p,black")
fig3.colorbar(frame='af+l"mGal"', position="JBC+w10c+h+o0/1c")
fig3.show()


# =============================================================================
#        NUEVO: SUBPLOTS DE ANOMALÍA DE BOUGUER COMPLETA (VARIAS DENSIDADES)
# =============================================================================
print("Calculando Bouguer Completa para varias densidades...")

# Ojo: Aquí usamos kg/m3 porque Harmonica trabaja en el Sistema Internacional
densidades_completas = [2200, 2300, 2400, 2500] 
resultados_bc_multi = {}

for rho in densidades_completas:
    print(f" -> Procesando prismas 3D para {rho} kg/m3...")
    # 1. Ajustar el contraste de densidad en el mar para esta nueva roca
    densidad_bucle = np.where(elevacion_utm >= 0, rho, rho_agua - rho)
    
    # 2. Crear los prismas usando la malla (easting_1d, northing_1d) que ya tenías
    capa_bucle = hm.prism_layer(
        coordinates=(easting_1d, northing_1d),
        surface=elevacion_utm,
        reference=0,
        properties={"density": densidad_bucle}
    )
    
    # 3. Calcular la atracción gravitatoria
    efecto_bucle = capa_bucle.prism_layer.gravity(
        coordinates=(easting_obs, northing_obs, h),
        field="g_z"
    )
    
    # 4. Calcular la anomalía completa final y guardarla en el diccionario
    resultados_bc_multi[rho] = a_g_l - efecto_bucle

# --- Dibujar los Subplots ---
print("Generando subplots de Bouguer Completa...")
fig5 = pygmt.Figure()

with fig5.subplot(
    nrows=2, ncols=2, figsize=("22c", "22c"), frame="lrtb", 
    margins=["1.5c", "2.5c"], title="Anomalia Bouguer COMPLETA segun Densidad"
):
    for i, rho in enumerate(densidades_completas):
        with fig5.set_panel(panel=i):
            val_bc = resultados_bc_multi[rho]
            
            # Mapas base
            fig5.basemap(region=region, projection="M?", frame=["af", f'WSen+t"Densidad {rho/1000} g/cm3"'])
            fig5.coast(shorelines="0.5p,black", land="lightgray", water="lightblue", resolution="f")
            
            # Escala de color dinámica para cada densidad
            vmin_i, vmax_i = float(val_bc.min()), float(val_bc.max())
            pygmt.makecpt(cmap="turbo", series=[vmin_i, vmax_i], continuous=True)
            
            # Puntos
            fig5.plot(x=lon, y=lat, style="c0.3c", fill=val_bc, cmap=True, pen="0.1p,black")
            fig5.colorbar(frame='af+l"mGal"', position="JMR+o0.8c/0c+w4c")

fig5.show()




print("¡Proceso finalizado con éxito!")

# =============================================================================
# BLOQUE 6: EXPORTACIÓN DE RESULTADOS A CSV
# =============================================================================
print("6. Exportando resultados finales a CSV...")



# Creamos un diccionario con todas las variables calculadas.
# Al usar las variables filtradas (lon, lat, h, etc.), todas tienen la misma longitud.
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

# Definimos el nombre del archivo (puedes cambiarlo según la isla)
nombre_archivo = r"C:\Users\Usuario\Desktop\IGN\Tablas obtenidas\Tabla_Tenerife_ensaio.csv"

# Guardamos el archivo CSV. 
# index=False evita que se añada una columna extra de números (0, 1, 2...) al principio.
df_final.to_csv(nombre_archivo, index=False, sep=',', encoding='utf-8')

print("--- Exportación completada con éxito ---")
print(f"Se han guardado {len(df_final)} estaciones gravimétricas limpias en: {nombre_archivo}")




