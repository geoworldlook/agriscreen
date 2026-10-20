"""
Karta winnicy (W3b): zdania dla winiarza.

Klasa działki wobec własnej historii, zdania karty (EN dla panelu, PL zachowane), kategorie suszy gleby wg progów
US Drought Monitor, odczyt satelitarnego SWI. Logika i testy: parcel.py, protokół docs/evidence/W3b_protokol_walidacji.md.
"""

from __future__ import annotations
import logging
import os
from typing import Any, Dict, Optional
import numpy as np
import pandas as pd

logger = logging.getLogger("agriscreen.card")


def _num(x: Any, nd: int = 2) -> str:
    """Liczba z przecinkiem dziesiętnym i typograficznym minusem; brak = „—”."""
    try:
        if x is None or not np.isfinite(float(x)):
            return "—"
        v = round(float(x), nd) or 0.0              # bez „−0,00”
        return f"{v:.{nd}f}".replace(".", ",").replace("-", "−")
    except (TypeError, ValueError):
        return "—"


def days_pl(n: int) -> str:
    """„1 dzień”, „5 dni” (odmiana liczebnika dla dni)."""
    return f"{n} dzień" if abs(int(n)) == 1 else f"{n} dni"


def days_ago_pl(n: int) -> str:
    """„dziś”, „wczoraj”, „5 dni temu”."""
    n = int(n)
    return "dziś" if n == 0 else "wczoraj" if n == 1 else f"{days_pl(n)} temu"


def _float(x: Any) -> float:
    """Liczba albo NaN (brak kolumny w starszym CSV, pusta komórka)."""
    try:
        return float(x)
    except (TypeError, ValueError):
        return np.nan


# Kategorie z percentyla (≤ górna granica): progi i kolory US Drought Monitor; powyżej WATER_WET_PCT — wilgotniej
WATER_CATEGORIES = ((2, "D4", "wyjątkowa susza", "#730000"), (5, "D3", "skrajna susza", "#e60000"),
                    (10, "D2", "silna susza", "#ffaa00"), (20, "D1", "umiarkowana susza", "#fcd37f"),
                    (30, "D0", "nienormalnie sucho", "#ffff00"))


WATER_NORMAL = ("N", "w normie", "#cfe3c8")


WATER_WET = ("W", "wilgotniej niż zwykle", "#9cc3e6")


WATER_LABEL_EN = {"D4": "exceptional drought", "D3": "extreme drought", "D2": "severe drought",
                  "D1": "moderate drought", "D0": "abnormally dry", "N": "near normal", "W": "wetter than usual"}


def plural_pl(n: int, one: str, few: str, many: str) -> str:
    """Odmiana rzeczownika po liczebniku: 1 rok, 2–4 lata (bez 12–14), 5+ lat."""
    n = abs(int(n))
    if n == 1:
        return one
    return few if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14) else many


def water_category(pct: Any, cfg: Dict[str, Any]) -> tuple:
    """(kod, etykieta PL, kolor) z percentyla 0–100: ≤ 2 D4 … ≤ 30 D0, ≥ WATER_WET_PCT wilgotniej, pomiędzy norma."""
    p = _float(pct)
    if not np.isfinite(p):
        return ("", "brak danych", "#d9d9d9")
    for upper, code, label, color in cfg.get("WATER_CATEGORIES", WATER_CATEGORIES):
        if p <= upper:
            return (code, label, color)
    return WATER_WET if p >= cfg.get("WATER_WET_PCT", 70) else WATER_NORMAL


SWI_CLASS_PL = {"dry": "sucho", "normal": "w normie", "wet": "wilgotno"}


SWI_CLASS_EN = {"dry": "dry", "normal": "near normal", "wet": "wet"}


def read_swi(cfg: Dict[str, Any], product: Optional[str] = None) -> Optional[pd.DataFrame]:
    """Oczyszczony dzienny SWI piksela winnicy zapisany przez task_ingest_swi (None, gdy pliku jeszcze nie ma)."""
    path = os.path.join(cfg.get("SWI_DIR", ""), f"swi_{product or cfg.get('SWI_PRODUCT', 'v4_0.1deg')}_point.csv")
    return pd.read_csv(path, parse_dates=["date"]) if os.path.exists(path) else None


