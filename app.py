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
def get_data_from_db():
    """
    Establece la conexión a la base de datos y ejecuta las consultas,
    utilizando la tabla 'fact_wide' y realizando la unión con 'dim_geo'.
    Se utiliza 'gdp_current_million' como proxy para el PIB debido a la estructura actual de 'fact_wide'.
    """
    try:
        conn = sqlite3.connect(DB_FILE)

        # Consulta principal: Usa gdp_current_million como proxy para el PIB
        query_main = """
        SELECT
            g.country_name,
            w.year,
            w.gdp_current_million AS gdp_per_capita, -- USANDO PIB TOTAL (MILLONES USD) COMO PROXY
            w.inflation_percent
        FROM
            fact_wide w
        JOIN
            dim_geo g ON w.country_code = g.country_code
        WHERE
            g.region LIKE 'Latin America%' AND w.year >= 2000
        ORDER BY
            g.country_name, w.year;
        """
        df_main = pd.read_sql_query(query_main, conn)

        # Consulta para outliers de INFLACIÓN: Usa inflación_percent
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

        # Consulta para la anomalía del PIB: Usa gdp_current_million
        OUTLIERS_GDP = ('Guyana', 'Venezuela, RB')
        query_outliers_gdp = f"""
        SELECT
            g.country_name,
            w.year,
            w.gdp_current_million AS gdp_per_capita -- USANDO PIB TOTAL (MILLONES USD) COMO PROXY
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
        return df_main, df_outliers_inflation, df_outliers_gdp
    except Exception as e:
        # En caso de error, mostramos un mensaje y devolvemos DataFrames vacíos
        st.error(f"Error al conectar o consultar la base de datos: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# La llamada a la función ahora retorna 3 DataFrames
df_main, df_outliers_inflation, df_outliers_gdp = get_data_from_db()

# --- Título y Descripción ---
st.title("🌎 Dashboard Económico de América Latina y el Caribe (ALC)")
st.markdown("Este *dashboard* presenta tendencias del **PIB Total (Millones de USD)** y la **Tasa de Inflación** para países de América Latina y el Caribe, utilizando datos del Banco Mundial.")
st.warning("⚠️ **Advertencia:** Debido a la estructura de la tabla 'fact_wide' proporcionada, la métrica de **PIB** mostrada es el **PIB Total (en Millones de USD)** en lugar del PIB per Cápita. Esto puede alterar el significado de algunos gráficos.")


# Verificar si se cargaron datos correctamente
if df_main.empty:
    st.warning("No se pudieron cargar los datos de la base de datos. Por favor, verifica que el archivo 'db/project.db' sea accesible y la consulta SQL sea correcta.")
else:
    # --- Barra Lateral (Filtros) ---
    st.sidebar.header("Filtros de Visualización")

    # Selector de Indicador Principal
    indicator = st.sidebar.selectbox(
        "Selecciona el Indicador Principal:",
        ("PIB Total (Millones USD, actual)", "Tasa de Inflación (% Anual)"),
        index=0
    )

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
    # Asegurar que los países por defecto están en la lista
    default_countries = [c for c in default_countries if c in available_countries]

    selected_countries = st.sidebar.multiselect(
        "Selecciona Países para el Gráfico de Líneas:",
        available_countries,
        default=default_countries
    )

    # Slider para limitar la escala de Inflación del Heatmap General (NUEVO CONTROL)
    st.sidebar.markdown("---")
    st.sidebar.subheader("Opciones de Heatmap")
    max_inflation_limit = st.sidebar.slider(
        "Límite Superior del Heatmap de Inflación (%)",
        min_value=10.0,
        max_value=100.0,
        value=30.0,
        step=5.0
    )
    st.sidebar.markdown("*(Aplica al Heatmap General en la pestaña 'Análisis de Inflación')*")


    # --- Definición de Pestañas ---
    tab1, tab2, tab3 = st.tabs(["📊 Resumen y Tendencias", "🔥 Análisis de Inflación", "📈 Anomalías del PIB"])

    # --- Lógica de cálculo de métricas ---
    df_filtered = df_main[
        (df_main['year'] >= year_range[0]) & (df_main['year'] <= year_range[1])
    ]
    
    # Calcular el promedio regional (ALC) para el último año disponible
    latest_year = df_filtered['year'].max()
    df_latest = df_main[df_main['year'] == latest_year]

    # Usamos los nombres de columna simples en Python
    if indicator == "PIB Total (Millones USD, actual)":
        y_col = 'gdp_per_capita' # Nombre de columna de Pandas, que ahora contiene PIB Total
        y_label = 'PIB Total (Millones USD)'
        value_format = ",.0f" # CORREGIDO: Se elimina el '$' del especificador de formato
        title_kpi = "PIB Total Promedio ALC"
    else:
        y_col = 'inflation_percent'
        y_label = 'Inflación (% Anual)'
        value_format = ".1f"
        title_kpi = "Tasa de Inflación Promedio ALC"

    alc_average = df_latest[y_col].mean()

    # --- Pestaña 1: Resumen y Tendencias ---
    with tab1:
        st.header("Análisis de Indicadores Clave")
        
        col_kpi, col_spacer, col_desc = st.columns([1, 0.1, 2])

        with col_kpi:
            st.subheader(f"Métrica Regional ({latest_year})")
            
            # Asegurar que la cifra no es NaN y formatearla
            if pd.isna(alc_average):
                display_value = "N/A"
            else:
                display_value = f"{alc_average:{value_format}}"
                
                # CORREGIDO: Se añade el símbolo de moneda ($)
                if y_col == 'gdp_per_capita':
                    display_value = "$ " + display_value
                
                if y_col == 'inflation_percent':
                    display_value += " %"
            
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
            st.subheader(f"Tendencia de {indicator}")

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
                    title=f'Evolución Anual del {y_label} por País',
                    labels={'year': 'Año', y_col: y_label, 'country_name': 'País'},
                    markers=True
                )
                
                fig_line.update_layout(
                    xaxis_title="Año",
                    yaxis_title=y_label,
                    hovermode="x unified",
                    margin=dict(t=50, b=50, l=20, r=20)
                )
                fig_line.update_yaxes(tickformat="$,.0f" if y_col == 'gdp_per_capita' else ".1f")
                st.plotly_chart(fig_line, use_container_width=True)

        # --- Gráfico 2: Distribución (Box Plot) ---
        with col_box:
            st.subheader(f"Distribución de {indicator}")
            
            if y_col == 'gdp_per_capita':
                fig_box = px.box(
                    df_filtered,
                    x='country_name',
                    y='gdp_per_capita',
                    title=f'Distribución de PIB Total por País ({year_range[0]}-{year_range[1]})',
                    labels={'country_name': 'País', 'gdp_per_capita': 'PIB Total (Millones USD)'},
                    notched=True
                )
                fig_box.update_yaxes(rangemode='normal', tickformat="$,.0f")
            else:
                fig_box = px.box(
                    df_filtered,
                    x='country_name',
                    y='inflation_percent',
                    title=f'Distribución de Tasa de Inflación por País ({year_range[0]}-{year_range[1]})',
                    labels={'country_name': 'País', 'inflation_percent': 'Inflación (% Anual)'},
                    notched=True
                )
                fig_box.update_yaxes(rangemode='normal', tickformat=".1f")

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
            values='inflation_percent'
        )

        # Reemplazar NaN con la media de la columna o un valor bajo para visualización (0 para inflación)
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
            # Preparar datos para el heatmap de outliers (como en el notebook)
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
                y='gdp_per_capita',
                color='country_name',
                title='PIB Total (Millones USD) de Guyana vs. Venezuela (2010-2023)',
                labels={'year': 'Año', 'gdp_per_capita': 'PIB Total (Millones USD)', 'country_name': 'País'},
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
            
        # --- Sección de Datos Brutos (Opcional, en la última pestaña) ---
        st.markdown("---")
        with st.expander("Ver Datos Completos de ALC (2000-2023)"):
            st.dataframe(df_main)