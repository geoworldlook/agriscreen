"""
W3b — symulacje projektowe do protokołu (docs/evidence/W3b_protokol_walidacji.md, §4, §6, §12).

Liczy, zanim powstanie jakakolwiek liczba z Sentinel-2:
  1. właściwości celu T3 z czujnika ISMN Condom (A4 W1, średnia 20/30 cm, z dzienne obcięte do [-3; 3],
     średnia z [t-30, t-1]) w VI–IX 2018–2024: autokorelacja, udział wariancji między latami;
  2. T3: jak często kryterium „dolna granica 95% CI ρ > 0” przechodzi przy prawdziwym ρ = 0 / 0,2 / 0,3 / 0,45,
     dla przedziału jackknife po latach (kryterium protokołu) i bootstrapu po latach (dla porównania);
  3. T1: rozrzut p̂ = P(z ≤ -1) przy poprawnej kalibracji i pokrycie 15,9% przez CI jackknife po latach.

Uruchomienie z katalogu repozytorium:  python docs/evidence/W3b_symulacje.py
Ziarno stałe (42), więc wynik jest powtarzalny. Bez danych satelitarnych.
"""
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

SEED = 42
G_T3 = 7                       # sezony 2018–2024
DAYS_T3 = (8, 16, 16, 16, 16, 16, 16)   # dni scen VI–IX z ważnym x i y (2018 częściowo); szacunek
SEASON = 122                   # dni VI–IX
N_SIM = 1000
N_BOOT = 1000
# Generator dopasowany do celu z czujnika (sekcja 1 wydruku): AR(1) dzienne φ = 0,9, średnia 30 dni,
# efekt roku 0,3 -> autokorelacja w sezonie ok. 0,90 / 0,69 przy 5 / 10 dniach, ok. 50% wariancji między latami.
PHI = 0.9
Y_YEAR, Y_SMOOTH = 0.3, 0.7          # cel T3 (czujnik): bez szumu iid, bo to średnia 30 dni
X_YEAR, X_SMOOTH = 0.3, 0.5          # część roślinności niezwiązana z celem; reszta 0,2 to szum sceny


# ------------------------------------------------------------------------------
# 1. Cel T3 z czujnika (jeśli dane ISMN są w repo)
# ------------------------------------------------------------------------------

def sensor_target(root: str, var: str = "W1") -> pd.Series:
    """y(t) jak w protokole §6: A4 (wariant `var`), średnia 20/30 cm, z wobec 2016–2024 (±15 dni, min. 20), obcięcie [-3; 3]."""
    sys.path.insert(0, root)
    import step_07_station_pipeline as s7
    from step_04_metrics_alert import clim_anomaly
    ov = {"PROJECT_DIR": root, "NETWORK": "SMOSMANIA", "STATION": "Condom", "END_DATE": "2024-12-31"}
    v20, v30 = s7.a4_variants(0.20, ov), s7.a4_variants(0.30, ov)
    rz = pd.concat([v20[var]["sm"], v30[var]["sm"]], axis=1, sort=True).dropna().mean(axis=1)
    rz = rz.loc["2016-01-01":"2024-12-31"]
    z = clim_anomaly(rz, ("2016-01-01", "2024-12-31"), 15, min_n=20)["z"].asfreq("D").clip(-3, 3)
    y = z.rolling(30, min_periods=20).mean().shift(1)
    sel = (y.index.month >= 6) & (y.index.month <= 9) & (y.index.year >= 2018) & (y.index.year <= 2024)
    return y[sel].dropna()


def target_properties(y: pd.Series) -> dict:
    """Autokorelacja w sezonie (surowa i po odjęciu średniej sezonu) oraz udział wariancji między latami."""
    out = {"n_days": len(y)}
    for lag in (5, 10, 30):
        raw, dem = [], []
        for _, g in y.groupby(y.index.year):
            g = g.asfreq("D")
            raw.append(pd.concat([g, g.shift(lag)], axis=1).dropna())
            h = g - g.mean()
            dem.append(pd.concat([h, h.shift(lag)], axis=1).dropna())
        r, d = pd.concat(raw), pd.concat(dem)
        out[f"acf{lag}"] = float(np.corrcoef(r.iloc[:, 0], r.iloc[:, 1])[0, 1])
        out[f"acf{lag}_within"] = float(np.corrcoef(d.iloc[:, 0], d.iloc[:, 1])[0, 1])
    m = y.groupby(y.index.year).mean()
    out["between_year_share"] = float(m.var(ddof=0) / y.var(ddof=0))
    return out


