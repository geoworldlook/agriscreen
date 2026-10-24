"""
Zadania AgriScreen v1 w kolejności uruchamiania (`run_all`). Każde zadanie: fn(rt, cfg) -> {"message", ...};
run_task zapisuje wynik w rejestrze gwl_runs, a błąd jednego zadania nie zatrzymuje kolejnych.

  1. ingest_s2         rastry Sentinel-2 L2A (GEE), przyrostowo
  2. ingest_era5       ERA5-Land 1991 → dziś w punkcie winnicy
  3. ingest_swi        satelitarny SWI (CLMS)
  4. parcel_stats      statystyki 15 winnic z pasem 20 m (gwl_observations)
  5. soil              anomalie ERA5-Land: wilgotność 0–7 i 0–100 cm, SPI-1, SPI-3 (era5_daily_anomalies.csv)
  6. parcel_tests      testy W3b zamrożone (T1–T3, wariant wielopasmowy) — liczone raz na wersję kodu
  7. parcel_anomalies  anomalie winnic wobec własnej historii, mediana okolicy, flaga zmiany gospodarowania
  8. reference         walidacja warstwy wody na 3 stacjach (W2 + REF)
  9. weather           Météo-France: walidacja ERA5-Land, progi przymrozku i upału, zdarzenia sezonu
 10. panel             panel.html + panel_data.json (produkt)
 11. summary           run_summary.md (raport z uruchomienia)
Eksperymenty (W3c, W3d) tylko przy run_all(..., experiments=True).
"""

from __future__ import annotations

import glob
import json
import os
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from agriscreen import card, ingest, metrics, parcel, reference, stations, weather
from agriscreen.config import era5_csv, main_site_lonlat, make_config
from agriscreen.runtime import _utc_now, registry_read, registry_upsert, run_task

# ==============================================================================
# I. DANE WEJŚCIOWE
# ==============================================================================


