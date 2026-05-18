# app.py
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import streamlit as st
from matplotlib.colors import TwoSlopeNorm
from pathlib import Path

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
# Map plotting function
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

    map_data = counties_sf.merge(
        latest_county,
        on="county_geoid",
        how="inner"
    )

    # Relevant states only
    relevant_states = states_sf[
        states_sf.intersects(map_data.unary_union)
    ]

    fig, ax = plt.subplots(figsize=(10, 7))

    map_data.plot(
        column="mean_percent_change",
        cmap="coolwarm",
        linewidth=0.2,
        edgecolor="none",
        legend=True,
        norm=norm,
        ax=ax
    )

    relevant_states.boundary.plot(
        ax=ax,
        color="black",
        linewidth=0.7
    )

    ax.set_title(
        pd.to_datetime(plot_date).strftime("%Y-%m-%d"),
        fontsize=14
    )

    ax.axis("off")

    return fig


# =========================
# Display maps
# =========================
st.header(title_prefix)

cols = st.columns(len(selected_dates))

for idx, plot_date in enumerate(selected_dates):

    fig = create_map(plot_date)

    with cols[idx]:
        st.pyplot(fig)

# =========================
# Optional data preview
# =========================
with st.expander("Preview Data"):
    st.dataframe(df.head())
