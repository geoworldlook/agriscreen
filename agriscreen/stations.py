"""
Czujniki wilgotności gleby w gruncie (ISMN, SMOSMANIA Condom).

Odczyt plików ISMN, kontrola jakości, reguły A4 (warianty W1–W3), dzienne serie 20 i 30 cm, korelacja z przedziałem
(bootstrap blokowy). Używane przez walidację warstwy wody (reference.py) i test T3 (parcel.py).
"""

from __future__ import annotations
import glob
import logging
import os
import re
from typing import Any, Callable, Dict, Optional, Tuple
import numpy as np
import pandas as pd

logger = logging.getLogger("agriscreen.stations")


# Ścieżki względne są liczone względem PROJECT_DIR. Nazwy kluczy nie kolidują z CONFIG z notatnika,
# więc można przekazać cały CONFIG notatnika: używane są tylko klucze znane temu modułowi.
STATION_CONFIG: Dict[str, Any] = {
    "PROJECT_DIR": ".",
    "NETWORK": "SMOSMANIA",
    "STATION": "Condom",
    "ISMN_DIR": "data/7_isismn_data",
    "STATION_OUTPUT_DIR": "data/08_Station_Validation",
    "GEE_PROJECT": "ee-geoworldlook",

    "START_DATE": "2016-01-01",
    "END_DATE": "auto",          # "auto" = ostatni dzień w plikach ISMN (data końcowa z nazwy pliku .stm)
    "DEPTH_M": 0.05,                 # warstwa powierzchniowa porównywalna z S-1
    "STATION_BUFFER_M": 50,          # promień bufora wokół stacji (S-1 wymaga wielu pikseli)

    # --- Kontrola jakości in situ (docs/evidence/Condom_QC.md) ---
    "SM_VALID_RANGE": (0.0, 0.60),   # m3/m3
    "STUCK_MIN_HOURS": 168,          # identyczna wartość przez >= 7 dni = zamrożony czujnik
    "EXCLUDE_PERIODS": [
        # (od, do, głębokość [m] lub None = wszystkie, powód)
        ("2019-02-06", "2019-02-21", 0.05, "QC-1: artefakt wymiany czujnika 5 cm (ML3 -> ML2x)"),
    ],
    "DAILY_MIN_HOURS": 18,           # minimalna liczba godzin do średniej dobowej
    # --- A4: utrata kontaktu w glinie, 20 i 30 cm (docs/evidence/A4_QC_czujnikow_ISMN.md §3–4, D-060–D-063;
    #     SHA-256 sekcji przed wdrożeniem w Planie v8 i v9) ---
    "A4_THETA_FLOOR": 0.10,          # LOW_IMPLAUSIBLE: średnia dobowa < θ_dno
    "A4_FAST_DROP": 0.05,            # FAST_DROP: spadek > 0,05 m3/m3 ...
    "A4_FAST_DROP_HOURS": 6,         # ... w <= 6 h (cały dzień oznaczony)
    "A4_WP": {0.20: 0.271, 0.30: 0.273},   # punkt więdnięcia (Saxton i Rawls 2006; a4_explore.log) — wrażliwość 0,5·WP
    "A4_FLOOR_SENS": 0.15,           # druga wartość wrażliwości θ_dno

    # --- Sentinel-1 change detection ---
    "CD_CALIBRATION": ("2016-01-01", "2021-12-31"),
    "CD_PERCENTILES": (5, 95),
    "CD_MIN_OBS_PER_ORBIT": 30,
    "S1_MIN_PIXEL_FRACTION": 0.5,    # min. udział pikseli bufora z danymi
    "POROSITY": None,                # None = odczyt z HWSD (static_variables.csv)

    # --- Flagi ---
    "S2_MIN_CLEAR_FRACTION": 0.9,
    "NDVI_TOLERANCE_DAYS": 15,
    "NDVI_DENSE_VEGETATION": 0.7,
    "FROZEN_T2M_MIN_C": 0.0,

    # --- Walidacja ---
    "MATCH_TOLERANCE_MIN": 60,
    "ANOMALY_WINDOW_DAYS": 35,
    "TEST_PERIOD": ("2022-01-01", "2024-12-31"),
    "MIN_N_METRICS": 10,
    "BOOTSTRAP_N": 1000,
    "BOOTSTRAP_BLOCK_DAYS": 30,
    "RANDOM_SEED": 42,

    # --- Pobieranie z GEE (długość fragmentów zapytań w miesiącach) ---
    "CHUNK_MONTHS": {"s1": 12, "s2": 6, "era5": 12},
}


