"""
Generator notatnika notebooks/AgriScreen_Monitor.ipynb (Colab: cały potok AgriScreen v1 na danych z Dysku Google).
Uruchomienie: python notebooks/build_monitor.py. Notatnik generujemy tylko celowo — nadpisanie kasuje zapisane wyniki
komórek (poprzednie przebiegi są w historii git).
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CELLS = [
    ("md", """# AgriScreen Monitor — 15 winnic wobec własnej historii (Condom, Gers)
Notatnik uruchamia cały potok AgriScreen v1. Otwórz go z GitHub (Plik → Otwórz notatnik → GitHub), potem
`Środowisko wykonawcze → Uruchom wszystko`. GPU nie jest potrzebne.

Łańcuch: Sentinel-2, ERA5-Land i satelitarny SWI (Copernicus) → statystyki 15 winnic z pasem 20 m od brzegu →
gleba (ERA5-Land) → testy W3b (zamrożone) → anomalie winnic wobec własnej historii → walidacja warstwy wody na
3 stacjach → pogoda (Météo-France) → **panel (EN) i jego dane JSON** → raport z uruchomienia.

- Kod: pakiet `agriscreen/` (opis: `docs/ARCHITEKTURA.md`); to samo bez notatnika: `pipeline.run_all(rt, cfg)`.
- Protokoły zarejestrowane przed liczeniem i wyniki: `docs/evidence/` (zbiorczo `karta_wynikow.md`).
- Klucze: tylko z `MyDrive/GeoWorldLook/secrets/` (np. `cdse.env`); notatnik nie wypisuje ich treści.
- Wyniki: `MyDrive/GeoWorldLook/agriwatch/data/05_Final_Outputs/agriwatch/` (`panel.html`, `panel_data.json`,
  `run_summary.md`) i tabele `data/registry/gwl_*.csv`."""),
    ("md", "## 1. Dysk Google i kod z GitHub"),
    ("code", """import os, sys
try:
    from google.colab import drive
    drive.mount('/content/drive')
    IN_COLAB = True
except Exception:
    IN_COLAB = False

REPO_URL = 'https://github.com/geoworldlook/agriscreen.git'
PROJECT_DIR = '/content/drive/MyDrive/GeoWorldLook/agriwatch'   # kod i dane projektu na Dysku
if IN_COLAB:
    if not os.path.exists(os.path.join(PROJECT_DIR, '.git')):
        os.makedirs(os.path.dirname(PROJECT_DIR), exist_ok=True)
        !git clone {REPO_URL} "{PROJECT_DIR}"
    # lokalne zmiany (np. zapisany notatnik) blokowałyby `pull --ff-only`: odkładamy je do stash (git stash list)
    !git -C "{PROJECT_DIR}" stash push -q -m "colab-autostash" || true
    !git -C "{PROJECT_DIR}" pull --ff-only
    !git -C "{PROJECT_DIR}" log -1 --format="Kod: %h %ci %s"
    if os.popen(f'git -C "{PROJECT_DIR}" rev-parse HEAD').read() != os.popen(f'git -C "{PROJECT_DIR}" rev-parse origin/main').read():
        print('[UWAGA] Kod na Dysku różni się od origin/main — wyniki będą z innej wersji kodu.')
else:
    PROJECT_DIR = os.path.abspath('..') if os.path.basename(os.getcwd()) == 'notebooks' else os.path.abspath('.')
os.chdir(PROJECT_DIR)
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)
import importlib
sys.modules.setdefault('imp', importlib)
try:
    %load_ext autoreload
    %autoreload 2
except Exception as e:
    print(f'[INFO] autoreload pominięty ({e})')
print('Projekt:', PROJECT_DIR)"""),
    ("md", """## 2. Środowisko i konfiguracja
`setup_runtime`: brakujące pakiety, Google Earth Engine, rejestr. `make_config`: ustawienia z `agriscreen/config.py`
(zmiana np. `make_config(PROJECT_DIR, {'MAIN_SITE': 'VINEYARD_07'})`). Wartości metod pochodzą z zarejestrowanych
protokołów — ich zmiana to nowa wersja protokołu."""),
    ("code", """import agriscreen
from agriscreen import pipeline as p
from agriscreen import experiments
from agriscreen.config import make_config
from agriscreen.runtime import setup_runtime, run_task, run_history, registry_summary, show_html
rt = setup_runtime(PROJECT_DIR, gee_project='ee-geoworldlook', pull=False)
cfg = make_config(PROJECT_DIR)
print(f"AgriScreen {agriscreen.__version__}, kod {rt['GIT_COMMIT']}")"""),
    ("md", """## 3. Dane: Sentinel-2, ERA5-Land, satelitarny SWI
Wszystko przyrostowo: rastry Sentinel-2 L2A sezonu IV–X (GEE, manifest), ERA5-Land 1991 → dziś w punkcie winnicy,
SWI 0,1° v4 (od 2007) i 1 km v2 (od VII 2025) z Copernicus Data Space."""),
    ("code", """run_task(rt, 'ingest_s2', p.task_ingest_s2, rt, cfg)
run_task(rt, 'ingest_era5', p.task_ingest_era5, rt, cfg)
run_task(rt, 'ingest_swi', p.task_ingest_swi, rt, cfg)"""),
    ("md", """## 4. Winnice: statystyki, gleba, testy W3b i anomalie