# ------------------------------------------------------------------------------
# 2. Generator: efekt roku + gładki przebieg w sezonie (średnia 30 dni z AR(1)) + szum
# ------------------------------------------------------------------------------

def season_process(rng: np.random.Generator, n_years: int, year_share: float, smooth_share: float,
                   phi: float = PHI) -> np.ndarray:
    """Macierz [lata, dni]: wariancja 1 = year_share (stała w roku) + smooth_share (średnia 30 dni z AR(1)) + reszta iid."""
    burn = 60
    e = rng.standard_normal((n_years, SEASON + burn))
    a = np.empty_like(e)
    a[:, 0] = e[:, 0]
    for t in range(1, a.shape[1]):
        a[:, t] = phi * a[:, t - 1] + np.sqrt(1 - phi ** 2) * e[:, t]
    k = np.ones(30) / 30
    sm = np.array([np.convolve(r, k, mode="valid")[-SEASON:] for r in a])
    sm = (sm - sm.mean()) / sm.std()
    yr = rng.standard_normal((n_years, 1))
    iid = rng.standard_normal((n_years, SEASON))
    rest = max(0.0, 1 - year_share - smooth_share)
    return np.sqrt(year_share) * yr + np.sqrt(smooth_share) * sm + np.sqrt(rest) * iid


def _rank(v: np.ndarray) -> np.ndarray:
    return np.argsort(np.argsort(v)).astype(float)   # wartości ciągłe, bez remisów


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    return float(np.corrcoef(_rank(x), _rank(y))[0, 1])


def jackknife_lower(x: np.ndarray, y: np.ndarray, g: np.ndarray) -> float:
    """Dolna granica 95%: ρ − t(0,975; G−1)·SE_jack, SE_jack = √((G−1)/G·Σ(ρ₋g − średnia)²)."""
    years = np.unique(g)
    G = len(years)
    rho = spearman(x, y)
    loo = np.array([spearman(x[g != k], y[g != k]) for k in years])
    se = np.sqrt((G - 1) / G * np.sum((loo - loo.mean()) ** 2))
    return rho - stats.t.ppf(0.975, G - 1) * se


def bootstrap_lower(x: np.ndarray, y: np.ndarray, g: np.ndarray, rng: np.random.Generator, n: int) -> float:
    years = np.unique(g)
    idx = {k: np.flatnonzero(g == k) for k in years}
    vals = []
    for _ in range(n):
        pick = rng.choice(years, size=len(years), replace=True)
        ii = np.concatenate([idx[k] for k in pick])
        vals.append(spearman(x[ii], y[ii]))
    return float(np.nanpercentile(vals, 2.5))


def simulate_t3(c: float, rng: np.random.Generator, n_sim: int, with_boot: bool) -> dict:
    """Odsetek prób, w których dolna granica > 0. Cel i predyktor mają efekt roku i gładki przebieg."""
    pj, pb, rhos = 0, 0, []
    for _ in range(n_sim):
        y = season_process(rng, G_T3, Y_YEAR, Y_SMOOTH)      # cel jak czujnik (sekcja 1)
        u = season_process(rng, G_T3, X_YEAR, X_SMOOTH)      # roślinność: część niezależna od celu
        x = c * y + np.sqrt(1 - c ** 2) * u
        xs, ys, gs = [], [], []
        for k, n in enumerate(DAYS_T3):
            d = np.sort(rng.choice(SEASON, size=n, replace=False))
            xs.append(x[k, d]); ys.append(y[k, d]); gs.append(np.full(n, k))
        xx, yy, gg = np.concatenate(xs), np.concatenate(ys), np.concatenate(gs)
        rhos.append(spearman(xx, yy))
        pj += jackknife_lower(xx, yy, gg) > 0
        if with_boot:
            pb += bootstrap_lower(xx, yy, gg, rng, N_BOOT) > 0
    out = {"c": c, "rho_median": float(np.median(rhos)), "pass_jackknife": pj / n_sim}
    if with_boot:
        out["pass_bootstrap"] = pb / n_sim
    return out


