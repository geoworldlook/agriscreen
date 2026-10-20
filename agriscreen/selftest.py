"""
Test AgriScreen v1 bez sieci i bez kluczy:  python -m agriscreen.selftest [--out KATALOG]

1. Dane syntetyczne (stałe ziarna): ERA5-Land 1991–2024, stacja Météo-France 5 km od winnicy, SWI z udawanego
   Copernicus Data Space, poziomy wilgotności z udawanego portalu ICOS i 126 scen Sentinel-2 (IV–X 2016–2024, dwie
   w miesiącu) na prawdziwych granicach 15 winnic. W 2024 r. winnica fid 7 dostaje sygnał (B11 +0,10), który ma
   wywołać flagę zmiany gospodarowania. Czujnik ISMN Condom i działki są prawdziwe (z repozytorium).
2. Zadania v1 przez run_task, tak jak w Colab, oraz eksperymenty W3c i W3d.
3. Sprawdzenie plików wynikowych (check_*) i testy jednostkowe modułów (unit_tests).
Wyniki trafiają wyłącznie do KATALOG (domyślnie data/_selftest).
"""

from __future__ import annotations

import argparse
import gzip
import io
import json
import logging
import os
import shutil
import zipfile
from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd

from agriscreen import experiments, metrics, parcel, pipeline
from agriscreen.config import era5_csv, make_config
from agriscreen.runtime import registry_read, run_task

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORBIDDEN = ("stres wodny", "wczesne ostrzeżenie", "early warning", "irrigate", "podlej")   # D-087: bez porad


# ==============================================================================
# I. DANE SYNTETYCZNE
# ==============================================================================

