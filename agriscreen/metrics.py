"""
Wskaźniki i anomalie.

- NDVI, NDMI, NDRE, CRSWIR z rastrów Sentinel-2; statystyki działek z pasem wewnętrznym.
- Tor orbity z godziny akwizycji; anomalia sceny wobec lat wcześniejszych (ten sam tor, z predykcyjne).
- Anomalie klimatologiczne ERA5-Land (percentyl, z wobec 1991–2020), warstwa 0–100 cm, SPI.
"""

from __future__ import annotations
import os
import re
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

S2_BANDS = ["B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B11", "B12"]


RASTER_CLOUD_BAND = 10          # indeks pasma 'cloudmask' w plikach z ingest (1 = chmura/cień)


INDICES = ("ndvi", "ndmi", "ndre", "crswir")


# CRSWIR: waga kontinuum dla B11 między B8A a B12. Stała potoku (przybliżone środki pasm [nm]) zostaje w produktach
# S2_10m i S2SR_2.5m, żeby ich historia nie mieszała dwóch stałych; produkt działek W3b (S2_10m_buf20) używa stałej
# z kodu FORDEAD (INRAE): środki pasm 864 / 1610,4 / 2185,7 nm (protokół W3b §3).
CRSWIR_W = (1610.0 - 865.0) / (2190.0 - 865.0)


CRSWIR_W_FORDEAD = (1610.4 - 864.0) / (2185.7 - 864.0)


def compute_indices(arr: np.ndarray, crswir_w: float = CRSWIR_W) -> Dict[str, np.ndarray]:
    """
    NDVI = (B08-B04)/(B08+B04)        — wigor / pokrycie roślinnością,
    NDMI = (B8A-B11)/(B8A+B11)        — woda w roślinności (SWIR + NIR, Ceccato i in. 2001); u Laroche-Pinel i in. 2021
                                         sam NDII (B8/B11) R² 0,09; w modelu wielopasmowym wystarczają B4, B6, B8A, B12,
    NDRE = (B8A-B05)/(B8A+B05)        — red-edge (chlorofil),
    CRSWIR = B11 / (B8A + (B12-B8A)·w) — głębokość absorpcji wody przy 1610 nm względem kontinuum B8A–B12
                                         (FORDEAD, INRAE); wyższa wartość = mniej wody. Przegląd: F3 §7, W3b (literatura).
    """
    b = {name: arr[i] for i, name in enumerate(S2_BANDS)}
    with np.errstate(all="ignore"):
        return {
            "ndvi": (b["B08"] - b["B04"]) / (b["B08"] + b["B04"]),
            "ndmi": (b["B8A"] - b["B11"]) / (b["B8A"] + b["B11"]),
            "ndre": (b["B8A"] - b["B05"]) / (b["B8A"] + b["B05"]),
            "crswir": b["B11"] / (b["B8A"] + (b["B12"] - b["B8A"]) * crswir_w),
        }


def scene_time(path: str) -> pd.Timestamp:
    """Czas akwizycji z nazwy pliku ingest: S2_L2A_YYYYMMDD_HHMMSS.tif."""
    m = re.search(r"S2_L2A_(\d{8})_(\d{6})", os.path.basename(path))
    if not m:
        raise ValueError(f"Nierozpoznana nazwa sceny: {path}")
    return pd.to_datetime(m.group(1) + m.group(2), format="%Y%m%d%H%M%S")


