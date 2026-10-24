# AgriScreen — architektura (wersja 1.0)

Opis kodu w pakiecie `agriscreen/`. Stan projektu i wyniki: `docs/STAN_I_PLAN.md`; zmiany wersji: `CHANGELOG.md`.

## 1. Przepływ

```text
GitHub (kod) ──git pull──▶ Dysk Google: MyDrive/GeoWorldLook/agriwatch (kod + dane) ◀── Colab (GEE, bez GPU)
                                         │
notebooks/AgriScreen_Monitor.ipynb ──▶ runtime.setup_runtime ──▶ runtime.run_task(...) dla każdego zadania
                                                                     │
 ingest_s2 ─▶ ingest_era5 ─▶ ingest_swi ─▶ parcel_stats ─▶ soil ─▶ parcel_tests ─▶ parcel_anomalies
 ─▶ reference ─▶ weather ─▶ [zones ─▶ months: eksperymenty, domyślnie wyłączone] ─▶ panel ─▶ summary
                                                                     │
                   data/registry/gwl_*.csv  +  data/05_Final_Outputs/agriwatch/ (panel.html, panel_data.json, …)
```

To samo bez notatnika: `pipeline.run_all(rt, cfg, ingest_data=True, experiments=False)`. Na własnym komputerze:
`python -m agriscreen weekly` (Harmonogram zadań Windows, `docs/URUCHOMIENIE_LOKALNE.md`); kod leży wtedy w klonie
na dysku C:, a dane w katalogu danych na Dysku Google (`make_config(..., data_dir=...)`, `setup_runtime(..., data_dir=...)`).
Każde zadanie zwraca słownik `{"message", "skipped"?, "registry"?}`; `run_task` zapisuje wiersz w `gwl_runs`
(czas, status, commit z flagą `+dirty`, parametry, liczba nowych wierszy). Błąd jednego zadania nie zatrzymuje
kolejnych.

## 2. Moduły

| Moduł | Odpowiedzialność | Główne funkcje |
|---|---|---|
| `config.py` | Wszystkie ustawienia w jednym miejscu; ścieżki względem katalogu projektu. Wartości metod pochodzą z protokołów (zmiana = nowa wersja protokołu) | `CONFIG`, `make_config`, `era5_csv`, `main_site_lonlat` |
| `runtime.py` | Środowisko (Colab / lokalnie), rejestr CSV, uruchamianie zadań | `setup_runtime`, `run_task`, `registry_read`, `registry_upsert`, `run_history`, `registry_summary`, `show_html` |
| `ingest.py` | Dane wejściowe: Sentinel-2 L2A z GEE (przyrostowo, manifest, maska chmur), ERA5-Land w punkcie (cache), satelitarny SWI z Copernicus Data Space (klucze tylko z folderu `secrets`), GeoTIFF | `sync_sentinel2_time_series`, `sync_era5_land_point`, `sync_swi_point`, `clean_swi`, `read_geotiff_to_numpy`, `write_geotiff` |
| `metrics.py` | Wskaźniki (NDVI, NDMI, NDRE, CRSWIR), statystyki działek z pasem wewnętrznym, anomalie klimatologiczne, SPI, tory orbit | `compute_indices`, `site_stats`, `load_parcels`, `clim_anomaly`, `rootzone`, `spi`, `era5_anomalies`, `track_ids`, `scene_anomaly` |
| `parcel.py` | W3b „Moja winnica”: anomalie 15 winnic wobec własnej historii i testy według protokołu `docs/evidence/W3b_protokol_walidacji.md` | `parcel_anomalies`, `water_index`, `area_series`, `management_flags`, `jackknife_ci`, `t1_rows`, `t2_rows`, `t3_main`, `multiband_rows`, `before_rows`, `run_tests`, `tests_summary`, `protocol_sha`, `freeze_info`, `t1_by_soil` (analiza dodatkowa) |
| `stations.py` | Czujnik ISMN Condom: odczyt, QC, reguły A4 | `read_ismn_stm`, `qc_insitu`, `insitu_daily`, `fast_drop_days`, `a4_variants`, `a4_flag_report` |
| `reference.py` | Stacje ICOS (Auradé, Lusignan) i wspólna walidacja warstwy wody (protokół W2 + REF) | `ingest_icos_site`, `icos_daily`, `validate_layer`, `validate_icos_site`, `monitor_current` |
| `weather.py` | Météo-France: walidacja ERA5-Land (Tmin, Tmax, opad, SPI), progi przymrozku i upału, zdarzenia | `download_mf`, `read_mf`, `select_stations`, `validate_weather`, `calibrated_thresholds`, `weather_hazards`, `hazard_summary` |
| `card.py` | Zdania karty winnicy (EN; PL zachowane w kodzie), kategorie suszy wg progów USDM, klasy SWI | `parcel_card`, `parcel_card_lines`, `parcel_class`, `water_category`, `read_swi`, `swi_agreement` |
| `panel.py` | Produkt: panel EN (Leaflet na zdjęciu Esri, mapy pikseli 10 m, strefy dnia, warstwy z, statystyki, gleba, pogoda, karta, sezon, „How far to trust it”) i jego dane JSON | `pixel_maps`, `weather_data`, `panel_data`, `trust_rows`, `panel_html`, `build_panel` |
| `pipeline.py` | Zadania v1 w kolejności uruchamiania | `task_*`, `TASKS`, `run_all` |
| `local.py`, `__main__.py` | Uruchamianie na własnym komputerze: ustawienia (`local_settings.json`), przebieg tygodniowy (pull → zadania → publikacja panelu na GitHub), blokada, log; polecenia `python -m agriscreen run / weekly / publish / selftest / settings` (`docs/URUCHOMIENIE_LOKALNE.md`) | `load_settings`, `run`, `publish`, `weekly`, `git_pull`, `git_publish`, `Lock` |
| `experiments/` | W3c (`zones.py`) i W3d (`months.py`): anomalie miejsc wewnątrz winnicy; testy według protokołów; panel pokazuje tylko wynik testu | `task_zones`, `task_months`, `trust_rows`, `run_zones`, `run_months` |
| `selftest.py` | Test bez sieci: dane syntetyczne, wszystkie zadania, kontrola plików, testy jednostkowe modułów | `make_inputs`, `run_tasks`, `check_*`, `unit_tests`, `main` |
| `assets/` | Arkusz stylów Leaflet 1.9.4 wbudowywany w panel (BSD-2) | |

