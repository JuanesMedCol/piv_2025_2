# Análisis Económico Global (1960–2023)

## **Proyecto Integrador 5**

* **Tema:** Unificación y análisis de indicadores macroeconómicos (PIB, exportaciones, importaciones e inflación)
* **Autor:** Juan Esteban Atehortúa Sánchez

---

* **Fuente de datos:**
  * Global Imports of Goods and Services (1960–Present) — Frederick Salazar (2023)
  * Global Exports of Goods and Services (1960–Present) — Frederick Salazar (2023)
  * PIB (GDP) Global by Countries since 1960 to 2021 — Frederick Salazar (2023)
  * Global Inflation Rate (1960–Present) — Frederick Salazar (2023)

---

## Objetivo General

Realizar un análisis descriptivo de indicadores económicos del Banco Mundial (PIB, comercio e inflación) para América Latina y el Caribe (ALC) entre 1960 y 2023, con el propósito de identificar y contrastar sus tendencias macroeconómicas frente a los patrones observados en agregados económicos globales y mundiales. 

---

## Objetivos Específicos

*	Seleccionar y preparar un subconjunto acotado de países y años (ALC) para asegurar que el análisis se mantenga dentro de un alcance manejable.

*	Integrar y depurar los indicadores seleccionados mediante un proceso ETL que garantice coherencia temporal, estandarización y ausencia de duplicados.

*	Describir las tendencias básicas del PIB, comercio exterior e inflación del subconjunto (ALC), contrastándolas con las tendencias de los principales agregados económicos globales.

*	Explorar relaciones simples entre comercio exterior (exportaciones/importaciones) y PIB a través de visualizaciones descriptivas, sin modelamiento estadístico avanzado.

*	Presentar visualizaciones sintéticas que permitan interpretar patrones generales y el posicionamiento de ALC en el escenario económico mundial.

---

## Metodologia agil de trabajo

El proyecto se desarrollará bajo la Metodología Scrum, una estructura de trabajo ágil que prioriza la entrega continua de valor y la adaptabilidad a los requerimientos. La planificación del trabajo se organizará en iteraciones (Sprints) con una duración de dos semanas cada una, al final de las cuales se realizará una entrega parcial con funcionalidades completas y evaluables. Solamente el primer periodo se extenderá a tres semanas, ya que esta fase inicial estará dedicada a la planeación del proyecto, incluyendo la selección de datos, el diseño de la arquitectura ETL, y la formulación detallada de los objetivos y el alcance final del análisis.

---

## Proceso Metodológico (ETL)

El proceso metodológico se estructuró bajo un enfoque ETL (Extract, Transform, Load), orientado a garantizar la calidad, coherencia y utilidad analítica de los datos económicos utilizados. Este enfoque permitió transformar un conjunto heterogéneo de archivos provenientes del Banco Mundial en una base de datos integrada, limpia y lista para su exploración.

El pipeline aborda tres fases principales. En la etapa de extracción, los datasets se descargan de forma programática y se organizan en una estructura uniforme de trabajo. Posteriormente, en la fase de transformación, los archivos se someten a un proceso de normalización que incluye detección automática de separadores, estandarización de nombres de columnas, corrección de tipos, eliminación de filas incompletas y unificación de nomenclaturas mediante mapas semánticos. A partir de estos datos limpios se generan estructuras analíticas: una tabla de hechos con grano país-año-indicador, dimensiones de geografía e indicadores enriquecidas con metadatos del Banco Mundial y WITS, y una tabla ancha orientada a análisis comparativo. La fase final de carga consolida el modelo en una base SQLite, permitiendo realizar consultas robustas mediante SQL, con indicadores renombrados en términos legibles e interpretables. Este pipeline garantiza consistencia, reproducibilidad y claridad semántica para los análisis subsecuentes de comercio exterior, precios, crecimiento económico y PIB.

---

### 1. Propósito general del pipeline

El script implementa un **pipeline ETL** que toma varios datasets económicos de Kaggle (importaciones, exportaciones, PIB, inflación), los limpia y unifica, y termina generando:

* Una tabla de hechos: `fact_indicators` (indicadores por país–año)
* Dimensiones:

  * `dim_geo` (países / agregados con nombres y región)
  * `dim_indicator` (indicadores con nombres en inglés y español, y categoría)
* Una tabla ancha: `fact_wide` (una fila por país–año, una columna por indicador)
* Una base SQLite (`project.db`) con todo cargado y una vista de conveniencia `vw_wide_geo`.

