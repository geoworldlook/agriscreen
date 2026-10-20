"""
================================================================================
MOJA WINNICA (W3b) — DZIAŁKA WOBEC WŁASNEJ HISTORII
================================================================================
Liczenie dla zadań pipeline (wejście i wyjście: DataFrame; dane czujnika ISMN czyta sensor_daily przez stations):
  task_parcel_anomalies — anomalie 15 winnic do karty bieżącej, mediana okolicy, flaga zmiany gospodarowania,
  task_parcel_tests     — testy zamrożone na scenach ≤ W3B_FREEZE: T1 kalibracja, T2 szum, T3 zgodność z czujnikiem
                          w gruncie, wariant wielopasmowy, wartości „przed” z F4 i kontrola jakości.

Definicje i kryteria: docs/evidence/W3b_protokol_walidacji.md (dalej §n), zarejestrowany przed liczeniem (D-089).
  - Anomalia każdego wskaźnika i pasma: metrics.scene_anomaly bez zmian metody (5 lat wcześniejszych, ±15 dni roku,
    ten sam tor orbity, z predykcyjne), jedna scena działki na dzień (§1–§2).
  - Wskaźnik wody w roślinności: z_woda = (z_NDMI − z_CRSWIR)/2; klasy ±1 (§3).
  - Przedział 95%: jackknife po latach (§0) — bez losowania, więc wynik nie zależy od ziarna.
  - Kryteria są tylko dwa: T3 (zdanie 3 karty) i przyjęcie wariantu wielopasmowego (§7); reszta opisowo (§11).
Karta nie mówi o stresie wodnym winorośli ani o wczesnym ostrzeżeniu (D-087): wskaźnik widzi całą działkę.
================================================================================
"""

from __future__ import annotations
import glob
import hashlib
import json
import os
import re
from typing import Any, Callable, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from agriscreen import metrics

CODE_VERSION = "1.0"           # poprawka błędu implementacji (§11) = nowa wersja -> testy liczone od nowa


P_BELOW = 0.15865525393145707  # Φ(−1): oczekiwany udział z ≤ −1 przy poprawnej kalibracji (§4)


INDEX_SIGN = {"crswir": -1.0}  # wyższy CRSWIR = mniej wody, więc w złożeniu i na karcie ze znakiem −


AREA, PARCELS = "W3B_AREA", "W3B_PARCELS"     # site_id wierszy okolicy (mediana) i wierszy łącznych dla działek


SENSOR_VARIANTS = ("W1", "W2", "W3", "W1_05WP", "W1_015")


COLS = ["site_id", "product", "index", "time", "value", "clim_mean", "clim_std", "z", "n_ref", "n_ref_years",
        "track", "ref_mode", "n_pixels", "qc_ok"]


METRIC_COLS = ["site_id", "product", "reference", "segment", "period", "subset", "metric", "value", "ci_low",
               "ci_high", "n", "date_from", "date_to"]


TEST_COLS = METRIC_COLS + ["n_parcels", "criterion", "verdict", "key"]


def _f(x: Any) -> float:
    try:
        x = float(x)
    except (TypeError, ValueError):
        return np.nan
    return x if np.isfinite(x) else np.nan


def _bool(s: pd.Series) -> pd.Series:
    """Kolumna logiczna po odczycie CSV (True / "True" / 1)."""
    return s.map(lambda v: str(v).strip().lower() in ("true", "1", "1.0"))


