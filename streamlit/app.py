import streamlit as st
import pandas as pd
from database import fetch_data
import charts

st.set_page_config(
    page_title="Weather Risk Monitoring",
    page_icon="🌪️",
    layout="wide"
)

# Ordered list of pages. Each entry is (label, kind, render_fn or None for "overview"/"table").
PAGES = [
    ("Overview", "overview"),
    ("Risk by City", "risk_by_city"),
    ("Risk Heatmap", "risk_heatmap"),
    ("Temperature vs Precipitation", "precip_vs_temp"),
    ("Risk Distribution", "risk_distribution"),
    ("Risk Score Spread", "risk_spread"),
    ("Forecast Data", "table"),
]


def load_all_data():
    """Fetch all forecast data joining with cities to get names."""
    query = """
        SELECT 
            c.name as city_name,
            w.forecast_date,
            w.temperature_max,
            w.temperature_min,
            w.precipitation_sum,
            w.wind_speed_max,
            w.risk_score,
            w.risk_level
        FROM weather_forecast w
        JOIN cities c ON w.city_id = c.id
    """
    try:
        return fetch_data(query)
    except Exception as e:
        st.error(f"Failed to load data from database: {e}")
        return pd.DataFrame(columns=[
            'city_name', 'forecast_date', 'temperature_max', 'temperature_min',
            'precipitation_sum', 'wind_speed_max', 'risk_score', 'risk_level'
        ])


def render_overview(filtered_df):
    st.header("Key Metrics")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Cities", filtered_df['city_name'].nunique())

    with col2:
        high_risk_cities = filtered_df[filtered_df['risk_level'].isin(['High', 'Critical'])]['city_name'].nunique()
        st.metric("High/Critical Risk Cities", high_risk_cities)

    with col3:
        max_temp = f"{filtered_df['temperature_max'].max():.1f}°C" if not filtered_df.empty else "N/A"
        st.metric("Max Temperature", max_temp)

    with col4:
        max_precip = f"{filtered_df['precipitation_sum'].max():.1f} mm" if not filtered_df.empty else "N/A"
        st.metric("Max Precipitation", max_precip)

    st.caption("Use the page selector below (or the sidebar) to browse each chart on its own full page.")


def render_table(filtered_df):
    st.header("Forecast Data")
    st.dataframe(
        filtered_df[['city_name', 'forecast_date', 'temperature_max', 'precipitation_sum', 'wind_speed_max', 'risk_score', 'risk_level']]
        .rename(columns={
            'city_name': 'City',
            'forecast_date': 'Date',
            'temperature_max': 'Max Temp (°C)',
            'precipitation_sum': 'Precipitation (mm)',
            'wind_speed_max': 'Max Wind (km/h)',
            'risk_score': 'Risk Score',
            'risk_level': 'Risk Level'
        }),
        use_container_width=True,
        height=600,
    )


CHART_RENDERERS = {
    "risk_by_city": (charts.risk_by_city, "Average risk score for each city in the current filter."),
    "risk_heatmap": (charts.risk_heatmap, "Risk score for every city across the selected date range, at a glance."),
    "precip_vs_temp": (charts.precipitation_vs_temperature, "Bubble size = risk score; color = risk level."),
    "risk_distribution": (charts.risk_distribution_pie, "Share of forecasts falling into each risk level."),
    "risk_spread": (charts.risk_score_spread, "Distribution (not just average) of risk scores within each risk level."),
}


def render_page(kind, filtered_df):
    if kind == "overview":
        render_overview(filtered_df)
    elif kind == "table":
        render_table(filtered_df)
    else:
        render_fn, caption = CHART_RENDERERS[kind]
        st.caption(caption)
        fig = render_fn(filtered_df)
        st.pyplot(fig, use_container_width=True)


def main():
    st.title("🌪️ Weather Risk Monitoring")

    df = load_all_data()

    if df.empty:
        st.warning("No data found in the database. Has the pipeline run successfully?")
        return

    df['forecast_date'] = pd.to_datetime(df['forecast_date']).dt.date

    # Filters
    st.sidebar.header("Filters")

    cities = df['city_name'].unique().tolist()
    city_filter = st.sidebar.selectbox("City", ["All"] + sorted(cities))

    min_date = df['forecast_date'].min()
    max_date = df['forecast_date'].max()
    date_filter = st.sidebar.date_input("Date Range", [min_date, max_date], min_value=min_date, max_value=max_date)

    risk_levels = ["Low", "Moderate", "High", "Critical"]
    risk_filter = st.sidebar.multiselect("Risk Level", risk_levels, default=risk_levels)

    filtered_df = df.copy()
    if city_filter != "All":
        filtered_df = filtered_df[filtered_df['city_name'] == city_filter]

    if len(date_filter) == 2:
        start_date, end_date = date_filter
        filtered_df = filtered_df[(filtered_df['forecast_date'] >= start_date) & (filtered_df['forecast_date'] <= end_date)]

    if risk_filter:
        filtered_df = filtered_df[filtered_df['risk_level'].isin(risk_filter)]

    # --- Pagination state ---
    if "page_index" not in st.session_state:
        st.session_state.page_index = 0

    page_labels = [label for label, _ in PAGES]

    st.sidebar.markdown("---")
    st.sidebar.header("Pages")
    chosen_label = st.sidebar.radio("Jump to page", page_labels, index=st.session_state.page_index)
    st.session_state.page_index = page_labels.index(chosen_label)

    current_index = st.session_state.page_index
    current_label, current_kind = PAGES[current_index]

    st.markdown("---")
    st.subheader(f"{current_label}")

    render_page(current_kind, filtered_df)

    # --- Prev / Next controls ---
    st.markdown("---")
    nav_prev, nav_status, nav_next = st.columns([1, 2, 1])

    with nav_prev:
        if st.button("⬅ Previous", disabled=current_index == 0, use_container_width=True):
            st.session_state.page_index = max(0, current_index - 1)
            st.rerun()

    with nav_status:
        st.markdown(
            f"<div style='text-align:center;'>Page {current_index + 1} of {len(PAGES)}</div>",
            unsafe_allow_html=True,
        )

    with nav_next:
        if st.button("Next ➡", disabled=current_index == len(PAGES) - 1, use_container_width=True):
            st.session_state.page_index = min(len(PAGES) - 1, current_index + 1)
            st.rerun()


if __name__ == "__main__":
    main()