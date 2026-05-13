

# Data set de mapas de gravedad de islas volcánicas.

Repositorio desarrollado durante unas prácticas externas en el Instituto de Productos Naturales y Agrobiología (IPNA-CSIC), centrado en el análisis de anomalías gravimétricas en archipiélagos volcánicos.  Este proyecto fue desarrollado por dos estudiantes Yose Bravo Pérez y Raquel Salamanca Cubas, de la Universidad de La Laguna, en un periodo de prácticas externas en el IPNA-CSIC.


---

# Objetivo del proyecto

El objetivo principal del trabajo es estudiar la posible presencia de complejos intrusivos de alta densidad en sistemas volcánicos mediante análisis gravimétrico .

El proyecto se basa en la hipótesis propuesta por George L. P. Walker, según la cual muchos volcanes podrían contener estructuras intrusivas internas no visibles en superficie.

---

# Área de estudio

Los sistemas volcánicos analizados pertenecen a los siguientes archipiélagos oceánicos:

- Canarias
- Azores
- Cabo Verde
- Hawaii
- Reunión

Estas regiones fueron seleccionadas por encontrarse sobre litosfera oceánica, lo que facilita la interpretación de anomalías gravitatorias asociadas a contrastes de densidad en las esctructuras volcánicas.

---

# Fuentes de datos

El proyecto combina diferentes tipos de información gravimétrica:

## 1. Mapas gravimétricos históricos
Mapas de anomalías obtenidos a partir de publicaciones científicas antiguas.

## 2. Datos numéricos asociados a publicaciones
Archivos con:
- coordenadas geográficas,
- altitudes ortométricas,
- gravedad observada,
- anomalías de Bouguer.
## 3. Base de datos del IGN
Datos gravimétricos procedentes del Instituto Geográfico Nacional (España) para las Islas Canarias.

---

# Digitalización de mapas

Los mapas históricos fueron digitalizados utilizando QGIS.

Se emplearon dos metodologías principales:

- Digitalización por puntos
- Vectorización mediante líneas/isovalores

La georreferenciación se realizó utilizando coordenadas WGS84.

---

# Procesamiento de datos

El procesamiento se realizó mediante scripts en Python.

Las principales etapas fueron:

- Conversión y limpieza de datos
- Cálculo de gravedad normal
- Obtención de anomalías de aire libre
- Cálculo de anomalías de Bouguer simple
- Correcciones topográficas
- Generación de mapas gravimétricos

Para las correcciones topográficas se utilizó la librería geofísica `Harmonica`.

---

# Resultados generales

El análisis preliminar permitió identificar múltiples anomalías gravimétricas positivas compatibles con posibles complejos intrusivos en diferentes islas volcánicas.

| Isla          | Nº de complejos | Corresponde con estructuras geológica| Localización principal | Estructura geológica |
|---------------|-----------------|--------------------------------------|------------------------|----------------------|
| Tenerife       | 1 | NO | Zona sur de Tenerife |  |
| La Gomera      | 1 | NO| Vallehermoso | Antigua caldera|
| El Hierro      | 1 | SI | Frontera | Posible antiguo edificio volcánico |
| La Palma       | 1 | SI | El Paso |Caldera de Taburiente |
| Gran Canaria   | 1 | SI | Tejeda | Caldera de Tejeda |
| Fuerteventura  | 1 | SI | Zoona central/oeste | Macizo de Betancuria |
| Lanzarote      | 1 |NO | Arrecife | |
| Pico           | 1 | SI | Pontas Negras | Topo Volcano  |
| Faial          | 1 | NO | Zona nordeste | |
| São Miguel     | 1 | SI | Zona Nordeste | Macizo volcánico |
| Terceira       | 5 | NO | sur de la isla | |
| Oahu           | 2 | SI | | Cordilleras sureste y noroeste |
| Big Island     | 2 | SI | Región volcánica central | Mauna Kea, Mauna Lea y Kilauea
| Maio           | 1 | SI | Zona centro| Monte Penoso |
| Reunión        | 1 | SI |  Zona centro y suoreste |Pico de Neiges y Dolomieu crater |

En Terceira aunque se identifican 5 anomalías gravitatorias positivas no se las puede considerar como posibles complejos intrusivos pues la vaciariación de la anomalñia con respecto de las zonas circundantes en menor de 5mGal.

---

# Estructura del repositorio

El repositorio se organiza por archipiélagos e islas e incluye:

- Papers históricos
- Capturas de mapas
- Datos digitalizados
- Archivos `.csv` y `.xlsx`
- Scripts en Python
- Resultados cartográficos

---

# Herramientas utilizadas

- Python
- QGIS
- Harmonica
- Pandas
- NumPy
- Matplotlib

---

# Líneas futuras

- Integración de datasets en una única base homogénea
- Mejora de modelos digitales de elevación
- Automatización de detección de anomalías
- Identificación geométrica de complejos intrusivos
