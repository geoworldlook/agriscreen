"""
================================================================================
AgriWatch - KROK 12: PANEL „AGRISCREEN” DO PUBLIKACJI (15 WINNIC, EN)
================================================================================
Panel w układzie aplikacji Wago (projekt ESA WineEO, eo4society 2021): lista winnic po lewej, mapa na zdjęciu
satelitarnym (Esri World Imagery, jak w dashboardzie step_06) z półprzezroczystą warstwą, po prawej stan działki,
gleba w okolicy, pogoda i dane działki. Pod mapą statystyki, sezon, zdania karty i tabela „How far to trust it”.

Warstwy mapy:
  - wnętrze działki: piksele 10 m NDVI / NDRE / NDMI z ostatnich bezchmurnych scen archiwum S2_DIR (opis miejsc
    w działce, bez normy i bez walidacji),
  - wobec własnej historii: z całej działki z parcel_anomalies.csv (woda w roślinności SWIR, NDVI, NDRE, NDMI, CRSWIR).
Pod kaflami Esri leży obraz Sentinel-2 w barwach naturalnych (widoczny, gdy kafle są niedostępne, np. bez sieci).
Pogoda dla całej okolicy (jedno oczko ERA5-Land): prognoza Open-Meteo z chwili budowy, ostatnie 10 dni i opad
30 / 90 dni z ERA5-Land, przymrozki i upały sezonu (task_weather).
Ten sam plik pokazuje notatnik Colab (show_dashboard) i trafia na blog GeoWorldLook.
================================================================================
"""

from __future__ import annotations

import base64
import glob
import html
import io
import json
import logging
import os
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("AgriWatch_Panel")

LAYERS = (("water", "Vegetation water (SWIR)", 1.0,
           "Mean of NDMI and sign-flipped CRSWIR anomalies: water in the whole parcel's vegetation (vines and inter-rows)"),
          ("ndvi", "Greenness (NDVI)", 1.0, "Green leaf cover of vines and inter-rows"),
          ("ndre", "Chlorophyll (NDRE)", 1.0, "Red-edge index, leaf greenness"),
          ("ndmi", "NDMI (SWIR/NIR)", 1.0, "Short-wave infrared moisture index"),
          ("crswir", "CRSWIR (sign flipped)", -1.0, "Continuum-removed SWIR; sign flipped so that lower = less water"))

# Mapy pikseli: stała skala dla wszystkich dat (porównywalne kolory), rampa brąz -> zieleń jak „Vegetation index” w Wago
VEG_RAMP = ("#8b5a2b", "#c9a45c", "#ece0a0", "#8cc152", "#2f8f3a", "#145a24")
WATER_RAMP = ("#8b5a2b", "#d6b98a", "#efe9d6", "#8fc1dc", "#2f75b5", "#173f7a")
PIXEL_LAYERS = (("ndvi", "Greenness (NDVI)", 0.10, 0.80, VEG_RAMP, "bare soil", "dense leaves"),
                ("ndre", "Chlorophyll (NDRE)", 0.05, 0.45, VEG_RAMP, "low", "high"),
                ("ndmi", "Water in vegetation (NDMI)", -0.20, 0.40, WATER_RAMP, "dry", "moist"))
# Strefy w działce (wariant A): piksel minus mediana tej samej działki w tym samym dniu. Bez normy i bez przesunięć
# między latami. Skala ± REL_RANGE; pierścień przy brzegu (środek piksela < REL_EDGE_M od brzegu) pominięty, bo piksele
# mieszają się tam z drogą i sąsiednią uprawą i wyglądałyby jak słabe miejsca.
REL_RANGE = {"ndvi": 0.15, "ndre": 0.10, "ndmi": 0.10}
REL_RAMP = {"ndvi": ("#8b3a12", "#d08a4a", "#f4efe2", "#7dbf5a", "#1f7a33"),
            "ndre": ("#8b3a12", "#d08a4a", "#f4efe2", "#7dbf5a", "#1f7a33"),
            "ndmi": ("#8b3a12", "#d08a4a", "#f4efe2", "#6fa9d6", "#1f4f8f")}
REL_EDGE_M = 10.0
# W3c „Zones vs usual” (step_13): kolory kodów komórek; brąz = słabsze niż zwykle, zieleń / błękit = mocniejsze;
# potwierdzone pełnym kolorem, nowe jaśniej; szare = za krótka historia; „jak zwykle” lekko rozjaśnione
HIST_RGBA = {0: (255, 255, 255, 45), 9: (150, 155, 150, 140), 1: (214, 150, 80, 200), 2: (122, 58, 14, 255)}
HIST_STRONG = {"ndvi": {3: (125, 191, 90, 200), 4: (31, 122, 51, 255)},
               "ndmi": {3: (111, 169, 214, 200), 4: (31, 79, 143, 255)}}
PIXEL_UPSCALE = 3            # obraz 10 m rysowany w siatce ~3,3 m (najbliższy sąsiad) — ostre brzegi działek
CLUSTER_MARGIN_M = 600       # obraz w barwach naturalnych sięga 600 m poza skupisko winnic


def _opt(path: str, **kw) -> Optional[pd.DataFrame]:
    return pd.read_csv(path, **kw) if os.path.exists(path) and os.path.getsize(path) > 1 else None


def _r(x: Any, nd: int = 2) -> Optional[float]:
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return round(x, nd) if np.isfinite(x) else None


def _ramp(stops, v: np.ndarray) -> np.ndarray:
    """Wartości 0–1 -> RGB uint8 wg listy kolorów (interpolacja liniowa między stopniami)."""
    c = np.array([[int(h[i:i + 2], 16) for i in (1, 3, 5)] for h in stops], float)
    x = np.clip(np.nan_to_num(v, nan=0.0), 0, 1) * (len(stops) - 1)
    i = np.minimum(np.floor(x).astype(int), len(stops) - 2)
    f = (x - i)[..., None]
    return (c[i] * (1 - f) + c[i + 1] * f).round().astype(np.uint8)


def _b64_image(arr: np.ndarray, fmt: str = "PNG") -> str:
    from PIL import Image
    buf = io.BytesIO()
    img = Image.fromarray(arr, "RGBA" if arr.shape[-1] == 4 else "RGB")
    if fmt == "PNG":                     # paleta 64 barw z przezroczystością: ok. 10× mniej bajtów, rampa bez zmian
        img = img.quantize(64, method=Image.Quantize.FASTOCTREE)
    img.save(buf, format=fmt, **({"optimize": True} if fmt == "PNG" else {"quality": 85}))
    return base64.b64encode(buf.getvalue()).decode()


def _parcel_shapes(cfg: Dict[str, Any], sites: List[str]) -> Dict[str, Any]:
    """Obrysy winnic: ścieżki SVG (wspólna skala; notatnik na blog) i pierścienie [lat, lon] (mapa Leaflet)."""
    import geopandas as gpd
    p = gpd.read_file(cfg["PARCELS_PATH"]).to_crs(4326)
    p = p[p["Typ"] == cfg["PARCEL_TYPE"]].copy()
    p["site_id"] = [f"VINEYARD_{int(f):02d}" for f in p["fid"]]
    p = p[p["site_id"].isin(sites) | (len(sites) == 0)]
    x0, y0, x1, y1 = p.total_bounds
    k = np.cos(np.radians((y0 + y1) / 2))
    w, h = (x1 - x0) * k, (y1 - y0)
    scale = 1000.0 / max(w, h)
    pad = 20

    def xy(lon, lat):
        return pad + (lon - x0) * k * scale, pad + (y1 - lat) * scale
    shapes = []
    for r in p.itertuples():
        polys = list(r.geometry.geoms) if r.geometry.geom_type == "MultiPolygon" else [r.geometry]
        d = ""
        for poly in polys:
            pts = [xy(lon, lat) for lon, lat in poly.exterior.coords]
            d += "M" + "L".join(f"{a:.1f},{b:.1f}" for a, b in pts) + "Z"
        c = r.geometry.representative_point()
        cx, cy = xy(c.x, c.y)
        area = float(gpd.GeoSeries([r.geometry], crs=4326).to_crs(cfg["EPSG"]).area.iloc[0] / 1e4)
        shapes.append({"id": r.site_id, "fid": int(r.fid), "d": d, "cx": round(cx, 1), "cy": round(cy, 1),
                       "area_ha": round(area, 2), "c": [round(c.y, 6), round(c.x, 6)],
                       "ll": [[[round(lat, 6), round(lon, 6)] for lon, lat in poly.exterior.coords] for poly in polys]})
    return {"shapes": sorted(shapes, key=lambda s: s["fid"]), "width": round(pad * 2 + w * scale),
            "height": round(pad * 2 + h * scale), "bounds": [[round(y0, 6), round(x0, 6)], [round(y1, 6), round(x1, 6)]]}


