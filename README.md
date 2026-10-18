# AgriScreen: vineyard drought monitoring from open Copernicus data

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/geoworldlook/agriscreen/blob/main/notebooks/AgriWatch_Monitor.ipynb)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Status](https://img.shields.io/badge/status-v1.2-green)

AgriScreen (pipeline name: **AgriWatch**) issues a 10-day drought status for one vineyard in Condom (Gers, France):
`VINEYARD_06`, 2.9 ha, 136 m from the ISMN SMOSMANIA soil-moisture station.
Every layer is validated against independent ground measurements. Each number on the dashboard comes with its error,
and anything that has not been validated is labelled as not validated.

**Skills shown:** EO time series · climate reanalysis · in-situ validation · drought indicators ·
deep-learning super-resolution (SEN2SR) · reproducible pipelines in Google Earth Engine and Colab.

## What it does

The status logic is a simplified version of the European Drought Observatory's
[Combined Drought Indicator (CDI)](https://edo.jrc.ec.europa.eu/), computed per 10-day period:

| Status | Condition | Action |
|---|---|---|
| `watch` | SPI-1 ≤ −2 or SPI-3 ≤ −1 (rainfall deficit) | watch |
| `warning` | ERA5-Land root-zone (0–100 cm) soil-moisture anomaly ≤ −1 | watch |
| `alert` | `warning` and vineyard NDVI anomaly ≤ −1 | inspect the vineyard |
| `recovery` | after `warning`/`alert`: back above thresholds, anomalies still negative | normal |

- **Vegetation:** Sentinel-2 L2A NDVI, NDMI and NDRE, super-resolved from 10 m to 2.5 m with SEN2SR.
  Anomalies are computed against the previous 5 years only (no future years) and from the same orbit track.
- **Soil moisture:** ERA5-Land, with a soil-drought probability attached to each status:
  p = Φ((−1 − ρz)/√(1−ρ²)), where ρ = 0.58 is the measured ERA5-to-station correlation.
- **Weather:** frost and heat-day warnings from ERA5-Land, validated against Météo-France stations.
- **Output:** an HTML dashboard (NDVI map, status, risk, weather, season curve, signal matrix), a text bulletin and a JSON summary.

Satellite data come only from the Copernicus programme.

## Validation

All numbers come from pipeline runs or from offline experiments that were repeated independently
([`docs/MIGRACJA_PODSUMOWANIE.md`](docs/MIGRACJA_PODSUMOWANIE.md), section 5; evidence in [`docs/evidence/`](docs/evidence/)).

| Layer | Result | Reference | Verdict |
|---|---|---|---|
| Root-zone soil moisture (ERA5-Land 0–100 cm) | R = 0.58 [0.50; 0.67], n = 2,976 days (2016–2024) | ISMN station, 20–30 cm | strong for reanalysis vs a point |
| Dry 10-day periods (soil z ≤ −1) | 57% detected, 57% false alarms | ISMN 20–30 cm | limited: this is the ceiling at R = 0.58 for a yes/no rule |
| Soil-drought probability | Brier 0.10, vs 0.17 for the yes/no rule and 0.13 for climatology | ISMN | strong, but evaluated offline and not yet in the pipeline's validation table |
| Vineyard NDVI (2.5 m) | R = 0.38 [0.16; 0.58], n = 200 days | ISMN 20–30 cm (indirect) | limited: vegetation lags soil moisture |
| 30-day rainfall / SPI-3 | R = 0.90 / 0.87; dry periods: 66% detected, 30% false alarms | Météo-France rain gauge, Condom | strong |
| Daily Tmin / Tmax | mean absolute error 1.04 / 1.09 °C | Météo-France, Condom | strong |
| Heat days (Tmax ≥ 35.5 °C) | 68% detected, 9% false alarms, n = 73 days (held-out years 2021+) | Météo-France, Condom | strong |
| Spring frost | 4 event days in the test years | Météo-France, Condom | not confirmed: too few events |
| `alert` (soil + vegetation) | 0 hits against dry ISMN periods in 2018–2024 | ISMN | not confirmed: vegetation responds 1–1.5 months later |

**Negative results, also reported:**
- No other index (NDMI, NDRE, CRSWIR, composites) and no multi-index agreement rule improves the vegetation layer.
  The indices are nearly redundant (z-score correlation 0.92–0.97). This was replicated twice.
- An FAO-56 water balance does not beat ERA5-Land. EnKF assimilation of Sentinel-1 does not improve it either.
- An earlier NDVI climatology used future years (data leakage). After the fix in v1.1, R dropped from 0.43 to 0.38.
- SEN2SR at 2.5 m gives the same validation result as 10 m, so it is used for map readability only.

**Limitations:**
- One reference station, under grass, with ISMN data only up to 2024-12-31.
- One vineyard, so there is no comparison with neighbouring plots yet.
- The `alert` layer has not been validated against vine water status.

## Architecture

```text
GitHub (code) ──► Google Colab (GPU + Google Earth Engine) ──► Google Drive (data, CSV registry, outputs)
```

```text
├── step_01_ingest.py            # GEE: Sentinel-2 L2A (incremental, manifest) + cloud mask, ERA5-Land at the point
├── step_03_super_resolve.py     # SEN2SR 10 m -> 2.5 m with quality checks (no silent fallback to interpolation)
├── step_04_metrics_alert.py     # indices, causal anomalies, SPI, 10-day status, bulletin
├── step_05_colab_run.py         # notebook control: setup_runtime, run_task, CSV registry, monitoring tasks, --selftest
├── step_06_dashboard.py         # vineyard dashboard
├── step_07_station_pipeline.py  # ISMN station: in-situ QC, anomaly validation with CIs; experimental Sentinel-1 branch
├── step_08_weather.py           # frost and heat, ERA5-Land validation on Météo-France stations
├── step_09_panels.py            # v1.2 panels: vineyard condition, season curve, signal matrix
├── step_10_reference.py         # ICOS reference stations (FR-Lus, FR-Aur): QC and one shared validation protocol
├── build_colab_master.py        # generates the notebook (the .ipynb is never edited by hand)
├── notebooks/AgriWatch_Monitor.ipynb
├── data/                        # AOI polygons, ISMN SMOSMANIA 2016–2024 (21 stations)
├── docs/                        # architecture, plans (D-xxx decisions), evidence (in Polish)
└── legacy/                      # previous version (v2.5: LST, ATPRK, TCARI/OSAVI, TVDI), not used
```

Step numbering is not continuous: step 2 of v2.5 lives in `legacy/`. Details: [`docs/ARCHITEKTURA.md`](docs/ARCHITEKTURA.md).

## How to run

1. Open `notebooks/AgriWatch_Monitor.ipynb` in Colab **from GitHub** (badge above), not from a Drive copy.
   A GPU runtime is needed only for new scenes (super-resolution).
2. Choose *Run all*. The notebook mounts Drive, clones or updates the repository, installs packages,
   initialises Earth Engine and runs:
   `ingest_s2 → ingest_era5 → scene_stats → anomalies → validate → weather → bulletin → dashboard → summary`.
3. Outputs: `data/05_Final_Outputs/agriwatch/` (`dashboard.html`, bulletin, plots, `agriwatch_latest.json`)
   and the registry tables `data/registry/gwl_*.csv`.

Offline tests (no GEE or GPU; real ISMN data and plots, synthetic satellite and Météo-France data):

```bash
python step_05_colab_run.py --selftest --out <dir>   # about 6 min
python step_08_weather.py
python step_07_station_pipeline.py --selftest         # Sentinel-1 branch (needs pytesmo)
```

**Dependencies:** `earthengine-api geemap geedim rasterio geopandas numpy pandas scipy matplotlib pytesmo ismn`;
for super-resolution also `sen2sr mlstac torch`.

## Versions and roadmap

| Version | Scope |
|---|---|
| 1.0 (2026-10-07) | EDO-style status from SPI, ERA5-Land soil moisture and 2.5 m NDVI; ISMN validation; dashboard |
| 1.1 (2026-10-09) | causal vegetation climatology, same orbit track, predictive z-scores, soil-drought probability; frost and heat with Météo-France validation |
| 1.2 (2026-10-09) | vineyard condition panel (NDVI, NDRE, NDMI), season curve, signal matrix |

Next ([`docs/plans/Plan_v8_cloud_native_dl.md`](docs/plans/Plan_v8_cloud_native_dl.md)):
- a cloud-native pipeline (STAC from Copernicus Data Space, xarray, Docker, GitHub Actions) that runs without Colab;
- a deep-learning stage: super-resolution validated against orthophotos, and a U-Net for vine rows on IGN CIR 20 cm imagery.

## Data and attribution

Copernicus Sentinel-2 (ESA), ERA5-Land (Copernicus Climate Change Service), ISMN SMOSMANIA (Météo-France / ISMN),
Météo-France station data, SEN2SR super-resolution model.

## License

[MIT](LICENSE)

---

Documentation in [`docs/`](docs/) is in Polish; a Polish version of this page is in [`docs/README_pl.md`](docs/README_pl.md).
