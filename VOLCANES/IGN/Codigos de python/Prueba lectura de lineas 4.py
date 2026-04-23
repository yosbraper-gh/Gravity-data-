# -*- coding: utf-8 -*-
"""
Created on Thu Apr 23 09:10:02 2026

@author: Usuario
"""

import os
import glob
import pdfplumber
import pandas as pd
import re

# ==========================================
# 1. CONFIGURACIÓN DE LA RUTA
# ==========================================
carpeta_pdfs = r"C:\Users\Usuario\Desktop\IGN\Lineas de Canarias\Tenerife" 
datos_linea = []

# ==========================================
# 2. EL FILTRO DE COLOR (Las Gafas Mágicas)
# ==========================================
def ignorar_color_rojo(obj):
    if obj.get("object_type") != "char":
        return True
    color = obj.get("non_stroking_color")
    if not color: return True 
    
    # Filtro RGB (Rojo)
    if len(color) == 3:
        r, g, b = color
        if r > max(g, b) + 0.3: return False 
    # Filtro CMYK (Rojo)
    elif len(color) == 4:
        c, m, y, k = color
        if m > 0.5 and y > 0.5 and c < 0.3: return False 
    return True

# ==========================================
# 3. PATRONES DE BÚSQUEDA
# ==========================================
patron_id   = re.compile(r"Número:\s*([A-Za-z0-9_]+)")
patron_lat  = re.compile(r"Latitud:.*?(-?\s*\d{1,3}°\s*\d{1,2}'\s*[\d,]+(?:''|\"))")
patron_lon  = re.compile(r"Longitud:.*?(-?\s*\d{1,3}°\s*\d{1,2}'\s*[\d,]+(?:''|\"))")
patron_alt  = re.compile(r"Altitud ortométrica:\s*([\d\.\,]+)") 
patron_elip = re.compile(r"Altitud elipsoidal:\s*([\d\.\,]+)")
patron_prec = re.compile(r"Precisión:\s*[±\s]*([\d\.\,]+)")
patron_grav = re.compile(r"Gravedad en superficie:\s*([\d\.\,]+)(.*)")

# ==========================================
# 4. BUCLE MASIVO (ISLA COMPLETA)
# ==========================================
archivos = glob.glob(os.path.join(carpeta_pdfs, "**", "*.pdf"), recursive=True)
print(f"Detectados {len(archivos)} archivos en Tenerife. Iniciando proceso...")

for archivo in archivos:
    linea_nombre = os.path.basename(os.path.dirname(archivo))
    
    try:
        with pdfplumber.open(archivo) as pdf:
            for num_pag, pagina in enumerate(pdf.pages):
                # APLICAMOS EL FILTRO EN CADA PÁGINA
                pag_limpia = pagina.filter(ignorar_color_rojo)
                texto = pag_limpia.extract_text()
                
                if not texto: continue
                
                # Extracción de ID
                m_id = patron_id.search(texto)
                if not m_id: continue
                id_p = m_id.group(1).strip()
                
                # Filtro Gravedad Calculada
                m_grav = patron_grav.search(texto)
                if m_grav and "CALCULADA" in m_grav.group(2).upper():
                    continue # Saltamos este punto si la gravedad es calculada
                
                # Coordenadas y limpieza
                raw_lat = patron_lat.search(texto).group(1) if patron_lat.search(texto) else ""
                lat = raw_lat.split("NO EXISTE")[0].strip() if raw_lat else "no encontrada"
                
                raw_lon = patron_lon.search(texto).group(1) if patron_lon.search(texto) else ""
                lon = raw_lon.split("NO EXISTE")[0].strip() if raw_lon else "no encontrada"
                
                # Resto de datos
                elip = patron_elip.search(texto).group(1).strip() if patron_elip.search(texto) else "no encontrada"
                alt = patron_alt.search(texto).group(1).strip() if patron_alt.search(texto) else "no encontrada"
                prec = patron_prec.search(texto).group(1).strip() if patron_prec.search(texto) else "no encontrada"
                grav = m_grav.group(1).strip() if m_grav else "no encontrada"
                
                datos_linea.append({
                    "Linea": linea_nombre,
                    "ID_Punto": id_p,
                    "Latitud": lat,
                    "Longitud": lon,
                    "Alt_Ortometrica": alt,
                    "Alt_Elipsoidal": elip,
                    "Precision_m": prec,
                    "Gravedad_mGal": grav
                })
    except Exception as e:
        print(f"Error en archivo {archivo}: {e}")

# ==========================================
# 5. GUARDADO FINAL
# ==========================================
if datos_linea:
    df = pd.DataFrame(datos_linea)
    cols_num = ['Alt_Ortometrica', 'Alt_Elipsoidal', 'Precision_m', 'Gravedad_mGal']
    for c in cols_num:
        df[c] = df[c].astype(str).str.replace(',', '.', regex=False).replace('None', '')
    
    ruta_out = os.path.join(carpeta_pdfs, "Tenerife_Base_Datos_Limpia.csv")
    df.to_csv(ruta_out, index=False, encoding='utf-8')
    print(f"\n¡LISTO! Se han procesado {len(df)} puntos de toda la isla.")
    print(f"Archivo guardado en: {ruta_out}")
else:
    print("No se extrajeron datos.")