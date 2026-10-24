"""
Generator notatnika notebooks/AgriScreen_Local.ipynb (Jupyter na własnym komputerze: podgląd wyników z Dysku Google
i, na żądanie, cały potok AgriScreen). Wzór: notebooks/build_monitor.py (Colab).

Uruchomienie: python notebooks/build_local.py   (robi to też skrypt agriscreen_jupyter.cmd, gdy notatnika brak)
Notatnik jest poza git (.gitignore): zapisane wyniki komórek nie blokują `git pull` w przebiegu tygodniowym.
Nowa wersja notatnika: usuń plik i uruchom generator ponownie.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CELLS = [
    ("md", """# AgriScreen Local — 15 winnic wobec własnej historii (Condom, Gers)
Notatnik na tym komputerze (Jupyter), wzorowany na `AgriScreen_Monitor.ipynb` z Colab. Kod: `projects\\agriscreen`,
dane: Dysk Google (`local_settings.json`). Uruchom wszystko: menu *Run → Run All Cells*.

- **Podgląd (domyślnie, `RECOMPUTE = False`):** nic nie liczy, czyta wyniki z Dysku — ostatni przebieg, panel,
  winnice, testy W3b, walidacja, raport, rejestr. Kilka sekund, bez Earth Engine.
- **Obliczenia (`RECOMPUTE = True`):** wszystkie zadania jak `python -m agriscreen run` (z blokadą przed drugim
  przebiegiem, np. zadaniem z Harmonogramu albo Colab), bez publikacji na GitHub. Publikacja: przebieg tygodniowy
  albo `python -m agriscreen publish`.
- Instrukcja: `docs/URUCHOMIENIE_LOKALNE.md`; protokoły i wyniki: `docs/evidence/`."""),
    ("md", "## 0. Ustawienia notatnika"),
    ("code", """RECOMPUTE = False         # True: przelicz wszystko przed podglądem
