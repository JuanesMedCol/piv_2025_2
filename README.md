# Análisis Económico Global (1960–2023)

## **Proyecto Integrador 5**
 
* **Tema:** Unificación y análisis de indicadores macroeconómicos (PIB, exportaciones, importaciones e inflación)
* **Autor:** Juan Esteban Atehortúa Sánchez

---

* **Fuente de datos:**
  *	Global Imports of Goods and Services (1960–Present) — Frederick Salazar (2023)
  *	Global Exports of Goods and Services (1960–Present) — Frederick Salazar (2023)
  *	PIB (GDP) Global by Countries since 1960 to 2021 — Frederick Salazar (2023)
  *	Global Inflation Rate (1960–Present) — Frederick Salazar (2023)

---

## Objetivo General

Realizar un análisis descriptivo de un conjunto limitado de indicadores económicos del Banco Mundial (PIB, exportaciones, importaciones e inflación), seleccionando únicamente un subconjunto representativo de países entre 1960 y 2023, con el fin de identificar tendencias generales y relaciones básicas sin pretender abarcar la totalidad de los datos globales disponibles.

---

## Objetivos Específicos

* Seleccionar y preparar un subconjunto acotado de países y años para asegurar que el análisis se mantenga dentro de un alcance manejable.

* Integrar y depurar los indicadores seleccionados mediante un proceso ETL que garantice coherencia temporal, estandarización y ausencia de duplicados.

* Describir las tendencias básicas del PIB, comercio exterior e inflación únicamente dentro de un subconjunto seleccionado, sin realizar comparaciones globales completas.

* Explorar relaciones simples entre comercio exterior (exportaciones/importaciones) y PIB a través de visualizaciones descriptivas, sin modelamiento estadístico avanzado.

* Presentar visualizaciones sintéticas que permitan interpretar patrones generales sin pretender caracterizar el comportamiento económico mundial en su totalidad.

---

## Estructura del Proyecto

```
proyecto
├── README.md                  ← Documentación principal
├── run.ipynb                  ← Notebook ejecutable del pipeline y consultas
│
├── data/
│   ├── external/              ← Datos basados en World Bank para Enriquecimiento 
│   ├── raw_data/              ← Datos originales descargados de Kaggle
│   ├── normalized_data/       ← Datos estandarizados a separacion por comas
│   └── unified_clean/         ← Integracion de datos limpia y normalizada (ETL)
│
├── db/
│   └──project.db              ← Base de datos SQLite final
│
└── docs/
    ├── EA1.md                 ← Documentacion de Evidencia 1
    ├── EA2.md                 ← Documentacion de Evidencia 2
    └── gantt.md               ← Planificación del proyecto
```

---

## Datasets Utilizados

| Indicador                  | Dataset                                               | URL                                                                                                             | Licencia |
| -------------------------- | ----------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- | -------- |
| **Importaciones (% PIB)**  | *Global Imports of Goods and Services (1960–Present)* | [🔗 Kaggle](https://www.kaggle.com/datasets/fredericksalazar/global-imports-goods-and-services-1960-present)    | PDDL     |
| **Exportaciones (% PIB)**  | *Global Exports of Goods and Services (1960–Present)* | [🔗 Kaggle](https://www.kaggle.com/datasets/fredericksalazar/global-exports-of-goods-and-services-1960-present) | PDDL     |
| **PIB Global (1960–2021)** | *PIB (GDP) Global by Countries since 1960 to 2021*    | [🔗 Kaggle](https://www.kaggle.com/datasets/fredericksalazar/pib-gdp-global-by-countries-since-1960-to-2021)    | PDDL     |
| **Inflación (% anual)**    | *Global Inflation Rate (1960–Present)*                | [🔗 Kaggle](https://www.kaggle.com/datasets/fredericksalazar/global-inflation-rate-1960-present)                | PDDL     |

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

---

## Derechos y Uso Académico

Este proyecto ha sido desarrollado con fines exclusivamente **académicos y educativos**, como parte del **Proyecto Integrador 5**.
El contenido, los análisis y las visualizaciones presentadas se basan en **fuentes de datos públicas y abiertas** del Banco Mundial, obtenidas a través de la plataforma **Kaggle**, bajo licencias **PDDL (Public Domain Dedication and License)**, que permiten su libre uso, redistribución y adaptación con fines no comerciales, siempre que se mantenga la atribución correspondiente a los autores originales.

El autor, **Juan Esteban Atehortúa Sánchez**, conserva los derechos morales sobre la estructura, metodología de análisis, procesamiento de datos y los materiales generados en este trabajo.
No obstante, se autoriza su uso, reproducción o adaptación en contextos académicos, investigativos o docentes, siempre que se cite la fuente de manera adecuada, conforme a las normas de **referenciación APA** o el formato bibliográfico requerido.

> **Cita sugerida:**
> Atehortúa Sánchez, J. E. (2025). *Análisis Económico Global (1960–2023): Unificación y análisis de indicadores macroeconómicos (PIB, exportaciones, importaciones e inflación)* [Proyecto académico].

El contenido de este proyecto **no representa posturas oficiales ni asesoramiento económico**, y su propósito es exclusivamente **analítico y formativo**, contribuyendo al fortalecimiento del conocimiento en economía aplicada y análisis de datos.