def pixel_maps(cfg: Dict[str, Any], n_dates: Optional[int] = None, zones: Optional[Dict[str, Any]] = None
               ) -> Dict[str, Any]:
    """
    Mapy pikseli 10 m wewnątrz winnic (NDVI, NDRE, NDMI) z ostatnich PANEL_PIXEL_DATES bezchmurnych scen sezonu
    w S2_DIR (≥ VEG_MIN_CLEAR_FRAC pikseli winnic bez chmur, jedna scena na dzień) i obraz w barwach naturalnych
    z najnowszej z nich. Statystyki działki (średnia, 10. i 90. percentyl, liczba pikseli) liczone jak produkt
    S2_10m_buf20: piksele bezchmurne w pasie PARCEL_INNER_M od brzegu. Mapa pokazuje całą działkę.
    Strefy (klucz `<indeks>_rel`): piksel minus mediana działki w tym dniu, liczone na pikselach, których środek leży
    ≥ REL_EDGE_M od brzegu; statystyki [mediana, p10 − mediana, p90 − mediana, n].
    „Zones vs usual” (klucz `<indeks>_hist`, W3c): kody komórek ze step_13 dla tej samej sceny, tylko dla wskaźników,
    które przeszły kryterium §6; statystyki [% słabsze, % potwierdzone słabsze, % mocniejsze, % potwierdzone
    mocniejsze, komórki z normą, mediana scen w normie, mediana lat w normie].
    """
    import rasterio
    from rasterio.features import rasterize
    from rasterio.transform import from_origin
    from rasterio.warp import Resampling, reproject
    from rasterio.windows import from_bounds

    import step_04_metrics_alert as s4
    layers = [{"key": k, "label": lab, "lo": lo, "hi": hi, "ramp": list(ramp), "low": low, "high": high,
               "rel": REL_RANGE[k], "rel_ramp": list(REL_RAMP[k])} for k, lab, lo, hi, ramp, low, high in PIXEL_LAYERS]
    res: Dict[str, Any] = {"dates": [], "rgb": None, "layers": layers, "bounds": None}
    scenes = sorted(glob.glob(os.path.join(cfg["S2_DIR"], "S2_L2A_*.tif")))
    if not scenes:
        return res
    n_dates = int(n_dates or cfg.get("PANEL_PIXEL_DATES", 16))
    parcels = s4.load_parcels(cfg, cfg["EPSG"]).to_crs(4326)
    m0, m1 = cfg["S2_MONTHS"]
    inner_m = float(cfg.get("PARCEL_INNER_M", 20))

    # siatka wynikowa w EPSG:4326 (Leaflet rozciąga obraz między narożnikami; dla ~1 km różnica wobec 3857 pomijalna)
    def ll_grid(bounds, step_m):
        w, s, e, n = bounds
        dlat = step_m / 111320.0
        dlon = dlat / np.cos(np.radians((s + n) / 2))
        width, height = int(np.ceil((e - w) / dlon)), int(np.ceil((n - s) / dlat))
        return from_origin(w, n, dlon, dlat), (height, width), [[n - height * dlat, w], [n, w + width * dlon]]
    pad = 20 / 111320.0
    w, s, e, n = parcels.total_bounds
    px_t, px_shape, px_bounds = ll_grid((w - pad, s - pad, e + pad, n + pad), 10.0 / PIXEL_UPSCALE)
    px_mask = rasterize(((g, 1) for g in parcels.geometry), out_shape=px_shape, transform=px_t, fill=0).astype(bool)
    res["bounds"] = [[round(v, 6) for v in c] for c in px_bounds]

    geo, box = None, None
    seen = set()
    for path in reversed(scenes):
        if len(res["dates"]) >= n_dates:
            break
        t = s4.scene_time(path)
        if not (m0 <= t.month <= m1) or t.normalize() in seen:
            continue
        with rasterio.open(path) as src:
            if geo is None:
                geo = parcels.to_crs(src.crs)
                x0, y0, x1, y1 = geo.total_bounds
                box = (x0 - CLUSTER_MARGIN_M, y0 - CLUSTER_MARGIN_M, x1 + CLUSTER_MARGIN_M, y1 + CLUSTER_MARGIN_M)
            win = from_bounds(*box, src.transform).round_offsets().round_lengths()
            data = src.read(window=win, boundless=True, fill_value=np.nan).astype("float32")
            if src.nodata is not None and np.isfinite(src.nodata):
                data[data == src.nodata] = np.nan
            tr, crs = src.window_transform(win), src.crs
        cloud = np.nan_to_num(data[s4.RASTER_CLOUD_BAND], nan=1.0)
        whole = rasterize(((g, 1) for g in geo.geometry), out_shape=cloud.shape, transform=tr, fill=0).astype(bool)
        clear = (cloud == 0) & np.isfinite(data[:10]).all(axis=0)
        if not whole.any() or clear[whole].mean() < float(cfg["VEG_MIN_CLEAR_FRAC"]):
            continue
        seen.add(t.normalize())
        idx = s4.compute_indices(data[:10])
        stats: Dict[str, Dict[str, Any]] = {}
        rel = {lay["key"]: np.full(cloud.shape, np.nan, "float32") for lay in layers}

        def mask(g):
            return (rasterize([(g, 1)], out_shape=cloud.shape, transform=tr, fill=0).astype(bool)
                    if not g.is_empty else np.zeros(cloud.shape, bool)) & clear
        for r in geo.itertuples():
            inner, core = mask(r.geometry.buffer(-inner_m)), mask(r.geometry.buffer(-REL_EDGE_M))
            stats[r.site_id] = {}
            for lay in layers:
                k = lay["key"]
                v = idx[k][inner]
                v = v[np.isfinite(v)]
                stats[r.site_id][k] = ([_r(v.mean(), 3), _r(np.percentile(v, 10), 3),
                                        _r(np.percentile(v, 90), 3), int(v.size)] if v.size else None)
                c = core & np.isfinite(idx[k])
                if c.any():
                    med = float(np.median(idx[k][c]))
                    rel[k][c] = idx[k][c] - med
                    d = rel[k][c]
                    stats[r.site_id][k + "_rel"] = [_r(med, 3), _r(np.percentile(d, 10), 3),
                                                    _r(np.percentile(d, 90), 3), int(c.sum())]
                else:
                    stats[r.site_id][k + "_rel"] = None
        pngs = {}
        for lay in layers:
            for name, a, lo, hi, ramp in (
                    (lay["key"], np.where(clear, idx[lay["key"]], np.nan), lay["lo"], lay["hi"], lay["ramp"]),
                    (lay["key"] + "_rel", rel[lay["key"]], -lay["rel"], lay["rel"], lay["rel_ramp"])):
                dst = np.full(px_shape, np.nan, "float32")
                reproject(a.astype("float32"), dst, src_transform=tr, src_crs=crs, dst_transform=px_t,
                          dst_crs="EPSG:4326", resampling=Resampling.nearest, src_nodata=np.nan, dst_nodata=np.nan)
                rgba = np.zeros(px_shape + (4,), np.uint8)
                rgba[..., :3] = _ramp(ramp, (dst - lo) / (hi - lo))
                rgba[..., 3] = np.where(px_mask & np.isfinite(dst), 255, 0)
                pngs[name] = _b64_image(rgba)
        if zones is not None:
            _hist_layers(zones, os.path.basename(path), px_t, px_shape, px_mask, pngs, stats)
        res["dates"].append({"date": t.strftime("%Y-%m-%d"), "clear": _r(clear[whole].mean(), 2), "png": pngs,
                             "stats": stats})
        if res["rgb"] is None:                       # najnowsza scena: barwy naturalne (B04, B03, B02) pod mapą
            m = CLUSTER_MARGIN_M / 111320.0
            rgb_t, rgb_shape, rgb_bounds = ll_grid((w - m * 1.4, s - m, e + m * 1.4, n + m), 5.0)
            out = np.zeros((3,) + rgb_shape, "float32")
            for k, b in enumerate((2, 1, 0)):
                reproject(np.nan_to_num(data[b], nan=0.0), out[k], src_transform=tr, src_crs=crs, dst_transform=rgb_t,
                          dst_crs="EPSG:4326", resampling=Resampling.bilinear)
            rgb = (np.clip(out * 3.2, 0, 1) ** (1 / 1.25) * 255).round().astype(np.uint8).transpose(1, 2, 0)
            res["rgb"] = {"date": t.strftime("%Y-%m-%d"), "jpg": _b64_image(np.ascontiguousarray(rgb), "JPEG"),
                          "bounds": [[round(v, 6) for v in c] for c in rgb_bounds]}
    return res


def _hist_layers(zones: Dict[str, Any], scene: str, px_t, px_shape, px_mask: np.ndarray,
                 pngs: Dict[str, str], stats: Dict[str, Dict[str, Any]]) -> None:
    """Warstwa W3c dla jednej sceny: kody komórek (siatka magazynu step_13) -> siatka mapy, kolory, statystyki."""
    from affine import Affine
    from rasterio.warp import Resampling, reproject
    if scene not in zones["scenes"]:
        return
    row = zones["scenes"].index(scene)
    h, w = (int(v) for v in zones["shape"])
    tr, crs = Affine(*zones["transform"]), str(zones["crs"])
    summ = zones.get("summary", pd.DataFrame())
    for k in zones.get("show_indices", []):
        codes = zones[f"codes_{k}"][row]
        grid = np.full(h * w, np.nan, "float32")
        grid[zones["pix"]] = np.where(codes >= 0, codes, np.nan)
        dst = np.full(px_shape, np.nan, "float32")
        reproject(grid.reshape(h, w), dst, src_transform=tr, src_crs=crs, dst_transform=px_t, dst_crs="EPSG:4326",
                  resampling=Resampling.nearest, src_nodata=np.nan, dst_nodata=np.nan)
        rgba = np.zeros(px_shape + (4,), np.uint8)
        for code, col in {**HIST_RGBA, **HIST_STRONG[k]}.items():
            rgba[(dst == code) & px_mask] = col
        pngs[f"{k}_hist"] = _b64_image(rgba)
        for j, sid in enumerate(zones["sites"]):
            c = codes[zones["site_idx"] == j]
            n = int(np.isin(c, (0, 1, 2, 3, 4)).sum())
            if c.max() < 0:
                stats.setdefault(sid, {})[f"{k}_hist"] = None
                continue
            q = summ[(summ["site_id"] == sid) & (summ["scene"] == scene) & (summ["index"] == k)] if len(summ) else summ
            pct = (lambda m: _r(100 * m / n, 1) if n else None)
            stats.setdefault(sid, {})[f"{k}_hist"] = [
                pct(int(np.isin(c, (1, 2)).sum())), pct(int((c == 2).sum())), pct(int(np.isin(c, (3, 4)).sum())),
                pct(int((c == 4).sum())), n, _r(q["med_ref_scenes"].iat[0], 0) if len(q) else None,
                _r(q["med_ref_years"].iat[0], 0) if len(q) else None]


def _verdict_en(v: str) -> str:
    """Werdykt kryterium W3c (step_13.criterion_row, PL) po angielsku dla panelu."""
    import re
    out = []
    for part in v.replace("nie pokazujemy — ", "").split("; "):
        m2 = re.match(r"2: MDC95 górna ([\d.]+) ≥ ½ rozstępu działki ([\d.]+)", part)
        m3 = re.match(r"3: udział komórek w strefach \((.*)\) górna ([\d.]+)% > (\d+)%", part)
        if part.startswith("1:"):
            out.append("too few pairs of scenes for the noise test")
        elif m2:
            out.append(f"noise (upper MDC95 {m2.group(1)}) is not below half the typical spread within a parcel "
                       f"({m2.group(2)})")
        elif m3:
            out.append(f"zones cover too much on {_subset_en(m3.group(1))} (upper {m3.group(2)}% > {m3.group(3)}%)")
        elif part.startswith(("2:", "3:")):
            out.append("too few years for a confidence interval")
        elif part == "pokazujemy":
            out.append("shown")
        else:
            out.append(part)
    return "; ".join(out)


def _subset_en(sub: str) -> str:
    return {"gleba w normie": "days with normal soil", "wszystkie dni VI–IX": "all June–September days",
            "wszystkie dni VI–IX (dni z glebą w normie w < 3 latach)":
                "all June–September days (normal-soil days in fewer than 3 years)"}.get(sub, sub)


def zones_info(out_dir: str) -> Optional[Dict[str, Any]]:
    """Wyniki W3c dla panelu: kody (step_13.load_zones), progi T, werdykty kryterium, wiersze Z1/Z2 do zaufania."""
    import step_13_zones as s13
    z = s13.load_zones(out_dir)
    t = _opt(os.path.join(out_dir, s13.TESTS_NAME))
    if z is None or t is None:
        return None
    k_rows = t.set_index("key")
    info = {"show": [], "T": {}, "verdict": {}, "z1": {}, "z2": {}, "freeze": str(t["freeze"].iat[0]),
            "protocol": str(t["protocol_sha256"].iat[0])[:12]}
    for k in [str(v).split("_")[-1] for v in t["key"].dropna() if str(v).startswith("z_show_")]:
        crit = k_rows.loc[f"z_show_{k}"]
        info["verdict"][k] = _verdict_en(str(crit["verdict"]))
        info["T"][k] = _r(k_rows.loc[f"z_T_{k}", "value"], 4) if f"z_T_{k}" in k_rows.index else None
        g = next((g for g in ("g5", "g13") if f"z1_{g}_{k}" in k_rows.index
                  and np.isfinite(float(k_rows.loc[f"z1_{g}_{k}", "value"]))), None)
        if g:
            r = k_rows.loc[f"z1_{g}_{k}"]
            info["z1"][k] = {"group": g.upper(), "value": _r(r["value"], 4), "lo": _r(r["ci_low"], 4),
                             "hi": _r(r["ci_high"], 4), "n": int(r["n"])}
        if f"z2_normal_{k}" in k_rows.index:
            r = k_rows.loc[f"z2_normal_{k}"]
            info["z2"][k] = {"value": _r(r["value"], 4), "lo": _r(r["ci_low"], 4), "hi": _r(r["ci_high"], 4),
                             "subset": _subset_en(str(r["subset"]).split(", strefy")[0])}
        if float(crit["value"]) == 1.0 and f"codes_{k}" in z:
            info["show"].append(k)
    z["show_indices"] = info["show"]
    info["data"] = z
    return info


