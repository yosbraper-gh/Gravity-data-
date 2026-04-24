# -*- coding: utf-8 -*-
"""
Created on Thu Apr 16 14:02:15 2026

@author: Usuario
"""




import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import harmonica as hm
import verde as vd
from pyproj import Transformer
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.io.shapereader as shpreader
from shapely.geometry import Point, box
from shapely.ops import unary_union

# ============================================================
# 1. CARGAR DATOS
# ============================================================
df = pd.read_csv("Datos_Oahu_Finales.csv")

lon = df["X"].values
lat = df["Y"].values
anomalia = df["Bouguer_mG"].values

print(f"Puntos cargados: {len(df)}")
print(f"Rango anomalía: {anomalia.min():.1f} – {anomalia.max():.1f} mGal")

# ============================================================
# 2. PROYECCIÓN A METROS (UTM zona 28N, Canarias)
# ============================================================
# Convierte lat/lon (grados) a metros para que la interpolación
# trabaje con distancias reales y no con grados
transformer = Transformer.from_crs("EPSG:4326", "EPSG:32628", always_xy=True)
transformer_inv = Transformer.from_crs("EPSG:32628", "EPSG:4326", always_xy=True)

x, y = transformer.transform(lon, lat)
altura = np.zeros_like(x)  # asumimos nivel del mar si no tienes altitudes

# ============================================================
# 3. EQUIVALENT SOURCES (Harmonica)
# ============================================================
# Simula fuentes de gravedad ficticias a 'depth' metros bajo
# la superficie que reproducen tus observaciones.
# depth: más alto = más suave, menos detalle
# damping: más alto = más suavizado, más estable
eqs = hm.EquivalentSources(depth=4000, damping=5)
eqs.fit((x, y, altura), anomalia)
print("Fuentes equivalentes ajustadas.")

# ============================================================
# 4. REJILLA REGULAR Y PREDICCIÓN
# ============================================================
# Verde genera una cuadrícula regular de puntos en metros
# spacing: distancia entre puntos de la rejilla en metros
region_utm = (x.min(), x.max(), y.min(), y.max())
espaciado = 500

grid_x, grid_y = vd.grid_coordinates(region_utm, spacing=espaciado)
grid_z = np.zeros_like(grid_x)

# Harmonica predice el valor de anomalía en cada punto de la rejilla
anomalia_grid = eqs.predict((grid_x, grid_y, grid_z))

# Convierte la rejilla de vuelta a lat/lon para el gráfico
lon_grid, lat_grid = transformer_inv.transform(grid_x, grid_y)

# ============================================================
# 5. MÁSCARA CON LA COSTA REAL
# ============================================================
# Descarga el shapefile mundial de tierra (se cachea localmente)
shpfilename = shpreader.natural_earth(
    resolution="10m", category="physical", name="land"
)
reader = shpreader.Reader(shpfilename)
tierras = list(reader.geometries())

# Une todos los polígonos del mundo en una sola geometría
tierra_union = unary_union(tierras)

# Recorta al bbox de El Hierro para acelerar la consulta
bbox = box(-158.35, -157.60, 21.20, 21.75)
tierra_hierro = tierra_union.intersection(bbox)

# Para cada punto de la rejilla comprueba si está en tierra
lon_flat = lon_grid.ravel()
lat_flat = lat_grid.ravel()

print("Calculando máscara costera... (puede tardar 1-2 minutos)")
dentro = np.array([
    tierra_hierro.contains(Point(lo, la))
    for lo, la in zip(lon_flat, lat_flat)
])
dentro = dentro.reshape(lon_grid.shape)

# Aplica la máscara: NaN fuera de la isla, valor real dentro
anomalia_grid_masked = np.where(dentro, anomalia_grid, np.nan)
print("Máscara aplicada.")

# ============================================================
# 6. VISUALIZACIÓN CON CARTOPY
# ============================================================
fig = plt.figure(figsize=(10, 9))
ax = fig.add_subplot(111, projection=ccrs.PlateCarree())

# Limita la vista a El Hierro con margen
ax.set_extent([-158.35, -157.60, 21.20, 21.75], crs=ccrs.PlateCarree())

nivel_min = np.percentile(anomalia, 2)
nivel_max = np.percentile(anomalia, 98)
niveles_fill = np.linspace(nivel_min, nivel_max, 60)
niveles_lineas = np.linspace(nivel_min, nivel_max, 20)

# Relleno de colores entre isolíneas
cf = ax.contourf(
    lon_grid, lat_grid, anomalia_grid_masked,
    levels=niveles_fill,
    cmap="jet",
    extend="both",
    transform=ccrs.PlateCarree()
)

# Isolíneas negras encima
cs = ax.contour(
    lon_grid, lat_grid, anomalia_grid_masked,
    levels=niveles_lineas,
    colors="black",
    linewidths=0.6,
    alpha=0.7,
    transform=ccrs.PlateCarree()
)
ax.clabel(cs, fmt="%.1f", fontsize=7, inline=True)

# Tierra de fondo en gris (para ver la silueta fuera del mapa)
tierra_feature = cfeature.NaturalEarthFeature(
    "physical", "land", "10m",
    edgecolor="none",
    facecolor="lightgray",
    zorder=0  # queda por debajo del mapa de colores
)
ax.add_feature(tierra_feature, zorder=0)

# Línea de costa encima de todo
costa = cfeature.NaturalEarthFeature(
    "physical", "coastline", "10m",
    edgecolor="black",
    facecolor="none",
    linewidth=1.2
)
ax.add_feature(costa, zorder=3)

# Puntos de datos originales (pequeños, semitransparentes)
ax.scatter(
    lon, lat, s=1, c="white", alpha=0.2,
    transform=ccrs.PlateCarree(), zorder=2
)

# Barra de color
cbar = fig.colorbar(cf, ax=ax, pad=0.05, fraction=0.03)
cbar.set_label("Complete Bouguer Anomaly (mGal)", fontsize=11)

# Cuadrícula con etiquetas de coordenadas
gl = ax.gridlines(draw_labels=True, linestyle="--", alpha=0.4, color="mediumpurple")
gl.top_labels = False
gl.right_labels = False

ax.set_title(
    "Complete Bouguer Anomaly Map\nEl Hierro (mGal) — Harmonica Equivalent Sources",
    fontsize=12, fontweight="bold"
)

plt.tight_layout()
plt.savefig("mapa_bouguer_elhierro_final.png", dpi=200, bbox_inches="tight")
plt.show()
