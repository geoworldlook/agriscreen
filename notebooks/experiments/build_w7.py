"""
Generator notatnika notebooks/experiments/W7_wskazowki.ipynb — eksperyment W7 „Wskazówki AgriScreen potwierdzone
pomiarami” (protokół docs/evidence/W7_protokol_wskazowki.md, D-093).

Uruchomienie (środowisko agriscreen, z katalogu projektu):
    python notebooks/experiments/build_w7.py
    jupyter nbconvert --to notebook --execute --inplace notebooks/experiments/W7_wskazowki.ipynb
Dane: archiwa ICOS L2 (MANIFEST_W7.csv), ERA5-Land i Sentinel-2 stacji (data/W7_stacje), czujnik ISMN Condom,
Météo-France, deklaracje celne Gers. Notatnik z wynikami jest w git (wyniki są częścią dowodu).
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))

CELLS = [
    ("md", """# W7 — wskazówki AgriScreen potwierdzone pomiarami (D-093)

**Pytanie.** Czy wskazówki z panelu trafiają częściej niż przypadek, gdy sprawdzimy je na **rzeczywistych pomiarach
naziemnych**? Nie oceniamy dokładnej wilgotności gleby ani stanu wody w winorośli, tylko to, czy wskazówka trafia.

**Zasady** (protokół `docs/evidence/W7_protokol_wskazowki.md`, zarejestrowany przed liczeniem):
- prawda = tylko wartości zmierzone (znacznik jakości 0) i oficjalne rejestry; wartości uzupełnione modelem odrzucone;
- stacje wybrane regułą: wszystkie stacje ICOS we Francji z produktem L2 Fluxnet + czujnik ISMN w Condom;
- produkt bez zmian (ERA5-Land, Sentinel-2, progi z panelu);
- dwa testy rozstrzygające: **K1** „gleba sucha” i **K2** „roślinność poniżej swojej normy”;
  kryterium: lepiej niż przypadek (dolna granica przedziału > 0) **i** potwierdzenie w ≥ 6 na 10 przypadków;
- testy na danych do 30.09.2026; wynik negatywny pokazujemy tak samo jak pozytywny."""),
    ("md", "## 0. Protokół, dane i ich pochodzenie"),
    ("code", """import os, sys, json, warnings
warnings.filterwarnings('ignore')
CODE_DIR = os.path.abspath(os.path.join(os.getcwd(), '..', '..')) if os.path.basename(os.getcwd()) == 'experiments' \\
    else os.path.abspath('.')
sys.path.insert(0, CODE_DIR)
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from IPython.display import display, Markdown
from agriscreen import local, parcel, weather
from agriscreen.config import make_config, era5_csv
from agriscreen.experiments import w7, w7_data

settings = local.load_settings()
cfg = make_config(CODE_DIR, data_dir=settings['data_dir'])
REF = cfg['REF_DIR']; W7DIR = os.path.join(settings['data_dir'], 'data', 'W7_stacje'); OUT = cfg['OUTPUT_DIR']
sha = parcel.protocol_sha(os.path.join(CODE_DIR, 'docs', 'evidence', 'W7_protokol_wskazowki.md'))
assert sha['status'] == 'REGISTERED' and sha['sha256'] == sha['registered'], f'protokół zmieniony: {sha}'
print(f"Protokół W7: {sha['status']}, SHA-256 {sha['sha256'][:16]}… (zgodny z zarejestrowanym); zamrożenie {w7.FREEZE}")
meta = pd.read_csv(os.path.join(REF, 'W7_stations.csv'))
man = w7_data.read_manifest(os.path.join(REF, 'MANIFEST_W7.csv'))
show = man.assign(sha256=man['sha256'].str[:12] + '…', MB=(man['bytes'].astype(float) / 1e6).round(1))
display(meta)
display(show[['station', 'spec', 'file_name', 'downloaded_utc', 'MB', 'sha256', 'licence']])"""),
    ("md", """## 1. K1 — „gleba sucha”: czy czujnik w gruncie był wtedy poniżej swojej normy?
