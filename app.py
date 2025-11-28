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
    Establece la conexión a la base de datos y ejecuta las consultas.
    CORRECCIÓN: Se arregla la fórmula matemática de la Tasa de Cambio Implícita.
    """
    try:
        conn = sqlite3.connect(DB_FILE)

        # 1. Consulta principal (ALC):
        # CORRECCIÓN DE FÓRMULA:
        # Tasa = PIB Moneda Local / (PIB Millones USD * 1,000,000)
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
                -- Dividimos el PIB Local entre el PIB USD (convertido de millones a unidades completas)
                CASE
                    WHEN w.gdp_current_million IS NULL OR w.gdp_current_million = 0
                    THEN NULL
                    ELSE w.gdp_current_local / (w.gdp_current_million * 1000000.0)
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
            costo_moneda_local_usd IS NOT NULL AND costo_moneda_local_usd > 0 -- Filtrar solo datos válidos
        ORDER BY
            country_name, year;
        """
        df_main = pd.read_sql_query(query_main, conn)
        
        # Calcular la Balanza Comercial Neta
        if 'exportaciones_percent' in df_main.columns and 'importaciones_percent' in df_main.columns:
             df_main['balanza_comercial_neta'] = df_main['exportaciones_percent'] - df_main['importaciones_percent']


        # 2. Consulta de Datos Globales para el Mapa Choropleth (Último Año)
        query_global = """
        SELECT
            g.country_name,
            g.country_code,
            w.year,
            w.gdp_current_million AS pib_millones
        FROM
            fact_wide w
        JOIN
            dim_geo g ON w.country_code = g.country_code
        WHERE
            w.year = (SELECT MAX(year) FROM fact_wide)
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
        return df_main, df_outliers_inflation, df_outliers_gdp, df_global
    except Exception as e:
        st.error(f"Error al conectar o consultar la base de datos: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# La llamada a la función
df_main, df_outliers_inflation, df_outliers_gdp, df_global = get_data_from_db()

# --- Título y Descripción ---
st.title("🌎 Dashboard Económico de América Latina y el Caribe (ALC)")
st.markdown("Este *dashboard* presenta tendencias de **PIB Total**, **Inflación**, **Comercio Exterior**, **Crecimiento Anual** y **Tasa de Cambio Implícita** para países de América Latina y el Caribe, utilizando datos del Banco Mundial.")
st.warning("⚠️ **Advertencia:** La métrica de **PIB** mostrada por defecto es el **PIB Total (en Millones de USD)**.")


if df_main.empty:
    st.warning("No se pudieron cargar los datos de la base de datos.")
else:
    # --- Barra Lateral (Filtros) ---
    st.sidebar.header("Filtros de Visualización")

    # Selector de Indicador Principal
    indicator_options = {
        # Como los datos ahora son normales, podemos usar formato decimal estándar (,.2f) 
        # O mantener .2E si prefieres notación científica. Lo cambiaré a decimal legible.
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

    indicator_key = st.sidebar.selectbox(
        "Selecciona el Indicador Principal:",
        sorted_indicator_keys,
        index=1 
    )

    indicator_meta = indicator_options[indicator_key]
    y_col = indicator_meta['col']
    y_label = indicator_meta['label']
    value_format = indicator_meta['format']
    unit = indicator_meta['unit']
    title_kpi = indicator_key.split(' [')[0] 

    # Slider de rango de años
    min_year = int(df_main['year'].min())
    max_year = int(df_main['year'].max())
    year_range = st.sidebar.slider(
        "Rango de Años para Gráficos:",
        min_value=min_year,
        max_value=max_year,
        value=(2010, max_year)
    )

    # Filtro por país
    available_countries = sorted(df_main['country_name'].unique().tolist())
    default_countries = ['Colombia', 'Panama', 'Brazil', 'Chile', 'Mexico', 'Argentina']
    default_countries = [c for c in default_countries if c in available_countries]

    selected_countries = st.sidebar.multiselect(
        "Selecciona Países para el Gráfico de Líneas:",
        available_countries,
        default=default_countries
    )
    
    # EXCLUSIÓN DE VENEZUELA (Sigue siendo útil)
    exclude_countries = []
    if y_col == 'costo_moneda_local_usd':
        st.sidebar.markdown("---")
        st.sidebar.subheader("⚠️ Filtro de Anomalías (Tasa Implícita)")
        
        exclude_venezuela = st.sidebar.checkbox(
            "Excluir Venezuela (RB) del Gráfico de Líneas", 
            value=True, 
            help="Venezuela puede tener tasas extremadamente altas debido a la inflación."
        )
        if exclude_venezuela:
            exclude_countries.append('Venezuela, RB')
    
    # Slider Heatmap
    st.sidebar.markdown("---")
    st.sidebar.subheader("Opciones de Heatmap")
    max_inflation_limit = st.sidebar.slider(
        "Límite Superior del Heatmap de Inflación (%)",
        min_value=10.0,
        max_value=100.0,
        value=30.0,
        step=5.0
    )


    # --- Pestañas ---
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Resumen y Tendencias", "🔥 Análisis de Inflación", "📈 Anomalías del PIB", "🗺️ Vista Global"])

    # Cálculos métricas
    df_filtered = df_main[
        (df_main['year'] >= year_range[0]) & (df_main['year'] <= year_range[1])
    ]
    latest_year = df_filtered['year'].max()
    df_latest = df_main[df_main['year'] == latest_year]

    if y_col in df_latest.columns:
        alc_average = df_latest[y_col].dropna().mean()
    else:
        alc_average = np.nan

    # --- Pestaña 1 ---
    with tab1:
        st.header("Análisis de Indicadores Clave")
        col_kpi, col_spacer, col_desc = st.columns([1, 0.1, 2])

        with col_kpi:
            st.subheader(f"Métrica Regional ({latest_year})")
            
            if pd.isna(alc_average):
                display_value = "N/A"
            else:
                display_value = f"{alc_average:{value_format}}"
                if 'E' in value_format.upper():
                    display_value = display_value + unit
                elif unit == '$ ':
                    display_value = unit.strip() + ' ' + display_value
                elif unit == ' / USD':
                    display_value = display_value + unit
                else:
                    display_value = display_value + unit
            
            st.metric(label=title_kpi, value=display_value, delta_color="off")
            st.markdown(f"*(Cifra promedio para todos los países de ALC en {latest_year}.)*")
        
        with col_desc:
            st.markdown("Utiliza el menú lateral para seleccionar el indicador principal y el rango de años de interés.")
        
        st.markdown("---")
        col_line, col_box = st.columns(2)

        with col_line:
            st.subheader(f"Tendencia de {title_kpi}")
            df_plot_line = df_filtered[df_filtered['country_name'].isin(selected_countries)]

            if exclude_countries:
                 df_plot_line = df_plot_line[~df_plot_line['country_name'].isin(exclude_countries)]

            if df_plot_line.empty:
                 st.info("Selecciona al menos un país y un rango de años válido.")
            else:
                fig_line = px.line(
                    df_plot_line,
                    x='year', y=y_col, color='country_name',
                    title=f'Evolución Anual de {y_label} por País',
                    labels={'year': 'Año', y_col: y_label, 'country_name': 'País'},
                    markers=True
                )
                
                # Configuración dinámica del eje Y
                if 'E' in value_format.upper():
                     y_tick_format = value_format
                elif unit == '$ ':
                    y_tick_format = "$,.0f" 
                elif unit == ' %':
                    y_tick_format = ".1f"
                elif unit == ' / USD':
                    y_tick_format = ",.2f"
                else:
                    y_tick_format = ",.0f"

                fig_line.update_layout(xaxis_title="Año", yaxis_title=y_label, hovermode="x unified", margin=dict(t=50, b=50, l=20, r=20))
                fig_line.update_yaxes(tickformat=y_tick_format)
                fig_line.update_xaxes(rangeslider_visible=True)
                st.plotly_chart(fig_line, use_container_width=True)

        with col_box:
            st.subheader(f"Distribución de {title_kpi}")
            
            # Configuración dinámica del eje Y para box plot
            if 'E' in value_format.upper():
                y_tick_format_box = value_format
            elif unit == '$ ':
                y_tick_format_box = "$,.0f" 
            elif unit == ' %':
                y_tick_format_box = ".1f"
            elif unit == ' / USD':
                y_tick_format_box = ",.2f"
            else:
                y_tick_format_box = ",.0f"

            fig_box = px.box(
                df_filtered, x='country_name', y=y_col,
                title=f'Distribución de {y_label} por País ({year_range[0]}-{year_range[1]})',
                labels={'country_name': 'País', y_col: y_label}, notched=True
            )
            fig_box.update_yaxes(rangemode='normal', tickformat=y_tick_format_box)
            fig_box.update_xaxes(showticklabels=False, title_text="Países de ALC (Ver países en Hover)")
            fig_box.update_layout(margin=dict(t=50, b=50, l=20, r=20), hovermode="closest")
            st.plotly_chart(fig_box, use_container_width=True)


    # --- Pestaña 2 ---
    with tab2:
        st.header("Tendencias Inflacionarias en ALC")
        heatmap_data = df_main.pivot_table(index='country_name', columns='year', values='inflacion').fillna(0)
        
        fig_heatmap = go.Figure(data=go.Heatmap(
                z=heatmap_data.values, x=heatmap_data.columns, y=heatmap_data.index,
                colorscale='Viridis', zmin=heatmap_data.values.min(), zmax=max_inflation_limit 
        ))
        fig_heatmap.update_layout(title='Tasa de Inflación Anual (%)', height=800)
        st.plotly_chart(fig_heatmap, use_container_width=True)

        if not df_outliers_inflation.empty:
            heatmap_out = df_outliers_inflation.pivot_table(index="country_name", columns="year", values="inflation_percent")
            fig_outlier_heatmap = go.Figure(data=go.Heatmap(
                    z=heatmap_out.values, x=heatmap_out.columns, y=heatmap_out.index,
                    colorscale='Hot', zmin=0, zmax=200
            ))
            fig_outlier_heatmap.update_layout(title='Inflación Extrema (Haití, Venezuela, Surinam)', height=300)
            st.plotly_chart(fig_outlier_heatmap, use_container_width=True)

    # --- Pestaña 3 ---
    with tab3:
        st.header("Anomalía del PIB: Guyana vs Venezuela")
        if not df_outliers_gdp.empty:
            fig_gdp_anomaly = px.line(
                df_outliers_gdp, x='year', y='pib_millones', color='country_name',
                title='PIB Total (Millones USD): Guyana vs Venezuela',
                markers=True
            )
            fig_gdp_anomaly.add_vline(x=2020, line_dash="dash", line_color="gray", annotation_text="Boom Petrolero Guyana")
            fig_gdp_anomaly.update_layout(yaxis_tickformat="$,.0f")
            st.plotly_chart(fig_gdp_anomaly, use_container_width=True)

    # --- Pestaña 4 ---
    with tab4:
        st.header("🗺️ PIB Total Global (Escala Logarítmica)")
        if not df_global.empty:
            # CORRECCIÓN: Usar LOG10 para el mapa
            df_global_plot = df_global.copy()
            df_global_plot['pib_log'] = np.log10(df_global_plot['pib_millones'].clip(lower=1)) 

            fig_map = px.choropleth(
                df_global_plot, locations="country_code", color="pib_log",
                hover_name="country_name",
                hover_data={'pib_millones': ':, .0f', 'pib_log': False}, 
                color_continuous_scale=px.colors.sequential.Plasma,
                title="PIB Total Mundial (Log10)",
                labels={'pib_log': 'Log10 del PIB'}
            )
            fig_map.update_traces(colorbar=dict(title="Log10 PIB", tickformat=".1f"))
            fig_map.update_layout(margin={"r":0,"t":50,"l":0,"b":0})
            st.plotly_chart(fig_map, use_container_width=True)
            
        st.markdown("---")
        with st.expander("Ver Datos Completos"):
            st.dataframe(df_main)