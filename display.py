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
    "Bing Tiles": "tk_facebook_pop_aggregated_bing.parquet",
    "Administrative Regions": "tk_facebook_pop_aggregated_admin.parquet"
}

scatter_files = {
    "Bing Tiles": "tk_facebook_pop_bing.parquet",
    "Administrative Regions": "tk_facebook_pop_admin.parquet"
}

selected_aggregation = st.sidebar.selectbox(
    "Type of Aggregation",
    options=list(aggregation_options.keys())
)

selected_file = aggregation_options[selected_aggregation]

# =========================
# Create the GeoJSON
# =========================

@st.cache_resource
def load_geojson():
    with open("data/counties.geojson") as f:
        return json.load(f)

county_geojson = load_geojson()
# =========================
# Load data
# =========================
@st.cache_data
def load_data(file_name):
    return pd.read_parquet(
        OUTPUTS_DIR / file_name
    )


df = load_data(selected_file)

scatter_df = load_data(scatter_files[selected_aggregation])

df["datetime"] = (
    pd.to_datetime(
        df["ds"].astype(str) + " " + df["hour"].astype(str).str.zfill(4),
        format="%Y-%m-%d %H%M"
    )
    .dt.tz_localize("America/Los_Angeles")
    .dt.tz_convert("America/New_York")
)

scatter_df["datetime"] = (
    pd.to_datetime(
        scatter_df["ds"].astype(str) + " " + scatter_df["hour"].astype(str).str.zfill(4),
        format="%Y-%m-%d %H%M"
    )
    .dt.tz_localize("America/Los_Angeles")
    .dt.tz_convert("America/New_York")
)
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

date_col = "datetime"

value_col = "percent_change"

title_prefix = "Population Change (%)"

# Convert date column
df[date_col] = pd.to_datetime(df[date_col])


@st.cache_data
def get_map_data(df, dt):
    return df[df["datetime"] == dt]
# =========================
# Date-Time selector
# =========================

available_datetimes = sorted(df["datetime"].dropna().unique())

selected_datetime = st.sidebar.select_slider(
    "Select date and hour",
    options=available_datetimes,
    value=available_datetimes[-1],
    format_func=lambda x: pd.Timestamp(x).strftime("%Y-%m-%d %I:%M %p")
)

# =========================
# County selector
# =========================
available_counties = sorted(df["county_name_acs"].dropna().unique())

selected_counties = st.sidebar.multiselect(
    "Select counties",
    options=available_counties
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
        ].copy()
        filtered_df["county_name_acs"] = (
            filtered_df["county_name_acs"]
            .cat.remove_unused_categories()
        )


    return filtered_df

# =========================
# Scatterplot prep
# =========================

def create_scatter_data():

    scatter_filtered = scatter_df[
        scatter_df["datetime"] == selected_datetime
    ].copy()

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

def create_map(plot_datetime):

    latest_county = get_map_data(df, selected_datetime)

    fig = px.choropleth_mapbox(
        latest_county,
        geojson=county_geojson,
        locations="county_geoid",
        featureidkey="properties.county_geoid",
        color="percent_change",
        color_continuous_scale="RdBu",
        hover_name="county_name_acs",
        hover_data={
            "county_state": False,
            "percent_change": ":.2f",
            "n_crisis": ":,.0f",
            "n_baseline": ":.0f",
            "total_population": ":.0f",
            "county_geoid": False
        },
        labels={
            "county_state": "State",
            "percent_change": "Facebook Pop Change from Baseline (%)",
            "n_crisis": "Facebook Population at Given Time",
            "n_baseline": "Facebook Population at 45-day Baseline",
            "total_population": "Total Population"
        },
        mapbox_style="carto-positron",
        center={"lat": 36, "lon": -88},
        zoom=5
    )

    fig.update_layout(
        title=pd.Timestamp(plot_datetime).strftime("%Y-%m-%d %I:%M %p"),
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

    fig = create_map(selected_datetime)

    st.plotly_chart(
        fig,
        use_container_width=True
    )

# =========================
# Scatterplot tab
# =========================

with tab_scatter:

    st.header("Point-Level Population Change")

    scatter_data = create_scatter_data()

    st.caption(f"{len(scatter_data):,} rows")

    if not scatter_data.empty:

        fig_scatter = px.scatter(
            scatter_data,
            x="longitude",
            y="latitude",
            color="percent_change",
            size="n_crisis",
            color_continuous_scale="RdBu",
            hover_data={
                "latitude": False,
                "longitude": False,
                "county_name_acs": True,
                "county_state": False,
                "percent_change": ":.2f",
                "n_crisis": ":,.0f",
                "n_baseline": ":,.0f",
                "total_population": ":,.0f"
            },
            labels={
                "county_name_acs": "County Name",
                "percent_change": "Facebook Pop Change from Baseline (%)",
                "n_crisis": "Facebook Population at Given Time",
                "n_baseline": "Facebook Population at 45-day Baseline",
                "total_population": "Total Population",
                "latitude": "Latitude",
                "longitude": "Longitude"
            }
        )

        # Add black border around markers
        fig_scatter.update_traces(
            marker=dict(
                line=dict(
                    color="black",
                    width=1
                )
            )
        )


        fig_scatter.update_layout(
            title=pd.Timestamp(selected_datetime).strftime("%Y-%m-%d %I:%M %p"),
            height=800,
            margin=dict(l=0, r=0, t=40, b=0)
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
                time_data.sort_values("datetime")
                .groupby("county_name_acs", observed=True)
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
            x="datetime",
            y="percent_change",
            color="county_name_acs",
            markers=True,
            hover_name="county_name_acs",
            hover_data={
                "percent_change": ":.2f",
                "datetime": True
            },
            labels={
                "datetime": "Date and Time",
                "county_name_acs": "County Name",
                "percent_change": "Facebook Pop Change from Baseline (%)",
                "n_crisis": "Facebook Population at Given Time",
                "n_baseline": "Facebook Population at 45-day Baseline",
                "total_population": "Total Population"
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

    table_df = df.copy()

    # Filter counties only if selected
    if len(selected_counties) > 0:
        table_df = table_df[
            table_df["county_name_acs"].isin(selected_counties)
        ]
        table_df["county_name_acs"] = (
            table_df["county_name_acs"]
            .cat.remove_unused_categories()
        )

    # Optional sorting
    table_df = table_df.sort_values(
        by=[date_col, "county_state", "county_name_acs"]
    )

    st.dataframe(
        table_df,
        use_container_width=True,
        column_config={
        "county_geoid": "County GEOID",
        "county_name_acs": "County Name",
        "county_state": "State",
        "percent_change": "Facebook Pop Change from Baseline (%)",
        "ds": "Date",
        "datetime": "Date and Time",
        "hour": "Hour",
        "n_crisis": "Facebook Population at Given Time",
        "n_baseline": "Facebook Population at 45-day Baseline",
        "total_population": "Total Population",
        "median_income": "Median Household Income",
        "poverty_rate": "Poverty Rate",
        "pct_age_65_plus": "Age 65+ Population (%)",
        "pct_no_vehicle": "Households Without Vehicle (%)",
    }
    )

    st.caption(
        f"{len(table_df):,} rows displayed"
    )