Todo el flujo está pensado para que luego puedas hacer consultas SQL y análisis de forma sencilla, sin pelearte con nombres de columnas raros ni formatos distintos.

#### Datasets Utilizados

| Indicador                  | Dataset                                               | URL                                                                                                             | Licencia |
| -------------------------- | ----------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- | -------- |
| **Importaciones (% PIB)**  | *Global Imports of Goods and Services (1960–Present)* | [🔗 Kaggle](https://www.kaggle.com/datasets/fredericksalazar/global-imports-goods-and-services-1960-present)    | PDDL     |
| **Exportaciones (% PIB)**  | *Global Exports of Goods and Services (1960–Present)* | [🔗 Kaggle](https://www.kaggle.com/datasets/fredericksalazar/global-exports-of-goods-and-services-1960-present) | PDDL     |
| **PIB Global (1960–2021)** | *PIB (GDP) Global by Countries since 1960 to 2021*    | [🔗 Kaggle](https://www.kaggle.com/datasets/fredericksalazar/pib-gdp-global-by-countries-since-1960-to-2021)    | PDDL     |
| **Inflación (% anual)**    | *Global Inflation Rate (1960–Present)*                | [🔗 Kaggle](https://www.kaggle.com/datasets/fredericksalazar/global-inflation-rate-1960-present)                | PDDL     |


---

### 2. Extracción (E de ETL): descarga de datos

Primero, el script:

1. Crea la estructura de carpetas:

   * `data/`
   * `data/raw_data/` → CSV originales descargados
   * `data/normalized_data/` → CSV ya limpios y normalizados

2. Usa `kagglehub` para descargar estos datasets de Kaggle:

   * `global-imports-goods-and-services-1960-present`
   * `global-exports-of-goods-and-services-1960-present`
   * `pib-gdp-global-by-countries-since-1960-to-2021`
   * `global-inflation-rate-1960-present`

3. Copia todos los archivos descargados a `data/raw_data/`.

En esta etapa no se modifica el contenido, solo se centralizan los archivos en una ubicación estándar.

4. Estructura del Proyecto

```markdown
proyecto
├── README.md              ← Documentación principal
├── run.ipynb              ← Notebook ejecutable del pipeline y consultas
│
├── data/
│   ├── external/          ← Datos de Enriquecimiento del World Bank
│   ├── raw_data/          ← Datos originales descargados de Kaggle
│   ├── normalized_data/   ← Datos normalizados para la integración
│   └── unified_clean/     ← Integración de datos limpios y enriquecidos (ETL)
│
├── db/
│   └──project.db          ← Base de datos SQLite final
│
└── docs/
    ├── EA1.md             ← Documentación de Evidencia 1
    ├── EA2.md             ← Documentación de Evidencia 2
    └── gantt.md           ← Planificación del proyecto
```

---

### 3. Primera transformación: limpieza y normalización de CSV

Sobre `data/raw_data/`, el script hace una limpieza genérica y guarda los resultados en `data/normalized_data/`:

1. **Detección de separador** (`detect_sep`):

   * Lee la primera línea de cada archivo.
   * Si encuentra `;` y no encuentra `,`, asume `;` como separador.
   * Si no, usa `,`.

2. **Lectura segura**:

   * Lee cada CSV como texto (`dtype=str`) para evitar conflictos de tipos.
   * Interpreta valores vacíos como NA (`'', ' ', 'NA', 'NaN', 'nan'`).

3. **Normalización de vacíos**:

   * Reemplaza celdas vacías o con solo espacios por `pd.NA`.

4. **Filtrado de filas “muy vacías”**:

   * Calcula el porcentaje de valores nulos por fila.
   * Elimina filas con más del 50% de celdas vacías (`THRESHOLD_EMPTY_ROW = 0.5`).

5. **Conversión de tipos numéricos**:

   * Para cada columna, intenta convertir a numérico.
   * Si al menos el 60% de los valores se pueden convertir, la columna se transforma a numérica.

6. **Relleno de texto con “N/A”**:

   * Solo las columnas de tipo texto (`object`) se rellenan con `"N/A"`.
   * Las columna numéricas se dejan con `NaN` (adecuado para análisis).

7. **Guardado unificado**:

   * Asegura que todos los archivos de salida:

     * sean `.csv` (aunque el original tuviera otra extensión)
     * estén separados por `,`
     * con codificación UTF-8
   * Resultado: `data/normalized_data/*.csv` contiene todos los datos limpios, con estructura más homogénea.

---

### 4. Segunda transformación: unificación a un esquema analítico

Aquí comienza la parte de “modelo de datos” (hechos y dimensiones), trabajando sobre `data/normalized_data/` y generando `data/unified_clean/`.

#### 4.1. Normalización de columnas

Se normalizan nombres de columnas para que todos los CSV hablen el mismo “idioma”:

* Función `to_snake`:

  * Pone en minúsculas, sin acentos, reemplaza espacios por `_`, quita caracteres raros.
  * Asegura que no empiece por dígito.
* `CANONICAL_MAP`:

  * Mapea sinónimos a nombres estándar, por ejemplo:

    * `country`, `countryname`, `country_name` → `country_name`
    * `indicator` → `indicator_name`
    * `total_gdp` → `gdp_current_local`
    * `imports_of_goods_and_services` → `imports_percent_gdp`
    * etc.

De esta forma, aunque cada dataset use nombres ligeramente diferentes, el pipeline termina con un conjunto de nombres canónicos (country_name, country_code, year, gdp_current_million, etc.).

#### 4.2. Detección de columnas de valor (indicadores)

Función `detect_value_cols`:

* Busca primero columnas cuyo nombre ya está en `T_VALUE_MAP` (por ejemplo `imports_of_goods_and_services`, `inflation_percent`, etc.).
* Si no las encuentra:

  * considera como “meta” columnas como país, región, año, etc.
  * busca columnas numéricas entre el resto
  * las columnas numéricas con suficiente densidad se consideran métricas (valores de indicador).

#### 4.3. Construcción de hechos desde cada archivo (`facts_from_file`)

Para cada CSV normalizado:

1. Normaliza columnas (`normalize_columns`).

2. Asegura que existan `country_code`, `country_name`, `year` (aunque sea como NA).

3. `country_code` se pasa a mayúsculas; `year` se convierte a entero nullable.

4. Detecta columnas de valor (`vcols`).

5. Para cada valor:

   * Si no hay `indicator_code`, se asigna usando `T_VALUE_MAP` (por ejemplo, `gdp_current_million` → `NY.GDP.MKTP.CD_MLN`).
   * Si no hay `indicator_name`, se toma de `INDICATOR_NAMES` (nombres oficiales del Banco Mundial en inglés).
   * Convierte la columna de valor a numérico (`value`).
   * Se queda solo con columnas clave:

     * país, región, año, indicador, valor, etc.

6. Devuelve un DataFrame con estructura homogénea:

   ```text
   country_code | country_name | region | sub_region | ... | year | indicator_code | indicator_name | value
   ```

---

### 5. Construcción del modelo dimensional

Una vez concatenados todos los hechos (`facts`), se construyen las tablas analíticas.

#### 5.1. Tabla de hechos depurada (`fact_indicators`)

Función `dedup_facts`:

1. Define la clave de grano:
   `country_code + year + indicator_code`.
2. Si hay duplicados para la misma clave, promedia el valor (`groupby(...).mean()`).
3. Reconstruye los metadatos (nombre de país, región, nombre de indicador) eligiendo la primera ocurrencia por clave.
4. Marca agregados geográficos (`is_aggregate`) usando `build_dim_geo` y la lógica de `tag_aggregates_dim_geo`:

   * Detecta códigos especiales del Banco Mundial (HIC, LMC, WLD, etc.).
   * Usa `income_group`, `region` y `organization_name` para marcar filas como agregados.
5. Resultado: una tabla limpia en long format:

   ```text
   fact_indicators.csv
   country_code | year | indicator_code | value | country_name | region | sub_region | ... | is_aggregate | indicator_name
   ```

#### 5.2. Dimensión geográfica (`dim_geo`)

Función `build_dim_geo`:

1. Extrae columnas relacionadas con geografía de los hechos:

   * country_code, country_name, region, sub_region, etc.
2. Elimina duplicados → una fila por país/agrupación.
3. Llama a `tag_aggregates_dim_geo` para identificar agregados WB:

   * ej. MIC, HIC, WLD, LCN, SSA, etc.
4. Arregla formato de `country_name` (Title Case, salvo etiquetas tipo “AGREGADOS”).

Luego tú enriqueces esta tabla con:

* Nombres oficiales de WITS (`country_name_official`)
* Región y subregión estándar (`region`, `sub_region`)
* Limpieza de columnas sobrantes (income_group, organization_name, intermediate_region)
* Definición final de:

  ```text
  country_code | country_name | region | sub_region | is_aggregate
  ```

#### 5.3. Dimensión de indicadores (`dim_indicator`)

Función `build_dim_indicator`:

1. Extrae pares únicos `indicator_code` – `indicator_name`.
2. Usa `INDICATOR_NAMES` para asegurar nombres consistentes en inglés.

Luego se enriquece con:

* Nombres en español (`indicator_label_es`), usando diccionarios:

  ```python
  INDICATOR_LABEL_ES = {
      "NE.IMP.GNFS.ZS": "Importaciones de bienes y servicios (% del PIB)",
      "NE.EXP.GNFS.ZS": "Exportaciones de bienes y servicios (% del PIB)",
      "FP.CPI.TOTL.ZG": "Inflación (variación anual del IPC, %)",
      "NY.GDP.MKTP.KD.ZG": "Crecimiento del PIB real (% anual)",
      "NY.GDP.MKTP.CD_MLN": "PIB corriente (millones, según archivo)",
      "NY.GDP.MKTP.CD_LOCAL": "PIB corriente (moneda local, según archivo)"
  }
  ```

* Grupos temáticos (`indicator_group`), por ejemplo:

  * Comercio exterior
  * Precios e inflación
  * Actividad económica
  * PIB (nivel)

Además, se hace una **última normalización semántica**:

* Se reemplazan códigos WB crípticos por códigos legibles:

  * `NE.IMP.GNFS.ZS` → `importaciones`
  * `NE.EXP.GNFS.ZS` → `exportaciones`
  * `FP.CPI.TOTL.ZG` → `inflacion`
  * `NY.GDP.MKTP.KD.ZG` → `crecimiento_anual`
  * `NY.GDP.MKTP.CD_LOCAL` → `pib_monedalocal`
  * `NY.GDP.MKTP.CD_MLN` → `pib_millones`

Esto se aplica **tanto en `dim_indicator` como en `fact_indicators`**, de forma que hacer consultas SQL sea mucho más claro.

---

### 6. Tabla ancha (`fact_wide`)

Función `build_wide`:

* Toma `fact_clean` (hechos depurados) y pivotea:

  * Índice: `country_code`, `year`
  * Columnas: `indicator_code`
  * Valores: `value`

Luego renombra columnas de códigos WB a nombres legibles:

* `NE.EXP.GNFS.ZS` → `exports_percent_gdp`
* `NE.IMP.GNFS.ZS` → `imports_percent_gdp`
* `FP.CPI.TOTL.ZG` → `inflation_percent`
* `NY.GDP.MKTP.KD.ZG` → `gdp_growth_percent`
* `NY.GDP.MKTP.CD_MLN` → `gdp_current_million`
* `NY.GDP.MKTP.CD_LOCAL` → `gdp_current_local`

Resultado:

```text
fact_wide.csv
country_code | year | exports_percent_gdp | imports_percent_gdp | inflation_percent | gdp_growth_percent | gdp_current_million | gdp_current_local
```

---

### 7. Carga (L de ETL): escritura en SQLite y vista

Finalmente, el script crea una base SQLite:

1. Crea/abre `db/project.db`.

2. Carga las tablas CSV a SQLite:

   ```python
   dim_indicator = pd.read_csv(os.path.join(CLEAN_DIR, "dim_indicator.csv"))
   fact_indicators = pd.read_csv(os.path.join(CLEAN_DIR, "fact_indicators.csv"))
   fact_wide = pd.read_csv(os.path.join(CLEAN_DIR, "fact_wide.csv"))
   dim_geo.to_sql("dim_geo", conn, if_exists="replace", index=False)
   dim_indicator.to_sql("dim_indicator", conn, if_exists="replace", index=False)
   fact_indicators.to_sql("fact_indicators", conn, if_exists="replace", index=False)
   fact_wide.to_sql("fact_wide", conn, if_exists="replace", index=False)
   ```

3. Crea una vista de conveniencia:

   ```sql
   CREATE VIEW IF NOT EXISTS vw_wide_geo AS
   SELECT
     w.country_code, g.country_name, g.region, g.sub_region,
     w.year,
     w.exports_percent_gdp,
     w.imports_percent_gdp,
     w.inflation_percent,
     w.gdp_growth_percent,
     w.gdp_current_million,
     w.gdp_current_local
   FROM fact_wide w
   LEFT JOIN dim_geo g USING (country_code);
   ```

---

### 8. Consultas posteriores

Una vez todo está en SQLite, puedes hacer consultas como:

```sql
SELECT 
    g.country_name,
    f.year,
    f.value AS indicador_valor,
    f.indicator_code,      -- ahora legible: importaciones, inflacion, etc.
    i.indicator_name       -- nombre descriptivo en español
FROM fact_indicators f
JOIN dim_geo g ON f.country_code = g.country_code
JOIN dim_indicator i ON f.indicator_code = i.indicator_code
WHERE g.is_aggregate = 0
  AND f.year BETWEEN 2010 AND 2022
ORDER BY f.year, f.indicator_code;
```

Y eso te devuelve una serie temporal país–año–indicador con nombres limpios en español y solo países (sin agregados).

#### Base de Datos (SQLite)

Archivo: `db/project.db`

### Tablas principales

| Tabla                | Descripción                                         |
| -------------------- | --------------------------------------------------- |
| `dim_geo`            | Dimensión geográfica (países y regiones)            |
| `dim_indicator`      | Catálogo de indicadores económicos                  |
| `fact_indicators`    | Hechos normalizados por país/año/indicador          |
| `fact_wide`          | Versión pivotada para análisis rápido               |
| `vw_exports_imports` | Vista SQL para comparar exportaciones/importaciones |

---

## Resultados y Análisis

undial (1960–2023), integrando indicadores esenciales del Banco Mundial tales como el Producto Interno Bruto (PIB), la inflación, y las exportaciones e importaciones de bienes y servicios. Gracias a la estandarización y unificación lograda en el proceso ETL, se obtuvo un conjunto de datos consistente y comparable a través del tiempo, lo que facilita el análisis histórico y la interpretación de tendencias económicas globales.

El estudio de los indicadores integrados revela relaciones coherentes entre crecimiento económico, estabilidad de precios y comercio exterior. Se observan periodos en los que la expansión del PIB coincide con incrementos sostenidos del comercio internacional, reflejando procesos de apertura económica y aumento de la actividad productiva. De manera complementaria, las series históricas evidencian que los episodios de inflación elevada suelen asociarse con desaceleraciones del crecimiento, lo que coincide con el comportamiento típico documentado en ciclos económicos globales.

El análisis temporal también permite identificar momentos clave en la dinámica económica mundial, como desaceleraciones simultáneas entre múltiples países durante crisis financieras, o fases de rápida recuperación impulsadas por mejoras en la actividad productiva y el comercio internacional. Asimismo, la estructura de la base facilita comparaciones entre países con diferentes trayectorias, permitiendo observar cómo algunos logran mantener crecimiento sostenido acompañado por estabilidad inflacionaria, mientras que otros muestran mayor volatilidad a lo largo del tiempo.

La arquitectura del modelo analítico diseñado no solo permitió integrar y estudiar estas relaciones, sino que también habilita consultas flexibles por país, periodo o indicador, generando una plataforma robusta para análisis más avanzados. Además, la estandarización de nombres de indicadores y códigos legibles facilita extender la base con nuevas variables económicas del Banco Mundial, garantizando la comparabilidad longitudinal y la reutilización en investigaciones futuras.

En conjunto, los resultados demuestran que la correcta integración de fuentes heterogéneas y la normalización semántica de los indicadores permiten obtener una visión clara, consistente y amplia de la evolución económica global, adecuada tanto para análisis descriptivos como para estudios comparativos o modelos econométricos.

---

## Referencias (APA)

Salazar, F. (2023). *Global Imports of Goods and Services (1960–Present)* [dataset]. Kaggle.
[https://www.kaggle.com/datasets/fredericksalazar/global-imports-goods-and-services-1960-present](https://www.kaggle.com/datasets/fredericksalazar/global-imports-goods-and-services-1960-present)

Salazar, F. (2023). *Global Exports of Goods and Services (1960–Present)* [dataset]. Kaggle.
[https://www.kaggle.com/datasets/fredericksalazar/global-exports-of-goods-and-services-1960-present](https://www.kaggle.com/datasets/fredericksalazar/global-exports-of-goods-and-services-1960-present)

Salazar, F. (2023). *PIB (GDP) Global by Countries since 1960 to 2021* [dataset]. Kaggle.
[https://www.kaggle.com/datasets/fredericksalazar/pib-gdp-global-by-countries-since-1960-to-2021](https://www.kaggle.com/datasets/fredericksalazar/pib-gdp-global-by-countries-since-1960-to-2021)

Salazar, F. (2023). *Global Inflation Rate (1960–Present)* [dataset]. Kaggle.
[https://www.kaggle.com/datasets/fredericksalazar/global-inflation-rate-1960-present](https://www.kaggle.com/datasets/fredericksalazar/global-inflation-rate-1960-present)

World Bank. (2023). *World Development Indicators*. The World Bank Group.
[https://databank.worldbank.org/source/world-development-indicators](https://databank.worldbank.org/source/world-development-indicators)
