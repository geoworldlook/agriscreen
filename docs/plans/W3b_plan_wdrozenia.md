# W3b — plan wdrożenia K1–K4 („Moja winnica”)

> **Status:** WDROŻONY W KODZIE 2026-10-19 (K1–K4; selftest offline przechodzi). Do zrobienia: przebieg w Colab
> i notatka wyników (K3b). Rozwija Plan W3b (`docs/plans/Plan_W3b_moja_winnica.md`, decyzje D-084–D-089). Definicje,
> liczby i kryteria są w protokole `docs/evidence/W3b_protokol_walidacji.md` (REGISTERED, SHA-256 `f01b74a804b28315…`),
> dalej **P§n**.

## Stan wdrożenia (2026-10-19)

- **Zrobione:** K1 (rejestracja protokołu) i cały kod K2–K4 naraz, zamiast w 4 sesjach. Selftest
  `python step_05_colab_run.py --selftest` przechodzi razem z nowymi testami W3b.
- **Uproszczenia względem opisu niżej** (metoda bez zmian):
  - `_veg_anomalies` zostaje nietknięta; anomalie działek liczy osobna funkcja `step_11.parcel_anomalies` (ta sama
    `scene_anomaly`), więc status i stare pliki nie mogą się zmienić;
  - zamiast bootstrapu po latach jest `jackknife_ci` (P§0, U8), bez losowania;
  - szczegół karty (NDMI, −CRSWIR, NDVI, NDRE) to jedna linia „niezwalidowane”, bez przeróbki `condition_panel`;
  - `W3B_FREEZE` ustala się samo przy pierwszym liczeniu testów (`w3b_freeze.json`, P§0, U6);
  - `parcel_tests` jest też w `run_monitoring`: liczy raz na commit kodu (nowy commit, np. poprawka błędu wg P§11,
    liczy od nowa na tych samych zamrożonych scenach), poza tym zwraca „skipped”; commit jest zapisany w `w3b_tests.csv`.
- **Następny krok (Ty, Colab):** otwórz notatnik z GitHub, „Uruchom wszystko”, prześlij komunikat `parcel_tests`,
  `w3b_tests.csv`, `parcel_qc.csv` i `run_summary.md`. Na ich podstawie powstaje `docs/evidence/W3b_wyniki.md` (K3b).

## Wynik w skrócie

- **Co powstanie:**
  - karta „Moja winnica” z 3 zdaniami (P§10) w dashboardzie, biuletynie (EN i JSON) i `run_summary.md`;
  - nagłówek gleby w 3 klasach;
  - notatka `docs/evidence/W3b_wyniki.md`: T1–T3, wariant wielopasmowy, przeliczone wartości „przed”.
- **Dane:** nowy produkt `S2_10m_buf20` dla 15 winnic, liczony z 414 scen już na Dysku. Bez pobierania i bez GPU.
  Nowe sceny przechodzą przez to samo zadanie.
- **Kod:**
  - nowy moduł `step_11_parcel.py` (funkcje czyste i `_selftest`);
  - 3 nowe zadania w `step_05`: `parcel_stats`, `parcel_anomalies`, `parcel_tests`;
  - w `step_04` tylko nowe argumenty z wartościami domyślnymi i jedna nowa kolumna;
  - karta w `step_09` i `step_06`.
- **Bez zmian:** status EDO, `_veg_anomalies`, `veg_anomalies.csv`, produkty `S2_10m` i `S2SR_2.5m`.
- **Sesje:** 5 i 1 zapasowa: K1 → K2 → K3a → K3b → K4. Colab uruchamiasz 3 razy: po K2, po K3a i po K4.
- **Spodziewany wynik:** T3 najpewniej „nierozstrzygnięty” (P§12: przy prawdziwym ρ = 0,3 kryterium przechodzi w ok.
  1 na 4 przypadki). Zdania 1 i 2 działają niezależnie od tego.

## Zasady

