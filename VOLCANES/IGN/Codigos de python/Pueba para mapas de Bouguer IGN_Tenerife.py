# -*- coding: utf-8 -*-
"""
Created on Thu Apr 23 15:18:50 2026

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

df = pd.read_csv(r"C:\Users\Usuario\Desktop\IGN\Lineas de Canarias\Tenerife\Tenerife_Base_Datos_Limpia.csv", dtype=str)

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

df = df.dropna(subset=['Gravedad_mGal', 'lat_dd', 'Alt_Ortometrica'])

# =============================================================================
# --- NUEVO: FILTRO DE VALORES ALTOS-
# La gravedad real en Canarias ronda los 979,000 mGal. El Teide mide 3718 m.
# Le decimos a Pandas: "Quédate solo con los datos que tengan sentido físico"
df = df[(df['Gravedad_mGal'] > 970000) & (df['Gravedad_mGal'] < 990000)]
df = df[(df['Alt_Ortometrica'] > -50) & (df['Alt_Ortometrica'] < 4000)]
# =============================================================================

# Arrays base
lat   = df['lat_dd'].values
lon   = df['lon_dd'].values
h     = df['Alt_Ortometrica'].values
g_obs = df['Gravedad_mGal'].values
print(h)
# =============================================================================
#  DEFINICIÓN DE LA REGIÓN
# =============================================================================
margin = 0.05
region = [-17.0, -16.1, 27.9, 28.65]


# =============================================================================
#                 GRAVEDAD NORMAL — SUSTITUIDA POR HARMONICA
# =============================================================================

# ANTES (fórmula manual):
# g_e = 978032.67715
# b_1 = 5.3024e-3
# b_2 = -5.8e-6
# g_n = g_e * (1 + b_1*sin²(lat) + b_2*sin²(2lat))

# AHORA (Harmonica, WGS84, altura en metros):
# normal_gravity devuelve en mGal igual que tu fórmula manual
elipsoide = bl.WGS84
g_n = bl.WGS84.normal_gravity(coordinates=(lon, lat, h))
# =============================================================================
#              ANOMALÍA DE AIRE LIBRE — SUSTITUIDA POR HARMONICA
# =============================================================================

# ANTES (manual):
# d_g_l = -0.3086 * h
# a_g_l = g_obs - (g_n + d_g_l)

# AHORA: como normal_gravity ya recibe la altura h, la corrección de aire libre
# va implícita dentro de g_n, así que la anomalía es simplemente:
a_g_l = g_obs - g_n

print('Anomalía de Aire Libre (mGal):', a_g_l)

# =============================================================================
#                     ANOMALÍA DE BOUGUER SIMPLE
# =============================================================================

# La corrección de Bouguer simple es: C_B = 0.04193 * rho * h
# La anomalía de Bouguer = Anomalía Aire Libre - C_B

densidad_referencia = 2.400   # g/cm³, densidad estándar de la corteza

c_bouguer = 0.04193 * densidad_referencia * h
a_bouguer = a_g_l - c_bouguer

print('Anomalía de Bouguer Simple (mGal):', a_bouguer)



# =============================================================================
# FILTRO DE VALORES BAJOS DEL EXCEL
# =============================================================================
# Mirando la gráfica, sabemos que los datos reales de Tenerife están por encima 
# de 150 mGal. Creamos una "máscara" para quedarnos solo con los buenos.
mascara_buenos = a_bouguer > 150

# Aplicamos la máscara a todas nuestras variables a la vez para borrar los puntos malos
lon = lon[mascara_buenos]
lat = lat[mascara_buenos]
h = h[mascara_buenos]
g_obs = g_obs[mascara_buenos]
g_n = g_n[mascara_buenos]
a_g_l = a_g_l[mascara_buenos]
a_bouguer = a_bouguer[mascara_buenos]

print(f"Se han eliminado {np.sum(~mascara_buenos)} puntos con errores de medición.")
# =============================================================================

# --- Comparación visual para diferentes densidades ---
densidades = [2.2, 2.4, 2.5, 2.7]
plt.figure(figsize=(10, 6))
for rho in densidades:
    c_b = 0.04193 * rho * h
    a_b = a_g_l - c_b
    plt.scatter(lon, a_b, label=f'ρ = {rho} g/cm³', s=10)

plt.title('Comparación Anomalía de Bouguer para distintas densidades')
plt.xlabel('Longitud (°)')
plt.ylabel('Anomalía de Bouguer (mGal)')
plt.legend()
plt.grid(True, linestyle='--', alpha=0.7)
plt.tight_layout()
plt.show()


# =============================================================================
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
#topo = pygmt.datasets.load_earth_relief(resolution="15s", region=region)
# Recomendado para precisión profesional en Lanzarote
topo = pygmt.datasets.load_earth_relief(resolution="03s", region=region, registration="gridline")
#(3 segundos de arco ~90m)


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
rho_roca = 2400
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
#       MAPAS DE ANOMALÍA DE BOUGUER PARA DISTINTAS DENSIDADES (SUBPLOTS)
# =============================================================================

fig3 = pygmt.Figure()

# 1. Añadimos 'margins' para dar espacio entre los mapas (ej. 1.5cm en X y 2.5cm en Y)
# 2. 'title' es el título general de toda la figura
with fig3.subplot(
    nrows=2,
    ncols=2,
    figsize=("22c", "22c"),
    frame="lrtb",
    margins=["1.5c", "2.5c"],
    title="Anomalía de Bouguer según Densidad (Tenerife)"
):
    for i, rho in enumerate(densidades):
        with fig3.set_panel(panel=i):
           
            # Cálculos
            c_b_temp = 0.04193 * rho * h
            a_b_temp = a_g_l - c_b_temp
           
            # Configurar el mapa del panel
            # Quitamos 'af' de los paneles internos si no quieres repetir coordenadas en todos,
            # pero para claridad lo dejamos con un offset de título
            fig3.basemap(
                region=region,
                projection="M?",
                frame=["af", f'WSen+t"Densidad {rho} g/cm3"']
            )
           
            fig3.coast(shorelines="0.5p,black", land="lightgray", water="lightblue", resolution="f")
           
            # Escala de colores
            vmin_i, vmax_i = a_b_temp.min(), a_b_temp.max()
            pygmt.makecpt(cmap="turbo", series=[vmin_i, vmax_i], continuous=True)
           
            # Pintar puntos
            fig3.plot(x=lon, y=lat, style="c0.3c", fill=a_b_temp, cmap=True, pen="0.1p,black")
           
            # Barra de colores: La movemos un poco a la derecha (+o0.8c) para que no pise el mapa
            fig3.colorbar(frame='af+l"mGal"', position="JMR+o0.8c/0c+w4c")

fig3.show()
#fig3.show('method external'), para que aparezca en pdf

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
nombre_archivo = "Resultados_Gravimetria_Tenerife.csv"
df_final.to_csv(nombre_archivo, index=False, sep=',', encoding='utf-8')

print("--- Exportación completada ---")
print("Los resultados se han guardado en: Tabla de Tenerife con igpp")