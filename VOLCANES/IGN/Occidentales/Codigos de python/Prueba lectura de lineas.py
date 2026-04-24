# -*- coding: utf-8 -*-
"""
Created on Tue Apr 21 17:08:29 2026

@author: Usuario
"""
import os
import glob
import pdfplumber
import pandas as pd
import re

# ==========================================
# 1. CONFIGURACIÓN DE LA RUTA PRINCIPAL
# ==========================================
# Ruta a la carpeta principal de Tenerife. 
# El programa buscará dentro de todas las subcarpetas ("linea 947", etc.)
carpeta_pdfs = r"C:\Users\Usuario\Desktop\IGN\Lineas de Canarias\Tenerife" 

datos_linea = []

# ==========================================
# 2. DEFINIR QUÉ BUSCAMOS EXACTAMENTE
# ==========================================
# Ajustado al formato exacto del IGN que vimos en el modo "Rayos X"
patron_lat = re.compile(r"Latitud:\s*(.+)")
patron_lon = re.compile(r"Longitud:\s*(.+)")
patron_alt  = re.compile(r"Altitud ortométrica:\s*([\d\.\,]+)") 
patron_grav = re.compile(r"Gravedad en superficie:\s*([\d\.\,]+)")

# ==========================================
# 3. LECTURA EN BUCLE (Buceando en subcarpetas)
# ==========================================
# El "**" y "recursive=True" hacen la magia de entrar en todas las carpetas
archivos = glob.glob(os.path.join(carpeta_pdfs, "**", "*.pdf"), recursive=True)

print(f"Se han encontrado {len(archivos)} PDFs en total. Iniciando extracción masiva...")

if len(archivos) == 0:
    print("No se encontraron PDFs. Revisa que la ruta principal sea correcta.")
else:
    for archivo in archivos:
        # Extraer el nombre del punto y de qué línea es
        nombre_punto = os.path.basename(archivo).replace('.pdf', '')
        carpeta_origen = os.path.basename(os.path.dirname(archivo))
        
        try:
            with pdfplumber.open(archivo) as pdf:
                texto = pdf.pages[0].extract_text()
                
                if not texto:
                    print(f"Aviso: El PDF {nombre_punto} parece estar vacío o ser una imagen.")
                    continue
                    
                # Extraemos los datos
                lat = patron_lat.search(texto).group(1).strip() if patron_lat.search(texto) else None
                lon = patron_lon.search(texto).group(1).strip() if patron_lon.search(texto) else None
                alt = patron_alt.search(texto).group(1).strip() if patron_alt.search(texto) else None
                grav = patron_grav.search(texto).group(1).strip() if patron_grav.search(texto) else None
                
                datos_linea.append({
                    "Linea": carpeta_origen, # Guardamos a qué carpeta/línea pertenece
                    "ID_Punto": nombre_punto,
                    "Latitud": lat,
                    "Longitud": lon,
                    "Altitud": alt,
                    "Gravedad_Obs": grav
                })
                
        except Exception as e:
            print(f"Error procesando el archivo {nombre_punto}: {e}")

    # ==========================================
    # 4. GUARDAR Y LIMPIAR RESULTADOS
    # ==========================================
    if len(datos_linea) > 0:
        df = pd.DataFrame(datos_linea)

        # Limpieza de datos numéricos (cambiar comas por puntos)
        if 'Gravedad_Obs' in df.columns:
            df['Gravedad_Obs'] = df['Gravedad_Obs'].astype(str).str.replace(',', '.', regex=False)
        if 'Altitud' in df.columns:
            df['Altitud'] = df['Altitud'].astype(str).str.replace(',', '.', regex=False)

        # Crear el CSV en la carpeta principal de Tenerife
        ruta_salida = os.path.join(carpeta_pdfs, "Datos_Completos_Tenerife.csv")
        df.to_csv(ruta_salida, index=False, encoding='utf-8')

        print(f"\n¡Éxito! Se han procesado y guardado los datos de {len(df)} puntos.")
        print(f"El archivo está guardado en: {ruta_salida}")
        print("\nPrimeras filas extraídas:")
        print(df.head())
    else:
        print("\nNo se pudo extraer ningún dato válido de los PDFs.")