def _swi_class(p: float, cfg: Dict[str, Any]) -> Optional[str]:
    """Trzy klasy reguły zgodności (W3a §2): ≤ 30 sucho, 30–70 norma, ≥ 70 wilgotno."""
    if not np.isfinite(p):
        return None
    return "dry" if p <= float(cfg.get("SWI_DRY_PCT", 30)) else ("wet" if p >= float(cfg.get("WATER_WET_PCT", 70))
                                                                  else "normal")


def swi_agreement(pe: pd.Series, ps: pd.Series, cfg: Dict[str, Any], n_boot: int = 1000,
                  seed: int = 0) -> Dict[str, Any]:
    """
    Zgodność klas ERA5–SWI w latach normy SWI_NORM (D-080): odsetek dni z tą samą klasą i kappa Cohena, z 95% CI
    z bootstrapu po latach (lata jako bloki — dni w roku są silnie zależne). Liczone na macierzach pomyłek lat.
    """
    n0, n1 = cfg["SWI_NORM"]
    df = pd.DataFrame({"e": pe, "s": ps}).loc[n0:n1].dropna()
    keys = ("dry", "normal", "wet")
    ix = {k: i for i, k in enumerate(keys)}
    years = sorted(set(df.index.year))
    cm = {y: np.zeros((3, 3)) for y in years}
    for (y, a, b) in zip(df.index.year, df["e"], df["s"]):
        cm[y][ix[_swi_class(a, cfg)], ix[_swi_class(b, cfg)]] += 1

    def scores(m):
        n = m.sum()
        po = np.trace(m) / n
        pe_ = float((m.sum(axis=1) / n) @ (m.sum(axis=0) / n))
        return po, (po - pe_) / (1 - pe_) if pe_ < 1 else np.nan

    if not years:
        return {"po": np.nan, "kappa": np.nan, "po_ci": (np.nan, np.nan), "kappa_ci": (np.nan, np.nan),
                "n_days": 0, "years": None}
    po, kappa = scores(sum(cm.values()))
    lo = hi = (np.nan, np.nan)
    if n_boot > 0:
        rng = np.random.default_rng(seed)
        boots = np.array([scores(sum(cm[years[i]] for i in rng.integers(0, len(years), len(years))))
                          for _ in range(n_boot)])
        lo, hi = np.nanpercentile(boots, [2.5, 97.5], axis=0)
    return {"po": float(po), "kappa": float(kappa), "po_ci": (float(lo[0]), float(hi[0])),
            "kappa_ci": (float(lo[1]), float(hi[1])), "n_days": int(len(df)), "years": (years[0], years[-1])}


def water_card_json(card: Dict[str, Any]) -> Dict[str, Any]:
    """Karta jako JSON (agriwatch_latest.json, przyszła strona): daty ISO, NaN -> None."""
    def conv(v):
        if isinstance(v, pd.Timestamp):
            return v.strftime("%Y-%m-%d")
        if isinstance(v, dict):
            return {str(k): conv(x) for k, x in v.items()}
        if isinstance(v, (list, tuple)):
            return [conv(x) for x in v]
        if isinstance(v, (float, np.floating)):
            return None if not np.isfinite(v) else round(float(v), 4)
        if isinstance(v, np.integer):
            return int(v)
        return v
    return conv(card)


# Miejsca walidacji warstwy wody i ich miara główna (protokół docs/evidence/W2_REF_protokol_walidacji.md, D-083)
REF_TRUST_SITES = (
    ("SMOSMANIA_Condom", "ISMN_20_30cm_A4W1", "anomaly_clim", "Condom (ISMN, po kontroli A4)", "Condom (ISMN, after A4 QC)"),
    ("FR-Aur", "ICOS_FR-Aur_30cm", "anomaly_clim", "Auradé (ICOS, Gers)", "Auradé (ICOS, Gers)"),
    ("FR-Lus", "ICOS_FR-Lus_20_30cm", "anomaly_35d", "Lusignan (ICOS, anomalie 35-dniowe)",
     "Lusignan (ICOS, 35-day anomalies)"),
)


