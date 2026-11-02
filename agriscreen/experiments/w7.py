"""
W7 — wskazówki AgriScreen potwierdzone pomiarami (protokół docs/evidence/W7_protokol_wskazowki.md, D-093).

Prawda = tylko wartości zmierzone (QC 0) z archiwów ICOS L2, czujnik ISMN Condom i Météo-France (§1).
Wskazówki = produkt bez zmian (§3): percentyl ERA5-Land 0–100 cm, z_woda Sentinel-2, progi przymrozku i upału.
Miara = trafność wskazówki wobec przypadku, przedział jackknife po latach łącznie dla stacji (§4–§5).
Odnośniki „§n” w docstringach wskazują paragraf protokołu.
"""

from __future__ import annotations

import os
import re
import zipfile
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from agriscreen.experiments import w7_data

FREEZE = "2026-09-30"                 # §0
SOIL_MONTHS = (4, 10)                 # §0: gleba i pogoda IV–X
VEG_MONTHS = (6, 9)                   # §0: roślinność VI–IX
HALF_WINDOW = 15                      # §2
MIN_OTHER_YEARS, MIN_VALUES = 2, 20   # §2
LE_DAY_FRAC = 0.70                    # §1
TA_MIN_HH, P_FULL_HH = 44, 48         # §1
EF_HOURS, EF_MIN_HH = (11, 15), 6     # §1 (opisowo; ważność EF: ≥ 6 z 8 półgodzin)
VEG_HALF, VEG_MIN_DAYS = 3, 5         # §2: okno [t−3, t+3], ≥ 5 ważnych dób
DRY_PCT, WET_PCT = 30.0, 70.0         # §3 (SWI_DRY_PCT, WATER_WET_PCT)
Z_LOW, Z_HIGH = -1.0, 1.0             # §3
P_MIN, MIN_HINTS, MIN_YEARS = 0.60, 30, 3   # §5
FROST_T, HEAT_T = 0.0, 35.0           # §2: prawda przymrozku / upału


# ----------------------------------------------------------------------------------------------------------------
# Odczyt archiwów ICOS
# ----------------------------------------------------------------------------------------------------------------

def _member(path: str, station: str, kind: str) -> str:
    """Nazwa pliku w archiwum: kind = FLUXNET_HH | METEO | VARINFO_METEO (wersja L2 lub INTERIM_L2)."""
    rx = re.compile(rf"ICOSETC_{re.escape(station)}_{kind}_(INTERIM_)?L2\.csv$")
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist() if rx.search(n)]
    if not names:
        raise FileNotFoundError(f"{os.path.basename(path)}: brak {kind}")
    return names[0]


def _read(path: str, member: str, usecols: Optional[List[str]] = None, **kw) -> pd.DataFrame:
    with zipfile.ZipFile(path) as z:
        with z.open(member) as f:
            cols = pd.read_csv(f, nrows=0).columns
        use = None if usecols is None else [c for c in usecols if c in cols]
        with z.open(member) as f:
            return pd.read_csv(f, usecols=use, na_values=[-9999, "-9999"], **kw)


def archive_path(ref_dir: str, station: str) -> str:
    """Najnowsze archiwum ICOS L2 stacji wg MANIFEST_W7.csv."""
    man = w7_data.read_manifest(os.path.join(ref_dir, "MANIFEST_W7.csv"))
    row = man[(man["station"] == station) & (man["spec"] == "ETC L2 ARCHIVE")]
    if row.empty:
        raise FileNotFoundError(f"{station}: brak archiwum w MANIFEST_W7.csv")
    return os.path.join(ref_dir, station, row["file_name"].iat[-1])


def _halfhour_index(ts: pd.Series) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(pd.to_datetime(ts.astype("int64").astype(str), format="%Y%m%d%H%M"))