Wskazówka: percentyl ERA5-Land 0–100 cm ≤ 30 (jak karta). Prawda: wilgotność gleby z czujnika (ICOS: warstwa
0–100 cm ważona miąższością; Condom: ISMN 20–30 cm) poniżej mediany tej samej pory roku z **innych lat**.
Dni IV–X do zamrożenia."""),
    ("code", """FZ = pd.Timestamp(w7.FREEZE)
k1_parts, k1_info = [], []

def k1_rows(site, truth, pct):
    ev = w7.events(truth[truth.index <= FZ])
    d = ev.join(pct.rename('pct'), how='inner').dropna(subset=['pct'])
    d = d[w7._in_months(d.index, w7.SOIL_MONTHS) & (d.index <= FZ)]
    return d.assign(site=site, year=d.index.year, hint_dry=d['pct'] <= w7.DRY_PCT, hint_wet=d['pct'] >= w7.WET_PCT)

for r in meta.itertuples():
    try:
        truth, info = w7.soil_daily(w7.archive_path(REF, r.station), r.station)
        pct = w7.soil_percentile(w7.era5_frame(os.path.join(W7DIR, f'{r.station}_era5_land_daily.csv')), cfg)
        d = k1_rows(r.station, truth, pct)
        k1_parts.append(d)
        k1_info.append({'site': r.station, 'levels_0_1m': info.get('depths'), 'days': len(d),
                        'years': f"{d['year'].min()}–{d['year'].max()}" if len(d) else '—'})
    except Exception as e:
        k1_info.append({'site': r.station, 'levels_0_1m': None, 'days': 0, 'years': f'brak: {type(e).__name__}: {e}'})
# Condom: czujnik ISMN A4 W1 (20–30 cm) i ERA5-Land punktu winnicy
cond = parcel.sensor_daily(cfg)['W1']['sm']
pct_c = w7.soil_percentile(w7.era5_frame(era5_csv(cfg)), cfg)
d = k1_rows('ISMN_Condom', cond, pct_c); k1_parts.append(d)
k1_info.append({'site': 'ISMN_Condom', 'levels_0_1m': '20–30 cm (A4 W1)', 'days': len(d),
                'years': f"{d['year'].min()}–{d['year'].max()}"})
K1 = pd.concat(k1_parts)
display(pd.DataFrame(k1_info))"""),
    ("code", """def stat_row(name, s, test=None):
    r = {k: s[k] for k in ('p', 'p_lo', 'p_hi', 'b', 'delta', 'delta_lo', 'delta_hi', 'n_hint', 'n_all', 'years_hint', 'sites')}
    r = {'test': name, **r}
    if test: r['werdykt'] = w7.verdict(s)
    return r

s1 = w7.hit_stats(K1, 'hint_dry', 'truth_below')
s1w = w7.hit_stats(K1, 'hint_wet', 'truth_above')
k1_tab = pd.DataFrame([stat_row('K1 gleba sucha → czujnik poniżej normy', s1, True),
                       stat_row('opisowo: gleba wilgotna → czujnik powyżej normy', s1w)])
display(k1_tab.round(3))
per = []
for site, g in K1.groupby('site'):
    h = g[g['hint_dry']]
    per.append({'site': site, 'dni': len(g), 'dni „sucho”': len(h), 'p (trafność)': h['truth_below'].mean() if len(h) else np.nan,
                'b (przypadek)': g['truth_below'].mean()})
k1_sites = pd.DataFrame(per); display(k1_sites.round(3))
print(f"K1: p = {s1['p']:.1%} [{s1['p_lo']:.1%}; {s1['p_hi']:.1%}], przypadek b = {s1['b']:.1%}, "
      f"Δ = {s1['delta']:+.1%} [{s1['delta_lo']:+.1%}; {s1['delta_hi']:+.1%}] → {w7.verdict(s1).upper()}")"""),
    ("md", """## 2. K2 — „roślinność poniżej swojej normy”: czy zmierzone parowanie było wtedy poniżej normy?