Zależności: `pipeline` → wszystkie moduły; `panel` → `card`, `parcel`, `metrics`, `experiments.trust_rows`;
`parcel` → `metrics`, `stations`; `reference` → `stations`, `metrics`; `weather` → `metrics`;
`experiments` → `parcel`, `metrics`. `ingest` importuje Earth Engine tylko, gdy jest zainstalowany (potrzebny
wyłącznie do `task_ingest_s2`).

## 3. Zadania (`pipeline.py`)

| Zadanie | Wejście | Wyjście |
|---|---|---|
| `task_ingest_s2` | AOI + bufor 320 m, sezon IV–X, ≤ 40% chmur nad AOI | `data/01_Raw_Sentinel2/S2_L2A_*.tif` (10 pasm [0–1] + maska chmur + SCL), manifest |
| `task_ingest_era5` | środek VINEYARD_06, 1991 → dziś | `data/02_ERA5_Land/era5_land_daily.csv` |
| `task_ingest_swi` | klucze z `SECRETS_DIR` | `SWI_DIR/swi_v4_0.1deg_point.csv` (od 2007), `swi_v2_1km_point.csv` (od VII 2025) |
| `task_parcel_stats` | sceny S2 (przyrostowo, para działka–scena) | `gwl_observations` (produkt `S2_10m_buf20`), `parcel_qc.csv` |
| `task_soil` | ERA5-Land | `era5_daily_anomalies.csv` (percentyl i z 0–7 i 0–100 cm, SPI-1, SPI-3) |
| `task_parcel_tests` | obserwacje ≤ zamrożenie, ERA5, SWI, czujnik ISMN | `w3b_tests.csv`, `w3b_freeze.json`, `gwl_validation_metrics`; pomijane przy tym samym protokole, zamrożeniu i commicie |
| `task_parcel_anomalies` | obserwacje działek | `parcel_anomalies.csv`, `parcel_area.csv`, `parcel_flags.csv` |
| `task_reference` | ISMN Condom, ICOS, ERA5 i SWI w punktach stacji | `validation_reference.csv`, `validation_reference_qc.csv`, `a4_flags.csv`, `reference_current.json` |
| `task_weather` | Météo-France, ERA5 w punktach stacji | `validation_weather.csv`, `mf_stations.csv`, `weather_hazards.csv`, `hazard_summary.csv`, `hazard_thresholds.json` |
| `experiments.task_zones` / `task_months` | sceny S2, ERA5, RPG | `w3c_*`, `w3d_*` (magazyny `.npz`, testy, podsumowania, zamrożenie) |
| `task_panel` | pliki wynikowe, sceny S2, prognoza Open-Meteo | `panel.html`, `panel_data.json` |
| `task_summary` | pliki wynikowe, `gwl_runs` | `run_summary.md`, `run_summary.json` |