PARCEL_CLASS_PL = {"below": "poniżej swojej normy", "normal": "w normie", "above": "powyżej swojej normy"}


PARCEL_CLASS_EN = {"below": "below its own normal", "normal": "within its own normal range",
                   "above": "above its own normal"}


PARCEL_DETAIL = (("ndmi", "NDMI", 1.0), ("crswir", "−CRSWIR", -1.0), ("ndvi", "NDVI", 1.0), ("ndre", "NDRE", 1.0))


PARCEL_NOTES = {
    "pl": ("Wskaźnik widzi całą działkę: winorośl, międzyrzędzie i glebę. Zmienia się zwykle razem z zielenią.",
           "Spadek wody w roślinności widać raczej przy silniejszym niedoborze (wniosek z badań na poziomie liścia, "
           "Ceccato i in. 2001)."),
    "en": ("The index sees the whole parcel: vines, inter-rows and soil. It usually moves together with greenness.",
           "A drop in vegetation water tends to show only under stronger water deficits (leaf-level studies, "
           "Ceccato et al. 2001)."),
}


def parcel_class(z: Any) -> Optional[str]:
    """Klasa z_woda (protokół W3b §3): ≤ −1 poniżej, ≥ +1 powyżej, pomiędzy w normie; None bez z."""
    z = _float(z)
    if not np.isfinite(z):
        return None
    return "below" if z <= -1 else ("above" if z >= 1 else "normal")