- **Status bez zmian.** Nie ruszamy `build_status`, `_veg_anomalies`, `VEG_INDEX`, `VEG_PRODUCT`, kluczy `VEG_*`
  i `THR_*`, `VINEYARDS` (tylko VINEYARD_06), `MAIN_SITE`, `CRSWIR_W` ani domyślnego działania `site_stats`. Wszystko
  nowe ma własną etykietę produktu i własne pliki. Po każdej sesji `gwl_status` jest identyczny jak przed nią.
- **Jedna konfiguracja.** Tylko `MONITOR_CONFIG` przez `monitor_config(rt)`. W F4 wyciek wziął się z ówczesnej normy
  „pozostałe lata” w `scene_anomaly`. Dziś skrypty F4 z własnym `VEG_CFG` dostałyby jeszcze inną normę niż potok, stąd
  zasada: żadnych ręcznie składanych słowników.
- **Pre-rejestracja.** K2 rusza dopiero po zapisaniu SHA-256 protokołu. Po wyniku definicji nie zmieniamy; poprawka błędu
  implementacji jest dozwolona, z commitem i opisem w notatce (P§11).
- **Notatnik tylko z generatora.** Zmieniamy `CELLS` w `build_colab_master.py` i uruchamiamy
  `python build_colab_master.py` bez argumentów. `notebooks/AgriWatch_Monitor.ipynb` nigdy nie edytujemy ręcznie.
- **Przed każdym pushem:** `python step_05_colab_run.py --selftest --out data/_selftest_monitor` (w nim
  `s11._selftest()` i `s9._selftest_parcel()`) oraz `python -m pyflakes step_*.py`.
- **Przed każdym Colab:**
  1. kod jest na `main` (sekcja 1 notatnika robi `pull --ff-only` i ostrzega, gdy HEAD ≠ origin/main);
  2. po regeneracji otwierasz notatnik z GitHub (Plik → Otwórz notatnik → GitHub). Nie zapisujesz do GitHub kopii
     otwartej przed regeneracją, bo cofnęłaby nowe sekcje.

## K1 — protokół

**Cel:** zatwierdzić definicje i zamrozić je skrótem SHA-256, zanim powstanie jakakolwiek liczba z Sentinel-2.

**Wejście:** szkic protokołu, Plan W3b §1–§4, wybory U1–U8 (P§13).

**Zmiany w kodzie:** brak (skrypt `docs/evidence/W3b_symulacje.py` już jest).

**Wyniki:**
- protokół ze statusem `REGISTERED`, §13 zamienione na „Rozstrzygnięcia”;
- skrót: `sed -n '/^## 0\./,$p' docs/evidence/W3b_protokol_walidacji.md | sha256sum`;
- Plan W3b §6: D-084–D-088 zatwierdzone, **D-089: protokół W3b zarejestrowany (SHA-256 …)**;
- wpis w `STAN_I_PLAN.md` §2.

**Kryterium odbioru:**
- ☐ U1–U8 rozstrzygnięte, oznaczenia „(U…)” usunięte
- ☐ skrót w nagłówku protokołu i w Planie W3b
- ☐ commit protokołu wcześniejszy niż pierwszy commit kodu K2

**Sesje:** 1, bez Colab.

## K2 — statystyki 15 winnic z archiwum

**Cel:** dla każdej pary (winnica, scena) zapisać średnie wskaźników i pasm B04, B06, B8A, B12 oraz `n_pixels`
i `clear_frac`, z pasem 20 m (P§1); dla 414 scen i dla każdej nowej.

**Wejście:** rastry `S2_DIR` (IV–X 2016–2026, 10 pasm, maska chmur), `data/1_AOI_GBOV_CONDOM.geojson`,
rejestr `gwl_observations`.

**Zmiany w kodzie:**