def weather_data(out_dir: str, cfg: Dict[str, Any], lat: float, lon: float, forecast: Any = "fetch") -> Dict[str, Any]:
    """
    Pogoda okolicy: prognoza 7 dni (Open-Meteo; forecast="fetch" pobiera, DataFrame z kolumnami date, tmax, tmin,
    precip_mm, et0_mm podaje gotową, None pomija), ostatnie 10 dni ERA5-Land, opad 30 / 90 dni z SPI, gleba 0–7 cm
    i przymrozki / upały sezonu z task_weather.
    """
    w: Dict[str, Any] = {"thr": {"frost": cfg["FROST_TMIN"], "heat": cfg["HEAT_TMAX"]},
                         "fc_thr": {"frost": cfg["FROST_TMIN"], "heat": cfg["HEAT_TMAX"]},
                         "frost_season": list(cfg["FROST_SEASON"])}
    fc = forecast
    if isinstance(forecast, str) and forecast == "fetch":
        import step_06_dashboard as s6
        fc = s6.fetch_forecast(lat, lon)
    if fc is not None and len(fc):
        w["forecast"] = [{"date": pd.Timestamp(r.date).strftime("%Y-%m-%d"), "tmax": _r(r.tmax, 1), "tmin": _r(r.tmin, 1),
                          "rain": _r(r.precip_mm, 1), "et0": _r(r.et0_mm, 1)} for r in fc.itertuples()]
    e = _opt(os.path.join(cfg["ERA5_DIR"], "era5_land_daily.csv"), parse_dates=["time"])
    if e is not None and {"precip_mm", "t2m_min_c", "t2m_max_c"} <= set(e.columns):
        e = e.dropna(subset=["precip_mm"]).sort_values("time").tail(10)
        w["last10"] = [{"date": r.time.strftime("%Y-%m-%d"), "rain": _r(r.precip_mm, 1), "tmin": _r(r.t2m_min_c, 1),
                        "tmax": _r(r.t2m_max_c, 1)} for r in e.itertuples()]
    a = _opt(os.path.join(out_dir, "era5_daily_anomalies.csv"), header=[0, 1], index_col=0, parse_dates=True)
    if a is not None:
        def last(col, sub):
            if (col, sub) not in a:
                return None
            s = a[(col, sub)].dropna()
            return [s.index[-1].strftime("%Y-%m-%d"), _r(s.iat[-1], 1)] if len(s) else None
        w["drivers"] = {"rain30": last("ERA5L_SPI1", "value"), "spi1": last("ERA5L_SPI1", "z"),
                        "rain90": last("ERA5L_SPI3", "value"), "spi3": last("ERA5L_SPI3", "z"),
                        "top_pct": last("ERA5L_SM_L1", "percentile")}
    q = os.path.join(out_dir, "hazard_thresholds.json")
    if os.path.exists(q):
        thr = json.load(open(q, encoding="utf-8"))
        w["thr"].update({k: thr[k] for k in ("frost", "heat") if k in thr})
    hz = _opt(os.path.join(out_dir, "hazard_summary.csv"))
    if hz is not None and len(hz):
        r = hz.sort_values("year").iloc[-1]
        w["season"] = {"year": int(r["year"]), "frost_days": int(r["frost_days"]), "heat_days": int(r["heat_days"]),
                       "last_frost": r["last_frost"] if isinstance(r.get("last_frost"), str) else None,
                       "max_tmax": _r(r.get("max_tmax"), 1)}
    return w


def panel_data(out_dir: str, cfg: Dict[str, Any], forecast: Any = "fetch") -> Dict[str, Any]:
    """Dane panelu z plików wynikowych: warstwy z dla 15 winnic w dniach scen, mapy pikseli, karty (EN), gleba,
    pogoda, walidacja. Mapy pikseli i pogoda są opcjonalne: ich błąd zostawia resztę panelu."""
    import step_09_panels as s9
    import step_11_parcel as s11
    pa = pd.read_csv(os.path.join(out_dir, "parcel_anomalies.csv"), parse_dates=["time"])
    pa["day"] = pa["time"].dt.normalize()
    tests = _opt(os.path.join(out_dir, "w3b_tests.csv"))
    summ = s11.tests_summary(tests)
    area = _opt(os.path.join(out_dir, "parcel_area.csv"))
    flags = _opt(os.path.join(out_dir, "parcel_flags.csv"))
    sites = sorted(pa["site_id"].unique())
    qc = pa.groupby("site_id")["qc_ok"].first().map(lambda v: str(v).strip().lower() in ("true", "1"))
    npx = pd.to_numeric(pa["n_pixels"], errors="coerce").groupby(pa["site_id"]).max()

    water = pa[(pa["index"] == "water") & pa["z"].notna()]
    first = water["day"].min()
    days = sorted(pa.loc[pa["z"].notna() & (pa["day"] >= first), "day"].unique())
    dix = {pd.Timestamp(d): i for i, d in enumerate(days)}
    layers = {}
    for key, _, sign, _ in LAYERS:
        sub = pa[(pa["index"] == key) & pa["z"].notna()]
        layers[key] = {}
        for sid, g in sub.groupby("site_id"):
            arr: List[Optional[float]] = [None] * len(days)
            for d, z in zip(g["day"], g["z"]):
                i = dix.get(pd.Timestamp(d))
                if i is not None:
                    arr[i] = _r(sign * z)
            layers[key][sid] = arr

    # gleba: percentyl ERA5-Land 0–100 cm wobec 1991–2020 (ta sama definicja co karta wody)
    soil_pct = pd.Series(dtype=float)
    e = _opt(os.path.join(out_dir, "era5_daily_anomalies.csv"), header=[0, 1], index_col=0, parse_dates=True)
    if e is not None and ("ERA5L_SM_RZ", "percentile") in e:
        soil_pct = e[("ERA5L_SM_RZ", "percentile")].dropna()
        soil_pct = soil_pct[soil_pct.index >= pd.Timestamp(first).replace(month=1, day=1)]
    last = pd.Timestamp(days[-1]) if days else pd.Timestamp.now().normalize()
    soil, soil_now = None, None
    if len(soil_pct):
        sd = soil_pct[soil_pct.index <= last + pd.Timedelta(days=1)]
        if len(sd):
            p = float(sd.iat[-1])
            code, label, _ = s9.water_category(p, cfg)
            soil = {"soil_class": s9._swi_class(p, cfg), "percentile": p, "category": {"code": code, "label": label},
                    "date": sd.index[-1], "clim_ref": (str(cfg["CLIM_REF"][0])[:4], str(cfg["CLIM_REF"][1])[:4])}
            soil_now = {"pct": _r(p, 0), "code": code, "label": s9.WATER_LABEL_EN.get(code, ""),
                        "class": soil["soil_class"], "date": sd.index[-1].strftime("%Y-%m-%d"),
                        "clim_ref": f"{soil['clim_ref'][0]}–{soil['clim_ref'][1]}"}

    cards = {}
    for sid in sites:
        card = s9.parcel_card(pa, area, flags, summ, soil, cfg, sid, today=last)
        lines = s9.parcel_card_lines(card, "en")
        cards[sid] = {"sentences": lines["sentences"], "notes": lines["notes"], "trust": lines["trust"],
                      "detail": lines["detail"], "fixed": lines["fixed"], "state": card["state"],
                      "date": card["date"].strftime("%Y-%m-%d") if card["date"] is not None else None}

    shapes = _parcel_shapes(cfg, sites)
    try:
        zinfo = zones_info(out_dir)
    except Exception as ex:                                   # brak albo uszkodzone wyniki W3c: panel bez tej warstwy
        logger.warning(f"Panel: wyniki W3c niedostępne: {type(ex).__name__}: {ex}")
        zinfo = None
    try:
        pixels = pixel_maps(cfg, zones=(zinfo or {}).get("data"))
    except Exception as ex:                                   # mapa działa dalej na warstwach „wobec historii”
        logger.warning(f"Panel: mapy pikseli niedostępne: {type(ex).__name__}: {ex}")
        pixels = {"dates": [], "rgb": None, "layers": [], "bounds": None}
    lat, lon = np.mean(np.array(shapes["bounds"]), axis=0)
    try:
        weather = weather_data(out_dir, cfg, float(lat), float(lon), forecast)
    except Exception as ex:
        logger.warning(f"Panel: pogoda niedostępna: {type(ex).__name__}: {ex}")
        weather = {}

    return {"generated": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d"), "last_scene": last.strftime("%Y-%m-%d"),
            "freeze": (summ or {}).get("freeze", ""), "protocol": ((summ or {}).get("protocol_sha256") or "")[:12],
            "region": cfg.get("PANEL_REGION", "Condom · Gers, France"),
            "map": shapes, "pixels": pixels, "weather": weather, "soil_now": soil_now,
            "sites": {sid: {"qc_ok": bool(qc.get(sid, False)), "n_pixels": _r(npx.get(sid), 0)} for sid in sites},
            "dates": [pd.Timestamp(d).strftime("%Y-%m-%d") for d in days],
            "layers": layers, "layer_info": [{"key": k, "label": lab, "about": about} for k, lab, _, about in LAYERS],
            "soil": {"dates": [d.strftime("%Y-%m-%d") for d in soil_pct.index],
                     "pct": [int(round(v)) for v in soil_pct.to_numpy()]},
            "cards": cards, "trust": trust_rows(out_dir, cfg, summ, tests, zinfo),
            "zones": {k: v for k, v in (zinfo or {}).items() if k != "data"} or None,
            "inner_m": int(cfg.get("PARCEL_INNER_M", 20)), "min_px": int(cfg.get("PARCEL_MIN_PX", 40)),
            "main_site": cfg.get("MAIN_SITE", "VINEYARD_06")}


