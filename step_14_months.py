"""
================================================================================
AgriWatch - KROK 14: MIEJSCE „NAJNIŻEJ OD 5 LAT” (W3d)
================================================================================
Protokół: docs/evidence/W3d_protokol_miesiace.md (zarejestrowany 2026-10-20, D-091). Numery § odnoszą się do niego.

Zdanie dla winiarza: „W lipcu 2026 to miejsce miało najniższą zieleń od 5 lat.”

  1. Magazyn (w3d_store.npz, przyrostowo, step_13.update_store(kind="abs")): wskaźnik kwadratu 30 m (okno 3×3,
     pas 20 m) w każdej czystej scenie 13 winnic z QC (§1).
  2. Wartość miesiąca = mediana z ≥ 2 czystych dni; klasa wobec tego samego miesiąca w 5 poprzednich latach
     tego samego kwadratu (≥ 4 lata), z resetem historii po przesadzeniu z rejestru RPG (§2, §3).
  3. Plamy ≥ 4 pikseli (§4). Test D1: w zwykłe miesiące „najniżej / najwyżej od N lat” ma wypadać ok. 1/(N + 1)
     kwadratów; kryterium pokazania: górna granica ilorazu ≤ 1,5 dla obu klas (§5).
Wyniki: w3d_tests.csv, w3d_summary.csv, w3d_months.npz (kody kwadratów do mapy panelu), w3d_freeze.json.
================================================================================
"""

from __future__ import annotations

import glob
import hashlib
import json
import logging
import os
import warnings
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

import step_04_metrics_alert as s4
import step_11_parcel as s11
import step_13_zones as s13

logger = logging.getLogger("AgriWatch_Months")

CODE_VERSION = "1.0"
STORE_NAME, MONTHS_NAME = "w3d_store.npz", "w3d_months.npz"
TESTS_NAME, SUMMARY_NAME, FREEZE_NAME = "w3d_tests.csv", "w3d_summary.csv", "w3d_freeze.json"
PRODUCT = "S2_10m_months"
# kody kwadratów (§2.3, §4): plamy „najniżej” / „najwyżej”, „w zakresie” (także małe plamy), szare
NO_DATA, IN_RANGE, LOW, HIGH, REPLANT, NO_HIST = -1, 0, 1, 3, 8, 9
REPLANT_CODES = ("RVI", "VRN")


# ==============================================================================
# I. PRZESADZENIA, MIESIĄCE, KLASY (§2–§4)
# ==============================================================================

def replant_years(path: str) -> Dict[str, Set[int]]:
    """Lata przesadzenia z RPG (§3): kod RVI albo VRN w punkcie winnicy. Brak pliku = brak przesadzeń."""
    if not os.path.exists(path):
        logger.warning(f"W3d: brak {path} — historia bez resetu po przesadzeniu")
        return {}
    d = pd.read_csv(path)
    out: Dict[str, Set[int]] = {}
    for r in d.itertuples():
        if any(c in str(r.code_cultu).split(",") for c in REPLANT_CODES):
            out.setdefault(str(r.site_id), set()).add(int(r.year))
    return out


def month_values(R: np.ndarray, sc: pd.DataFrame, min_days: int) -> Dict[Tuple[int, int], Tuple[np.ndarray, int]]:
    """Wartość miesiąca każdego kwadratu (§2.1): mediana z czystych dni miesiąca; NaN przy < min_days dniach z
    wartością. Zwraca {(rok, miesiąc): (wartości, liczba czystych dni winnicy w miesiącu)}."""
    out = {}
    if not len(sc):
        return out
    ym = list(zip(sc["time"].dt.year, sc["time"].dt.month))
    for key in sorted(set(ym)):
        rows = np.flatnonzero([k == key for k in ym])
        X = R[rows]
        n = np.isfinite(X).sum(axis=0)
        with warnings.catch_warnings():                       # kwadraty bez żadnej wartości: NaN bez ostrzeżeń
            warnings.simplefilter("ignore", RuntimeWarning)
            v = np.where(n >= min_days, np.nanmedian(X, axis=0), np.nan)
        out[(int(key[0]), int(key[1]))] = (v, int(len(rows)))
    return out