| Plik | Funkcja | Zmiana | Co robi |
|---|---|---|---|
| `step_04_metrics_alert.py` | `CRSWIR_W_FORDEAD` | nowa stała | `(1610.4 - 864.0) / (2185.7 - 864.0)` = 0,5647, tylko dla nowego produktu (P§3) |
| | `compute_indices(arr, crswir_w=CRSWIR_W)` | nowy argument | domyślnie bez zmian |
| | `site_stats(..., inner_m=None, bands=(), crswir_w=CRSWIR_W, all_touched_fallback=True)` | nowe argumenty | Pas `buffer(-(inner_m or res))`; `rec[b.lower()]` = średnia pasma z czystych pikseli; przy `False` bez awaryjnego `all_touched`, a przy 0 pikseli rekord z `n_pixels=0` i NaN. Domyślne wywołanie daje to samo co dziś |
| | `load_parcels(cfg, crs)` | nowa | działki `Typ == PARCEL_TYPE`, `site_id = VINEYARD_{fid:02d}` (VINEYARD_06 zachowuje id) |
| `step_05_colab_run.py` | `task_parcel_stats(rt, cfg)` | nowa | opis niżej |
| | `run_monitoring` | +1 wiersz | `parcel_stats` zaraz po `scene_stats` |
| `build_colab_master.py` | `CELLS` | po sekcji 4 | „## 4b. Moja winnica: statystyki 15 winnic (W3b K2)” z `run_task(rt, 'parcel_stats', task_parcel_stats, rt, cfg)` |

**Jak działa `task_parcel_stats`:**
- idzie po scenach `S2_DIR`; „zrobione” = para (`site_id`, `time_utc`) produktu `PARCEL_PRODUCT`, więc nowa działka
  dostaje całą historię;
- `s1.read_geotiff_to_numpy` → `s4.site_stats(..., inner_m=20, bands=PARCEL_BANDS, crswir_w=CRSWIR_W_FORDEAD,
  all_touched_fallback=False)` → `_stats_to_obs` → `registry_upsert` co 25 scen (własny licznik, nie licznik
  `task_scene_stats`);
- zapisuje raport `parcel_qc.csv` i w komunikacie podaje datę ostatniej sceny (to będzie `W3B_FREEZE`, P§0);
- nie pisze do `gwl_sites` ani do statusu; zwraca `skipped`, gdy nie było nic nowego.

**Nowe klucze konfiguracji** (w `MONITOR_CONFIG`, po `REF_SITES`):

| Klucz | Wartość | Źródło |
|---|---|---|
| `PARCEL_PRODUCT` | `"S2_10m_buf20"` | nowa etykieta; status jej nie widzi |
| `PARCEL_TYPE` | `"winnice"` | 15 winnic z geojson, bez listy w kodzie |
| `PARCEL_INNER_M` | `20` | P§1 |
| `PARCEL_BANDS` | `("B04", "B06", "B8A", "B12")` | P§7 (Laroche-Pinel 2021, s. 13) |
| `PARCEL_MIN_PX` | `40` | P§1 |

**Wyniki:**
- `gwl_observations`: produkt `S2_10m_buf20`, zmienne `ndvi, ndmi, ndre, crswir, b04, b06, b8a, b12, clear_frac`,
  `n_pixels` = komórki 10 m w zwężonym obrysie; ok. 56 tys. wierszy (szacunek);
- `OUTPUT_DIR/parcel_qc.csv` (tylko raport): `site_id, fid, area_ha, n_pixels, qc_ok, n_scenes, n_clear`.

**Testy (selftest):**
- drugie uruchomienie `parcel_stats` zwraca `skipped`; produkt ma 15 `site_id`;
- `qc_ok` fałszywe dokładnie dla VINEYARD_16 i VINEYARD_18; `n_pixels` VINEYARD_06 w [134; 142];
- **regresja:** `n_pixels` i `px_method` wszystkich obiektów `S2_10m` i `S2SR_2.5m` równe wzorcowi zapisanemu przed
  zmianą (np. VINEYARD_06, `S2_10m`: 213, `"centre"`). Same średnie tego nie wykryją, bo rastry syntetyczne są
  jednorodne;
- dotychczasowe asercje (SR, status VINEYARD_06 z `S2SR_2.5m`, 126 scen) przechodzą bez zmian.