def make_inputs(out_dir: str) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """Katalog testu z danymi wejściowymi. Zwraca (rt, cfg, atrapy usług: cdse, icos, era5_fetch)."""
    import geopandas as gpd
    from rasterio.features import geometry_mask
    from rasterio.transform import from_origin
    from agriscreen import ingest

    shutil.rmtree(out_dir, ignore_errors=True)
    rt = {"PROJECT_DIR": PROJECT_DIR, "REGISTRY_DIR": os.path.join(out_dir, "registry"), "GIT_COMMIT": "selftest"}
    cfg = make_config(PROJECT_DIR, {k: os.path.join(out_dir, v) for k, v in (
        ("S2_DIR", "s2"), ("ERA5_DIR", "era5"), ("OUTPUT_DIR", "out"), ("MF_DIR", "mf"), ("SWI_DIR", "swi"),
        ("SECRETS_DIR", "secrets"), ("REF_DIR", "ref"))})
    cfg["BOOTSTRAP_N"] = 200
    rng = np.random.default_rng(1)

    # ERA5-Land 1991–2024: cykl roczny + szum AR(1); opad gamma
    days = pd.date_range("1991-01-01", "2024-12-31", freq="D")
    seas = np.cos(2 * np.pi * (days.dayofyear.to_numpy() - 30) / 365.25)
    ar = np.zeros(len(days))
    for i in range(1, len(days)):
        ar[i] = 0.97 * ar[i - 1] + rng.normal(0, 0.01)
    era5 = pd.DataFrame({"time": days, "sm_l1": 0.25 + 0.08 * seas + ar, "sm_l2": 0.27 + 0.06 * seas + 0.8 * ar,
                         "sm_l3": 0.30 + 0.04 * seas + 0.6 * ar, "precip_mm": rng.gamma(0.4, 6.0, len(days)),
                         "t2m_min_c": 8 - 6 * seas + rng.normal(0, 3, len(days)), "t2m_c": 13 - 7 * seas,
                         "t2m_max_c": 18 - 9 * seas + rng.normal(0, 3, len(days))})
    os.makedirs(cfg["ERA5_DIR"], exist_ok=True)
    era5.to_csv(era5_csv(cfg), index=False)

    # Stacja Météo-France 5 km od winnicy: Tmin 1 °C chłodniej niż ERA5; ERA5 w jej punkcie w cache
    os.makedirs(os.path.join(cfg["MF_DIR"], "era5_32999001"), exist_ok=True)
    mf = pd.DataFrame({"NUM_POSTE": "32999001", "NOM_USUEL": "SELFTEST", "LAT": 43.98, "LON": 0.37, "ALTI": 100,
                       "AAAAMMJJ": days.strftime("%Y%m%d").astype(int), "RR": (era5["precip_mm"] * 1.1).round(1),
                       "QRR": 1, "TN": (era5["t2m_min_c"] - 1 + rng.normal(0, 1, len(days))).round(1), "QTN": 1,
                       "TX": (era5["t2m_max_c"] + rng.normal(0, 1, len(days))).round(1), "QTX": 1})
    with gzip.open(os.path.join(cfg["MF_DIR"], "Q_32_previous-1950-2023_RR-T-Vent.csv.gz"), "wt") as f:
        mf.to_csv(f, sep=";", index=False)
    era5.to_csv(os.path.join(cfg["MF_DIR"], "era5_32999001", "era5land_19910101_20250101.csv"), index=False)

    # Klucze w syntetycznym folderze secrets (nigdy prawdziwe)
    os.makedirs(cfg["SECRETS_DIR"], exist_ok=True)
    with open(os.path.join(cfg["SECRETS_DIR"], "cdse.env"), "w") as f:
        f.write("CDSE_CLIENT_ID=selftest\nCDSE_CLIENT_SECRET=selftest\n")
    rz = metrics.rootzone(era5.set_index("time"))
    fakes = {"cdse": _fake_cdse(rz), "icos": _fake_icos(rz), "era5_fetch": lambda *a, **k: era5}

    # Sceny Sentinel-2 (12 pasm jak z GEE: 10 pasm, maska chmur, SCL) na siatce obejmującej wszystkie winnice
    parcels = gpd.read_file(cfg["PARCELS_PATH"]).to_crs(cfg["EPSG"])
    x0, y0, x1, y1 = parcels.total_bounds
    x0, y1 = np.floor(x0 / 10) * 10 - 200, np.ceil(y1 / 10) * 10 + 200
    w, h = int((x1 - x0 + 400) / 10) + 1, int((y1 - y0 + 400) / 10) + 1
    prof = {"driver": "GTiff", "crs": f"EPSG:{cfg['EPSG']}", "transform": from_origin(x0, y1, 10, 10),
            "width": w, "height": h, "count": 12, "dtype": "float32"}
    os.makedirs(cfg["S2_DIR"], exist_ok=True)
    m7 = geometry_mask([parcels.loc[parcels["fid"] == 7].geometry.iloc[0]], out_shape=(h, w),
                       transform=prof["transform"], invert=True)
    ar_s = pd.Series(ar, index=days)
    for year in range(2016, 2025):
        for month in range(4, 11):
            for day in (5, 20):
                t = pd.Timestamp(year=year, month=month, day=day, hour=10, minute=50)
                anom = float(ar_s.loc[t.normalize()])
                ndvi = 0.35 + 0.25 * np.sin(np.pi * (t.dayofyear - 90) / 200) + 2.0 * anom
                red = np.full((h, w), 0.08) + rng.normal(0, 0.005, (h, w))
                nir = red * (1 + ndvi) / (1 - ndvi)
                arr = np.stack([red * 0.8, red * 0.9, red, red * 1.5, nir * 0.7, nir * 0.9, nir, nir,
                                np.full((h, w), 0.25 - anom), np.full((h, w), 0.18 - anom),
                                np.zeros((h, w)), np.full((h, w), 4.0)]).astype("float32")
                if year == 2024:
                    arr[8][m7] += 0.10                # B11: sygnał tylko w winnicy fid 7
                ingest.write_geotiff(arr, prof, os.path.join(cfg["S2_DIR"], f"S2_L2A_{t:%Y%m%d_%H%M%S}.tif"))
    return rt, cfg, fakes


class _Resp:
    def __init__(self, js: Any = None, content: bytes = b""):
        self.status_code, self._js, self.content, self.text = 200, js, content, ""

    def json(self) -> Any:
        return self._js


