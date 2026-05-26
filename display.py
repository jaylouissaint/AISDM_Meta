# app.py
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import streamlit as st
from matplotlib.colors import TwoSlopeNorm
from pathlib import Path
import seaborn as sns
import plotly.express as px
import json

# =========================
# Streamlit page settings
# =========================
st.set_page_config(
    page_title="County Percent Change Maps",
    layout="wide"
)

st.title("US County Percent Change Maps")


# =========================
# Load spatial data
# =========================
@st.cache_data
def load_spatial_data():
    """
    Load county and state shapefiles.
    
    You can create these once and save them locally as:
      - data/counties.parquet
      - data/states.parquet

    Recommended workflow in Python:
      counties.to_parquet(...)
      states.to_parquet(...)
    """

    counties_sf = gpd.read_parquet("data/counties.parquet")
    states_sf = gpd.read_parquet("data/states.parquet")

    counties_sf = counties_sf.to_crs(epsg=4326)
    states_sf = states_sf.to_crs(epsg=4326)

    return counties_sf, states_sf


counties_sf, states_sf = load_spatial_data()

# =========================
# Sidebar controls
# =========================
OUTPUTS_DIR = Path("./outputs")

aggregation_options = {
    "Bing Tiles": "tk_facebook_pop_aggregated_bing.csv",
    "Administrative Regions": "tk_facebook_pop_aggregated_admin.csv"
}

selected_aggregation = st.sidebar.selectbox(
    "Type of Aggregation",
    options=list(aggregation_options.keys())
)

selected_file = aggregation_options[selected_aggregation]




# =========================
# Load data
# =========================
@st.cache_data
def load_data(file_name):
    return pd.read_csv(OUTPUTS_DIR / file_name)


df = load_data(selected_file)

counties_sf["county_geoid"] = (
    counties_sf["county_geoid"]
    .astype(str)
    .str.zfill(5)
)

df["county_geoid"] = (
    df["county_geoid"]
    .astype(str)
    .str.zfill(5)
)

date_col = "ds"

value_col = "percent_change"

title_prefix = "Population Density Change (%)"

# Convert date column
df[date_col] = pd.to_datetime(df[date_col])

# =========================
# Date selector
# =========================
available_dates = sorted(df[date_col].dropna().unique())

selected_dates = st.sidebar.multiselect(
    "Select date(s)",
    options=available_dates,
    default=[available_dates[-1]],
    format_func=lambda x: pd.to_datetime(x).strftime("%Y-%m-%d")
)

if len(selected_dates) == 0:
    st.warning("Please select at least one date.")
    st.stop()


# =========================
# County selector
# =========================
available_counties = sorted(df["county_name"].dropna().unique())

selected_counties = st.sidebar.multiselect(
    "Select counties",
    options=available_counties
)


# =========================
# Compute global fill range
# =========================
all_summarized = (
    df[df[date_col].isin(selected_dates)]
    .groupby(
        ["county_geoid", "county_name", "county_state", date_col],
        as_index=False
    )[value_col]
    .mean()
    .rename(columns={value_col: "mean_percent_change"})
)

fill_min = all_summarized["mean_percent_change"].min()
fill_max = all_summarized["mean_percent_change"].max()

# Center colormap at 0
norm = TwoSlopeNorm(
    vmin=fill_min,
    vcenter=0,
    vmax=fill_max
)

# =========================
# County time series prep
# =========================
def make_county_time_data(selected_county_names):

    filtered = df[
        df["county_name"].isin(selected_county_names)
    ].copy()

    summary = (
        filtered.groupby(
            ["ds", "county_geoid", "county_name"],
            as_index=False
        )
        .agg(
            mean_percent_change=("percent_change", "mean"),
            median_percent_change=("percent_change", "median")
        )
    )

    return summary

# =========================
# Map plotting function
# =========================
# =========================
# Interactive map plotting
# =========================
def create_map(plot_date):

    latest_county = (
        df[df[date_col] == plot_date]
        .groupby(
            ["county_geoid", "county_name", "county_state"],
            as_index=False
        )[value_col]
        .mean()
        .rename(columns={value_col: "mean_percent_change"})
    )

    # Keep only geometry from shapefile to avoid duplicate columns
    counties_geometry = counties_sf[
        ["county_geoid", "geometry"]
    ]

    map_data = counties_geometry.merge(
        latest_county,
        on="county_geoid",
        how="inner"
    )

    # Convert GeoDataFrame to GeoJSON
    geojson_data = json.loads(map_data.to_json())

    fig = px.choropleth(
        map_data,
        geojson=geojson_data,
        locations="county_geoid",
        featureidkey="properties.county_geoid",
        color="mean_percent_change",
        color_continuous_scale="RdBu_r",
        range_color=(fill_min, fill_max),
        scope="usa",
        hover_name="county_name",
        hover_data={
            "county_state": True,
            "mean_percent_change": ":.2f",
            "county_geoid": False
        },
        labels={
            "county_state": "State",
            "mean_percent_change": "% Change"
        }
    )

    fig.update_geos(
        fitbounds="locations",
        visible=False
    )

    fig.update_layout(
        title=pd.to_datetime(plot_date).strftime("%Y-%m-%d"),
        margin={"r": 0, "t": 40, "l": 0, "b": 0},
        height=700
    )

    return fig


# =========================
# Tabs
# =========================
tab_maps, tab_timeseries, tab_table = st.tabs(
    ["Maps", "County Time Series", "Table"]
)

# =========================
# Maps tab
# =========================
with tab_maps:

    st.header(title_prefix)

    cols = st.columns(len(selected_dates))

    for idx, plot_date in enumerate(selected_dates):

        fig = create_map(plot_date)

        with cols[idx]:
            st.plotly_chart(
                fig,
                use_container_width=True
            )

# =========================
# County time series tab
# =========================
with tab_timeseries:

    st.header("County Time Series")

    time_data = make_county_time_data(selected_counties)

    if not time_data.empty:

        fig_ts, ax = plt.subplots(figsize=(12, 6))

        sns.lineplot(
            data=time_data,
            x="ds",
            y="mean_percent_change",
            hue="county_name",
            marker="o",
            ax=ax
        )

        ax.axhline(
            y=0,
            color="black",
            linewidth=0.5,
            linestyle="--"
        )

        ax.set_title("County Percent Change Over Time")

        ax.set_xlabel("")
        ax.set_ylabel("% Change vs Baseline")

        plt.xticks(rotation=45)

        st.pyplot(fig_ts)

    else:
        st.warning("No county data available.")

# =========================
# Table tab
# =========================
with tab_table:

    st.header("Data Table")

    table_df = df[df[date_col].isin(selected_dates)].copy()

    # Filter counties only if selected
    if len(selected_counties) > 0:
        table_df = table_df[
            table_df["county_name"].isin(selected_counties)
        ]

    # Optional sorting
    table_df = table_df.sort_values(
        by=[date_col, "county_state", "county_name"]
    )

    st.dataframe(
        table_df,
        use_container_width=True
    )

    st.caption(
        f"{len(table_df):,} rows displayed"
    )
