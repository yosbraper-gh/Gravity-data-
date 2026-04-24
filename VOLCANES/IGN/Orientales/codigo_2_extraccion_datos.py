# -*- coding: utf-8 -*-
"""
Created on Wed Apr 22 11:05:21 2026

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
carpeta_pdfs = r"C:\UNIVERSIDAD\PRÁCTICAS EXTERNAS\proyecto_IGN\Gran Canaria"
datos_linea = []

# Palabra que aparecerá en el Excel si no se encuentra el dato
VALOR_VACIO = "DATO NO DETECTADO"

# ==========================================
# 2. DEFINIR QUÉ BUSCAMOS
# ==========================================
patron_id   = re.compile(r"Número:\s*([A-Za-z0-9_]+)")
patron_lat  = re.compile(r"Latitud:\s*(.+)")
patron_lon  = re.compile(r"Longitud:\s*(.+)")
patron_alt  = re.compile(r"Altitud ortométrica:\s*([\d\.\,]+)")
patron_elip = re.compile(r"Altitud elipsoidal:\s*([\d\.\,]+)")
patron_prec = re.compile(r"Precisión:\s*[±\s]*([\d\.\,]+)")
patron_grav = re.compile(r"Gravedad en superficie:\s*([\d\.\,]+)(.*)")

# ==========================================
# 3. LECTURA EN BUCLE
# ==========================================
archivos = glob.glob(os.path.join(carpeta_pdfs, "**", "*.pdf"), recursive=True)

print(f"Se han encontrado {len(archivos)} PDFs. Iniciando extracción...")

if len(archivos) == 0:
    print("No se encontraron PDFs. Revisa la ruta.")
else:
    for archivo in archivos:
        nombre_archivo = os.path.basename(archivo).replace('.pdf', '')
        
        try:
            with pdfplumber.open(archivo) as pdf:
                for num_pagina, pagina in enumerate(pdf.pages):
                    texto = pagina.extract_text()
                    
                    if not texto:
                        continue 
                    
                    match_id = patron_id.search(texto)
                    if not match_id:
                        continue
                        
                    id_punto = match_id.group(1).strip()
                    
                    # --- EXTRACCIÓN CON CONTROL DE VALORES VACÍOS ---
                    # Si search() devuelve None, asignamos VALOR_VACIO
                    lat = patron_lat.search(texto).group(1).strip() if patron_lat.search(texto) else VALOR_VACIO
                    lon = patron_lon.search(texto).group(1).strip() if patron_lon.search(texto) else VALOR_VACIO
                    alt = patron_alt.search(texto).group(1).strip() if patron_alt.search(texto) else VALOR_VACIO
                    elip = patron_elip.search(texto).group(1).strip() if patron_elip.search(texto) else VALOR_VACIO
                    prec = patron_prec.search(texto).group(1).strip() if patron_prec.search(texto) else VALOR_VACIO
                    
                    # Lógica para Gravedad
                    grav_valor = VALOR_VACIO
                    tipo_grav = "No disponible"
                    
                    match_grav = patron_grav.search(texto)
                    if match_grav:
                        numero = match_grav.group(1).strip()
                        texto_posterior = match_grav.group(2).upper()
                        
                        if "CALCULADA" in texto_posterior:
                            grav_valor = "DESCARTADA (CALCULADA)"
                            tipo_grav = "Calculada"
                        else:
                            grav_valor = numero
                            tipo_grav = "Observada"

                    datos_linea.append({
                        "Archivo_Origen": nombre_archivo,
                        "Pagina_PDF": num_pagina + 1,
                        "ID_Punto": id_punto,
                        "Latitud": lat,
                        "Longitud": lon,
                        "Alt_Ortometrica": alt,
                        "Alt_Elipsoidal": elip,
                        "Precision_m": prec,
                        "Gravedad_mGal": grav_valor,
                        "Tipo_Gravedad": tipo_grav
                    })
                    
        except Exception as e:
            print(f"Error procesando el archivo {nombre_archivo}: {e}")

    # ==========================================
    # 4. GUARDAR Y LIMPIAR
    # ==========================================
    if len(datos_linea) > 0:
        df = pd.DataFrame(datos_linea)

        # Limpieza de comas, pero SOLO si el valor no es nuestra palabra de error
        columnas_numericas = ['Alt_Ortometrica', 'Alt_Elipsoidal', 'Precision_m', 'Gravedad_mGal']
        for col in columnas_numericas:
            if col in df.columns:
                # Solo reemplazamos comas en las filas que NO contienen el mensaje de error
                mask = df[col] != VALOR_VACIO
                df.loc[mask, col] = df.loc[mask, col].astype(str).str.replace(',', '.', regex=False)

        ruta_salida = os.path.join(carpeta_pdfs, "Datos_IGN_Completos_Filtrados_Gran Canaria.csv")
        # Usamos utf-8-sig para que Excel no rompa los símbolos de grados o acentos
        df.to_csv(ruta_salida, index=False, encoding='utf-8-sig')

        print(f"\n¡Éxito! Se han guardado {len(df)} registros.")
        print(f"Archivo: {ruta_salida}")
    else:
        print("\nNo se pudo extraer ningún dato válido.")