**Kryterium odbioru:**
- ☐ selftest i pyflakes OK; kod na `main`
- ☐ Colab, sekcje 1, 2, 4b: liczba scen = liczba plików w `S2_DIR`; drugie uruchomienie `skipped`
- ☐ `parcel_qc.csv`: 13 z 15 `qc_ok` (fid 16 i 18 poniżej progu); inaczej zgłaszamy, reguła P§1 obowiązuje
- ☐ liczba wierszy `S2_10m` i `S2SR_2.5m` oraz `gwl_status` bez zmian
- ☐ zapisana data ostatniej sceny i lista plików (SHA-256) → `W3B_FREEZE`

**Ryzyka:** odczyt 414 GeoTIFF z Dysku zajmie ok. 5–15 min (szacunek) — zapis co 25 scen, więc przerwana sesja
wznawia się sama. Rejestr urośnie ok. 3–4 razy; `registry_read` zwolni o sekundy.

**Sesje:** 1.

## K3 — anomalie, testy, wariant wielopasmowy, wartości „przed”

**Cel:** policzyć anomalie działek i wszystkie wiersze P§4–P§9, potem napisać notatkę wyników.

**Wejście:** wiersze z K2; `era5_land_daily.csv`; ISMN Condom 20 i 30 cm (`s7.a4_variants`); SWI v4 T15
(`s9.read_swi`); `veg_anomalies.csv` (krok b drabinki P§9); pliki F4 (`a2_variant_series.csv`); zarejestrowany protokół.

**Zmiany w kodzie:**

| Plik | Funkcja | Co robi |
|---|---|---|
| `step_04` | `scene_anomaly` | **addytywnie** kolumna `n_ref_years` (liczba różnych lat w puli). z, `n_ref`, `ref_mode` bez zmian |
| `step_11_parcel.py` | moduł | funkcje czyste na DataFrame, bez I/O (wzór: `step_10_reference.py`) |
| | `one_scene_per_day(wide)` | dla każdej pary (działka, dzień) zostaje scena z największym `clear_frac`; zwraca też liczbę usuniętych (P§1) |
| | `parcel_anomalies(wide, cfg, indices)` | `one_scene_per_day`, potem `s4.scene_anomaly` dla każdej działki i wskaźnika; `qc_ok` z `n_pixels ≥ PARCEL_MIN_PX`. Ta sama funkcja dla karty i testów |
| | `water_index(pa)` | wiersze `index="water"`: z = (z_ndmi − z_crswir)/2, gdy są oba; `value` = NaN, `track` wspólny, `n_ref` i `n_ref_years` = minimum, `ref_mode` wspólny albo `"mixed"` |
| | `area_median(pa, sites, index="water", min_parcels=6)` | dla każdego dnia sceny: `z_med`, `n_parcels` (P§6) |
| | `management_flags(pa, cfg)` | `site_id, year, n, share_low, share_high, flag` (P§8) |
| | `soil_pct(era5, cfg)` | percentyl 0–100 cm: `s4.clim_anomaly(s4.rootzone(e), CLIM_REF, hw)["percentile"]`, tak samo jak karta wody |
| | `ismn_target(overrides, cfg, var="W1")` | y(t) i udział dni cenzurowanych (P§6 pkt 1–3); okres ISMN na stałe 2016-01-01–2024-12-31 |
| | `jackknife_ci(df, stat, year_col="year")` | wartość, przedział jackknife po latach i wartości bez każdego roku (P§0) |
| | `t1_calibration`, `t2_noise`, `t3_soil` | P§4, P§5, P§6; ρ z `s10._spearman` |
| | `multiband_loyo(X, y, years)` | P§7: OLS bez kolejnych lat; zwraca s⁽⁻ᵍ⁾ bez β0, podzielone przez SD z lat uczących, i wagi z każdego foldu |
| | `compare_delta_rho(s, x, y, years)` | Δρ na wspólnych dniach, przedział jackknife (P§7) |
| | `before_values(...)` | drabinka a–d dla P4 i P1–P3, P5 w konfiguracji d (P§9); R i przedział jak F4 (`s7._r_with_ci`) |
| | `_selftest()` | patrz „Testy” |
| `step_05` | `task_parcel_anomalies(rt, cfg)` | przy każdym uruchomieniu, opis niżej |
| | `task_parcel_tests(rt, cfg, force=False)` | tylko na żądanie (sekcja 5c), opis niżej |
| | `run_monitoring` | `parcel_anomalies` po `anomalies`; `parcel_tests` nie |
| `build_colab_master.py` | `CELLS` | w sekcji 5 `parcel_anomalies` po `anomalies`; nowa sekcja „## 5c. Moja winnica: testy (W3b K3) — prześlij wynik” |

