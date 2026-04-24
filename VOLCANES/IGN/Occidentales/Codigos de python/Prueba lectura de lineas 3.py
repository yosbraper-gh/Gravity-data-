# -*- coding: utf-8 -*-
"""
Created on Wed Apr 22 11:15:20 2026

@author: Usuario
"""

import os
import glob
import pdfplumber
import pandas as pd
import re

# ==========================================
# 1. CONFIGURACIÓN
# ==========================================
carpeta_pdfs = r"C:\Users\Usuario\Desktop\IGN\Lineas de Canarias\Tenerife" 
datos_linea = []

# ==========================================
# 2. DEFINIR PATRONES DE BÚSQUEDA (VERSIÓN ROBUSTA)
# ==========================================
patron_id   = re.compile(r"Número:\s*([A-Za-z0-9_]+)")

# Estos nuevos patrones ignoran la basura (.*?) y buscan la estructura exacta:
# [- opcional] [números]° [números]' [números con comas]''
patron_lat  = re.compile(r"Latitud:.*?(-?\s*\d{1,3}°\s*\d{1,2}'\s*[\d,]+(?:''|\"))")
patron_lon  = re.compile(r"Longitud:.*?(-?\s*\d{1,3}°\s*\d{1,2}'\s*[\d,]+(?:''|\"))")

patron_alt  = re.compile(r"Altitud ortométrica:\s*([\d\.\,]+)") 
patron_elip = re.compile(r"Altitud elipsoidal:\s*([\d\.\,]+)")
patron_prec = re.compile(r"Precisión:\s*[±\s]*([\d\.\,]+)")
patron_grav = re.compile(r"Gravedad en superficie:\s*([\d\.\,]+)(.*)") 
# ==========================================
# 3. PROCESAMIENTO
# ==========================================
archivos = glob.glob(os.path.join(carpeta_pdfs, "**", "*.pdf"), recursive=True)
print(f"Se han encontrado {len(archivos)} PDFs. Iniciando extracción...")
for archivo in archivos:
    nombre_archivo = os.path.basename(archivo).replace('.pdf', '')
    
    try:
        with pdfplumber.open(archivo) as pdf:
            for num_pagina, pagina in enumerate(pdf.pages):
                texto_original = pagina.extract_text()
                if not texto_original: continue
                
                # --- LIMPIEZA DE SELLOS ROJOS ---
                # 1. Aplastamos el texto a una sola línea (por si el sello cortó la coordenada)
                texto = texto_original.replace("\n", " ")
                # 2. Borramos las frases del sello directamente de la memoria
                texto = re.sub(r"SEÑAL DESAPARECIDA", "", texto, flags=re.IGNORECASE)
                texto = re.sub(r"\d{4}-\d{2}-\d{2}:?\s*Desaparecido\.?", "", texto, flags=re.IGNORECASE)
                # --------------------------------
                
                # Buscamos el ID. Si no hay ID, no es una ficha.
                match_id = patron_id.search(texto)
                if not match_id: continue
                
                # --- FILTRO DE GRAVEDAD CALCULADA ---
                match_grav = patron_grav.search(texto)
                if match_grav:
                    texto_posterior = match_grav.group(2).upper()
                    if "CALCULADA" in texto_posterior:
                        continue 
                    grav_valor = match_grav.group(1).strip()
                else:
                    grav_valor = None
                
                # --- EXTRACCIÓN Y LIMPIEZA DE LATITUD/LONGITUD ---
                # Usamos .split() para cortar la frase si aparece "NO EXISTE"
                raw_lat = patron_lat.search(texto).group(1) if patron_lat.search(texto) else ""
                lat = raw_lat.split("NO EXISTE")[0].strip()
                
                raw_lon = patron_lon.search(texto).group(1) if patron_lon.search(texto) else ""
                lon = raw_lon.split("NO EXISTE")[0].strip()
                
                # --- ALTITUD ELIPSOIDAL "NO ENCONTRADA" ---
                elip_match = patron_elip.search(texto)
                elip = elip_match.group(1).strip() if elip_match else "no encontrada"
                
                # Resto de datos
                id_punto = match_id.group(1).strip()
                alt = patron_alt.search(texto).group(1).strip() if patron_alt.search(texto) else None
                prec = patron_prec.search(texto).group(1).strip() if patron_prec.search(texto) else None
                
                datos_linea.append({
                    "ID_Punto": id_punto,
                    "Latitud": lat,
                    "Longitud": lon,
                    "Alt_Ortometrica": alt,
                    "Alt_Elipsoidal": elip,
                    "Precision_m": prec,
                    "Gravedad_mGal": grav_valor
                })
                    
    except Exception as e:
        print(f"Error en {nombre_archivo}: {e}")

# ==========================================
# 4. EXPORTACIÓN Y MENSAJES FINALES
# ==========================================
if len(datos_linea) > 0:
    df = pd.DataFrame(datos_linea)
    
    # Limpiamos todos los campos numéricos (cambiamos comas por puntos)
    columnas_numericas = ['Alt_Ortometrica', 'Alt_Elipsoidal', 'Precision_m', 'Gravedad_mGal']
    for col in columnas_numericas:
        if col in df.columns:
            # Reemplazamos comas y también borramos la palabra 'None' si algo estaba vacío
            df[col] = df[col].astype(str).str.replace(',', '.', regex=False).replace('None', '')

    # Guardar el archivo final
    ruta_salida = os.path.join(carpeta_pdfs, "Tenerife_Datos_Limpios.csv")
    df.to_csv(ruta_salida, index=False, encoding='utf-8')

    # --- Los mensajes de éxito detallados ---
    print(f"\n" + "="*40)
    print(f"¡Éxito! Se han extraído y guardado {len(df)} puntos.")
    print(f"Archivo guardado en: {ruta_salida}")
    print(f"="*40)
    
    print("\nMuestra de los datos extraídos (Primeras 5 filas):")
    # Mostramos las columnas clave para verificar que todo quedó perfecto
    print(df[['ID_Punto', 'Latitud', 'Alt_Elipsoidal', 'Precision_m', 'Gravedad_mGal']].head())
    
else:
    print("\nNo se pudo extraer ningún dato válido de los PDFs.")