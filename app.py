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
        # El campo costo_moneda_local_usd fue eliminado de esta consulta
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
                w.gdp_growth_percent AS crecimiento_anual
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

# --- FUNCIÓN DE ANÁLISIS INTELIGENTE ---
def generate_metric_analysis(df, latest_year):
    """Genera un análisis de texto basado en las métricas filtradas, incluyendo mejor, peor y situación general."""
    
    analysis_points = []
    
    # Filtrar solo el último año (excluyendo a Venezuela RB para promedios, ya que distorsiona las medias)
    df_latest_valid = df[(df['year'] == latest_year) & (df['country_name'] != 'Venezuela, RB')].dropna(subset=['crecimiento_anual', 'inflacion', 'balanza_comercial_neta', 'exportaciones_percent', 'importaciones_percent'])
    
    if df_latest_valid.empty:
        return ["No hay datos suficientes para generar un análisis inteligente para este periodo."]
    
    # --- ANÁLISIS DE CRECIMIENTO (CRECIMIENTO ANUAL) ---
    avg_growth = df_latest_valid['crecimiento_anual'].mean()
    
    if not pd.isna(avg_growth):
        country_best_growth = df_latest_valid.loc[df_latest_valid['crecimiento_anual'].nlargest(1).index, 'country_name'].iloc[0] if not df_latest_valid['crecimiento_anual'].empty else 'N/A'
        country_worst_growth = df_latest_valid.loc[df_latest_valid['crecimiento_anual'].nsmallest(1).index, 'country_name'].iloc[0] if not df_latest_valid['crecimiento_anual'].empty else 'N/A'
        
        # 1. Situación General (Resumen Regional/Selección)
        if avg_growth > 3.0:
            analysis_points.append(f"📈 **Crecimiento General Sólido ({latest_year}):** La selección muestra un sólido crecimiento promedio del PIB del **{avg_growth:.1f}%**.")
        elif avg_growth > 0.5:
            analysis_points.append(f"📉 **Crecimiento General Moderado ({latest_year}):** El crecimiento promedio del PIB es moderado, situándose en **{avg_growth:.1f}%**, indicando una expansión lenta.")
        elif avg_growth > 0:
            analysis_points.append(f"🔻 **Crecimiento General Débil ({latest_year}):** El crecimiento promedio del PIB es marginal (**{avg_growth:.1f}%**), lo que sugiere una recuperación frágil.")
        else:
            analysis_points.append(f"🚨 **Contracción General ({latest_year}):** El PIB promedio se ha **contraído** en **{avg_growth:.1f}%**, indicando recesión en gran parte de la selección.")
        
        # 2. Rendimiento Individual (Mejor/Peor)
        analysis_points.append(f"🏆 **Mejor Crecimiento ({latest_year}):** El país con mejor rendimiento fue **{country_best_growth}** con un crecimiento de **{df_latest_valid['crecimiento_anual'].max():.1f}%** del PIB.")
        analysis_points.append(f"⚠️ **Peor Crecimiento ({latest_year}):** El país con menor o peor crecimiento fue **{country_worst_growth}** con **{df_latest_valid['crecimiento_anual'].min():.1f}%** del PIB.")


    # --- ANÁLISIS DE INFLACIÓN (INFLACION) ---
    avg_inflation = df_latest_valid['inflacion'].mean()
    
    if not pd.isna(avg_inflation):
        country_high_inf = df_latest_valid.loc[df_latest_valid['inflacion'].nlargest(1).index, 'country_name'].iloc[0] if not df_latest_valid['inflacion'].empty else 'N/A'
        country_low_inf = df_latest_valid.loc[df_latest_valid['inflacion'].nsmallest(1).index, 'country_name'].iloc[0] if not df_latest_valid['inflacion'].empty else 'N/A'
        
        # 1. Situación General
        if avg_inflation > 15:
            analysis_points.append(f"🔥 **Inflación General Muy Alta ({latest_year}):** El promedio de inflación en la selección es muy elevado (**{avg_inflation:.1f}%**).")
        elif avg_inflation > 5:
            analysis_points.append(f"⚠️ **Inflación General Elevada ({latest_year}):** La inflación promedio (**{avg_inflation:.1f}%**) supera los rangos meta de estabilidad de precios.")
        else:
            analysis_points.append(f"✅ **Inflación General Controlada ({latest_year}):** La inflación promedio se mantiene en niveles manejables (**{avg_inflation:.1f}%**).")
            
        # 2. Rendimiento Individual (Mejor/Peor)
        analysis_points.append(f"📈 **País con Mayor Inflación ({latest_year}):** La mayor tasa se registró en **{country_high_inf}** con **{df_latest_valid['inflacion'].max():.1f}%**.")
        analysis_points.append(f"📉 **País con Menor Inflación ({latest_year}):** El país con la menor inflación fue **{country_low_inf}** con **{df_latest_valid['inflacion'].min():.1f}%**.")

    # --- ANÁLISIS DE COMERCIO (BALANZA COMERCIAL NETA) ---
    avg_trade_balance = df_latest_valid['balanza_comercial_neta'].mean()
    
    if not pd.isna(avg_trade_balance):
        country_best_trade = df_latest_valid.loc[df_latest_valid['balanza_comercial_neta'].nlargest(1).index, 'country_name'].iloc[0] if not df_latest_valid['balanza_comercial_neta'].empty else 'N/A'
        country_worst_trade = df_latest_valid.loc[df_latest_valid['balanza_comercial_neta'].nsmallest(1).index, 'country_name'].iloc[0] if not df_latest_valid['balanza_comercial_neta'].empty else 'N/A'
        
        # 1. Situación General
        if avg_trade_balance > 0.5:
            analysis_points.append(f"💰 **Balanza Comercial: Superávit ({latest_year}):** La Balanza Comercial Neta promedio es positiva (**+{avg_trade_balance:.1f}% del PIB**), indicando que la selección es exportadora neta.")
        elif avg_trade_balance < -0.5:
            analysis_points.append(f"🚢 **Balanza Comercial: Déficit ({latest_year}):** La Balanza Comercial Neta promedio es negativa (**{avg_trade_balance:.1f}% del PIB**), lo que implica una mayor dependencia de las importaciones.")
        else:
            analysis_points.append(f"⚖️ **Balanza Comercial: Neutral ({latest_year}):** La Balanza Comercial Neta es cercana a cero, sugiriendo un equilibrio.")
            
        # 2. Rendimiento Individual (Mejor/Peor)
        analysis_points.append(f"🥇 **Mayor Superávit/Menor Déficit ({latest_year}):** **{country_best_trade}** muestra la mejor balanza comercial con **{df_latest_valid['balanza_comercial_neta'].max():.1f}%** del PIB.")
        analysis_points.append(f"🛑 **Mayor Déficit/Menor Superávit ({latest_year}):** **{country_worst_trade}** muestra la balanza comercial más débil con **{df_latest_valid['balanza_comercial_neta'].min():.1f}%** del PIB.")

    # --- ANÁLISIS DE PIB TOTAL (LÍDER DE LA SELECCIÓN) ---
    # Usar df_latest_valid para PIB total dentro de la selección
    df_latest_pib = df_latest_valid.copy().dropna(subset=['pib_millones'])

    if not df_latest_pib.empty:
        outlier_pib = df_latest_pib.loc[df_latest_pib['pib_millones'].nlargest(1).index, 'country_name'].iloc[0]
        pib_value = df_latest_pib['pib_millones'].max()
        
        analysis_points.append(f"⭐ **Líder de PIB de la Selección ({latest_year}):** El país con el **PIB Total** más grande dentro de los seleccionados es **{outlier_pib}** con un valor de **{pib_value:,.0f} millones USD**.")

    return analysis_points