**Jak działa `task_parcel_anomalies`** (karta bieżąca):
- czyta obserwacje `PARCEL_PRODUCT` z rejestru → `s11.parcel_anomalies` → `water_index` → `area_median` →
  `management_flags`;
- zapisuje `parcel_anomalies.csv`, `parcel_area.csv`, `parcel_flags.csv`; nie pisze do statusu ani `gwl_anomalies`.

**Jak działa `task_parcel_tests`** (zamrożone testy):
- liczy anomalie od nowa z obserwacji z datą ≤ `W3B_FREEZE` (nie czyta `parcel_anomalies.csv`), więc nowsze sceny nie
  zmienią toru ani puli normy;
- T1, T2, T3, P§7, wartości „przed” i QC;
- zapisuje `w3b_tests.csv` (z SHA-256 protokołu i commitem kodu) i wiersze `gwl_validation_metrics`;
- przy ponownym uruchomieniu z tym samym SHA i commitem zwraca `skipped`, chyba że `force=True`. Karta czyta tylko
  `w3b_tests.csv`.

**Funkcje użyte bez zmian:** `s4.clim_anomaly`, `s4.rootzone`, `s7.a4_variants`, `s7._r_with_ci`, `s10._spearman`,
`s9._swi_class`, `s9.read_swi`, `registry_read`.

**Nowe klucze konfiguracji:**

| Klucz | Wartość | Źródło |
|---|---|---|
| `PARCEL_ANOM_INDICES` | `("ndmi", "crswir", "ndvi", "ndre", "b04", "b06", "b8a", "b12")` | składniki, szczegół karty, pasma P§7 |
| `PARCEL_TEST_MONTHS` | `(6, 9)` | P§1 |
| `PARCEL_MIN_AREA` | `6` | minimum winnic w dniu (P§6, P§8) |
| `PARCEL_T3_EXCLUDE` | `("VINEYARD_06",)` | P§1 |
| `PARCEL_T3_DAYS`, `PARCEL_T3_MIN_DAYS`, `PARCEL_T3_CLIP` | `30`, `20`, `3.0` | P§6 |
| `PARCEL_RAIN_MM` | `5.0` | P§5 |
| `PARCEL_FLAG_MIN_SCENES`, `PARCEL_FLAG_SHARE` | `6`, `2/3` | P§8 |
| `W3B_FREEZE` | data ostatniej sceny z K2 | P§0 (U6) |
| `RANDOM_SEED`, `BOOTSTRAP_BLOCK_DAYS`, `MIN_N_METRICS` | `42`, `30`, `10` | te same co w `step_07`; potrzebne `s7._r_with_ci` (P§9). Dziś `MONITOR_CONFIG` ma tylko `BOOTSTRAP_N` |

**Wyniki** (w `OUTPUT_DIR`):
- `parcel_anomalies.csv` (kolumny jak `veg_anomalies.csv` oraz `n_ref_years`, `n_pixels`, `qc_ok`), `parcel_area.csv`,
  `parcel_flags.csv`;
- `w3b_tests.csv`: schemat `gwl_validation_metrics` oraz `criterion`, `verdict`; do rejestru tylko kolumny schematu;
- K3b: `docs/evidence/W3b_wyniki.md`, wiersze w `docs/evidence/karta_wynikow.md`.

**Testy (`s11._selftest`):**
- **T1:** dla z ~ N(0,1) przedział zawiera 15,9%.
- **T2:** bez par n = 0 i NaN, bez błędu; przy wstrzykniętym szumie σ MDC95 ≈ 1,96·√2·σ (±10%).
- **T3:** sygnał (ρ ≈ 0,6) daje dolną granicę > 0; czysty szum nie spełnia kryterium (stałe ziarno).
- **`jackknife_ci`:** zgodność z ręcznie policzonym przykładem; przy < 3 latach NaN.
- **`ismn_target`:** przy normie podanej z zewnątrz zmiana wartości w dniu t nie zmienia y(t); dla pełnej funkcji
  |Δy(t)| < 0,01.
