import geopandas as gpd
from pygris import counties, states

# Counties
counties_sf = counties(
    cb=True,
    year=2023
).to_crs(4326)[
    ["STATE_NAME", "NAME", "GEOID", "geometry"]
]

counties_sf = counties_sf.rename(columns={
    "STATE_NAME": "county_state",
    "NAME": "county_name",
    "GEOID": "county_geoid"
})

# States
states_sf = states(
    cb=True,
    year=2023
).to_crs(4326)[
    ["NAME", "geometry"]
]

states_sf = states_sf.rename(columns={
    "NAME": "state_name"
})

# Save
counties_sf.to_parquet("data/counties.parquet")
states_sf.to_parquet("data/states.parquet")
counties_sf[["county_geoid", "geometry"]].to_file(
    "data/counties.geojson",
    driver="GeoJSON"
)