# ------------------------------------------------------------------------------
# 3. T1: kalibracja przy 9 sezonach (2018–2026), 25 scen × 13 winnic
# ------------------------------------------------------------------------------

def simulate_t1(year_share: float, rng: np.random.Generator, n_sim: int = N_SIM, scale: float = 1.0) -> dict:
    """z = scale·(efekt roku + efekt dnia sceny wspólny dla okolicy + część działki), brzegowo N(0, scale²)."""
    G, S, V = 9, 25, 13
    day_share = 0.3
    p_hat, cover = [], 0
    for _ in range(n_sim):
        yr = rng.standard_normal((G, 1, 1))
        day = rng.standard_normal((G, S, 1))
        own = rng.standard_normal((G, S, V))
        rest = 1 - year_share - day_share
        z = scale * (np.sqrt(year_share) * yr + np.sqrt(day_share) * day + np.sqrt(rest) * own)
        z = [z[0, : S // 2]] + [z[k] for k in range(1, G)]    # 2018 częściowo: połowa scen
        low = [float((zz <= -1).sum()) for zz in z]
        cnt = [float(zz.size) for zz in z]
        p = sum(low) / sum(cnt)
        loo = np.array([(sum(low) - low[k]) / (sum(cnt) - cnt[k]) for k in range(G)])
        se = np.sqrt((G - 1) / G * np.sum((loo - loo.mean()) ** 2))
        lo, hi = p - stats.t.ppf(0.975, G - 1) * se, p + stats.t.ppf(0.975, G - 1) * se
        p_hat.append(p)
        cover += lo <= stats.norm.cdf(-1) <= hi
    q = np.percentile(p_hat, [2.5, 97.5])
    return {"year_share": year_share, "scale": scale, "p_true": float(stats.norm.cdf(-1 / scale)),
            "p_hat_2.5": float(q[0]), "p_hat_97.5": float(q[1]),
            "ci_contains_15.9": cover / n_sim}


def main() -> None:
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    rng = np.random.default_rng(SEED)
    print("== 1. Cel T3 z czujnika (A4 W1, VI–IX 2018–2024) ==")
    try:
        y1 = sensor_target(root)
        print({k: round(v, 3) if isinstance(v, float) else v for k, v in target_properties(y1).items()})
        for var in ("W1_05WP", "W1_015", "W3"):       # ranga celu a umowny próg θ_dno i stare QC
            d = pd.concat([y1, sensor_target(root, var)], axis=1, sort=True).dropna()
            print(f"Spearman celu W1 vs {var}: {d.corr(method='spearman').iloc[0, 1]:.2f} (n = {len(d)})")
    except Exception as e:  # dane ISMN nieobecne — symulacje i tak działają
        print("brak danych czujnika:", type(e).__name__, e)
    print("== Generator (kontrola, 200 sezonów) ==")
    y = season_process(rng, 200, Y_YEAR, Y_SMOOTH)
    idx = pd.MultiIndex.from_product([range(200), range(SEASON)])
    s = pd.Series(y.ravel(), index=idx)
    for lag in (5, 10, 30):
        d = s.groupby(level=0).transform(lambda v: v - v.mean())
        r = np.mean([np.corrcoef(g.values[lag:], g.values[:-lag])[0, 1] for _, g in d.groupby(level=0)])
        print(f"acf{lag}_within ≈ {r:.2f}")
    print("== 2. T3: odsetek zaliczeń kryterium (dolna granica 95% > 0) ==")
    for c in (0.0, 0.2, 0.3, 0.45):
        print(simulate_t3(c, rng, N_SIM, with_boot=False))
    print("-- porównanie z bootstrapem po latach (200 prób) --")
    for c in (0.0, 0.3):
        print(simulate_t3(c, rng, 200, with_boot=True))
    print("== 3. T1: 9 sezonów × 25 scen × 13 winnic ==")
    for ys in (0.2, 0.4, 0.6):
        print(simulate_t1(ys, rng))
    print("-- rozkalibrowanie: z rozciągnięte 1,3 raza (p ≈ 22%) --")
    print(simulate_t1(0.4, rng, scale=1.3))


if __name__ == "__main__":
    main()