def flux_daily(path: str, station: str) -> pd.DataFrame:
    """§1: dobowe wartości z pomiarów FLUXNET_HH (tylko półgodziny zmierzone): et_le (średnie LE w dzień),
    gpp (opisowo), ef (11–15), tmin, tmax, p. NaN, gdy doba nie spełnia progu pomiarów."""
    cols = ["TIMESTAMP_START", "LE_F_MDS", "LE_F_MDS_QC", "H_F_MDS", "H_F_MDS_QC", "SW_IN_POT", "GPP_NT_VUT_REF",
            "NEE_VUT_REF_QC", "TA_F_MDS", "TA_F_MDS_QC", "P"]
    d = _read(path, _member(path, station, "FLUXNET_HH"), cols)
    idx = _halfhour_index(d["TIMESTAMP_START"])
    d.index = idx
    day = idx.floor("D")
    dt = d["SW_IN_POT"] > 0
    le_ok = d["LE_F_MDS"].notna() & (d["LE_F_MDS_QC"] == 0)
    g = pd.DataFrame({"n_day": dt, "n_le": dt & le_ok, "le": d["LE_F_MDS"].where(dt & le_ok),
                      "n_nee": dt & (d["NEE_VUT_REF_QC"] == 0), "gpp": d["GPP_NT_VUT_REF"].where(dt)}, index=idx)
    agg = g.groupby(day).agg(n_day=("n_day", "sum"), n_le=("n_le", "sum"), le=("le", "mean"),
                             n_nee=("n_nee", "sum"), gpp=("gpp", "mean"))
    out = pd.DataFrame(index=agg.index)
    out["et_le"] = agg["le"].where((agg["n_day"] > 0) & (agg["n_le"] >= LE_DAY_FRAC * agg["n_day"]))
    out["gpp"] = agg["gpp"].where((agg["n_day"] > 0) & (agg["n_nee"] >= LE_DAY_FRAC * agg["n_day"]))
    # EF w godzinach 11–15: obie składowe zmierzone
    hr = idx.hour
    mid = (hr >= EF_HOURS[0]) & (hr < EF_HOURS[1])
    both = le_ok & d["H_F_MDS"].notna() & (d["H_F_MDS_QC"] == 0) & mid
    e = pd.DataFrame({"le": d["LE_F_MDS"].where(both), "h": d["H_F_MDS"].where(both), "n": both}, index=idx)
    ea = e.groupby(day).agg(le=("le", "sum"), h=("h", "sum"), n=("n", "sum"))
    den = ea["le"] + ea["h"]
    out["ef"] = (ea["le"] / den).where((ea["n"] >= EF_MIN_HH) & (den > 0))
    # temperatura i opad (pomiar, bez ERA)
    ta_ok = d["TA_F_MDS"].notna() & (d["TA_F_MDS_QC"] == 0)
    t = pd.DataFrame({"ta": d["TA_F_MDS"].where(ta_ok), "n": ta_ok}, index=idx).groupby(day)
    ta = t.agg(tmin=("ta", "min"), tmax=("ta", "max"), n=("n", "sum"))
    out["tmin"] = ta["tmin"].where(ta["n"] >= TA_MIN_HH)
    out["tmax"] = ta["tmax"].where(ta["n"] >= TA_MIN_HH)
    p = pd.DataFrame({"p": d["P"], "n": d["P"].notna()}, index=idx).groupby(day).agg(p=("p", "sum"), n=("n", "sum"))
    out["p"] = p["p"].where(p["n"] >= P_FULL_HH)
    out.index.name = "date"
    return out


def soil_depths(path: str, station: str, until: str = FREEZE) -> Dict[int, float]:
    """§1: głębokości poziomów SWC_n [m, dodatnie] z VARINFO_METEO; przy kilku wpisach — najnowszy ≤ zamrożenia."""
    v = _read(path, _member(path, station, "VARINFO_METEO"), dtype=str, keep_default_na=False)
    v = v[v["VARIABLE_GROUP"] == "GRP_VAR_INFO"]
    rows = []
    for _, g in v.groupby("GROUP_ID"):
        kv = dict(zip(g["VARIABLE"], g["DATAVALUE"]))
        m = re.fullmatch(r"SWC_(\d+)", kv.get("VAR_INFO_VARNAME", ""))
        if m and kv.get("VAR_INFO_HEIGHT", "") not in ("", None):
            rows.append({"level": int(m.group(1)), "depth": -float(kv["VAR_INFO_HEIGHT"]),
                         "date": kv.get("VAR_INFO_DATE", "00000000")})
    if not rows:
        return {}
    r = pd.DataFrame(rows)
    r = r[r["date"] <= until.replace("-", "")].sort_values("date")
    return {int(k): float(g["depth"].iat[-1]) for k, g in r.groupby("level")}


def soil_daily(path: str, station: str) -> Tuple[pd.Series, Dict[str, Any]]:
    """§1: wilgotność 0–100 cm ze stacji ICOS (L2 Meteo, QC jak W2/REF §2, profil ważony miąższością)."""
    from agriscreen import reference
    depths = {k: d for k, d in soil_depths(path, station).items() if 0 < d <= 1.0}
    info = {"depths": depths}
    if not depths:
        return pd.Series(dtype=float), info
    use = [f"SWC_{n}" for n in depths]
    hh = _read(path, _member(path, station, "METEO"), ["TIMESTAMP_END"] + use)
    hh.index = _halfhour_index(hh.pop("TIMESTAMP_END")) - pd.Timedelta(minutes=15)
    hh = (hh / 100.0).sort_index()
    have = {k: d for k, d in depths.items() if f"SWC_{k}" in hh.columns}
    daily, rep = reference.icos_daily(hh[[f"SWC_{k}" for k in have]], reference.REF_QC)
    info.update({"levels_in_file": sorted(have), "qc": rep})
    return reference.profile_series(daily, have), info


