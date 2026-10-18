# Plan W3b — „Moja winnica wobec jej historii” (wersja 4)

Status: **PROPOSED** 2026-10-18, do akceptacji przed kodem. Wersja 4 = wersja 3 + wybór wskaźnika (wariant b,
2026-10-18): główny wskaźnik „woda w liściach” z NDMI i CRSWIR, pozostałe jako szczegół. Literatura:
`docs/evidence/W3b_przeglad_literatury_woda_w_lisciach.md`. Rozwija W3b z Planu v9 §5b (D-073).

## 1. Co dostaje rolnik

Karta „Moja winnica” z trzema zdaniami:

1. **Gleba w okolicy** (ERA5 + SWI, ~10 km): sucho / w normie / wilgotno wobec historii. *Już zwalidowane (W2 + REF).*
2. **Twoja działka — woda w liściach** (Sentinel-2, SWIR): poniżej / w normie / powyżej **swojej własnej historii**
   o tej porze roku; obok, ile winnic w okolicy jest w tym samym stanie.
   Pod spodem szczegół: każdy składnik osobno (NDMI, CRSWIR) oraz zieleń (NDVI) i chlorofil (NDRE).
3. **Czy to się zgadza z glebą:** jedno zdanie łączące 1 i 2, pokazywane tylko wtedy, gdy test T3 potwierdzi związek.

Czego karta nie mówi: „winorośl ma stres wodny”. Wskaźnik widzi całą działkę: winorośl, międzyrzędzie i glebę.
Wydzielenie samej winorośli to następny etap (Plan v8: rozplątanie kanałów siecią neuronową).

## 2. Wskaźnik „woda w liściach”

| | Definicja | Dlaczego (literatura i nasze dane) |
|---|---|---|
| **Składniki** | NDMI = (B8A − B11)/(B8A + B11); CRSWIR = B11 / [B8A + (B12 − B8A)·w] (wyższy = mniej wody, więc w złożeniu ze znakiem −). Oba już liczone w `step_04.compute_indices`, z natywnych pasm 20 m | woda pochłania w SWIR, a NIR koryguje budowę liścia (Ceccato 2001); wskaźniki wody reagują w suszy wcześniej niż zieleń (Unnisa i in. 2025); CRSWIR z INRAE FORDEAD liczy anomalię piksela wobec własnej historii, jak my |
| **Anomalia składnika** | z wobec własnej historii działki: ten sam tor orbity, ±15 dni roku, 5 wcześniejszych lat, z predykcyjne z rozkładu t (istniejące `scene_anomaly`) | metoda potoku, bez zmian |
| **Złożenie** | z_woda = (z_NDMI + z_−CRSWIR) / √(2·(1 + r)), gdzie r = korelacja obu z w scenach odniesienia tej działki | średnia przeskalowana tak, żeby znowu miała skalę z (wtedy progi −1 i +1 znaczą to samo co dla jednego wskaźnika) |
| **Klasy** | z_woda ≤ −1 „poniżej swojej normy”; ≥ +1 „powyżej”; pomiędzy „w normie” | bez klas bezwzględnych (D-081) |

**Co wiemy z góry (zapis uczciwości):** na VINEYARD_06 anomalie NDMI i CRSWIR korelują na poziomie 0,97 (F4). Złożenie
da więc prawie to samo co NDMI; jego zaletą jest odporność (dwa sposoby pomiaru tej samej absorpcji), nie dodatkowa
informacja. NDVI i NDRE korelują z NDMI na poziomie 0,94–0,98, dlatego są szczegółem, a nie drugim potwierdzeniem.

## 3. Dlaczego to się obroni: jedno zdanie, jeden test

| Zdanie na karcie | Test (zapisany przed liczeniem) | Dane |
|---|---|---|
| 1. Gleba w okolicy | zrobione: R 0,52–0,68 wobec czujników na 3 stacjach | ERA5, SWI, ISMN, ICOS |
| 2. „Działka poniżej swojej normy” | **T1 kalibracja:** gdy gleba w okolicy jest w normie, „poniżej” zdarza się tak często, jak mówi rozkład (ok. 1 scena na 6) | archiwum S-2 na Dysku, ERA5 |
| 2. „Zmiana od poprzedniej sceny” | **T2 szum:** dwie sceny w odstępie ≤ 5 dni dają to samo; zmiana mniejsza niż szum = „bez zmian” | archiwum S-2 na Dysku |
| 3. „Spójne z suszą w glebie” | **T3 związek z czujnikiem:** ρ Spearmana między anomalią winnic wokół Condom a średnią anomalią wody zmierzonej przez czujnik ISMN (136 m od Twojej winnicy) z 30 dni przed sceną; VI–IX; obok to samo dla ERA5 i SWI | archiwum S-2, ISMN 2016–2024, ERA5, SWI |