def _fake_cdse(rz: pd.Series) -> Any:
    """Udawany Copernicus Data Space (SWI): gleba syntetycznego ERA5 przeskalowana do 0–100 + szum;
    po 2024 r. mediana dnia roku."""
    swi = 100 * (rz - rz.min()) / (rz.max() - rz.min())
    swi_doy = swi.groupby(swi.index.dayofyear).median()
    rng = np.random.default_rng(7)

    class FakeCdse:
        def post(self, url, data=None, json=None, headers=None, timeout=None):
            if "token" in url:
                return _Resp({"access_token": "T"})
            t0 = pd.Timestamp(json["aggregation"]["timeRange"]["from"][:10])
            t1 = pd.Timestamp(json["aggregation"]["timeRange"]["to"][:10])
            rows = []
            for d in pd.date_range(t0, t1, freq="D"):
                v = float(np.clip(swi.get(d, swi_doy[d.dayofyear]) + rng.normal(0, 2), 0, 100))
                bands = {f"B{k}": {"stats": {"mean": v, "sampleCount": 1, "noDataCount": 0}} for k in range(8)}
                rows.append({"interval": {"from": f"{d:%Y-%m-%d}T00:00:00Z"}, "outputs": {"swi": {"bands": bands}}})
            return _Resp({"data": rows})

    return FakeCdse()


def _fake_icos(rz: pd.Series) -> Any:
    """Udawany portal ICOS: poziomy SWC (%) z gleby syntetycznego ERA5 + szum, co pół godziny 2022–2024.
    FR-Lus: L2 do 30 XI 2024, NRT od 1 XI 2024 (po końcu L2 wchodzi tylko grudzień)."""
    hh = pd.date_range("2022-01-01 00:30", "2025-01-01 00:00", freq="30min")
    rng = np.random.default_rng(11)
    rz_hh = rz.reindex((hh - pd.Timedelta(minutes=15)).floor("D")).to_numpy() * 100

    def icos_zip(n_levels: int, t0: str, t1: str) -> bytes:
        sel = (hh >= pd.Timestamp(t0)) & (hh <= pd.Timestamp(t1))
        d = pd.DataFrame({"TIMESTAMP_START": (hh[sel] - pd.Timedelta(minutes=30)).strftime("%Y%m%d%H%M"),
                          "TIMESTAMP_END": hh[sel].strftime("%Y%m%d%H%M")})
        for k in range(1, n_levels + 1):
            d[f"SWC_{k}"] = (rz_hh[sel] + k * 0.5 + rng.normal(0, 0.3, int(sel.sum()))).round(2)
        b = io.BytesIO()
        with zipfile.ZipFile(b, "w") as z:
            z.writestr("meteo.csv", d.to_csv(index=False))
        return b.getvalue()

    files = {"FR-Aur_L2": icos_zip(5, "2022-01-01", "2025-01-01"),
             "FR-Lus_L2": icos_zip(6, "2022-01-01", "2024-12-01 00:00"),
             "FR-Lus_NRT": icos_zip(6, "2024-11-01", "2025-01-01")}

    class FakeIcos:
        def post(self, url, data=None, headers=None, timeout=None):
            site = "FR-Aur" if "ES_FR-Aur" in data["query"] else "FR-Lus"
            kind = "NRT" if '"ETC NRT Meteo"' in data["query"] else "L2"
            oid = f"{site}_{kind}"
            if oid not in files:
                return _Resp({"results": {"bindings": []}})
            return _Resp({"results": {"bindings": [{"d": {"value": f"https://meta.icos-cp.eu/objects/{oid}"},
                                                    "fn": {"value": f"{oid}.zip"},
                                                    "start": {"value": "2022-01-01T00:00:00Z"},
                                                    "end": {"value": "2025-01-01T00:00:00Z"}}]}})

        def get(self, url, cookies=None, timeout=None):
            return _Resp(content=files[url.rsplit("/", 1)[-1]])

    return FakeIcos()


# ==============================================================================
# II. PRZEBIEG ZADAŃ
# ==============================================================================