Wskazówka: z_woda ≤ −1 dla kwadratu 300 m wokół wieży (produkt bez zmian). Prawda: średnie dzienne parowanie (LE,
tylko półgodziny zmierzone) z okna [t−3, t+3] poniżej mediany z innych lat. Sceny VI–IX do zamrożenia;
7 stacji bez upraw polowych."""),
    ("code", """k2_parts, k2_info, FLUX = [], [], {}

def k2_rows(site, truth_daily, z, col='z'):
    ev = w7.events(w7.window_mean(truth_daily[truth_daily.index <= FZ]))
    d = z[[col]].rename(columns={col: 'z'}).join(ev, how='inner')
    d = d[w7._in_months(d.index, w7.VEG_MONTHS) & (d.index <= FZ)]
    return d.assign(site=site, year=d.index.year, hint_below=d['z'] <= w7.Z_LOW, hint_above=d['z'] >= w7.Z_HIGH)

for r in meta[meta['vegetation_test']].itertuples():
    try:
        fd = w7.flux_daily(w7.archive_path(REF, r.station), r.station); FLUX[r.station] = fd
        z = w7.station_water_z(os.path.join(W7DIR, r.station), CODE_DIR)
        d = k2_rows(r.station, fd['et_le'], z); k2_parts.append(d)
        k2_info.append({'site': r.station, 'sceny S2 z z_woda': len(z), 'sceny w teście': len(d),
                        'lata': f"{d['year'].min()}–{d['year'].max()}" if len(d) else '—'})
    except Exception as e:
        k2_info.append({'site': r.station, 'sceny S2 z z_woda': 0, 'sceny w teście': 0, 'lata': f'brak: {type(e).__name__}: {e}'})
K2 = pd.concat(k2_parts) if k2_parts else pd.DataFrame()
display(pd.DataFrame(k2_info))"""),
    ("code", """s2 = w7.hit_stats(K2, 'hint_below', 'truth_below')
s2a = w7.hit_stats(K2, 'hint_above', 'truth_above')
k2_tab = pd.DataFrame([stat_row('K2 roślinność poniżej normy → parowanie poniżej normy', s2, True),
                       stat_row('opisowo: roślinność powyżej normy → parowanie powyżej normy', s2a)])
display(k2_tab.round(3))
per = []
for site, g in K2.groupby('site'):
    h = g[g['hint_below']]
    per.append({'site': site, 'sceny': len(g), 'sceny „poniżej”': len(h), 'p (trafność)': h['truth_below'].mean() if len(h) else np.nan,
                'b (przypadek)': g['truth_below'].mean(),
                'ρ z_woda–anomalia ET': w7.spearman(g['z'], g['truth'] - g['normal'])})
k2_sites = pd.DataFrame(per); display(k2_sites.round(3))
print(f"K2: p = {s2['p']:.1%} [{s2['p_lo']:.1%}; {s2['p_hi']:.1%}], przypadek b = {s2['b']:.1%}, "
      f"Δ = {s2['delta']:+.1%} [{s2['delta_lo']:+.1%}; {s2['delta_hi']:+.1%}] → {w7.verdict(s2).upper()}")"""),
    ("md", """## 3. Opisowo (bez wpływu na werdykt)
Fotosynteza (GPP, wyliczona z pomiaru CO₂) i udział parowania w energii (EF) zamiast parowania; kwadrat 200 i 500 m;
związek wewnątrz sezonu i między sezonami."""),
    ("code", """desc = []
for var in ('gpp', 'ef'):
    parts = []
    for r in meta[meta['vegetation_test']].itertuples():
        if r.station not in FLUX: continue
        z = w7.station_water_z(os.path.join(W7DIR, r.station), CODE_DIR)
        parts.append(k2_rows(r.station, FLUX[r.station][var], z))
    if parts:
        desc.append(stat_row(f'R-poniżej → {var.upper()} poniżej normy', w7.hit_stats(pd.concat(parts), 'hint_below', 'truth_below')))
for sid, side in (('VINEYARD_02', 200), ('VINEYARD_03', 500)):
    parts = []
    for r in meta[meta['vegetation_test']].itertuples():
        if r.station not in FLUX: continue
        try:
            z = w7.station_water_z(os.path.join(W7DIR, r.station), CODE_DIR, site_id=sid)
            parts.append(k2_rows(r.station, FLUX[r.station]['et_le'], z))
        except Exception:
            pass
    if parts:
        desc.append(stat_row(f'R-poniżej → ET, kwadrat {side} m', w7.hit_stats(pd.concat(parts), 'hint_below', 'truth_below')))
