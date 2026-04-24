# -*- coding: utf-8 -*-
"""
Created on Thu Apr 23 15:18:50 2026

@author: Usuario
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
# Cargar el dataset
df = pd.read_csv('Datos_IGN_Completos_Filtrados_Lanzarote - copia.csv')

# Función para convertir DMS a Grados Decimales:

import pandas as pd
import numpy as np

# Leer TODO como string
df = pd.read_csv('Datos_IGN_Completos_Filtrados_Lanzarote - copia.csv', dtype=str)

# Función vectorizada usando pandas
def dms_to_dd_vector(col):
    # Reemplazar coma decimal por punto
    col = col.str.replace(',', '.', regex=False)
   
    # Extraer grados, minutos, segundos
    d = col.str.extract(r'(\d+)[^\d]+(\d+)[^\d]+(\d+\.?\d*)')
   
    # Convertir a float (ahora sí funciona)
    d = d.astype(float)
   
    dd = d[0] + d[1]/60 + d[2]/3600
   
    # Detectar signo (Oeste o negativo)
    dd[col.str.contains('W|-', na=False)] *= -1
   
    return dd

# Aplicar directamente
df['lat_dd'] = dms_to_dd_vector(df['Latitud'])
df['lon_dd'] = dms_to_dd_vector(df['Longitud'])

# Convertir a arrays
lat = df['lat_dd'].to_numpy()
lon = df['lon_dd'].to_numpy()

# Convertir Gravedad y Altitud a numérico (manejando errores)
df['Gravedad_mGal'] = pd.to_numeric(df['Gravedad_mGal'], errors='coerce')
df['Alt_Ortometrica'] = pd.to_numeric(df['Alt_Ortometrica'], errors='coerce')

# Eliminar filas sin datos esenciales
df = df.dropna(subset=['Gravedad_mGal', 'lat_dd', 'Alt_Ortometrica'])

#### Mis arrays son:
   
lat = df['lat_dd'].values            # Array de latitudes
lon = df['lon_dd'].values
h = df['Alt_Ortometrica'].values  # Array de alturas
g_obs = df['Gravedad_mGal'].values   # Array de medidas reales

print(' ')
print('Mis variables iniciales son: ')
print('Latitud en grados decimales: ', lat)
print('Longitud en grados decimales: ', lon)
print('Altitud ortonométrica en metros: ', h)
print('Gravedad observada: ', g_obs)

lat_rad = np.radians(lat)
#===============================================================================
#                      GRAVEDAD NORMAL
#===============================================================================

#La gravedad normal se define como:

g_e = 978032.67715
b_1 = 5.3024 * 10**(-3)
b_2 = -5.8 *10 **(-6)


g_n = g_e * (1 + b_1 * (np.sin(lat_rad))**2 + b_2 * (np.sin(2*lat_rad))**2)

print(' ')
#print('La gravedad normal es: ', g_n)

"""
plt.plot(lat, g_n, 'b.', label='Puntos de Lanzarote')
plt.title('Variación de la Gravedad Normal frente a la Latitud', fontsize=14)
plt.xlabel('Latitud (Grados Decimales)', fontsize=12)
plt.ylabel('Gravedad Normal (mGal)', fontsize=12)
plt.grid(True, linestyle='--', alpha=0.7)
plt.legend()
plt.tight_layout()
plt.show()
"""  
 

#===============================================================================
#                      CORRECCIÓN AIRE LIBRE
#===============================================================================
 
#La corrección de aire libre trata de justar la diferencia de elevación entre
#el punto de medida y el elipsoide sin considerar la de la roca debajo del punto
#de medida.

d_g_l = - 0.3086*h

print(' ')
print('La corrección de aire libre es: ', d_g_l)



#=============================================================================
#                       ANOMALÍA DE AIRE LIBRE
#==============================================================================


#La anomalía de aire libre se define como:

a_g_l = g_obs - (g_n + d_g_l)

print(' ')
print('La anomalía de aire libre es: ', a_g_l)

print("Lat min:", lat.min())
print("Lat max:", lat.max())
print("Lon min:", lon.min())
print("Lon max:", lon.max())


######################### Representación:

import pygmt
import pandas as pd

# Crear DataFrame para PyGMT:
# DataFrame es unaestructura de datos bidimensional, tabular y etiquetada
data = pd.DataFrame({
    "lon": lon,
    "lat": lat,
    "anom": a_g_l
})


# Crear figura
fig = pygmt.Figure()

# Región con margen para que los puntos del borde no queden cortados:
#☻ pygmt.Figure() crea el lienzo en blanco. La region define la ventana
#geográfica del mapa en formato [lon_min, lon_max, lat_min, lat_max].
# El margen de 0.05° (~5 km) evita que los puntos del borde queden cortados.
margin = 0.05
region = [
    data.lon.min() - margin, data.lon.max() + margin,
    data.lat.min() - margin, data.lat.max() + margin
]

# Mapa base con cuadrícula etiquetada
fig.basemap(
    region=region,
    projection="M15c",       # Más grande: 15c en vez de 10c
    frame=["af", "WSen"]     # Ejes con etiquetas en los 4 lados
)



# --- COSTA DE LANZAROTE ---
fig.coast(
    shorelines="1/0.8p,black",   # Nivel 1 = costa principal, grosor 0.8p, color negro
    land="lightgray",             # Relleno tierra (opcional, quítalo si no quieres)
    water="lightblue",            # Relleno mar (opcional)
    resolution="f"                # f = full, máxima resolución (importante para islas pequeñas)
)


# Paleta ajustada al rango REAL de los datos
vmin = a_g_l.min()
vmax = a_g_l.max()

pygmt.makecpt(cmap="viridis", series=[vmin, vmax])  # salto cada 10 mGal

# Plot puntos — tamaño aumentado a 0.5c y sin borde negro para no tapar el color
fig.plot(
    x=data.lon,
    y=data.lat,
    style="c0.5c",           # Círculos de 0.5 cm (antes 0.2c)
    fill=data.anom,
    cmap=True,               # Usa la CPT activa
)

# Barra de color
fig.colorbar(
    frame='af+l"Anomalía de Aire Libre (mGal)"',
    position="JBC+w10c+h"    # Centrada abajo, horizontal
)

fig.show()