def run_tasks(rt: Dict[str, Any], cfg: Dict[str, Any], fakes: Dict[str, Any], with_experiments: bool = True) -> None:
    """Zadania v1 w kolejności run_all (bez pobierania S2 i ERA5), z atrapami usług; eksperymenty przed panelem."""
    kwargs = {"ingest_swi": {"session": fakes["cdse"]},
              "reference": {"cdse_session": fakes["cdse"], "icos_session": fakes["icos"],
                            "era5_fetch": fakes["era5_fetch"]},
              "weather": {"fetch": False}, "panel": {"forecast": False}}
    for name, fn in pipeline.TASKS:
        if name in ("ingest_s2", "ingest_era5"):
            continue
        if name == "panel" and with_experiments:
            run_task(rt, "zones", experiments.task_zones, rt, cfg, raise_errors=True)
            run_task(rt, "months", experiments.task_months, rt, cfg, raise_errors=True)
        run_task(rt, name, fn, rt, cfg, raise_errors=True, **kwargs.get(name, {}))


# ==============================================================================
# III. SPRAWDZENIE WYNIKÓW
# ==============================================================================

def _out(cfg: Dict[str, Any], name: str) -> str:
    return os.path.join(cfg["OUTPUT_DIR"], name)


def check_repeat(rt: Dict[str, Any], cfg: Dict[str, Any]) -> None:
    """Drugie uruchomienie nie liczy ponownie statystyk działek ani testów W3b (ten sam kod i zamrożenie)."""
    res_p = run_task(rt, "parcel_stats_repeat", pipeline.task_parcel_stats, rt, cfg, raise_errors=True)
    res_t = run_task(rt, "parcel_tests_repeat", pipeline.task_parcel_tests, rt, cfg, raise_errors=True)
    assert res_p["skipped"] and res_t["skipped"], (res_p, res_t)
    print("[OK] Powtórne uruchomienie: statystyki działek i testy W3b pominięte.")


def check_w3b(rt: Dict[str, Any], cfg: Dict[str, Any]) -> None:
    """Moja winnica (W3b): 15 winnic z pasem 20 m, QC 13 z 15, anomalie, flaga z wstrzykniętego sygnału (fid 7, 2024),
    testy zamrożone z kryteriami i SHA-256 protokołu."""
    obs = registry_read(rt, "gwl_observations")
    pobs = obs[obs["product"] == cfg["PARCEL_PRODUCT"]]
    assert set(obs["product"]) == {cfg["PARCEL_PRODUCT"]}, set(obs["product"])
    assert pobs["site_id"].nunique() == 15 and set(pobs["variable"]) == {
        "ndvi", "ndmi", "ndre", "crswir", "b04", "b06", "b8a", "b12", "clear_frac"}, set(pobs["variable"])
    qc = pd.read_csv(_out(cfg, "parcel_qc.csv")).set_index("site_id")
    assert set(qc.index[~qc["qc_ok"]]) == {"VINEYARD_16", "VINEYARD_18"} and 134 <= qc.loc["VINEYARD_06", "n_pixels"] <= 142
    pa = pd.read_csv(_out(cfg, "parcel_anomalies.csv"), parse_dates=["time"])
    assert pa["site_id"].nunique() == 15 and (pa["index"] == "water").any() and "n_ref_years" in pa, pa.columns
    fl = pd.read_csv(_out(cfg, "parcel_flags.csv"))
    f7 = fl[(fl["site_id"] == "VINEYARD_07") & (fl["year"] == 2024)]
    assert len(f7) and f7["flag"].iat[0] == "-" and f7["d_median"].iat[0] < -1, f7
    assert not fl[fl["site_id"] == "VINEYARD_06"]["flag"].astype(str).isin(["-", "+"]).any(), fl
    tests = pd.read_csv(_out(cfg, "w3b_tests.csv"))
    kt = tests.set_index("key")
    assert {"t1_main", "t2_g5", "t2_g13", "t3_main", "p7_accept"} <= set(kt.index.dropna()), set(kt.index)
    assert set(tests.loc[tests["criterion"], "key"]) == {"t3_main", "p7_accept"}, tests[tests["criterion"]]
    assert (kt.loc[["t2_g5", "t2_g13"], "verdict"] == "za mało par").all()   # sceny co 15–16 dni: brak par G5 / G13
    proto = parcel.protocol_sha(cfg["W3B_PROTOCOL"])
    assert proto["status"] == "REGISTERED" and tests["protocol_sha256"].iat[0] == proto["sha256"] == proto["registered"]
    assert tests["freeze"].iat[0] == "2024-10-20" and int(tests["scenes"].iat[0]) == 126, tests[["freeze", "scenes"]].iloc[0]
    assert (tests["subset"] == "P4 krok d: S2_10m_buf20, czujnik po A4").any(), "brak drabinki wartości „przed”"
    assert tests["code_commit"].iat[0] == rt["GIT_COMMIT"]
    n_main = int(kt.loc["t3_main", "n"])
    same = tests[tests["subset"].isin(["ERA5-Land 0–100 cm zamiast czujnika", "SWI zamiast czujnika"])]
    assert len(same) == 2 and (same["n"] == n_main).all(), (n_main, same[["subset", "n"]])   # te same dni co T3 (§6)
    assert kt.loc["p7_rho_multi", "verdict"] == "zdanie 3: nie" or kt.loc["p7_accept", "verdict"] == "przyjęty"
    reg = registry_read(rt, "gwl_validation_metrics")
    assert (reg["segment"] == "T3").any() and (reg["site_id"] == parcel.AREA).any()
    t3 = kt.loc["t3_main"]
    print(f"[OK] W3b: 15 winnic (QC 13), flaga VINEYARD_07 2024 „−”, testy zamrożone ({len(tests)} wierszy; "
          f"T3 na danych syntetycznych: ρ = {t3['value']:.2f}, {t3['verdict']}).")