def trust_rows(out_dir: str, cfg: Dict[str, Any], summ: Optional[Dict[str, Any]],
               tests: Optional[pd.DataFrame], zinfo: Optional[Dict[str, Any]] = None) -> List[Dict[str, str]]:
    """Tabela „How far to trust it”: co, wynik, status (validated / partly / not confirmed / not validated)."""
    import step_09_panels as s9
    rows: List[Dict[str, str]] = []

    def f(x, nd=2):
        return "—" if x is None or not np.isfinite(float(x)) else f"{float(x):.{nd}f}"
    ref = _opt(os.path.join(out_dir, "validation_reference.csv"))
    if ref is not None:
        for prod, what in (("ERA5L_SM_RZ", "Soil moisture 0–100 cm (ERA5-Land model, ~9 km)"),
                           (f"SWI_v4_T{int(cfg.get('SWI_T', 15)):03d}", "Soil water index (ASCAT satellite, ~10 km)")):
            parts, agree = [], []
            for site, reference, seg, _, name in s9.REF_TRUST_SITES:
                q = ref[(ref["site_id"] == site) & (ref["reference"] == reference) & (ref["product"] == prod)]
                r = q[(q["segment"] == seg) & (q["metric"] == "pearson_r")]
                a = q[(q["segment"] == "class_agreement") & (q["metric"] == "agreement")]
                if len(r):
                    parts.append(f"{name.split(' (')[0]} R {f(r['value'].iat[0])}")
                if len(a):
                    agree.append(f"{100 * a['value'].iat[0]:.0f}%")
            if parts:
                rows.append({"what": what, "against": "in situ soil sensors at 3 stations (ISMN Condom, ICOS Auradé "
                                                      "and Lusignan)",
                             "result": "; ".join(parts) + (f"; same dry/normal/wet class on {', '.join(agree)} of days"
                                                           if agree else ""),
                             "status": "validated"})
    wv = _opt(os.path.join(out_dir, "validation_weather.csv"))
    if wv is not None:
        q = wv[(wv["product"] == "ERA5L_PRECIP") & (wv["segment"] == "sum_30d") & (wv["period"].astype(str) == "all")
               & (wv["metric"] == "pearson_r")]
        if len(q):
            rows.append({"what": "Rainfall, 30-day sums (ERA5-Land)", "against": f"rain gauge {q['subset'].iat[0]}",
                         "result": f"R {f(q['value'].iat[0])}", "status": "validated"})
    if summ:
        t2 = summ["mdc"]
        g5, g13 = (t2.get("G5") or {}).get("value"), (t2.get("G13") or {}).get("value")
        rows.append({"what": "Parcel vegetation water index: noise between scenes",
                     "against": "pairs of scenes a few days apart without rain",
                     "result": f"smallest clear change: {f(g5, 1)} z (same orbit), {f(g13, 1)} z (different orbits)",
                     "status": "validated"})
        t1 = summ["t1"]
        normal = None
        if tests is not None:
            q = tests[tests["subset"].astype(str).str.startswith("gleba w normie")]
            normal = q["value"].iat[0] if len(q) else None
        rows.append({"what": "Parcel index: how often “below its own normal” appears",
                     "against": "all scenes June–September, 13 vineyards (expected 16%, 1 in 6)",
                     "result": f"{100 * t1['value']:.0f}% [{100 * t1['lo']:.0f}–{100 * t1['hi']:.0f}%], mostly in dry "
                               f"years" + (f"; {100 * normal:.0f}% when soil is near normal" if normal is not None else ""),
                     "status": "validated"})
        t3 = summ["t3"]
        rows.append({"what": "Area vegetation follows soil water of the previous 30 days",
                     "against": "ISMN sensor at Condom, June–September 2018–2024 (pre-registered test)",
                     "result": f"ρ {f(t3['value'])} [{f(t3['lo'])}; {f(t3['hi'])}]; mostly between years, not within "
                               f"a season", "status": "confirmed" if t3.get("passed") else "not confirmed"})
        d = summ["p7"].get("delta") or {}
        rows.append({"what": "4-band model (red, red-edge, NIR, SWIR) instead of the simple index",
                     "against": "same test, years unseen by the model",
                     "result": f"no gain: Δρ {f(d.get('value'))} [{f(d.get('lo'))}; {f(d.get('hi'))}]",
                     "status": "accepted" if summ["p7"].get("accepted") else "not adopted"})
    for k, name in (("ndvi", "greenness (NDVI)"), ("ndmi", "water in vegetation (NDMI)")):
        if not zinfo or k not in zinfo["verdict"]:
            continue
        z1, z2, shown = zinfo["z1"].get(k), zinfo["z2"].get(k), k in zinfo["show"]
        res = (f"threshold {f(z1['value'], 3)} [{f(z1['lo'], 3)}–{f(z1['hi'], 3)}] from {z1['n']} scene pairs "
               f"({z1['group']})" if z1 else "too few scene pairs for a threshold")
        if z2 and z2.get("value") is not None:
            res += f"; cells in zones: {100 * z2['value']:.1f}% [{100 * z2['lo']:.1f}–{100 * z2['hi']:.1f}%] ({z2['subset']})"
        if not shown:
            res += "; not shown: " + zinfo["verdict"][k]
        rows.append({"what": f"Zones vs usual, {name}: places weaker or stronger than usual, relative to the parcel",
                     "against": "noise between scenes a few days apart without rain; how often zones appear when soil "
                                "is normal (pre-registered W3c, " + zinfo["protocol"] + "…)",
                     "result": res, "status": "noise-tested" if shown else "not shown"})
    rows.append({"what": "Vine water stress", "against": "no measurements inside the vineyards",
                 "result": "not assessed; the index sees the whole parcel, vines and inter-rows", "status": "not validated"})
    return rows


_CSS = """
/* Wago-like product page: green top bar, vineyard list | map + statistics | state, soil, weather, plot data.
   One light look on purpose (map imagery and the index ramps are tuned for it); every colour set explicitly. */
:root{--bg:#eef2ea;--panel:#ffffff;--ink:#1f2a22;--muted:#5d695f;--line:#dde3d8;--brand:#6f9b3a;--brand-d:#4b7023;
--brand-l:#eaf2df;--sel:#f2c230;--wb:#7a4a0e;--b:#c08a3e;--n:#e9e6dc;--a:#5fa69b;--wa:#1f6a62;--nd:#cfd3cc;
--ok:#2f7a45;--warn:#a26b00;--bad:#b23a2e;--soil:#8a6a3d;--rain:#2f75b5;color-scheme:light;
--ui:"Figtree",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;--mono:"IBM Plex Mono",ui-monospace,Menlo,Consolas,monospace}
body{background:var(--bg);color:var(--ink);font-family:var(--ui);font-size:15px;line-height:1.45;margin:0}
.top{background:var(--brand);color:#fff;padding-block:10px;padding-left:max(16px,env(safe-area-inset-left,0px));
padding-right:max(16px,env(safe-area-inset-right,0px));display:flex;flex-wrap:wrap;gap:4px 18px;align-items:center;
justify-content:space-between}
.logo{display:flex;align-items:center;gap:8px;font-weight:700;font-size:1.25rem;letter-spacing:.01em}
.logo small{font-weight:400;font-size:.95rem;opacity:.92}
.top .meta{font-size:.82rem;opacity:.95;font-family:var(--mono)}
.tabs{background:var(--panel);border-bottom:1px solid var(--line);display:flex;overflow-x:auto;
padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
.tabs a{color:var(--muted);text-decoration:none;font-size:.78rem;letter-spacing:.08em;text-transform:uppercase;
padding:12px 18px;border-bottom:3px solid transparent;white-space:nowrap}
.tabs a:first-child{color:var(--brand-d);border-bottom-color:var(--brand)}
.tabs a:hover{color:var(--brand-d)}
.app{display:grid;grid-template-columns:240px minmax(0,1fr) 350px;gap:14px;align-items:start;padding-block:14px 32px;
padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));
max-width:1680px;margin:0 auto}
.side{grid-row:span 2;position:sticky;top:10px}
.wide{grid-column:2 / 4;display:grid;gap:14px;min-width:0}
.col{display:grid;gap:14px;min-width:0}
.box{background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:14px;min-width:0}
h2{font-size:1.15rem;font-weight:600;margin:0;text-wrap:balance}
h3{font-size:.74rem;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin:0 0 8px;font-weight:600}
.side h2{font-size:1.25rem;margin-bottom:6px}
.region{display:flex;justify-content:space-between;font-size:.74rem;text-transform:uppercase;letter-spacing:.07em;
color:var(--muted);border-top:1px solid var(--line);padding:10px 2px 6px;margin-top:6px}
.vlist{display:grid;gap:2px}
.vlist button{all:unset;box-sizing:border-box;display:flex;align-items:center;gap:9px;padding:8px 9px;border-radius:5px;
cursor:pointer;font-size:.95rem}
.vlist button:hover{background:var(--brand-l)}
.vlist button[aria-pressed=true]{background:var(--brand);color:#fff}
.vlist button[aria-pressed=true] .ha{color:#eef6e4}
.vlist .ha{margin-left:auto;font-family:var(--mono);font-size:.78rem;color:var(--muted)}
.dot{width:12px;height:12px;border-radius:50%;flex:none;border:1px solid rgba(0,0,0,.25)}
.vlist .all{font-weight:600}
.side .small{margin-top:10px}
.mhead{display:flex;flex-wrap:wrap;gap:6px 14px;align-items:baseline;justify-content:space-between;margin-bottom:10px}
.mhead .ha{font-family:var(--mono);font-size:.9rem;color:var(--muted);font-weight:400}
.ctrl{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:end;margin-bottom:10px}
.ctrl label{display:grid;gap:3px;font-size:.7rem;text-transform:uppercase;letter-spacing:.07em;color:var(--muted)}
select,button.step{font:inherit;font-size:.92rem;color:var(--ink);background:#fff;border:1px solid #c9d1c4;border-radius:5px;
padding:6px 8px;cursor:pointer;text-transform:none;letter-spacing:0}
.datebox{display:flex;gap:4px}
input[type=range]{accent-color:var(--brand);width:120px}
:focus-visible{outline:2px solid var(--brand-d);outline-offset:2px}
#lmap{height:560px;border-radius:4px;background:#d9dfd3;position:relative}
.legend-box{position:absolute;left:10px;bottom:10px;z-index:500;background:rgba(255,255,255,.94);border-radius:4px;
padding:8px 10px;font-size:.78rem;min-width:220px;max-width:calc(100% - 20px);box-shadow:0 1px 4px rgba(0,0,0,.25)}
.legend-box b{display:block;text-align:center;font-weight:600;margin-bottom:4px;font-size:.88rem}
.ramp{height:10px;border-radius:2px;margin:3px 0}
.rl{display:flex;justify-content:space-between;color:var(--muted);font-family:var(--mono);font-size:.72rem}
.sw{display:inline-block;width:11px;height:11px;border-radius:2px;border:1px solid rgba(0,0,0,.2);vertical-align:-1px;margin-right:4px}
.zl{display:flex;flex-wrap:wrap;gap:3px 10px}
.vlabel{background:rgba(31,42,34,.72);color:#fff;border:0;box-shadow:none;font-family:var(--mono);font-size:11px;
padding:0 4px;border-radius:3px}
.vlabel:before{display:none}
.pxl{image-rendering:pixelated}
.nomap{padding:20px;color:var(--muted)}
.note{font-size:.8rem;color:var(--muted);margin:8px 0 0}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin-top:12px}
.tile{border:1px solid var(--line);border-radius:5px;padding:9px 11px;display:grid;gap:2px}
.tile span{font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}
.tile b{font-family:var(--mono);font-size:1.45rem;font-weight:500;font-variant-numeric:tabular-nums}
.tile small{font-size:.78rem;color:var(--muted)}
.tbl{overflow-x:auto;margin-top:12px}
table{border-collapse:collapse;width:100%;font-size:.86rem}
th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:.7rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);font-weight:600}
td.num{font-family:var(--mono);font-variant-numeric:tabular-nums;white-space:nowrap}
tr.pick{cursor:pointer}tr.pick:hover{background:var(--brand-l)}
.alert{border:2px solid var(--nd);text-align:center;display:grid;gap:4px;justify-items:center}
.alert .ic{width:34px;height:34px}
.chip{display:inline-block;font-family:var(--mono);font-size:.8rem;padding:2px 8px;border-radius:3px}
.alert .big{font-size:1.6rem;font-weight:600;font-family:var(--mono)}
.alert p{margin:0;font-size:.92rem}
.gauge{text-align:center}
.gauge .lab{font-size:1.15rem;font-weight:600;margin-top:-6px}
.wx{padding:0;overflow:hidden}
.wx .in{padding:12px 14px}
.today{background:var(--brand);color:#fff;padding:12px 14px;display:grid;grid-template-columns:1fr 1fr 1fr;gap:4px;
text-align:center}
.today .t0{grid-column:1/4;font-weight:600}
.today .tmax{grid-column:1/4;font-size:2rem;font-weight:600;font-family:var(--mono)}
.today div small{display:block;font-size:.72rem;opacity:.9}
.today div b{font-family:var(--mono)}
.days{display:grid}
.days div{display:grid;grid-template-columns:7ch 1fr auto;gap:8px;padding:6px 14px;border-bottom:1px solid var(--line);
font-size:.88rem;align-items:center}
.days .r{color:var(--rain);font-family:var(--mono);font-size:.82rem}
.days .t{font-family:var(--mono);text-align:right}
.flag{font-size:.68rem;padding:1px 6px;border-radius:9px;background:#fde7c8;color:#7a4a0e;margin-left:6px}
.flag.frost{background:#dbe9f7;color:#1f4f86}
.kv{display:grid;grid-template-columns:auto 1fr;gap:4px 12px;font-size:.88rem}
.kv span{color:var(--muted)}
.kv b{font-weight:500;text-align:right;font-family:var(--mono);font-size:.86rem}
.fields{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.field{border:1px solid #c9d1c4;border-radius:4px;padding:16px 10px 7px;position:relative;font-size:.92rem}
.field span{position:absolute;top:-8px;left:8px;background:var(--panel);padding:0 4px;font-size:.72rem;color:var(--muted)}
.field.w2{grid-column:1/3}
.card ol{padding-left:20px;margin:8px 0;display:grid;gap:6px}
.notes{color:var(--warn);font-size:.88rem;margin:6px 0;padding-left:18px}
.small{color:var(--muted);font-size:.82rem}
svg text{fill:var(--muted);font-family:var(--mono);font-size:11px}
.st-validated,.st-confirmed,.st-accepted{color:var(--ok)}.st-not-confirmed,.st-not-adopted{color:var(--warn)}
.st-not-validated{color:var(--bad)}
footer{grid-column:1 / -1;color:var(--muted);font-size:.82rem;max-width:110ch}
footer a{color:var(--brand-d)}
.leaflet-container{font-family:var(--ui)}
/* narrower screens last, so they override the rules above */
@media (max-width:1240px){.app{grid-template-columns:220px minmax(0,1fr)}.right{grid-column:2}.wide{grid-column:2}}
@media (max-width:760px){.app{grid-template-columns:minmax(0,1fr)}.side{position:static;grid-row:auto}
.right,.wide{grid-column:1}.vlist{display:flex;overflow-x:auto;gap:6px}.vlist button{flex:none;white-space:nowrap}
.region{display:none}#lmap{height:400px}}
"""

