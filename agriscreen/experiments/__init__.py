"""
Eksperymenty: anomalie konkretnych miejsc wewnątrz winnicy. Domyślnie wyłączone (`run_all(experiments=True)`).

- zones.py (W3c, protokół docs/evidence/W3c_protokol_strefy.md): miejsce wobec reszty działki i własnych 5 lat,
  próg z testu szumu. Pierwszy przebieg 2026-10-20: nie przeszło (docs/evidence/W3c_wyniki.md).
- months.py (W3d, protokół docs/evidence/W3d_protokol_miesiace.md): kwadrat 30 m „najniżej / najwyżej od 5 lat”
  w danym miesiącu. Pierwszy przebieg: nie przeszło — za mało lat na potwierdzenie (docs/evidence/W3d_wyniki.md).

Obie metody liczą testy zarejestrowane przed liczeniem i zapisują wynik (`w3c_tests.csv`, `w3d_tests.csv`). Panel nie
rysuje tych warstw; pokazuje tylko wiersze w tabeli „How far to trust it” (`trust_rows`). Powtórka testów: po sezonie
2027, z tymi samymi regułami.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from agriscreen.config import era5_csv


def task_zones(rt: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    """W3c: magazyn stref, test szumu Z1, Z2 i kryterium pokazania (experiments/zones.py)."""
    from agriscreen import parcel
    from agriscreen.experiments import zones
    proto = parcel.protocol_sha(cfg["W3C_PROTOCOL"])
    res = zones.run_zones(cfg, cfg["OUTPUT_DIR"], pd.read_csv(era5_csv(cfg), parse_dates=["time"]),
                          commit=str(rt.get("GIT_COMMIT", "")))
    show = "; ".join(f"{k.upper()}: {v}" for k, v in res["show"].items())
    return {"message": f"{res['sites']} winnic, {res['n_scenes']} scen (+{res['n_new']}); zamrożenie "
                       f"{res['freeze']['freeze']}; {show}" + _proto_warn(proto)}


def task_months(rt: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    """W3d: magazyn kwadratów 30 m, klasy miesięcy, test D1 i kryterium pokazania (experiments/months.py)."""
    from agriscreen import parcel
    from agriscreen.experiments import months
    proto = parcel.protocol_sha(cfg["W3D_PROTOCOL"])
    res = months.run_months(cfg, cfg["OUTPUT_DIR"], pd.read_csv(era5_csv(cfg), parse_dates=["time"]),
                            commit=str(rt.get("GIT_COMMIT", "")))
    show = "; ".join(f"{k.upper()}: {v}" for k, v in res["show"].items())
    return {"message": f"{res['sites']} winnic, {res['n_scenes']} scen (+{res['n_new']}); zamrożenie "
                       f"{res['freeze']['freeze']}; {show}" + _proto_warn(proto)}


def _proto_warn(proto: Dict[str, str]) -> str:
    return "" if proto["sha256"] == proto["registered"] else \
        f"; UWAGA: treść protokołu różni się od zarejestrowanej ({proto['sha256'][:12]}… ≠ {proto['registered'][:12]}…)"


# ==============================================================================
# Wiersze „How far to trust it” (EN) z plików testów
# ==============================================================================

_NAMES = (("ndvi", "greenness (NDVI)"), ("ndmi", "water in vegetation (NDMI)"))


def _read(path: str) -> pd.DataFrame:
    return pd.read_csv(path) if os.path.exists(path) and os.path.getsize(path) > 1 else pd.DataFrame()


def _f(x: Any, nd: int = 2) -> str:
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "—"
    return f"{x:.{nd}f}" if np.isfinite(x) else "—"


def _subset_en(sub: str) -> str:
    sub = str(sub)
    if sub.startswith("gleba w normie"):
        return "days with normal soil"
    if sub.startswith("wszystkie"):
        return "all June–September days"
    return sub


def _verdict_en(v: str) -> str:
    """Werdykt kryterium (PL, z plików testów) po angielsku: który warunek nie przeszedł i z jakimi liczbami."""
    out = []
    for part in str(v).replace("nie pokazujemy — ", "").split("; "):
        m2 = re.match(r"2: MDC95 górna ([\d.]+) ≥ ½ rozstępu działki ([\d.]+)", part)
        m3 = re.match(r"3: udział komórek w strefach \((.*)\) górna ([\d.]+)% > (\d+)%", part)
        md = re.match(r"„(najniżej|najwyżej)” górna ([\d.]+) > ([\d.]+)", part)
        if part.startswith("1:"):
            out.append("too few pairs of scenes for the noise test")
        elif m2:
            out.append(f"noise (upper MDC95 {m2.group(1)}) is not below half the typical spread within a parcel "
                       f"({m2.group(2)})")
        elif m3:
            out.append(f"zones cover too much on {_subset_en(m3.group(1))} (upper {m3.group(2)}% > {m3.group(3)}%)")
        elif md:
            out.append(f"“{'lowest' if md.group(1) == 'najniżej' else 'highest'} in N years” not confirmed to be as "
                       f"rare as chance (upper bound {md.group(2)} × chance > {md.group(3)})")
        elif part == "pokazujemy":
            out.append("passed")
        elif "za mało lat" in part or "< 3 lat" in part or part.startswith(("2:", "3:")):
            out.append("too few years for a confidence interval")
        else:
            out.append(part)
    return "; ".join(out)


def trust_rows(out_dir: str) -> List[Dict[str, str]]:
    """Wiersze W3c i W3d do tabeli „How far to trust it”: wynik testu i — gdy nie przeszedł — powód. Panel nie rysuje
    tych warstw (eksperyment), więc status to „experimental, not shown” albo „experimental, passed”."""
    from agriscreen.experiments import months, zones
    rows: List[Dict[str, str]] = []
    t = _read(os.path.join(out_dir, zones.TESTS_NAME))
    if len(t):
        kr = t.dropna(subset=["key"]).set_index("key")
        proto = str(t["protocol_sha256"].iat[0])[:12]
        for k, name in _NAMES:
            if f"z_show_{k}" not in kr.index:
                continue
            z1 = next((kr.loc[f"z1_{g}_{k}"] for g in ("g5", "g13") if f"z1_{g}_{k}" in kr.index
                       and np.isfinite(float(kr.loc[f"z1_{g}_{k}", "value"]))), None)
            res = (f"threshold {_f(z1['value'], 3)} [{_f(z1['ci_low'], 3)}–{_f(z1['ci_high'], 3)}] from {int(z1['n'])} "
                   f"scene pairs" if z1 is not None else "too few scene pairs for a threshold")
            if f"z2_normal_{k}" in kr.index:
                z2 = kr.loc[f"z2_normal_{k}"]
                res += (f"; cells in zones: {100 * float(z2['value']):.1f}% [{100 * float(z2['ci_low']):.1f}–"
                        f"{100 * float(z2['ci_high']):.1f}%] ({_subset_en(z2['subset'])}; about 1% expected from noise)")
            passed = float(kr.loc[f"z_show_{k}", "value"]) == 1.0
            if not passed:
                res += "; not shown: " + _verdict_en(kr.loc[f"z_show_{k}", "verdict"])
            rows.append({"what": f"Zones vs usual, {name}: places weaker or stronger than usual, relative to the parcel",
                         "against": "noise between scenes a few days apart without rain; how often zones appear when "
                                    f"soil is normal (pre-registered W3c, {proto}…)",
                         "result": res, "status": "experimental, passed" if passed else "experimental, not shown"})
    t = _read(os.path.join(out_dir, months.TESTS_NAME))
    if len(t):
        kr = t.dropna(subset=["key"]).set_index("key")
        proto = str(t["protocol_sha256"].iat[0])[:12]
        for k, name in _NAMES:
            if f"d_show_{k}" not in kr.index:
                continue
            parts = [f"{w} {_f(kr.loc[f'd1_{c}_{k}', 'value'])} [{_f(kr.loc[f'd1_{c}_{k}', 'ci_low'])}–"
                     f"{_f(kr.loc[f'd1_{c}_{k}', 'ci_high'])}] × chance"
                     for c, w in (("low", "lowest"), ("high", "highest")) if f"d1_{c}_{k}" in kr.index]
            res = "; ".join(parts) or "no test result"
            if f"d1_low_{k}" in kr.index:
                res += f" ({'months with normal soil' if str(kr.loc[f'd1_low_{k}', 'subset']).startswith('gleba w normie') else 'all June–September months'})"
            passed = float(kr.loc[f"d_show_{k}", "value"]) == 1.0
            if not passed:
                res += "; not shown: " + _verdict_en(kr.loc[f"d_show_{k}", "verdict"])
            rows.append({"what": f"Lowest in N years, {name}: a 30 m place against the same month in its last 5 years",
                         "against": "how often “lowest / highest in N years” occurs vs chance 1/(N+1) (pre-registered "
                                    f"W3d, {proto}…)",
                         "result": res, "status": "experimental, passed" if passed else "experimental, not shown"})
    return rows
