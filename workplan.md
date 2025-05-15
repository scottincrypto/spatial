# work plan

## Tasks
- [ ] move the piepline into a notebook using the python bindings for pdal
- [ ] Implement the ground filter pipe as per this: https://pdal.io/en/stable/tutorial/ground-filters.html
- [ ] Tune the SMRF filter params
- [ ] Run a selection on multiple las files - routine to select the 1000m plots which are on the rehab
- [ ] Tune and ground-truth the other parts of the CHM pipe
- [ ] Run across multiple time periods, create the time series of metrics
- [ ] segment the results by the planting domains
- [ ] See if there is value in the clipped 1000m set which has ground/low/med/high veg already in there - can I create a DTM from this? Is this better than my ground detection model?









# Appendix - o3 plan

Below is a menu of concrete AI/ML avenues you can start on right away, ordered from “quick‑win analytics” to “advanced modelling”.  Everything can be done in pure Python with PDAL + PyTorch/fastai and your existing LiDAR (\*.las/ \*.laz) and RGB imagery.  Metric units are used throughout.

---

## 1  Pre‑processing Foundation (one‑off, then reusable)

| Step | What                                                   | How (Python snippets – **no pip install lines**)                                                                                                                                                      |
| ---- | ------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1.1  | **Tile & index point clouds** so they stream from disk | `python import pdal, json; pipeline = json.loads("""{ "pipeline":[ "veg.laz", { "type":"filters.reprojection", "out_srs":"EPSG:7856" }, "ept" ] }"""); pdal.Pipeline(json.dumps(pipeline)).execute()` |
| 1.2  | **Ground/vegetation split**                            | PDAL’s `filters.smrf` (ground) then `filters.hag` to attach **H**eight **A**bove **G**round.                                                                                                          |
| 1.3  | **Raster products**                                    | `filters.dem` (DTM, 1 m), `filters.dsm` (DSM, 1 m) → CHM = DSM − DTM.  PDAL example notebook: OpenTopography workflow ([Google Colab][1]).                                                            |

You now have:

* **CHM (GeoTIFF)** – canopy height in metres.
* **Ground‑normalised point cloud** – every point has `HeightAboveGround`.

---

## 2  Fast Progress Indicators (no ML training yet)

| Metric                        | Code sketch                                        | Use‑case                                                  |
| ----------------------------- | -------------------------------------------------- | --------------------------------------------------------- |
| % area with woody cover > 1 m | `cover = (chm > 1).mean()`                         | Check whether rehab blocks meet “dense woody” thresholds. |
| Mean / P90 canopy height      | `np.percentile(chm, [50,90])`                      | Growth tracking.                                          |
| Stem density proxy            | Grid 2 × 2 m → count clusters of points with H>2 m | Quick stocktake until individual trees can be segmented.  |

Generate these time‑series per rehab block, store in a DataFrame, and a simple Matplotlib line chart already gives management‑level insight.

---

## 3  Supervised ML Building Blocks

### 3.1  2‑D CNN on raster stacks

* **Inputs**: `[CHM, RGB ortho, NDVI]` stacked to a 4‑band image tile.
* **Model**: U‑Net or DeepLab in fastai; each pixel labelled *dense woody*, *grass/shrub*, *bare ground*.
* **Label sources**:

  * Historical field plots.
  * Quick manual polygons drawn in QGIS over a few tiles → export as mask.
* **Why start here**: Low annotation effort and CNN transfer‑learning is familiar (fastai‑style). TorchGeo makes tiling, CRS harmonisation, and data loaders painless ([PyTorch][2], [GitHub][3]).

### 3.2  3‑D point‑cloud segmentation

* **Models**: RandLA‑Net (efficient for large‑scale scenes) ([ScienceDirect][4]), PointMLP or FSCT for fine plant/wood separation ([ScienceDirect][5], [Frontiers][6]).
* **Pipeline**:

  1. Sample \~ 10 k‑points patches (with ground truth) using Open3D.
  2. Train model → predict class (*wood*, *leaf*, *ground*, *other*).
  3. Post‑process to derive **stem count, crown diameter, basal area** per hectare.

