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

scatter_files = {
    "Bing Tiles": "tk_facebook_pop_bing.csv",
    "Administrative Regions": "tk_facebook_pop_admin.csv"
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

scatter_df = load_data(scatter_files[selected_aggregation])

scatter_df["ds"] = pd.to_datetime(scatter_df["ds"]).dt.normalize()

scatter_df["hour"] = (
    scatter_df["hour"]
    .astype(str)
    .str.zfill(4)
)

df["ds"] = pd.to_datetime(df["ds"]).dt.normalize()

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

df["hour"] = df["hour"].astype(str).str.zfill(4)

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
# Hour selector
# =========================

hour_options = {
    "12am PST": "0000",
    "8am PST": "0800",
    "4pm PST": "1600",
}

selected_hour = st.sidebar.selectbox(
    "Select hour",
    options=list(hour_options.keys())
)

selected_hour = hour_options[selected_hour]

if len(selected_hour) == 0:
    st.warning("Please select at least one hour.")
    st.stop()

# =========================
# County selector
# =========================
available_counties = sorted(df["county_name_acs"].dropna().unique())

selected_counties = st.sidebar.multiselect(
    "Select counties",
    options=available_counties
)


# =========================
# Compute global fill range
# =========================
all_summarized = df[
    df[date_col].isin(selected_dates) &
    (df["hour"] == selected_hour)
]


fill_min = all_summarized["percent_change"].min()
fill_max = all_summarized["percent_change"].max()

# Center colormap at 0
norm = TwoSlopeNorm(
    vmin=fill_min,
    vcenter=0,
    vmax=fill_max
)

# =========================
# County time series prep
# =========================

def make_county_time_data(selected_counties):

    filtered_df = df.copy()

    # Filter only if counties selected
    if len(selected_counties) > 0:
        filtered_df = filtered_df[
            filtered_df["county_name_acs"].isin(selected_counties)
        ]

    return (
        filtered_df.assign(
            ds=pd.to_datetime(
                filtered_df["ds"].astype(str) + " " + filtered_df["hour"].astype(str),
                format="%Y-%m-%d %H%M"
            ).dt.tz_localize("America/Los_Angeles")
        )
    )

# =========================
# Scatterplot prep
# =========================

def create_scatter_data():

    scatter_filtered = scatter_df[
        scatter_df["ds"].isin(selected_dates)
        & (scatter_df["hour"] == selected_hour)
    ].copy()

    # county filter
    if len(selected_counties) > 0:
        scatter_filtered = scatter_filtered[
            scatter_filtered["county_name_acs"].isin(selected_counties)
        ]

    return scatter_filtered

# =========================
# Map plotting function
# =========================
# =========================
# Interactive map plotting
# =========================
def create_map(plot_date):

    latest_county = df[
    (df[date_col] == plot_date) &
    (df["hour"] == selected_hour)
    ]

    # Keep only geometry from shapefile to avoid duplicate columns
    counties_geometry = counties_sf[
        ["county_geoid", "geometry"]
    ]

    map_data = counties_geometry.merge(
        latest_county,
        on="county_geoid",
        how="inner"
    )
    map_data["ds"] = map_data["ds"].astype(str)

    # Convert GeoDataFrame to GeoJSON
    geojson_data = json.loads(map_data.to_json())

    fig = px.choropleth(
        map_data,
        geojson=geojson_data,
        locations="county_geoid",
        featureidkey="properties.county_geoid",
        color="percent_change",
        color_continuous_scale="RdBu_r",
        range_color=(fill_min, fill_max),
        scope="usa",
        hover_name="county_name_acs",
        hover_data={
            "county_state": True,
            "percent_change": ":.2f",
            "county_geoid": False
        },
        labels={
            "county_state": "State",
            "percent_change": "% Change"
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
tab_maps, tab_scatter, tab_timeseries, tab_table = st.tabs(
    [
        "Maps",
        "Point Scatter",
        "County Time Series",
        "Table"
    ]
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
    
        st.divider()

# =========================
# Scatterplot tab
# =========================

with tab_scatter:

    st.header("Point-Level Population Change")

    scatter_data = create_scatter_data()

    st.caption(f"{len(scatter_data):,} rows")

    if not scatter_data.empty:

        scatter_data["date_label"] = (
            pd.to_datetime(scatter_data["ds"])
            .dt.strftime("%Y-%m-%d")
        )

        fig_scatter = px.scatter(
            scatter_data,
            x="longitude",
            y="latitude",
            color="percent_change",
            size="n_crisis",
            facet_col="date_label" if len(selected_dates) > 1 else None,
            color_continuous_scale="RdBu_r",
            range_color=(fill_min, fill_max),
            hover_data={
                "county_name_acs": True,
                "county_state": True,
                "percent_change": ":.2f",
                "n_crisis": ":,.0f",
                "n_baseline": ":,.0f"
            }
        )

        fig_scatter.update_layout(
            height=800,
            margin=dict(l=0, r=0, t=40, b=0),
            plot_bgcolor="white",
            paper_bgcolor="white"
        )



        st.plotly_chart(
            fig_scatter,
            use_container_width=True
        )

    else:
        st.warning(
            "No rows available for the selected date/hour/county filters."
        )

# =========================
# County time series tab
# =========================
with tab_timeseries:

    st.header("County Time Series")

    time_data = make_county_time_data(selected_counties)

    if not time_data.empty:

                # =====================================
        # User-friendly county summary metrics
        # =====================================
        if len(selected_counties) > 0:

            summary_df = (
                time_data.sort_values("ds")
                .groupby("county_name_acs")
                .last()
                .reset_index()
            )

            st.subheader("County Summary")

            for _, row in summary_df.iterrows():

                county_name = row["county_name_acs"]

                total_population = row.get("total_population", None)
                median_income = row.get("median_income", None)
                poverty_rate = row.get("poverty_rate", None)
                pct_age_65_plus = row.get("pct_age_65_plus", None)
                pct_no_vehicle = row.get("pct_no_vehicle", None)

                pop_text = (
                    f"{int(total_population):,}"
                    if pd.notnull(total_population)
                    else "N/A"
                )

                income_text = (
                    f"${int(median_income):,}"
                    if pd.notnull(median_income)
                    else "N/A"
                )

                poverty_text = (
                    f"{poverty_rate:.1f}%"
                    if pd.notnull(poverty_rate)
                    else "N/A"
                )

                age65_text = (
                    f"{pct_age_65_plus:.1f}%"
                    if pd.notnull(pct_age_65_plus)
                    else "N/A"
                )

                no_vehicle_text = (
                    f"{pct_no_vehicle:.1f}%"
                    if pd.notnull(pct_no_vehicle)
                    else "N/A"
                )

                st.markdown(
                    f"""
                    ### {county_name}

                    - **Total Population:** {pop_text}
                    - **Median Household Income:** {income_text}
                    - **Poverty Rate:** {poverty_text}
                    - **Age 65+ Population:** {age65_text}
                    - **Households Without Vehicle:** {no_vehicle_text}
                    """
                )

            st.divider()

        # =====================================
        # Time series chart
        # =====================================
        fig_ts = px.line(
            time_data,
            x="ds",
            y="percent_change",
            color="county_name_acs",
            markers=True,
            hover_name="county_name_acs",
            hover_data={
                "percent_change": ":.2f",
                "ds": True
            }
        )

        fig_ts.add_hline(
            y=0,
            line_dash="dash",
            line_color="black",
            line_width=1
        )

        fig_ts.update_layout(
            title="County Percent Change Over Time",
            xaxis_title="",
            yaxis_title="% Change vs Baseline",
            showlegend=False,  # removes legend
            height=600
        )

        st.plotly_chart(
            fig_ts,
            use_container_width=True
        )

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
            table_df["county_name_acs"].isin(selected_counties)
        ]

    # Optional sorting
    table_df = table_df.sort_values(
        by=[date_col, "county_state", "county_name_acs"]
    )

    st.dataframe(
        table_df,
        use_container_width=True
    )

    st.caption(
        f"{len(table_df):,} rows displayed"
    )