display(pd.DataFrame(desc).round(3))
a = K2.assign(anom=K2['truth'] - K2['normal'])
within = a.groupby(['site', 'year'])[['z', 'anom']].transform(lambda x: x - x.mean())
seas = a.groupby(['site', 'year'])[['z', 'anom']].mean()
print(f"ρ wewnątrz sezonu = {w7.spearman(within['z'], within['anom']):.2f}; ρ średnich sezonów = {w7.spearman(seas['z'], seas['anom']):.2f} "
      f"(n sezonów = {len(seas)})")"""),
    ("md", """### Przymrozek i upał (opisowo)
Wskazówka: ERA5-Land w punkcie stacji (progi produktu; w Condom progi z panelu). Prawda: zmierzona Tmin ≤ 0 °C
w sezonie przymrozków, Tmax ≥ 35 °C w sezonie upałów."""),
    ("code", """rows = []
thr = json.load(open(os.path.join(OUT, 'hazard_thresholds.json'), encoding='utf-8'))
def hazard_rows(site, e, tmin, tmax, f_thr, h_thr):
    out = []
    for kind, season, prod, truth in (('przymrozek', cfg['FROST_SEASON'], e['t2m_min_c'] <= f_thr, tmin <= w7.FROST_T),
                                       ('upał', cfg['HEAT_SEASON'], e['t2m_max_c'] >= h_thr, tmax >= w7.HEAT_T)):
        d = pd.DataFrame({'hint': prod, 'truth': truth.reindex(prod.index)}).dropna()
        d = d[w7._in_season(d.index, season) & (d.index <= FZ)].astype(bool)
        out.append({'site': site, 'zdarzenie': kind, **w7.contingency(d, 'hint', 'truth')})
    return out
for r in meta.itertuples():
    if r.station in FLUX:
        fd = FLUX[r.station]
    else:
        try: fd = w7.flux_daily(w7.archive_path(REF, r.station), r.station)
        except Exception: continue
    e = w7.era5_frame(os.path.join(W7DIR, f'{r.station}_era5_land_daily.csv'))
    rows += hazard_rows(r.station, e, fd['tmin'], fd['tmax'], cfg['FROST_TMIN'], cfg['HEAT_TMAX'])
# Condom: stacje Météo-France z task_weather, ERA5 punktu winnicy, progi z panelu
mfs = pd.read_csv(os.path.join(OUT, 'mf_stations.csv'))
import glob
mf = weather.read_mf(sorted(glob.glob(os.path.join(cfg['MF_DIR'], 'Q_*RR-T-Vent.csv.gz'))), start='2016-01-01')
ec = w7.era5_frame(era5_csv(cfg))
for _, s in mfs.iterrows():
    st = mf[mf['num_poste'] == s['num_poste']].set_index(pd.to_datetime(mf.loc[mf['num_poste'] == s['num_poste'], 'time']))
    rows += hazard_rows(f"MF {s.get('name', s['num_poste'])}", ec, st['tn'], st['tx'], thr.get('frost', cfg['FROST_TMIN']),
                        thr.get('heat', cfg['HEAT_TMAX']))
hz = pd.DataFrame(rows); display(hz.round(2))"""),
    ("md", """### Winnice w Gers: plon wina a roślinność 13 winnic (oficjalny rejestr, opisowo)
Plon = produkcja całkowita / powierzchnia winnic w produkcji (deklaracje celne, departament 32). Roślinność =
mediana z_woda 13 winnic z QC w VI–IX. Tylko 9 lat i wiele innych przyczyn (przymrozki 2017 i 2021, grad, mildiu):
bez kryterium."""),
    ("code", """dg = w7_data.douane_gers(os.path.join(REF, 'douane'))
