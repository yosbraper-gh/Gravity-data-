# -*- coding: utf-8 -*-
"""
Created on Thu Apr 16 09:16:15 2026

@author: Usuario
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import harmonica as hm
import verde as vd
from pyproj import Transformer

# ============================================================
# 1. CARGAR DATOS
# ============================================================
df = pd.read_csv("Datos_El_Hierro_Anomalia_Bouguer_limpio.csv")

# Adapta estos nombres a los de tus columnas reales
lon = df["X"].values
lat = df["Y"].values
anomalia = df["Bouguer_mG"].values  # o mGal, según tus datos

print(f"Puntos cargados: {len(df)}")
print(f"Anomalía min: {anomalia.min():.1f}, max: {anomalia.max():.1f}")

# ============================================================
# 2. PROYECTAR A COORDENADAS MÉTRICAS (necesario para el gridding)
# ============================================================
# Harmonica trabaja mejor en metros que en grados
transformer = Transformer.from_crs("EPSG:4326", "EPSG:32628", always_xy=True)
# EPSG:32628 = UTM zona 28N, que corresponde a Canarias

x, y = transformer.transform(lon, lat)

# ============================================================
# 3. INTERPOLACIÓN CON VERDE (gridding)
# ============================================================
# Verde es la librería compañera de Harmonica para interpolar
# ScipyGridder es el más sencillo y robusto para empezar
# Luego puedes probar vd.Spline() para resultados más suaves

coordenadas = (x, y)

gridder = vd.ScipyGridder(method="cubic")
gridder.fit(coordenadas, anomalia)

# Definir la región y resolución de la rejilla de salida
region_utm = (x.min(), x.max(), y.min(), y.max())
espaciado = 500  # metros entre puntos de la rejilla (ajusta según densidad de tus datos)

grid_coords = vd.grid_coordinates(region_utm, spacing=espaciado)
anomalia_grid = gridder.predict(grid_coords)

# Convertir rejilla de vuelta a lat/lon para el plot
transformer_inv = Transformer.from_crs("EPSG:32628", "EPSG:4326", always_xy=True)
lon_grid, lat_grid = transformer_inv.transform(grid_coords[0], grid_coords[1])

# ============================================================
# 4. CALCULAR GRADIENTE (opcional, para las isolíneas automáticas)
# ============================================================
# Harmonica puede calcular derivadas del campo gravitatorio
# Por ahora lo dejamos para un paso posterior si te interesa

# ============================================================
# 5. VISUALIZACIÓN — replicando el estilo del mapa original
# ============================================================
fig, ax = plt.subplots(figsize=(10, 9))

# Mapa de color (usa la misma paleta que el mapa original: rainbow/jet)
nivel_min = anomalia.min()
nivel_max = anomalia.max()
niveles_fill = np.linspace(nivel_min, nivel_max, 60)
niveles_lineas = np.linspace(nivel_min, nivel_max, 20)  # isolíneas cada ~2250 µGal aprox

cf = ax.contourf(
    lon_grid, lat_grid, anomalia_grid,
    levels=niveles_fill,
    cmap="jet",           # igual que el mapa original
    extend="both"
)

# Isolíneas encima
cs = ax.contour(
    lon_grid, lat_grid, anomalia_grid,
    levels=niveles_lineas,
    colors="black",
    linewidths=0.6,
    alpha=0.7
)

# Etiquetas en las isolíneas
ax.clabel(cs, fmt="%.0f", fontsize=7, inline=True)

# Barra de color
cbar = fig.colorbar(cf, ax=ax, pad=0.02, fraction=0.03)
cbar.set_label("Complete Bouguer Anomaly (µGal)", fontsize=11)

# Puntos originales (opcional, para ver la cobertura de datos)
ax.scatter(lon, lat, s=2, c="white", alpha=0.3, label="Datos originales")

# Formato ejes
ax.set_xlabel("Longitud (°)", fontsize=11)
ax.set_ylabel("Latitud (°)", fontsize=11)
ax.set_title("Complete Bouguer Anomaly Map\nL El Hierro (mGal)", fontsize=13, fontweight="bold")
ax.xaxis.set_major_formatter(mticker.FormatStrFormatter("%.2f°"))
ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.2f°"))
ax.grid(True, linestyle="--", alpha=0.4, color="mediumpurple")

plt.tight_layout()
plt.savefig("mapa_bouguer_El_Hierro.png", dpi=200, bbox_inches="tight")
plt.show()
print("Mapa guardado.")








