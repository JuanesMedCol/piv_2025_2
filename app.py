import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# --- Configuración de la Página ---
st.set_page_config(
    page_title="Dashboard Económico de América Latina y el Caribe (ALC)",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Conexión y Carga de Datos ---
# Ruta de la base de datos
DB_FILE = 'db/project.db'
@st.cache_data
def get_data_from_db():
    """
    Establece la conexión a la base de datos y ejecuta las consultas,
    incluyendo ahora las métricas de Comercio, Crecimiento y la Tasa de Cambio Implícita.
    """
    try:
        conn = sqlite3.connect(DB_FILE)

        # 1. Consulta principal (ALC):
        # Usamos un CTE (Common Table Expression) para calcular la Tasa de Cambio
        # Implícita (GDP_Local / GDP_USD) * 1,000,000 en el propio SQL.
        query_main = """
        WITH data_cte AS (
            SELECT
                g.country_name,
                w.year,
                w.gdp_current_million AS pib_millones,
                w.inflation_percent AS inflacion,
                w.exports_percent_gdp AS exportaciones_percent,
                w.imports_percent_gdp AS importaciones_percent,
                w.gdp_current_local AS pib_monedalocal,
                w.gdp_growth_percent AS crecimiento_anual,
                -- Cálculo de la Tasa de Cambio Implícita:
                -- (PIB en Moneda Local / PIB en Millones de USD) * 1,000,000
                CASE
                    WHEN w.gdp_current_million IS NULL OR w.gdp_current_million = 0
                    THEN NULL
                    ELSE (w.gdp_current_local * 1000000.0) / w.gdp_current_million
                END AS costo_moneda_local_usd
            FROM
                fact_wide w
            JOIN
                dim_geo g ON w.country_code = g.country_code
            WHERE
                g.region LIKE 'Latin America%' AND w.year >= 2000
        )
        SELECT * FROM data_cte
        WHERE
            costo_moneda_local_usd IS NOT NULL AND costo_moneda_local_usd > 0 -- Filtrar solo datos válidos para la tasa de cambio
        ORDER BY
            country_name, year;
        """
        df_main = pd.read_sql_query(query_main, conn)
        
        # Calcular la Balanza Comercial Neta (Exportaciones - Importaciones) en Pandas, aunque ya está en SQL
        if 'exportaciones_percent' in df_main.columns and 'importaciones_percent' in df_main.columns:
             df_main['balanza_comercial_neta'] = df_main['exportaciones_percent'] - df_main['importaciones_percent']


        # 2. Consulta de Datos Globales para el Mapa Choropleth (Último Año)
        query_global = """
        SELECT
            g.country_name,
            g.country_code,
            w.year,
            w.gdp_current_million AS pib_millones -- Indicador para el mapa (PIB Total)
        FROM
            fact_wide w
        JOIN
            dim_geo g ON w.country_code = g.country_code
        WHERE
            w.year = (SELECT MAX(year) FROM fact_wide) -- Último año disponible
            AND w.gdp_current_million IS NOT NULL
        ORDER BY
            g.country_name;
        """
        df_global = pd.read_sql_query(query_global, conn)

        # 3. Consulta para outliers de INFLACIÓN
        OUTLIERS_INFLATION = ('Haiti', 'Venezuela, RB', 'Suriname')
        query_outliers_inflation = f"""
        SELECT
            g.country_name,
            w.year,
            w.inflation_percent
        FROM
            fact_wide w
        JOIN
            dim_geo g ON w.country_code = g.country_code
        WHERE
            g.region LIKE 'Latin America%'
            AND g.country_name IN ({','.join(['?']*len(OUTLIERS_INFLATION))})
            AND w.year BETWEEN 2010 AND 2023
        ORDER BY
            g.country_name, w.year;
        """
        df_outliers_inflation = pd.read_sql_query(query_outliers_inflation, conn, params=OUTLIERS_INFLATION)

        # 4. Consulta para la anomalía del PIB
        OUTLIERS_GDP = ('Guyana', 'Venezuela, RB')
        query_outliers_gdp = f"""
        SELECT
            g.country_name,
            w.year,
            w.gdp_current_million AS pib_millones
        FROM
            fact_wide w
        JOIN
            dim_geo g ON w.country_code = g.country_code
        WHERE
            g.region LIKE 'Latin America%'
            AND g.country_name IN ({','.join(['?']*len(OUTLIERS_GDP))})
            AND w.year BETWEEN 2010 AND 2023
        ORDER BY
            g.country_name, w.year;
        """
        df_outliers_gdp = pd.read_sql_query(query_outliers_gdp, conn, params=OUTLIERS_GDP)


        conn.close()
        # Devolver todos los DataFrames
        return df_main, df_outliers_inflation, df_outliers_gdp, df_global
    except Exception as e:
        # En caso de error, mostramos un mensaje y devolvemos DataFrames vacíos
        st.error(f"Error al conectar o consultar la base de datos: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# La llamada a la función ahora retorna 4 DataFrames
df_main, df_outliers_inflation, df_outliers_gdp, df_global = get_data_from_db()

# --- Título y Descripción ---
st.title("🌎 Dashboard Económico de América Latina y el Caribe (ALC)")
st.markdown("Este *dashboard* presenta tendencias de **PIB Total**, **Inflación**, **Comercio Exterior**, **Crecimiento Anual** y **Tasa de Cambio Implícita** para países de América Latina y el Caribe, utilizando datos del Banco Mundial.")
st.warning("⚠️ **Advertencia:** La métrica de **PIB** mostrada por defecto es el **PIB Total (en Millones de USD)**.")


# Verificar si se cargaron datos correctamente
if df_main.empty:
    st.warning("No se pudieron cargar los datos de la base de datos. Por favor, verifica que el archivo 'db/project.db' sea accesible y la consulta SQL sea correcta.")
else:
    # --- Barra Lateral (Filtros) ---
    st.sidebar.header("Filtros de Visualización")

    # Selector de Indicador Principal
    indicator_options = {
        # Nuevo Indicador
        "Costo Moneda Local/USD (Tasa Implícita) [costo_moneda_local_usd]": {'col': 'costo_moneda_local_usd', 'label': 'Costo Moneda Local por 1 USD', 'format': ",.2f", 'unit': ' / USD', 'category': 'Moneda'},
        
        # Indicadores Existentes
        "PIB Total (Millones USD) [pib_millones]": {'col': 'pib_millones', 'label': 'PIB Total (Millones USD)', 'format': ",.0f", 'unit': '$ ', 'category': 'PIB'},
        "PIB (Moneda Local) [pib_monedalocal]": {'col': 'pib_monedalocal', 'label': 'PIB (Moneda Local)', 'format': ",.0f", 'unit': '', 'category': 'PIB'},
        "Crecimiento Anual (% PIB) [crecimiento_anual]": {'col': 'crecimiento_anual', 'label': 'Crecimiento Anual (% PIB)', 'format': ".1f", 'unit': ' %', 'category': 'PIB'},
        "Balanza Comercial Neta (% PIB) [importaciones_vs_exportaciones]": {'col': 'balanza_comercial_neta', 'label': 'Balanza Comercial Neta (% PIB)', 'format': ".1f", 'unit': ' %', 'category': 'Comercio'},
        "Exportaciones (% PIB) [exportaciones]": {'col': 'exportaciones_percent', 'label': 'Exportaciones (% PIB)', 'format': ".1f", 'unit': ' %', 'category': 'Comercio'},
        "Importaciones (% PIB) [importaciones]": {'col': 'importaciones_percent', 'label': 'Importaciones (% PIB)', 'format': ".1f", 'unit': ' %', 'category': 'Comercio'},
        "Tasa de Inflación (% Anual) [inflacion]": {'col': 'inflacion', 'label': 'Inflación (% Anual)', 'format': ".1f", 'unit': ' %', 'category': 'Precios'},
    }
    
    # Ordenar los indicadores para el selectbox
    sorted_indicator_keys = sorted(indicator_options.keys(), key=lambda k: indicator_options[k]['category'] + k)

    indicator_key = st.sidebar.selectbox(
        "Selecciona el Indicador Principal:",
        sorted_indicator_keys,
        index=1 # PIB Total (Millones USD) [pib_millones] como default
    )

    indicator_meta = indicator_options[indicator_key]
    y_col = indicator_meta['col']
    y_label = indicator_meta['label']
    value_format = indicator_meta['format']
    unit = indicator_meta['unit']
    title_kpi = indicator_key.split(' [')[0] # Usa solo el nombre principal para el título

    # Slider de rango de años
    min_year = int(df_main['year'].min())
    max_year = int(df_main['year'].max())
    year_range = st.sidebar.slider(
        "Rango de Años para Gráficos:",
        min_value=min_year,
        max_value=max_year,
        value=(2010, max_year)
    )

    # Filtro por país para el gráfico de líneas
    available_countries = sorted(df_main['country_name'].unique().tolist())
    default_countries = ['Colombia', 'Panama', 'Brazil', 'Chile', 'Mexico', 'Argentina']
    default_countries = [c for c in default_countries if c in available_countries]

    selected_countries = st.sidebar.multiselect(
        "Selecciona Países para el Gráfico de Líneas:",
        available_countries,
        default=default_countries
    )

    # Slider para limitar la escala de Inflación del Heatmap General
    st.sidebar.markdown("---")
    st.sidebar.subheader("Opciones de Heatmap")
    max_inflation_limit = st.sidebar.slider(
        "Límite Superior del Heatmap de Inflación (%)",
        min_value=10.0,
        max_value=100.0,
        value=30.0,
        step=5.0
    )
    st.sidebar.markdown("*(Aplica al Heatmap General en 'Análisis de Inflación')*")


    # --- Definición de Pestañas ---
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Resumen y Tendencias", "🔥 Análisis de Inflación", "📈 Anomalías del PIB", "🗺️ Vista Global"])

    # --- Lógica de cálculo de métricas ---
    df_filtered = df_main[
        (df_main['year'] >= year_range[0]) & (df_main['year'] <= year_range[1])
    ]
    
    # Calcular el promedio regional (ALC) para el último año disponible
    latest_year = df_filtered['year'].max()
    df_latest = df_main[df_main['year'] == latest_year]

    # Asegurarse de que y_col exista antes de calcular el promedio
    if y_col in df_latest.columns:
        # Excluir países con valores NaN para el promedio regional
        alc_average = df_latest[y_col].dropna().mean()
    else:
        alc_average = np.nan

    # --- Pestaña 1: Resumen y Tendencias ---
    with tab1:
        st.header("Análisis de Indicadores Clave")
        
        col_kpi, col_spacer, col_desc = st.columns([1, 0.1, 2])

        with col_kpi:
            st.subheader(f"Métrica Regional ({latest_year})")
            
            # Formatear el valor KPI
            if pd.isna(alc_average):
                display_value = "N/A"
            else:
                # Usar el formato dinámico definido en indicator_options
                display_value = f"{alc_average:{value_format}}"
                
                # Manejo de la unidad de visualización
                if unit == '$ ':
                    # Ejemplo: $ 123,456
                    display_value = unit.strip() + ' ' + display_value
                elif unit == ' / USD':
                    # Ejemplo: 123.45 / USD
                    display_value = display_value + unit
                else:
                    # Ejemplo: 12.3 % o 123,456 (PIB Local sin unidad)
                    display_value = display_value + unit
            
            st.metric(
                label=title_kpi,
                value=display_value,
                delta_color="off"
            )
            st.markdown(f"*(Cifra promedio para todos los países de ALC en {latest_year}.)*")
        
        with col_desc:
            st.markdown("""
                Utiliza el menú lateral para seleccionar el indicador principal y el rango de años de interés. 
                Esta sección te permite comparar la **tendencia histórica** de países seleccionados 
                frente a la **distribución general** del indicador en la región de ALC.
            """)
        
        st.markdown("---")
        
        col_line, col_box = st.columns(2)

        # --- Gráfico 1: Tendencia Histórica del Indicador Principal (Líneas) ---
        with col_line:
            st.subheader(f"Tendencia de {title_kpi}")
            st.markdown("_*Usa el Range Slider inferior para hacer zoom en períodos específicos.*_")

            df_plot_line = df_filtered[df_filtered['country_name'].isin(selected_countries)]
            
            # Verificar si hay datos seleccionados para el gráfico de líneas
            if df_plot_line.empty:
                 st.info("Selecciona al menos un país y un rango de años válido para mostrar la tendencia.")
            else:
                fig_line = px.line(
                    df_plot_line,
                    x='year',
                    y=y_col,
                    color='country_name',
                    title=f'Evolución Anual de {y_label} por País',
                    labels={'year': 'Año', y_col: y_label, 'country_name': 'País'},
                    markers=True
                )
                
                # Formato del eje Y: dinámico basado en la unidad
                if unit == '$ ':
                    y_tick_format = "$,.0f" 
                elif unit == ' %':
                    y_tick_format = ".1f"
                elif unit == ' / USD':
                    y_tick_format = ",.2f"
                else: # PIB Moneda Local sin unidad
                    y_tick_format = ",.0f"

                
                fig_line.update_layout(
                    xaxis_title="Año",
                    yaxis_title=y_label,
                    hovermode="x unified",
                    margin=dict(t=50, b=50, l=20, r=20)
                )
                fig_line.update_yaxes(tickformat=y_tick_format)
                
                # **MEJORA CLAVE: Range Slider para hacer la gráfica más descriptiva**
                fig_line.update_xaxes(
                    rangeslider_visible=True, 
                    rangeselector=dict(
                        buttons=list([
                            dict(count=1, label="1A", step="year", stepmode="backward"),
                            dict(count=5, label="5A", step="year", stepmode="backward"),
                            dict(step="all")
                        ])
                    )
                )

                st.plotly_chart(fig_line, use_container_width=True)

        # --- Gráfico 2: Distribución (Box Plot) ---
        with col_box:
            st.subheader(f"Distribución de {title_kpi}")
            
            # Formato del eje Y para el Box Plot (dinámico)
            if unit == '$ ':
                y_tick_format_box = "$,.0f" 
            elif unit == ' %':
                y_tick_format_box = ".1f"
            elif unit == ' / USD':
                y_tick_format_box = ",.2f"
            else: # PIB Moneda Local sin unidad
                y_tick_format_box = ",.0f"


            fig_box = px.box(
                df_filtered,
                x='country_name',
                y=y_col,
                title=f'Distribución de {y_label} por País ({year_range[0]}-{year_range[1]})',
                labels={'country_name': 'País', y_col: y_label},
                notched=True
            )
            fig_box.update_yaxes(rangemode='normal', tickformat=y_tick_format_box)

            fig_box.update_xaxes(showticklabels=False, title_text="Países de ALC (Ver países en Hover)")
            fig_box.update_layout(
                margin=dict(t=50, b=50, l=20, r=20),
                hovermode="closest"
            )
            st.plotly_chart(fig_box, use_container_width=True)


    # --- Pestaña 2: Análisis de Inflación ---
    with tab2:
        st.header("Tendencias Inflacionarias en ALC (2000-2023)")
        st.markdown(f"El mapa de calor inferior muestra la Tasa de Inflación anual para toda la región, con un límite de escala en **{max_inflation_limit:.1f}%** (controlado por el *sidebar*). El segundo gráfico enfoca los **países *outliers*** (Haití, Venezuela, Surinam) para un análisis de alta volatilidad.")

        # --- Heatmap general de Inflación ---
        st.subheader("Inflación Anual por País (Mapa de Calor)")

        # Pivotear los datos de inflación
        heatmap_data = df_main.pivot_table(
            index='country_name',
            columns='year',
            values='inflacion'
        )

        # Reemplazar NaN con 0 para visualización
        heatmap_data = heatmap_data.fillna(0)

        fig_heatmap = go.Figure(data=go.Heatmap(
                z=heatmap_data.values,
                x=heatmap_data.columns,
                y=heatmap_data.index,
                colorscale='Viridis',
                zmin=heatmap_data.values.min(),
                # Aplicamos el filtro del sidebar (max_inflation_limit)
                zmax=max_inflation_limit 
        ))

        fig_heatmap.update_layout(
            title='Tasa de Inflación Anual (%): ALC (2000-2023)',
            xaxis_title='Año',
            yaxis_title='País',
            height=800,
            margin=dict(t=50, b=50, l=20, r=20)
        )
        st.plotly_chart(fig_heatmap, use_container_width=True)


        # --- Heatmap de Outliers de Inflación (Haití, Venezuela, Surinam) ---
        st.subheader("Foco en Países con Inflación Extrema (2010-2023)")
        st.markdown("Las dinámicas inflacionarias en estos tres países exceden el rango común regional. (Escala máxima fija en 200%).")

        if not df_outliers_inflation.empty:
            # Preparar datos para el heatmap de outliers
            heatmap_out = df_outliers_inflation.pivot_table(
                index="country_name",
                columns="year",
                values="inflation_percent"
            )

            fig_outlier_heatmap = go.Figure(data=go.Heatmap(
                    z=heatmap_out.values,
                    x=heatmap_out.columns,
                    y=heatmap_out.index,
                    colorscale='Hot',
                    zmin=0,
                    zmax=200 # Se mantiene fijo para mostrar la escala extrema
            ))

            fig_outlier_heatmap.update_layout(
                title='Inflación Anual – Haití, Venezuela y Surinam (2010-2023)',
                xaxis_title='Año',
                yaxis_title='País',
                height=300,
                margin=dict(t=50, b=50, l=20, r=20)
            )
            st.plotly_chart(fig_outlier_heatmap, use_container_width=True)
        else:
            st.warning("No se pudieron cargar los datos de outliers de inflación.")


    # --- Pestaña 3: Anomalía del PIB ---
    with tab3:
        st.header("Divergencia Extrema: Guyana (Crecimiento) vs. Venezuela (Contracción)")
        st.markdown("""
            El PIB Total de **Guyana** ha mostrado un crecimiento anómalo, disparándose después de **2020** debido al inicio de la explotación masiva de reservas de petróleo.
            En contraste, **Venezuela** ha experimentado una profunda recesión durante la última década.
            *(Nota: Este gráfico muestra el PIB Total en Millones de USD, no per cápita.)*
        """)

        if not df_outliers_gdp.empty:
            fig_gdp_anomaly = px.line(
                df_outliers_gdp,
                x='year',
                y='pib_millones',
                color='country_name',
                title='PIB Total (Millones USD) de Guyana vs. Venezuela (2010-2023)',
                labels={'year': 'Año', 'pib_millones': 'PIB Total (Millones USD)', 'country_name': 'País'},
                markers=True
            )

            # Ajuste de anotación para resaltar el inicio de la anomalía de Guyana
            fig_gdp_anomaly.add_vline(
                x=2020, 
                line_width=1, 
                line_dash="dash", 
                line_color="gray", 
                annotation_text="Inicio de la Explosión del PIB de Guyana", 
                annotation_position="top left"
            )
            
            fig_gdp_anomaly.update_layout(
                xaxis_title="Año",
                yaxis_title="PIB Total (Millones USD)",
                hovermode="x unified",
                yaxis_tickformat="$,.0f",
                margin=dict(t=50, b=50, l=20, r=20)
            )
            st.plotly_chart(fig_gdp_anomaly, use_container_width=True)
        else:
            st.warning("No se pudieron cargar los datos de la anomalía del PIB de Guyana y Venezuela.")
            
    # --- Pestaña 4: Vista Global (Mapa Mundial) ---
    with tab4:
        st.header("🗺️ PIB Total Global (Último Año Disponible: " + str(df_global['year'].max()) + ")")
        st.markdown("Este mapa de calor mundial (Choropleth) muestra la distribución del PIB Total (Millones USD) por país.")
        
        if not df_global.empty:
            
            fig_map = px.choropleth(
                df_global,
                locations="country_code",
                color="pib_millones",
                hover_name="country_name",
                color_continuous_scale=px.colors.sequential.Plasma,
                title="PIB Total Mundial (Millones USD)",
                labels={'pib_millones': 'PIB Total (Millones USD)', 'country_name': 'País'}
            )

            fig_map.update_layout(
                margin={"r":0,"t":50,"l":0,"b":0}
            )
            
            st.plotly_chart(fig_map, use_container_width=True)

            # Opcional: Mostrar los datos brutos del mapa
            with st.expander("Ver Datos del Mapa Mundial"):
                st.dataframe(df_global[['country_name', 'pib_millones', 'year']].sort_values(by='pib_millones', ascending=False))
        else:
            st.warning("No se pudieron cargar los datos globales para el mapa mundial.")

        # --- Sección de Datos Brutos (Opcional) ---
        st.markdown("---")
        with st.expander("Ver Datos Completos de ALC (2000-2023)"):
            st.dataframe(df_main)