pa = pd.read_csv(os.path.join(OUT, 'parcel_anomalies.csv'), parse_dates=['time'])
wz = pa[(pa['index'] == 'water') & pa['site_id'].isin(parcel.qc_sites(pa))].dropna(subset=['z'])
wz = wz[wz['time'].dt.month.between(6, 9)]
vy = wz.groupby(wz['time'].dt.year)['z'].median().rename('z_woda_mediana')
g = dg.set_index('year').join(vy, how='left')
display(g.round(2))
gg = g.loc[2017:2025].dropna()
print(f"ρ (plon, mediana z_woda) 2017–2025 = {w7.spearman(gg['yield_hl_ha'], gg['z_woda_mediana']):.2f} (n = {len(gg)})")"""),
    ("md", "## 4. Werdykt i zapis wyników"),
    ("code", """res = pd.concat([k1_tab.iloc[[0]], k2_tab.iloc[[0]]])
display(res[['test', 'p', 'p_lo', 'p_hi', 'b', 'delta', 'delta_lo', 'delta_hi', 'n_hint', 'years_hint', 'sites', 'werdykt']].round(3))
fig, ax = plt.subplots(figsize=(8, 3.2))
lab = ['K1: gleba sucha', 'K2: roślinność poniżej normy']
for i, s in enumerate((s1, s2)):
    ax.barh(i + 0.18, 100 * s['p'], 0.34, color='tab:blue', label='trafność wskazówki' if i == 0 else None)
    ax.errorbar(100 * s['p'], i + 0.18, xerr=[[100 * (s['p'] - s['p_lo'])], [100 * (s['p_hi'] - s['p'])]], color='k', capsize=3)
    ax.barh(i - 0.18, 100 * s['b'], 0.34, color='0.75', label='przypadek' if i == 0 else None)
ax.axvline(60, color='tab:red', ls='--', lw=1, label='próg praktyczny 60%')
ax.set_yticks([0, 1], lab); ax.set_xlim(0, 100); ax.set_xlabel('% przypadków potwierdzonych pomiarem')
ax.legend(fontsize=8, loc='lower right'); plt.tight_layout(); plt.show()
tests = res.assign(protocol_sha256=sha['sha256'], freeze=w7.FREEZE)
tests.to_csv(os.path.join(OUT, 'w7_tests.csv'), index=False)
pd.concat([k1_tab, k2_tab, pd.DataFrame(desc)]).to_csv(os.path.join(OUT, 'w7_all_rows.csv'), index=False)
k1_sites.to_csv(os.path.join(OUT, 'w7_k1_sites.csv'), index=False); k2_sites.to_csv(os.path.join(OUT, 'w7_k2_sites.csv'), index=False)
hz.to_csv(os.path.join(OUT, 'w7_hazards.csv'), index=False); g.to_csv(os.path.join(OUT, 'w7_gers_yield.csv'))
K1.to_csv(os.path.join(OUT, 'w7_k1_days.csv')); K2.to_csv(os.path.join(OUT, 'w7_k2_scenes.csv'))
print('Zapisano: w7_tests.csv, w7_all_rows.csv, w7_k1_sites.csv, w7_k2_sites.csv, w7_hazards.csv, w7_gers_yield.csv, w7_k1_days.csv, w7_k2_scenes.csv')"""),
    ("md", """## 5. Wnioski
Opis wyników i decyzja: `docs/evidence/W7_wyniki.md` (po przebiegu tego notatnika)."""),
]


def create(path=os.path.join(HERE, "W7_wskazowki.ipynb")):
    nb = {"cells": [], "nbformat": 4, "nbformat_minor": 5,
          "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3 (agriscreen)", "language": "python"},
                       "language_info": {"name": "python"}}}
    for i, (kind, text) in enumerate(CELLS):
        src = [line + "\n" for line in text.strip().split("\n")]
        src[-1] = src[-1].rstrip("\n")
        cell = {"id": f"w7{i:02d}", "metadata": {}, "source": src}
        if kind == "md":
            cell["cell_type"] = "markdown"
        else:
            cell.update({"cell_type": "code", "execution_count": None, "outputs": []})
        nb["cells"].append(cell)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
    print(f"Wygenerowano: {path}")


if __name__ == "__main__":
    create()