def parcel_card(pa: pd.DataFrame, area: Optional[pd.DataFrame], flags: Optional[pd.DataFrame],
                summ: Optional[Dict[str, Any]], soil: Optional[Dict[str, Any]], cfg: Dict[str, Any], site_id: str,
                precip: Optional[pd.Series] = None, today: Optional[Any] = None) -> Dict[str, Any]:
    """
    Dane karty „Moja winnica” dla jednej działki (słownik zwykłych typów Pythona i pd.Timestamp):
      state     — "ok" | "stale" (scena starsza niż VEG_MAX_AGE_DAYS) | "small" (< PARCEL_MIN_PX pikseli) | "none",
      z, cls    — z_woda najnowszej sceny i klasa; k z N winnic z QC w tej samej klasie w tym dniu,
      change    — poprzednia scena, Δz, grupa pary (G5 / G13), próg MDC95 z testu T2, opad między scenami,
      flag_years, n_ref_years, off_season — dopiski (§8, U2, U4); detail — z NDMI, −CRSWIR, NDVI, NDRE (niezwalidowane),
      soil      — klasa gleby z karty wody (zdanie 1); area, sentence3 — zdanie 3 (§6 albo §7); tests — podsumowanie testów.
    """
    today = pd.Timestamp(today if today is not None else pd.Timestamp.now()).normalize()
    m0, m1 = cfg["PARCEL_TEST_MONTHS"]
    pa = pa.copy()
    pa["time"] = pd.to_datetime(pa["time"])
    site = pa[pa["site_id"] == site_id]
    n_px = _float(pd.to_numeric(site["n_pixels"], errors="coerce").max()) if len(site) else np.nan
    me = site[site["index"] == "water"].dropna(subset=["z"]).sort_values("time")
    card: Dict[str, Any] = {
        "site_id": site_id, "n_pixels": n_px, "min_px": int(cfg["PARCEL_MIN_PX"]),
        "qc_ok": bool(np.isfinite(n_px) and n_px >= cfg["PARCEL_MIN_PX"]), "state": "none", "date": None,
        "age_days": None, "z": np.nan, "cls": None, "k": None, "N": None, "change": None, "flag_years": [],
        "n_ref_years": None, "off_season": False, "detail": {}, "season": [], "soil": None, "area": None,
        "sentence3": False, "tests": summ}
    if soil:
        card["soil"] = {"class": soil.get("soil_class"), "percentile": _float(soil.get("percentile")),
                        "code": soil["category"]["code"], "label": soil["category"]["label"], "date": soil.get("date"),
                        "clim_ref": soil.get("clim_ref")}
    if not card["qc_ok"]:
        card["state"] = "small"
    elif len(me):
        last = me.iloc[-1]
        day = last["time"].normalize()
        nry = _float(last.get("n_ref_years"))
        card.update(date=last["time"], age_days=int((today - day).days), z=_float(last["z"]),
                    n_ref_years=int(nry) if np.isfinite(nry) else None, off_season=not (m0 <= day.month <= m1),
                    state="stale" if (today - day).days > cfg["VEG_MAX_AGE_DAYS"] else "ok")
        card["season"] = [{"date": t.strftime("%d.%m.%Y"), "z": float(z)}
                          for t, z in zip(me["time"], me["z"]) if t.year == day.year]
        for idx, label, sign in PARCEL_DETAIL:
            r = site[(site["index"] == idx) & (site["time"] == last["time"])].dropna(subset=["z"])
            if len(r):
                card["detail"][label] = sign * float(r["z"].iat[0])
        if card["state"] == "ok":
            card["cls"] = parcel_class(card["z"])
            ok = pa[(pa["index"] == "water") & (pa["time"].dt.normalize() == day)].dropna(subset=["z"])
            ok = ok[ok["qc_ok"].map(lambda v: str(v).strip().lower() in ("true", "1", "1.0"))]
            cls = ok["z"].map(parcel_class)
            card["N"], card["k"] = int(ok["site_id"].nunique()), int(ok.loc[cls == card["cls"], "site_id"].nunique())
            if len(me) >= 2:
                p = me.iloc[-2]
                pday = p["time"].normalize()
                dt = int((day - pday).days)
                same = _float(p["track"]) == _float(last["track"])
                grp = "G5" if same and 4 <= dt <= 6 else ("G13" if not same and 1 <= dt <= 3 else None)
                mdc = ((summ or {}).get("mdc") or {}).get(grp) if grp else None
                rain = float(pd.Series(precip).loc[pday:day].sum()) if precip is not None and len(precip) else np.nan
                card["change"] = {"date_prev": p["time"], "z_prev": _float(p["z"]), "dt": dt,
                                  "dz": card["z"] - _float(p["z"]), "group": grp,
                                  "mdc": _float(mdc["value"]) if mdc else np.nan, "rain_mm": rain}
    year = card["date"].year if card["date"] is not None else today.year
    if flags is not None and len(flags):
        f = flags[(flags["site_id"] == site_id) & flags["year"].between(year - int(cfg.get("VEG_REF_YEARS") or 5), year)]
        card["flag_years"] = sorted(int(y) for y in f.loc[f["flag"].astype(str).isin(["-", "+"]), "year"])
    p7 = (summ or {}).get("p7") or {}
    use_mb = bool(p7.get("accepted"))
    if area is not None and len(area):
        a = area[area["index"] == ("water_mb" if use_mb else "water")].copy()
        a["day"] = pd.to_datetime(a["day"])
        a = a.dropna(subset=["z_med"]).sort_values("day")
        if len(a):
            r = a.iloc[-1]
            n = _float(r.get("n_parcels"))
            card["area"] = {"date": r["day"], "z": _float(r["z_med"]), "cls": parcel_class(r["z_med"]),
                            "n": int(n) if np.isfinite(n) else None, "source": "water_mb" if use_mb else "water",
                            "age_days": int((today - r["day"].normalize()).days)}
    t3 = (summ or {}).get("t3") or {}
    passed = p7.get("passed_multi") if use_mb else t3.get("passed")
    card["sentence3"] = bool(passed and card["area"] and card["area"]["age_days"] <= cfg["VEG_MAX_AGE_DAYS"])
    return card


