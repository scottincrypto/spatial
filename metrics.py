# chm_metrics.py
import numpy as np
import rasterio
import laspy
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

###############################################################################
# 1. QUICK METRICS FROM THE CHM (GeoTIFF, 1 m pixels)
###############################################################################

def chm_summary(chm_path: Path):
    """Return % woody cover > 1 m, mean height, P90 height."""
    with rasterio.open(chm_path) as src:
        chm = src.read(1, masked=True)          # 2‑D masked array, metres
    woody_mask = chm > 1                        # dense‑woody threshold
    pct_woody = woody_mask.mean() * 100         # % of raster area
    mean_h     = float(chm.mean())              # metres
    p90_h      = float(np.percentile(chm.compressed(), 90))
    return pct_woody, mean_h, p90_h

###############################################################################
# 2. STEM‑DENSITY PROXY FROM THE POINT CLOUD (HeightAboveGround already added)
###############################################################################

def stem_density(las_path: Path, grid=2.0):
    """
    Very lightweight stem‑density proxy:
      • keep points with HeightAboveGround > 2 m (ignore grass/shrub noise)
      • drop them into a grid (default 2 × 2 m)
      • assume one stem/cluster per occupied cell
      • report stems ha⁻¹
    """
    las = laspy.read(las_path)
    try:
        hag = las['HeightAboveGround']          # PDAL wrote this extra dim
    except KeyError:
        raise RuntimeError("LAS file missing HeightAboveGround dimension")

    mask = hag > 2                              # metres
    if mask.sum() == 0:
        return 0.0

    x = las.x[mask]
    y = las.y[mask]

    # snap to grid
    gx = np.floor((x - x.min()) / grid).astype(np.int32)
    gy = np.floor((y - y.min()) / grid).astype(np.int32)
    occupied = np.unique(np.stack([gx, gy], axis=1), axis=0).shape[0]

    # area covered = raster footprint (min→max) so density is consistent
    area_m2 = (x.max() - x.min()) * (y.max() - y.min())
    area_ha = area_m2 / 10_000
    return occupied / area_ha                  # stems per hectare

###############################################################################
# 3. WRAP EVERYTHING FOR ONE DATE (EXTEND TO MANY DATES AS NEEDED)
###############################################################################

def analyse_block(date, chm_path, las_path):
    pct, mean_h, p90_h = chm_summary(chm_path)
    stems              = stem_density(las_path)
    return {
        "date": pd.to_datetime(date),
        "woody_cover_pct": pct,
        "mean_height_m": mean_h,
        "p90_height_m": p90_h,
        "stem_density_stems_per_ha": stems,
    }

###############################################################################
# 4. EXAMPLE USAGE
###############################################################################

if __name__ == "__main__":
    # ---- adjust paths & dates to suit your layout --------------------------
    records = []
    for date in ["2024‑10‑01", "2025‑02‑15", "2025‑05‑01"]:
        records.append(
            analyse_block(
                date,
                Path(f"products/{date}_chm.tif"),
                Path(f"products/{date}_hag.laz"),
            )
        )

    df = pd.DataFrame(records).set_index("date").sort_index()
    print(df.round(2))

    # quick visual: growth & cover trends
    ax = df[["mean_height_m", "p90_height_m"]].plot(marker="o")
    df["woody_cover_pct"].plot(secondary_y=True, style="--o", ax=ax)
    ax.set_ylabel("Height (m)")
    ax.right_ax.set_ylabel("Woody cover (%)")
    plt.title("Rehab block – fast progress indicators")
    plt.tight_layout()
    plt.show()