def task_ingest_s2(rt: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Rastry Sentinel-2 dla AOI (sezon S2_MONTHS), przyrostowo z manifestem."""
    before = set(glob.glob(os.path.join(cfg["S2_DIR"], "S2_L2A_*.tif")))
    aoi, _, _ = ingest.load_aoi_geometry(cfg["AOI_PATH"], buffer_m=cfg["AOI_BUFFER_M"])
    ingest.sync_sentinel2_time_series(aoi, start_year=cfg["S2_START_YEAR"], output_dir=cfg["S2_DIR"],
                                      manifest_path=cfg["S2_MANIFEST"], cloud_thresh=cfg["S2_CLOUD_MAX_AOI"],
                                      epsg_code=cfg["EPSG"], months=cfg["S2_MONTHS"])
    after = set(glob.glob(os.path.join(cfg["S2_DIR"], "S2_L2A_*.tif")))
    new = len(after - before)
    return {"skipped": new == 0, "message": f"{len(after)} scen na Dysku, {new} nowych"}


def task_ingest_era5(rt: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    """ERA5-Land 1991 → dziś w punkcie winnicy, przyrostowo (cache fragmentów roku)."""
    lon, lat = main_site_lonlat(cfg)
    end = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d")
    df = ingest.sync_era5_land_point(lat, lon, cfg["ERA5_START"], end, os.path.join(cfg["ERA5_DIR"], "cache"))
    df.to_csv(era5_csv(cfg), index=False)
    return {"message": f"ERA5-Land: {len(df)} dni do {df['time'].max():%Y-%m-%d}"}


def task_ingest_swi(rt: Dict[str, Any], cfg: Dict[str, Any], session: Any = None) -> Dict[str, Any]:
    """
    Satelitarny SWI piksela winnicy, przyrostowo: SWI_PRODUCT (0,1° v4, 2007 – dziś) oraz — gdy SWI_1KM — SWI 1 km v2
    (od VII 2025), zbierany bez normy. Klucze tylko z SECRETS_DIR. Zapis: SWI_DIR/swi_<produkt>_point.csv.
    """
    lon, lat = main_site_lonlat(cfg)
    end = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d")
    prods = [cfg["SWI_PRODUCT"]] + (["v2_1km"] if cfg.get("SWI_1KM") and cfg["SWI_PRODUCT"] != "v2_1km" else [])
    os.makedirs(cfg["SWI_DIR"], exist_ok=True)
    msgs = []
    for prod in prods:
        raw = ingest.sync_swi_point(cfg["SECRETS_DIR"], lat, lon, prod, end, os.path.join(cfg["SWI_DIR"], "cache"),
                                    session=session)
        clean, info = ingest.clean_swi(raw)
        clean.to_csv(os.path.join(cfg["SWI_DIR"], f"swi_{prod}_point.csv"), index=False)
        msgs.append(f"{prod}: {info['days_ok']} dni z danymi {info['first']}…{info['last']}, "
                    f"z flagą producenta {info['days_flagged']}")
    return {"message": "; ".join(msgs)}


# ==============================================================================
# II. WINNICE (W3b) I GLEBA
# ==============================================================================

def _stats_to_obs(recs: List[Dict[str, Any]], run_tag: str, variables: tuple) -> pd.DataFrame:
    rows = []
    for r in recs:
        for var in variables:
            rows.append({"site_id": r["site_id"], "product": r["product"], "variable": var,
                         "time_utc": r["time"].strftime("%Y-%m-%dT%H:%M:%SZ"), "orbit": 0, "value": r[var],
                         "unit": "1", "n_pixels": r["n_pixels"], "qc_flags": r["px_method"], "calib_id": "",
                         "run_id": run_tag, "ingested_at": _utc_now()})
    return pd.DataFrame(rows)


def task_parcel_stats(rt: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Średnie wskaźników i pasm PARCEL_BANDS dla wszystkich winnic, z pasem wewnętrznym PARCEL_INNER_M (W3b §1), jako
    produkt PARCEL_PRODUCT w gwl_observations. Z archiwum S2_DIR, przyrostowo: „zrobione” = para (działka, scena), więc
    nowa działka dostaje całą historię. Zapis co 25 scen (przerwana sesja wznawia się sama). Raport: parcel_qc.csv.
    """
    prod = cfg["PARCEL_PRODUCT"]
    tag = f"parcel_stats_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}"
    variables = metrics.INDICES + tuple(b.lower() for b in cfg["PARCEL_BANDS"]) + ("clear_frac",)
    scenes = sorted(glob.glob(os.path.join(cfg["S2_DIR"], "S2_L2A_*.tif")))
    obs = registry_read(rt, "gwl_observations")
    o = obs[obs["product"] == prod]
    done = set(zip(o["site_id"].astype(str), o["time_utc"].astype(str)))
    parcels, geo = metrics.load_parcels(cfg, cfg["EPSG"]), None
    buf: List[Dict[str, Any]] = []
    n_new = 0
    for path in reversed(scenes):
        t = metrics.scene_time(path)
        tkey = t.strftime("%Y-%m-%dT%H:%M:%SZ")
        todo = [sid for sid in parcels["site_id"] if (sid, tkey) not in done]
        if not todo:
            continue
        data, prof = ingest.read_geotiff_to_numpy(path)
        geo = parcels.to_crs(prof["crs"]) if geo is None else geo
        buf.extend(metrics.site_stats(data[:10], np.nan_to_num(data[metrics.RASTER_CLOUD_BAND], nan=1.0), prof,
                                      geo[geo["site_id"].isin(todo)], prod, t, inner_m=cfg["PARCEL_INNER_M"],
                                      bands=cfg["PARCEL_BANDS"], crswir_w=metrics.CRSWIR_W_FORDEAD,
                                      all_touched_fallback=False))
        n_new += 1
        if n_new % 25 == 0:
            registry_upsert(rt, "gwl_observations", _stats_to_obs(buf, tag, variables))
            buf.clear()
    if buf:
        registry_upsert(rt, "gwl_observations", _stats_to_obs(buf, tag, variables))
    obs = registry_read(rt, "gwl_observations")
    cf = obs[(obs["product"] == prod) & (obs["variable"] == "clear_frac")]
    g = cf.groupby("site_id")
    qc = parcels[["site_id", "fid", "area_ha"]].set_index("site_id").join(pd.DataFrame({
        "n_pixels": pd.to_numeric(cf["n_pixels"], errors="coerce").groupby(cf["site_id"]).max(), "n_scenes": g.size(),
        "n_clear": (pd.to_numeric(cf["value"], errors="coerce") >= cfg["VEG_MIN_CLEAR_FRAC"]).groupby(cf["site_id"]).sum()}))
    qc["qc_ok"] = qc["n_pixels"] >= cfg["PARCEL_MIN_PX"]
    os.makedirs(cfg["OUTPUT_DIR"], exist_ok=True)
    qc.reset_index().to_csv(os.path.join(cfg["OUTPUT_DIR"], "parcel_qc.csv"), index=False)
    small = ", ".join(f"{sid} ({int(r.n_pixels) if np.isfinite(r.n_pixels) else 0} px)"
                      for sid, r in qc[~qc["qc_ok"]].iterrows())
    last = f"{metrics.scene_time(scenes[-1]):%Y-%m-%d}" if scenes else "—"
    msg = (f"{n_new} scen przeliczonych; {len(scenes)} scen w S2_DIR (ostatnia {last}); winnice z QC "
           f"(≥ {cfg['PARCEL_MIN_PX']} pikseli 10 m po pasie {cfg['PARCEL_INNER_M']} m): {int(qc['qc_ok'].sum())}/{len(qc)}"
           + (f"; poniżej progu: {small}" if small else ""))
    return {"skipped": n_new == 0, "message": msg}


def task_soil(rt: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Dzienne anomalie ERA5-Land wobec 1991–2020: wilgotność 0–7 i 0–100 cm (percentyl, z), SPI-1, SPI-3."""
    os.makedirs(cfg["OUTPUT_DIR"], exist_ok=True)
    era5 = pd.read_csv(era5_csv(cfg), parse_dates=["time"])
    an = metrics.era5_anomalies(era5, cfg)
    daily = pd.concat({k: v[[c for c in ("value", "z", "percentile") if c in v]] for k, v in an.items()}, axis=1)
    daily.to_csv(os.path.join(cfg["OUTPUT_DIR"], "era5_daily_anomalies.csv"))
    rz = an["ERA5L_SM_RZ"].dropna(subset=["percentile"])
    last = f"{rz.index[-1]:%Y-%m-%d}: percentyl 0–100 cm {rz['percentile'].iat[-1]:.0f}" if len(rz) else "brak danych"
    return {"message": f"ERA5-Land {len(daily)} dni; {last}"}


def _parcel_obs(rt: Dict[str, Any], cfg: Dict[str, Any], until: Optional[str] = None) -> pd.DataFrame:
    return parcel.parcel_wide(registry_read(rt, "gwl_observations"), cfg["PARCEL_PRODUCT"], until)


def _read_tests(cfg: Dict[str, Any]) -> Optional[pd.DataFrame]:
    p = os.path.join(cfg["OUTPUT_DIR"], "w3b_tests.csv")
    return pd.read_csv(p) if os.path.exists(p) and os.path.getsize(p) > 1 else None


def task_parcel_tests(rt: Dict[str, Any], cfg: Dict[str, Any], force: bool = False) -> Dict[str, Any]:
    """
    Testy W3b zamrożone (protokół §0–§11): T1, T2, T3, wariant wielopasmowy, wartości „przed” i QC na scenach
    ≤ W3B_FREEZE (anomalie liczone od nowa z tych scen). Wynik: w3b_tests.csv (z SHA-256 protokołu, zamrożeniem
    i commitem kodu) i gwl_validation_metrics. Ten sam protokół, zamrożenie i commit = „skipped” (chyba że force=True);
    nowy commit liczy testy od nowa na tych samych zamrożonych danych (powtarzalność wyniku).
    Wartości „przed” (§9) czytają archiwalny veg_anomalies.csv z wcześniejszych wersji, gdy jest w OUTPUT_DIR.
    """
    out = cfg["OUTPUT_DIR"]
    proto = parcel.protocol_sha(cfg["W3B_PROTOCOL"])
    fz = parcel.freeze_info(cfg, out)
    commit = str(rt.get("GIT_COMMIT", ""))
    warn = "; UWAGA: lista scen ≤ zamrożenia zmieniła się od pierwszego liczenia" \
        if fz["scenes_sha256"] != fz["scenes_sha256_at_freeze"] else ""
    old = _read_tests(cfg)
    if old is not None and not force and len(old) and {"protocol_sha256", "freeze", "code_commit"} <= set(old) and \
            str(old["protocol_sha256"].iat[0]) == proto["sha256"] and str(old["freeze"].iat[0]) == fz["freeze"] \
            and str(old["code_commit"].iat[0]) == commit:
        return {"skipped": True, "message": f"testy W3b już policzone (zamrożenie {fz['freeze']}, protokół "
                                            f"{proto['sha256'][:12]}…, kod {commit}); force=True liczy ponownie{warn}"}
    w = _parcel_obs(rt, cfg, until=fz["freeze"])
    if w.empty:
        return {"skipped": True, "message": "brak statystyk działek — uruchom parcel_stats"}
    n_min = int(w.groupby("site_id")["time_utc"].nunique().min())
    if n_min < fz["n_scenes"]:                     # testy tylko na pełnym archiwum do daty zamrożenia
        return {"skipped": True, "message": f"statystyki działek niepełne ({n_min} z {fz['n_scenes']} scen ≤ "
                                            f"{fz['freeze']}) — dokończ parcel_stats"}
    pa, n_dup = parcel.parcel_anomalies(w, cfg)
    counts = pd.DataFrame({"n_scenes": w.groupby("site_id").size(), "n_clear": (pd.to_numeric(
        w["clear_frac"], errors="coerce") >= cfg["VEG_MIN_CLEAR_FRAC"]).groupby(w["site_id"]).sum()})
    era5 = pd.read_csv(era5_csv(cfg), parse_dates=["time"])
    vpath = os.path.join(out, "veg_anomalies.csv")
    veg = pd.read_csv(vpath, parse_dates=["time"]) if os.path.exists(vpath) else None
    f4p = os.path.join(cfg["PROJECT_DIR"], "docs", "evidence", "F4_eksperymenty", "A_roslinnosc", "a2_variant_series.csv")
    f4 = pd.read_csv(f4p) if os.path.exists(f4p) else None
    tests = parcel.run_tests(pa, n_dup, parcel.sensor_daily(cfg), era5, card.read_swi(cfg), veg, f4, cfg, counts)
    tests = tests.assign(protocol_sha256=proto["sha256"], protocol_status=proto["status"],
                         protocol_registered=proto["registered"], freeze=fz["freeze"], scenes=fz["n_scenes"],
                         scenes_sha256=fz["scenes_sha256"], code_version=parcel.CODE_VERSION, code_commit=commit)
    os.makedirs(out, exist_ok=True)
    tests.to_csv(os.path.join(out, "w3b_tests.csv"), index=False)
    summ = parcel.tests_summary(tests)
    t3, p7 = summ["t3"], summ["p7"]
    msg = (f"zamrożenie {fz['freeze']} ({fz['n_scenes']} scen, {fz['source']}); "
           f"T3 ρ = {t3['value']:.2f} [{t3['lo']:.2f}; {t3['hi']:.2f}] — {t3['verdict']}; "
           f"wariant wielopasmowy: {p7['delta']['verdict'] if p7['delta'] else '—'}; "
           f"T1 {100 * summ['t1']['value']:.1f}% [{100 * summ['t1']['lo']:.1f}; {100 * summ['t1']['hi']:.1f}] — "
           f"{summ['t1']['verdict']}")
    if proto["status"] != "REGISTERED" or proto["registered"] != proto["sha256"]:
        msg += f"; UWAGA: protokół {proto['status'] or 'bez statusu'}, skrót niezgodny z zarejestrowanym"
    return {"message": msg + warn, "registry": {"gwl_validation_metrics": tests[parcel.METRIC_COLS]}}


def task_parcel_anomalies(rt: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Anomalie wszystkich winnic do karty i panelu (parcel.parcel_anomalies), mediana okolicy (zbiór T3; przy przyjętym
    wariancie wielopasmowym także jego wynik) i flaga zmiany gospodarowania.
    Pliki: parcel_anomalies.csv, parcel_area.csv, parcel_flags.csv.
    """
    w = _parcel_obs(rt, cfg)
    if w.empty:
        return {"skipped": True, "message": "brak statystyk działek — uruchom parcel_stats"}
    pa, n_dup = parcel.parcel_anomalies(w, cfg)
    ok, t3s = parcel.qc_sites(pa), parcel.t3_sites(pa, cfg)
    mn = int(cfg["PARCEL_MIN_AREA"])
    area = parcel.area_series(pa, "water", t3s, mn).assign(index="water")
    summ = parcel.tests_summary(_read_tests(cfg))
    mb = parcel.multiband_area(parcel.band_features(pa, t3s, tuple(b.lower() for b in cfg["PARCEL_BANDS"]), mn), summ)
    if len(mb):
        area = pd.concat([area, pd.DataFrame({"z_med": mb, "n_parcels": np.nan, "index": "water_mb"})])
    flags = parcel.management_flags(pa, ok, cfg)
    out = cfg["OUTPUT_DIR"]
    os.makedirs(out, exist_ok=True)
    pa.to_csv(os.path.join(out, "parcel_anomalies.csv"), index=False)
    area.rename_axis("day").reset_index().to_csv(os.path.join(out, "parcel_area.csv"), index=False)
    flags.to_csv(os.path.join(out, "parcel_flags.csv"), index=False)
    cur = pa[(pa["site_id"] == cfg["MAIN_SITE"]) & (pa["index"] == "water")].dropna(subset=["z"])
    last = (f"; {cfg['MAIN_SITE']} {pd.Timestamp(cur['time'].iat[-1]):%Y-%m-%d}: z_woda {cur['z'].iat[-1]:+.2f}"
            if len(cur) else "")
    nflag = int(flags["flag"].astype(str).isin(["-", "+"]).sum()) if len(flags) else 0
    return {"message": f"{pa['site_id'].nunique()} winnic ({len(ok)} z QC), {int((pa['index'] == 'water').sum())} scen "
                       f"z z_woda, dni z 2 scenami: {n_dup}, sezony z flagą: {nflag}{last}"}


# ==============================================================================
# III. WALIDACJA I POGODA
# ==============================================================================

def task_reference(rt: Dict[str, Any], cfg: Dict[str, Any], cdse_session: Any = None, icos_session: Any = None,
                   era5_fetch: Any = None) -> Dict[str, Any]:
    """
    W2 + REF (protokół D-083): walidacja warstwy wody na trzech miejscach — Condom (ISMN 20–30 cm po regułach A4:
    W1 główny, W2, W3, wrażliwość progu), FR-Aur i FR-Lus (ICOS). Produkty: ERA5-Land 0–100 cm i SWI v4 (T = SWI_T,
    wrażliwość SWI_T_SENS) w pikselu każdego miejsca. Wyniki: validation_reference.csv, validation_reference_qc.csv,
    a4_flags.csv, reference_current.json. Błąd jednego miejsca nie zatrzymuje pozostałych.
    """
    out = cfg["OUTPUT_DIR"]
    os.makedirs(out, exist_ok=True)
    overrides = {"PROJECT_DIR": cfg["PROJECT_DIR"], "NETWORK": cfg["NETWORK"], "STATION": cfg["STATION"],
                 "BOOTSTRAP_N": cfg["BOOTSTRAP_N"], "STATION_BUFFER_M": cfg["STATION_BUFFER_M"]}
    s7cfg = stations.build_config(overrides)
    hw = int(cfg["CLIM_HALF_WINDOW_DAYS"])
    era5_fetch = era5_fetch or ingest.sync_era5_land_point
    end = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d")
    vals, qc_rows, current, errors = [], [], {}, []

    def products_from(era: pd.DataFrame, swi: Optional[pd.DataFrame]) -> Dict[str, Any]:
        e = era.set_index(pd.to_datetime(era["time"]).dt.floor("D")).sort_index()
        prods = {"ERA5L_SM_RZ": (metrics.rootzone(e[~e.index.duplicated(keep="last")]), "ERA5 cell")}
        if swi is not None and len(swi):
            sw = swi.set_index(pd.to_datetime(swi["date"]).dt.floor("D")).sort_index()
            for t in (int(cfg["SWI_T"]),) + tuple(int(x) for x in cfg.get("SWI_T_SENS", ())):
                if f"swi{t:03d}" in sw:
                    prods[f"SWI_v4_T{t:03d}"] = (sw[f"swi{t:03d}"].astype(float), "SWI 0.1° cell")
        return prods

    # 1. Condom: ISMN 20–30 cm po A4, ERA5 i SWI piksela winnicy (stacja 136 m od winnicy, ta sama komórka 0,1°)
    try:
        v20, v30 = stations.a4_variants(0.20, overrides), stations.a4_variants(0.30, overrides)
        stations.a4_flag_report(v20, v30).to_csv(os.path.join(out, "a4_flags.csv"), index=False)
        prods = products_from(pd.read_csv(era5_csv(cfg), parse_dates=["time"]), card.read_swi(cfg))
        for var in ("W1", "W2", "W3", "W1_05WP", "W1_015"):
            rz = pd.concat([v20[var]["sm"], v30[var]["sm"]], axis=1).dropna().mean(axis=1)
            vals.append(reference.validate_layer(rz, prods, (s7cfg["START_DATE"], s7cfg["END_DATE"]),
                                                 stations.site_id(s7cfg), f"ISMN_20_30cm_A4{var}", s7cfg, hw))
    except Exception as e:
        errors.append(f"Condom: {type(e).__name__}: {e}")
    # 2. Stacje ICOS
    for site in cfg.get("REF_SITES", ()):
        try:
            sc = reference.REF_SITES[site]
            daily, info = reference.ingest_icos_site(site, os.path.join(cfg["REF_DIR"], site), session=icos_session)
            era = era5_fetch(sc["lat"], sc["lon"], sc["fetch_from"], end, os.path.join(cfg["ERA5_DIR"], f"ref_{site}"))
            raw = ingest.sync_swi_point(cfg["SECRETS_DIR"], sc["lat"], sc["lon"], cfg["SWI_PRODUCT"], end,
                                        os.path.join(cfg["SWI_DIR"], f"ref_{site}"), start=sc["fetch_from"],
                                        session=cdse_session)
            swi, _ = ingest.clean_swi(raw)
            v, cur = reference.validate_icos_site(site, daily, era, swi, cfg, s7cfg)
            vals.append(v)
            current[site] = cur
            for lvl, q in info["qc"].items():
                qc_rows.append({"site": site, "level": lvl, "depth_m": sc["depths"][int(lvl.split("_")[1])], **q,
                                "nrt_days": info["nrt_days"], "first": info["first"], "last": info["last"]})
        except Exception as e:
            errors.append(f"{site}: {type(e).__name__}: {e}")
    val = pd.concat([v for v in vals if len(v)], ignore_index=True) if any(len(v) for v in vals) else pd.DataFrame()
    val.to_csv(os.path.join(out, "validation_reference.csv"), index=False)
    pd.DataFrame(qc_rows).to_csv(os.path.join(out, "validation_reference_qc.csv"), index=False)
    with open(os.path.join(out, "reference_current.json"), "w", encoding="utf-8") as f:
        json.dump({"current": current, "errors": errors}, f, indent=1, ensure_ascii=False, default=str)
    msg = []
    for (site, ref), g in (val.groupby(["site_id", "reference"]) if len(val) else []):
        seg = reference.MAIN_SEGMENT.get(site, "anomaly_clim")
        r = g[(g["segment"] == seg) & (g["metric"] == "pearson_r")]
        if len(r) and (ref.endswith("A4W1") or (ref.startswith("ICOS") and not ref.endswith("0_100cm"))):
            msg.append(f"{site} ({seg}): " + ", ".join(f"{p} R = {x:.2f}" for p, x in zip(r["product"], r["value"])
                                                      if p in ("ERA5L_SM_RZ", f"SWI_v4_T{int(cfg['SWI_T']):03d}")))
    msg += [f"BŁĄD {x}" for x in errors]
    return {"message": "; ".join(msg) or "brak wyników", "registry": {"gwl_validation_metrics": val} if len(val) else {}}


def task_weather(rt: Dict[str, Any], cfg: Dict[str, Any], fetch: bool = True) -> Dict[str, Any]:
    """
    Przymrozki i upały dla winnicy (ERA5-Land) + walidacja ERA5 (Tmin, Tmax, opad, SPI) na najbliższych stacjach
    Météo-France (ERA5-Land w punkcie każdej stacji, cache). Wyniki: validation_weather.csv, mf_stations.csv,
    weather_hazards.csv, hazard_summary.csv, hazard_thresholds.json.
    """
    os.makedirs(cfg["OUTPUT_DIR"], exist_ok=True)
    lon, lat = main_site_lonlat(cfg)
    paths = weather.download_mf(cfg["MF_DEPTS"], cfg["MF_DIR"]) if fetch else \
        sorted(glob.glob(os.path.join(cfg["MF_DIR"], "Q_*_RR-T-Vent.csv.gz")))
    mf = weather.read_mf(paths, cfg["CLIM_REF"][0])
    mf_st = weather.select_stations(mf, lat, lon, cfg) if len(mf) else pd.DataFrame()
    era_by = {}
    end = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d")
    for st in mf_st.itertuples():
        cache = os.path.join(cfg["MF_DIR"], f"era5_{st.num_poste}")
        if fetch:
            era_by[st.num_poste] = ingest.sync_era5_land_point(st.lat, st.lon, cfg["CLIM_REF"][0], end, cache)
        elif os.path.isdir(cache):
            fr = [pd.read_csv(p, parse_dates=["time"]) for p in sorted(glob.glob(os.path.join(cache, "*.csv")))]
            era_by[st.num_poste] = pd.concat(fr, ignore_index=True).drop_duplicates("time") if fr else pd.DataFrame()
    val = weather.validate_weather(mf_st, mf, era_by, cfg) if len(mf_st) else pd.DataFrame()
    val.to_csv(os.path.join(cfg["OUTPUT_DIR"], "validation_weather.csv"), index=False)
    mf_st.to_csv(os.path.join(cfg["OUTPUT_DIR"], "mf_stations.csv"), index=False)
    era5 = pd.read_csv(era5_csv(cfg), parse_dates=["time"])
    thr = weather.calibrated_thresholds(val, mf_st, cfg)
    if "t2m_max_c" not in era5:
        era5["t2m_max_c"] = np.nan
    hz = weather.weather_hazards(era5, cfg, thr)
    hz.to_csv(os.path.join(cfg["OUTPUT_DIR"], "weather_hazards.csv"))
    weather.hazard_summary(hz, cfg, cfg["HAZARD_YEARS"]).to_csv(os.path.join(cfg["OUTPUT_DIR"], "hazard_summary.csv"),
                                                                index=False)
    with open(os.path.join(cfg["OUTPUT_DIR"], "hazard_thresholds.json"), "w") as f:
        json.dump(thr, f)
    msg = (f"{len(mf_st)} stacji MF ({', '.join(f'{r.name} {r.dist_km:.0f} km' for r in mf_st.itertuples())}); "
           f"progi ERA5: przymrozek Tmin ≤ {thr['frost']:+.2f} °C ({thr['frost_source']}), "
           f"upał Tmax ≥ {thr['heat']:.2f} °C ({thr['heat_source']}); {len(val)} metryk")
    res: Dict[str, Any] = {"message": msg}
    if len(val):
        res["registry"] = {"gwl_validation_metrics": val}
    return res


# ==============================================================================
# IV. PRODUKT I RAPORT
# ==============================================================================

def task_panel(rt: Dict[str, Any], cfg: Dict[str, Any], forecast: bool = True) -> Dict[str, Any]:
    """Panel AgriScreen (EN, 15 winnic): panel.html (samodzielny, także na blog) i panel_data.json."""
    from agriscreen import panel
    path = panel.build_panel(cfg["OUTPUT_DIR"], cfg, forecast="fetch" if forecast else None)
    return {"message": f"{path} ({os.path.getsize(path) // 1024} kB)"}


def _read_csv(cfg: Dict[str, Any], name: str, **kw) -> pd.DataFrame:
    p = os.path.join(cfg["OUTPUT_DIR"], name)
    return pd.read_csv(p, **kw) if os.path.exists(p) and os.path.getsize(p) > 1 else pd.DataFrame()


def task_summary(rt: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Raport z uruchomienia (run_summary.md i run_summary.json): wersja i commit kodu, pokrycie danych, testy W3b,
    walidacja warstwy wody i pogody, eksperymenty, ostatnie zadania. Bez danych surowych (kilka kB).
    """
    import agriscreen
    out = cfg["OUTPUT_DIR"]
    scenes = sorted(glob.glob(os.path.join(cfg["S2_DIR"], "S2_L2A_*.tif")))
    era = _read_csv(cfg, "era5_daily_anomalies.csv", header=[0, 1], index_col=0, parse_dates=True)
    qc = _read_csv(cfg, "parcel_qc.csv")
    info = {"version": agriscreen.__version__, "commit": rt.get("GIT_COMMIT", ""), "generated_utc": _utc_now(),
            "scenes": len(scenes), "last_scene": f"{metrics.scene_time(scenes[-1]):%Y-%m-%d}" if scenes else "",
            "era5_last": f"{era.index[-1]:%Y-%m-%d}" if len(era) else "",
            "vineyards": int(len(qc)), "vineyards_qc": int(qc["qc_ok"].sum()) if len(qc) else 0}
    md = [f"# AgriScreen — raport z uruchomienia ({info['generated_utc']})", "",
          f"Wersja {info['version']} · commit `{info['commit']}` · {info['scenes']} scen Sentinel-2 (ostatnia "
          f"{info['last_scene'] or '—'}) · ERA5-Land do {info['era5_last'] or '—'} · winnice z QC "
          f"{info['vineyards_qc']}/{info['vineyards']}", ""]
    summ = parcel.tests_summary(_read_tests(cfg))
    if summ:
        t1, t3, mdc, p7 = summ["t1"], summ["t3"], summ["mdc"], summ["p7"]
        md += ["## Testy W3b (zamrożone)", "",
               f"- Zamrożenie {summ.get('freeze', '—')}, protokół `{(summ.get('protocol_sha256') or '')[:12]}…`, "
               f"kod `{summ.get('code_commit', '')}`",
               f"- T1 kalibracja: {100 * t1['value']:.1f}% [{100 * t1['lo']:.1f}; {100 * t1['hi']:.1f}] — {t1['verdict']}",
               f"- T2 szum (MDC95): G5 {mdc.get('G5', {}).get('value', float('nan')):.2f}, "
               f"G13 {mdc.get('G13', {}).get('value', float('nan')):.2f} z",
               f"- T3 roślinność okolicy a czujnik: ρ {t3['value']:.2f} [{t3['lo']:.2f}; {t3['hi']:.2f}] — {t3['verdict']}",
               f"- Wariant wielopasmowy: {(p7.get('delta') or {}).get('verdict', '—')}", ""]
    ref = _read_csv(cfg, "validation_reference.csv")
    if len(ref):
        r = ref[(ref["metric"] == "pearson_r") & ref["product"].isin(["ERA5L_SM_RZ", f"SWI_v4_T{int(cfg['SWI_T']):03d}"])]
        r = r[r["segment"].isin(set(reference.MAIN_SEGMENT.values()) | {"anomaly_clim"})]
        md += ["## Walidacja warstwy wody (W2 + REF)", "", "| stacja | odniesienie | produkt | segment | R | 95% CI | n |",
               "|---|---|---|---|---|---|---|"]
        md += [f"| {x.site_id} | {x.reference} | {x.product} | {x.segment} | {x.value:.2f} | [{x.ci_low:.2f}; "
               f"{x.ci_high:.2f}] | {int(x.n)} |" for x in r.itertuples()] + [""]
    wv = _read_csv(cfg, "validation_weather.csv")
    if len(wv):
        q = wv[(wv["product"] == "ERA5L_PRECIP") & (wv["segment"] == "sum_30d") & (wv["period"].astype(str) == "all")
               & (wv["metric"] == "pearson_r")]
        thr = json.load(open(os.path.join(out, "hazard_thresholds.json"))) \
            if os.path.exists(os.path.join(out, "hazard_thresholds.json")) else {}
        md += ["## Pogoda", "", f"- Opad 30 dni ERA5-Land wobec deszczomierza: R {q['value'].iat[0]:.2f}" if len(q) else "",
               f"- Progi: przymrozek Tmin ≤ {thr.get('frost', '—')} °C ({thr.get('frost_source', '')}); upał Tmax ≥ "
               f"{thr.get('heat', '—')} °C ({thr.get('heat_source', '')})", ""]
    for name, label in (("w3c_tests.csv", "W3c (strefa gorsza niż zwykle)"), ("w3d_tests.csv", "W3d (najniżej od 5 lat)")):
        t = _read_csv(cfg, name)
        if len(t):
            crit = t[t["key"].astype(str).str.contains("_show_")]
            md += [f"## Eksperyment {label}", ""] + [f"- {r.product}: {r.verdict}" for r in crit.itertuples()] + [""]
    runs = registry_read(rt, "gwl_runs").sort_values("started_at", ascending=False).head(15)
    md += ["## Ostatnie zadania", "", "| zadanie | status | s | komunikat |", "|---|---|---|---|"]
    md += [f"| {r.task} | {r.status} | {r.duration_s} | {str(r.message)[:160].replace('|', '/')} |"
           for r in runs.itertuples()]
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "run_summary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    with open(os.path.join(out, "run_summary.json"), "w", encoding="utf-8") as f:
        json.dump(dict(info, w3b=summ), f, indent=1, ensure_ascii=False, default=str)
    return {"message": f"run_summary.md ({sum(len(x) for x in md) // 1024 + 1} kB)"}


# ==============================================================================
# V. CAŁOŚĆ
# ==============================================================================

TASKS: Tuple[Tuple[str, Callable[..., Dict[str, Any]]], ...] = (
    ("ingest_s2", task_ingest_s2), ("ingest_era5", task_ingest_era5), ("ingest_swi", task_ingest_swi),
    ("parcel_stats", task_parcel_stats), ("soil", task_soil), ("parcel_tests", task_parcel_tests),
    ("parcel_anomalies", task_parcel_anomalies), ("reference", task_reference), ("weather", task_weather),
    ("panel", task_panel), ("summary", task_summary))
INGEST = {"ingest_s2", "ingest_era5", "ingest_swi"}


def run_all(rt: Dict[str, Any], cfg: Optional[Dict[str, Any]] = None, ingest_data: bool = True,
            experiments: bool = False) -> Dict[str, Any]:
    """Wszystkie zadania po kolei (każde zapisane w gwl_runs; błąd jednego nie zatrzymuje kolejnych).
    ingest_data=False: bez pobierania (praca na danych z Dysku). experiments=True: także W3c i W3d przed panelem."""
    cfg = cfg or make_config(rt["PROJECT_DIR"], data_dir=rt.get("DATA_ROOT"))
    results = {}
    for name, fn in TASKS:
        if name in INGEST and not ingest_data:
            continue
        if name == "panel" and experiments:
            from agriscreen import experiments as ex
            results["zones"] = run_task(rt, "zones", ex.task_zones, rt, cfg)
            results["months"] = run_task(rt, "months", ex.task_months, rt, cfg)
        kwargs = {"fetch": ingest_data} if name == "weather" else {}
        results[name] = run_task(rt, name, fn, rt, cfg, **kwargs)
    return results