def parcel_card_lines(card: Dict[str, Any], lang: str = "pl") -> Dict[str, Any]:
    """Zdania karty „Moja winnica”: tytuł, 3 zdania (trzecie tylko po spełnionym kryterium), dopiski, stałe uwagi,
    „Na ile ufać” i szczegół (niezwalidowane). lang = "pl" (dashboard, raport) lub "en" (biuletyn)."""
    pl = lang == "pl"

    def num(x, nd=1):
        x = _float(x)
        return _num(x, nd) if pl else ("—" if not np.isfinite(x) else f"{x:.{nd}f}")

    def date(t):
        return pd.Timestamp(t).strftime("%d.%m.%Y" if pl else "%Y-%m-%d")

    def per(x):
        return str((x or {}).get("period", "")).replace("-", "–")
    cls_txt = PARCEL_CLASS_PL if pl else PARCEL_CLASS_EN
    out: Dict[str, Any] = {"title": "Moja winnica — działka wobec własnej historii" if pl else
                           "My vineyard — the parcel against its own history", "sentences": [], "notes": [],
                           "trust": [], "detail": "", "fixed": list(PARCEL_NOTES["pl" if pl else "en"])}
    soil = card.get("soil")
    if soil and soil.get("class"):
        c0, c1 = soil.get("clim_ref") or ("1991", "2020")
        word = (SWI_CLASS_PL if pl else SWI_CLASS_EN)[soil["class"]]
        usdm = (f" ({soil['code']} wg US Drought Monitor)" if pl else f" ({soil['code']}, US Drought Monitor)") \
            if soil.get("code") else ""
        out["sentences"].append(
            f"Gleba w okolicy (~10 km, model ERA5-Land): {word} — percentyl {num(soil['percentile'], 0)} wobec "
            f"{c0}–{c1}{usdm}, stan na {date(soil['date'])}." if pl else
            f"Soil in the area (~10 km, ERA5-Land model): {word} — percentile {num(soil['percentile'], 0)} vs "
            f"{c0}–{c1}{usdm}, as of {date(soil['date'])}.")
    st = card["state"]
    if st == "small":
        out["sentences"].append(
            f"Twoja działka: za mała na wiarygodną anomalię ({num(card['n_pixels'], 0)} pikseli 10 m po odcięciu pasa "
            f"przy brzegu; potrzeba co najmniej {card['min_px']})." if pl else
            f"Your parcel: too small for a reliable anomaly ({num(card['n_pixels'], 0)} 10 m pixels after removing the "
            f"edge strip; at least {card['min_px']} needed).")
    elif st == "none":
        out["sentences"].append("Twoja działka: brak sceny z oceną wobec historii." if pl else
                                "Your parcel: no scene with an anomaly yet.")
    elif st == "stale":
        out["sentences"].append(f"Twoja działka: brak aktualnej sceny (ostatnia {date(card['date'])}, "
                                f"{days_ago_pl(card['age_days'])})." if pl else
                                f"Your parcel: no recent scene (last one {date(card['date'])}, "
                                f"{card['age_days']} days ago).")
    else:
        txt = (f"Twoja działka — wskaźnik wody w roślinności (SWIR): {cls_txt[card['cls']]} (z = {num(card['z'])}), "
               f"scena {date(card['date'])}; tak samo {card['k']} z {card['N']} winnic w okolicy." if pl else
               f"Your parcel — vegetation water index (SWIR): {cls_txt[card['cls']]} (z = {num(card['z'])}), scene "
               f"{date(card['date'])}; {card['k']} of {card['N']} vineyards in the area are in the same class.")
        ch = card.get("change")
        if ch:
            prev = f"{date(ch['date_prev'])}, z = {num(ch['z_prev'])}"
            if ch["dt"] > 6:
                txt += f" Poprzednia scena: {prev}." if pl else f" Previous scene: {prev}."
            elif ch["group"] is None or not np.isfinite(_float(ch["mdc"])):
                txt += (f" Poprzednia scena: {prev} (zmiany nie oceniamy: brak progu dla tej pary scen)." if pl else
                        f" Previous scene: {prev} (change not assessed: no threshold for this pair of scenes).")
            elif abs(ch["dz"]) >= ch["mdc"]:
                txt += (f" Wyraźna zmiana od poprzedniej sceny ({prev}): {num(ch['dz'])} przy progu {num(ch['mdc'])}."
                        if pl else f" Clear change since the previous scene ({prev}): {num(ch['dz'])} vs threshold "
                                   f"{num(ch['mdc'])}.")
            else:
                txt += (f" Bez wyraźnej zmiany od poprzedniej sceny ({prev}; różnica {num(ch['dz'])} poniżej progu "
                        f"{num(ch['mdc'])})." if pl else f" No clear change since the previous scene ({prev}; "
                                                         f"difference {num(ch['dz'])} below threshold {num(ch['mdc'])}).")
            if ch["dt"] <= 6 and np.isfinite(_float(ch["rain_mm"])) and ch["rain_mm"] >= 5:
                txt += (f" Między scenami padało ({num(ch['rain_mm'], 0)} mm)." if pl else
                        f" It rained between the scenes ({num(ch['rain_mm'], 0)} mm).")
        out["sentences"].append(txt)
    summ = card.get("tests") or {}
    t3 = summ.get("t3") or {}
    if card.get("sentence3") and card.get("area"):
        a = card["area"]
        p7 = summ.get("p7") or {}
        r = p7.get("rho_multi") if a["source"] == "water_mb" else t3
        src = (" (model 4 pasm)" if pl else " (4-band model)") if a["source"] == "water_mb" else ""
        out["sentences"].append(
            f"Okolica: roślinność winnic {cls_txt[a['cls']]}{src}, scena {date(a['date'])}. W latach {per(r)} "
            f"szła w parze z wodą w glebie z 30 dni przed sceną (ρ = {num(r['value'], 2)} [{num(r['lo'], 2)}; "
            f"{num(r['hi'], 2)}], czujnik ISMN w Condom). Dla pojedynczej działki tego nie sprawdzaliśmy." if pl else
            f"Area: vineyard vegetation {cls_txt[a['cls']]}{src}, scene {date(a['date'])}. In {per(r)} it moved "
            f"together with soil water of the previous 30 days (ρ = {num(r['value'], 2)} [{num(r['lo'], 2)}; "
            f"{num(r['hi'], 2)}], ISMN sensor at Condom). Not checked for a single parcel.")
    if card["flag_years"]:
        ys = ", ".join(map(str, card["flag_years"]))
        out["notes"].append(f"Porównanie z historią mniej pewne: w sezonie {ys} działka wyraźnie odbiegała od sąsiednich "
                            f"winnic (możliwa zmiana gospodarowania)." if pl else
                            f"Comparison with history less certain: in {ys} the parcel departed clearly from the "
                            f"neighbouring vineyards (possible change in management).")
    if st in ("ok", "stale") and card.get("n_ref_years") is not None and card["n_ref_years"] < 3:
        n = card["n_ref_years"]
        out["notes"].append(f"Krótka historia ({n} {plural_pl(n, 'rok', 'lata', 'lat')} w normie)." if pl else
                            f"Short history ({n} years in the baseline).")
    if st in ("ok", "stale") and card.get("off_season"):
        out["notes"].append("Poza okresem sprawdzonym (VI–IX)." if pl else "Outside the tested period (June–September).")
    t1 = summ.get("t1")
    if t1 and np.isfinite(_float(t1["value"])):
        out["trust"].append(
            f"W archiwum (VI–IX, {per(t1)}) klasa „poniżej swojej normy” wypadła w {num(100 * t1['value'])}% scen "
            f"[{num(100 * t1['lo'])}; {num(100 * t1['hi'])}]; zakładane ok. 16% (1 na 6) — {t1['verdict']}." if pl else
            f"In the archive (June–September, {per(t1)}) the class “below its own normal” occurred in "
            f"{num(100 * t1['value'])}% of scenes [{num(100 * t1['lo'])}; {num(100 * t1['hi'])}]; expected about 16%.")
        from agriscreen.parcel import P_BELOW
        lo, hi = _float(t1["lo"]), _float(t1["hi"])
        if np.isfinite(lo) and not lo <= P_BELOW <= hi:
            out["notes"].append(f"W archiwum ta klasa wypadała {'częściej' if lo > P_BELOW else 'rzadziej'} niż 1 na 6 scen."
                                if pl else f"In the archive this class occurred {'more' if lo > P_BELOW else 'less'} "
                                           f"often than 1 in 6 scenes.")
    mdc = summ.get("mdc") or {}
    if mdc:
        parts = []
        for g, lab_pl, lab_en in (("G5", "ten sam tor, 4–6 dni", "same orbit track, 4–6 days"),
                                  ("G13", "różne tory, 1–3 dni", "different tracks, 1–3 days")):
            m = mdc.get(g)
            v = _float(m["value"]) if m else np.nan
            parts.append(f"{num(v)} ({lab_pl})" if pl and np.isfinite(v) else
                         f"za mało par ({lab_pl})" if pl else
                         f"{num(v)} ({lab_en})" if np.isfinite(v) else f"too few pairs ({lab_en})")
        out["trust"].append(("Najmniejsza wyraźna zmiana z między scenami: " if pl else
                             "Smallest clear change of z between scenes: ") + "; ".join(parts) + ".")
    if t3:
        ok3 = t3.get("passed")
        out["trust"].append(
            f"Roślinność okolicy a czujnik w gruncie (T3, VI–IX {per(t3)}): ρ = {num(t3['value'], 2)} "
            f"[{num(t3['lo'], 2)}; {num(t3['hi'], 2)}]" + ("" if ok3 else " — niepotwierdzone") + "." if pl else
            f"Area vegetation vs in situ sensor (T3, June–September {per(t3)}): ρ = {num(t3['value'], 2)} "
            f"[{num(t3['lo'], 2)}; {num(t3['hi'], 2)}]" + ("" if ok3 else " — not confirmed") + ".")
    if not summ:
        out["trust"].append("Testy W3b jeszcze nie policzone (notatnik, sekcja 5c)." if pl else
                            "W3b tests not computed yet.")
    if card["detail"]:
        out["detail"] = (("Szczegół (niezwalidowane): " if pl else "Detail (not validated): ")
                         + ", ".join(f"{k} z = {num(v)}" for k, v in card["detail"].items()) + ".")
    return out


