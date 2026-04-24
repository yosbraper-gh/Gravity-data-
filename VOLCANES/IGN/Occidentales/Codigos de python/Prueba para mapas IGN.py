# -*- coding: utf-8 -*-
"""
Created on Thu Apr 23 10:26:21 2026

@author: Usuario
"""

import pandas as pd
import numpy as np
import pygmt
import re

# ==========================================
# 1. CARGA DE DATOS Y LIMPIEZA
# ==========================================
ruta_csv = r"C:\Users\Usuario\Desktop\IGN\Lineas de Canarias\Tenerife\Tenerife_Datos_Final_Color.csv"
df = pd.read_csv(ruta_csv)

# Función para pasar de Grados Minutos Segundos a Decimal
def gms_a_decimal(gms_str):
    try:
        partes = re.findall(r"[-+]?\d*\.\d+|\d+", str(gms_str))
        if len(partes) >= 3:
            d = float(partes[0])
            m = float(partes[1])
            s = float(partes[2].replace(',', '.'))
            return d + (m/60) + (s/3600)
    except:
        return np.nan

# Aplicamos la conversión
df['lat_deg'] = df['Latitud'].apply(gms_a_decimal)
df['lon_deg'] = df['Longitud'].apply(gms_a_decimal)
df['lon_deg'] = df['lon_deg'].apply(lambda x: -abs(x) if x > 0 else x) # Forzar Oeste (-)

# ==========================================
# 2. CÁLCULOS GEOFÍSICOS
# ==========================================
DENSIDAD_BOUGUER = 2670  # kg/m3
ge = 978032.53359        # Constante Gravedad WGS84 Ecuatorial
k = 0.00193185265241
e2 = 0.00669437999013

def calcular_anomalias(row):
    lat = np.radians(row['lat_deg'])
    h = row['Alt_Ortometrica']
    g_obs = row['Gravedad_mGal']
    
    if np.isnan(lat) or np.isnan(h) or np.isnan(g_obs):
        return pd.Series([np.nan, np.nan])

    # Gravedad Normal (Somigliana)
    gamma = ge * (1 + k * np.sin(lat)**2) / np.sqrt(1 - e2 * np.sin(lat)**2)
    
    # Anomalía de Aire Libre (FAA)
    faa = g_obs - gamma + (0.3086 * h)
    
    # Anomalía de Bouguer Simple (BA)
    ba = faa - (0.04193 * DENSIDAD_BOUGUER * h / 1000)
    
    return pd.Series([faa, ba])

df[['FAA', 'BA']] = df.apply(calcular_anomalias, axis=1)

# Limpiamos filas vacías para evitar errores al dibujar
df_limpio = df.dropna(subset=['lat_deg', 'lon_deg', 'FAA', 'BA'])

# ==========================================
# 3. REPRESENTACIÓN EN MAPA CON PYGMT
# ==========================================
# Coordenadas límite para Tenerife (Oeste, Este, Sur, Norte)
region_tenerife = [-17.0, -16.1, 27.9, 28.65]

def crear_mapa_pygmt(datos, columna, titulo, archivo_salida):
    # Inicializamos la figura
    fig = pygmt.Figure()
    
    # Creamos el mapa base. 
    # projection="M15c" significa Mercator de 15 centímetros de ancho
    # shorelines="1p,black" dibuja la costa con grosor 1
    # land="lightgray" pinta la tierra de gris claro
    fig.basemap(region=region_tenerife, projection="M15c", frame=["a", f'+t"{titulo}"'])
    fig.coast(shorelines="1p,black", water="azure1", land="gainsboro")
    
    # Creamos una paleta de colores científica (CPT) adaptada a nuestros datos
    # Usamos la paleta "jet" (clásica en geofísica) o "polar" (para anomalías + y -)
    vmin = datos[columna].min()
    vmax = datos[columna].max()
    pygmt.makecpt(cmap="jet", series=[vmin, vmax])
    
    # Dibujamos los puntos
    # style="c0.25c" significa "círculos de 0.25 cm"
    # pen="0.5p,black" le pone un borde negro a cada puntito
    fig.plot(
        x=datos['lon_deg'], 
        y=datos['lat_deg'], 
        color=datos[columna], 
        cmap=True, 
        style="c0.25c", 
        pen="0.5p,black"
    )
    
    # Añadimos la barra de leyenda (Colorbar)
    fig.colorbar(frame='af+l"mGal"')
    
    # Mostramos la figura en pantalla
    fig.show()
    
    # OPCIONAL: Guardar el mapa en alta calidad (PDF o PNG)
    # fig.savefig(archivo_salida)

# Generar ambos mapas
print("Generando mapa de Aire Libre...")
crear_mapa_pygmt(df_limpio, 'FAA', 'Anomalia de Aire Libre - Tenerife', 'Mapa_AireLibre.png')

print("Generando mapa de Bouguer...")
crear_mapa_pygmt(df_limpio, 'BA', 'Anomalia de Bouguer Simple - Tenerife', 'Mapa_Bouguer.png')