def classify(V: Dict[Tuple[int, int], Tuple[np.ndarray, int]], y: int, m: int, replant: Set[int],
             cfg: Dict[str, Any]) -> Tuple[np.ndarray, np.ndarray]:
    """Klasa kwadratów w miesiącu (y, m) (§2.2–2.3, §3): historia z lat y−5…y−1 po ostatnim przesadzeniu przed y,
    ≥ MONTHS_MIN_YEARS lat z wartością. Zwraca kody (bez filtra plam) i N (liczba lat historii)."""
    v = V[(y, m)][0]
    if y in replant:
        return np.where(np.isfinite(v), REPLANT, NO_DATA).astype(np.int8), np.zeros(len(v), int)
    last = max([r for r in replant if r < y], default=-10 ** 6)
    years = [yy for yy in range(y - int(cfg["MONTHS_HISTORY_YEARS"]), y) if yy > last and (yy, m) in V]
    if years:
        H = np.vstack([V[(yy, m)][0] for yy in years])
        N = np.isfinite(H).sum(axis=0)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            lo, hi = np.nanmin(H, axis=0), np.nanmax(H, axis=0)
    else:
        N, lo, hi = np.zeros(len(v), int), np.full(len(v), np.nan), np.full(len(v), np.nan)
    c = np.full(len(v), NO_DATA, np.int8)
    fin = np.isfinite(v)
    c[fin] = NO_HIST
    ok = fin & (N >= int(cfg["MONTHS_MIN_YEARS"]))
    c[ok] = IN_RANGE
    with np.errstate(invalid="ignore"):
        c[ok & (v < lo)] = LOW
        c[ok & (v > hi)] = HIGH
    return c, N


def spots(codes: np.ndarray, rr: np.ndarray, cc: np.ndarray, min_cells: int) -> np.ndarray:
    """Filtr plam (§4): „najniżej” / „najwyżej” tylko w zwartych grupach ≥ min_cells (8 sąsiadów); reszta → w zakresie."""
    from scipy import ndimage
    out = codes.copy()
    r0, c0 = rr.min(), cc.min()
    shape = (rr.max() - r0 + 1, cc.max() - c0 + 1)
    for code in (LOW, HIGH):
        g = np.zeros(shape, bool)
        g[rr - r0, cc - c0] = codes == code
        lab, _ = ndimage.label(g, structure=np.ones((3, 3), int))
        sizes = np.bincount(lab.ravel())
        keep = sizes >= min_cells
        keep[0] = False
        small = (codes == code) & ~keep[lab][rr - r0, cc - c0]
        out[small] = IN_RANGE
    return out


# ==============================================================================
# II. TEST D1 (§5) I OPIS (§6)
# ==============================================================================

def _ratio(q: pd.DataFrame, col: str) -> float:
    return float(q[col].sum() / q["expected"].sum()) if len(q) and q["expected"].sum() > 0 else np.nan