# ----------------------------------------------------------------------------------------------------------------
# Norma i zdarzenia (§2)
# ----------------------------------------------------------------------------------------------------------------

def loyo_normal(s: pd.Series, half: int = HALF_WINDOW) -> pd.Series:
    """Norma dnia: mediana z innych lat (≠ rok dnia) w oknie ±half dni kalendarzowych; ≥ 2 lata i ≥ 20 wartości."""
    s = pd.Series(s, dtype=float).dropna()
    if s.empty:
        return s
    yrs, doy, vals = s.index.year.to_numpy(), s.index.dayofyear.to_numpy(), s.to_numpy()
    out = np.full(len(s), np.nan)
    for i in range(len(s)):
        dd = np.abs(doy - doy[i])
        m = (np.minimum(dd, 366 - dd) <= half) & (yrs != yrs[i])
        if m.sum() >= MIN_VALUES and len(np.unique(yrs[m])) >= MIN_OTHER_YEARS:
            out[i] = np.median(vals[m])
    return pd.Series(out, index=s.index)


def window_mean(s: pd.Series, half: int = VEG_HALF, min_days: int = VEG_MIN_DAYS) -> pd.Series:
    """§2: średnia z okna [t−half, t+half] przy ≥ min_days ważnych dobach."""
    s = pd.Series(s, dtype=float)
    if s.dropna().empty:
        return s.dropna()
    full = s.reindex(pd.date_range(s.index.min(), s.index.max(), freq="D"))
    return full.rolling(2 * half + 1, center=True, min_periods=min_days).mean().dropna()


def events(truth: pd.Series) -> pd.DataFrame:
    """Wartość, norma i zdarzenia poniżej / powyżej normy (§2)."""
    n = loyo_normal(truth)
    d = pd.DataFrame({"truth": truth.reindex(n.index), "normal": n}).dropna()
    d["truth_below"] = d["truth"] < d["normal"]
    d["truth_above"] = d["truth"] > d["normal"]
    return d


def _in_months(idx: pd.DatetimeIndex, months: Tuple[int, int]) -> np.ndarray:
    return (idx.month >= months[0]) & (idx.month <= months[1])


def _in_season(idx: pd.DatetimeIndex, season: Tuple[str, str]) -> np.ndarray:
    md = idx.strftime("%m-%d")
    return (md >= season[0]) & (md <= season[1])


# ----------------------------------------------------------------------------------------------------------------
# Wskazówki produktu (§3)
# ----------------------------------------------------------------------------------------------------------------

def era5_frame(path_or_df: Any) -> pd.DataFrame:
    e = pd.read_csv(path_or_df, parse_dates=["time"]) if isinstance(path_or_df, str) else path_or_df
    e = e.set_index(pd.to_datetime(e["time"]).dt.floor("D")).sort_index()
    return e[~e.index.duplicated(keep="last")]


def soil_percentile(e: pd.DataFrame, cfg: Dict[str, Any]) -> pd.Series:
    """§3: percentyl ERA5-Land 0–100 cm wobec CLIM_REF (±CLIM_HALF_WINDOW_DAYS), jak karta (parcel.soil_pct)."""
    from agriscreen import metrics
    return metrics.clim_anomaly(metrics.rootzone(e), cfg["CLIM_REF"], int(cfg["CLIM_HALF_WINDOW_DAYS"]))["percentile"]


_PA_CACHE: Dict[str, pd.DataFrame] = {}


def station_anomalies(station_dir: str, code_dir: str, until: str = FREEZE) -> pd.DataFrame:
    """§3: anomalie kwadratów stacji z rejestru stacji (produkt bez zmian: parcel_anomalies z water_index);
    liczone raz na stację i zapamiętane."""
    key = f"{station_dir}|{until}"
    if key not in _PA_CACHE:
        from agriscreen import parcel
        from agriscreen.config import make_config
        from agriscreen.runtime import registry_read
        rt = {"REGISTRY_DIR": os.path.join(station_dir, "data", "registry")}
        cfg = make_config(code_dir, {"PARCEL_TYPE": w7_data.SQUARE_TYPE}, data_dir=station_dir)
        w = parcel.parcel_wide(registry_read(rt, "gwl_observations"), cfg["PARCEL_PRODUCT"], until)
        _PA_CACHE[key] = parcel.parcel_anomalies(w, cfg)[0]
    return _PA_CACHE[key]