def site_stats(arr: np.ndarray, cloud: np.ndarray, profile: Dict[str, Any], sites, product: str,
               t: pd.Timestamp, inner_m: Optional[float] = None, bands: Tuple[str, ...] = (),
               crswir_w: float = CRSWIR_W, all_touched_fallback: bool = True) -> List[Dict[str, Any]]:
    """
    Średnie indeksów w obiektach (tylko piksele bezchmurne) + udział pikseli czystych i ich liczba.
    Winnice: bez pasa brzegowego o szerokości 1 piksela tej rozdzielczości (Sozzi i in. 2020:
    usunięcie pikseli brzegowych poprawia zgodność z UAV; dla działek < 0,5 ha bywa odwrotnie).
    Działki W3b (protokół §1): inner_m = 20 (pas 20 m, bo piksel 20 m zapisany na siatce 10 m wystaje przy pasie
    10 m do ok. 11 m poza działkę), bands = średnie odbicie pasm (np. B04, B06, B8A, B12), bez awaryjnego all_touched;
    obiekt bez pikseli dostaje rekord z n_pixels = 0 (żeby nie był liczony ponownie przy każdym uruchomieniu).
    """
    from rasterio.features import geometry_mask

    res = abs(profile["transform"].a)
    shape = arr.shape[1:]
    idx = compute_indices(arr, crswir_w)
    clear = (cloud == 0) & np.isfinite(arr).all(axis=0)
    out = []
    for s in sites.itertuples():
        geom = s.geometry.buffer(-(inner_m if inner_m is not None else res)) if s.inner_buffer else s.geometry
        mask = (np.zeros(shape, bool) if geom.is_empty else
                geometry_mask([geom], out_shape=shape, transform=profile["transform"], invert=True))
        method = "centre"
        if mask.sum() == 0 and all_touched_fallback and not geom.is_empty:
            mask = geometry_mask([geom], out_shape=shape, transform=profile["transform"], invert=True, all_touched=True)
            method = "all_touched"
        n = int(mask.sum())
        if n == 0 and all_touched_fallback:
            continue
        ok = mask & clear
        rec = {"site_id": s.site_id, "product": product, "time": t, "n_pixels": n,
               "clear_frac": float(ok.sum() / n) if n else 0.0, "px_method": method}
        for k, v in idx.items():
            rec[k] = float(np.nanmean(v[ok])) if ok.any() else np.nan
        for b in bands:
            rec[b.lower()] = float(np.nanmean(arr[S2_BANDS.index(b)][ok])) if ok.any() else np.nan
        out.append(rec)
    return out


def load_parcels(cfg: Dict[str, Any], crs: Any):
    """Działki W3b: wszystkie obiekty `Typ == PARCEL_TYPE` z pliku działek; site_id = VINEYARD_{fid:02d}
    (VINEYARD_06 zachowuje id), pas wewnętrzny jak winnice potoku (szerokość podaje site_stats(inner_m=...))."""
    import geopandas as gpd

    p = gpd.read_file(cfg["PARCELS_PATH"]).to_crs(crs)
    p = p[p["Typ"] == cfg["PARCEL_TYPE"]].sort_values("fid")
    return gpd.GeoDataFrame({"site_id": [f"VINEYARD_{int(f):02d}" for f in p["fid"]],
                             "fid": p["fid"].astype(int).to_numpy(), "site_type": "vineyard", "inner_buffer": True,
                             "area_ha": (p.geometry.area / 1e4).round(3).to_numpy()},
                            geometry=p.geometry.to_numpy(), crs=p.crs)


def _circ_doy_dist(a: np.ndarray, b: int) -> np.ndarray:
    d = np.abs(a - b)
    return np.minimum(d, 366 - d)


def clim_anomaly(s: pd.Series, ref: Tuple[str, str], half_window: int = 15, min_n: int = 30) -> pd.DataFrame:
    """
    Anomalia standaryzowana względem klimatologii dnia roku (okno ±half_window dni, lata referencyjne),
    jak SMA w EDO (odchylenie od średniej wieloletniej / odchylenie standardowe dla tej pory roku).
    Zwraca: value, clim_mean, clim_std, z, percentile (empiryczny, 0-100), n_ref.
    """
    s = s.dropna().sort_index()
    r = s.loc[ref[0]:ref[1]]
    rd, rv = r.index.dayofyear.to_numpy(), r.to_numpy(float)
    doy = s.index.dayofyear.to_numpy()
    out = pd.DataFrame(index=s.index, data={"value": s.to_numpy(float)})
    for c in ("clim_mean", "clim_std", "percentile", "n_ref"):
        out[c] = np.nan
    for d in np.unique(doy):
        pool = np.sort(rv[_circ_doy_dist(rd, d) <= half_window])
        if len(pool) < min_n:
            continue
        sel = doy == d
        v = out["value"].to_numpy()[sel]
        out.loc[sel, "clim_mean"] = pool.mean()
        out.loc[sel, "clim_std"] = pool.std(ddof=1)
        out.loc[sel, "percentile"] = 100.0 * np.searchsorted(pool, v, side="right") / len(pool)
        out.loc[sel, "n_ref"] = len(pool)
    out["z"] = (out["value"] - out["clim_mean"]) / out["clim_std"]
    return out