def d1_rows(counts: pd.DataFrame, index: str, cfg: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """D1 (§5): iloraz R = udział „najniżej” (i „najwyżej”) / oczekiwane 1/(N + 1), miesiące VI–IX z glebą w normie
    (gdy takie miesiące są w < 3 latach: wszystkie VI–IX). Kryterium: górna granica R ≤ MONTHS_MAX_RATIO dla obu klas
    i ≥ 3 lata. Opisowo: miesiące suche i wilgotne, po latach, udział w plamach."""
    rows: List[Dict[str, Any]] = []
    prod = f"{PRODUCT}_{index.upper()}"
    res: Dict[str, Any] = {"show": False, "why": [], "basis": ""}
    if counts.empty:
        res["why"].append("brak miesięcy z historią")
        rows.append(s11._row("D", s11.PARCELS, prod, "", "kryterium pokazania warstwy (§5)", "show", 0.0, criterion=True,
                             verdict="nie pokazujemy — brak miesięcy z historią", key=f"d_show_{index}"))
        return rows, res
    normal = counts[counts["soil"].between(30, 70)]
    basis = normal if normal["year"].nunique() >= 3 else counts
    res["basis"] = "gleba w normie" if basis is normal else "wszystkie miesiące VI–IX (gleba w normie w < 3 latach)"
    max_r = float(cfg["MONTHS_MAX_RATIO"])
    for sub, q in (("gleba w normie", normal), ("gleba sucha (< 30)", counts[counts["soil"] < 30]),
                   ("gleba wilgotna (> 70)", counts[counts["soil"] > 70]), ("wszystkie miesiące VI–IX", counts)):
        for col, what in (("low", "najniżej"), ("high", "najwyżej")):
            key = f"d1_{col}_{index}" if q is basis else ""
            m, lo, hi, _ = s11.jackknife_ci(q, lambda g, c=col: _ratio(g, c), bounds=(0, np.inf))
            rows.append(s11._row("D1", s11.PARCELS, prod, "", f"{sub}: „{what} od N lat” / oczekiwane 1/(N+1)",
                                 "ratio", m, (lo, hi), pd.to_datetime(q["month"] + "-01"),
                                 n_parcels=q["site_id"].nunique() if len(q) else 0, key=key,
                                 verdict="podstawa kryterium" if key else ""))
            if key:
                res[col] = {"value": m, "lo": lo, "hi": hi}
                if not (np.isfinite(hi) and hi <= max_r):
                    res["why"].append(f"„{what}” górna {hi:.2f} > {max_r:.1f}" if np.isfinite(hi)
                                      else f"„{what}”: za mało lat do przedziału")
        rows.append(s11._row("D1", s11.PARCELS, prod, "", f"{sub}: oczekiwany udział 1/(N+1)", "expected_share",
                             q["expected"].sum() / q["n"].sum() if len(q) and q["n"].sum() else np.nan,
                             days=pd.to_datetime(q["month"] + "-01")))
    if basis["year"].nunique() < 3:
        res["why"].append("dane z < 3 lat")
    for y, g in counts.groupby("year"):
        rows.append(s11._row("D1", s11.PARCELS, prod, "", f"rok {y} (opisowo): „najniżej” / oczekiwane", "ratio",
                             _ratio(g, "low"), days=pd.to_datetime(g["month"] + "-01")))
    for col, what in (("low_spot", "najniżej"), ("high_spot", "najwyżej")):
        rows.append(s11._row("D1", s11.PARCELS, prod, "", f"{res['basis']}: udział powierzchni w plamach „{what}”",
                             "share_cells", basis[col].sum() / basis["n"].sum() if basis["n"].sum() else np.nan,
                             days=pd.to_datetime(basis["month"] + "-01")))
    res["show"] = not res["why"]
    rows.append(s11._row("D", s11.PARCELS, prod, "", "kryterium pokazania warstwy (§5)", "show",
                         1.0 if res["show"] else 0.0, criterion=True,
                         verdict="pokazujemy" if res["show"] else "nie pokazujemy — " + "; ".join(res["why"]),
                         key=f"d_show_{index}"))
    return rows, res


def freeze_info(cfg: Dict[str, Any], out_dir: str) -> Dict[str, Any]:
    """Zamrożenie testu W3d (§0): W3D_FREEZE z konfiguracji albo ostatnia scena przy pierwszym liczeniu."""
    path = os.path.join(out_dir, FREEZE_NAME)
    names = sorted(os.path.basename(p) for p in glob.glob(os.path.join(cfg["S2_DIR"], "S2_L2A_*.tif")))
    saved = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else None
    if cfg.get("W3D_FREEZE"):
        freeze, source = str(cfg["W3D_FREEZE"])[:10], "konfiguracja"
    elif saved:
        freeze, source = saved["freeze"], FREEZE_NAME
    else:
        freeze, source = f"{s4.scene_time(names[-1]):%Y-%m-%d}", "ostatnia scena przy pierwszym liczeniu"
    frozen = [n for n in names if s4.scene_time(n).normalize() <= pd.Timestamp(freeze)]
    sha = hashlib.sha256("\n".join(frozen).encode("utf-8")).hexdigest()
    info = {"freeze": freeze, "source": source, "n_scenes": len(frozen), "scenes_sha256": sha,
            "scenes_sha256_at_freeze": (saved or {}).get("scenes_sha256", sha)}
    if saved is None and not cfg.get("W3D_FREEZE"):
        os.makedirs(out_dir, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(dict(info, created_utc=pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%dT%H:%M:%SZ")), f, indent=1)
    return info


# ==============================================================================
# III. CAŁOŚĆ
# ==============================================================================

def run_months(cfg: Dict[str, Any], out_dir: str, era5: pd.DataFrame, commit: str = "") -> Dict[str, Any]:
    """W3d od magazynu do plików wynikowych; zwraca podsumowanie do komunikatu zadania."""
    store = s13.update_store(cfg, os.path.join(out_dir, STORE_NAME), kind="abs")
    fz = freeze_info(cfg, out_dir)
    proto = s11.protocol_sha(cfg["W3D_PROTOCOL"])
    freeze = pd.Timestamp(fz["freeze"])
    rp = replant_years(cfg["RPG_PATH"])
    soil = s11.soil_pct(era5, cfg)
    soil_m = soil.groupby(soil.index.strftime("%Y-%m")).mean()
    m0, m1 = cfg["PARCEL_TEST_MONTHS"]
    width = int(store["shape"][1])
    rr_all, cc_all = store["pix"] // width, store["pix"] % width
    min_days, min_cells = int(cfg["MONTHS_MIN_DAYS"]), int(cfg["ZONES_MIN_CELLS"])
    all_months = sorted({f"{s4.scene_time(n):%Y-%m}" for n in store["scenes"]})
    mi = {m: i for i, m in enumerate(all_months)}
    out: Dict[str, Any] = {k: store[k] for k in ("transform", "shape", "crs", "pix", "site_idx")}
    out.update(sites=np.array(store["sites"], dtype=str), months=np.array(all_months, dtype=str))
    rows: List[Dict[str, Any]] = []
    summary: List[Dict[str, Any]] = []
    result: Dict[str, Any] = {"n_scenes": len(store["scenes"]), "n_new": store.get("n_new", 0),
                              "n_skipped": len(store["skipped"]), "sites": len(store["sites"]), "show": {}}
    for k in cfg["ZONES_INDICES"]:
        codes = np.full((len(all_months), len(store["pix"])), NO_DATA, np.int8)
        nyear = np.zeros((len(all_months), len(store["pix"])), np.int8)
        counts = []
        for j, sid in enumerate(store["sites"]):
            sel = np.flatnonzero(store["site_idx"] == j)
            sc = s13.parcel_scenes(store, j, cfg)
            R = store[f"r_{k}"][sc["row"].to_numpy()][:, sel] if len(sc) else np.zeros((0, len(sel)))
            V = month_values(R, sc, min_days)                      # mapa: wszystkie sceny
            frozen = sc["time"].dt.normalize() <= freeze
            Vt = month_values(R[frozen.to_numpy()], sc[frozen].reset_index(drop=True), min_days)   # test: ≤ zamrożenia
            for (y, m), (v, nd) in V.items():
                c, N = classify(V, y, m, rp.get(sid, set()), cfg)
                cs = spots(c, rr_all[sel], cc_all[sel], min_cells)
                month = f"{y}-{m:02d}"
                codes[mi[month], sel], nyear[mi[month], sel] = cs, np.minimum(N, 127)
                valid = np.isin(c, (LOW, IN_RANGE, HIGH))
                summary.append({"site_id": sid, "month": month, "index": k, "n_days": nd, "n_cells": int(valid.sum()),
                                "low": int((c == LOW).sum()), "high": int((c == HIGH).sum()),
                                "low_spot": int((cs == LOW).sum()), "high_spot": int((cs == HIGH).sum()),
                                "no_hist": int((c == NO_HIST).sum()), "replant": int((c == REPLANT).sum()),
                                "expected": float(np.sum(1.0 / (N[valid] + 1))) if valid.any() else 0.0,
                                "med_years": float(np.median(N[valid])) if valid.any() else np.nan})
            for (y, m) in Vt:
                if not (m0 <= m <= m1):
                    continue
                c, N = classify(Vt, y, m, rp.get(sid, set()), cfg)
                valid = np.isin(c, (LOW, IN_RANGE, HIGH))
                if not valid.any():
                    continue
                cs = spots(c, rr_all[sel], cc_all[sel], min_cells)
                month = f"{y}-{m:02d}"
                counts.append({"site_id": sid, "month": month, "year": y, "n": int(valid.sum()),
                               "low": int((c == LOW).sum()), "high": int((c == HIGH).sum()),
                               "low_spot": int((cs == LOW).sum()), "high_spot": int((cs == HIGH).sum()),
                               "expected": float(np.sum(1.0 / (N[valid] + 1))),
                               "soil": float(soil_m.get(month, np.nan))})
        r1, res = d1_rows(pd.DataFrame(counts), k, cfg)
        rows += r1
        out[f"codes_{k}"], out[f"nyears_{k}"] = codes, nyear
        out[f"show_{k}"] = np.array(bool(res["show"]))
        result["show"][k] = ("pokazujemy" if res["show"] else "nie pokazujemy — " + "; ".join(res["why"]))
    tests = pd.DataFrame(rows, columns=s11.TEST_COLS).assign(
        protocol_sha256=proto["sha256"], protocol_status=proto["status"], protocol_registered=proto["registered"],
        freeze=fz["freeze"], scenes=fz["n_scenes"], scenes_sha256=fz["scenes_sha256"], code_version=CODE_VERSION,
        code_commit=commit)
    os.makedirs(out_dir, exist_ok=True)
    tests.to_csv(os.path.join(out_dir, TESTS_NAME), index=False)
    pd.DataFrame(summary).to_csv(os.path.join(out_dir, SUMMARY_NAME), index=False)
    np.savez_compressed(os.path.join(out_dir, MONTHS_NAME), **out)
    result.update(freeze=fz, protocol=proto)
    return result


def load_months(out_dir: str) -> Optional[Dict[str, Any]]:
    """Wyniki W3d do panelu (kody kwadratów, decyzje, podsumowanie). None, gdy brak."""
    p = os.path.join(out_dir, MONTHS_NAME)
    if not os.path.exists(p):
        return None
    with np.load(p, allow_pickle=False) as z:
        d = {k: z[k] for k in z.files}
    d["months"] = [str(s) for s in d["months"]]
    d["sites"] = [str(s) for s in d["sites"]]
    sp = os.path.join(out_dir, SUMMARY_NAME)
    d["summary"] = pd.read_csv(sp) if os.path.exists(sp) and os.path.getsize(sp) > 1 else pd.DataFrame()
    return d


# ==============================================================================
# IV. SELFTEST (dane syntetyczne)
# ==============================================================================

def _selftest(cfg: Dict[str, Any]) -> None:
    """
    Testy na danych syntetycznych: mediana miesiąca z ≥ 2 dni; klasa „najniżej / najwyżej od N lat” z ≥ 4 lat;
    reset po przesadzeniu; filtr plam ≥ 4; przy samym szumie iloraz D1 ≈ 1 (kryterium spełnione), przy trendzie
    w części winnicy „najniżej” wypada za często (kryterium niespełnione).
    """
    rng = np.random.default_rng(11)
    cfg_t = dict(cfg, MONTHS_HISTORY_YEARS=5, MONTHS_MIN_YEARS=4, MONTHS_MIN_DAYS=2, MONTHS_MAX_RATIO=1.5,
                 ZONES_MIN_CELLS=4, PARCEL_TEST_MONTHS=(6, 9))
    rr, cc = np.divmod(np.arange(400), 20)
    times = [pd.Timestamp(f"{y}-{m:02d}-{d:02d} 10:59") for y in range(2016, 2027) for m in range(4, 11)
             for d in (3, 13, 23)]
    sc = pd.DataFrame({"time": pd.to_datetime(times)})
    base = 0.5 + 0.05 * np.sin(rr / 4.0) + 0.03 * np.cos(cc / 5.0)
    # 1. mediana miesiąca: jeden dzień bez wartości -> nadal 2 dni; dwa -> NaN
    R = base + rng.normal(0, 0.02, (len(sc), 400))
    R[0, 0] = np.nan
    R[:2, 1] = np.nan
    V = month_values(R, sc, 2)
    assert np.isfinite(V[(2016, 4)][0][0]) and np.isnan(V[(2016, 4)][0][1]) and V[(2016, 4)][1] == 3
    # 2. sam szum (lata wymienne): D1 ≈ 1, kryterium spełnione
    counts = []
    for (y, m) in V:
        c, N = classify(V, y, m, set(), cfg_t)
        valid = np.isin(c, (LOW, IN_RANGE, HIGH))
        if valid.any() and 6 <= m <= 9:
            cs = spots(c, rr, cc, 4)
            counts.append({"site_id": "X", "month": f"{y}-{m:02d}", "year": y, "n": int(valid.sum()),
                           "low": int((c == LOW).sum()), "high": int((c == HIGH).sum()),
                           "low_spot": int((cs == LOW).sum()), "high_spot": int((cs == HIGH).sum()),
                           "expected": float(np.sum(1.0 / (N[valid] + 1))), "soil": 50.0})
    c0, N0 = classify(V, 2016, 7, set(), cfg_t)
    assert (c0[np.isfinite(V[(2016, 7)][0])] == NO_HIST).all(), "pierwszy rok bez historii"
    _, res = d1_rows(pd.DataFrame(counts), "ndvi", cfg_t)
    assert res["show"] and 0.8 < res["low"]["value"] < 1.25 and 0.8 < res["high"]["value"] < 1.25, res
    # 3. trend w połowie winnicy (np. starzejące się krzewy): „najniżej” za często -> nie pokazujemy
    R2 = R.copy()
    yrs = sc["time"].dt.year.to_numpy()
    R2[:, rr < 10] -= 0.03 * (yrs - 2016)[:, None]
    V2 = month_values(R2, sc, 2)
    counts2 = []
    for (y, m) in V2:
        c, N = classify(V2, y, m, set(), cfg_t)
        valid = np.isin(c, (LOW, IN_RANGE, HIGH))
        if valid.any() and 6 <= m <= 9:
            counts2.append({"site_id": "X", "month": f"{y}-{m:02d}", "year": y, "n": int(valid.sum()),
                            "low": int((c == LOW).sum()), "high": int((c == HIGH).sum()), "low_spot": 0,
                            "high_spot": 0, "expected": float(np.sum(1.0 / (N[valid] + 1))), "soil": 50.0})
    _, res2 = d1_rows(pd.DataFrame(counts2), "ndvi", cfg_t)
    assert not res2["show"] and res2["low"]["value"] > 2, res2
    # 4. reset po przesadzeniu: rok przesadzenia bez klasy, potem historia tylko z lat po nim
    c, N = classify(V, 2022, 7, {2019}, cfg_t)
    assert (N[np.isfinite(V[(2022, 7)][0])] <= 2).all() and not np.isin(c, (LOW, HIGH, IN_RANGE)).any()
    c, _ = classify(V, 2019, 7, {2019}, cfg_t)
    assert (c[np.isfinite(V[(2019, 7)][0])] == REPLANT).all()
    c, N = classify(V, 2024, 7, {2019}, cfg_t)
    assert (N[np.isfinite(V[(2024, 7)][0])] == 4).all(), "historia 2020–2023 po przesadzeniu w 2019"
    # 5. plamy: pojedynczy kwadrat „najniżej” znika, blok 2×2 zostaje
    c = np.full(400, IN_RANGE, np.int8)
    c[(rr == 3) & (cc == 3)] = LOW
    blk = (rr >= 10) & (rr < 12) & (cc >= 10) & (cc < 12)
    c[blk] = LOW
    s = spots(c, rr, cc, 4)
    assert s[(rr == 3) & (cc == 3)][0] == IN_RANGE and (s[blk] == LOW).all()
    print(f"[OK] W3d (step_14): mediana miesiąca (≥ 2 dni), klasa od N ≥ 4 lat, reset po przesadzeniu, plamy ≥ 4; "
          f"sam szum: iloraz „najniżej” {res['low']['value']:.2f} (pokazujemy), trend w części winnicy: "
          f"{res2['low']['value']:.2f} (nie pokazujemy).")