- `parcel_stats`: średnie wskaźników i pasm dla 15 winnic z pasem 20 m od brzegu (pierwsze uruchomienie przelicza
  całe archiwum, ok. 5–15 min; potem tylko nowe sceny). Próg: 40 pikseli 10 m (oczekiwane 13 z 15 winnic).
- `soil`: percentyl wilgotności ERA5-Land 0–100 cm wobec 1991–2020, SPI-1, SPI-3.
- `parcel_tests`: testy W3b według zarejestrowanego protokołu, na scenach do daty zamrożenia (`w3b_freeze.json`).
  Liczone raz na wersję kodu; nowy commit liczy je od nowa na tych samych danych i **musi dać te same liczby**
  (`docs/evidence/W3b_wyniki.md`).
- `parcel_anomalies`: anomalie wszystkich winnic do karty i panelu, mediana okolicy, flaga zmiany gospodarowania."""),
    ("code", """run_task(rt, 'parcel_stats', p.task_parcel_stats, rt, cfg)
run_task(rt, 'soil', p.task_soil, rt, cfg)
run_task(rt, 'parcel_tests', p.task_parcel_tests, rt, cfg)
run_task(rt, 'parcel_anomalies', p.task_parcel_anomalies, rt, cfg)"""),
    ("md", """## 5. Walidacja warstwy wody i pogoda
- `reference`: ERA5-Land i SWI wobec czujników w gruncie — Condom (ISMN, po kontroli A4), Auradé i Lusignan (ICOS);
  protokół `docs/evidence/W2_REF_protokol_walidacji.md`. Pierwsze uruchomienie pobiera dane stacji (kilkanaście minut).
- `weather`: Météo-France (Gers, Lot-et-Garonne) — walidacja Tmin, Tmax i opadu ERA5-Land, progi przymrozku i upału."""),
    ("code", """run_task(rt, 'reference', p.task_reference, rt, cfg)
run_task(rt, 'weather', p.task_weather, rt, cfg)"""),
    ("md", """## 6. Eksperymenty W3c i W3d (domyślnie wyłączone)
Miejsca wewnątrz winnicy wobec ich własnej historii: W3c „strefa gorsza niż zwykle” i W3d „najniżej od 5 lat”.
Oba nie przeszły zarejestrowanych testów w pierwszym przebiegu (`docs/evidence/W3c_wyniki.md`, `W3d_wyniki.md`);
panel ich nie rysuje, pokazuje tylko wynik testu w „How far to trust it”. Powtórka po sezonie 2027 z tymi samymi
regułami: ustaw `RUN_EXPERIMENTS = True`."""),
    ("code", """RUN_EXPERIMENTS = False
if RUN_EXPERIMENTS:
    run_task(rt, 'zones', experiments.task_zones, rt, cfg)
    run_task(rt, 'months', experiments.task_months, rt, cfg)"""),
    ("md", """## 7. Panel AgriScreen (EN) — produkt
Lista 15 winnic, mapa na zdjęciu satelitarnym (Esri) z półprzezroczystą warstwą: piksele 10 m (NDVI, NDRE, NDMI),
strefy wobec reszty działki tego samego dnia albo cała działka wobec własnej historii; statystyki, gleba, pogoda
(prognoza Open-Meteo), karta, sezon i „How far to trust it”. `panel.html` to jeden plik (Leaflet z unpkg) do
publikacji; `panel_data.json` czyta notatnik na blog (`notebooks/AgriScreen_story.ipynb`, przez `docs/showcase/`)."""),
    ("code", """run_task(rt, 'panel', p.task_panel, rt, cfg)
path = os.path.join(cfg['OUTPUT_DIR'], 'panel.html')
if os.path.exists(path):
    show_html(path, height=3600)"""),
    ("md", """## 8. Raport z uruchomienia
`run_summary.md`: wersja i commit, pokrycie danych, testy W3b, walidacja, pogoda, eksperymenty, ostatnie zadania.
Po większym uruchomieniu prześlij ten plik — na nim opieramy wnioski."""),
    ("code", """run_task(rt, 'summary', p.task_summary, rt, cfg)
print(open(os.path.join(cfg['OUTPUT_DIR'], 'run_summary.md'), encoding='utf-8').read())"""),
    ("md", "## 9. Rejestr i historia uruchomień"),
    ("code", """display(registry_summary(rt))
display(run_history(rt, n=15))"""),
]


def create_monitor_notebook(path=os.path.join(ROOT, "notebooks", "AgriScreen_Monitor.ipynb")):
    nb = {"cells": [], "nbformat": 4, "nbformat_minor": 0,
          "metadata": {"colab": {"name": "AgriScreen_Monitor.ipynb", "provenance": []},
                       "language_info": {"name": "python"}}}
    for kind, text in CELLS:
        src = [line + "\n" for line in text.strip().split("\n")]
        if kind == "md":
            nb["cells"].append({"cell_type": "markdown", "metadata": {}, "source": src})
        else:
            nb["cells"].append({"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
                                "source": src})
    with open(path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=2, ensure_ascii=False)
    print(f"Wygenerowano: {os.path.relpath(path, ROOT)}")


if __name__ == "__main__":
    create_monitor_notebook()