def spi(precip: pd.Series, days: int, ref: Tuple[str, str], half_window: int = 15) -> pd.DataFrame:
    """
    SPI (McKee i in. 1993) z sum kroczących `days` dni: rozkład gamma dopasowany dla pory roku
    (okno ±half_window dni w latach referencyjnych), z uwzględnieniem prawdopodobieństwa zera.
    """
    from scipy import stats

    p = precip.sort_index().asfreq("D")
    acc = p.rolling(days, min_periods=int(0.9 * days)).sum().dropna()
    r = acc.loc[ref[0]:ref[1]]
    rd, rv = r.index.dayofyear.to_numpy(), r.to_numpy(float)
    doy = acc.index.dayofyear.to_numpy()
    z = np.full(len(acc), np.nan)
    for d in np.unique(doy):
        pool = rv[_circ_doy_dist(rd, d) <= half_window]
        if len(pool) < 30:
            continue
        q0 = np.mean(pool <= 0.01)
        pos = pool[pool > 0.01]
        if len(pos) < 20:
            continue
        a, loc, scale = stats.gamma.fit(pos, floc=0)
        sel = doy == d
        x = acc.to_numpy()[sel]
        prob = q0 + (1 - q0) * stats.gamma.cdf(np.maximum(x, 0), a, loc=0, scale=scale)
        prob = np.where(x <= 0.01, q0 / 2 if q0 > 0 else 1e-6, prob)
        z[sel] = stats.norm.ppf(np.clip(prob, 1e-6, 1 - 1e-6))
    return pd.DataFrame({"value": acc.to_numpy(), "z": z}, index=acc.index)


def rootzone(era5: pd.DataFrame) -> pd.Series:
    """Wilgotność 0-100 cm: średnia ważona grubością warstw ERA5-Land (7, 21, 72 cm)."""
    return (7 * era5["sm_l1"] + 21 * era5["sm_l2"] + 72 * era5["sm_l3"]) / 100.0