def check_water_and_weather(cfg: Dict[str, Any]) -> None:
    """Gleba (ERA5-Land, SWI), walidacja W2 + REF na 3 stacjach i pogoda Météo-France."""
    for prod in ("v4_0.1deg", "v2_1km"):
        assert os.path.exists(os.path.join(cfg["SWI_DIR"], f"swi_{prod}_point.csv")), prod
    soil = pd.read_csv(_out(cfg, "era5_daily_anomalies.csv"), header=[0, 1], index_col=0, parse_dates=True)
    assert ("ERA5L_SM_RZ", "percentile") in soil and soil.index[-1] == pd.Timestamp("2024-12-31"), soil.columns
    rv = pd.read_csv(_out(cfg, "validation_reference.csv"))
    assert {"SMOSMANIA_Condom", "FR-Aur", "FR-Lus"} <= set(rv["site_id"]), set(rv["site_id"])
    assert {f"ISMN_20_30cm_A4{v}" for v in ("W1", "W2", "W3", "W1_05WP", "W1_015")} <= set(rv["reference"])
    assert (rv["segment"] == "anomaly_clim_from_2020-10-19").any() and "ICOS_FR-Lus_0_100cm" in set(rv["reference"])
    lus = rv[(rv["reference"] == "ICOS_FR-Lus_20_30cm") & (rv["segment"] == "anomaly_35d") & (rv["metric"] == "pearson_r")]
    assert set(lus["product"]) == {"ERA5L_SM_RZ", "SWI_v4_T015", "SWI_v4_T010", "SWI_v4_T040"}, lus
    r_lus = lus.set_index("product").loc["ERA5L_SM_RZ", "value"]
    assert r_lus > 0.5, lus
    rcur = json.load(open(_out(cfg, "reference_current.json"), encoding="utf-8"))
    assert not rcur["errors"] and rcur["current"]["FR-Lus"]["products"]["ERA5L_SM_RZ"]["class"], rcur
    assert rcur["current"]["FR-Aur"] == {}, "kontrola bieżąca tylko na stacji z danymi bieżącymi (protokół §6)"
    rqc = pd.read_csv(_out(cfg, "validation_reference_qc.csv"))
    assert int(rqc[rqc["site"] == "FR-Lus"]["nrt_days"].iat[0]) == 31, rqc
    wv = pd.read_csv(_out(cfg, "validation_weather.csv"))
    b = wv[(wv["product"] == "ERA5L_TMIN") & (wv["period"] == "all") & (wv["metric"] == "bias")]["value"].iat[0]
    assert abs(b - 1.0) < 0.1, b                    # ERA5 cieplejsze o 1 °C od stacji
    thr = json.load(open(_out(cfg, "hazard_thresholds.json")))
    assert 0.0 <= thr["frost"] < 2.0 and thr["reference"] == "MF_32999001", thr
    print(f"[OK] Woda i pogoda: {len(rv)} metryk W2 + REF (FR-Lus ERA5 R anomalii 35 d = {r_lus:.2f}, dane "
          f"syntetyczne), {len(wv)} metryk Météo-France, progi {thr}.")


