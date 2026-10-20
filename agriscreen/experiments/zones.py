"""
================================================================================
STREFA „GORSZA NIŻ ZWYKLE” (W3c)
================================================================================
Protokół: docs/evidence/W3c_protokol_strefy.md (zarejestrowany 2026-10-20, D-090). Numery § w komentarzach
odnoszą się do niego.

Pytanie: czy to miejsce w winnicy jest dziś słabsze (suchsze) względem reszty tej samej działki, niż zwykle o tej
porze roku? Porównanie zdjęć satelitarnych, bez oceny stanu winorośli.

  1. Magazyn (w3c_store.npz, przyrostowo): dla każdej czystej sceny i winnicy z QC strefa dnia
     r = wskaźnik − mediana działki, wygładzona oknem 3×3 (§2.1–2.2), w pikselach pasa 20 m.
  2. Norma miejsca z 5 lat wcześniejszych (±15 dni, reguła toru jak W3b) i odchylenie Δ = r − μ (§2.3–2.4).
  3. Z1: szum z par scen bez deszczu -> próg T (§3, §4). Z2: jak często mapa świeci (§5). Kryterium (§6).
  4. Strefy ≥ 4 komórki (8 sąsiadów) i „nowa / potwierdzona” w 10 dni wstecz (§4).
Wyniki: w3c_tests.csv, w3c_summary.csv, w3c_zones.npz (kody komórek do mapy panelu), w3c_freeze.json.
================================================================================
"""

from __future__ import annotations
import glob
import hashlib
import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from agriscreen import metrics
from agriscreen import parcel

logger = logging.getLogger("agriscreen.experiments.zones")


CODE_VERSION = "1.0"


WINDOW_MARGIN_M = 60.0       # okno odczytu = winnice ± 60 m (sąsiedzi 3×3 i zapas na zaokrąglenie siatki)


STORE_NAME, ZONES_NAME = "w3c_store.npz", "w3c_zones.npz"


TESTS_NAME, SUMMARY_NAME, FREEZE_NAME = "w3c_tests.csv", "w3c_summary.csv", "w3c_freeze.json"


PRODUCT = "S2_10m_zones"


# kody komórek mapy (§4, §7)
NO_DATA, USUAL, WEAK_NEW, WEAK_CONF, STRONG_NEW, STRONG_CONF, NO_NORM = -1, 0, 1, 2, 3, 4, 9


def smooth3(raw: np.ndarray, valid: np.ndarray, min_valid: int) -> np.ndarray:
    """Średnia z okna 3×3 tylko z ważnych pikseli; NaN, gdy ważnych < min_valid (§2.2)."""
    h, w = raw.shape
    v = np.pad(np.where(valid, raw, 0.0).astype("float64"), 1)
    c = np.pad(valid.astype("float64"), 1)
    s = sum(v[i:i + h, j:j + w] for i in range(3) for j in range(3))
    n = sum(c[i:i + h, j:j + w] for i in range(3) for j in range(3))
    return np.where(n >= min_valid, s / np.maximum(n, 1.0), np.nan)


def day_zone(index: np.ndarray, inner: np.ndarray, clear: np.ndarray, min_valid: int) -> np.ndarray:
    """Strefa dnia r (§2.1–2.2): wskaźnik minus mediana czystych pikseli pasa, wygładzony 3×3 w obrębie pasa."""
    ok = inner & clear & np.isfinite(index)
    if not ok.any():
        return np.full(index.shape, np.nan)
    raw = index - float(np.median(index[ok]))
    return smooth3(raw, ok, min_valid)


def _params(cfg: Dict[str, Any], kind: str = "rel") -> Dict[str, Any]:
    """Ustawienia, od których zależy zawartość magazynu; inne = magazyn liczony od nowa."""
    extra = {} if kind == "rel" else {"kind": kind}           # W3c bez zmian; W3d: wartości bezwzględne
    return {**extra, "code": CODE_VERSION, "inner_m": float(cfg["PARCEL_INNER_M"]), "min_px": int(cfg["PARCEL_MIN_PX"]),
            "indices": list(cfg["ZONES_INDICES"]), "min_valid": int(cfg["ZONES_SMOOTH_MIN"]),
            "clear": float(cfg["VEG_MIN_CLEAR_FRAC"]), "parcels": os.path.basename(cfg["PARCELS_PATH"]),
            "type": cfg["PARCEL_TYPE"]}