_JS = r"""
const D = JSON.parse(document.getElementById('panel-data').textContent);
const $ = id => document.getElementById(id);
const fmt = (d, o) => new Date(d + 'T00:00:00Z').toLocaleDateString('en-GB',
  Object.assign({day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC'}, o || {}));
const esc = t => String(t).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
const num = (v, nd) => v == null ? '—' : (v < 0 ? '−' : '') + Math.abs(v).toFixed(nd);
const COL = {wb: '#7a4a0e', b: '#c08a3e', n: '#e9e6dc', a: '#5fa69b', wa: '#1f6a62', nd: '#cfd3cc'};
const cls = z => z == null ? 'nd' : z <= -1.5 ? 'wb' : z <= -1 ? 'b' : z < 1 ? 'n' : z < 1.5 ? 'a' : 'wa';
const CLS_TXT = {wb: 'well below its normal', b: 'below its normal', n: 'within its normal', a: 'above its normal',
                 wa: 'well above its normal', nd: 'no clear scene'};
const SH = Object.fromEntries(D.map.shapes.map(s => [s.id, s]));
const vname = id => 'Vineyard ' + String(SH[id].fid).padStart(2, '0');
const PX = D.pixels && D.pixels.dates ? D.pixels : {dates: [], layers: []};
const PXL = Object.fromEntries(PX.layers.map(l => [l.key, l]));
const ZL = Object.fromEntries(D.layer_info.map(l => [l.key, l]));
const qc = id => !!(D.sites[id] && D.sites[id].qc_ok);
const dIndex = Object.fromEntries(D.dates.map((d, i) => [d, i]));
const zAt = (key, site, i) => i == null ? null : (((D.layers[key] || {})[site] || [])[i] ?? null);
const median = a => { a = a.filter(v => v != null).sort((x, y) => x - y); if (!a.length) return null;
  const m = a.length >> 1; return a.length % 2 ? a[m] : (a[m - 1] + a[m]) / 2; };
let S = {site: 'ALL', layer: PX.dates.length ? 'px:ndvi' : 'z:water', pi: 0, di: D.dates.length - 1, op: 0.8, base: 'esri'};
try { const m = JSON.parse(localStorage.getItem('agriscreen-v2') || '{}');
  if (m.site && (m.site === 'ALL' || SH[m.site])) S.site = m.site;
  if (m.layer && (m.layer.startsWith('z:') || PX.dates.length)) S.layer = m.layer; } catch (e) {}
if (!/^(px|rel|hist|z):/.test(S.layer) || (S.layer.startsWith('hist:') && !ZN.show.includes(S.layer.slice(5)))) S.layer = PX.dates.length ? 'px:ndvi' : 'z:water';
const mode = () => S.layer.split(':')[0], key = () => S.layer.split(':')[1];
const isPx = () => mode() !== 'z';                       // 'px' value, 'rel' vs parcel median: pixel-map dates
const pk = () => mode() === 'rel' ? key() + '_rel' : mode() === 'hist' ? key() + '_hist' : key();
const ZN = D.zones || {show: [], T: {}, verdict: {}};
const HIST_COL = {ndvi: ['#d69650', '#7a3a0e', '#7dbf5a', '#1f7a33'], ndmi: ['#d69650', '#7a3a0e', '#6fa9d6', '#1f4f8f']};
const curDate = () => isPx() ? PX.dates[S.pi].date : D.dates[S.di];
const sgn = (v, nd) => v == null ? '—' : (v > 0 ? '+' : '') + num(v, nd);

// latest state of each vineyard (card: latest scene; water index against its own history)
function stateOf(id) {
  const c = D.cards[id] || {};
  if (!qc(id)) return {c: 'nd', txt: 'too small for a reliable anomaly', z: null, date: c.date};
  const z = c.date ? zAt('water', id, dIndex[c.date]) : null;
  if (c.state !== 'ok' || z == null) return {c: 'nd', txt: c.state === 'stale' ? 'no clear scene in the last 30 days' : 'no clear scene', z, date: c.date};
  return {c: cls(z), txt: CLS_TXT[cls(z)], z, date: c.date};
}

// ---------- sidebar ----------
function side() {
  const btn = (id, label, extra, dot) => `<button type="button" data-site="${id}" aria-pressed="${S.site === id}"${id === 'ALL' ? ' class="all"' : ''}>` +
    `<span class="dot" style="background:${dot}"></span>${label}<span class="ha">${extra}</span></button>`;
  let h = btn('ALL', 'All vineyards', D.map.shapes.length, 'linear-gradient(135deg,#c08a3e,#5fa69b)');
  h += `<div class="region"><span>${esc(D.region)}</span><span>${D.map.shapes.length}</span></div>`;
  D.map.shapes.forEach(s => { const st = stateOf(s.id); h += btn(s.id, vname(s.id), s.area_ha.toFixed(1) + ' ha', COL[st.c]); });
  $('vlist').innerHTML = h;
  $('vlist').querySelectorAll('button').forEach(b => b.addEventListener('click', () => select(b.dataset.site)));
}

// ---------- map ----------
let map = null, ov = null, esri = null;
const polys = {};
if (window.L) {
  map = L.map('lmap', {zoomSnap: 0.25, scrollWheelZoom: false});
  map.createPane('fallback').style.zIndex = 150;
  map.createPane('pixels').style.zIndex = 350;
  if (PX.rgb) L.imageOverlay('data:image/jpeg;base64,' + PX.rgb.jpg, PX.rgb.bounds,
    {pane: 'fallback', attribution: `Sentinel-2 ${PX.rgb.date} (Copernicus)`}).addTo(map);
  esri = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    {maxZoom: 19, maxNativeZoom: 18, attribution: 'Imagery © Esri, Maxar, Earthstar Geographics'}).addTo(map);
  D.map.shapes.forEach(s => {
    const p = L.polygon(s.ll, {weight: 1.5, color: '#fff', fillOpacity: 0}).addTo(map);
    p.on('click', () => select(s.id));
    p.bindTooltip(String(s.fid).padStart(2, '0'), {permanent: true, direction: 'center', className: 'vlabel'});
    polys[s.id] = p;
  });
  map.fitBounds(D.map.bounds, {padding: [24, 24]});
} else {
  $('lmap').innerHTML = '<p class="nomap">The map library could not load here. Lists, statistics and charts still work.</p>';
}

function drawMap() {
  if (!map) return;
  if (ov) { map.removeLayer(ov); ov = null; }
  if (isPx() && PX.dates[S.pi] && PX.dates[S.pi].png[pk()])
    ov = L.imageOverlay('data:image/png;base64,' + PX.dates[S.pi].png[pk()], PX.bounds,
      {pane: 'pixels', opacity: S.op, className: 'pxl'}).addTo(map);
  styleParcels();
  esri.setOpacity(S.base === 'esri' ? 1 : 0);
}
function styleParcels() {
  D.map.shapes.forEach(s => {
    const sel = s.id === S.site, z = mode() === 'z' ? zAt(key(), s.id, S.di) : null;
    polys[s.id].setStyle({color: sel ? '#f2c230' : '#ffffff', weight: sel ? 3.5 : 1.5, dashArray: qc(s.id) ? null : '4 3',
      fillColor: COL[qc(s.id) ? cls(z) : 'nd'], fillOpacity: mode() === 'z' ? S.op : 0});
    if (sel) polys[s.id].bringToFront();
  });
}
function legend() {
  let h;
  if (mode() === 'hist') {
    const c = HIST_COL[key()], dry = key() === 'ndmi' ? 'drier' : 'weaker', wet = key() === 'ndmi' ? 'wetter' : 'stronger';
    h = `<b>${esc(PXL[key()].label)} vs usual for this place</b><div class="zl">` +
      [[c[1], `${dry} than usual, confirmed`], [c[0], `${dry}, new`], [c[3], `${wet}, confirmed`], [c[2], `${wet}, new`],
       ['#969b96', 'history too short'], ['#f4f4f0', 'as usual']]
        .map(([col, t]) => `<span><span class="sw" style="background:${col}"></span>${t}</span>`).join('') + '</div>' +
      `<div class="rl"><span>threshold ${num(ZN.T[key()], 3)} from the noise test · zones ≥ 4 cells of 30 m · ${fmt(curDate())}</span></div>`;
  } else if (mode() === 'rel') {
    const l = PXL[key()], r = l.rel_ramp;
    h = `<b>${esc(l.label)} vs parcel median</b><div class="ramp" style="background:linear-gradient(90deg,${r.join(',')})"></div>` +
      `<div class="rl"><span>${sgn(-l.rel, 2)} weaker</span><span>median</span><span>stronger ${sgn(l.rel, 2)}</span></div>` +
      `<div class="rl"><span>same day · ${fmt(curDate())} · 10 m edge ring left out</span></div>`;
  } else if (mode() === 'px') {
    const l = PXL[key()];
    h = `<b>${esc(l.label)}</b><div class="ramp" style="background:linear-gradient(90deg,${l.ramp.join(',')})"></div>` +
      `<div class="rl"><span>${num(l.lo, 2)} ${esc(l.low)}</span><span>${esc(l.high)} ${num(l.hi, 2)}</span></div>` +
      `<div class="rl"><span>10 m pixels · ${fmt(curDate())}</span></div>`;
  } else {
    h = `<b>${esc(ZL[key()].label)} vs its own normal</b><div class="zl">` +
      [['wb', '≤ −1.5'], ['b', '−1.5…−1'], ['n', 'normal'], ['a', '+1…+1.5'], ['wa', '≥ +1.5'], ['nd', 'no data / too small']]
        .map(([c, t]) => `<span><span class="sw" style="background:${COL[c]}"></span>${t}</span>`).join('') + '</div>';
  }
  $('legend').innerHTML = h;
}

// ---------- controls ----------
function fillLayers() {
  const og = (label, items) => `<optgroup label="${label}">` + items.map(([v, t]) => `<option value="${v}">${esc(t)}</option>`).join('') + '</optgroup>';
  let h = '';
  if (PX.dates.length) {
    h += og('Inside the parcel · 10 m pixels', PX.layers.map(l => ['px:' + l.key, l.label]));
    h += og('Zones · pixel vs the rest of the parcel, same day', PX.layers.map(l => ['rel:' + l.key, l.label + ' — vs parcel median']));
    if (ZN.show.length) h += og('Zones vs usual · this place against its last 5 years (noise-tested)',
      PX.layers.filter(l => ZN.show.includes(l.key)).map(l => ['hist:' + l.key, l.label + ' — vs usual']));
  }
  h += og('Against its own history · whole parcel', D.layer_info.map(l => ['z:' + l.key, l.label + ' — anomaly']));
  $('layer').innerHTML = h;
}
function fillDates() {
  const list = isPx() ? PX.dates.map(p => p.date) : D.dates;
  const cur = isPx() ? S.pi : S.di;
  const idx = list.map((d, i) => i);
  const order = isPx() ? idx : idx.slice().reverse();
  $('date').innerHTML = order.map(i => `<option value="${i}"${i === cur ? ' selected' : ''}>${fmt(list[i])}</option>`).join('');
}
function nearest(list, d) {
  const t = Date.parse(d); let best = 0, bd = Infinity;
  list.forEach((x, i) => { const dd = Math.abs(Date.parse(x) - t); if (dd < bd) { bd = dd; best = i; } });
  return best;
}
$('layer').addEventListener('change', e => {
  const before = curDate(); S.layer = e.target.value;
  if (isPx()) S.pi = nearest(PX.dates.map(p => p.date), before); else S.di = nearest(D.dates, before);
  render(true);
});
$('date').addEventListener('change', e => { if (isPx()) S.pi = +e.target.value; else S.di = +e.target.value; render(true); });
function step(k) {   // k = +1 newer, −1 older
  if (isPx()) S.pi = Math.min(PX.dates.length - 1, Math.max(0, S.pi - k));
  else S.di = Math.min(D.dates.length - 1, Math.max(0, S.di + k));
  render(true);
}
$('older').addEventListener('click', () => step(-1));
$('newer').addEventListener('click', () => step(1));
$('op').addEventListener('input', e => { S.op = +e.target.value / 100; if (ov) ov.setOpacity(S.op); if (map) styleParcels(); });
$('base').addEventListener('change', e => { S.base = e.target.value; if (esri) esri.setOpacity(S.base === 'esri' ? 1 : 0); });
function select(id) {
  S.site = id;
  if (map) { if (id === 'ALL') map.fitBounds(D.map.bounds, {padding: [24, 24]});
             else map.fitBounds(polys[id].getBounds(), {padding: [70, 70], maxZoom: 18}); }
  render(false);
}

// ---------- statistics under the map ----------
function stats() {
  const d = curDate(), di = dIndex[d];
  const zline = id => ['water', 'ndvi', 'ndre'].map(k => { const z = zAt(k, id, di);
    return `${esc(ZL[k].label)} ${z == null ? '—' : num(z, 1)}`; }).join(' · ');
  let h = '';
  if (S.site !== 'ALL') {
    const id = S.site;
    if (mode() === 'hist') {
      const st = ((PX.dates[S.pi].stats || {})[id] || {})[pk()], l = PXL[key()];
      const dry = key() === 'ndmi' ? 'Drier' : 'Weaker', wet = key() === 'ndmi' ? 'Wetter' : 'Stronger';
      h += `<h3>${esc(l.label)}: ${vname(id)} against its usual pattern · ${fmt(d)}</h3>`;
      h += st && st[4] ? `<div class="tiles"><div class="tile"><span>${dry} than usual</span><b>${num(st[0], 0)}%</b><small>of the parcel; confirmed ${num(st[1], 0)}%</small></div>` +
        `<div class="tile"><span>${wet} than usual</span><b>${num(st[2], 0)}%</b><small>of the parcel; confirmed ${num(st[3], 0)}%</small></div>` +
        `<div class="tile"><span>Threshold</span><b>${num(ZN.T[key()], 3)}</b><small>from the noise test (pairs of scenes without rain)</small></div>` +
        `<div class="tile"><span>Usual pattern</span><b>${st[5] ?? '—'}</b><small>scenes from ${st[6] ?? '—'} years (median per cell)</small></div></div>`
        : `<p class="small">No usual pattern for this scene (cloudy parcel or history too short).</p>`;
      h += `<p class="note">Relative to the rest of this parcel, compared with the same place in the previous five years at this time of year. "Confirmed": the same zone was also seen on another clear scene in the last 10 days. A comparison of satellite images, not a measurement of the vines; mowing or tilling part of the inter-rows looks the same.</p>`;
    } else if (mode() === 'rel') {
      const st = ((PX.dates[S.pi].stats || {})[id] || {})[pk()], l = PXL[key()];
      h += `<h3>${esc(l.label)} zones inside ${vname(id)} · ${fmt(d)}</h3>`;
      h += st ? `<div class="tiles"><div class="tile"><span>Parcel median</span><b>${num(st[0], 2)}</b><small>reference for the colours</small></div>` +
        `<div class="tile"><span>Weakest 10%</span><b>${sgn(st[1], 2)}</b><small>below the median by at least this</small></div>` +
        `<div class="tile"><span>Strongest 10%</span><b>${sgn(st[2], 2)}</b><small>above the median by at least this</small></div>` +
        `<div class="tile"><span>Pixels</span><b>${st[3]}</b><small>cloud-free, centre ≥ 10 m from the edge</small></div></div>`
        : `<p class="small">No cloud-free pixels left after removing the 10 m edge ring.</p>`;
      h += `<p class="note">Brown: weaker${key() === 'ndmi' ? ' or drier' : ''} than the rest of this parcel on the same day; green${key() === 'ndmi' ? '/blue: wetter' : ': stronger'}. A zone that keeps the same colour on several dates is more likely to be real.</p>`;
    } else if (mode() === 'px') {
      const st = ((PX.dates[S.pi].stats || {})[id] || {})[key()], l = PXL[key()];
      h += `<h3>${esc(l.label)} inside ${vname(id)} · ${fmt(d)}</h3>`;
      h += st ? `<div class="tiles"><div class="tile"><span>Mean</span><b>${num(st[0], 2)}</b><small>pixels ≥ ${D.inner_m} m from the edge</small></div>` +
        `<div class="tile"><span>Weakest 10%</span><b>${num(st[1], 2)}</b><small>10th percentile</small></div>` +
        `<div class="tile"><span>Strongest 10%</span><b>${num(st[2], 2)}</b><small>90th percentile</small></div>` +
        `<div class="tile"><span>Spread</span><b>${num(st[2] - st[1], 2)}</b><small>how uneven the parcel is</small></div>` +
        `<div class="tile"><span>Pixels</span><b>${st[3]}</b><small>10 m, cloud-free</small></div></div>`
        : `<p class="small">No cloud-free pixels left after removing the ${D.inner_m} m edge strip.</p>`;
      h += `<p class="note">Same day against its own history (z): ${di == null ? 'not in the anomaly series' : zline(id)}.</p>`;
    } else {
      h += `<h3>${vname(id)} against its own history · ${fmt(d)}</h3><div class="tiles">` +
        D.layer_info.map(l => { const z = zAt(l.key, id, S.di), c = qc(id) ? cls(z) : 'nd';
          return `<div class="tile" style="border-left:5px solid ${COL[c]}"><span>${esc(l.label)}</span><b>${num(z, 1)}</b><small>${qc(id) ? CLS_TXT[c] : 'parcel too small'}</small></div>`; }).join('') + '</div>';
      const others = D.map.shapes.map(s => s.id).filter(s => s !== id && qc(s));
      const m = median(others.map(s => zAt(key(), s, S.di)));
      h += `<p class="note">Other vineyards that day (median, ${esc(ZL[key()].label)}): ${m == null ? '—' : num(m, 1)}.</p>`;
    }
  } else {
    const rows = D.map.shapes.map(s => {
      const z = zAt('water', s.id, di), st = isPx() ? ((PX.dates[S.pi].stats || {})[s.id] || {})[pk()] : null;
      const zk = mode() === 'z' ? zAt(key(), s.id, S.di) : null;
      return `<tr class="pick" data-site="${s.id}"><td>${vname(s.id)}</td><td class="num">${s.area_ha.toFixed(2)}</td>` +
        (mode() === 'hist' ? `<td class="num">${st && st[4] ? num(st[0], 0) + '% (' + num(st[1], 0) + '%)' : '—'}</td><td class="num">${st && st[4] ? num(st[2], 0) + '% (' + num(st[3], 0) + '%)' : '—'}</td>`
         : mode() === 'rel' ? `<td class="num">${st ? num(st[0], 2) : '—'}</td><td class="num">${st ? sgn(st[1], 2) + ' / ' + sgn(st[2], 2) : '—'}</td>`
         : mode() === 'px' ? `<td class="num">${st ? num(st[0], 2) : '—'}</td><td class="num">${st ? num(st[1], 2) + ' – ' + num(st[2], 2) : '—'}</td>`
                         : `<td class="num">${num(zk, 1)}</td><td>${qc(s.id) ? CLS_TXT[cls(zk)] : 'too small'}</td>`) +
        `<td class="num" style="color:${qc(s.id) && z != null && z <= -1 ? 'var(--wb)' : 'inherit'}">${qc(s.id) ? num(z, 1) : '—'}</td></tr>`;
    }).join('');
    const below = D.map.shapes.filter(s => qc(s.id) && (zAt('water', s.id, di) ?? 0) <= -1).length;
    const n = D.map.shapes.filter(s => qc(s.id) && zAt('water', s.id, di) != null).length;
    h += `<h3>All vineyards · ${fmt(d)}</h3>`;
    h += `<div class="tiles"><div class="tile"><span>Below own normal</span><b>${n ? below + ' / ' + n : '—'}</b><small>vegetation water (SWIR), z ≤ −1</small></div>` +
      `<div class="tile"><span>Vineyards</span><b>${D.map.shapes.length}</b><small>${Object.values(D.sites).filter(s => s.qc_ok).length} large enough for an anomaly</small></div>` +
      `<div class="tile"><span>Area</span><b>${D.map.shapes.reduce((a, s) => a + s.area_ha, 0).toFixed(1)}</b><small>hectares</small></div></div>`;
    h += `<div class="tbl"><table><thead><tr><th>Vineyard</th><th>ha</th>` +
      (mode() === 'hist' ? `<th>${key() === 'ndmi' ? 'drier' : 'weaker'} than usual (confirmed)</th><th>${key() === 'ndmi' ? 'wetter' : 'stronger'} than usual (confirmed)</th>`
       : mode() === 'rel' ? `<th>${esc(PXL[key()].label)} median</th><th>weakest / strongest 10% vs median</th>`
       : mode() === 'px' ? `<th>${esc(PXL[key()].label)} mean</th><th>10–90%</th>` : `<th>z ${esc(ZL[key()].label)}</th><th>class</th>`) +
      `<th>z water</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  }
  $('stats').innerHTML = h;
  $('stats').querySelectorAll('tr.pick').forEach(r => r.addEventListener('click', () => select(r.dataset.site)));
}

// ---------- right column ----------
function alertBox() {
  let c, title, chip, big, txt;
  if (S.site === 'ALL') {
    const d = D.last_scene, di = dIndex[d];
    const ids = D.map.shapes.map(s => s.id).filter(qc);
    const zs = ids.map(id => zAt('water', id, di)).filter(v => v != null);
    const below = zs.filter(z => z <= -1).length;
    c = below > zs.length / 2 ? 'b' : 'n'; chip = fmt(d); big = `${below} of ${zs.length}`;
    title = 'vineyards below their own normal'; txt = 'Vegetation water (SWIR), latest scene';
  } else {
    const st = stateOf(S.site); c = st.c; chip = st.date ? fmt(st.date) : '—';
    big = st.z == null ? '—' : 'z ' + num(st.z, 1); title = st.txt; txt = `${vname(S.site)} · vegetation water (SWIR) against its own history`;
  }
  const col = c === 'n' ? '#3a7d44' : c === 'nd' ? '#7b8579' : COL[c];
  $('alert').style.borderColor = col;
  $('alert').innerHTML = `<svg class="ic" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3 2 21h20L12 3z" fill="none" stroke="${col}" stroke-width="2" stroke-linejoin="round"/><path d="M12 10v5M12 17.5v.5" stroke="${col}" stroke-width="2" stroke-linecap="round"/></svg>` +
    `<span class="chip" style="background:${col}1f;color:${col}">${chip}</span><p>${esc(txt)}</p><div class="big" style="color:${col}">${big}</div><p><b>${esc(title)}</b></p>`;
}
function gauge() {
  const s = D.soil_now;
  if (!s) { $('gauge').innerHTML = '<h3>Soil dryness · area</h3><p class="small">No ERA5-Land soil data.</p>'; return; }
  const cx = 110, cy = 100, r = 80, zones = [[0, .7, '#3a9d4f'], [.7, .8, '#e0b400'], [.8, .9, '#f08a24'], [.9, 1, '#d63a2f']];
  const pt = (f, rr) => [cx + rr * Math.cos(Math.PI * (1 - f)), cy - rr * Math.sin(Math.PI * (1 - f))];
  let svg = zones.map(([a, b, col]) => { const [x0, y0] = pt(a, r), [x1, y1] = pt(b, r);
    return `<path d="M${x0.toFixed(1)},${y0.toFixed(1)} A${r},${r} 0 0 1 ${x1.toFixed(1)},${y1.toFixed(1)}" stroke="${col}" stroke-width="16" fill="none"/>`; }).join('');
  const f = Math.max(0, Math.min(1, 1 - s.pct / 100)), [nx, ny] = pt(f, r - 20);
  svg += `<line x1="${cx}" y1="${cy}" x2="${nx.toFixed(1)}" y2="${ny.toFixed(1)}" stroke="#1f2a22" stroke-width="4" stroke-linecap="round"/><circle cx="${cx}" cy="${cy}" r="6" fill="#1f2a22"/>` +
    `<text x="22" y="116">wet</text><text x="176" y="116">dry</text>`;
  const lab = s.label.charAt(0).toUpperCase() + s.label.slice(1);
  $('gauge').innerHTML = `<h3>Soil dryness · area</h3><svg viewBox="0 0 220 122" width="100%" style="max-width:260px" role="img" aria-label="Soil dryness gauge">${svg}</svg>` +
    `<div class="lab">${esc(lab)}${s.code && s.code.startsWith('D') ? ' (' + s.code + ')' : ''}</div>` +
    `<p class="small">Soil 0–100 cm, ERA5-Land (~9 km): percentile ${s.pct} vs ${s.clim_ref} · ${fmt(s.date)}. Checked against soil sensors at 3 stations (R about 0.6). Drought classes after the US Drought Monitor.</p>`;
}
function weather() {
  const W = D.weather || {}, F = W.forecast || [], t = W.fc_thr || {frost: 0, heat: 35};
  const day = d => fmt(d, {weekday: 'short', day: 'numeric', month: 'short', year: undefined});
  let h = '';
  if (F.length) {
    const f0 = F[0];
    h += `<div class="today"><div class="t0">${esc(day(f0.date))}</div><div class="tmax">${num(f0.tmax, 0)} °C</div>` +
      `<div><b>${num(f0.tmin, 0)} °C</b><small>min</small></div><div><b>${num(f0.rain, 1)} mm</b><small>rain</small></div>` +
      `<div><b>${num(f0.et0, 1)} mm</b><small>ET0</small></div></div><div class="days">` +
      F.slice(1).map(f => `<div><b>${esc(fmt(f.date, {weekday: 'short', day: undefined, month: undefined, year: undefined}))} ${new Date(f.date).getUTCDate()}</b>` +
        `<span class="r">${num(f.rain, 1)} mm${f.tmin != null && f.tmin <= t.frost ? '<span class="flag frost">frost</span>' : ''}${f.tmax != null && f.tmax >= t.heat ? '<span class="flag">heat</span>' : ''}</span>` +
        `<span class="t">${num(f.tmax, 0)}° / ${num(f.tmin, 0)}°</span></div>`).join('') + '</div>' +
      `<div class="in small">7-day forecast, Open-Meteo, issued ${fmt(F[0].date)}. Frost: Tmin ≤ ${t.frost} °C; heat: Tmax ≥ ${t.heat} °C (nominal thresholds, forecast not validated).</div>`;
  } else {
    h += '<div class="in small">Forecast not available (no connection to Open-Meteo when the panel was built).</div>';
  }
  h += '<div class="in">';
  const L10 = W.last10 || [];
  if (L10.length) {
    const sum = L10.reduce((a, r) => a + (r.rain || 0), 0), mx = Math.max(...L10.map(r => r.rain || 0), 5);
    const bars = L10.map((r, i) => `<rect x="${i * 26 + 2}" y="${50 - (r.rain || 0) / mx * 44}" width="20" height="${(r.rain || 0) / mx * 44}" fill="var(--rain)"><title>${fmt(r.date)}: ${num(r.rain, 1)} mm</title></rect>`).join('');
    h += `<h3>Last 10 days · ERA5-Land</h3><svg viewBox="0 0 262 54" width="100%" style="max-width:300px" role="img" aria-label="Daily rain, last 10 days">${bars}<line x1="0" x2="262" y1="50.5" y2="50.5" stroke="var(--line)"/></svg>` +
      `<div class="kv"><span>Rain ${fmt(L10[0].date, {year: undefined})} – ${fmt(L10[L10.length - 1].date, {year: undefined})}</span><b>${num(sum, 1)} mm</b>` +
      `<span>Warmest day</span><b>${num(Math.max(...L10.map(r => r.tmax ?? -99)), 1)} °C</b><span>Coldest night</span><b>${num(Math.min(...L10.map(r => r.tmin ?? 99)), 1)} °C</b></div>`;
  }
  const dr = W.drivers || {};
  if (dr.rain30 || dr.rain90) {
    h += `<h3 style="margin-top:12px">Rain against 1991–2020</h3><div class="kv">` +
      (dr.rain30 ? `<span>30 days to ${fmt(dr.rain30[0], {year: undefined})}</span><b>${num(dr.rain30[1], 0)} mm · SPI ${dr.spi1 ? num(dr.spi1[1], 1) : '—'}</b>` : '') +
      (dr.rain90 ? `<span>90 days</span><b>${num(dr.rain90[1], 0)} mm · SPI ${dr.spi3 ? num(dr.spi3[1], 1) : '—'}</b>` : '') +
      (dr.top_pct ? `<span>Topsoil 0–7 cm</span><b>percentile ${num(dr.top_pct[1], 0)}</b>` : '') + '</div>' +
      `<p class="small">SPI below −1: drier than usual; below −2: extremely dry. Rain checked against the Météo-France gauge at Condom.</p>`;
  }
  const se = W.season;
  if (se) {
    const th = W.thr || {};
    h += `<h3 style="margin-top:12px">Season ${se.year}</h3><div class="kv">` +
      `<span>Spring frost days (Tmin ≤ ${num(th.frost, 1)} °C)</span><b>${se.frost_days}${se.last_frost ? ' · last ' + fmt(se.last_frost, {year: undefined}) : ''}</b>` +
      `<span>Heat days (Tmax ≥ ${num(th.heat, 1)} °C)</span><b>${se.heat_days}</b>` +
      (se.max_tmax != null ? `<span>Hottest day</span><b>${num(se.max_tmax, 1)} °C</b>` : '') + '</div>';
  }
  $('wx').innerHTML = h + '</div>';
}
function info() {
  let f;
  const fld = (k, v, w) => `<div class="field${w ? ' w2' : ''}"><span>${k}</span>${v}</div>`;
  if (S.site === 'ALL') {
    const pd = PX.dates.map(p => p.date);
    f = fld('Crop', 'Grapevine') + fld('Vineyards', `${D.map.shapes.length} (${Object.values(D.sites).filter(s => s.qc_ok).length} with anomaly)`) +
      fld('Region', esc(D.region), true) +
      fld('Scene days', `${D.dates.length} · ${fmt(D.dates[0], {day: undefined})} – ${fmt(D.dates[D.dates.length - 1])}`, true) +
      fld('Pixel maps', pd.length ? `${pd.length} cloud-free scenes · ${fmt(pd[pd.length - 1], {year: undefined})} – ${fmt(pd[0])}` : 'none', true);
  } else {
    const s = SH[S.site], site = D.sites[S.site] || {};
    f = fld('Crop', 'Grapevine') + fld('Area', s.area_ha.toFixed(2) + ' ha') + fld('Region', esc(D.region), true) +
      fld('Irrigation', 'unknown') + fld('Quality check', qc(S.site) ? 'passed' : 'too small') +
      fld('Pixels used', `${site.n_pixels ?? '—'} (10 m, ≥ ${D.inner_m} m from edge; min ${D.min_px})`, true) +
      fld('Normal', 'same parcel, previous 5 years, same orbit', true);
  }
  $('info').innerHTML = `<h3>${S.site === 'ALL' ? 'Area information' : 'Plot information'}</h3><div class="fields">${f}</div>`;
}

// ---------- season, card, trust ----------
function chart(el, pts, med, year, opt) {
  const W = 720, H = opt.h, L = 38, R = 10, T = 10, B = 22;
  const t0 = Date.UTC(year, 3, 1), t1 = Date.UTC(year, 9, 31);
  const X = d => L + (Date.parse(d + 'T00:00:00Z') - t0) / (t1 - t0) * (W - L - R);
  const Y = v => T + (opt.max - Math.max(opt.min, Math.min(opt.max, v))) / (opt.max - opt.min) * (H - T - B);
  let s = `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="${opt.label}">`;
  (opt.bands || []).forEach(b => s += `<rect x="${L}" width="${W - L - R}" y="${Y(b[1])}" height="${Y(b[0]) - Y(b[1])}" fill="${b[2]}" opacity="0.18"/>`);
  opt.ticks.forEach(v => s += `<line x1="${L}" x2="${W - R}" y1="${Y(v)}" y2="${Y(v)}" stroke="var(--line)" ${v === 0 ? '' : 'stroke-dasharray="3 3"'}/><text x="${L - 6}" y="${Y(v) + 4}" text-anchor="end">${v}</text>`);
  ['Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct'].forEach((m, i) => { const d = `${year}-${String(i + 4).padStart(2, '0')}-01`;
    s += `<text x="${X(d)}" y="${H - 6}">${m}</text>`; });
  if (opt.marker) s += `<line x1="${X(opt.marker)}" x2="${X(opt.marker)}" y1="${T}" y2="${H - B}" stroke="#4b7023" stroke-width="1.5"/>`;
  if (med && med.length) s += `<polyline fill="none" stroke="var(--muted)" stroke-width="1.5" points="${med.map(p => `${X(p.d).toFixed(1)},${Y(p.v).toFixed(1)}`).join(' ')}"/>`;
  if (opt.line) s += `<polyline fill="none" stroke="${opt.line}" stroke-width="2" points="${pts.map(p => `${X(p.d).toFixed(1)},${Y(p.v).toFixed(1)}`).join(' ')}"/>`;
  else pts.forEach(p => s += `<circle cx="${X(p.d).toFixed(1)}" cy="${Y(p.v).toFixed(1)}" r="4" fill="${COL[cls(p.v)]}" stroke="#1f2a22" stroke-width=".6"><title>${fmt(p.d)}: z ${p.v.toFixed(1)}</title></circle>`);
  el.innerHTML = s + '</svg>';
}
function season() {
  const day = curDate(), year = +day.slice(0, 4);
  const k = D.layers[key()] ? key() : 'water', lab = ZL[k].label;
  const yi = D.dates.map((d, i) => [d, i]).filter(([d]) => +d.slice(0, 4) === year);
  const ids = D.map.shapes.map(s => s.id).filter(qc);
  let pts, med = null, title;
  if (S.site === 'ALL') {
    pts = yi.map(([d, i]) => ({d, v: median(ids.map(s => zAt(k, s, i)))})).filter(p => p.v != null);
    title = `${year} season · ${lab}: median of the ${ids.length} vineyards (dots coloured by class)`;
  } else {
    pts = yi.map(([d, i]) => ({d, v: zAt(k, S.site, i)})).filter(p => p.v != null);
    med = yi.map(([d, i]) => ({d, v: median(ids.filter(s => s !== S.site).map(s => zAt(k, s, i)))})).filter(p => p.v != null);
    title = `${year} season · ${lab}: ${vname(S.site)} (dots) and the median of the other vineyards (grey line)`;
  }
  $('stitle').textContent = title;
  chart($('seasonc'), pts, med, year, {h: 230, min: -3, max: 3, ticks: [-2, -1, 0, 1, 2], marker: day, label: 'season chart',
    bands: [[-3, -1, 'var(--b)'], [1, 3, 'var(--a)']]});
  const sp = D.soil.dates.map((d, i) => ({d, v: D.soil.pct[i]}))
    .filter(p => +p.d.slice(0, 4) === year && +p.d.slice(5, 7) >= 4 && +p.d.slice(5, 7) <= 10);
  $('soiltitle').textContent = `${year} · soil moisture 0–100 cm in the area (ERA5-Land percentile vs 1991–2020; ≤ 30 dry, ≥ 70 wet)`;
  chart($('soil'), sp, null, year, {h: 150, min: 0, max: 100, ticks: [0, 30, 70, 100], marker: day, line: 'var(--soil)',
    label: 'soil moisture chart', bands: [[0, 30, 'var(--b)'], [70, 100, 'var(--a)']]});
}
function cardText() {
  if (S.site === 'ALL') {
    $('cname').textContent = 'What the panel says';
    $('csent').innerHTML = `<li>${esc(D.region)}: ${D.map.shapes.length} vineyards, each compared with itself in the previous five years at the same time of year.</li>` +
      `<li>Pick a vineyard in the list or on the map to read its card.</li>`;
    $('cnotes').hidden = true; $('cfixed').textContent = ''; $('cdetail').textContent = ''; return;
  }
  const C = D.cards[S.site] || {sentences: [], notes: [], fixed: [], detail: ''};
  $('cname').textContent = `${vname(S.site)} · latest scene ${C.date ? fmt(C.date) : '—'}`;
  $('csent').innerHTML = C.sentences.map(t => `<li>${esc(t)}</li>`).join('');
  $('cnotes').innerHTML = C.notes.map(t => `<li>${esc(t)}</li>`).join(''); $('cnotes').hidden = !C.notes.length;
  $('cfixed').textContent = C.fixed.join(' ');
  $('cdetail').textContent = C.detail || '';
}

function render(mapOnly) {
  const m = mode();
  $('layer').value = S.layer;
  fillDates();
  $('older').disabled = isPx() ? S.pi >= PX.dates.length - 1 : S.di <= 0;
  $('newer').disabled = isPx() ? S.pi <= 0 : S.di >= D.dates.length - 1;
  $('pxnote').hidden = m !== 'px';
  $('relnote').hidden = m !== 'rel';
  $('histnote').hidden = m !== 'hist';
  $('znote').hidden = m !== 'z';
  $('mtitle').innerHTML = S.site === 'ALL' ? `All vineyards <span class="ha">${esc(D.region)}</span>`
    : `${vname(S.site)} <span class="ha">${SH[S.site].area_ha.toFixed(2)} ha</span>`;
  drawMap(); legend(); stats(); season();
  if (!mapOnly) { side(); alertBox(); info(); cardText(); }
  try { localStorage.setItem('agriscreen-v2', JSON.stringify({layer: S.layer, site: S.site})); } catch (e) {}
}
fillLayers();
if (PX.rgb) $('base').options[1].textContent = `Sentinel-2 natural colour, ${fmt(PX.rgb.date)}`; else $('base').options[1].disabled = true;
gauge(); weather();
$('trust').innerHTML = D.trust.map(r => `<tr><td>${esc(r.what)}</td><td>${esc(r.against)}</td><td>${esc(r.result)}</td><td class="st-${r.status.replace(/ /g, '-')}">${esc(r.status)}</td></tr>`).join('');
if (S.site !== 'ALL' && map) map.fitBounds(polys[S.site].getBounds(), {padding: [70, 70], maxZoom: 18});
render(false);
"""