- **Wszystkie testy liczymy dla wskaźnika głównego i dla każdego składnika i szczegółu** (NDMI, CRSWIR, NDVI, NDRE).
  Wskaźnik na karcie jest wybrany przed liczeniem i nie zmieniamy go po wyniku. Tabela pokaże, czy SWIR daje coś
  ponad zieleń.
- **Okno T3 (30 dni przed sceną)** pochodzi z literatury (reakcja upraw po ok. 25 dniach — Choi i in. 2017) i z F4
  (najlepsze w każdym roku walidacji krzyżowej). F4 widziało VINEYARD_06, dlatego miarą główną T3 jest mediana
  pozostałych 14 winnic.
- Jeśli T3 wyjdzie słabo, zdanie 3 nie pojawia się na karcie, a zdanie 2 opisuje tylko działkę.

## 4. Kroki

| Krok | Co | Sesje |
|---|---|---|
| **K1** | Protokół T1–T3 i definicja wskaźnika (§2–3); skrót SHA-256 przed liczeniem | 1 |
| **K2** | Statystyki działek z archiwum na Dysku (414 scen 2016–2026, bez nowego pobierania): istniejące `task_scene_stats` rozszerzone z VINEYARD_06 na wszystkie 15 winnic; obrys zwężony o 20 m (pasma SWIR mają 20 m) | 1 |
| **K3** | Anomalie składników i wskaźnika „woda w liściach” + przebieg T1–T3 w Colab; notatka wyników z tabelą wszystkich wskaźników; wiersze w karcie wyników | 1–2 |
| **K4** | Karta „Moja winnica” w dashboardzie, biuletynie i notatniku (wskaźnik główny + rozwijany szczegół); nagłówek gleby w 3 klasach | 1–2 |

Razem 4–6 sesji. Bieżące sceny dochodzą przyrostowo tym samym potokiem, więc karta działa w sezonie 2027 na bieżąco.

**Potem:** rozplątanie kanałów (Plan v8, moduły 2–3). Ocena: te same T1–T3, przed i po.

**Świadomie poza tym planem:** sceny S-2 przy stacjach ICOS, mapa stref w działce, wgrywanie dowolnej działki,
temperatura liści (w Copernicusie tylko 1 km), GVMI / NMDI / MSI (kolejne warianty tej samej informacji).

## 5. Decyzje do zatwierdzenia

- **D-084 Dane:** archiwum S-2 z Dysku i obecny potok (jedno źródło dla historii i bieżących scen).
- **D-085 Wskaźnik:** „woda w liściach” = przeskalowana średnia anomalii NDMI i −CRSWIR (§2); klasy ±1; działka liczona,
  gdy ≥ 80% pikseli bez chmur; NDMI, CRSWIR, NDVI, NDRE jako szczegół.
- **D-086 Walidacja:** T1–T3 jak w §3, dla wskaźnika głównego i wszystkich szczegółów; zapisane i zahaszowane przed
  liczeniem.
- **D-087 Słowa:** „woda w liściach działki (winorośl i międzyrzędzie)”, nigdy „stres wodny winorośli”; nagłówek
  gleby w 3 klasach (sucho / w normie / wilgotno).

## 6. Źródła

Pełna lista i oznaczenia wiarygodności: `docs/evidence/W3b_przeglad_literatury_woda_w_lisciach.md`. Najważniejsze:
Ceccato i in. 2001 (fizyka SWIR + NIR); Unnisa, Ogutu, Dash 2025 (woda w łanie reaguje na suszę wcześniej niż zieleń);
Laroche-Pinel i in. 2021 (winnice, R² 0,40); FORDEAD, INRAE (CRSWIR); Choi i in. 2017 (opóźnienie ok. 25 dni);
dane własne F4 i F7.