# --- NUEVA FUNCIÓN: ANÁLISIS DE TENDENCIAS HISTÓRICAS (AÑADIR) ---
def generate_trend_analysis(df, start_year, latest_year):
    """
    Genera un análisis de texto comparando las métricas promedio entre el año inicial 
    y el año final del rango seleccionado.
    """
    
    analysis_points = []
    
    # 1. Preparar datos para los dos años (excluyendo Venezuela RB para promedios)
    df_start = df[(df['year'] == start_year) & (df['country_name'] != 'Venezuela, RB')].dropna(subset=['crecimiento_anual', 'inflacion', 'balanza_comercial_neta'])
    df_latest = df[(df['year'] == latest_year) & (df['country_name'] != 'Venezuela, RB')].dropna(subset=['crecimiento_anual', 'inflacion', 'balanza_comercial_neta'])

    if df_start.empty or df_latest.empty:
        return [f"No hay suficientes datos disponibles para los años {start_year} y {latest_year} para realizar un análisis de tendencias."]

    # 2. CALCULAR CAMBIOS PROMEDIO
    avg_growth_start = df_start['crecimiento_anual'].mean()
    avg_growth_latest = df_latest['crecimiento_anual'].mean()
    change_growth = avg_growth_latest - avg_growth_start
    
    avg_inf_start = df_start['inflacion'].mean()
    avg_inf_latest = df_latest['inflacion'].mean()
    change_inf = avg_inf_latest - avg_inf_start
    
    avg_trade_start = df_start['balanza_comercial_neta'].mean()
    avg_trade_latest = df_latest['balanza_comercial_neta'].mean()
    change_trade = avg_trade_latest - avg_trade_start
    
    
    # 3. GENERAR PUNTOS DE ANÁLISIS
    analysis_points.append(f"Este análisis compara el rendimiento promedio de la selección de países entre el inicio del rango de años ({start_year}) y el año más reciente ({latest_year}).")
    
    
    # --- ANÁLISIS DE CRECIMIENTO ---
    if not pd.isna(change_growth):
        if change_growth > 0.5:
            analysis_points.append(f"📈 **Crecimiento del PIB:** La región mejoró significativamente, con un aumento de **+{change_growth:.1f} puntos porcentuales (p.p.)** en el crecimiento promedio ({avg_growth_start:.1f}% -> {avg_growth_latest:.1f}%).")
        elif change_growth < -0.5:
            analysis_points.append(f"📉 **Crecimiento del PIB:** La tendencia de crecimiento se deterioró, cayendo en **{change_growth:.1f} p.p.**, indicando una desaceleración económica regional.")
        else:
            analysis_points.append(f"⚖️ **Crecimiento del PIB:** El crecimiento promedio se mantuvo estable, con un cambio marginal de **{change_growth:.1f} p.p.**.")

    
    # --- ANÁLISIS DE INFLACIÓN ---
    if not pd.isna(change_inf):
        if change_inf < -2.0:
            analysis_points.append(f"✅ **Tasa de Inflación:** Se observa una fuerte contención de precios, con una caída de la inflación promedio de **{abs(change_inf):.1f} p.p.**, señalando un éxito en la estabilidad macroeconómica.")
        elif change_inf > 2.0:
            analysis_points.append(f"🔥 **Tasa de Inflación:** La presión inflacionaria aumentó, con un incremento promedio de **+{change_inf:.1f} p.p.**, lo que representa un desafío para el control de precios.")
        else:
            analysis_points.append(f"⚖️ **Tasa de Inflación:** La inflación se mantuvo en niveles similares, con un cambio poco significativo de **{change_inf:.1f} p.p.**.")

    
    # --- ANÁLISIS DE BALANZA COMERCIAL NETA ---
    if not pd.isna(change_trade):
        if change_trade > 0.5:
            analysis_points.append(f"💰 **Balanza Comercial Neta:** La balanza mejoró en **+{change_trade:.1f} p.p. del PIB**, sugiriendo un aumento de las exportaciones netas.")
        elif change_trade < -0.5:
            analysis_points.append(f"🚢 **Balanza Comercial Neta:** La balanza se deterioró en **{change_trade:.1f} p.p. del PIB**, lo que podría indicar un aumento del déficit comercial promedio.")
        else:
            analysis_points.append(f"⚖️ **Balanza Comercial Neta:** Se mantuvo estable, con un cambio marginal de **{change_trade:.1f} p.p. del PIB**.")

    return analysis_points

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
        "PIB Total (Millones USD) [pib_millones]": {'col': 'pib_millones', 'label': 'PIB Total (Millones USD)', 'format': ",.0f", 'unit': '$ ', 'category': 'PIB'},
        "PIB (Moneda Local) [pib_monedalocal]": {'col': 'pib_monedalocal', 'label': 'PIB (Moneda Local)', 'format': ",.0f", 'unit': '', 'category': 'PIB'},
        "Crecimiento Anual (% PIB) [crecimiento_anual]": {'col': 'crecimiento_anual', 'label': 'Crecimiento Anual (% PIB)', 'format': ".1f", 'unit': ' %', 'category': 'PIB'},
        "Balanza Comercial Neta (% PIB) [importaciones_vs_exportaciones]": {'col': 'balanza_comercial_neta', 'label': 'Balanza Comercial Neta (% PIB)', 'format': ".1f", 'unit': ' %', 'category': 'Comercio'},
        "Exportaciones (% PIB) [exportaciones]": {'col': 'exportaciones_percent', 'label': 'Exportaciones (% PIB)', 'format': ".1f", 'unit': ' %', 'category': 'Comercio'},
        "Importaciones (% PIB) [importaciones]": {'col': 'importaciones_percent', 'label': 'Importaciones (% PIB)', 'format': ".1f", 'unit': ' %', 'category': 'Comercio'},
        "Tasa de Inflación (% Anual) [inflacion]": {'col': 'inflacion', 'label': 'Inflación (% Anual)', 'format': ".1f", 'unit': ' %', 'category': 'Precios'},
    }
    
    sorted_indicator_keys = sorted(indicator_options.keys(), key=lambda k: indicator_options[k]['category'] + k)

    indicator_key = st.sidebar.selectbox("Selecciona el Indicador Principal:", sorted_indicator_keys, index=0)

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
    default_countries = ['Colombia', 'Panama', 'Ecuador', 'Chile', 'Mexico', 'Uruguay']
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
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Metricas", "📈 Analisis", "🔥 Historico Inflación", "🗺️ Vista Global"])

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
    # La escala logarítmica ahora es siempre False
    log_scale = False

    # --- Pestaña 1: Resumen y Tendencias ---
    with tab1:
        st.header("Metricas")
        
        col_kpi, col_spacer, col_desc = st.columns([1, 0.1, 2])

        with col_kpi:
            st.subheader(f"Métrica Regional ({latest_year})")
            
            if pd.isna(alc_average):
                display_value = "N/A"
            else:
                display_value = f"{alc_average:{value_format}}"
                
                if unit == '$ ':
                    display_value = unit.strip() + ' ' + display_value
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
                    log_y=log_scale # APPLIED LOG SCALE (always False)
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
                    log_y=log_scale # APPLIED LOG SCALE (always False)
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