def era5_anomalies(era5: pd.DataFrame, cfg: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
    """Dzienne anomalie z ERA5-Land: wilgotność 0-7 cm i 0-100 cm, SPI-1 i SPI-3."""
    e = era5.set_index(pd.to_datetime(era5["time"]).dt.floor("D")).sort_index()
    e = e[~e.index.duplicated(keep="last")]
    ref, hw = cfg["CLIM_REF"], cfg["CLIM_HALF_WINDOW_DAYS"]
    out = {
        "ERA5L_SM_L1": clim_anomaly(e["sm_l1"], ref, hw),
        "ERA5L_SM_RZ": clim_anomaly(rootzone(e), ref, hw),
    }
    for days, name in zip(cfg["SPI_DAYS"], ("ERA5L_SPI1", "ERA5L_SPI3")):
        out[name] = spi(e["precip_mm"], days, ref, hw)
    return out


def track_ids(t: pd.Series, min_sep_min: float = 5.0) -> np.ndarray:
    """Tor orbity S-2 z godziny akwizycji: nad stałym punktem sąsiednie orbity względne przelatują o różnej porze
    (nad Condom ~10:59 i ~11:09 UTC, z rozrzutem kilku minut w archiwum). Podział na dwie grupy progiem Otsu
    na minutach doby; gdy średnie grup różnią się o mniej niż min_sep_min minut — jeden tor."""
    mins = (t.dt.hour * 60 + t.dt.minute + t.dt.second / 60).to_numpy(float)
    u = np.sort(np.unique(mins))
    if len(u) < 2:
        return np.zeros(len(mins), int)
    best, thr = -1.0, None
    for cut in (u[:-1] + u[1:]) / 2:
        a, b = mins[mins <= cut], mins[mins > cut]
        score = len(a) * len(b) * (a.mean() - b.mean()) ** 2
        if score > best:
            best, thr = score, cut
    lo, hi = mins[mins <= thr], mins[mins > thr]
    if hi.mean() - lo.mean() < min_sep_min:
        return np.zeros(len(mins), int)
    return (mins > thr).astype(int)


def scene_anomaly(df: pd.DataFrame, col: str, cfg: Dict[str, Any]) -> pd.DataFrame:
    """
    Anomalia roślinności dla nieregularnych scen S-2 względem scen z ±VEG_HALF_WINDOW_DAYS dni roku.
    Domyślnie (Plan v7, A1–A3):
      - VEG_CAUSAL: tylko lata WCZEŚNIEJSZE (tak, jak system działałby w danym dniu; trend NDVI winnicy
        sprawiał, że klimatologia z „pozostałych lat” zawyżała zgodność z gruntem: R 0,50 → 0,29 na tych samych dniach);
      - VEG_BY_TRACK: odniesienie z tego samego toru orbity (różnica średnich z między torami ~0,4 na winnicy,
        geometria rzędów); gdy scen z toru za mało — wszystkie tory (ref_mode = "all_tracks");
      - VEG_PREDICTIVE_Z: z predykcyjne z rozkładu t-Studenta (krótka historia, n_ref 5–30),
        żeby częstość z <= -1 odpowiadała rozkładowi normalnemu (było 19,6% zamiast 15,9%).
    Tylko sceny z udziałem pikseli czystych >= VEG_MIN_CLEAR_FRAC.
    """
    from scipy import stats

    d = df[(df["clear_frac"] >= cfg["VEG_MIN_CLEAR_FRAC"]) & df[col].notna()].sort_values("time").copy()
    if d.empty:
        return d.assign(clim_mean=np.nan, clim_std=np.nan, z=np.nan, n_ref=0, track=0, ref_mode="", n_ref_years=0)
    causal, by_track = cfg.get("VEG_CAUSAL", True), cfg.get("VEG_BY_TRACK", True)
    doy, yr, v = d["time"].dt.dayofyear.to_numpy(), d["time"].dt.year.to_numpy(), d[col].to_numpy(float)
    trk = track_ids(d["time"])
    mu, sd, n, mode, n_years = [], [], [], [], []
    for i in range(len(d)):
        m = (yr < yr[i]) if causal else (yr != yr[i])
        if causal and cfg.get("VEG_REF_YEARS"):
            m &= yr >= yr[i] - cfg["VEG_REF_YEARS"]
        m &= _circ_doy_dist(doy, doy[i]) <= cfg["VEG_HALF_WINDOW_DAYS"]
        ref = "all_tracks"
        if by_track and (m & (trk == trk[i])).sum() >= cfg["VEG_MIN_REF"]:
            m, ref = m & (trk == trk[i]), "same_track"
        pool = v[m]
        ok = len(pool) >= cfg["VEG_MIN_REF"]
        mu.append(pool.mean() if ok else np.nan)
        sd.append(pool.std(ddof=1) if ok else np.nan)
        n.append(len(pool))
        mode.append(ref if ok else "")
        n_years.append(len(np.unique(yr[m])) if ok else 0)     # lata w puli normy (protokół W3b §2)
    d["clim_mean"], d["clim_std"], d["n_ref"], d["track"], d["ref_mode"] = mu, sd, n, trk, mode
    d["n_ref_years"] = n_years
    if cfg.get("VEG_PREDICTIVE_Z", True):
        nn = d["n_ref"].to_numpy(float)
        t = (d[col] - d["clim_mean"]).to_numpy() / (d["clim_std"].to_numpy() * np.sqrt(1 + 1 / np.maximum(nn, 1)))
        d["z"] = stats.norm.ppf(np.clip(stats.t.cdf(t, df=np.maximum(nn - 1, 1)), 1e-6, 1 - 1e-6))
        d.loc[~np.isfinite(t), "z"] = np.nan
    else:
        d["z"] = (d[col] - d["clim_mean"]) / d["clim_std"]
    return d


def dekad_end(t: pd.Series) -> pd.Series:
    """Koniec dekady (10., 20. lub ostatni dzień miesiąca)."""
    t = pd.to_datetime(t)
    end_month = t + pd.offsets.MonthEnd(0)
    return pd.to_datetime(np.where(t.dt.day <= 10, t.dt.to_period("M").dt.to_timestamp() + pd.Timedelta(days=9),
                          np.where(t.dt.day <= 20, t.dt.to_period("M").dt.to_timestamp() + pd.Timedelta(days=19),
                                   end_month))).normalize()