def _selftest_parcel(cfg: Dict[str, Any]) -> None:
    """Karta „Moja winnica” na ręcznie zbudowanych danych: klasy, mała działka, flaga, wyraźna zmiana i opad,
    zdanie 3 tylko po kryterium, słowa zakazane (D-087), JSON, znak CRSWIR w szczególe."""
    import json
    assert [parcel_class(z) for z in (-1.0, -0.99, 0.0, 0.99, 1.0, np.nan)] == \
        ["below", "normal", "normal", "normal", "above", None]
    t = pd.to_datetime(["2026-08-02 10:59", "2026-08-07 10:59", "2026-08-07 10:59", "2026-08-07 10:59"])
    base = {"product": "S2_10m_buf20", "value": np.nan, "n_ref": 20, "n_ref_years": 5, "ref_mode": "same_track",
            "n_pixels": 141, "qc_ok": True}
    rows = [dict(base, site_id="VINEYARD_06", index="water", time=t[0], z=0.2, track=0),
            dict(base, site_id="VINEYARD_06", index="water", time=t[1], z=-1.4, track=0),
            dict(base, site_id="VINEYARD_06", index="crswir", time=t[1], z=1.6, track=0),
            dict(base, site_id="VINEYARD_06", index="ndmi", time=t[1], z=-1.2, track=0)]
    rows += [dict(base, site_id=f"VINEYARD_{i:02d}", index="water", time=t[1], z=z, track=0)
             for i, z in zip((7, 8, 9, 10), (-1.1, -0.5, -2.0, 0.3))]
    rows += [dict(base, site_id="VINEYARD_16", index="water", time=t[1], z=-3.0, track=0, n_pixels=19, qc_ok=False)]
    pa = pd.DataFrame(rows)
    summ = {"t1": {"value": 0.17, "lo": 0.14, "hi": 0.20, "period": "2018-2026", "verdict": "nie wykryto grubego "
                   "rozkalibrowania", "n": 900},
            "mdc": {"G5": {"value": 1.2, "lo": 1.0, "hi": 1.4, "period": "2018-2026", "verdict": "", "n": 300},
                    "G13": None},
            "t3": {"value": 0.31, "lo": 0.05, "hi": 0.57, "period": "2018-2024", "verdict": "spełnione", "n": 110,
                   "passed": True},
            "p7": {"accepted": False}}
    area = pd.DataFrame({"day": [pd.Timestamp("2026-08-07")], "index": ["water"], "z_med": [-1.05], "n_parcels": [9]})
    flags = pd.DataFrame({"site_id": ["VINEYARD_06"], "year": [2023], "flag": ["+"]})
    precip = pd.Series(3.0, index=pd.date_range("2026-07-01", "2026-08-31"))
    soil = {"soil_class": "dry", "percentile": 12.0, "category": {"code": "D1", "label": "umiarkowana susza"},
            "date": pd.Timestamp("2026-08-05"), "clim_ref": ("1991", "2020")}
    today = pd.Timestamp("2026-08-10")
    card = parcel_card(pa, area, flags, summ, soil, cfg, "VINEYARD_06", precip=precip, today=today)
    assert card["state"] == "ok" and card["cls"] == "below" and (card["k"], card["N"]) == (3, 5), card
    assert card["change"]["group"] == "G5" and card["detail"]["−CRSWIR"] == -1.6 and card["sentence3"], card
    pl, en = parcel_card_lines(card), parcel_card_lines(card, "en")
    s = " ".join(pl["sentences"] + pl["notes"] + pl["trust"])
    assert pl["sentences"][0].startswith("Gleba w okolicy (~10 km, model ERA5-Land): sucho") and len(pl["sentences"]) == 3
    assert "(D1 wg US Drought Monitor)" in pl["sentences"][0], pl["sentences"][0]
    assert "poniżej swojej normy (z = −1,4)" in s and "tak samo 3 z 5 winnic" in s, s
    assert "Wyraźna zmiana od poprzedniej sceny" in s and "Między scenami padało (18 mm)" in s, s
    assert "Porównanie z historią mniej pewne" in s and "2023" in s and "Dla pojedynczej działki" in s, s
    assert "za mało par (różne tory, 1–3 dni)" in s and "−CRSWIR z = −1,6" in pl["detail"], (s, pl["detail"])
    nopass = parcel_card(pa, area, flags, dict(summ, t3=dict(summ["t3"], passed=False)), soil, cfg, "VINEYARD_06",
                         precip=precip, today=today)
    lp = parcel_card_lines(nopass)
    assert not nopass["sentence3"] and len(lp["sentences"]) == 2 and "niepotwierdzone" in " ".join(lp["trust"]), lp
    small = parcel_card(pa, area, flags, summ, soil, cfg, "VINEYARD_16", precip=precip, today=today)
    assert small["state"] == "small" and "za mała na wiarygodną anomalię" in parcel_card_lines(small)["sentences"][1]
    old = parcel_card(pa, area, None, summ, soil, cfg, "VINEYARD_06", today=pd.Timestamp("2026-10-01"))
    assert old["state"] == "stale" and not old["sentence3"] and "brak aktualnej sceny" in parcel_card_lines(old)["sentences"][1]
    small_dz = pa.copy()
    small_dz.loc[(small_dz["index"] == "water") & (small_dz["site_id"] == "VINEYARD_06") & (small_dz["time"] == t[0]),
                 "z"] = -1.0
    c2 = parcel_card(small_dz, area, None, summ, soil, cfg, "VINEYARD_06", precip=precip * 0, today=today)
    l2 = " ".join(parcel_card_lines(c2)["sentences"])
    assert "Bez wyraźnej zmiany" in l2 and "padało" not in l2, l2
    for lines in (pl, en, lp, parcel_card_lines(small, "en")):
        txt = " ".join([lines["title"], lines["detail"]] + lines["sentences"] + lines["notes"] + lines["trust"]
                       + lines["fixed"]).lower()
        for bad in ("stres wodny", "wczesne ostrzeżenie", "water stress", "early warning"):
            assert bad not in txt, bad
    json.dumps(water_card_json(card))
    print(f"[OK] Karta „Moja winnica”: {pl['sentences'][1][:110]}…")