_LEAF = ('<svg width="26" height="26" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 20c0-9 6-15 16-16-1 10-7 16-16 '
         '16z" fill="#fff" opacity=".95"/><path d="M4 20 14 10" stroke="#6f9b3a" stroke-width="1.6"/></svg>')


def _leaflet_css() -> str:
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "leaflet-1.9.4.css")
    return open(p, encoding="utf-8").read() if os.path.exists(p) else ""


def panel_html(data: Dict[str, Any], standalone: bool = True) -> str:
    """Strona panelu. standalone=True: pełny dokument (Colab, blog); False: bez szkieletu (podgląd Artifact).
    Leaflet 1.9.4: skrypt z unpkg, arkusz stylów wbudowany (assets/), bo część przeglądarek treści blokuje CSS z CDN."""
    esc = html.escape
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"), default=str).replace("</", "<\\/")
    body = f"""<title>AgriScreen Vineyard Panel</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Figtree:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>{_leaflet_css()}
{_CSS}</style>
<header class="top"><div class="logo">{_LEAF}AgriScreen <small>· vineyards against their own history</small></div>
<div class="meta">{esc(data.get('region', ''))} · last scene {esc(fmt_date(data['last_scene']))} · tests frozen {esc(data['freeze'])}</div>
</header>
<nav class="tabs" aria-label="Sections"><a href="#map">Overview</a><a href="#season">Season</a><a href="#weather">Weather</a><a href="#trust-sec">Trust</a></nav>
<div class="app">
<aside class="box side" aria-label="Vineyards"><h2>Vineyards</h2><div class="vlist" id="vlist"></div>
<p class="small">Dot colour: vegetation water at the latest scene against the vineyard's own normal. Grey: parcel too small
or no clear scene.</p></aside>
<div class="col">
<section class="box" id="map" aria-labelledby="mtitle">
<div class="mhead"><h2 id="mtitle"></h2></div>
<div class="ctrl" role="group" aria-label="Map controls">
<label>Layer <select id="layer"></select></label>
<label>Date <span class="datebox"><button class="step" id="older" type="button" aria-label="Older scene">◀</button><select id="date"></select><button class="step" id="newer" type="button" aria-label="Newer scene">▶</button></span></label>
<label>Opacity <input id="op" type="range" min="20" max="100" value="80"></label>
<label>Background <select id="base"><option value="esri">Satellite photo (Esri)</option><option value="s2">Sentinel-2 natural colour</option></select></label>
</div>
<div id="lmap"><div class="legend-box" id="legend"></div></div>
<p class="note" id="pxnote">Pixel maps show where the parcel is greener, weaker, wetter or drier on that day. They describe the
parcel; they are not compared with a normal and are not validated. Inter-rows and soil count too.</p>
<p class="note" id="relnote">Zones: each pixel minus the median of the same parcel on the same day. This shows weaker and
stronger parts of the parcel without comparing years, so small shifts of the satellite image between years do not matter.
Pixels within 10 m of the edge are left out (they mix with roads and neighbouring fields). Descriptive, not validated.</p>
<p class="note" id="histnote">Zones vs usual: is this place weaker or stronger, relative to the rest of the parcel, than it
usually is at this time of year? Coloured only when the change is larger than the satellite noise measured on pairs of
scenes a few days apart without rain, and only zones of at least 4 cells. This layer is shown because it passed the
pre-registered noise test; it is not validated in the field.</p>
<p class="note" id="znote">Whole-parcel value against the same parcel in the previous five years (same time of year, same
orbit), as a z-score: −1 means clearly below its own normal.</p>
<div id="stats"></div>
</section>
</div>
<div class="col right">
<section class="box alert" id="alert" aria-live="polite"></section>
<section class="box gauge" id="gauge"></section>
<section class="box wx" id="weather" aria-label="Weather"><div id="wx"></div></section>
<section class="box" id="info"></section>
</div>
<div class="wide">
<section class="box card" aria-labelledby="cname"><h2 id="cname"></h2><ol id="csent"></ol><ul class="notes" id="cnotes"></ul>
<p class="small" id="cfixed"></p><p class="small" id="cdetail"></p></section>
<section class="box" id="season" aria-labelledby="sh"><h2 id="sh">Season</h2><p class="small" id="stitle"></p><div id="seasonc"></div>
<p class="small" id="soiltitle"></p><div id="soil"></div></section>
<section class="box" id="trust-sec" aria-labelledby="trusth"><h2 id="trusth">How far to trust it</h2>
<div class="tbl"><table><thead><tr><th>What</th><th>Checked against</th><th>Result</th><th>Status</th></tr></thead>
<tbody id="trust"></tbody></table></div></section>
</div>
<footer>Data: Copernicus Sentinel-2 L2A, ERA5-Land and CLMS Soil Water Index; reference sensors ISMN (SMOSMANIA Condom)
and ICOS (Auradé, Lusignan); rain gauges Météo-France; forecast Open-Meteo; background imagery Esri World Imagery.
The vegetation index sees the whole parcel (vines, inter-rows and soil), so it is not a diagnosis of vine water stress
and gives no irrigation advice. Tests registered before computing (protocol {esc(data['protocol'])}…). Method and code:
<a href="https://github.com/geoworldlook/agriscreen" rel="noopener">github.com/geoworldlook/agriscreen</a>. Generated
{esc(data['generated'])}.</footer>
</div>
<script type="application/json" id="panel-data">{payload}</script>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>{_JS}</script>"""
    if not standalone:
        return body
    return (f'<!doctype html>\n<html lang="en"><head><meta charset="utf-8">\n<meta name="viewport" '
            f'content="width=device-width, initial-scale=1, viewport-fit=cover">\n</head><body>\n{body}\n</body></html>')


def fmt_date(d: str) -> str:
    return pd.Timestamp(d).strftime("%-d %B %Y") if d else ""


def build_panel(out_dir: str, cfg: Dict[str, Any], path: Optional[str] = None, standalone: bool = True,
                forecast: Any = "fetch") -> str:
    """Zapisuje panel (panel.html w OUTPUT_DIR) i dane (panel_data.json) — te same dane czyta notatnik na blog.
    forecast: "fetch" (Open-Meteo), None (bez prognozy) albo gotowa tabela (date, tmax, tmin, precip_mm, et0_mm)."""
    data = panel_data(out_dir, cfg, forecast)
    path = path or os.path.join(out_dir, "panel.html")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(panel_html(data, standalone))
    with open(os.path.join(os.path.dirname(path), "panel_data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"), default=str)
    n_px = len((data.get("pixels") or {}).get("dates", []))
    logger.info(f"Panel: {path} ({os.path.getsize(path) // 1024} kB, map pikseli: {n_px}, prognoza: "
                f"{'tak' if (data.get('weather') or {}).get('forecast') else 'nie'})")
    return path
