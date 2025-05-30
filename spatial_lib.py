# imports
import pdal
import json
import os
import time
import numpy as np
import laspy

def run_pipe_with_time(pipeline, streaming=False, chunk_size=10000):
    """
    Run a PDAL pipeline and measure the time taken.
    """
    print("Starting PDAL pipeline execution in streaming mode..." if streaming else "Starting PDAL pipeline execution...")
    start_time = time.time()
    if streaming and pipeline.streamable:
        # Execute the pipeline in streaming mode
        num_points = pipeline.execute_streaming(chunk_size)
    else:
        # Execute the pipeline in normal mode
        num_points = pipeline.execute()
    end_time = time.time()
    elapsed = end_time - start_time
    # print(pipeline.log)
    print(f"Pipeline execution complete. Processed {num_points} points in {elapsed:.2f} seconds.")


def grid_cell_stem_proxy(las_path: str, grid=2.0, height_cutoff=2.0) -> float:
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

    mask = hag > height_cutoff                              # metres
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