def station_water_z(station_dir: str, code_dir: str, site_id: str = "VINEYARD_01",
                    until: str = FREEZE) -> pd.DataFrame:
    """§3: z_woda kwadratu stacji (VINEYARD_01 = 300 m; 02 = 200 m; 03 = 500 m), tylko qc_ok."""
    from agriscreen import parcel
    pa = station_anomalies(station_dir, code_dir, until)
    z = pa[(pa["index"] == "water") & (pa["site_id"] == site_id) & parcel._bool(pa["qc_ok"])].dropna(subset=["z"])
    z = z.assign(day=pd.to_datetime(z["time"]).dt.normalize())
    return z.set_index("day")[["z", "n_ref_years", "track"]].sort_index()


# ----------------------------------------------------------------------------------------------------------------
# Miara i testy (§4–§5)
# ----------------------------------------------------------------------------------------------------------------

def hit_stats(df: pd.DataFrame, hint: str, truth: str) -> Dict[str, Any]:
    """§4: trafność p, przypadek b, Δ = p − b z przedziałem jackknife po latach (łącznie dla stacji)."""
    from agriscreen.parcel import jackknife_ci

    def p_of(d):
        h = d[d[hint]]
        return float(h[truth].mean()) if len(h) else np.nan

    def delta(d):
        return p_of(d) - float(d[truth].mean()) if len(d) else np.nan
    h = df[df[hint]]
    p, plo, phi, _ = jackknife_ci(df, p_of, bounds=(0, 1))
    dv, dlo, dhi, loo = jackknife_ci(df, delta, bounds=(-1, 1))
    return {"p": p, "p_lo": plo, "p_hi": phi, "b": float(df[truth].mean()) if len(df) else np.nan,
            "delta": dv, "delta_lo": dlo, "delta_hi": dhi, "n_hint": int(len(h)), "n_all": int(len(df)),
            "years_hint": int(h["year"].nunique()) if len(h) else 0, "years_all": int(df["year"].nunique()),
            "sites": int(df["site"].nunique()), "loo": loo}


def verdict(s: Dict[str, Any]) -> str:
    """§5: kryterium testu rozstrzygającego."""
    if s["n_hint"] < MIN_HINTS or s["years_hint"] < MIN_YEARS or not np.isfinite(s["delta_lo"]):
        return "za mało danych (niepotwierdzone)"
    return "potwierdzone" if (s["delta_lo"] > 0 and s["p"] >= P_MIN) else "niepotwierdzone"


def contingency(df: pd.DataFrame, hint: str, truth: str) -> Dict[str, Any]:
    """§6: POD, FAR i trafność dla zdarzeń rzadkich (przymrozek, upał)."""
    a = int((df[hint] & df[truth]).sum())
    fa = int((df[hint] & ~df[truth]).sum())
    miss = int((~df[hint] & df[truth]).sum())
    return {"hits": a, "false_alarms": fa, "misses": miss, "n_days": int(len(df)),
            "POD": a / (a + miss) if a + miss else np.nan, "FAR": fa / (a + fa) if a + fa else np.nan}


TESTS_NAME = "w7_tests.csv"
_TRUST = {
    "K1": ("Hint “dry soil in the area” (ERA5-Land model)",
           "measured soil moisture below its usual level for the time of year: 10 ICOS stations in France and the "
           "ISMN sensor at Condom, April–October"),
    "K2": ("Hint “vegetation below its own normal” (Sentinel-2)",
           "measured evapotranspiration below its usual level: 7 ICOS towers in forests and grasslands "
           "(not vineyards), June–September"),
}


def trust_rows(out_dir: str) -> List[Dict[str, str]]:
    """§7: wiersze K1 i K2 do tabeli „How far to trust it” z w7_tests.csv (brak pliku = brak wierszy)."""
    p = os.path.join(out_dir, TESTS_NAME)
    if not os.path.exists(p) or os.path.getsize(p) < 2:
        return []
    t = pd.read_csv(p)
    rows: List[Dict[str, str]] = []
    for _, r in t.iterrows():
        key = str(r["test"])[:2]
        if key not in _TRUST:
            continue
        what, against = _TRUST[key]
        ok = str(r.get("werdykt", "")) == "potwierdzone"
        result = (f"confirmed by the measurement on {100 * r['p']:.0f}% of hint days "
                  f"[{100 * r['p_lo']:.0f}–{100 * r['p_hi']:.0f}%] vs {100 * r['b']:.0f}% by chance "
                  f"({int(r['n_hint'])} hint days, {int(r['years_hint'])} years)")
        if not ok and str(r.get("werdykt", "")).startswith("za mało"):
            result += "; too little data for a verdict"
        rows.append({"what": what, "against": against + f" (pre-registered W7, {str(r['protocol_sha256'])[:8]}…)",
                     "result": result, "status": "confirmed" if ok else "not confirmed"})
    return rows


def spearman(a: pd.Series, b: pd.Series) -> float:
    from scipy.stats import spearmanr
    m = a.notna() & b.notna()
    return float(spearmanr(a[m], b[m])[0]) if m.sum() >= 5 else np.nan