def check_experiments(rt: Dict[str, Any], cfg: Dict[str, Any]) -> None:
    """W3c i W3d: testy z SHA-256 zarejestrowanych protokołów, kryterium pokazania dla NDVI i NDMI.
    Sceny syntetyczne są co 15–16 dni, więc W3c nie ma par do testu szumu („1: za mało par”)."""
    from agriscreen.experiments import months, zones
    for key, mod, crit in (("W3C_PROTOCOL", zones, "z_show"), ("W3D_PROTOCOL", months, "d_show")):
        t = pd.read_csv(_out(cfg, mod.TESTS_NAME))
        proto = parcel.protocol_sha(cfg[key])
        assert proto["status"] == "REGISTERED" and proto["sha256"] == proto["registered"], proto
        assert (t["protocol_sha256"] == proto["sha256"]).all() and t["code_commit"].iat[0] == rt["GIT_COMMIT"]
        assert {f"{crit}_ndvi", f"{crit}_ndmi"} <= set(t["key"].dropna()), set(t["key"])
    zc = pd.read_csv(_out(cfg, zones.TESTS_NAME)).set_index("key").loc[["z_show_ndvi", "z_show_ndmi"]]
    assert (zc["value"] == 0).all() and zc["verdict"].str.contains("1: za mało par").all(), zc["verdict"]
    st = zones.load_store(_out(cfg, zones.STORE_NAME))
    assert len(st["sites"]) == 13 and len(st["scenes"]) >= 100 and not st["skipped"], (len(st["sites"]), st["skipped"])
    mo = months.load_months(cfg["OUTPUT_DIR"])
    assert len(mo["sites"]) == 13 and len(mo["months"]) > 20, (len(mo["sites"]), len(mo["months"]))
    sel = mo["site_idx"] == mo["sites"].index("VINEYARD_13")              # RPG: przesadzenie w 2019–2020
    for m in ("2019-07", "2020-07"):
        if m in mo["months"]:
            c = mo["codes_ndvi"][mo["months"].index(m)][sel]
            assert set(np.unique(c)) <= {months.REPLANT, months.NO_DATA}, (m, np.unique(c))
    print(f"[OK] Eksperymenty: W3c {len(st['scenes'])} scen × 13 winnic („za mało par”), W3d {len(mo['months'])} "
          f"miesięcy, reset po przesadzeniu VINEYARD_13; testy z zarejestrowanymi protokołami.")


