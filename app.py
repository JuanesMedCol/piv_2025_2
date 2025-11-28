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

# Definir los agregados y territorios a excluir como una TUPLA
AGREGADOS_A_EXCLUIR = (
    'Latin America & Caribbean (excluding high income)',
    'Latin America & Caribbean (IBRD & IDA)',
    'Latin America & Caribbean',
    'U.S. Virgin Islands'
)

# Definiciones de outliers como tuplas (solo para SQL)
OUTLIERS_INFLATION = ('Haiti', 'Venezuela, RB', 'Suriname')
OUTLIERS_GDP = ('Guyana', 'Venezuela, RB')

@st.cache_data
def get_data_from_db():
    """
    Establece la conexión a la base de datos y ejecuta las consultas.
    """
    exclusion_placeholders = ','.join(['?'] * len(AGREGADOS_A_EXCLUIR))
    outlier_placeholders_inf = ','.join(['?'] * len(OUTLIERS_INFLATION))
    outlier_placeholders_gdp = ','.join(['?'] * len(OUTLIERS_GDP))
    
    try:
        conn = sqlite3.connect(DB_FILE)

        # 1. Consulta principal (ALC): Contiene todos los datos limpios de ALC.
        query_main = f"""
        WITH data_cte AS (
            SELECT
                g.country_name,
                g.country_code,
                w.year,
                w.gdp_current_million AS pib_millones,
                w.inflation_percent AS inflacion,
                w.exports_percent_gdp AS exportaciones_percent,
                w.imports_percent_gdp AS importaciones_percent,
                w.gdp_current_local AS pib_monedalocal,
                w.gdp_growth_percent AS crecimiento_anual,
                CASE
                    WHEN w.gdp_current_million IS NULL OR w.gdp_current_million = 0
                    THEN NULL
                    ELSE ((w.gdp_current_local / 1000000.0) / w.gdp_current_million)
                END AS costo_moneda_local_usd
            FROM
                fact_wide w
            JOIN
                dim_geo g ON w.country_code = g.country_code
            WHERE
                g.region LIKE 'Latin America%'
                AND w.year >= 2000
                AND g.country_name NOT IN ({exclusion_placeholders})
        )
        SELECT * FROM data_cte
        WHERE
            costo_moneda_local_usd IS NOT NULL AND costo_moneda_local_usd > 0
        ORDER BY
            country_name, year;
        """
        df_main = pd.read_sql_query(query_main, conn, params=AGREGADOS_A_EXCLUIR)
        
        # Calcular la Balanza Comercial Neta
        if 'exportaciones_percent' in df_main.columns and 'importaciones_percent' in df_main.columns:
             df_main['balanza_comercial_neta'] = df_main['exportaciones_percent'] - df_main['importaciones_percent']


        # 2. Consulta para outliers de INFLACIÓN
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
            AND g.country_name IN ({outlier_placeholders_inf})
            AND w.year BETWEEN 2010 AND 2023
            AND g.country_name NOT IN ({exclusion_placeholders})
        ORDER BY
            g.country_name, w.year;
        """
        df_outliers_inflation = pd.read_sql_query(query_outliers_inflation, conn, params=OUTLIERS_INFLATION + AGREGADOS_A_EXCLUIR)

        # 3. Consulta para la anomalía del PIB
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
            AND g.country_name IN ({outlier_placeholders_gdp})
            AND w.year BETWEEN 2010 AND 2023
            AND g.country_name NOT IN ({exclusion_placeholders})
        ORDER BY
            g.country_name, w.year;
        """
        df_outliers_gdp = pd.read_sql_query(query_outliers_gdp, conn, params=OUTLIERS_GDP + AGREGADOS_A_EXCLUIR)

        conn.close()
        return df_main, df_outliers_inflation, df_outliers_gdp
    except Exception as e:
        st.error(f"Error al conectar o consultar la base de datos: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# La llamada a la función ahora retorna 3 DataFrames
df_main, df_outliers_inflation, df_outliers_gdp = get_data_from_db()

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
        "Costo Moneda Local/USD (Tasa Implícita) [costo_moneda_local_usd]": {'col': 'costo_moneda_local_usd', 'label': 'Costo Moneda Local por 1 USD', 'format': ",.2f", 'unit': ' / USD', 'category': 'Moneda'},
        "PIB Total (Millones USD) [pib_millones]": {'col': 'pib_millones', 'label': 'PIB Total (Millones USD)', 'format': ",.0f", 'unit': '$ ', 'category': 'PIB'},
        "PIB (Moneda Local) [pib_monedalocal]": {'col': 'pib_monedalocal', 'label': 'PIB (Moneda Local)', 'format': ",.0f", 'unit': '', 'category': 'PIB'},
        "Crecimiento Anual (% PIB) [crecimiento_anual]": {'col': 'crecimiento_anual', 'label': 'Crecimiento Anual (% PIB)', 'format': ".1f", 'unit': ' %', 'category': 'PIB'},
        "Balanza Comercial Neta (% PIB) [importaciones_vs_exportaciones]": {'col': 'balanza_comercial_neta', 'label': 'Balanza Comercial Neta (% PIB)', 'format': ".1f", 'unit': ' %', 'category': 'Comercio'},
        "Exportaciones (% PIB) [exportaciones]": {'col': 'exportaciones_percent', 'label': 'Exportaciones (% PIB)', 'format': ".1f", 'unit': ' %', 'category': 'Comercio'},
        "Importaciones (% PIB) [importaciones]": {'col': 'importaciones_percent', 'label': 'Importaciones (% PIB)', 'format': ".1f", 'unit': ' %', 'category': 'Comercio'},
        "Tasa de Inflación (% Anual) [inflacion]": {'col': 'inflacion', 'label': 'Inflación (% Anual)', 'format': ".1f", 'unit': ' %', 'category': 'Precios'},
    }
    
    sorted_indicator_keys = sorted(indicator_options.keys(), key=lambda k: indicator_options[k]['category'] + k)

    indicator_key = st.sidebar.selectbox("Selecciona el Indicador Principal:", sorted_indicator_keys, index=1)

    indicator_meta = indicator_options[indicator_key]
    y_col = indicator_meta['col']
    y_label = indicator_meta['label']
    value_format = indicator_meta['format']
    unit = indicator_meta['unit']
    title_kpi = indicator_key.split(' [')[0]

    min_year = int(df_main['year'].min())
    max_year = int(df_main['year'].max())
    year_range = st.sidebar.slider("Rango de Años para Gráficos:", min_value=min_year, max_value=max_year, value=(2010, max_year))

    available_countries = sorted(df_main['country_name'].unique().tolist())
    default_countries = ['Colombia', 'Panama', 'Brazil', 'Chile', 'Mexico', 'Argentina']
    default_countries = [c for c in default_countries if c in available_countries]

    selected_countries = st.sidebar.multiselect("Selecciona Países para el Gráfico de Líneas:", available_countries, default=default_countries)
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("Opciones Adicionales")

    # Filtro para el Box Plot (Outliers)
    exclude_outliers_box_plot = st.sidebar.checkbox(
        "Excluir Venezuela (RB) de la Distribución", 
        value=True, 
        help="Venezuela (RB) presenta valores atípicos extremos para inflación y tasas de cambio, lo que distorsiona la escala del gráfico de distribución (Box Plot)."
    )
    
    st.sidebar.subheader("Opciones de Heatmap")
    max_inflation_limit = st.sidebar.slider("Límite Superior del Heatmap de Inflación (%)", min_value=10.0, max_value=100.0, value=30.0, step=5.0)

    # --- Definición de Pestañas ---
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Resumen y Tendencias", "🔥 Análisis de Inflación", "📈 Anomalías del PIB", "🗺️ Vista Global"])

    # --- Lógica de cálculo de métricas ---
    df_filtered = df_main[
        (df_main['year'] >= year_range[0]) & (df_main['year'] <= year_range[1])
    ]
    
    latest_year = df_filtered['year'].max()
    df_latest = df_main[df_main['year'] == latest_year] 

    if y_col in df_latest.columns:
        # Aquí se aplica la exclusión de Venezuela (RB) para el KPI
        df_latest_kpi = df_latest[df_latest['country_name'] != 'Venezuela, RB']
        alc_average = df_latest_kpi[y_col].dropna().mean()
    else:
        alc_average = np.nan

    # --- CONFIGURACIÓN DE ESCALA ---
    # Aplicar escala logarítmica si el indicador es el costo de la moneda local/USD
    log_scale = y_col == 'costo_moneda_local_usd'

    # --- Pestaña 1: Resumen y Tendencias ---
    with tab1:
        st.header("Análisis de Indicadores Clave")
        
        col_kpi, col_spacer, col_desc = st.columns([1, 0.1, 2])

        with col_kpi:
            st.subheader(f"Métrica Regional ({latest_year})")
            
            if pd.isna(alc_average):
                display_value = "N/A"
            else:
                display_value = f"{alc_average:{value_format}}"
                
                if unit == '$ ':
                    display_value = unit.strip() + ' ' + display_value
                elif unit == ' / USD':
                    display_value = display_value + unit
                else:
                    display_value = display_value + unit
            
            st.metric(label=title_kpi, value=display_value, delta_color="off")
            st.markdown(f"*(Cifra promedio para ALC excluyendo a Venezuela en {latest_year}.)*")
        
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
            
            if log_scale:
                st.info("ℹ️ **Escala Logarítmica:** El eje Y usa una escala logarítmica para manejar el amplio rango de valores (ej. Venezuela).")
            st.markdown("_*Usa el Range Slider inferior para hacer zoom en períodos específicos.*_")

            df_plot_line = df_filtered[df_filtered['country_name'].isin(selected_countries)]
            
            if df_plot_line.empty:
                 st.info("Selecciona al menos un país y un rango de años válido para mostrar la tendencia.")
            else:
                fig_line = px.line(
                    df_plot_line, x='year', y=y_col, color='country_name',
                    title=f'Evolución Anual de {y_label} por País',
                    labels={'year': 'Año', y_col: y_label, 'country_name': 'País'},
                    markers=True,
                    log_y=log_scale # APLICACIÓN DE ESCALA LOGARÍTMICA
                )
                
                if unit == '$ ':
                    y_tick_format = "$,.0f" 
                elif unit == ' %':
                    y_tick_format = ".1f"
                elif unit == ' / USD':
                    y_tick_format = ",.2f"
                else:
                    y_tick_format = ",.0f"
                
                # Para la escala logarítmica, el formato de tick no es útil
                if not log_scale:
                    fig_line.update_yaxes(tickformat=y_tick_format)

                fig_line.update_layout(xaxis_title="Año", yaxis_title=y_label, hovermode="x unified", margin=dict(t=50, b=50, l=20, r=20))
                
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
            
            # Aplicar el filtro de países seleccionados
            df_box_plot = df_filtered.copy()
            
            # 1. Aplicar el filtro de países seleccionados
            if selected_countries:
                df_box_plot = df_box_plot[df_box_plot['country_name'].isin(selected_countries)]

            # 2. Aplicar la exclusión opcional de Venezuela
            if exclude_outliers_box_plot:
                df_box_plot = df_box_plot[df_box_plot['country_name'] != 'Venezuela, RB']


            if df_box_plot.empty:
                st.info("No hay datos disponibles para la distribución con los filtros aplicados.")
            else:
                if unit == '$ ':
                    y_tick_format_box = "$,.0f" 
                elif unit == ' %':
                    y_tick_format_box = ".1f"
                elif unit == ' / USD':
                    y_tick_format_box = ",.2f"
                else:
                    y_tick_format_box = ",.0f"


                fig_box = px.box(
                    df_box_plot, 
                    x='country_name', y=y_col,
                    title=f'Distribución de {y_label} por País ({year_range[0]}-{year_range[1]})',
                    labels={'country_name': 'País', y_col: y_label}, notched=True,
                    log_y=log_scale # APLICACIÓN DE ESCALA LOGARÍTMICA
                )
                
                fig_box.update_yaxes(rangemode='normal')
                
                # Solo aplicar el formato si no es escala logarítmica
                if not log_scale:
                    fig_box.update_yaxes(tickformat=y_tick_format_box)


                # Ajuste de Eje X: Mostrar nombres si la selección es manejable (<= 10 países)
                num_countries_in_box_plot = df_box_plot['country_name'].nunique()
                
                if num_countries_in_box_plot > 10 or num_countries_in_box_plot == 0:
                    fig_box.update_xaxes(showticklabels=False, title_text="Países seleccionados (Ver nombres en Hover)")
                else:
                    fig_box.update_xaxes(showticklabels=True, title_text="País")
                    fig_box.update_xaxes(tickangle=45) 

                fig_box.update_layout(margin=dict(t=50, b=50, l=20, r=20), hovermode="closest")
                st.plotly_chart(fig_box, use_container_width=True)


    # --- Pestaña 2: Análisis de Inflación ---
    with tab2:
        st.header("Tendencias Inflacionarias en ALC (2000-2023)")
        st.markdown(f"El mapa de calor inferior muestra la Tasa de Inflación anual para toda la región, con un límite de escala en **{max_inflation_limit:.1f}%**.")

        # --- Heatmap general de Inflación ---
        st.subheader("Inflación Anual por País (Mapa de Calor)")

        heatmap_data = df_main.pivot_table(index='country_name', columns='year', values='inflacion').fillna(0)

        fig_heatmap = go.Figure(data=go.Heatmap(
                z=heatmap_data.values, x=heatmap_data.columns, y=heatmap_data.index,
                colorscale='Viridis', zmin=heatmap_data.values.min(), zmax=max_inflation_limit 
        ))

        fig_heatmap.update_layout(title='Tasa de Inflación Anual (%): ALC (2000-2023)', xaxis_title='Año', yaxis_title='País', height=800)
        st.plotly_chart(fig_heatmap, use_container_width=True)


        # --- Heatmap de Outliers de Inflación (Haití, Venezuela, Surinam) ---
        st.subheader("Foco en Países con Inflación Extrema (2010-2023)")

        if not df_outliers_inflation.empty:
            heatmap_out = df_outliers_inflation.pivot_table(index="country_name", columns="year", values="inflation_percent")

            fig_outlier_heatmap = go.Figure(data=go.Heatmap(
                    z=heatmap_out.values, x=heatmap_out.columns, y=heatmap_out.index,
                    colorscale='Hot', zmin=0, zmax=200
            ))

            fig_outlier_heatmap.update_layout(title='Inflación Anual – Haití, Venezuela y Surinam (2010-2023)', height=300)
            st.plotly_chart(fig_outlier_heatmap, use_container_width=True)
        else:
            st.warning("No se pudieron cargar los datos de outliers de inflación.")


    # --- Pestaña 3: Anomalía del PIB ---
    with tab3:
        st.header("Divergencia Extrema: Guyana (Crecimiento) vs. Venezuela (Contracción)")
        st.markdown("El PIB Total de **Guyana** ha mostrado un crecimiento anómalo... En contraste, **Venezuela** ha experimentado una profunda recesión.")

        if not df_outliers_gdp.empty:
            fig_gdp_anomaly = px.line(
                df_outliers_gdp, x='year', y='pib_millones', color='country_name',
                title='PIB Total (Millones USD) de Guyana vs. Venezuela (2010-2023)',
                labels={'year': 'Año', 'pib_millones': 'PIB Total (Millones USD)', 'country_name': 'País'},
                markers=True
            )

            fig_gdp_anomaly.add_vline(x=2020, line_dash="dash", line_color="gray", annotation_text="Inicio de la Explosión del PIB de Guyana", annotation_position="top left")
            
            fig_gdp_anomaly.update_layout(yaxis_tickformat="$,.0f")
            st.plotly_chart(fig_gdp_anomaly, use_container_width=True)
        else:
            st.warning("No se pudieron cargar los datos de la anomalía del PIB de Guyana y Venezuela.")
            
    # --- Pestaña 4: Vista Global (Mapa Mundial) ---
    with tab4:
        # Generamos df_global_map a partir del df_filtered (que respeta el slider de años)
        if not df_filtered.empty:
            
            map_year = df_filtered['year'].max() 
            
            # Filtramos df_filtered para obtener solo el último año disponible en el rango
            df_global_map = df_filtered[df_filtered['year'] == map_year].copy()
            
            st.header("🗺️ PIB Total Global (Año mostrado: " + str(map_year) + ")")
            st.markdown("Este mapa muestra la distribución del PIB Total (Millones USD). La **escala de color utiliza el logaritmo de base 10 del PIB** para hacer visibles las diferencias entre países con PIB de diferentes órdenes de magnitud.")
            
            # Reaplicación del cálculo logarítmico para el mapa
            df_global_map['pib_log'] = np.log10(df_global_map['pib_millones'].clip(lower=1)) 

            fig_map = px.choropleth(
                df_global_map, locations="country_code", color="pib_log", 
                hover_name="country_name",
                hover_data={'pib_millones': ':, .0f', 'pib_log': False}, 
                color_continuous_scale=px.colors.sequential.Plasma,
                title=f"PIB Total Mundial ({map_year}) - Escala de Color con Logaritmo (Base 10)",
                labels={'pib_log': 'Log10 del PIB'}
            )

            fig_map.update_traces(colorbar=dict(title="Log10 PIB", tickformat=".1f"))
            fig_map.update_layout(margin={"r":0,"t":50,"l":0,"b":0})
            
            st.plotly_chart(fig_map, use_container_width=True)

            with st.expander("Ver Datos del Mapa Mundial"):
                st.dataframe(df_global_map[['country_name', 'pib_millones', 'year']].sort_values(by='pib_millones', ascending=False))
        else:
            st.warning("No hay datos disponibles en el rango de años seleccionado para el mapa mundial.")

        st.markdown("---")
        with st.expander("Ver Datos Completos de ALC (2000-2023)"):
            st.dataframe(df_main)