### 3.3  Tree‑level object detection in imagery

* **Model**: RetinaNet or Mask‑R‑CNN on RGB orthophotos.
* **Augment features**: For each detection attach max CHM within the mask → estimate tree height & volume.

---

## 4  Multi‑Temporal Change Detection

| Technique                   | Library                                                | Idea                                                                                                                                                                                  |
| --------------------------- | ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Siamese CNN on raster pairs | TorchGeo `ChangeDataset`                               | Input = (t₁ stack, t₂ stack) → binary “change/no‑change” heat‑map.  Recent Siamese & transformer CD papers give off‑the‑shelf architectures ([ScienceDirect][7], [ScienceDirect][8]). |
| CHM differencing            | Numpy diff of yearly CHMs, cracked into 5 × 5 m cells. | Map areas where ∆height < 0.1 m yr⁻¹ → flag stagnant or die‑back zones.                                                                                                               |
| Time‑series ML              | XGBoost / LSTM on per‑cell metrics over time           | Forecast canopy closing date per block.                                                                                                                                               |

---

## 5  Dashboards & Operationalisation

* **Raster & vector outputs** → serve from a lightweight PostGIS + GeoServer or straight GeoTIFFs on an S3 bucket.
* **Visualization**:

  * Potree or Kepler.gl for interactive 3‑D web view of LiDAR.
  * Streamlit dashboard: KPI cards, trend plots, CHM layer toggle.
* **Automation**: Perfect cron:  \`python analyse\_block.py --date \$(date +%F)\` reading latest drone flight.

---

## 6  Validation & Regulatory Reporting

| Field plot metric         | Remote proxy              | Typical accuracy |
| ------------------------- | ------------------------- | ---------------- |
| Canopy cover (%)          | Pixel count from CNN mask | ±5 % absolute    |
| Mean tree height (m)      | P95 CHM per plot          | ±0.5 m           |
| Stem density (stems ha⁻¹) | Point‑cloud ITD counts    | ±15 %            |

Keep aside 20 % of plots for blind testing; report MAE / IoU per metric to auditors.

---

## 7  Next‑Week Action Plan

1. **Pre‑process one rehab block** (Section 1).
2. **Derive quick metrics** & plot growth curves (Section 2).
3. Label \~10 ha of imagery and train first U‑Net for woody cover.
4. Present dashboard mock‑up to stakeholders → agree KPI targets.

This staged approach delivers value immediately while laying foundations for richer ML (Sections 3–4).

Happy coding, and feel free to dive deeper on any block!

[1]: https://colab.research.google.com/github/OpenTopography/OT_3DEP_Workflows/blob/main/notebooks/05_3DEP_Generate_Canopy_Height_Models_User_AOI.ipynb?utm_source=chatgpt.com "05_3DEP_Generate_Canopy_Height_Models_User_AOI.ipynb - Colab"
[2]: https://pytorch.org/blog/geospatial-deep-learning-with-torchgeo/?utm_source=chatgpt.com "Geospatial deep learning with TorchGeo – PyTorch"
[3]: https://github.com/microsoft/torchgeo?utm_source=chatgpt.com "GitHub - microsoft/torchgeo: TorchGeo: datasets, samplers, transforms ..."
[4]: https://www.sciencedirect.com/science/article/pii/S0950061824044829?utm_source=chatgpt.com "Intelligent identification of rock mass structural based on point cloud ..."
[5]: https://www.sciencedirect.com/science/article/pii/S0034425724006175?utm_source=chatgpt.com "Towards a point cloud understanding framework for forest scene semantic ..."
[6]: https://www.frontiersin.org/journals/forests-and-global-change/articles/10.3389/ffgc.2025.1431603/abstract?utm_source=chatgpt.com "Efficient Tree Species Classification Using Machine and Deep Learning ..."
[7]: https://www.sciencedirect.com/science/article/pii/S1569843224002516?utm_source=chatgpt.com "Deep Siamese Network for annual change detection in Beijing using ..."
[8]: https://www.sciencedirect.com/science/article/pii/S0952197624011187?utm_source=chatgpt.com "Multi-granularity siamese transformer-based change detection in remote ..."