def check_panel(cfg: Dict[str, Any], with_experiments: bool = True) -> None:
    """Panel (produkt): 15 winnic, warstwy, mapy pikseli 10 m, karty EN, pogoda, „How far to trust it” bez warstw
    eksperymentów i bez słów zakazanych."""
    html = open(_out(cfg, "panel.html"), encoding="utf-8").read()
    pdata = json.load(open(_out(cfg, "panel_data.json"), encoding="utf-8"))
    assert "How far to trust it" in html and len(pdata["map"]["shapes"]) == 15 and len(pdata["cards"]) == 15
    assert set(pdata["layers"]) == {"water", "ndvi", "ndre", "ndmi", "crswir"} and pdata["dates"], pdata["layers"].keys()
    assert not {"zones", "months"} & set(pdata), "panel v1 nie rysuje warstw eksperymentów"
    px = pdata["pixels"]
    assert px["dates"] and set(px["dates"][0]["png"]) == {"ndvi", "ndre", "ndmi", "ndvi_rel", "ndre_rel", "ndmi_rel"} \
        and px["rgb"] and px["bounds"], "mapy pikseli 10 m, strefy wobec mediany działki, barwy naturalne"
    st6 = px["dates"][0]["stats"]["VINEYARD_06"]["ndvi"]
    assert st6 is not None and st6[1] <= st6[0] <= st6[2] and st6[3] > 0, st6
    rel6 = px["dates"][0]["stats"]["VINEYARD_06"]["ndvi_rel"]      # p10 ≤ 0 ≤ p90 wokół mediany działki
    assert rel6 is not None and rel6[1] <= 0 <= rel6[2] and rel6[3] > 0, rel6
    assert pdata["weather"].get("last10") and "forecast" not in pdata["weather"] and pdata["soil_now"], pdata["weather"]
    assert "unpkg.com/leaflet@1.9.4" in html and ".leaflet-pane" in html and "World_Imagery" in html
    status = {r["what"]: r["status"] for r in pdata["trust"]}
    w3c = [s for w, s in status.items() if w.startswith("Zones vs usual")]
    w3d = [s for w, s in status.items() if w.startswith("Lowest in N years")]
    if with_experiments:                           # W3c bez par do testu szumu; W3d dowolny wynik, ale tylko wiersz
        assert w3c == ["experimental, not shown"] * 2, w3c
        assert len(w3d) == 2 and set(w3d) <= {"experimental, passed", "experimental, not shown"}, w3d
    else:
        assert not w3c and not w3d, (w3c, w3d)
    assert status["Vine water stress"] == "not validated" and pdata["cards"][cfg["MAIN_SITE"]]["sentences"]
    ex = pdata["explore"]["t1_by_soil"]["rows"]
    assert [r["soil"] for r in ex] == ["dry", "normal", "wet"] and sum(r["n"] for r in ex) > 0, ex
    for txt in (html, json.dumps(pdata, ensure_ascii=False), open(_out(cfg, "run_summary.md"), encoding="utf-8").read()):
        low = txt.lower()
        assert not any(w in low for w in FORBIDDEN), [w for w in FORBIDDEN if w in low]
    smd = open(_out(cfg, "run_summary.md"), encoding="utf-8").read()
    assert "## Testy W3b (zamrożone)" in smd and "## Walidacja warstwy wody" in smd and "## Pogoda" in smd, smd[:800]
    print(f"[OK] Panel: 15 winnic, {len(px['dates'])} map pikseli, {len(pdata['trust'])} wierszy „How far to trust it”, "
          f"{os.path.getsize(_out(cfg, 'panel.html')) // 1024} kB.")


# ==============================================================================
# IV. TESTY JEDNOSTKOWE
# ==============================================================================

def unit_tests(cfg: Dict[str, Any], out_dir: str) -> None:
    """Testy jednostkowe modułów na danych syntetycznych (każdy moduł ma własny _selftest)."""
    from agriscreen import card, ingest, reference, weather
    from agriscreen.experiments import months, zones
    ingest._selftest_swi()
    reference._selftest()
    weather._selftest(os.path.join(out_dir, "unit_weather"))
    card._selftest_parcel(cfg)
    parcel._selftest(cfg)
    zones._selftest(cfg)
    months._selftest(cfg)
    print("[OK] Testy jednostkowe: ingest (SWI), reference, weather, card, parcel, zones, months.")


def main(out_dir: str) -> None:
    rt, cfg, fakes = make_inputs(out_dir)
    run_tasks(rt, cfg, fakes)
    check_repeat(rt, cfg)
    check_w3b(rt, cfg)
    check_water_and_weather(cfg)
    check_experiments(rt, cfg)
    check_panel(cfg)
    unit_tests(cfg, out_dir)
    print(f"[OK] Selftest AgriScreen v1 zakończony. Wyniki: {cfg['OUTPUT_DIR']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="AgriScreen v1: test bez sieci na danych syntetycznych")
    ap.add_argument("--out", default=os.path.join(PROJECT_DIR, "data", "_selftest"))
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    main(ap.parse_args().out)