# --- Pestaña 2: Informe Inteligente ---
    with tab2:
        st.header("Análisis Económico Inteligente de la Selección")
        st.info("Este informe combina un análisis detallado del año más reciente con un estudio de la tendencia histórica de las métricas clave, de acuerdo al rango de años y países seleccionados. Es una aproximación para una lectura rápida de los datos.")

        # 1. Preparación de datos (Se calcula una sola vez)
        df_analysis = df_filtered[df_filtered['country_name'].isin(selected_countries)] if selected_countries else df_filtered
        
        start_year = df_filtered['year'].min()
        is_multi_year = latest_year > start_year

        if df_analysis.empty:
            st.warning("Selecciona al menos un país y un rango de años válido en el panel lateral para generar el análisis inteligente.")
            
        else:
            # --- 1. Análisis del Último Año (Rendimiento por Métrica) ---
            st.subheader(f"💡 Resumen Inteligente del Último Año: {latest_year}")
            
            analysis_results = generate_metric_analysis(df_analysis, latest_year)
            for point in analysis_results:
                st.markdown(f"- {point}")

            # --- 2. Análisis de Tendencias (Solo si hay más de un año) ---
            if is_multi_year:
                st.markdown("---")
                st.subheader(f"⏱️ Análisis Comparativo de Tendencia: {start_year} a {latest_year}")
                
                trend_analysis_results = generate_trend_analysis(df_analysis, start_year, latest_year)
                for point in trend_analysis_results:
                    st.markdown(point)
            else:
                # Mensaje de advertencia si solo hay un año seleccionado
                st.markdown("---")
                st.warning("El **Análisis de Tendencias** requiere seleccionar un rango de años (mínimo 2 años) en el filtro lateral para realizar la comparación histórica.")

    # --- Pestaña 3: Análisis de Inflación ---
    with tab3:
        st.header("Tendencias Inflacionarias en ALC (2000-2023)")
        st.markdown(f"El mapa de calor inferior muestra la Tasa de Inflación anual, **filtrada por los países seleccionados en el menú lateral**, con un límite de escala en **{max_inflation_limit:.1f}%**.")

        # --- Heatmap general de Inflación ---
        st.subheader("Inflación Anual por País (Mapa de Calor)")

        # Lógica para filtrar por países seleccionados
        if selected_countries:
            df_heatmap_filtered = df_main[df_main['country_name'].isin(selected_countries)].copy()
        else:
            df_heatmap_filtered = df_main.copy()
            st.info("ℹ️ No hay países seleccionados en el filtro lateral. Mostrando el Heatmap para todos los países de ALC.")
        
        
        if df_heatmap_filtered.empty:
            st.warning("No hay datos para generar el Heatmap con los países seleccionados.")
        else:
            heatmap_data = df_heatmap_filtered.pivot_table(index='country_name', columns='year', values='inflacion').fillna(0)

            # Usar 0 para zmin si es apropiado, sino el mínimo real.
            z_min = max(0, heatmap_data.values.min())
            
            fig_heatmap = go.Figure(data=go.Heatmap(
                    z=heatmap_data.values, x=heatmap_data.columns, y=heatmap_data.index,
                    colorscale='Viridis', zmin=z_min, zmax=max_inflation_limit 
            ))

            fig_heatmap.update_layout(
                title=f'Tasa de Inflación Anual (%): Países Seleccionados ({df_main["year"].min()}-{df_main["year"].max()})', 
                xaxis_title='Año', 
                yaxis_title='País', 
                # Ajustar la altura dinámicamente según el número de países
                height=max(500, len(heatmap_data.index) * 25) 
            )
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


            
    # --- Pestaña 4: Vista Global (Mapa Mundial) ---
    with tab4:
        # Generamos df_global_map a partir del df_filtered (que respeta el slider de años)
        if not df_filtered.empty:
            
            map_year = df_filtered['year'].max() 
            
            # Filtramos df_filtered para obtener solo el último año disponible en el rango
            df_global_map = df_filtered[df_filtered['year'] == map_year].copy()
            
            # LÓGICA DE FILTRADO PARA EL MAPA
            if selected_countries:
                # Filtrar solo los países seleccionados
                df_global_map = df_global_map[df_global_map['country_name'].isin(selected_countries)].copy()
                map_title = f"🗺️ PIB Total (Países Seleccionados - Año: {map_year})"
                st.header(map_title)
            else:
                # Mostrar todos los datos de ALC
                map_title = f"🗺️ PIB Total Global (Año mostrado: {map_year})"
                st.header(map_title)
                st.info("ℹ️ No hay países seleccionados. Mostrando el PIB para toda la región ALC.")

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