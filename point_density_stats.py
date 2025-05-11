import json, subprocess, math

info = subprocess.check_output(
    ["pdal", "info", "--summary", "output/rehab_sample_hag.laz"]
)
density = json.loads(info)["summary"]["density"]  # points per m²
opt_cell = round(1 / math.sqrt(density), 2)  # ≈ average spacing
print(f"Average spacing ≈ {opt_cell} m")