## 4. Rejestr (`data/registry/`, na Dysku)

| Tabela | Klucz | Zawartość |
|---|---|---|
| `gwl_observations` | site_id, product, variable, time_utc, orbit | statystyki działek ze scen (`S2_10m_buf20`) |
| `gwl_validation_metrics` | site_id, product, reference, segment, period, subset, metric | wyniki walidacji i testów |
| `gwl_runs` | run_id | historia zadań |

Zapis według klucza (`registry_upsert`): ten sam wiersz z tą samą wartością nie jest dopisywany ponownie.

## 5. Testy

- `python -m agriscreen.selftest [--out KATALOG]` (kilka minut, bez sieci i kluczy): dane syntetyczne (ERA5 1991–2024,
  stacja Météo-France, atrapy Copernicus Data Space i portalu ICOS, 126 scen Sentinel-2 na prawdziwych granicach
  15 winnic, sygnał wstrzyknięty w winnicę 7 w 2024 r.), wszystkie zadania, eksperymenty, kontrola plików i
  testy jednostkowe modułów (`_selftest` w `ingest`, `reference`, `weather`, `card`, `parcel`, `zones`, `months`).
- Prawdziwe dane w teście: granice winnic i czujnik ISMN Condom z repozytorium.
- Lint: `ruff check agriscreen` (reguły w `pyproject.toml`).

## 6. Stare nazwy modułów (protokoły i notatki sprzed 1.0)

Zarejestrowane protokoły i notatki wyników odwołują się do modułów `step_*`. Odpowiedniki w 1.0:

| Do wersji 1.0 | Wersja 1.0 |
|---|---|
| `step_01_ingest.py` | `agriscreen/ingest.py` |
| `step_04_metrics_alert.py` | `agriscreen/metrics.py` |
| `step_05_colab_run.py` | `agriscreen/runtime.py`, `config.py`, `pipeline.py`, `selftest.py` |
| `step_07_station_pipeline.py` | `agriscreen/stations.py` (bez gałęzi Sentinel-1) |
| `step_08_weather.py` | `agriscreen/weather.py` |
| `step_09_panels.py` | `agriscreen/card.py` (bez karty wody PL, paneli v1.2 i biuletynu) |
| `step_10_reference.py` | `agriscreen/reference.py` |
| `step_11_parcel.py` | `agriscreen/parcel.py` |
| `step_12_panel.py` | `agriscreen/panel.py` |
| `step_13_zones.py`, `step_14_months.py` | `agriscreen/experiments/zones.py`, `months.py` |
| `step_03_super_resolve.py`, `step_06_dashboard.py` | wycofane (SEN2SR, dashboard PL) |

Funkcje przeniesiono bez zmian logiki; regresja na danych syntetycznych daje identyczne pliki wynikowe
(`CHANGELOG.md`). Ostatni commit z modułami `step_*`: `82844ae`.

## 7. Zasady

- Dane satelitarne tylko z programu Copernicus (D-048). Kafle Esri tylko jako tło w przeglądarce (bez zapisu).
- Klucze tylko z `MyDrive/GeoWorldLook/secrets/`; kod nie wypisuje ich wartości.
- Metody z protokołów zarejestrowanych przed liczeniem (SHA-256 treści od „## 0.” do końca, `parcel.protocol_sha`);
  testy na danych do daty zamrożenia; zmiana metody = nowa wersja protokołu i nowe dane.
- Notatniki generujemy skryptami (`notebooks/build_monitor.py`, `notebooks/build_story.py`), nie edytujemy ręcznie.
