# make_animation.py

import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import imageio.v2 as imageio
from pathlib import Path
import json
from matplotlib.colors import TwoSlopeNorm
import time

OUTPUTS_DIR = Path("./outputs")
FRAME_DIR = Path("./frames")
FRAME_DIR.mkdir(exist_ok=True)

# -------------------------
# Load data
# -------------------------
df = pd.read_parquet(
    OUTPUTS_DIR / "tk_facebook_pop_aggregated_bing.parquet"
)

with open("data/counties.geojson") as f:
    county_geojson = json.load(f)

counties = gpd.read_file("data/counties.geojson")

# Ensure consistent key types
df["county_geoid"] = df["county_geoid"].astype(str)
counties["county_geoid"] = counties["county_geoid"].astype(str)

# -------------------------
# Create datetime column
# -------------------------
df["datetime"] = pd.to_datetime(
    df["ds"].astype(str) + " " +
    df["hour"].astype(str).str.zfill(4),
    format="%Y-%m-%d %H%M"
)

times = sorted(df["datetime"].unique())

# -------------------------
# Pre-merge static geometry once (IMPORTANT speedup)
# -------------------------
base_geo = counties[["county_geoid", "geometry"]]
#bounds = counties.total_bounds
#print(f"Map bounds: {bounds}")

vmin = df["percent_change"].min()
vmax = df["percent_change"].max()
norm = TwoSlopeNorm(vmin=vmin, vcenter=0, vmax=vmax)

# -------------------------
# Frame generation loop
# -------------------------
for i, dt in enumerate(times):

    start_time = time.time()
    print(f"Processing frame {i+1}/{len(times)}: {dt}")

    current = df[df["datetime"] == dt]

    merged = base_geo.merge(
        current,
        on="county_geoid",
        how="left"
    )

    fig, ax = plt.subplots(figsize=(16, 9))

    merged.plot(
        column="percent_change",
        cmap="RdBu",
        norm=norm,
        linewidth=0.1,
        edgecolor="black",
        legend=True,
        ax=ax,
        missing_kwds={"color": "lightgrey"}
    )

    # 🔒 FIXED VIEWPORT (CRITICAL)
    ax.set_xlim(-95, -75)
    ax.set_ylim(30, 50)

    ax.set_axis_off()
    ax.set_title(str(dt), fontsize=14)

    frame_path = FRAME_DIR / f"frame_{i:04d}.png"
    plt.savefig(frame_path, dpi=128)
    plt.close()

    end_time = time.time()
    print(f"Frame {i+1} done in {end_time - start_time:.2f} seconds")

# -------------------------
# Create video
# -------------------------
frames = sorted(FRAME_DIR.glob("*.png"))

with imageio.get_writer("storm_animation.mp4", fps=5) as writer:
    for frame in frames:
        writer.append_data(imageio.imread(frame))

print("Video saved: storm_animation.mp4")