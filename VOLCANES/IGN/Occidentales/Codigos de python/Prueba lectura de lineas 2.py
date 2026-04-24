# -*- coding: utf-8 -*-
"""
Created on Wed Apr 22 08:55:28 2026

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
carpeta_pdfs = r"C:\Users\Usuario\Desktop\IGN\Lineas de Canarias\El Hierro" 
datos_linea = []

# ==========================================
# 2. DEFINIR QUÉ BUSCAMOS (Nuevos Patrones)
# ==========================================
# Ahora buscamos también el Número del punto directamente en el texto
patron_id   = re.compile(r"Número:\s*([A-Za-z0-9_]+)")
patron_lat  = re.compile(r"Latitud:\s*(.+)")
patron_lon  = re.compile(r"Longitud:\s*(.+)")
patron_alt  = re.compile(r"Altitud ortométrica:\s*([\d\.\,]+)") 

# Nuevos patrones solicitados:
patron_elip = re.compile(r"Altitud elipsoidal:\s*([\d\.\,]+)")
# Ignoramos el símbolo ± y sacamos solo el número
patron_prec = re.compile(r"Precisión:\s*[±\s]*([\d\.\,]+)")

# Para la gravedad, capturamos el número (Grupo 1) y TODO lo que sigue después (Grupo 2)
patron_grav = re.compile(r"Gravedad en superficie:\s*([\d\.\,]+)(.*)")

# ==========================================
# 3. LECTURA EN BUCLE (Página por página)
# ==========================================
archivos = glob.glob(os.path.join(carpeta_pdfs, "**", "*.pdf"), recursive=True)

print(f"Se han encontrado {len(archivos)} PDFs. Iniciando extracción...")

if len(archivos) == 0:
    print("No se encontraron PDFs. Revisa la ruta.")
else:
    for archivo in archivos:
        # Usamos el nombre del archivo PDF como nombre de la línea
        nombre_archivo = os.path.basename(archivo).replace('.pdf', '')
        
        try:
            with pdfplumber.open(archivo) as pdf:
                # ¡NUEVO!: En lugar de leer solo la [0], iteramos por TODAS las páginas del PDF
                for num_pagina, pagina in enumerate(pdf.pages):
                    texto = pagina.extract_text()
                    
                    if not texto:
                        continue # Si la página está vacía, saltamos a la siguiente
                    
                    # 1. Buscar el ID del punto. Si la página no tiene ID, no es una ficha válida.
                    match_id = patron_id.search(texto)
                    if not match_id:
                        continue
                        
                    id_punto = match_id.group(1).strip()
                    
                    # 2. Extraer datos básicos
                    lat = patron_lat.search(texto).group(1).strip() if patron_lat.search(texto) else None
                    lon = patron_lon.search(texto).group(1).strip() if patron_lon.search(texto) else None
                    alt = patron_alt.search(texto).group(1).strip() if patron_alt.search(texto) else None
                    
                    # 3. Extraer nuevos datos (Elipsoidal y Precisión)
                    elip = patron_elip.search(texto).group(1).strip() if patron_elip.search(texto) else None
                    prec = patron_prec.search(texto).group(1).strip() if patron_prec.search(texto) else None
                    
                    # 4. Lógica Inteligente para la Gravedad
                    grav_valor = None
                    tipo_grav = "No disponible"
                    
                    match_grav = patron_grav.search(texto)
                    if match_grav:
                        numero = match_grav.group(1).strip()
                        texto_posterior = match_grav.group(2).upper() # Lo pasamos a mayúsculas para buscar fácilmente
                        
                        if "CALCULADA" in texto_posterior:
                            grav_valor = None # Descartamos el valor
                            tipo_grav = "Calculada (Descartada)"
                        else:
                            grav_valor = numero
                            tipo_grav = "Observada"
                    
                    # Guardamos los datos de esta página
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
    # 4. GUARDAR Y LIMPIAR RESULTADOS
    # ==========================================
    if len(datos_linea) > 0:
        df = pd.DataFrame(datos_linea)

        # Limpiamos todos los campos numéricos (cambiamos comas por puntos)
        columnas_numericas = ['Alt_Ortometrica', 'Alt_Elipsoidal', 'Precision_m', 'Gravedad_mGal']
        for col in columnas_numericas:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
                # Opcional: Convertir los 'None' (que al pasarlos a texto se vuelven 'None') en valores vacíos reales
                df[col] = df[col].replace('None', '')

        ruta_salida = os.path.join(carpeta_pdfs, "Datos_IGN_Completos_Filtrados.csv")
        df.to_csv(ruta_salida, index=False, encoding='utf-8')

        print(f"\n¡Éxito! Se han extraído {len(df)} puntos.")
        print(f"Archivo guardado en: {ruta_salida}")
        print("\nMuestra de los datos extraídos:")
        # Mostramos unas columnas específicas para ver cómo funcionó el filtro
        print(df[['ID_Punto', 'Alt_Elipsoidal', 'Precision_m', 'Gravedad_mGal', 'Tipo_Gravedad']].head())
    else:
        print("\nNo se pudo extraer ningún dato válido de los PDFs.") 
        
        
        
        
        
        
        

        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        