def ismn_end_date(station_dir: str) -> str:
    """
    Koniec okresu danych ISMN z nazw plików (…_RRRRMMDD_RRRRMMDD.stm; data końcowa jest wyłączna).
    Nowe pliki pobrane z ismn.earth wydłużają walidację bez zmian w kodzie. Brak plików = dziś.
    """
    ends = []
    for p in glob.glob(os.path.join(station_dir, "*_sm_*.stm")):
        m = re.search(r"_(\d{8})_(\d{8})\.stm$", os.path.basename(p))
        if m:
            ends.append(pd.Timestamp(m.group(2)) - pd.Timedelta(days=1))
    return (max(ends) if ends else pd.Timestamp.now().normalize()).strftime("%Y-%m-%d")


def build_config(overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Łączy konfigurację domyślną z nadpisaniami i rozwiązuje ścieżki względne."""
    cfg = dict(STATION_CONFIG)
    if overrides:
        cfg.update({k: v for k, v in overrides.items() if k in STATION_CONFIG})
    root = cfg["PROJECT_DIR"]
    for key in ("ISMN_DIR", "STATION_OUTPUT_DIR"):
        if not os.path.isabs(cfg[key]):
            cfg[key] = os.path.join(root, cfg[key])
    cfg["STATION_DIR"] = os.path.join(cfg["ISMN_DIR"], cfg["NETWORK"], cfg["STATION"])
    if cfg["END_DATE"] == "auto":
        cfg["END_DATE"] = ismn_end_date(cfg["STATION_DIR"])
    cfg["RUN_DIR"] = os.path.join(cfg["STATION_OUTPUT_DIR"], cfg["STATION"])
    cfg["CACHE_DIR"] = os.path.join(cfg["RUN_DIR"], "cache")
    return cfg


_STM_NAME = re.compile(r"_sm_(?P<dfrom>[0-9.]+)_(?P<dto>[0-9.]+)_(?P<sensor>.+?)_\d+_\d+_\d{8}_\d{8}\.stm$")


def read_ismn_stm(path: str) -> pd.DataFrame:
    """
    Czyta plik ISMN w formacie Header+values (.stm).
    Wiersz 1: nagłówek stacji; kolejne: 'YYYY/MM/DD HH:MM wartość flaga_ISMN flaga_źródła'.
    Zwraca DataFrame z indeksem czasu UTC oraz kolumnami: sm, flag, sensor, depth_from, depth_to.
    """
    m = _STM_NAME.search(os.path.basename(path))
    if m is None:
        raise ValueError(f"Nierozpoznana nazwa pliku ISMN: {os.path.basename(path)}")
    df = pd.read_csv(
        path, sep=r"\s+", skiprows=1, header=None,
        names=["date", "time", "sm", "flag", "origin"],
        dtype={"flag": str, "origin": str},
    )
    df.index = pd.to_datetime(df["date"] + " " + df["time"], format="%Y/%m/%d %H:%M")
    df.index.name = "time"
    out = df[["sm", "flag"]].copy()
    out["sensor"] = m.group("sensor")
    out["depth_from"] = float(m.group("dfrom"))
    out["depth_to"] = float(m.group("dto"))
    return out


def load_insitu(cfg: Dict[str, Any]) -> pd.DataFrame:
    """Wczytuje wszystkie czujniki dla zadanej głębokości i nadaje identyfikatory segmentów."""
    files = sorted(glob.glob(os.path.join(cfg["STATION_DIR"], "*_sm_*.stm")))
    frames = [read_ismn_stm(p) for p in files]
    frames = [f for f in frames if np.isclose(f["depth_from"].iloc[0], cfg["DEPTH_M"])]
    if not frames:
        raise FileNotFoundError(f"Brak czujników na głębokości {cfg['DEPTH_M']} m w {cfg['STATION_DIR']}")

    # Segment = jeden czujnik; kolejność według początku pomiarów
    frames.sort(key=lambda f: f.index.min())
    for k, f in enumerate(frames, start=1):
        short = f["sensor"].iloc[0].replace("DeltaT-ThetaProbe-", "")
        f["segment"] = f"seg{k}_{short}"
    df = pd.concat(frames).sort_index()
    # Nakładające się znaczniki czasu przy wymianie czujnika: zostaje nowszy czujnik
    df = df[~df.index.duplicated(keep="last")]
    df = df.loc[cfg["START_DATE"]:pd.Timestamp(cfg["END_DATE"]) + pd.Timedelta(days=1)]
    logger.info(f"In situ: {len(df)} rekordów, segmenty: {df['segment'].unique().tolist()}")
    return df


def _stuck_mask(sm: pd.Series, min_hours: int) -> pd.Series:
    """Oznacza serie identycznych wartości trwające >= min_hours (zamrożony czujnik)."""
    s = sm.dropna()
    if s.empty:
        return pd.Series(False, index=sm.index)
    run_id = (s.diff() != 0).cumsum().to_numpy()
    t = s.index.to_series()
    grp = t.groupby(run_id)
    span_h = (grp.transform("max") - grp.transform("min")) / pd.Timedelta(hours=1)
    return (span_h >= min_hours).reindex(sm.index, fill_value=False)


def qc_insitu(df: pd.DataFrame, cfg: Dict[str, Any]) -> pd.DataFrame:
    """
    Kontrola jakości ponad flagi ISMN. Dodaje kolumny:
      qc_ok (bool) i qc_reason (pierwszy powód odrzucenia).
    Rekordy odrzucone nie są usuwane — raport pokazuje ich liczbę per powód.
    """
    out = df.copy()
    reason = pd.Series("", index=out.index, dtype=object)

    def mark(mask: pd.Series, code: str) -> None:
        nonlocal reason
        reason = reason.where(~(mask & (reason == "")), code)

    lo, hi = cfg["SM_VALID_RANGE"]
    mark(out["flag"] != "G", "FLAG_NOT_G")
    mark(out["sm"].isna() | (out["sm"] < lo) | (out["sm"] > hi), "OUT_OF_RANGE")
    for _seg, g in out.groupby("segment"):
        mark(_stuck_mask(g["sm"], cfg["STUCK_MIN_HOURS"]).reindex(out.index, fill_value=False), "STUCK_VALUE")
    for start, end, depth, _why in cfg["EXCLUDE_PERIODS"]:
        in_period = (out.index >= pd.Timestamp(start)) & (out.index < pd.Timestamp(end) + pd.Timedelta(days=1))
        depth_ok = np.ones(len(out), bool) if depth is None else np.isclose(out["depth_from"], depth)
        mark(pd.Series(in_period & depth_ok, index=out.index), "EXCLUDED_PERIOD")

    out["qc_reason"] = reason
    out["qc_ok"] = reason == ""
    summary = out["qc_reason"].replace("", "OK").value_counts()
    logger.info("QC in situ: " + ", ".join(f"{k}={v}" for k, v in summary.items()))
    return out


def insitu_daily(df_qc: pd.DataFrame, cfg: Dict[str, Any]) -> pd.DataFrame:
    """Średnie dobowe z rekordów qc_ok (min. DAILY_MIN_HOURS godzin) z segmentem dnia."""
    ok = df_qc[df_qc["qc_ok"]]
    g = ok.groupby(ok.index.floor("D"))
    daily = pd.DataFrame({"sm": g["sm"].mean(), "n_hours": g["sm"].count(), "segment": g["segment"].last()})
    daily = daily[daily["n_hours"] >= cfg["DAILY_MIN_HOURS"]]
    daily.index.name = "date"
    return daily


def fast_drop_days(sm: pd.Series, step: str = "1h", hours: int = 6, thr: float = 0.05) -> pd.DatetimeIndex:
    """
    A4 FAST_DROP: dni, w których wartość spada o > thr w <= hours godzin. Na regularnej siatce `step`: maksimum
    z bieżącego i poprzednich pomiarów w oknie `hours` minus bieżąca wartość (jak docs/evidence/A4_QC/a4_explore.py).
    """
    s = sm.dropna().sort_index()
    s = s[~s.index.duplicated(keep="last")]
    if s.empty:
        return pd.DatetimeIndex([])
    s = s.asfreq(step)
    n = int(pd.Timedelta(hours=hours) / pd.Timedelta(step)) + 1
    drop = (s.rolling(n, min_periods=2).max() - s) > thr
    return pd.DatetimeIndex(drop[drop].index.normalize().unique())


def a4_variants(depth_m: float, overrides: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
    """
    Średnie dobowe czujnika 20 lub 30 cm po dotychczasowym QC i regułach A4 (notatka A4 §3–4), w wariantach:
      W1        — główny: dzień LOW_IMPLAUSIBLE (średnia < θ_dno) -> wartość θ_dno i flaga „cenzurowany”;
                  dzień FAST_DROP -> brak danych (dzień z obiema flagami traktujemy jak FAST_DROP),
      W2        — wykluczenie: dni LOW_IMPLAUSIBLE i FAST_DROP -> brak danych,
      W3        — bez nowego QC (jak dotąd),
      W1_05WP, W1_015 — wariant W1 z θ_dno = 0,5·WP i 0,15 (wrażliwość).
    Kolumny: sm, censored, low, fast.
    """
    c = build_config({**overrides, "DEPTH_M": depth_m})
    q = qc_insitu(load_insitu(c), c)
    base = insitu_daily(q, c)[["sm"]].copy()
    fast = fast_drop_days(q.loc[q["qc_ok"], "sm"], "1h", int(c["A4_FAST_DROP_HOURS"]), float(c["A4_FAST_DROP"]))
    is_fast = base.index.normalize().isin(fast)
    wp = float(c["A4_WP"].get(round(depth_m, 2), np.nan))
    floors = {"W1": float(c["A4_THETA_FLOOR"]), "W1_05WP": 0.5 * wp, "W1_015": float(c["A4_FLOOR_SENS"])}
    out: Dict[str, pd.DataFrame] = {}
    for name, fl in floors.items():
        d = base.copy()
        d["low"], d["fast"] = d["sm"] < fl, is_fast
        d["censored"] = d["low"] & ~d["fast"]
        d.loc[d["fast"], "sm"] = np.nan
        d.loc[d["censored"], "sm"] = fl
        out[name] = d
    d = base.copy()
    d["low"], d["fast"] = d["sm"] < floors["W1"], is_fast
    d["censored"] = False
    d.loc[d["low"] | d["fast"], "sm"] = np.nan
    out["W2"] = d
    d = base.copy()
    d["low"], d["fast"], d["censored"] = d["sm"] < floors["W1"], is_fast, False
    out["W3"] = d
    return out


def a4_flag_report(v20: Dict[str, pd.DataFrame], v30: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Raport A4 (notatka §5): liczba dni oznaczonych per rok, głębokość i reguła (z progami wrażliwości)."""
    rows = []
    for depth, v in ((20, v20), (30, v30)):
        for y, g in v["W3"].groupby(v["W3"].index.year):
            r = {"year": int(y), "depth_cm": depth, "days": int(g["sm"].notna().sum()),
                 "fast_drop": int(g["fast"].sum()), "low_010": int(v["W1"].loc[g.index, "low"].sum()),
                 "low_05wp": int(v["W1_05WP"].loc[g.index, "low"].sum()),
                 "low_015": int(v["W1_015"].loc[g.index, "low"].sum())}
            rows.append(r)
    return pd.DataFrame(rows)


def _moving_anomaly(series: pd.Series, window_days: int, min_periods: int) -> pd.Series:
    """Anomalia krótkoterminowa: wartość minus wyśrodkowana średnia ruchoma (jak w QA4SM)."""
    s = series.dropna().sort_index()
    s = s[~s.index.duplicated(keep="first")]
    ma = s.rolling(f"{window_days}D", center=True, min_periods=min_periods).mean()
    return s - ma


def _block_bootstrap_ci(
    times: pd.Series, x: np.ndarray, y: np.ndarray, func: Callable[[np.ndarray, np.ndarray], float], cfg: Dict[str, Any]
) -> Tuple[float, float]:
    """95% CI z bootstrapu blokowego (bloki kalendarzowe BOOTSTRAP_BLOCK_DAYS) — uwzględnia autokorelację."""
    rng = np.random.default_rng(cfg["RANDOM_SEED"])
    block = ((times - times.min()) / pd.Timedelta(days=cfg["BOOTSTRAP_BLOCK_DAYS"])).astype(int).to_numpy()
    uniq = np.unique(block)
    if len(uniq) < 5:
        return np.nan, np.nan
    idx_by_block = {b: np.flatnonzero(block == b) for b in uniq}
    stats = []
    for _ in range(cfg["BOOTSTRAP_N"]):
        pick = rng.choice(uniq, size=len(uniq), replace=True)
        idx = np.concatenate([idx_by_block[b] for b in pick])
        if len(idx) < 3:
            continue
        with np.errstate(all="ignore"):
            stats.append(func(x[idx], y[idx]))
    stats = np.asarray(stats, float)
    stats = stats[np.isfinite(stats)]
    if len(stats) < 50:
        return np.nan, np.nan
    return float(np.percentile(stats, 2.5)), float(np.percentile(stats, 97.5))


def site_id(cfg: Dict[str, Any]) -> str:
    return f"{cfg['NETWORK']}_{cfg['STATION']}"


def _r_with_ci(t: pd.Series, x: np.ndarray, y: np.ndarray, cfg: Dict[str, Any]) -> Tuple[float, float, float]:
    if len(x) < cfg["MIN_N_METRICS"]:
        return np.nan, np.nan, np.nan
    r = float(np.corrcoef(x, y)[0, 1])
    lo, hi = _block_bootstrap_ci(t.reset_index(drop=True), x, y, lambda a, b: np.corrcoef(a, b)[0, 1], cfg)
    return r, lo, hi
