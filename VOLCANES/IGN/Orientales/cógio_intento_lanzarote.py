# -*- coding: utf-8 -*-
"""
Created on Wed Apr 22 10:44:37 2026

@author: Usuario
"""

import os
import glob
import pdfplumber
import pandas as pd
import re

# 1. CONFIGURACIÓN
carpeta_pdfs = r"C:\UNIVERSIDAD\PRÁCTICAS EXTERNAS\proyecto_IGN\pdfs_ign_lanzarote"
datos_linea = []

# 2. REGEX ACTUALIZADAS (Incluyendo Altitud Elipsoidal y Precisión)
patron_lat = re.compile(r"Latitud:\s*(.*)")
patron_lon = re.compile(r"Longitud:\s*(.*)")
patron_alt_orto = re.compile(r"Altitud\s+ortométrica:\s*([\d\.,]+)")
patron_grav = re.compile(r"Gravedad\s+en\s+superficie:\s*([\d\.,]+)")

# Nuevos patrones
patron_alt_elip = re.compile(r"Altitud\s+elipsoidal:\s*([\d\.,]+)")
# Captura el número después de ± o +- 
patron_precision = re.compile(r"Precisión:\s*(?:±|\+\-)?\s*([\d\.,]+)")

# 3. PROCESAMIENTO
archivos = glob.glob(os.path.join(carpeta_pdfs, "**", "*.pdf"), recursive=True)
print(f"Iniciando extracción de {len(archivos)} archivos...")

for archivo in archivos:
    nombre_punto = os.path.basename(archivo).replace('.pdf', '')
    carpeta_origen = os.path.basename(os.path.dirname(archivo))
    
    try:
        with pdfplumber.open(archivo) as pdf:
            texto = ""
            for page in pdf.pages:
                texto += page.extract_text() + "\n"
            
            if not texto.strip():
                continue

            # Extracción de valores
            lat_m = patron_lat.search(texto)
            lon_m = patron_lon.search(texto)
            alt_o_m = patron_alt_orto.search(texto)
            grav_m = patron_grav.search(texto)
            alt_e_m = patron_alt_elip.search(texto)
            prec_m = patron_precision.search(texto)

            # Función auxiliar para limpiar números (coma a punto)
            def limpiar_num(match):
                return match.group(1).replace(',', '.') if match else None

            datos_linea.append({
                "Linea": carpeta_origen,
                "ID_Punto": nombre_punto,
                "Latitud": lat_m.group(1).strip() if lat_m else None,
                "Longitud": lon_m.group(1).strip() if lon_m else None,
                "Altitud_Ortometrica": limpiar_num(alt_o_m),
                "Altitud_Elipsoidal": limpiar_num(alt_e_m),
                "Precision": limpiar_num(prec_m),
                "Gravedad_Obs": limpiar_num(grav_m)
            })
            
    except Exception as e:
        print(f"[ERROR] En {nombre_punto}: {e}")

# 4. GUARDADO
if datos_linea:
    df = pd.DataFrame(datos_linea)
    
    # Convertir columnas numéricas para asegurar calidad de datos
    cols_numericas = ["Altitud_Ortometrica", "Altitud_Elipsoidal", "Precision", "Gravedad_Obs"]
    for col in cols_numericas:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    ruta_salida = os.path.join(carpeta_pdfs, "Datos_IGN_Completos.csv")
    df.to_csv(ruta_salida, index=False, encoding='utf-8-sig')
    
    print(f"\n¡Listo! Se han extraído {len(df)} registros.")
    print(f"Columnas generadas: {list(df.columns)}")
else:
    print("No se encontraron datos.")