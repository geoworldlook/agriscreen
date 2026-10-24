"""
Konfiguracja AgriScreen v1. Jedno miejsce na wszystkie ustawienia; ścieżki względne liczone od katalogu projektu.

Wartości metod (okna, progi, okresy) pochodzą z protokołów zarejestrowanych przed liczeniem (docs/evidence/*_protokol_*.md;
numer § przy kluczu). Ich zmiana = nowa wersja protokołu, nie zwykła zmiana konfiguracji.
Użycie: cfg = make_config(project_dir, {"OUTPUT_DIR": "...", ...}).
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

CONFIG: Dict[str, Any] = {
    # --- Obszar i działki --------------------------------------------------------------------------------------------
    "PARCELS_PATH": "data/1_AOI_GBOV_CONDOM.geojson",     # działki (Typ = winnice) i stacja Condom
    "AOI_PATH": "data/1_AOI_GBOV_CONDOM_ZASIEG.geojson",  # zasięg pobierania rastrów
    "AOI_BUFFER_M": 320,
    "EPSG": 32631,
    "PARCEL_TYPE": "winnice",             # wszystkie winnice z pliku działek (fid 6–18, 21, 22)
    "MAIN_SITE": "VINEYARD_06",           # winnica 136 m od stacji ISMN Condom (punkt pogody i SWI)
    "VINEYARDS": {"VINEYARD_06": 6},
    "PANEL_REGION": "Condom · Gers, France",
    "RPG_PATH": "data/rpg_winnice.csv",   # rejestr upraw RPG (IGN) 2015–2024: przesadzenia (W3d §3)

    # --- Dane wejściowe ----------------------------------------------------------------------------------------------
    "S2_DIR": "data/01_Raw_Sentinel2",    # rastry Sentinel-2 L2A: 10 pasm [0, 1] + maska chmur + SCL
    "S2_MANIFEST": "data/00_Metadata/ingest_manifest.json",
    "S2_START_YEAR": 2016,
    "S2_CLOUD_MAX_AOI": 40,               # % chmur nad AOI (s2cloudless)
    "S2_MONTHS": (4, 10),                 # sezon winorośli; zimą NDVI to okrywa międzyrzędzi
    "ERA5_DIR": "data/02_ERA5_Land",      # ERA5-Land w punkcie (całe AOI to jedno oczko ~9 km)
    "ERA5_START": "1991-01-01",
    "SWI_DIR": "data/03_Copernicus_Auxiliary/SWI",
    "SWI_PRODUCT": "v4_0.1deg",           # CLMS SWI 0,1° v4 (2007 – dziś)
    "SWI_1KM": True,                      # zbieramy też SWI 1 km v2 (od VII 2025), bez normy
    "SECRETS_DIR": "../secrets",          # klucze tylko z folderu na Dysku obok projektu (np. cdse.env)
    "ISMN_DIR": "data/7_isismn_data",     # czujniki ISMN (SMOSMANIA Condom)
    "NETWORK": "SMOSMANIA",
    "STATION": "Condom",
    "STATION_BUFFER_M": 50,
    "REF_DIR": "data/09_Reference_Stations",
    "REF_SITES": ("FR-Aur", "FR-Lus"),    # ICOS Auradé i Lusignan (W2 + REF)
    "MF_DIR": "data/08_MeteoFrance",
    "MF_DEPTS": ["32", "47"],             # Gers + Lot-et-Garonne
    "MF_MAX_KM": 30,
    "MF_MAX_STATIONS": 3,
    "MF_MIN_COVERAGE": 0.8,

    # --- Gleba i opad (ERA5-Land, SWI) ------------------------------------------------------------------------------
    "CLIM_REF": ("1991-01-01", "2020-12-31"),   # okres odniesienia WMO
    "CLIM_HALF_WINDOW_DAYS": 15,
    "SPI_DAYS": (30, 90),                 # SPI-1 i SPI-3
    "THR_SPI1": -2.0, "THR_SPI3": -1.0,   # „suchy okres” w walidacji opadu (EDO CDI)
    "WATER_WET_PCT": 70,                  # percentyl ≥ 70: wilgotniej niż zwykle
    "SWI_DRY_PCT": 30,                    # ≤ 30: sucho (trzy klasy gleby)
    "SWI_T": 15,                          # D-075
    "SWI_T_SENS": (10, 40),               # wrażliwość na T (raportowana)
    "SWI_NORM": ("2007-01-01", "2024-12-31"),

    # --- Roślinność winnic (W3b, protokół docs/evidence/W3b_protokol_walidacji.md) ----------------------------------
    "PARCEL_PRODUCT": "S2_10m_buf20",
    "PARCEL_INNER_M": 20,                 # pas wewnętrzny 20 m (§1)
    "PARCEL_MIN_PX": 40,                  # min. pikseli 10 m po pasie (§1)
    "PARCEL_BANDS": ("B04", "B06", "B8A", "B12"),   # wariant wielopasmowy (§7)
    "PARCEL_ANOM_INDICES": ("ndmi", "crswir", "ndvi", "ndre", "b04", "b06", "b8a", "b12"),
    "PARCEL_TEST_MONTHS": (6, 9),         # testy VI–IX, karta IV–X (§1)
    "PARCEL_MIN_AREA": 6,                 # min. winnic w dniu dla mediany okolicy (§6, §8)
    "PARCEL_T3_EXCLUDE": ("VINEYARD_06",),
    "PARCEL_T3_YEARS": (2018, 2024),
    "PARCEL_ISMN_PERIOD": ("2016-01-01", "2024-12-31"),
    "PARCEL_T3_DAYS": 30,
    "PARCEL_T3_MIN_DAYS": 20,
    "PARCEL_T3_CLIP": 3.0,
    "PARCEL_RAIN_MM": 5.0,                # para scen „z opadem” (§5)
    "PARCEL_FLAG_MIN_SCENES": 6,          # flaga zmiany gospodarowania (§8)
    "PARCEL_FLAG_SHARE": 2 / 3,
    "VEG_HALF_WINDOW_DAYS": 15,           # norma: ±15 dni roku (§2)
    "VEG_MIN_REF": 5,
    "VEG_MIN_CLEAR_FRAC": 0.9,            # czysta scena: ≥ 90% pikseli bez chmur
    "VEG_MAX_AGE_DAYS": 30,               # karta: scena starsza niż 30 dni = „brak bieżącej sceny”
    "VEG_CAUSAL": True,                   # norma tylko z lat wcześniejszych
    "VEG_BY_TRACK": True,                 # ten sam tor orbity
    "VEG_PREDICTIVE_Z": True,             # z predykcyjne (rozkład t)
    "VEG_REF_YEARS": 5,                   # 5 lat wcześniejszych
    "W3B_PROTOCOL": "docs/evidence/W3b_protokol_walidacji.md",
    "W3B_FREEZE": None,                   # None = data zapisana w w3b_freeze.json przy pierwszym liczeniu

    # --- Pogoda (Météo-France, ERA5-Land, Open-Meteo) ---------------------------------------------------------------
    "WX_VAL_START": "2016-01-01",
    "WX_CAL_SPLIT_YEAR": 2021,            # próg kalibrowany na latach < 2021, oceniany na ≥ 2021
    "WX_REF_MAX_KM": 5.0,
    "WX_MIN_CAL_EVENTS": 10,
    "WX_MIN_TEST_EVENTS": 10,
    "WX_MIN_CSI_GAIN": 0.05,
    "FROST_SEASON": ("03-15", "05-15"),
    "FROST_TMIN": 0.0,
    "HEAT_SEASON": ("06-01", "08-31"),
    "HEAT_TMAX": 35.0,
    "HAZARD_YEARS": 5,                    # podsumowanie przymrozków i upałów: ostatnie 5 lat

    # --- Panel -------------------------------------------------------------------------------------------------------
    "PANEL_PIXEL_DATES": 16,              # mapy pikseli 10 m z 16 ostatnich bezchmurnych scen sezonu
    "OUTPUT_DIR": "data/05_Final_Outputs/agriwatch",   # katalog wyników (nazwa z wcześniejszych wersji: dane na Dysku)

    # --- Statystyka --------------------------------------------------------------------------------------------------
    "BOOTSTRAP_N": 1000,
    "BOOTSTRAP_BLOCK_DAYS": 30,
    "RANDOM_SEED": 42,
    "MIN_N_METRICS": 10,

    # --- Eksperymenty (domyślnie wyłączone; nie przeszły testów, powtórka po sezonie 2027) --------------------------
    # W3c: docs/evidence/W3c_protokol_strefy.md (D-090)
    "W3C_PROTOCOL": "docs/evidence/W3c_protokol_strefy.md",
    "W3C_FREEZE": None,
    "ZONES_INDICES": ("ndvi", "ndmi"),
    "ZONES_SMOOTH_MIN": 5,
    "ZONES_MIN_SCENES": 5,
    "ZONES_MIN_YEARS": 3,
    "ZONES_MIN_CELLS": 4,
    "ZONES_CONFIRM_DAYS": 10,
    "ZONES_MIN_PAIRS": 30,
    "ZONES_SPREAD_FRAC": 0.5,
    "ZONES_MAX_SHARE": 0.05,
    "ZONES_GRID_TOL_M": 1.0,
    # W3d: docs/evidence/W3d_protokol_miesiace.md (D-091)
    "W3D_PROTOCOL": "docs/evidence/W3d_protokol_miesiace.md",
    "W3D_FREEZE": None,
    "MONTHS_HISTORY_YEARS": 5,
    "MONTHS_MIN_YEARS": 4,
    "MONTHS_MIN_DAYS": 2,
    "MONTHS_MAX_RATIO": 1.5,
}

# Ścieżki do plików w repozytorium (kod, działki, czujniki ISMN, protokoły) — względem katalogu kodu
REPO_KEYS = ("PARCELS_PATH", "AOI_PATH", "RPG_PATH", "ISMN_DIR", "W3B_PROTOCOL", "W3C_PROTOCOL", "W3D_PROTOCOL")
# Ścieżki do danych poza repozytorium (sceny, cache, klucze, wyniki) — względem katalogu danych
DATA_KEYS = ("S2_DIR", "S2_MANIFEST", "ERA5_DIR", "SWI_DIR", "SECRETS_DIR", "REF_DIR", "MF_DIR", "OUTPUT_DIR")
PATH_KEYS = REPO_KEYS + DATA_KEYS


def make_config(project_dir: str, overrides: Optional[Dict[str, Any]] = None,
                data_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    CONFIG z nadpisaniami; ścieżki względne -> bezwzględne. project_dir: katalog kodu (klon repozytorium);
    data_dir: katalog danych (np. zsynchronizowany Dysk Google ...\GeoWorldLook\agriwatch). Bez data_dir dane leżą
    w katalogu kodu (układ z Colab, gdzie klon jest na Dysku).
    """
    data_dir = data_dir or project_dir
    cfg = dict(CONFIG)
    cfg.update(overrides or {})
    for keys, root in ((REPO_KEYS, project_dir), (DATA_KEYS, data_dir)):
        for k in keys:
            if not os.path.isabs(cfg[k]):
                cfg[k] = os.path.normpath(os.path.join(root, cfg[k]))
    cfg["PROJECT_DIR"] = project_dir
    cfg["DATA_ROOT"] = data_dir
    return cfg


def era5_csv(cfg: Dict[str, Any]) -> str:
    """Plik dziennej serii ERA5-Land w punkcie winnicy."""
    return os.path.join(cfg["ERA5_DIR"], "era5_land_daily.csv")


def main_site_lonlat(cfg: Dict[str, Any]):
    """Środek winnicy MAIN_SITE (lon, lat): punkt pogody, ERA5-Land i SWI."""
    import geopandas as gpd
    p = gpd.read_file(cfg["PARCELS_PATH"])
    g = p.loc[p["fid"] == cfg["VINEYARDS"][cfg["MAIN_SITE"]]].to_crs(cfg["EPSG"]).geometry.centroid
    c = g.to_crs(4326).iloc[0]
    return c.x, c.y