def load_store(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.exists(path):
        return None
    with np.load(path, allow_pickle=False) as z:
        st = {k: z[k] for k in z.files}
    st["params"] = json.loads(str(st["params"]))
    st["sites"] = [str(s) for s in st["sites"]]
    st["scenes"] = [str(s) for s in st["scenes"]]
    st["skipped"] = [str(s) for s in st["skipped"]]
    return st


def _save_store(path: str, st: Dict[str, Any]) -> None:
    out = {k: v for k, v in st.items() if k not in ("params", "sites", "scenes", "skipped")}
    out.update(params=np.array(json.dumps(st["params"])), sites=np.array(st["sites"], dtype=str),
               scenes=np.array(st["scenes"], dtype=str), skipped=np.array(st["skipped"], dtype=str))
    tmp = path + ".tmp.npz"
    np.savez_compressed(tmp, **out)
    os.replace(tmp, path)


def update_store(cfg: Dict[str, Any], path: str, save_every: int = 50, kind: str = "rel") -> Dict[str, Any]:
    """
    Magazyn stref dnia (przyrostowo, zapis co save_every scen): okno wokół winnic z pierwszej sceny, piksele pasa
    PARCEL_INNER_M winnic z ≥ PARCEL_MIN_PX pikseli (QC jak W3b), dla każdej sceny udział czystych pikseli pasa
    i r(x, t) dla ZONES_INDICES (NaN, gdy scena działki nie jest czysta). Scena z siatką przesuniętą o
    > ZONES_GRID_TOL_M wypada (lista `skipped`, §0). kind="abs" (W3d): zamiast r zapisuje sam wskaźnik wygładzony
    3×3 (bez odejmowania mediany działki), pod tymi samymi kluczami r_<indeks>.
    """
    import rasterio
    from rasterio.features import rasterize
    from rasterio.windows import from_bounds

    scenes = sorted(glob.glob(os.path.join(cfg["S2_DIR"], "S2_L2A_*.tif")))
    if not scenes:
        raise RuntimeError("Brak scen w S2_DIR.")
    params, keys = _params(cfg, kind), list(cfg["ZONES_INDICES"])
    st = load_store(path)
    if st is not None and st["params"] != params:
        logger.info("W3c: zmienione ustawienia magazynu — liczę od nowa")
        st = None
    if st is None:
        with rasterio.open(scenes[0]) as src:
            geo = metrics.load_parcels(cfg, src.crs)
            x0, y0, x1, y1 = geo.total_bounds
            box = (x0 - WINDOW_MARGIN_M, y0 - WINDOW_MARGIN_M, x1 + WINDOW_MARGIN_M, y1 + WINDOW_MARGIN_M)
            win = from_bounds(*box, src.transform).round_offsets().round_lengths()
            tr, crs = src.window_transform(win), src.crs.to_wkt()
        shape = (int(win.height), int(win.width))
        pix, site_idx, sites = [], [], []
        for r in geo.itertuples():
            g = r.geometry.buffer(-float(cfg["PARCEL_INNER_M"]))
            m = (rasterize([(g, 1)], out_shape=shape, transform=tr, fill=0).astype(bool) if not g.is_empty
                 else np.zeros(shape, bool))
            if m.sum() < int(cfg["PARCEL_MIN_PX"]):
                continue
            f = np.flatnonzero(m.ravel())
            pix.append(f)
            site_idx.append(np.full(len(f), len(sites)))
            sites.append(r.site_id)
        st = {"params": params, "box": np.array(box), "transform": np.array(tr[:6]), "shape": np.array(shape),
              "crs": np.array(crs), "pix": np.concatenate(pix), "site_idx": np.concatenate(site_idx), "sites": sites,
              "scenes": [], "skipped": [], "clear": np.zeros((0, len(sites)), "float32"),
              **{f"r_{k}": np.zeros((0, sum(len(p) for p in pix)), "float32") for k in keys}}
    from affine import Affine
    tr = Affine(*st["transform"])
    shape = tuple(int(v) for v in st["shape"])
    box = tuple(float(v) for v in st["box"])
    tol = float(cfg.get("ZONES_GRID_TOL_M", 1.0))
    masks = []
    for j in range(len(st["sites"])):
        m = np.zeros(shape[0] * shape[1], bool)
        m[st["pix"][st["site_idx"] == j]] = True
        masks.append(m.reshape(shape))
    done = set(st["scenes"]) | set(st["skipped"])
    todo = [p for p in scenes if os.path.basename(p) not in done]
    new_clear, new_r, new_names = [], {k: [] for k in keys}, []

    def flush():
        if not new_names:
            return
        st["scenes"] += new_names
        st["clear"] = np.vstack([st["clear"], np.array(new_clear, "float32")])
        for k in keys:
            st[f"r_{k}"] = np.vstack([st[f"r_{k}"], np.array(new_r[k], "float32")])
        _save_store(path, st)
        new_names.clear(), new_clear.clear()
        for k in keys:
            new_r[k].clear()
    for n_done, p in enumerate(todo, 1):
        name = os.path.basename(p)
        with rasterio.open(p) as src:
            win = from_bounds(*box, src.transform).round_offsets().round_lengths()
            t2 = src.window_transform(win)
            if (src.crs.to_wkt() != str(st["crs"]) or (int(win.height), int(win.width)) != shape
                    or abs(t2.c - tr.c) > tol or abs(t2.f - tr.f) > tol or abs(t2.a - tr.a) > 1e-6):
                st["skipped"].append(name)
                continue
            data = src.read(window=win, boundless=True, fill_value=np.nan).astype("float32")
            if src.nodata is not None and np.isfinite(src.nodata):
                data[data == src.nodata] = np.nan
        cloud = np.nan_to_num(data[metrics.RASTER_CLOUD_BAND], nan=1.0)
        clear = (cloud == 0) & np.isfinite(data[:10]).all(axis=0)
        idx = metrics.compute_indices(data[:10])
        rows = {k: np.full(len(st["pix"]), np.nan, "float32") for k in keys}
        cf = []
        for j, m in enumerate(masks):
            frac = float(clear[m].mean())
            cf.append(frac)
            if frac < float(cfg["VEG_MIN_CLEAR_FRAC"]):
                continue
            sel = st["site_idx"] == j
            for k in keys:
                if kind == "rel":
                    v = day_zone(idx[k], m, clear, int(cfg["ZONES_SMOOTH_MIN"]))
                else:
                    v = smooth3(idx[k], m & clear & np.isfinite(idx[k]), int(cfg["ZONES_SMOOTH_MIN"]))
                rows[k][sel] = v.ravel()[st["pix"][sel]]
        new_names.append(name)
        new_clear.append(cf)
        for k in keys:
            new_r[k].append(rows[k])
        if n_done % save_every == 0:
            flush()
    flush()
    if not os.path.exists(path):
        _save_store(path, st)
    st["n_new"] = len(todo)
    return st


def parcel_scenes(st: Dict[str, Any], j: int, cfg: Dict[str, Any]) -> pd.DataFrame:
    """Czyste sceny działki j, jedna na dzień (większy udział czystych pikseli), z torem orbity (§1)."""
    t = pd.Series([metrics.scene_time(n) for n in st["scenes"]], dtype="datetime64[ns]")
    d = pd.DataFrame({"row": np.arange(len(t)), "time": t, "clear": st["clear"][:, j] if len(t) else []})
    d = d[d["clear"] >= float(cfg["VEG_MIN_CLEAR_FRAC"])]
    d = d.assign(day=d["time"].dt.normalize()).sort_values(["day", "clear"], ascending=[True, False])
    d = d.drop_duplicates("day").sort_values("time").reset_index(drop=True)
    d["track"] = metrics.track_ids(d["time"]) if len(d) else []
    return d


def norm_delta(R: np.ndarray, sc: pd.DataFrame, cfg: Dict[str, Any]) -> Tuple[np.ndarray, pd.DataFrame]:
    """
    Δ = r − μ (§2.3–2.4). μ: średnia r z czystych scen z lat Y−5…Y−1 w oknie ±VEG_HALF_WINDOW_DAYS dni roku; ten sam
    tor, gdy w puli jest ≥ VEG_MIN_REF scen, inaczej oba tory. Komórka ma normę przy ≥ ZONES_MIN_SCENES wartościach
    z ≥ ZONES_MIN_YEARS różnych lat. Zwraca Δ (sceny × komórki) i opis puli każdej sceny.
    """
    n, m = R.shape
    D = np.full((n, m), np.nan)
    doy, yr = sc["time"].dt.dayofyear.to_numpy(), sc["time"].dt.year.to_numpy()
    trk = sc["track"].to_numpy()
    y_back, half, min_ref = int(cfg["VEG_REF_YEARS"]), int(cfg["VEG_HALF_WINDOW_DAYS"]), int(cfg["VEG_MIN_REF"])
    min_sc, min_yr = int(cfg["ZONES_MIN_SCENES"]), int(cfg["ZONES_MIN_YEARS"])
    info = []
    for i in range(n):
        cand = (yr < yr[i]) & (yr >= yr[i] - y_back) & (metrics._circ_doy_dist(doy, doy[i]) <= half)
        same = cand & (trk == trk[i])
        use, mode = (same, "same_track") if same.sum() >= min_ref else (cand, "all_tracks")
        if use.sum() < min_sc:
            info.append({"ref_mode": "", "n_pool": int(use.sum()), "med_ref_scenes": np.nan, "med_ref_years": np.nan})
            continue
        X = R[use]
        ok = np.isfinite(X)
        cnt = ok.sum(axis=0)
        yrs = np.zeros(m, int)
        for y in np.unique(yr[use]):
            yrs += ok[yr[use] == y].any(axis=0)
        valid = (cnt >= min_sc) & (yrs >= min_yr)
        mu = np.where(cnt > 0, np.nansum(np.where(ok, X, 0.0), axis=0) / np.maximum(cnt, 1), np.nan)
        D[i] = np.where(valid, R[i] - mu, np.nan)
        info.append({"ref_mode": mode, "n_pool": int(use.sum()),
                     "med_ref_scenes": float(np.median(cnt[valid])) if valid.any() else np.nan,
                     "med_ref_years": float(np.median(yrs[valid])) if valid.any() else np.nan})
    return D, pd.DataFrame(info)


def zone_masks(delta: np.ndarray, rr: np.ndarray, cc: np.ndarray, T: float, min_cells: int
               ) -> Tuple[np.ndarray, np.ndarray]:
    """Komórki w strefach (§4, U6): Δ ≤ −T (słabsze) / Δ ≥ +T (mocniejsze), zwarte grupy ≥ min_cells, 8 sąsiadów."""
    from scipy import ndimage
    out = []
    if not np.isfinite(T):
        return np.zeros(len(delta), bool), np.zeros(len(delta), bool)
    r0, c0 = rr.min(), cc.min()
    shape = (rr.max() - r0 + 1, cc.max() - c0 + 1)
    with np.errstate(invalid="ignore"):
        flags = (delta <= -T, delta >= T)
    for f in flags:
        g = np.zeros(shape, bool)
        g[rr - r0, cc - c0] = f
        lab, _ = ndimage.label(g, structure=np.ones((3, 3), int))
        sizes = np.bincount(lab.ravel())
        keep = sizes >= min_cells
        keep[0] = False
        out.append(keep[lab][rr - r0, cc - c0])
    return out[0], out[1]


def confirm(days: pd.Series, zones: np.ndarray, window: int) -> np.ndarray:
    """U7: komórka strefy potwierdzona, gdy była w strefie tego samego kierunku w innej czystej scenie z ostatnich
    `window` dni przed t (tylko wstecz)."""
    d = pd.to_datetime(days).to_numpy()
    out = np.zeros_like(zones)
    for i in range(len(d)):
        prev = (d < d[i]) & (d >= d[i] - np.timedelta64(int(window), "D"))
        if prev.any():
            out[i] = zones[i] & zones[prev].any(axis=0)
    return out


def cell_codes(delta: np.ndarray, r: np.ndarray, weak: np.ndarray, strong: np.ndarray, weak_c: np.ndarray,
               strong_c: np.ndarray) -> np.ndarray:
    """Kody komórek mapy (§7) dla jednej sceny działki."""
    c = np.full(len(delta), NO_DATA, np.int8)
    c[np.isfinite(r)] = NO_NORM
    c[np.isfinite(delta)] = USUAL
    c[weak], c[weak & weak_c] = WEAK_NEW, WEAK_CONF
    c[strong], c[strong & strong_c] = STRONG_NEW, STRONG_CONF
    return c


def pair_rows(D: np.ndarray, sc: pd.DataFrame, rain: pd.Series, cfg: Dict[str, Any], site: str) -> List[Dict[str, Any]]:
    """Pary scen Z1 (§3): G5 ten sam tor 4–6 dni, G13 różne tory 1–3 dni, opad < PARCEL_RAIN_MM, VI–IX.
    Na parę: suma d² i liczba komórek z Δ w obu scenach."""
    m0, m1 = cfg["PARCEL_TEST_MONTHS"]
    day = sc["time"].dt.normalize().to_numpy()
    mon = sc["time"].dt.month.to_numpy()
    trk = sc["track"].to_numpy()
    out = []
    for i in range(len(sc)):
        if not (m0 <= mon[i] <= m1):
            continue
        for j in range(i + 1, len(sc)):
            dt = int((day[j] - day[i]) / np.timedelta64(1, "D"))
            if dt > 6:
                break
            if not (m0 <= mon[j] <= m1):
                continue
            same = trk[i] == trk[j]
            grp = "G5" if same and 4 <= dt <= 6 else ("G13" if not same and 1 <= dt <= 3 else None)
            if grp is None:
                continue
            p = float(rain.loc[day[i]:day[j]].sum())
            if p >= float(cfg["PARCEL_RAIN_MM"]):
                continue
            d = D[j] - D[i]
            d = d[np.isfinite(d)]
            if len(d):
                out.append({"site_id": site, "t1": day[i], "group": grp, "year": pd.Timestamp(day[i]).year,
                            "ssq": float(np.sum(d ** 2)), "n": int(len(d))})
    return out


def _mdc(q: pd.DataFrame) -> float:
    return float(1.96 * np.sqrt(q["ssq"].sum() / q["n"].sum())) if len(q) and q["n"].sum() else np.nan


def _share(q: pd.DataFrame, col: str) -> float:
    return float(q[col].sum() / q["n"].sum()) if len(q) and q["n"].sum() else np.nan


def z1_threshold(pairs: pd.DataFrame, index: str, cfg: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Z1 (§3) i próg T (§4, U2): MDC95 G5, gdy ≥ ZONES_MIN_PAIRS par, inaczej G13; opisowo MDC per rok."""
    rows: List[Dict[str, Any]] = []
    prod = f"{PRODUCT}_{index.upper()}"
    res: Dict[str, Any] = {"T": np.nan, "group": "", "hi": np.nan, "n_pairs": 0}
    min_pairs = int(cfg["ZONES_MIN_PAIRS"])
    for grp, label in (("G5", "ten sam tor, 4–6 dni"), ("G13", "różne tory, 1–3 dni")):
        q = pairs[pairs["group"] == grp] if len(pairs) else pairs
        key = f"z1_{grp.lower()}_{index}"
        if len(q) < min_pairs:
            rows.append(parcel._row("Z1", parcel.PARCELS, prod, "", f"{grp} ({label}), bez opadu", "mdc95_value", np.nan,
                                 days=q["t1"] if len(q) else [], verdict="za mało par", key=key))
            continue
        m, lo, hi, _ = parcel.jackknife_ci(q, _mdc, bounds=(0, np.inf))
        rows.append(parcel._row("Z1", parcel.PARCELS, prod, "", f"{grp} ({label}), bez opadu", "mdc95_value", m, (lo, hi),
                             q["t1"], n_parcels=q["site_id"].nunique(), key=key))
        if not res["group"]:
            res = {"T": m, "group": grp, "hi": hi, "n_pairs": len(q)}
            for y, g in q.groupby("year"):
                rows.append(parcel._row("Z1", parcel.PARCELS, prod, "", f"{grp}, rok {y} (opisowo)", "mdc95_value", _mdc(g),
                                     days=g["t1"], n_parcels=g["site_id"].nunique()))
    rows.append(parcel._row("Z1", parcel.PARCELS, prod, "", f"próg mapy T (z {res['group'] or '—'})", "threshold_T",
                         res["T"], n=res["n_pairs"], verdict="" if res["group"] else "brak progu",
                         key=f"z_T_{index}"))
    return rows, res


def z2_rows(counts: pd.DataFrame, index: str, cfg: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Z2 (§5): udział komórek w strefach; podstawa warunku 3 (§6): gleba w normie, a gdy jej dni są w < 3 latach —
    wszystkie dni VI–IX."""
    rows: List[Dict[str, Any]] = []
    prod = f"{PRODUCT}_{index.upper()}"
    res: Dict[str, Any] = {"value": np.nan, "hi": np.nan, "basis": ""}
    if counts.empty:
        rows.append(parcel._row("Z2", parcel.PARCELS, prod, "", "brak scen z normą", "share_zones", np.nan,
                             verdict="brak danych", key=f"z2_normal_{index}"))
        return rows, res
    normal = counts[counts["soil_normal"]]
    basis = normal if normal["year"].nunique() >= 3 else counts
    res["basis"] = "gleba w normie" if basis is normal else "wszystkie dni VI–IX (dni z glebą w normie w < 3 latach)"
    for sub, q in (("gleba w normie", normal), ("wszystkie dni VI–IX", counts)):
        for col, what in (("both", "oba kierunki"), ("weak", "słabsze"), ("strong", "mocniejsze"),
                          ("raw_both", "oba kierunki, przed U6")):
            key = ""
            if col == "both" and q is basis:
                key = f"z2_normal_{index}"
            m, lo, hi, _ = parcel.jackknife_ci(q, lambda g, c=col: _share(g, c), bounds=(0, 1))
            rows.append(parcel._row("Z2", parcel.PARCELS, prod, "", f"{sub}, strefy {what}", "share_cells", m, (lo, hi),
                                 q["time"], n_parcels=q["site_id"].nunique(), key=key,
                                 verdict=("podstawa warunku 3" if key else "")))
            if key:
                res.update(value=m, hi=hi)
    return rows, res


def criterion_row(index: str, z1: Dict[str, Any], spread: float, z2: Dict[str, Any], cfg: Dict[str, Any]
                  ) -> Dict[str, Any]:
    """Kryterium pokazania warstwy (§6): trzy warunki; werdykt podaje, który nie przeszedł i z jakimi liczbami."""
    why = []
    if not z1["group"]:
        why.append(f"1: za mało par (< {int(cfg['ZONES_MIN_PAIRS'])}) w G5 i G13")
    lim = float(cfg["ZONES_SPREAD_FRAC"]) * spread if np.isfinite(spread) else np.nan
    if z1["group"] and not (np.isfinite(z1["hi"]) and np.isfinite(lim) and z1["hi"] < lim):
        why.append(f"2: MDC95 górna {z1['hi']:.3f} ≥ ½ rozstępu działki {lim:.3f}" if np.isfinite(z1["hi"])
                   and np.isfinite(lim) else "2: brak przedziału MDC95 albo rozstępu (za mało lat)")
    max_share = float(cfg["ZONES_MAX_SHARE"])
    if z1["group"] and not (np.isfinite(z2["hi"]) and z2["hi"] <= max_share):
        why.append(f"3: udział komórek w strefach ({z2['basis']}) górna {100 * z2['hi']:.1f}% > "
                   f"{100 * max_share:.0f}%" if np.isfinite(z2["hi"]) else "3: brak przedziału udziału (za mało lat)")
    ok = not why
    return parcel._row("Z", parcel.PARCELS, f"{PRODUCT}_{index.upper()}", "", "kryterium pokazania warstwy (§6)", "show",
                    1.0 if ok else 0.0, criterion=True, verdict="pokazujemy" if ok else "nie pokazujemy — " +
                    "; ".join(why), key=f"z_show_{index}")


def freeze_info(cfg: Dict[str, Any], out_dir: str) -> Dict[str, Any]:
    """Zamrożenie testów W3c (§0): W3C_FREEZE z konfiguracji albo ostatnia scena przy pierwszym liczeniu."""
    path = os.path.join(out_dir, FREEZE_NAME)
    names = sorted(os.path.basename(p) for p in glob.glob(os.path.join(cfg["S2_DIR"], "S2_L2A_*.tif")))
    saved = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else None
    if cfg.get("W3C_FREEZE"):
        freeze, source = str(cfg["W3C_FREEZE"])[:10], "konfiguracja"
    elif saved:
        freeze, source = saved["freeze"], FREEZE_NAME
    else:
        freeze, source = f"{metrics.scene_time(names[-1]):%Y-%m-%d}", "ostatnia scena przy pierwszym liczeniu"
    frozen = [n for n in names if metrics.scene_time(n).normalize() <= pd.Timestamp(freeze)]
    sha = hashlib.sha256("\n".join(frozen).encode("utf-8")).hexdigest()
    info = {"freeze": freeze, "source": source, "n_scenes": len(frozen), "scenes_sha256": sha,
            "scenes_sha256_at_freeze": (saved or {}).get("scenes_sha256", sha)}
    if saved is None and not cfg.get("W3C_FREEZE"):
        os.makedirs(out_dir, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(dict(info, created_utc=pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%dT%H:%M:%SZ")), f, indent=1)
    return info


def run_zones(cfg: Dict[str, Any], out_dir: str, era5: pd.DataFrame, commit: str = "") -> Dict[str, Any]:
    """Liczy W3c od magazynu do plików wynikowych; zwraca podsumowanie do komunikatu zadania."""
    store = update_store(cfg, os.path.join(out_dir, STORE_NAME))
    fz = freeze_info(cfg, out_dir)
    proto = parcel.protocol_sha(cfg["W3C_PROTOCOL"])
    freeze = pd.Timestamp(fz["freeze"])
    e = era5.set_index(pd.to_datetime(era5["time"]).dt.floor("D")).sort_index()
    rain = e[~e.index.duplicated(keep="last")]["precip_mm"].astype(float)
    soil = parcel.soil_pct(era5, cfg)
    m0, m1 = cfg["PARCEL_TEST_MONTHS"]
    n_pix = len(store["pix"])
    width = int(store["shape"][1])
    rr_all, cc_all = store["pix"] // width, store["pix"] % width
    zones: Dict[str, Any] = {k: store[k] for k in ("transform", "shape", "crs", "pix", "site_idx")}
    zones.update(sites=np.array(store["sites"], dtype=str), scenes=np.array(store["scenes"], dtype=str))
    rows: List[Dict[str, Any]] = []
    summary: List[Dict[str, Any]] = []
    result: Dict[str, Any] = {"n_scenes": len(store["scenes"]), "n_new": store.get("n_new", 0),
                              "n_skipped": len(store["skipped"]), "sites": len(store["sites"]), "show": {}}
    for k in cfg["ZONES_INDICES"]:
        R_all = store[f"r_{k}"]
        per_site = []
        pairs: List[Dict[str, Any]] = []
        spreads: List[float] = []
        for j, sid in enumerate(store["sites"]):
            sel = np.flatnonzero(store["site_idx"] == j)
            sc = parcel_scenes(store, j, cfg)
            R = R_all[sc["row"].to_numpy()][:, sel] if len(sc) else np.zeros((0, len(sel)))
            D, info = norm_delta(R, sc, cfg) if len(sc) else (np.zeros((0, len(sel))), pd.DataFrame())
            per_site.append((j, sid, sel, sc, R, D, info))
            test = (sc["time"].dt.normalize() <= freeze) & sc["time"].dt.month.between(m0, m1) if len(sc) else []
            for i in np.flatnonzero(np.asarray(test)):
                v = R[i][np.isfinite(R[i])]
                if len(v) >= 2:
                    spreads.append(float(np.percentile(v, 90) - np.percentile(v, 10)))
            keep = (sc["time"].dt.normalize() <= freeze).to_numpy() if len(sc) else np.zeros(0, bool)
            pairs += pair_rows(D[keep], sc[keep].reset_index(drop=True), rain, cfg, sid)
        pairs_df = pd.DataFrame(pairs, columns=["site_id", "t1", "group", "year", "ssq", "n"])
        r1, z1 = z1_threshold(pairs_df, k, cfg)
        rows += r1
        spread = float(np.median(spreads)) if spreads else np.nan
        rows.append(parcel._row("Z", parcel.PARCELS, f"{PRODUCT}_{k.upper()}", "", "typowy rozstęp p90 − p10 strefy dnia "
                             "w działce (mediana, VI–IX)", "spread_p90_p10", spread, n=len(spreads), key=f"z_spread_{k}"))
        T = z1["T"]
        codes = np.full((len(store["scenes"]), n_pix), NO_DATA, np.int8)
        delta = np.full((len(store["scenes"]), n_pix), np.nan, np.float16)
        counts = []
        for j, sid, sel, sc, R, D, info in per_site:
            if not len(sc):
                continue
            rr, cc = rr_all[sel], cc_all[sel]
            zw, zs = np.zeros(D.shape, bool), np.zeros(D.shape, bool)
            zw_raw, zs_raw = np.zeros(D.shape, bool), np.zeros(D.shape, bool)
            for i in range(len(sc)):
                zw[i], zs[i] = zone_masks(D[i], rr, cc, T, int(cfg["ZONES_MIN_CELLS"]))
                if np.isfinite(T):
                    with np.errstate(invalid="ignore"):
                        zw_raw[i], zs_raw[i] = D[i] <= -T, D[i] >= T
            cw = confirm(sc["time"], zw, int(cfg["ZONES_CONFIRM_DAYS"]))
            cs = confirm(sc["time"], zs, int(cfg["ZONES_CONFIRM_DAYS"]))
            for i, row in enumerate(sc["row"].to_numpy()):
                c = cell_codes(D[i], R[i], zw[i], zs[i], cw[i], cs[i])
                codes[row, sel] = c
                delta[row, sel] = D[i].astype(np.float16)
                nd = int(np.isfinite(D[i]).sum())
                t = sc["time"].iat[i]
                summary.append({"site_id": sid, "time": t.strftime("%Y-%m-%dT%H:%M:%S"), "scene": store["scenes"][row],
                                "index": k, "n_cells": int(np.isfinite(R[i]).sum()), "n_norm": nd,
                                "weak": int(zw[i].sum()), "weak_conf": int((zw[i] & cw[i]).sum()),
                                "strong": int(zs[i].sum()), "strong_conf": int((zs[i] & cs[i]).sum()),
                                "ref_mode": info["ref_mode"].iat[i], "med_ref_scenes": info["med_ref_scenes"].iat[i],
                                "med_ref_years": info["med_ref_years"].iat[i]})
                if nd and t.normalize() <= freeze and m0 <= t.month <= m1:
                    p = soil.get(t.normalize(), np.nan)
                    counts.append({"site_id": sid, "time": t.normalize(), "year": t.year, "n": nd,
                                   "weak": int(zw[i].sum()), "strong": int(zs[i].sum()),
                                   "both": int(zw[i].sum() + zs[i].sum()),
                                   "raw_both": int(zw_raw[i].sum() + zs_raw[i].sum()),
                                   "soil_normal": bool(np.isfinite(p) and 30 <= p <= 70)})
        r2, z2 = z2_rows(pd.DataFrame(counts), k, cfg)
        rows += r2
        crit = criterion_row(k, z1, spread, z2, cfg)
        rows.append(crit)
        zones[f"codes_{k}"], zones[f"delta_{k}"] = codes, delta
        zones[f"T_{k}"], zones[f"show_{k}"] = np.array(T), np.array(bool(crit["value"] == 1.0))
        result["show"][k] = crit["verdict"]
    tests = pd.DataFrame(rows, columns=parcel.TEST_COLS).assign(
        protocol_sha256=proto["sha256"], protocol_status=proto["status"], protocol_registered=proto["registered"],
        freeze=fz["freeze"], scenes=fz["n_scenes"], scenes_sha256=fz["scenes_sha256"], code_version=CODE_VERSION,
        code_commit=commit)
    os.makedirs(out_dir, exist_ok=True)
    tests.to_csv(os.path.join(out_dir, TESTS_NAME), index=False)
    pd.DataFrame(summary).to_csv(os.path.join(out_dir, SUMMARY_NAME), index=False)
    np.savez_compressed(os.path.join(out_dir, ZONES_NAME), **zones)
    result.update(freeze=fz, protocol=proto)
    return result


def load_zones(out_dir: str) -> Optional[Dict[str, Any]]:
    """Wyniki W3c do panelu: kody komórek, progi, decyzja o pokazaniu, podsumowanie scen. None, gdy brak."""
    p = os.path.join(out_dir, ZONES_NAME)
    if not os.path.exists(p):
        return None
    with np.load(p, allow_pickle=False) as z:
        d = {k: z[k] for k in z.files}
    d["scenes"] = [str(s) for s in d["scenes"]]
    d["sites"] = [str(s) for s in d["sites"]]
    sp = os.path.join(out_dir, SUMMARY_NAME)
    d["summary"] = pd.read_csv(sp) if os.path.exists(sp) and os.path.getsize(sp) > 1 else pd.DataFrame()
    return d


def _selftest(cfg: Dict[str, Any]) -> None:
    """
    Testy jednostkowe na danych syntetycznych: wygładzenie 3×3 (≥ 5 z 9), mediana dnia usuwa przesunięcie całej
    działki, norma z lat wcześniejszych i minimum lat, MDC z par ≈ 1,96·√2·σ (σ po wygładzeniu), wykrycie
    wstrzykniętej strefy i jej potwierdzenie w drugiej scenie, U6 odrzuca pojedynczą komórkę, szum rzadko świeci.
    """
    rng = np.random.default_rng(7)
    # 1. wygładzenie: średnia z ważnych, NaN przy < 5 z 9
    a = np.arange(16, dtype=float).reshape(4, 4)
    v = np.ones((4, 4), bool)
    s = smooth3(a, v, 5)
    assert np.isnan(s[0, 0]) and np.isclose(s[1, 1], a[0:3, 0:3].mean()), s
    v2 = v.copy()
    v2[0, :] = False
    assert np.isclose(smooth3(a, v2, 5)[1, 1], a[1:3, 0:3].mean())
    # 2. strefa dnia: przesunięcie całej działki (pogoda) znika
    inner = np.zeros((12, 12), bool)
    inner[2:10, 2:10] = True
    clear = np.ones((12, 12), bool)
    base = rng.normal(0.5, 0.02, (12, 12))
    assert np.allclose(day_zone(base, inner, clear, 5), day_zone(base + 0.2, inner, clear, 5), equal_nan=True)
    # 3. syntetyczna działka 16×16 komórek, 7 sezonów, sceny co 2–3 dni VI–IX, wzór stały + szum σ
    cfg_t = dict(cfg, VEG_REF_YEARS=5, VEG_HALF_WINDOW_DAYS=15, VEG_MIN_REF=5, ZONES_MIN_SCENES=5, ZONES_MIN_YEARS=3,
                 PARCEL_TEST_MONTHS=(6, 9), PARCEL_RAIN_MM=5.0, ZONES_MIN_CELLS=4, ZONES_MIN_PAIRS=30,
                 VEG_MIN_CLEAR_FRAC=0.9)
    rr, cc = np.divmod(np.arange(256), 16)
    pattern = 0.03 * np.sin(rr / 3.0) + 0.02 * np.cos(cc / 4.0)
    times = []
    for y in range(2018, 2025):
        d = pd.Timestamp(f"{y}-06-01")
        while d.month <= 9:
            times.append(d + pd.Timedelta(hours=10, minutes=59 if len(times) % 2 else 9))
            d += pd.Timedelta(days=int(rng.choice([2, 3])))
    sc = pd.DataFrame({"time": pd.to_datetime(times)})
    sc["track"] = metrics.track_ids(sc["time"])
    sigma = 0.01
    R = pattern + rng.normal(0, sigma, (len(sc), 256))
    blob = (rr >= 5) & (rr < 9) & (cc >= 5) & (cc < 9)              # 16 komórek
    lone = (rr == 13) & (cc == 2)                                    # pojedyncza komórka
    hit = np.flatnonzero((sc["time"].dt.year == 2024) & (sc["time"].dt.month == 8))[:2]
    R[np.ix_(hit, np.flatnonzero(blob))] -= 0.10
    R[np.ix_(hit, np.flatnonzero(lone))] -= 0.10
    D, info = norm_delta(R, sc, cfg_t)
    early = sc["time"].dt.year <= 2020
    assert np.isnan(D[early.to_numpy() & (sc["time"].dt.year == 2018).to_numpy()]).all(), "norma tylko z lat wcześniejszych"
    assert np.isfinite(D[(sc["time"].dt.year >= 2022).to_numpy()]).all(), "pełna norma od 3. roku historii"
    rain = pd.Series(0.0, index=pd.date_range("2018-01-01", "2024-12-31"))
    pr = pd.DataFrame(pair_rows(D, sc, rain, cfg_t, "X"))
    rows, z1 = z1_threshold(pr, "ndvi", cfg_t)
    expect = 1.96 * np.sqrt(2) * sigma * np.sqrt(1 + 1 / 8)          # norma z ok. 8 scen: wariancja Δ trochę większa
    assert z1["group"] and 0.6 * expect < z1["T"] < 1.6 * expect, (z1, expect)
    T = z1["T"]
    w, st_ = zone_masks(D[hit[0]], rr, cc, T, 4)
    assert w[blob].mean() > 0.9 and not w[lone].any(), "strefa wykryta, pojedyncza komórka odrzucona (U6)"
    zw = np.array([zone_masks(D[i], rr, cc, T, 4)[0] for i in range(len(sc))])
    cw = confirm(sc["time"], zw, 10)
    assert not cw[hit[0]][blob].any() and cw[hit[1]][blob].mean() > 0.9, "U7: nowa, potem potwierdzona"
    noise = np.flatnonzero((sc["time"].dt.year >= 2022).to_numpy())
    noise = np.setdiff1d(noise, hit)
    share = zw[noise].sum() / np.isfinite(D[noise]).sum()
    assert share < 0.01, share
    c = cell_codes(D[hit[1]], R[hit[1]], zw[hit[1]], np.zeros(256, bool), cw[hit[1]], np.zeros(256, bool))
    assert (c[blob] == WEAK_CONF).mean() > 0.9 and (c[~blob & ~lone] == USUAL).mean() > 0.95
    print(f"[OK] W3c (experiments/zones): wygładzenie 3×3, mediana dnia, norma z lat wcześniejszych (≥ 3 lata), T = {T:.4f} "
          f"(oczekiwane ok. {expect:.4f}), strefa wykryta i potwierdzona, pojedyncza komórka odrzucona, szum w strefach "
          f"{100 * share:.2f}% komórek.")
