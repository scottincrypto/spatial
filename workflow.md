# Workflow

## Install deps

```cmd.exe
micromamba.exe create -n geo_env -c conda-forge pdal gdal rasterio laspy[lazrs,laszip] lazrs-python pandas matplotlib numpy jupyter python=3.12 --yes
micromamba shell init --shell cmd.exe --root-prefix=C:\Users\<username>\micromamba
micromamba install -c conda-forge geopandas --yes
micromamba activate geo_env
```

## Tile & Index the LiDAR Data
This creates an optimised file for reading to allow streaming & cloud storage and use of viz tools

Two options:
- Cloud Optimised Point Cloud (COPC)
- Entwine Point Tile (EPT)

### Merge LAS to single LAZ
Merge the LAS files into a single LAZ using the many_laz.py script
Edit the script to point at the correct folders



### Cloud Optimised Point Cloud (COPC)
Open the file in QGIS.
QGIS will build a copc file with the same name `.copc.laz`
Confirm classifications & other metadata




## Generate the DSM, DTM & CHM
DTM (digital terrain model) - bare earth surface
DSM (digital surface model) - as-is surface
CHM (canopy height model) - DSM - DTM

### DSM/DTM

Iterate on the resolution by running this pipe
```json
[
    { "type":"readers.las",  "filename":"output/rehab_sample_hag.laz" },
    { "type":"writers.gdal",
      "filename":"output/count_01.tif",
      "resolution":0.1,
      "output_type":"count" }
]
```
Then look at the layer properties in QGIS and run a histogram (processing toolbox)
Heuristic:
| What to look at                                 | Guidance                                    |
| ----------------------------------------------- | ------------------------------------------- |
| **mean count ≥ 1**                              | grid is fine                                |
| > 20 % pixels with count 0 (use QGIS histogram) | grid too fine – you’ll get stripy artefacts |
| Memory / file size becomes huge                 | stay coarser or tile the raster             |


Typical Outcomes:
| Nominal spacing (from header)   | Safe raster cell size |
| ------------------------------- | --------------------- |
| 0.2 – 0.4 m (dense drone LiDAR) | 0.25 m or 0.5 m       |
| 0.5 – 0.9 m (standard airborne) | 1 m (what you have)   |
| 1 – 2 m (legacy surveys)        | 2 m or coarser        |


Then use the optimal resolution (using 0.25 based on the above)

```json
[
    {                                   // read the height‑normalised cloud
      "type": "readers.las",
      "filename": "output/rehab_sample_hag.laz"
    },
  
    {                                   // 1️⃣  DSM – max Z per 1 m cell
      "type": "writers.gdal",
      "filename": "output/dsm_0_25m.tif",
      "resolution": 0.25,
      "output_type": "max"              // top‑of‑canopy/ground
    },
  
    {                                   // keep only ground returns (Class 2)
      "type": "filters.range",
      "limits": "Classification[2:2]"
    },
  
    {                                   // 2️⃣  DTM – min Z of ground points
      "type": "writers.gdal",
      "filename": "output/dtm_0_25m.tif",
      "resolution": 0.25,               // used histogram technique from https://chatgpt.com/c/681fdf43-d69c-800d-a2ae-79417743ab02
      "output_type": "min"              // bare‑earth surface
    }
]
```
This creates a dtm.tif and dsm.tif

Then create the CHM via:
```python
python gdal_calc.py -A output/dsm_0_25m.tif -B output/dtm_0_25m.tif --calc="A-B" --outfile=output/chm_0_25m.tif --NoDataValue=-9999
```

This is now done in `generate_rasters.ipynb`

## Generate basic stats

Run the notebook `metrics.ipynb`