def spearman(a: Any, b: Any) -> float:
    """ρ Spearmana z rangami średnimi (jak reference._spearman); NaN przy < 3 parach albo stałej serii."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) < 3:
        return np.nan
    ra, rb = pd.Series(a).rank().to_numpy(), pd.Series(b).rank().to_numpy()
    if ra.std() == 0 or rb.std() == 0:
        return np.nan
    return float(np.corrcoef(ra, rb)[0, 1])


def pearson(a: Any, b: Any) -> float:
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) < 3 or a.std() == 0 or b.std() == 0:
        return np.nan
    return float(np.corrcoef(a, b)[0, 1])


def jackknife_ci(df: pd.DataFrame, stat: Callable[[pd.DataFrame], float], year_col: str = "year",
                 min_years: int = 3, bounds: Tuple[float, float] = (-np.inf, np.inf)
                 ) -> Tuple[float, float, float, Dict[int, float]]:
    """
    Wartość statystyki, 95% przedział jackknife po latach i wartości bez kolejnych lat (§0):
    SE = √((G−1)/G · Σ(θ₋g − θ̄₋)²), przedział θ ± t(0,975; G−1)·SE, przycięty do zakresu statystyki (bounds,
    np. udział 0–1). NaN, gdy lat < min_years.
    """
    from scipy import stats
    years = sorted(pd.unique(df[year_col])) if len(df) else []
    est = _f(stat(df)) if len(df) else np.nan
    if len(years) < min_years or not np.isfinite(est):
        return est, np.nan, np.nan, {}
    loo = {int(y): _f(stat(df[df[year_col] != y])) for y in years}
    v = np.array(list(loo.values()), float)
    if not np.isfinite(v).all():
        return est, np.nan, np.nan, loo
    g = len(v)
    se = float(np.sqrt((g - 1) / g * np.sum((v - v.mean()) ** 2)))
    q = float(stats.t.ppf(0.975, g - 1))
    return est, float(np.clip(est - q * se, *bounds)), float(np.clip(est + q * se, *bounds)), loo


def _in_months(t: pd.Series, months: Tuple[int, int]) -> pd.Series:
    return pd.to_datetime(t).dt.month.between(int(months[0]), int(months[1]))


def _row(seg: str, site: str, product: str, reference: str, subset: str, metric: str, value: Any,
         ci: Tuple[Any, Any] = (np.nan, np.nan), days: Any = None, n: Optional[int] = None,
         n_parcels: Any = np.nan, criterion: bool = False, verdict: str = "", key: str = "") -> Dict[str, Any]:
    """Jeden wiersz tabeli testów (schemat gwl_validation_metrics + kryterium, werdykt i klucz dla karty)."""
    t = pd.to_datetime(pd.Series(list(days))) if days is not None and len(days) else pd.Series([], dtype="datetime64[ns]")
    return {"site_id": site, "product": product, "reference": reference, "segment": seg,
            "period": f"{t.dt.year.min()}-{t.dt.year.max()}" if len(t) else "", "subset": subset, "metric": metric,
            "value": _f(value), "ci_low": _f(ci[0]), "ci_high": _f(ci[1]), "n": int(n if n is not None else len(t)),
            "date_from": t.min().strftime("%Y-%m-%d") if len(t) else "",
            "date_to": t.max().strftime("%Y-%m-%d") if len(t) else "", "n_parcels": n_parcels,
            "criterion": bool(criterion), "verdict": verdict, "key": key}


def parcel_wide(obs: pd.DataFrame, product: str, until: Optional[str] = None) -> pd.DataFrame:
    """Obserwacje produktu działek (gwl_observations) w układzie szerokim: wiersz = (działka, scena)."""
    o = obs[obs["product"] == product].copy()
    if o.empty:
        return pd.DataFrame(columns=["site_id", "time_utc", "time", "n_pixels", "clear_frac"])
    o["value"] = pd.to_numeric(o["value"], errors="coerce")
    w = o.pivot_table(index=["site_id", "time_utc"], columns="variable", values="value", aggfunc="first").reset_index()
    w.columns.name = None
    w["time"] = pd.to_datetime(w["time_utc"]).dt.tz_localize(None)
    npx = pd.to_numeric(o["n_pixels"], errors="coerce").groupby(o["site_id"]).max()
    w["n_pixels"] = w["site_id"].map(npx)
    if "clear_frac" not in w:
        w["clear_frac"] = np.nan
    if until is not None:
        w = w[w["time"].dt.normalize() <= pd.Timestamp(until)]
    return w.reset_index(drop=True)


def one_scene_per_day(w: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
    """Jedna scena działki na dzień: zostaje ta z większym clear_frac (§1). Zwraca też liczbę dni z 2 scenami."""
    if w.empty:
        return w, 0
    d = w.assign(_day=w["time"].dt.normalize(), _cf=pd.to_numeric(w["clear_frac"], errors="coerce").fillna(-1.0))
    d = d.sort_values(["site_id", "_day", "_cf", "time"])
    keep = ~d.duplicated(["site_id", "_day"], keep="last")
    return d[keep].drop(columns=["_day", "_cf"]).reset_index(drop=True), int(d.loc[~keep, "_day"].nunique())


def water_index(pa: pd.DataFrame) -> pd.DataFrame:
    """Wiersze index = "water": z = (z_NDMI − z_CRSWIR)/2, tylko gdy oba z istnieją dla tej samej sceny (§3)."""
    a = pa[pa["index"] == "ndmi"].dropna(subset=["z"]).set_index(["site_id", "time"])
    c = pa[pa["index"] == "crswir"].dropna(subset=["z"]).set_index(["site_id", "time"])
    j = a.join(c[["z", "n_ref", "n_ref_years", "ref_mode"]], rsuffix="_c", how="inner")
    if j.empty:
        return pd.DataFrame(columns=COLS)
    out = pd.DataFrame({
        "product": j["product"], "index": "water", "value": np.nan, "clim_mean": np.nan, "clim_std": np.nan,
        "z": (j["z"] - j["z_c"]) / 2.0, "n_ref": np.minimum(j["n_ref"], j["n_ref_c"]),
        "n_ref_years": np.minimum(j["n_ref_years"], j["n_ref_years_c"]), "track": j["track"],
        "ref_mode": np.where(j["ref_mode"] == j["ref_mode_c"], j["ref_mode"], "mixed"),
        "n_pixels": j["n_pixels"], "qc_ok": j["qc_ok"]}, index=j.index).reset_index()
    return out[COLS]


def parcel_anomalies(w: pd.DataFrame, cfg: Dict[str, Any]) -> Tuple[pd.DataFrame, int]:
    """
    Anomalie wszystkich działek i wskaźników PARCEL_ANOM_INDICES (metrics.scene_anomaly, §2) po regule jednej sceny
    na dzień (§1), qc_ok = n_pixels ≥ PARCEL_MIN_PX, plus wiersze "water" (§3). Zwraca (anomalie, liczba dni z 2 scenami).
    """
    if w.empty:
        return pd.DataFrame(columns=COLS), 0
    m0, m1 = cfg["S2_MONTHS"]
    w = w[w["time"].dt.month.between(m0, m1)]
    w, n_dup = one_scene_per_day(w)
    parts = []
    for site, g in w.groupby("site_id"):
        for idx in cfg["PARCEL_ANOM_INDICES"]:
            if idx not in g or g[idx].isna().all():
                continue
            a = metrics.scene_anomaly(g, idx, cfg)
            if len(a):
                parts.append(pd.DataFrame({
                    "site_id": site, "index": idx, "time": a["time"].to_numpy(), "value": a[idx].to_numpy(),
                    "clim_mean": a["clim_mean"].to_numpy(), "clim_std": a["clim_std"].to_numpy(),
                    "z": a["z"].to_numpy(), "n_ref": a["n_ref"].to_numpy(), "n_ref_years": a["n_ref_years"].to_numpy(),
                    "track": a["track"].to_numpy(), "ref_mode": a["ref_mode"].to_numpy(),
                    "n_pixels": a["n_pixels"].to_numpy()}))
    if not parts:
        return pd.DataFrame(columns=COLS), n_dup
    pa = pd.concat(parts, ignore_index=True)
    pa["product"] = cfg["PARCEL_PRODUCT"]
    pa["qc_ok"] = pd.to_numeric(pa["n_pixels"], errors="coerce") >= cfg["PARCEL_MIN_PX"]
    pa = pd.concat([pa[COLS], water_index(pa[COLS])], ignore_index=True)
    return pa.sort_values(["site_id", "index", "time"]).reset_index(drop=True), n_dup


def qc_sites(pa: pd.DataFrame) -> List[str]:
    """Winnice spełniające QC (≥ PARCEL_MIN_PX pikseli, §1): zbiór T1, T2 i flagi."""
    return sorted(pa.loc[_bool(pa["qc_ok"]), "site_id"].unique()) if len(pa) else []


def t3_sites(pa: pd.DataFrame, cfg: Dict[str, Any]) -> List[str]:
    """Zbiór T3 i §7: winnice z QC bez PARCEL_T3_EXCLUDE (VINEYARD_06)."""
    return [s for s in qc_sites(pa) if s not in cfg["PARCEL_T3_EXCLUDE"]]


def area_series(pa: pd.DataFrame, index: str, sites: List[str], min_n: int, col: str = "z") -> pd.DataFrame:
    """Mediana `col` wskaźnika w dniu sceny wśród `sites` (znak −1 dla CRSWIR), ważna przy ≥ min_n winnicach."""
    d = pa[(pa["index"] == index) & pa["site_id"].isin(sites)].dropna(subset=[col])
    if d.empty:
        return pd.DataFrame(columns=["z_med", "n_parcels"], index=pd.DatetimeIndex([], name="day"))
    g = d.assign(day=pd.to_datetime(d["time"]).dt.normalize()).groupby("day")[col]
    out = pd.DataFrame({"z_med": INDEX_SIGN.get(index, 1.0) * g.median(), "n_parcels": g.size()})
    return out[out["n_parcels"] >= min_n]


def band_features(pa: pd.DataFrame, sites: List[str], bands: Tuple[str, ...], min_n: int) -> pd.DataFrame:
    """Cechy §7: mediana z każdego pasma wśród winnic, które mają w tym dniu wszystkie pasma (≥ min_n winnic)."""
    d = pa[pa["index"].isin(bands) & pa["site_id"].isin(sites)].dropna(subset=["z"])
    if d.empty:
        return pd.DataFrame(columns=list(bands))
    d = d.assign(day=pd.to_datetime(d["time"]).dt.normalize())
    piv = d.pivot_table(index=["day", "site_id"], columns="index", values="z", aggfunc="last")
    piv = piv.reindex(columns=list(bands)).dropna()
    g = piv.groupby(level="day")
    x, n = g.median(), g.size()
    return x[n >= min_n]


def management_flags(pa: pd.DataFrame, sites: List[str], cfg: Dict[str, Any]) -> pd.DataFrame:
    """
    Flaga „możliwa zmiana gospodarowania” (§8): d = z_woda działki − mediana z_woda pozostałych winnic z QC (≥ PARCEL_MIN_AREA);
    w sezonie (IV–X) ≥ PARCEL_FLAG_MIN_SCENES scen z d, z czego ≥ PARCEL_FLAG_SHARE ma d ≤ −1 → "-", d ≥ +1 → "+".
    Normy nie zmieniamy i z testów niczego nie wyłączamy.
    """
    cols = ["site_id", "year", "n", "share_low", "share_high", "d_median", "flag"]
    w = pa[(pa["index"] == "water") & pa["site_id"].isin(sites)].dropna(subset=["z"])
    if w.empty:
        return pd.DataFrame(columns=cols)
    piv = w.assign(day=pd.to_datetime(w["time"]).dt.normalize()).pivot_table(index="day", columns="site_id",
                                                                            values="z", aggfunc="last")
    rows = []
    for v in piv.columns:
        others = piv.drop(columns=v)
        d = (piv[v] - others.median(axis=1)).where(others.notna().sum(axis=1) >= cfg["PARCEL_MIN_AREA"]).dropna()
        for y, dy in d.groupby(d.index.year):
            n, lo, hi = len(dy), float((dy <= -1).mean()), float((dy >= 1).mean())
            ok = n >= cfg["PARCEL_FLAG_MIN_SCENES"]
            flag = "-" if ok and lo >= cfg["PARCEL_FLAG_SHARE"] else ("+" if ok and hi >= cfg["PARCEL_FLAG_SHARE"] else "")
            rows.append({"site_id": v, "year": int(y), "n": n, "share_low": lo, "share_high": hi,
                         "d_median": float(dy.median()), "flag": flag})
    return pd.DataFrame(rows, columns=cols)


def sensor_daily(cfg: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
    """
    Czujnik ISMN Condom 20 i 30 cm po regułach A4 (warianty W1 główny, W2, W3 = QC sprzed A4, W1_05WP, W1_015),
    w stałym okresie PARCEL_ISMN_PERIOD (§0). Dzień = średnia obu głębokości, tylko gdy obie mają wartość (jak W2+REF);
    censored / fast = którakolwiek głębokość cenzurowana / z flagą FAST_DROP.
    """
    from agriscreen import stations
    p0, p1 = cfg["PARCEL_ISMN_PERIOD"]
    ov = {"PROJECT_DIR": cfg["PROJECT_DIR"], "NETWORK": cfg["NETWORK"], "STATION": cfg["STATION"],
          "START_DATE": p0, "END_DATE": p1}
    v20, v30 = stations.a4_variants(0.20, ov), stations.a4_variants(0.30, ov)
    out = {}
    for var in SENSOR_VARIANTS:
        sm = pd.concat([v20[var]["sm"], v30[var]["sm"]], axis=1, sort=True)
        ok = sm.notna().all(axis=1)

        def either(col):
            return pd.concat([v20[var][col], v30[var][col]], axis=1, sort=True).fillna(False).astype(bool).any(axis=1)
        d = pd.DataFrame({"sm": sm.mean(axis=1).where(ok), "censored": either("censored").where(ok),
                          "fast": either("fast")})
        d.index = pd.DatetimeIndex(d.index).normalize()
        out[var] = d[~d.index.duplicated(keep="last")].loc[p0:p1]
    return out


def anomaly_daily(daily: pd.Series, cfg: Dict[str, Any]) -> pd.Series:
    """z dzienne wobec okresu PARCEL_ISMN_PERIOD (±CLIM_HALF_WINDOW_DAYS, min. 20 wartości w puli), obcięte do
    ±PARCEL_T3_CLIP (§6 pkt 2). Ta sama funkcja dla czujnika, ERA5-Land i SWI (wiersze opisowe)."""
    s = pd.Series(daily, dtype=float).dropna()
    if s.empty:
        return s
    s.index = pd.DatetimeIndex(s.index).normalize()
    s = s[~s.index.duplicated(keep="last")]
    z = metrics.clim_anomaly(s, tuple(cfg["PARCEL_ISMN_PERIOD"]), int(cfg["CLIM_HALF_WINDOW_DAYS"]), min_n=20)["z"]
    c = float(cfg["PARCEL_T3_CLIP"])
    return z.clip(-c, c)


def window_mean(daily: pd.Series, cfg: Dict[str, Any], include_t: bool = False) -> pd.Series:
    """Średnia z dni [t−30, t−1] (cel T3, §6 pkt 3) albo [t−30, t] (okno F4, §9), ważna przy ≥ PARCEL_T3_MIN_DAYS."""
    s = pd.Series(daily, dtype=float).dropna().sort_index()
    if s.empty:
        return s
    s = s[~s.index.duplicated(keep="last")].asfreq("D")
    n, k = int(cfg["PARCEL_T3_DAYS"]), int(cfg["PARCEL_T3_MIN_DAYS"])
    return s.rolling(n + 1, min_periods=k).mean() if include_t else s.rolling(n, min_periods=k).mean().shift(1)


def soil_pct(era5: pd.DataFrame, cfg: Dict[str, Any]) -> pd.Series:
    """Percentyl wilgotności ERA5-Land 0–100 cm wobec CLIM_REF (±CLIM_HALF_WINDOW_DAYS) — ta sama definicja co karta wody."""
    e = era5.set_index(pd.to_datetime(era5["time"]).dt.floor("D")).sort_index()
    e = e[~e.index.duplicated(keep="last")]
    return metrics.clim_anomaly(metrics.rootzone(e), cfg["CLIM_REF"], int(cfg["CLIM_HALF_WINDOW_DAYS"]))["percentile"]


def t1_rows(pa: pd.DataFrame, sites: List[str], cfg: Dict[str, Any], soil: Optional[pd.Series] = None,
            area: Optional[pd.DataFrame] = None) -> List[Dict[str, Any]]:
    """T1 (opisowo, reguła karty): udział z_woda ≤ −1 w VI–IX łącznie dla winnic z QC; oczekiwane 15,9% (§4)."""
    prod = f"{cfg['PARCEL_PRODUCT']}_WATER"
    months = cfg["PARCEL_TEST_MONTHS"]
    rows: List[Dict[str, Any]] = []

    def season(index):
        d = pa[(pa["index"] == index) & pa["site_id"].isin(sites)].dropna(subset=["z"])
        d = d[_in_months(d["time"], months)]
        return d.assign(year=pd.to_datetime(d["time"]).dt.year)

    def share(fn):
        return lambda d: float(fn(d["z"]).mean()) if len(d) else np.nan
    below = share(lambda z: z <= -1)
    w = season("water")
    p, lo, hi, _ = jackknife_ci(w, below, bounds=(0, 1))
    if not np.isfinite(lo):
        verdict = "za mało lat"
    elif lo <= P_BELOW <= hi:
        verdict = "nie wykryto grubego rozkalibrowania"
    else:
        verdict = f"klasa „poniżej” {'częściej' if lo > P_BELOW else 'rzadziej'} niż zakładane (1 na 6 scen)"
    rows.append(_row("T1", PARCELS, prod, "", f"winnice z QC ({len(sites)}), VI–IX", "share_z_le_-1", p, (lo, hi),
                     w["time"], n_parcels=len(sites), verdict=verdict, key="t1_main"))
    for metric, fn in (("share_z_ge_+1", lambda z: z >= 1), ("share_abs_z_ge_2", lambda z: z.abs() >= 2)):
        v, a, b, _ = jackknife_ci(w, share(fn), bounds=(0, 1))
        rows.append(_row("T1", PARCELS, prod, "", f"winnice z QC ({len(sites)}), VI–IX", metric, v, (a, b), w["time"],
                         n_parcels=len(sites)))
    for y, g in w.groupby("year"):
        rows.append(_row("T1", PARCELS, prod, "", f"rok {y}", "share_z_le_-1", below(g), days=g["time"],
                         n_parcels=g["site_id"].nunique()))
    nry = pd.to_numeric(w["n_ref_years"], errors="coerce")
    for label, m in (("1–2 lata w normie", nry < 3), ("≥ 3 lata w normie", nry >= 3)):
        v, a, b, _ = jackknife_ci(w[m], below, bounds=(0, 1))
        rows.append(_row("T1", PARCELS, prod, "", label, "share_z_le_-1", v, (a, b), w.loc[m, "time"]))
    nd = season("ndvi")
    v, a, b, _ = jackknife_ci(nd, below, bounds=(0, 1))
    rows.append(_row("T1", PARCELS, f"{cfg['PARCEL_PRODUCT']}_NDVI", "", "NDVI, winnice z QC, VI–IX", "share_z_le_-1",
                     v, (a, b), nd["time"], n_parcels=len(sites)))
    if soil is not None and len(soil):
        pct = pd.Series(soil).reindex(pd.to_datetime(w["time"]).dt.normalize()).to_numpy()
        m = (pct > 30) & (pct < 70)
        v, a, b, _ = jackknife_ci(w[m], below, bounds=(0, 1))
        rows.append(_row("T1", PARCELS, prod, "ERA5L_SM_RZ", "gleba w normie (percentyl 30–70; inne normy gleby i "
                         "roślinności sprzyjają niskiej wartości)", "share_z_le_-1", v, (a, b), w.loc[m, "time"]))
    if area is not None and len(area):
        ar = area[_in_months(pd.Series(area.index), months).to_numpy()]
        ar = pd.DataFrame({"z": ar["z_med"].to_numpy(), "time": ar.index, "year": ar.index.year})
        v, a, b, _ = jackknife_ci(ar, below, bounds=(0, 1))
        rows.append(_row("T1", AREA, prod, "", "mediana okolicy (zbiór T3)", "share_z_le_-1", v, (a, b), ar["time"]))
    return rows


def mdc95(d: Any) -> float:
    """Najmniejsza wykrywalna zmiana: 1,96·√(Σd²/n) (§5)."""
    d = np.asarray(d, float)
    return float(1.96 * np.sqrt(np.mean(d ** 2))) if len(d) else np.nan


def scene_pairs(pa: pd.DataFrame, sites: List[str], index: str, precip: pd.Series,
                cfg: Dict[str, Any]) -> pd.DataFrame:
    """Pary scen tej samej winnicy (§5): G5 = ten sam tor, Δt 4–6 dni; G13 = różne tory, Δt 1–3 dni; opad od t1 do t2."""
    cols = ["site_id", "t1", "t2", "dt", "group", "d", "dv", "rain", "same_ref", "year"]
    d = pa[(pa["index"] == index) & pa["site_id"].isin(sites)].dropna(subset=["z"])
    d = d[_in_months(d["time"], cfg["PARCEL_TEST_MONTHS"])]
    p = pd.Series(precip, dtype=float)
    p.index = pd.DatetimeIndex(p.index)
    p = p.sort_index()
    rows = []
    for site, g in d.groupby("site_id"):
        g = g.sort_values("time")
        day = pd.to_datetime(g["time"]).dt.normalize().to_numpy()
        z, v = g["z"].to_numpy(float), pd.to_numeric(g["value"], errors="coerce").to_numpy(float)
        trk, ref = g["track"].to_numpy(), g["ref_mode"].astype(str).to_numpy()
        for i in range(len(g)):
            for j in range(i + 1, len(g)):
                dt = int((day[j] - day[i]) / np.timedelta64(1, "D"))
                if dt > 6:
                    break
                same = trk[i] == trk[j]
                grp = "G5" if same and 4 <= dt <= 6 else ("G13" if not same and 1 <= dt <= 3 else None)
                if grp is None:
                    continue
                rows.append({"site_id": site, "t1": day[i], "t2": day[j], "dt": dt, "group": grp, "d": z[j] - z[i],
                             "dv": v[j] - v[i], "rain": float(p.loc[day[i]:day[j]].sum()),
                             "same_ref": ref[i] == "same_track" and ref[j] == "same_track",
                             "year": pd.Timestamp(day[i]).year})
    return pd.DataFrame(rows, columns=cols)


def t2_rows(pa: pd.DataFrame, sites: List[str], precip: pd.Series, cfg: Dict[str, Any],
            min_pairs: int = 30) -> List[Dict[str, Any]]:
    """T2 (opisowo, reguła karty): MDC95 z par bez opadu, oba końce z normą z tego samego toru (§5)."""
    rows: List[Dict[str, Any]] = []
    for index in ("water", "ndmi", "crswir", "ndvi", "ndre"):
        prod = f"{cfg['PARCEL_PRODUCT']}_{index.upper()}"
        pr = scene_pairs(pa, sites, index, precip, cfg)
        dry = pr[(pr["rain"] < cfg["PARCEL_RAIN_MM"]) & pr["same_ref"]]
        wet = pr[pr["rain"] >= cfg["PARCEL_RAIN_MM"]]
        for grp in ("G5", "G13"):
            label = "ten sam tor, 4–6 dni" if grp == "G5" else "różne tory, 1–3 dni"
            sub = dry[dry["group"] == grp]
            key = f"t2_{grp.lower()}" if index == "water" else ""
            if len(sub) < min_pairs:
                rows.append(_row("T2", PARCELS, prod, "", f"{grp} ({label}), bez opadu", "mdc95_z", np.nan, days=sub["t1"],
                                 verdict="za mało par", key=key))
            else:
                m, lo, hi, _ = jackknife_ci(sub, lambda q: mdc95(q["d"]), bounds=(0, np.inf))
                rows.append(_row("T2", PARCELS, prod, "", f"{grp} ({label}), bez opadu", "mdc95_z", m, (lo, hi),
                                 sub["t1"], n_parcels=sub["site_id"].nunique(), key=key))
                if index != "water":
                    m, lo, hi, _ = jackknife_ci(sub, lambda q: mdc95(q["dv"]), bounds=(0, np.inf))
                    rows.append(_row("T2", PARCELS, prod, "", f"{grp} ({label}), bez opadu", "mdc95_value", m, (lo, hi),
                                     sub["t1"]))
            if index == "water":
                ws = wet[wet["group"] == grp]
                rows.append(_row("T2", PARCELS, prod, "", f"{grp} ({label}), z opadem ≥ {cfg['PARCEL_RAIN_MM']:g} mm",
                                 "mdc95_z", mdc95(ws["d"]) if len(ws) >= min_pairs else np.nan, days=ws["t1"],
                                 verdict="" if len(ws) >= min_pairs else "za mało par"))
    return rows


def t3_frame(x: pd.Series, y: pd.Series, cfg: Dict[str, Any]) -> pd.DataFrame:
    """Dni scen VI–IX w PARCEL_T3_YEARS z ważnym predyktorem x i celem y (§6)."""
    d = pd.DataFrame({"x": pd.Series(x, dtype=float), "y": pd.Series(y, dtype=float)}).dropna()
    t = pd.DatetimeIndex(d.index)
    y0, y1 = cfg["PARCEL_T3_YEARS"]
    m0, m1 = cfg["PARCEL_TEST_MONTHS"]
    d = d[(t.month >= m0) & (t.month <= m1) & (t.year >= y0) & (t.year <= y1)]
    return d.assign(year=pd.DatetimeIndex(d.index).year)


def rho_row(x: pd.Series, y: pd.Series, cfg: Dict[str, Any], product: str, reference: str, subset: str,
            seg: str = "T3", key: str = "", days: Optional[pd.Index] = None) -> Dict[str, Any]:
    """Wiersz opisowy: ρ Spearmana łącznie dla lat z przedziałem jackknife (§6); `days` = dni wiersza głównego T3
    (te same dni dla wszystkich wierszy opisowych; wariant celu bez wartości w danym dniu ten dzień pomija)."""
    d = t3_frame(x, y, cfg)
    if days is not None:
        d = d[d.index.isin(days)]
    r, lo, hi, _ = jackknife_ci(d, lambda q: spearman(q["x"], q["y"]), bounds=(-1, 1))
    return _row(seg, AREA, product, reference, subset, "spearman_rho", r, (lo, hi), d.index, key=key)


def t3_main(x: pd.Series, y: pd.Series, cfg: Dict[str, Any], product: str, reference: str, subset: str,
            n_parcels: int) -> Tuple[List[Dict[str, Any]], bool]:
    """Kryterium zdania 3 (§6): dolna granica przedziału jackknife ρ > 0; < 5 sezonów z ≥ 5 dniami = nierozstrzygnięty."""
    d = t3_frame(x, y, cfg)
    seasons = int((d.groupby("year").size() >= 5).sum()) if len(d) else 0
    r, lo, hi, loo = jackknife_ci(d, lambda q: spearman(q["x"], q["y"]), bounds=(-1, 1))
    if seasons < 5:
        passed, verdict = False, f"nierozstrzygnięty: tylko {seasons} sezonów z ≥ 5 dniami"
    else:
        passed = bool(np.isfinite(lo) and lo > 0)
        verdict = "spełnione" if passed else "niespełnione (nierozstrzygnięty)"
        if passed and any(v <= 0 for v in loo.values()):
            verdict += "; wynik zależy od jednego roku"
    rows = [_row("T3", AREA, product, reference, subset, "spearman_rho", r, (lo, hi), d.index, n_parcels=n_parcels,
                 criterion=True, verdict=verdict, key="t3_main")]
    for yr, v in loo.items():
        rows.append(_row("T3", AREA, product, reference, f"{subset}, bez roku {yr}", "spearman_rho", v,
                         days=d.index[d["year"] != yr]))
    if len(d):
        dm = d.copy()
        dm[["x", "y"]] = d[["x", "y"]] - d.groupby("year")[["x", "y"]].transform("mean")
        rw, a, b, _ = jackknife_ci(dm, lambda q: spearman(q["x"], q["y"]), bounds=(-1, 1))
        rows.append(_row("T3", AREA, product, reference, f"{subset}, wewnątrz roku", "spearman_rho", rw, (a, b), d.index))
        means = d.groupby("year")[["x", "y"]].mean()
        rows.append(_row("T3", AREA, product, reference, f"{subset}, średnie sezonów", "spearman_rho",
                         spearman(means["x"], means["y"]), days=d.index, n=len(means)))
    return rows, passed


def multiband_loyo(X: pd.DataFrame, y: pd.Series, years: pd.Series,
                   min_train: int = 30) -> Tuple[pd.Series, pd.DataFrame]:
    """
    OLS y = β0 + Σ βb·x_b uczony kolejno bez każdego roku; wynik roku pominiętego s⁽⁻ᵍ⁾ = Σ βb⁽⁻ᵍ⁾·x_b BEZ β0,
    podzielony przez SD tej sumy na dniach uczących (§7). β0 foldu jest ujemnie związany ze średnią roku pominiętego,
    więc nie wchodzi do oceny. Zwraca predykcje i wagi z każdego foldu.
    """
    X, y, years = X.astype(float), pd.Series(y, dtype=float), pd.Series(years)
    s = pd.Series(np.nan, index=X.index)
    w_rows = []
    for g in sorted(pd.unique(years)):
        tr, te = (years != g).to_numpy(), (years == g).to_numpy()
        if tr.sum() < min_train or te.sum() == 0:
            continue
        A = np.column_stack([np.ones(tr.sum()), X.to_numpy()[tr]])
        beta = np.linalg.lstsq(A, y.to_numpy()[tr], rcond=None)[0]
        sd = float((X.to_numpy()[tr] @ beta[1:]).std(ddof=1))
        if not sd > 0:
            continue
        s[te] = X.to_numpy()[te] @ beta[1:] / sd
        w_rows.append({"year_out": int(g), "b0": beta[0], **{c: b for c, b in zip(X.columns, beta[1:])}})
    return s, pd.DataFrame(w_rows)


def multiband_rows(X: pd.DataFrame, y: pd.Series, x_simple: pd.Series, cfg: Dict[str, Any],
                   n_parcels: int) -> List[Dict[str, Any]]:
    """
    Ocena §7 na dniach T3: ρ_multi (s⁽⁻ᵍ⁾ z walidacji bez roku) i ρ_prosty (mediana z_woda) na tych samych dniach,
    Δρ z przedziałem jackknife (predykcje stałe). Przyjęcie: dolna granica Δρ > 0. Gdy przyjęty — wagi z lat
    PARCEL_T3_YEARS i średnia / SD wyniku okolicy do karty (zdanie 3, wariant A).
    """
    prod = f"{cfg['PARCEL_PRODUCT']}_MB"
    ref = "ISMN_20_30cm_A4W1"
    d = t3_frame(x_simple, y, cfg).join(X, how="inner").dropna()
    rows: List[Dict[str, Any]] = []
    if len(d) < 30 or d["year"].nunique() < 3:
        rows.append(_row("P7", AREA, prod, ref, "Δρ = ρ_multi − ρ_prosty", "delta_rho", np.nan, days=d.index,
                         criterion=True, verdict="nierozstrzygnięty: za mało dni", key="p7_accept"))
        return rows
    s, wts = multiband_loyo(d[list(X.columns)], d["y"], d["year"])
    d = d.assign(s=s).dropna(subset=["s"])

    def delta(q):
        return spearman(q["s"], q["y"]) - spearman(q["x"], q["y"])
    dr, lo, hi, loo = jackknife_ci(d, delta, bounds=(-2, 2))
    accepted = bool(np.isfinite(lo) and lo > 0)
    rows.append(_row("P7", AREA, prod, ref, "Δρ = ρ_multi − ρ_prosty", "delta_rho", dr, (lo, hi), d.index,
                     n_parcels=n_parcels, criterion=True, verdict="przyjęty" if accepted else "nieprzyjęty",
                     key="p7_accept"))
    rm, a, b, _ = jackknife_ci(d, lambda q: spearman(q["s"], q["y"]), bounds=(-1, 1))
    rows.append(_row("P7", AREA, prod, ref, "ρ_multi (lata niewidziane przez model)", "spearman_rho", rm, (a, b),
                     d.index, n_parcels=n_parcels, verdict=("zdanie 3: tak" if accepted and np.isfinite(a) and a > 0
                                                            else "zdanie 3: nie"), key="p7_rho_multi"))
    rp, a, b, _ = jackknife_ci(d, lambda q: spearman(q["x"], q["y"]), bounds=(-1, 1))
    rows.append(_row("P7", AREA, f"{cfg['PARCEL_PRODUCT']}_WATER", ref, "ρ_prosty (te same dni)", "spearman_rho", rp,
                     (a, b), d.index))
    for yr, g in d.groupby("year"):
        rows.append(_row("P7", AREA, prod, ref, f"rok testowy {yr}", "spearman_rho", spearman(g["s"], g["y"]),
                         days=g.index))
    for r in wts.itertuples(index=False):
        for c in X.columns:
            rows.append(_row("P7", AREA, prod, ref, f"wagi bez roku {r.year_out}", f"weight_{c}", getattr(r, c),
                             days=d.index))
    cx = d[list(X.columns)].corr()
    for i, a_ in enumerate(X.columns):
        for b_ in X.columns[i + 1:]:
            rows.append(_row("P7", AREA, prod, "", f"korelacja cech {a_}–{b_}", "pearson_r", cx.loc[a_, b_],
                             days=d.index))
    if accepted:
        A = np.column_stack([np.ones(len(d)), d[list(X.columns)].to_numpy()])
        beta = np.linalg.lstsq(A, d["y"].to_numpy(), rcond=None)[0]
        sa = d[list(X.columns)].to_numpy() @ beta[1:]
        for c, b_ in zip(X.columns, beta[1:]):
            rows.append(_row("P7", AREA, prod, ref, "wagi końcowe (zamrożone)", f"weight_{c}", b_, days=d.index,
                             key=f"p7_w_{c}"))
        rows.append(_row("P7", AREA, prod, ref, "wynik okolicy: średnia", "mb_mean", sa.mean(), days=d.index,
                         key="p7_mean"))
        rows.append(_row("P7", AREA, prod, ref, "wynik okolicy: SD", "mb_sd", sa.std(ddof=1), days=d.index,
                         key="p7_sd"))
    return rows


def multiband_area(X: pd.DataFrame, summ: Dict[str, Any]) -> pd.Series:
    """z_mb okolicy (§7, wariant A) z zamrożonych wag: (Σ βb·x_b − średnia) / SD; pusta seria, gdy wariant nieprzyjęty."""
    p7 = (summ or {}).get("p7") or {}
    w = p7.get("weights") or {}
    if not p7.get("accepted") or not w or not np.isfinite(_f(p7.get("sd"))) or X.empty:
        return pd.Series(dtype=float)
    cols = [c for c in w if c in X.columns]
    if len(cols) != len(w):
        return pd.Series(dtype=float)
    s = X[cols].astype(float) @ np.array([w[c] for c in cols])
    return (s - p7["mean"]) / p7["sd"]


def _by_day(pa: pd.DataFrame, site: str, index: str, sign: float = 1.0) -> pd.Series:
    d = pa[(pa["site_id"] == site) & (pa["index"] == index)].dropna(subset=["z"])
    return pd.Series(sign * d["z"].to_numpy(float), index=pd.to_datetime(d["time"]).dt.normalize()).groupby(level=0).last()


def before_rows(pa: pd.DataFrame, veg_sr: Optional[pd.DataFrame], f4: Optional[pd.DataFrame],
                sensor_z: Dict[str, pd.Series], area_ndmi: pd.Series, area_crswir: pd.Series, area_ndvi: pd.Series,
                cfg: Dict[str, Any], site: str = "VINEYARD_06") -> List[Dict[str, Any]]:
    """
    Drabinka P4 (§9) na wspólnych dniach IV–X 2018–2024: a — z_NDMI z F4 + czujnik W3; b — norma przyczynowa SR 2,5 m
    (veg_anomalies.csv) + W3; c — jak b + A4 W1; d — S2_10m_buf20 + W1. R Pearsona z przedziałem z bloków 30 dni (jak F4).
    P1, P2, P3, P5 w konfiguracji d dla VINEYARD_06 i mediany zbioru T3. Bez kryteriów.
    """
    from agriscreen import stations
    y0, y1 = cfg["PARCEL_T3_YEARS"]
    y = {v: window_mean(sensor_z[v], cfg, include_t=True) for v in ("W3", "W1") if v in sensor_z}
    xs: Dict[str, pd.Series] = {"d": _by_day(pa, site, "ndmi")}
    if f4 is not None and len(f4) and "V3a_ndmi_scene" in f4:
        xs["a"] = pd.Series(f4["V3a_ndmi_scene"].to_numpy(float),
                            index=pd.to_datetime(f4.iloc[:, 0]).dt.normalize()).dropna().groupby(level=0).last()
    if veg_sr is not None and len(veg_sr):
        v = veg_sr[(veg_sr["site_id"] == site) & (veg_sr["product"] == "S2SR_2.5m") & (veg_sr["index"] == "ndmi")]
        v = v.dropna(subset=["z"])
        xs["b"] = pd.Series(v["z"].to_numpy(float), index=pd.to_datetime(v["time"]).dt.normalize()).groupby(level=0).last()
    steps = (("a", "a", "W3", "z_NDMI z F4 (SR 2,5 m, norma „pozostałe lata”)", "F4_S2SR_2.5m_NDMI"),
             ("b", "b", "W3", "norma przyczynowa, SR 2,5 m", "S2SR_2.5m_NDMI"),
             ("c", "b", "W1", "jak b, czujnik po A4", "S2SR_2.5m_NDMI"),
             ("d", "d", "W1", "S2_10m_buf20, czujnik po A4", f"{cfg['PARCEL_PRODUCT']}_NDMI"))
    frame = pd.DataFrame({k: v for k, v in xs.items()})
    for v, s in y.items():
        frame[f"y_{v}"] = s
    t = pd.DatetimeIndex(frame.index)
    m0, m1 = cfg["S2_MONTHS"]
    frame = frame[(t.month >= m0) & (t.month <= m1) & (t.year >= y0) & (t.year <= y1)].dropna()
    rows: List[Dict[str, Any]] = []
    for step, xk, yv, label, prod in steps:
        if xk not in frame or f"y_{yv}" not in frame:
            rows.append(_row("P9", site, prod, f"ISMN_20_30cm_A4{yv}", f"P4 krok {step}: {label}", "pearson_r", np.nan,
                             verdict="brak danych"))
            continue
        r, lo, hi = stations._r_with_ci(pd.Series(frame.index), frame[xk].to_numpy(), frame[f"y_{yv}"].to_numpy(), cfg)
        rows.append(_row("P9", site, prod, f"ISMN_20_30cm_A4{yv}", f"P4 krok {step}: {label}", "pearson_r", r, (lo, hi),
                         frame.index))
    zw1 = sensor_z.get("W1", pd.Series(dtype=float))
    yw1 = y.get("W1", pd.Series(dtype=float))
    subjects = ((site, _by_day(pa, site, "ndmi"), _by_day(pa, site, "crswir", -1.0), _by_day(pa, site, "ndvi")),
                (AREA, area_ndmi, area_crswir, area_ndvi))
    prod = f"{cfg['PARCEL_PRODUCT']}_NDMI"
    for who, ndmi, ncr, ndvi in subjects:
        def keep(s):
            t_ = pd.DatetimeIndex(s.index)
            return s[(t_.month >= m0) & (t_.month <= m1) & (t_.year >= y0) & (t_.year <= y1)]
        for name, other in (("P1 r z_NDMI i −z_CRSWIR", ncr), ("P2 r z_NDMI i z_NDVI", ndvi)):
            q = pd.concat([ndmi, other], axis=1, sort=True).dropna()
            q = keep(q)
            rows.append(_row("P9", who, prod, "", name, "pearson_r", pearson(q.iloc[:, 0], q.iloc[:, 1]), days=q.index))
        for name, target in (("P3 R wobec z czujnika z dnia sceny", zw1), ("P4 R wobec średniej [t−30, t]", yw1)):
            q = keep(pd.concat([ndmi, target], axis=1, sort=True).dropna())
            r, lo, hi = stations._r_with_ci(pd.Series(q.index), q.iloc[:, 0].to_numpy(), q.iloc[:, 1].to_numpy(), cfg) \
                if len(q) else (np.nan, np.nan, np.nan)
            rows.append(_row("P9", who, prod, "ISMN_20_30cm_A4W1", name, "pearson_r", r, (lo, hi), q.index))
        q = keep(pd.concat([ndmi, yw1], axis=1, sort=True).dropna())
        if len(q):
            q.columns = ["x", "y"]
            yr = pd.DatetimeIndex(q.index).year
            dm = q - q.groupby(yr).transform("mean")
            r, lo, hi = stations._r_with_ci(pd.Series(dm.index), dm["x"].to_numpy(), dm["y"].to_numpy(), cfg)
            rows.append(_row("P9", who, prod, "ISMN_20_30cm_A4W1", "P5 R wewnątrz roku", "pearson_r", r, (lo, hi), q.index))
            mm = q.groupby(yr).mean()
            rows.append(_row("P9", who, prod, "ISMN_20_30cm_A4W1", "P5 R średnich sezonów", "pearson_r",
                             pearson(mm["x"], mm["y"]), days=q.index, n=len(mm)))
    return rows


def qc_rows(pa: pd.DataFrame, n_dup: int, flags: pd.DataFrame, x_t3: pd.Series, t3_days: pd.Index,
            sensor: Dict[str, pd.DataFrame], cfg: Dict[str, Any],
            counts: Optional[pd.DataFrame] = None) -> List[Dict[str, Any]]:
    """
    Kontrola jakości (§11 pkt 5): na działkę — piksele, sceny przyjęte i odrzucone, normy (n_ref, ref_mode, lata w puli),
    flagi; łącznie — dni z 2 scenami, zgodność toru; czujnik — dni cenzurowane i FAST_DROP w oknach [t−30, t−1] dni T3;
    r(mediana zbioru T3, VINEYARD_06) w dniach T3. counts: sceny na działkę (n_scenes, n_clear) z obserwacji ≤ zamrożenia.
    """
    prod = f"{cfg['PARCEL_PRODUCT']}_WATER"
    ok = qc_sites(pa)
    w = pa[(pa["index"] == "water") & pa["site_id"].isin(ok)].dropna(subset=["z"])
    w = w[_in_months(w["time"], cfg["PARCEL_TEST_MONTHS"])]
    day = pd.to_datetime(w["time"]).dt.normalize()
    rows = [_row("QC", PARCELS, prod, "", "dni z 2 scenami działki (zostaje scena z większym clear_frac)", "count",
                 n_dup, n=n_dup)]
    if len(w):
        tr = w.groupby(day)["track"].nunique()
        rows.append(_row("QC", PARCELS, prod, "", "dni z różnym torem między działkami", "share", float((tr > 1).mean()),
                         days=tr.index))
        rows.append(_row("QC", PARCELS, prod, "", "norma z tego samego toru", "share",
                         float((w["ref_mode"] == "same_track").mean()), days=w["time"]))
        rows.append(_row("QC", PARCELS, prod, "", "norma z < 3 lat", "share",
                         float((pd.to_numeric(w["n_ref_years"], errors="coerce") < 3).mean()), days=w["time"]))
    for site, g in pa[pa["index"] == "water"].groupby("site_id"):
        t = g["time"]
        rows.append(_row("QC", site, prod, "", "piksele 10 m w zwężonym obrysie", "n_pixels",
                         pd.to_numeric(g["n_pixels"], errors="coerce").max(), days=t))
        if counts is not None and site in counts.index:
            rows.append(_row("QC", site, prod, "", "sceny ≤ zamrożenia (IV–X)", "count", counts.loc[site, "n_scenes"], days=t))
            rows.append(_row("QC", site, prod, "", "sceny przyjęte (≥ 90% pikseli czystych)", "count",
                             counts.loc[site, "n_clear"], days=t))
        rows.append(_row("QC", site, prod, "", "sceny z z_woda (IV–X)", "count", g["z"].notna().sum(), days=t))
        rows.append(_row("QC", site, prod, "", "mediana n_ref", "median", pd.to_numeric(g["n_ref"], errors="coerce").median(),
                         days=t))
        rows.append(_row("QC", site, prod, "", "norma z tego samego toru", "share",
                         float((g["ref_mode"] == "same_track").mean()) if len(g) else np.nan, days=t))
        rows.append(_row("QC", site, prod, "", "mediana lat w normie", "median",
                         pd.to_numeric(g["n_ref_years"], errors="coerce").median(), days=t))
        nf = int(flags.loc[flags["site_id"] == site, "flag"].astype(str).isin(["-", "+"]).sum()) if len(flags) else 0
        rows.append(_row("QC", site, prod, "", "sezony z flagą zmiany gospodarowania", "count", nf, n=nf))
    if len(flags):
        f = flags[flags["flag"].astype(str).isin(["-", "+"])]
        rows.append(_row("QC", PARCELS, prod, "", "sezony z flagą zmiany gospodarowania", "count", len(f), n=len(f)))
    v06 = _by_day(pa, "VINEYARD_06", "water")
    q = t3_frame(x_t3, v06, cfg)
    q = q[q.index.isin(t3_days)]
    rows.append(_row("QC", AREA, prod, "", "r(mediana zbioru T3, z_woda VINEYARD_06), dni T3", "pearson_r",
                     pearson(q["x"], q["y"]), days=q.index))
    s = sensor.get("W1")
    if s is not None and len(s) and len(t3_days):
        win = pd.DatetimeIndex(sorted({d - pd.Timedelta(days=k) for d in pd.DatetimeIndex(t3_days)
                                       for k in range(1, int(cfg["PARCEL_T3_DAYS"]) + 1)}))
        sel = s.reindex(win)
        valid = sel["sm"].notna()
        rows.append(_row("QC", AREA, "ISMN_20_30cm", "ISMN_20_30cm_A4W1", "dni cenzurowane czujnika w oknach T3",
                         "count", int(_bool(sel["censored"].fillna(False)).sum()), days=sel.index[valid]))
        rows.append(_row("QC", AREA, "ISMN_20_30cm", "ISMN_20_30cm_A4W1", "dni FAST_DROP czujnika w oknach T3", "count",
                         int(_bool(sel["fast"].fillna(False)).sum()), days=win))
    return rows


def protocol_sha(path: str) -> Dict[str, str]:
    """SHA-256 sekcji 0–13 protokołu (jak `sed -n '/^## 0\\./,$p' plik | sha256sum`) i skrót zapisany przy rejestracji."""
    if not os.path.exists(path):
        return {"sha256": "", "registered": "", "status": "brak pliku protokołu"}
    txt = open(path, encoding="utf-8").read()
    m = re.search(r"^## 0\.", txt, flags=re.M)
    body = txt[m.start():] if m else txt
    reg = re.search(r"SHA-256[^`\n]*`([0-9a-f]{64})`", txt[:m.start()] if m else "")
    status = re.search(r"\*\*Status:\*\*\s*`([A-Z]+)", txt)
    return {"sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(), "registered": reg.group(1) if reg else "",
            "status": status.group(1) if status else ""}


def freeze_info(cfg: Dict[str, Any], out_dir: str) -> Dict[str, Any]:
    """
    Zamrożenie testów (§0, U6): W3B_FREEZE z konfiguracji albo data ostatniej sceny w S2_DIR przy pierwszym liczeniu
    testów (zapis w w3b_freeze.json razem z SHA-256 listy plików). Lista scen ≤ zamrożenia jest sprawdzana co bieg.
    """
    path = os.path.join(out_dir, "w3b_freeze.json")
    names = sorted(os.path.basename(p) for p in glob.glob(os.path.join(cfg["S2_DIR"], "S2_L2A_*.tif")))
    if not names:
        raise RuntimeError("Brak scen w S2_DIR — najpierw task_ingest_s2 i task_parcel_stats.")
    saved = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else None
    if cfg.get("W3B_FREEZE"):
        freeze, source = str(cfg["W3B_FREEZE"])[:10], "konfiguracja"
    elif saved:
        freeze, source = saved["freeze"], "w3b_freeze.json"
    else:
        freeze, source = f"{metrics.scene_time(names[-1]):%Y-%m-%d}", "ostatnia scena przy pierwszym liczeniu testów"
    frozen = [n for n in names if metrics.scene_time(n).normalize() <= pd.Timestamp(freeze)]
    sha = hashlib.sha256("\n".join(frozen).encode("utf-8")).hexdigest()
    info = {"freeze": freeze, "source": source, "n_scenes": len(frozen),
            "first": f"{metrics.scene_time(frozen[0]):%Y-%m-%d}" if frozen else "",
            "last": f"{metrics.scene_time(frozen[-1]):%Y-%m-%d}" if frozen else "", "scenes_sha256": sha,
            "scenes_sha256_at_freeze": (saved or {}).get("scenes_sha256", sha)}
    if saved is None and not cfg.get("W3B_FREEZE"):
        os.makedirs(out_dir, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(dict(info, created_utc=pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%dT%H:%M:%SZ")), f, indent=1)
    return info


def run_tests(pa: pd.DataFrame, n_dup: int, sensor: Dict[str, pd.DataFrame], era5: pd.DataFrame,
              swi: Optional[pd.DataFrame], veg_sr: Optional[pd.DataFrame], f4: Optional[pd.DataFrame],
              cfg: Dict[str, Any], counts: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """
    Wszystkie wiersze §4–§9 i QC na anomaliach scen ≤ W3B_FREEZE. Kryteria: T3 (key t3_main) i §7 (key p7_accept).
    Wiersze opisowe T3 liczone na dniach wiersza głównego. Zwraca tabelę TEST_COLS (wiersze gwl_validation_metrics
    + kryterium, werdykt, klucz).
    """
    prod = cfg["PARCEL_PRODUCT"]
    ok, t3s = qc_sites(pa), t3_sites(pa, cfg)
    mn = int(cfg["PARCEL_MIN_AREA"])
    area = {i: area_series(pa, i, t3s, mn) for i in ("water", "ndmi", "crswir", "ndvi")}
    x = area["water"]["z_med"]
    zs = {v: anomaly_daily(sensor[v]["sm"], cfg) for v in sensor}
    y = {v: window_mean(z, cfg) for v, z in zs.items()}
    e = era5.set_index(pd.to_datetime(era5["time"]).dt.floor("D")).sort_index()
    e = e[~e.index.duplicated(keep="last")]
    rows = t1_rows(pa, ok, cfg, soil_pct(era5, cfg), area["water"])
    rows += t2_rows(pa, ok, e["precip_mm"] if "precip_mm" in e else pd.Series(dtype=float), cfg)
    ref = "ISMN_20_30cm_A4W1"
    main, _ = t3_main(x, y["W1"], cfg, f"{prod}_WATER", ref, f"mediana {len(t3s)} winnic z QC bez VINEYARD_06",
                      len(t3s))
    rows += main
    days = t3_frame(x, y["W1"], cfg).index           # dni wiersza głównego T3: te same dla wierszy opisowych (§6)
    for v in ("W2", "W3", "W1_05WP", "W1_015"):
        if v in y:
            rows.append(rho_row(x, y[v], cfg, f"{prod}_WATER", f"ISMN_20_30cm_A4{v}", "wariant celu", days=days))
    rows.append(rho_row(x, window_mean(anomaly_daily(metrics.rootzone(e), cfg), cfg), cfg, f"{prod}_WATER", "ERA5L_SM_RZ",
                        "ERA5-Land 0–100 cm zamiast czujnika", days=days))
    T = int(cfg.get("SWI_T", 15))
    if swi is not None and len(swi) and f"swi{T:03d}" in swi:
        sw = pd.Series(swi[f"swi{T:03d}"].to_numpy(float), index=pd.to_datetime(swi["date"]).dt.floor("D"))
        rows.append(rho_row(x, window_mean(anomaly_daily(sw, cfg), cfg), cfg, f"{prod}_WATER", f"SWI_v4_T{T:03d}",
                            "SWI zamiast czujnika", days=days))
    cens = window_mean(sensor["W1"]["censored"].astype(float), cfg)
    rows.append(rho_row(x, cens, cfg, f"{prod}_WATER", "ISMN_20_30cm_A4W1_censored",
                        "kontrola: udział dni cenzurowanych w oknie", days=days))
    raw_x = area_series(pa, "ndmi", t3s, mn, col="value")["z_med"]
    rows.append(rho_row(raw_x, window_mean(sensor["W1"]["sm"], cfg), cfg, f"{prod}_NDMI_RAW", "ISMN_20_30cm_A4W1_RAW",
                        "wartości surowe (z cyklem sezonowym)", days=days))
    for idx in ("ndvi", "ndmi", "crswir"):
        rows.append(rho_row(area[idx]["z_med"], y["W1"], cfg, f"{prod}_{idx.upper()}", ref,
                            f"predyktor {'−' if idx == 'crswir' else ''}{idx.upper()}", days=days))
    rows.append(rho_row(area_series(pa, "water", ok, mn)["z_med"], y["W1"], cfg, f"{prod}_WATER", ref,
                        "zbiór z VINEYARD_06", days=days))
    X = band_features(pa, t3s, tuple(b.lower() for b in cfg["PARCEL_BANDS"]), mn)
    rows += multiband_rows(X, y["W1"], x, cfg, len(t3s))
    flags = management_flags(pa, ok, cfg)
    rows += before_rows(pa, veg_sr, f4, zs, area["ndmi"]["z_med"], area["crswir"]["z_med"], area["ndvi"]["z_med"], cfg)
    rows += qc_rows(pa, n_dup, flags, x, days, sensor, cfg, counts)
    return pd.DataFrame(rows, columns=TEST_COLS)


def tests_summary(tests: Optional[pd.DataFrame]) -> Optional[Dict[str, Any]]:
    """Liczby dla karty i raportu z w3b_tests.csv (wiersze z kluczem): T1, MDC95, T3, §7. None bez testów."""
    if tests is None or not len(tests) or "key" not in tests:
        return None
    k = tests.set_index(tests["key"].fillna("").astype(str))

    def get(key):
        if key not in k.index:
            return None
        r = k.loc[key]
        r = r.iloc[0] if isinstance(r, pd.DataFrame) else r
        n = _f(r["n"])
        return {"value": _f(r["value"]), "lo": _f(r["ci_low"]), "hi": _f(r["ci_high"]), "n": int(n) if np.isfinite(n) else 0,
                "period": str(r["period"]) if pd.notna(r["period"]) else "", "verdict": str(r["verdict"])
                if pd.notna(r["verdict"]) else ""}
    t3, acc, rm = get("t3_main"), get("p7_accept"), get("p7_rho_multi")
    accepted = bool(acc and acc["verdict"] == "przyjęty")
    weights = {key[5:]: get(key)["value"] for key in k.index if key.startswith("p7_w_")}
    first = tests.iloc[0]
    return {"t1": get("t1_main"), "mdc": {"G5": get("t2_g5"), "G13": get("t2_g13")},
            "t3": dict(t3, passed=t3["verdict"].startswith("spełnione")) if t3 else None,
            "p7": {"accepted": accepted, "delta": acc, "rho_multi": rm,
                   "passed_multi": bool(accepted and rm and np.isfinite(rm["lo"]) and rm["lo"] > 0),
                   "weights": weights, "mean": (get("p7_mean") or {}).get("value", np.nan),
                   "sd": (get("p7_sd") or {}).get("value", np.nan)},
            "protocol_sha256": str(first.get("protocol_sha256", "")), "freeze": str(first.get("freeze", "")),
            "code_commit": str(first.get("code_commit", ""))}


def _selftest(cfg: Dict[str, Any]) -> None:
    """Testy jednostkowe funkcji W3b na danych syntetycznych (stałe ziarno) i na prawdziwym czujniku ISMN z repo."""
    from scipy import stats
    rng = np.random.default_rng(42)
    # jackknife: ręcznie policzony przykład i brak przedziału przy < 3 latach
    df = pd.DataFrame({"year": [1, 1, 2, 2, 3, 3, 4, 4], "v": [1.0, 2, 2, 4, 3, 5, 4, 8]})
    est, lo, hi, loo = jackknife_ci(df, lambda d: d["v"].mean())
    v = np.array([np.mean([2, 4, 3, 5, 4, 8]), np.mean([1, 2, 3, 5, 4, 8]), np.mean([1, 2, 2, 4, 4, 8]),
                  np.mean([1, 2, 2, 4, 3, 5])])
    se = np.sqrt(3 / 4 * np.sum((v - v.mean()) ** 2))
    assert abs(est - 3.625) < 1e-12 and abs(hi - (3.625 + stats.t.ppf(0.975, 3) * se)) < 1e-9, (est, lo, hi)
    assert np.isnan(jackknife_ci(df[df["year"] <= 2], lambda d: d["v"].mean())[1])
    # T1: z ~ N(0,1) w 9 sezonach -> przedział obejmuje 15,9%
    scenes = [d for y in range(2018, 2027) for d in pd.date_range(f"{y}-06-01", periods=25, freq="4D")]
    pa1 = pd.DataFrame([{"site_id": f"V{i:02d}", "time": d} for d in scenes for i in range(13)])
    pa1 = pa1.assign(index="water", z=rng.standard_normal(len(pa1)), n_ref_years=5, qc_ok=True)
    r1 = {r["metric"]: r for r in t1_rows(pa1, sorted(pa1["site_id"].unique()), cfg) if r["subset"].startswith("winnice")}
    t1 = r1["share_z_le_-1"]
    assert t1["ci_low"] <= P_BELOW <= t1["ci_high"] and t1["verdict"] == "nie wykryto grubego rozkalibrowania", t1
    # T2: bez par -> NaN i „za mało par”; szum σ -> MDC95 ≈ 1,96·√2·σ
    pa2 = pd.DataFrame({"site_id": "V", "index": "water", "time": pd.date_range("2020-06-01", periods=20, freq="15D"),
                        "z": rng.standard_normal(20), "value": 0.0, "track": 0, "ref_mode": "same_track", "qc_ok": True})
    r2 = [r for r in t2_rows(pa2, ["V"], pd.Series(dtype=float), cfg) if r["key"] == "t2_g5"][0]
    assert np.isnan(r2["value"]) and r2["verdict"] == "za mało par" and r2["n"] == 0, r2
    sig = 0.3
    days = pd.date_range("2018-06-01", "2024-09-30", freq="5D")
    days = days[days.month.isin([6, 7, 8, 9])]
    pa3 = pd.concat([pd.DataFrame({"site_id": v, "index": "water", "time": days, "z": rng.normal(0, sig, len(days)),
                                   "value": 0.0, "track": 0, "ref_mode": "same_track", "qc_ok": True})
                     for v in ("V1", "V2", "V3")], ignore_index=True)
    r3 = [r for r in t2_rows(pa3, ["V1", "V2", "V3"], pd.Series(0.0, index=pd.date_range("2018-01-01", "2024-12-31")),
                             cfg) if r["key"] == "t2_g5"][0]
    assert abs(r3["value"] / (1.96 * np.sqrt(2) * sig) - 1) < 0.1, r3
    # T3: sygnał (ρ ≈ 0,6) spełnia kryterium; czysty szum nie (stałe ziarno)
    days = pd.DatetimeIndex([d for d in pd.date_range("2018-06-01", "2024-09-30", freq="4D") if 6 <= d.month <= 9])
    yy = pd.Series(rng.standard_normal(len(days)), index=days)
    xx = 0.7 * yy + 0.5 * pd.Series(rng.standard_normal(len(days)), index=days)
    _, ok_sig = t3_main(xx, yy, cfg, "P", "R", "test", 12)
    _, ok_noise = t3_main(pd.Series(rng.standard_normal(len(days)), index=days), yy, cfg, "P", "R", "test", 12)
    assert ok_sig and not ok_noise, (ok_sig, ok_noise)
    # Wariant wielopasmowy: cel z pasm -> przyjęty; zmiana celu w roku Y nie zmienia predykcji Y; brak związku -> ρ ≈ 0
    X = pd.DataFrame(rng.standard_normal((len(days), 4)), index=days, columns=["b04", "b06", "b8a", "b12"])
    ymb = pd.Series(0.8 * X["b12"] - 0.6 * X["b04"] + 0.3 * rng.standard_normal(len(days)), index=days)
    xs = pd.Series(0.3 * X["b12"] + rng.standard_normal(len(days)), index=days)
    rows = {r["key"]: r for r in multiband_rows(X, ymb, xs, cfg, 12) if r["key"]}
    assert rows["p7_accept"]["verdict"] == "przyjęty" and "p7_w_b12" in rows and "p7_sd" in rows, rows["p7_accept"]
    yrs = pd.Series(days.year, index=days)
    s_a, _ = multiband_loyo(X, ymb, yrs)
    y_b = ymb.copy()
    y_b[days.year == 2021] += 5.0
    s_b, _ = multiband_loyo(X, y_b, yrs)
    assert np.allclose(s_a[days.year == 2021], s_b[days.year == 2021]), "wyciek roku testowego do predykcji"
    reps = []
    for _ in range(200):
        Xn = pd.DataFrame(rng.standard_normal((len(days), 4)), index=days)
        yn = pd.Series(rng.standard_normal(len(days)) + 2.0 * pd.Series(days.year).map(
            dict(zip(range(2018, 2025), rng.standard_normal(7)))).to_numpy(), index=days)
        sn, _ = multiband_loyo(Xn, yn, yrs)
        reps.append(spearman(sn, yn))
    assert -0.05 <= float(np.mean(reps)) <= 0.05, np.mean(reps)
    # Wskaźnik wody: (z_NDMI − z_CRSWIR)/2, brak składnika -> brak wiersza; jedna scena na dzień: większy clear_frac
    t = pd.to_datetime(["2020-07-01 10:59", "2020-07-03 11:09"])
    base = {"product": "P", "value": 0.0, "clim_mean": 0.0, "clim_std": 1.0, "n_ref": 10, "n_ref_years": 5,
            "track": 0, "ref_mode": "same_track", "n_pixels": 100, "qc_ok": True}
    pw = pd.DataFrame([dict(base, site_id="V", index="ndmi", time=t[0], z=-1.0),
                       dict(base, site_id="V", index="crswir", time=t[0], z=0.6),
                       dict(base, site_id="V", index="ndmi", time=t[1], z=0.5)])
    wi = water_index(pw)
    assert len(wi) == 1 and np.isclose(wi["z"].iat[0], -0.8), wi
    wd = pd.DataFrame({"site_id": "V", "time": pd.to_datetime(["2020-07-01 10:59:04", "2020-07-01 10:59:11"]),
                       "clear_frac": [0.95, 0.99]})
    kept, n_d = one_scene_per_day(pd.concat([wd, wd.assign(site_id="V2")], ignore_index=True))
    assert n_d == 1 and (kept["clear_frac"] == 0.99).all() and len(kept) == 2, kept      # 1 dzień, 2 działki
    # Cel T3 z prawdziwego czujnika: wartość dnia t wpływa na y(t) tylko przez normę (< 0,01 z)
    sen = sensor_daily(cfg)
    sm = sen["W1"]["sm"]
    y_a = window_mean(anomaly_daily(sm, cfg), cfg)
    t0 = sm.loc["2022-07-15":"2022-07-31"].dropna().index[0]
    sm_b = sm.copy()
    sm_b.loc[t0] = sm_b.loc[t0] + 0.05
    y_b2 = window_mean(anomaly_daily(sm_b, cfg), cfg)
    assert abs(y_a[t0] - y_b2[t0]) < 0.01 and abs(y_a[t0 + pd.Timedelta(days=1)] - y_b2[t0 + pd.Timedelta(days=1)]) > 0.001
    sel = y_a[(y_a.index.month >= 6) & (y_a.index.month <= 9) & (y_a.index.year >= 2018)].dropna()
    assert len(sel) > 750 and set(sen) == set(SENSOR_VARIANTS), len(sel)
    print(f"[OK] W3b (parcel): jackknife, T1 ({100 * t1['value']:.1f}% [{100 * t1['ci_low']:.1f}; "
          f"{100 * t1['ci_high']:.1f}]), MDC95 ≈ 1,96·√2·σ, T3 sygnał/szum, §7 bez wycieku "
          f"(ρ przy braku związku {np.mean(reps):+.3f}), cel T3 z czujnika ({len(sel)} dni VI–IX 2018–2024).")