- **`multiband_loyo`:** cel zbudowany z pasm → przyjęty; zmiana celu w roku Y nie zmienia predykcji dla Y; cechy bez
  związku z celem przy silnym efekcie roku → średni ρ_multi z 200 powtórzeń w [−0,05; 0,05].
- **`water_index`:** `allclose` z (z_ndmi − z_crswir)/2; brak składnika → brak wiersza.
- **`one_scene_per_day`:** z 2 scen dnia zostaje ta z większym `clear_frac`.

**Testy integracyjne (`step_05._selftest`):**
- `parcel_anomalies.csv` ma 15 działek i indeks `water`; `veg_anomalies.csv` i `validation_anomalies.csv` bez zmian;
- sygnał między działkami: B11 **+0,10** wewnątrz fid 7 tylko w 2024 → mediana d < −1, flaga „−” dla VINEYARD_07,
  VINEYARD_06 bez flagi;
- `w3b_tests.csv` ma wiersze 2 kryteriów; G5 i G13 dają „za mało par” (sceny syntetyczne co 15–16 dni), bez błędu;
- drugie uruchomienie `parcel_tests` zwraca `skipped`.

**Kryterium odbioru K3a:**
- ☐ selftest OK; kod na `main`
- ☐ Colab: sekcje 4b, 5 i 5c bez błędu; `w3b_tests.csv` ma wszystkie wiersze P§4–P§9
- ☐ SHA-256 protokołu w `w3b_tests.csv` taki sam jak przy rejestracji; `gwl_status` bez zmian

**Kryterium odbioru K3b:**
- ☐ `W3b_wyniki.md` według „Co raportujemy”, wynik negatywny pierwszy
- ☐ wiersze w karcie wyników; wariant zdania 3 (prosty albo wielopasmowy) według P§7

**Ryzyka:**

| Ryzyko | Co robimy |
|---|---|
| T3 nierozstrzygnięty (najbardziej prawdopodobne, P§12) | zdanie 3 ukryte; wynik w notatce i na karcie wyników. Zdania 1–2 działają dalej |
| T1 pokazuje rozkalibrowanie | dopisek na karcie (P§4); metoda bez zmian w tej wersji |
| Za mało par w G5 lub G13 | „za mało par”; dla tej grupy karta nie ocenia zmiany |
| Błąd kodu wykryty po wyniku | poprawka, commit i opis w notatce; definicje bez zmian (P§11) |

**Sesje:** 2. K3a: kod i Colab. K3b: notatka i karta wyników.

## K4 — karta „Moja winnica”

**Cel:** karta według P§10 i nagłówek gleby w 3 klasach.

**Wejście:** `parcel_anomalies.csv`, `parcel_area.csv`, `parcel_flags.csv`, `w3b_tests.csv`, karta wody.

**Zmiany w kodzie:**