INGEST = True             # przy RECOMPUTE: pobierz nowe dane (Sentinel-2, ERA5-Land przez Earth Engine, SWI)
RUN_EXPERIMENTS = True    # przy RECOMPUTE: także eksperymenty W3c i W3d (panel ich nie rysuje)
SITE = None               # winnica do wykresu w §4 (None = MAIN_SITE z config.py, VINEYARD_06)"""),
    ("md", "## 1. Kod i dane"),
    ("code", """import os, sys, json, glob, subprocess
CODE_DIR = os.path.abspath('..') if os.path.basename(os.getcwd()) == 'notebooks' else os.path.abspath('.')
if CODE_DIR not in sys.path:
    sys.path.insert(0, CODE_DIR)
import pandas as pd
from IPython.display import display, Markdown
import agriscreen
from agriscreen import local
settings = local.load_settings()
DATA_DIR = settings['data_dir']
git = lambda *a: subprocess.run(['git', '-C', CODE_DIR, *a], capture_output=True, text=True).stdout.strip()
print(f"AgriScreen {agriscreen.__version__}, kod {git('log', '-1', '--format=%h %ci %s')}")
print(f"Gałąź: {git('rev-parse', '--abbrev-ref', 'HEAD')}; niezapisane zmiany: {git('status', '--porcelain', '--untracked-files=no') or 'brak'}")
print('Kod: ', CODE_DIR)
print('Dane:', DATA_DIR)"""),
    ("md", """## 2. Obliczenia (tylko przy `RECOMPUTE = True`)
Kolejność jak w Colab: Sentinel-2, ERA5-Land i SWI → statystyki 15 winnic (pas 20 m) → gleba → testy W3b
(zamrożone) → anomalie → walidacja warstwy wody (3 stacje) → pogoda (Météo-France) → [W3c, W3d] → panel → raport.
Earth Engine bez okna logowania: gdy logowanie wygasło, liczy na danych z Dysku (w konsoli: `earthengine authenticate`).
Pierwsze pobranie po dłuższej przerwie może trwać długo."""),
    ("code", """if RECOMPUTE:
    with local.Lock(DATA_DIR):
        res = local.run(settings, ingest_data=INGEST, experiments=RUN_EXPERIMENTS)
    bad = [k for k, v in res['results'].items() if not isinstance(v, dict)]
    print(f"Zadania z błędem: {', '.join(bad) or 'brak'}")
else:
    print('Podgląd: bez obliczeń (RECOMPUTE = False).')"""),
    ("code", """from agriscreen.config import make_config
from agriscreen.runtime import setup_runtime, run_history, registry_summary, show_html
rt = setup_runtime(CODE_DIR, pull=False, install=False, init_gee=False, data_dir=DATA_DIR)
cfg = make_config(CODE_DIR, data_dir=DATA_DIR)
OUT = cfg['OUTPUT_DIR']
out = lambda name: os.path.join(OUT, name)
print('Wyniki:', OUT)"""),
    ("md", """## 3. Ostatni przebieg
Podsumowanie przebiegu tygodniowego (`last_weekly.json`) i koniec najnowszego logu z `data\\logs`."""),
    ("code", """LOGS = os.path.join(DATA_DIR, 'data', 'logs')
lw = os.path.join(LOGS, 'last_weekly.json')
if os.path.exists(lw):
    print(json.dumps(json.load(open(lw, encoding='utf-8')), ensure_ascii=False, indent=1))
else:
    print('Brak last_weekly.json (przebieg tygodniowy jeszcze nie działał).')
logs = sorted(glob.glob(os.path.join(LOGS, '*.log')), key=os.path.getmtime)
if logs:
    lines = open(logs[-1], encoding='utf-8', errors='replace').read().splitlines()
    print(f"\\n--- {os.path.basename(logs[-1])}: zadania, ostrzeżenia, błędy ---")
    print('\\n'.join(l for l in lines if l.startswith('[') or ' WARNING ' in l or ' ERROR ' in l))"""),
    ("md", """## 4. Winnice: ostatnia scena wobec własnej historii
z = (wartość − średnia z lat wcześniejszych tej samej pory) / odchylenie. Około jedna scena na sześć jest poniżej −1
z samej definicji, więc pojedyncze z ≈ −1 to nic niezwykłego. `qc_ok = False`: za mało pikseli 10 m po pasie 20 m
(wynik tylko poglądowy). Warstwa `water` to wskaźnik wody w roślinności z panelu (z_woda)."""),
    ("code", """an = pd.read_csv(out('parcel_anomalies.csv'), parse_dates=['time'])
qc = pd.read_csv(out('parcel_qc.csv'))
last = (an.dropna(subset=['z']).sort_values('time')
          .groupby(['site_id', 'index']).tail(1)
          .pivot_table(index='site_id', columns='index', values='z'))
cols = [c for c in ('water', 'ndvi', 'ndmi', 'ndre') if c in last]
day = (an.dropna(subset=['z']).groupby('site_id')['time'].max().dt.strftime('%Y-%m-%d').rename('ostatnia scena'))
tab = last[cols].round(2).join(day).join(qc.set_index('site_id')[['area_ha', 'n_pixels', 'qc_ok']])
display(tab.style.background_gradient(cmap='RdBu', vmin=-2.5, vmax=2.5, subset=cols).format(precision=2, subset=cols))"""),
    ("code", """import matplotlib.pyplot as plt
site = SITE or cfg['MAIN_SITE']
s = an[(an.site_id == site) & (an['index'] == 'water')].dropna(subset=['z']).sort_values('time')
s = s[s.time >= s.time.max() - pd.DateOffset(years=2)]
fig, ax = plt.subplots(figsize=(11, 3.2))
ax.axhspan(-1, 1, color='0.92', zorder=0, label='±1 (zwykły zakres)')
for i, (_, g) in enumerate(s.groupby(s.time.dt.year)):   # osobna linia na sezon: bez łączenia przez zimę
    ax.plot(g.time, g.z, '-o', ms=3, lw=1, color='tab:blue', label=f'{site}: z_woda' if i == 0 else None)
ax.axhline(0, color='0.5', lw=0.8)
ax.set_ylabel('z'); ax.set_title(f'{site}: wskaźnik wody w roślinności wobec własnej historii, ostatnie 2 lata')
ax.legend(loc='lower left', fontsize=8); plt.tight_layout(); plt.show()"""),
    ("md", """## 5. Testy W3b (zamrożone) i walidacja warstwy wody
Testy W3b liczone według zarejestrowanego protokołu na scenach do daty zamrożenia (`w3b_freeze.json`); werdykty
tylko tam, gdzie protokół ma kryterium. Walidacja: korelacja anomalii ERA5-Land i SWI z czujnikami w gruncie
(Condom ISMN, Auradé i Lusignan ICOS); `checked` = porównanie bez progu zaliczenia."""),
    ("code", """t = pd.read_csv(out('w3b_tests.csv'))
keep = t['verdict'].notna() & (t['verdict'].astype(str) != '')
cols = ['segment', 'period', 'subset', 'metric', 'value', 'ci_low', 'ci_high', 'n', 'verdict']
display(t.loc[keep, cols].round(3).reset_index(drop=True))
print('Zamrożenie:', json.load(open(out('w3b_freeze.json'), encoding='utf-8')).get('freeze'))"""),
    ("code", """v = pd.read_csv(out('validation_reference.csv'))
r = v[v.metric == 'pearson_r'].copy()
r['R [95% CI]'] = r.apply(lambda x: f"{x.value:.2f} [{x.ci_low:.2f}; {x.ci_high:.2f}]", axis=1)
display(r.pivot_table(index=['site_id', 'reference', 'segment'], columns='product', values='R [95% CI]', aggfunc='first'))"""),
    ("md", """## 6. Panel AgriScreen (EN) — produkt
Ten sam `panel.html`, który trafia na GitHub. Mapa potrzebuje internetu (Leaflet i podkład Esri / Sentinel-2).
Gdy ramka jest pusta, otwórz panel w przeglądarce (`OPEN_IN_BROWSER = True`)."""),
    ("code", """import warnings
warnings.filterwarnings('ignore', message='Consider using IPython.display.IFrame')
OPEN_IN_BROWSER = False
path = out('panel.html')
if os.path.exists(path):
    show_html(path, height=3600)
    if OPEN_IN_BROWSER:
        os.startfile(path)
else:
    print('Brak panel.html — uruchom obliczenia (RECOMPUTE = True).')"""),
    ("md", """## 7. Raport z uruchomienia
`run_summary.md`: wersja i commit, pokrycie danych, testy W3b, walidacja, pogoda, eksperymenty, ostatnie zadania."""),
    ("code", """display(Markdown(open(out('run_summary.md'), encoding='utf-8').read()))"""),
    ("md", "## 8. Rejestr i historia uruchomień"),
    ("code", """display(registry_summary(rt))
display(run_history(rt, n=15))"""),
]


def create_local_notebook(path=os.path.join(ROOT, "notebooks", "AgriScreen_Local.ipynb")):
    nb = {"cells": [], "nbformat": 4, "nbformat_minor": 5,
          "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3 (agriscreen)", "language": "python"},
                       "language_info": {"name": "python"}}}
    for i, (kind, text) in enumerate(CELLS):
        src = [line + "\n" for line in text.strip().split("\n")]
        src[-1] = src[-1].rstrip("\n")
        cell = {"id": f"c{i:02d}", "metadata": {}, "source": src}
        if kind == "md":
            cell["cell_type"] = "markdown"
        else:
            cell.update({"cell_type": "code", "execution_count": None, "outputs": []})
        nb["cells"].append(cell)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
    print(f"Wygenerowano: {os.path.relpath(path, ROOT)}")


if __name__ == "__main__":
    create_local_notebook()
