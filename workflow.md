# Workflow

## Tile & Index the LiDAR Data
This creates an optimised file for reading to allow streaming & cloud storage and use of viz tools

Two options:
- Cloud Optimised Point Cloud (COPC)
- Entwine Point Tile (EPT)


### Entwine Point Tile (EPT)
```bash
# Build an EPT pyramid from every LAZ in ./input
entwine build 
    -i "./input/**/*.laz" \      # input files (wild‑cards / recursive)
    -o "./rehab_ept" \           # output folder that will contain ept.json, data/, ...
    --srs EPSG:7856 \            # set output CRS (GDA2020 / MGA Zone 56, metres)
    --resolution 1 \             # target voxel size ≈ mean point spacing (1 m here)
    --threads 8                  # parallel CPU threads
entwine build -i "input\rehab_sample.las" -o "output\rehab_ept" --srs EPSG:7856 --resolution 1 --threads 12
```


### Cloud Optimised Point Cloud (COPC)
```bash
# Merge every LAZ in the folder and write a spatially‑indexed COPC
pdal pipeline copc_convert.json
```
using the json file:
```json
{
    "pipeline": [
      "input\\rehab_sample.las",
      {
        "type": "filters.reprojection",
        "in_srs": "EPSG:7856",
        "out_srs": "EPSG:7856"
      },
      {
        "type": "writers.copc",
        "filename": "output\\rehab.copc.laz"
      }
    ],
    "num_threads": 12
}
```

This is now intergrated into the HAG pipeline

## Classify the ground & compute HAG

```json
{
    "pipeline": [
      {
        "type": "readers.las",
        "filename": "input/rehab_sample.las"
      },
      { 
        "type": "filters.reprojection", 
        "in_srs": "EPSG:7856", 
        "out_srs": "EPSG:7856"
      },
      {
        "type": "filters.assign",
        "assignment": "Classification[:]=0"
      },
      {
        "type": "filters.smrf",
        "ignore": "Classification[7:7]",
        "window": 18.0,
        "slope": 0.2,
        "threshold": 0.5,
        "scalar": 1.25
      },
      {
        "type": "filters.hag_nn"
      },
      { 
        "type": "filters.stats",
        "dimensions": "Classification" 
      },
      {
        "type": "writers.las",
        "filename": "output/rehab_sample_hag.las",
        "minor_version": 4,
        "dataformat_id": 6,
        "extra_dims": "HeightAboveGround=float32" 
      },
      {
        "type": "writers.copc",
        "filename": "output\\rehab.copc.laz",
        "extra_dims": "HeightAboveGround=float32" 
      }
    ]
    , "num_threads": 12
  }
  
  
```
```bash
pdal pipeline ground_hag_pipeline.json
```

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

## Generate basic stats

Run the notebook `metrics.ipynb`