| Plik | Funkcja | Co robi |
|---|---|---|
| `step_09_panels.py` | `water_card` | nowe pole `soil_class = _swi_class(pct, cfg)` (≤ 30 / ≥ 70); `category` (USDM) zostaje jako szczegół |
| | `water_card_lines` | nagłówek zaczyna się od klasy: „Sucho w glebie okolicy — {etykieta} ({kod} wg US Drought Monitor)…”, „Wilgotność gleby w normie…”, „Wilgotno — …”; EN analogicznie. „Raz na N lat” i percentyl zostają |
| | `INDEX_PL`, `PRODUCT_PL` | `crswir` (znak −1), `water`, `S2_10m_buf20`; `ndmi` z etykietą „woda w roślinności (SWIR)” (D-087) |
| | `condition_panel` | z i mini-wykres mnożone przez znak wskaźnika; zapasowe 10 m tylko przy `prod == "S2SR_2.5m"` |
| | `parcel_card(pa, area, flags, tests, cfg, site_id, today=None)` | klasa i wiek sceny, „k z N winnic”, flaga, zmiana od poprzedniej sceny (P§10), pasek sezonu, kafelki, zdanie 3 i „Na ile ufać” z `tests`. Tylko typy Pythona (JSON) |
| | `parcel_card_lines(card, lang="pl", soil=None)` | 3 zdania, 2 stałe uwagi (Plan W3b §1) i dopiski P§10 |
| | `_selftest_parcel(cfg)` | patrz „Testy” |
| `step_06_dashboard.py` | `_spark_svg(..., thr_hi=None)` | linia +1 dla paska sezonu |
| | `_condition_html(..., footer=None)` | własna stopka karty: „niezwalidowane” zamiast zdania o czujniku |
| | `_parcel_html(card, lines, cfg)` | h3 „Moja winnica”, lista 3 zdań, pasek sezonu, kafelki |
| | `build_dashboard`, `_render` | karta przed „Woda w glebie”; wiersz „Nawadnianie: nie” → „nieznane” (Plan W3b §3 pkt 6) |
| `step_05` | `task_bulletin`, `task_summary` | `payload["parcel_card"]`, sekcja EN „My vineyard (parcel vs its own history)”; w raporcie sekcje „Moja winnica (W3b)” i tabela z `w3b_tests.csv` |
| `build_colab_master.py` | `CELLS` | `bulletin` przeniesiony z sekcji 5 do 6, przed dashboard, żeby widział wyniki 5c |
| `step_11_parcel.py` | `multiband_area(area_bands, weights, mean, sd)` | **tylko gdy P§7 przyjęty:** z_mb okolicy z zamrożonych wag (U7, wariant A); karta bierze go do zdania 3 |

**Kafelki karty:** `condition_panel(pa, None, dict(cfg, CONDITION_PRODUCT=PARCEL_PRODUCT,
CONDITION_INDICES=("ndmi", "crswir", "ndvi", "ndre"), VEG_INDEX=None), site_id, status_row=None)`. Bez `VEG_INDEX`
kafelek NDVI nie dostaje odznaki statusu, a bez walidacji pokazuje „niezwalidowane”.

**Testy:**
- **`s9._selftest_parcel`:**
  - granice klas: −1 → „poniżej”, −0,99 → „w normie”, +1 → „powyżej”;
  - < 40 pikseli → „działka za mała…”; flaga → „porównanie z historią mniej pewne”;
  - „wyraźna zmiana” i „między scenami padało” na ręcznie zbudowanej tabeli `tests` z MDC95;
  - zdanie 3 wtedy i tylko wtedy, gdy spełnione kryterium;
  - w PL i EN brak „stres wodny”, „wczesne ostrzeżenie”, „water stress”, „early warning”;
  - `json.dumps` karty działa; klasa kafelka CRSWIR uwzględnia znak.
- **`s9._selftest_water`:** asercje nagłówka „Wyjątkowa susza w glebie” i „Exceptional drought” zastępujemy nowymi
  („Sucho w glebie”, „Dry soil”, „D4”, „wyjątkowa susza”); asercje „raz na N lat” i „(percentyl … wobec 1991–2020)”
  zostają. W pętli p ∈ [0, 100]: `code.startswith("D")` ⇔ `"dry"`, `code == "W"` ⇔ `"wet"`.
- **Integracja:** „Moja winnica” przed „Woda w glebie”; `bulletin.md` zawiera „My vineyard”; JSON ma `parcel_card`
  i `soil_class`; `run_summary.md` ma obie nowe sekcje; bez step_09 kart „Element niedostępny” jest 5 zamiast 4.

**Kryterium odbioru:**
- ☐ selftest OK; notatnik wygenerowany, nie edytowany ręcznie; kod na `main`
- ☐ Colab „Uruchom wszystko” (notatnik otwarty z GitHub): karta widoczna, zdanie 3 zgodne z `w3b_tests.csv`
- ☐ każda liczba na karcie ma wynik testu albo napis „niezwalidowane”
- ☐ `docs/ARCHITEKTURA.md` (§2–3), `STAN_I_PLAN.md` i Plan W3b §5 zaktualizowane

**Ryzyka:**

| Ryzyko | Co robimy |
|---|---|
| Regeneracja notatnika czyści zapisane wyniki komórek | wyniki są na Dysku; komórek nie przenosimy ręcznie |
| „Kondycja winnicy” (SR 2,5 m) pokazuje drugą wartość NDMI tej samej działki | podpis produktu na obu kafelkach; o usunięciu decydujemy po K4 |

**Sesje:** 1.

## Kolejność pracy w sesjach

| Sesja | Zadania | Co uruchamiasz w Colab | Co odsyłasz |
|---|---|---|---|
| 1 — K1 | rozstrzygnięcie U1–U8, rejestracja protokołu, D-084–D-089 | nic | „zatwierdzam” albo zmiany U1–U8 |
| 2 — K2 | `step_04` (argumenty, `load_parcels`), `task_parcel_stats`, klucze, sekcja 4b, selftest, push | sekcje 1, 2 i 4b (CPU, ok. 5–15 min) | komunikat `parcel_stats` i `parcel_qc.csv` |
| 3 — K3a | `step_11_parcel.py`, 2 zadania, sekcje 5 i 5c, selftest, push | sekcje 1, 2, 4b, 5 i 5c | komunikat 5c i `w3b_tests.csv` |
| 4 — K3b | notatka `W3b_wyniki.md`, karta wyników, wariant zdania 3 według P§7 | nic (5c ponownie tylko po poprawce błędu, z `force=True`) | akceptacja notatki |
| 5 — K4 | karta, nagłówek gleby, biuletyn, raport, notatnik, selftest, push | „Uruchom wszystko” | zrzut karty, `bulletin.md`, `run_summary.md` |
| 6 — zapas | poprawki; ARCHITEKTURA, STAN, Plan W3b §5 | w razie potrzeby | — |

## Co raportujemy

**Notatka `docs/evidence/W3b_wyniki.md`** (wzór: `W2_REF_wyniki.md`):
1. Nagłówek: SHA-256 protokołu, commit kodu, `W3B_FREEZE`, SHA-256 listy scen, liczba scen i działek.
2. „Wynik w skrócie”: 2 kryteria (T3, P§7) z wartością i przedziałem, potem T1 i T2; wynik negatywny pierwszy.
3. Tabele: kryteria; T1; T2 (MDC95 G5 i G13 w z i w jednostkach wskaźnika); wiersze opisowe P§6; drabinka „przed”.
4. QC według P§11 pkt 5.
5. Zmiany na karcie i ograniczenia.

**Karta wyników** (`docs/evidence/karta_wynikow.md`), nowa sekcja „Roślinność działki (W3b)”:

| Zmiana | Referencja i okres | Przed | Po | Wniosek |
|---|---|---|---|---|
| Norma, czujnik i produkt (drabinka P§9) | ISMN, IV–X 2018–2024, VINEYARD_06 | NDMI R 0,47 (F4, 30 dni) | a / b / c / d | a→b: wpływ normy (wyciek); b→c: czujnik; c→d: produkt |
| Prosty wskaźnik wody (T3) | ISMN A4 W1, VI–IX 2018–2024, mediana 12 winnic | — | ρ [przedział] | zdanie 3: tak / nie |
| Wariant wielopasmowy (P§7) | jw., lata testowe | ρ prostego wskaźnika | Δρ [przedział] | przyjęty / nie |
| Kalibracja z (T1) | archiwum VI–IX | 19,6% (Plan v7, VINEYARD_06, przed A3) | p̂ [przedział] | wykryto / nie wykryto rozkalibrowania |
| Szum (T2) | pary scen | — | MDC95 G5 / G13 | próg „wyraźnej zmiany” |

## Po W3b

Rozplątanie sygnału winnicy (Plan v8, moduły 2–3) oceniamy tymi samymi T1–T3, na tym samym produkcie `S2_10m_buf20`,
w nowej wersji protokołu, która zmienia tylko wejścia. Punktem odniesienia są wiersze `w3b_tests.csv` dla prostego
wskaźnika i wariantu wielopasmowego, niezależnie od tego, który wygrał.
