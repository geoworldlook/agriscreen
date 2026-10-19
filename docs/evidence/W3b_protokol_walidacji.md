# W3b — protokół walidacji „Moja winnica” (pre-rejestracja)

> **Status:** `REGISTERED` 2026-10-19 (D-089) · SHA-256 sekcji 0–13: `f01b74a804b28315dea94df90b9c685b4e5c9d621211be92be5e992a542b05cf`
> - Skrót liczy `sed -n '/^## 0\./,$p' docs/evidence/W3b_protokol_walidacji.md | sha256sum`. Ten sam skrót
>   `task_parcel_tests` zapisuje w `w3b_tests.csv` i ostrzega, gdy treść sekcji 0–13 różni się od zarejestrowanej.
> - Rozstrzygnięcia U1–U8 (§13) to rekomendacje przyjęte 2026-10-19 razem z poleceniem wdrożenia kodu, bez osobnej
>   decyzji dla każdego punktu. Rejestracja jest przed pierwszym liczeniem testów na danych Sentinel-2 (testy liczy
>   dopiero notatnik w Colab); zmiana któregoś U przed tym przebiegiem = nowa wersja protokołu i nowy skrót.
> - **Zmiana po rejestracji:** nowa wersja protokołu, nowy skrót i opis, co i dlaczego zmieniono (jak W2+REF, D-083).
> - **Podstawa:** Plan W3b §1–§4 (D-084–D-088); reguły czujnika A4 §3–4 (D-060–D-063). Wdrożenie:
>   `docs/plans/W3b_plan_wdrozenia.md`, kod `step_11_parcel.py`. Symulacje: `docs/evidence/W3b_symulacje.py` (ziarno 42).
>
> **Oznaczenia:** [P] pełny tekst pracy; [D] nasze dane, kod albo dokument; [K] konwencja, nie optimum i nie wynik
> z danych; [W] wiedza ogólna; **(U1–U8)** — rozstrzygnięcie w §13.

## 0. Dane, zamrożenie, przedział ufności

| Dane | Zakres | Uwagi |
|---|---|---|
| Sentinel-2 L2A (`COPERNICUS/S2_SR_HARMONIZED`, `step_01`) | rastry na Dysku, IV–X, 2016 → `W3B_FREEZE`; 414 scen przy pisaniu protokołu | Pasma 20 m zapisane na siatce 10 m metodą najbliższego sąsiada (bloki 2×2) [D]. Kolekcja zharmonizowana, więc zmiana przetwarzania z 2022 r. nie wymaga korekty [D] |
| Zamrożenie testów (U6) | `W3B_FREEZE` = data ostatniej sceny w `S2_DIR` przy pierwszym liczeniu testów, po statystykach działek (K2); zapis w `w3b_freeze.json` razem z SHA-256 listy plików | Testy liczymy tylko na scenach ≤ tej daty; anomalie do testów liczymy od nowa z tych scen. Nowsze sceny trafiają na kartę, nie do testów. Notatka wyników podaje liczbę scen, pierwszą i ostatnią datę, SHA-256 listy plików i commit kodu |
| ERA5-Land, dane dobowe | 1991 → dziś | `precip_mm`; warstwa 0–100 cm = `step_04.rootzone`; percentyl wobec 1991–2020, ±15 dni, liczony tak samo jak na karcie wody |
| SWI v4 0,1°, T = 15 | 2007 → dziś | tylko wiersz opisowy (§6) |
| ISMN Condom 20 i 30 cm | stały okres 2016-01-01 – 2024-12-31 | reguły A4, wariant główny W1 (`step_07.a4_variants`) |

**Przedział 95% — jedna metoda dla wszystkich wierszy: jackknife po latach (U8).**
- Statystykę θ liczymy na całej próbie i G razy bez kolejnego roku: θ₋₁ … θ₋G.
- SE = √((G−1)/G · Σ(θ₋g − θ̄₋)²); przedział θ ± t(0,975; G−1)·SE, przycięty do zakresu statystyki (udział 0–1,
  MDC ≥ 0, ρ w [−1; 1]).
- Bez losowania, więc wynik nie zależy od ziarna.
- Uzasadnienie [D, `W3b_symulacje.py`]: przy 7 sezonach i celu o autokorelacji jak czujnik jackknife daje 2,5% fałszywych
  zaliczeń kryterium przy ρ = 0, a bootstrap percentylowy po latach (Plan W3b v5) ok. 3,5%.

## 1. Działki, piksele, sceny

| Element | Definicja | Uzasadnienie, źródło |
|---|---|---|
| Działki | 15 winnic `Typ = winnice` (fid 6–18, 21, 22); `site_id = VINEYARD_{fid:02d}` | wszystkie winnice w AOI [D: geojson] |
| Pas wewnętrzny | Obrys zwężony o 20 m. Piksel 10 m wchodzi, gdy jego środek leży w zwężonym obrysie. **Bez awaryjnego `all_touched`** | Piksel 20 m wystaje poza działkę najwyżej ok. 1 m przy pasie 20 m, a do ok. 11 m przy pasie 10 m [D]. Laroche-Pinel 2021, s. 18: pas ≥ 5 m, tylko piksele w całości w działce; zalecenie nietestowane [P] |
| Wielkość działki | Działka wchodzi do testów i mediany, gdy zwężony obrys ma **≥ 40 pikseli 10 m**. Mniejsza dostaje na karcie „działka za mała na wiarygodną anomalię” | [K] próg z rozmiarów działek, nie z wyników. Przy 4 przesunięciach siatki [D]: fid 16 ma 18–19 pikseli, fid 18 14–16; najbliżej progu fid 22 (44–46) i fid 10 (47–49); VINEYARD_06 135–142. Przechodzi 13 z 15 |
| Czysta scena | ≥ 90% pikseli zwężonego obrysu czystych (`cloudmask = 0`) i wszystkie 10 pasm skończone | [K] `VEG_MIN_CLEAR_FRAC` potoku |
| Wartość w scenie | Wskaźnik w pikselu, potem średnia z czystych pikseli; dla B04, B06, B8A, B12 średnie odbicie | jak `step_04.site_stats` [D] |
| Jedna scena na dzień | Przy 2 scenach działki w jednym dniu zostaje ta z większym `clear_frac`, **zanim** liczymy normę. Liczbę takich dni raportujemy | inaczej ta sama scena weszłaby 2 razy do normy, mediany i par T2 |
| Zbiory | **T1, T2, flaga (§8):** winnice z QC (13). **T3 i §7:** winnice z QC bez VINEYARD_06 (12) | na VINEYARD_06 w F4 wybierano okno (Plan W3b §3) |
| Miesiące | Testy VI–IX, karta IV–X | Unnisa 2025, s. 16: wskaźniki działały przy rozwiniętym łanie [P]. W IV i X okno normy ±15 dni jest ucięte, bo archiwum to IV–X [D] |

## 2. Norma

- Każdy wskaźnik (NDMI, CRSWIR, NDVI, NDRE) i każde pasmo (B04, B06, B8A, B12) osobno liczy `step_04.scene_anomaly`
  z `monitor_config`, bez zmian metody [K: potok, Plan v7 A1–A3]:
  - sceny z lat Y−5…Y−1 w oknie ±15 dni roku;
  - ten sam tor orbity, gdy ma ≥ 5 scen, inaczej oba tory (`all_tracks`); min. 5 scen, inaczej brak z;
  - z predykcyjne: t = (x − μ)/(s·√(1 + 1/n)), z = Φ⁻¹(F_t(t; n − 1)).
- Przy każdej scenie zapisujemy `n_ref`, `n_ref_years` (liczba różnych lat w puli), `ref_mode`, `track`.
- z istnieje częściowo od 2018 (ok. połowa scen, głównie oba tory), w pełnych sezonach od 2019, z pełną 5-letnią pulą
  od 2021 [D, Plan W3b §3].
- Minimalna liczba lat w puli (U2): bez progu, jak w potoku. Opisowo podział 1–2 / ≥ 3 lata; przy < 3 latach karta
  dopisuje „krótka historia (N lat)”.
- Tor: `track_ids` (próg Otsu na godzinie akwizycji) [D]. QC podaje udział dni, w których tor różni się między
  działkami.

## 3. Wskaźnik wody i klasy

| | Definicja | Uzasadnienie, źródło |
|---|---|---|
| NDMI | (B8A − B11)/(B8A + B11) | Carletti 2025, tab. 1 [P]. Ceccato 2001, tab. 6: iloraz SWIR/NIR podnosi udział wody w odbiciu liścia z 36% do 87% [P] |
| CRSWIR | B11 / [B8A + (B12 − B8A)·w], w = (1610,4 − 864)/(2185,7 − 864) = **0,5647** | kod FORDEAD [P]. Stała 0,5623 (`CRSWIR_W`) zostaje w starych produktach; 0,5647 tylko w `S2_10m_buf20` [D] |
| z_woda | (z_NDMI − z_CRSWIR)/2, tylko gdy oba z istnieją dla tej samej sceny | z predykcyjne jest antysymetryczne, więc −z_CRSWIR = z(−CRSWIR) dokładnie [D]. Wagi po ½ [K] |
| Znak | Ujemne = mniej wody w roślinności (winorośl + międzyrzędzie) niż we własnej historii o tej porze roku | Plan W3b §2 |
| Klasy | z ≤ −1 „poniżej swojej normy”; z ≥ +1 „powyżej”; pomiędzy „w normie” | [K] `THR_VEG` potoku; D-081 bez klas bezwzględnych. Unnisa 2025, s. 16: progi σ „somewhat arbitrary” [P] |
| Skala | Bez przeskalowania. Przy r składników ≥ 0,9: P(z ≤ −1) = 15,2–15,9%. r raportujemy | obliczenie [D]. Wysokie r częściowo z konstrukcji: oba składniki używają B8A i B11 |
| Szczegół na karcie | z NDMI, −CRSWIR, NDVI i NDRE z tego samego produktu, z napisem „niezwalidowane” | Plan W3b §1 |

## 4. T1 — kalibracja (opisowo, reguła karty) (U1)

- **Zbiór:** pary (winnica z QC, scena) z VI–IX, sceny ≤ `W3B_FREEZE`, z_woda istnieje.
- **Miara:** p̂ = udział z_woda ≤ −1, liczony łącznie; oczekiwane 15,9% = Φ(−1). Przedział jackknife (§0).
- **Werdykt (słowa w tabeli wyników):** „nie wykryto grubego rozkalibrowania”, gdy przedział zawiera 15,9%; inaczej
  „klasa »poniżej« częściej / rzadziej niż zakładane”. Nie piszemy „zaliczony”.
- **Skutek na karcie:** „Na ile ufać” zawsze podaje p̂ z przedziałem. Gdy przedział nie zawiera 15,9%, karta dopisuje
  „w archiwum ta klasa wypadała częściej (rzadziej) niż 1 na 6 scen”. Metody w tej wersji nie poprawiamy; każda
  poprawka (np. norma ważona latami, Plan v7 A3) to nowa wersja protokołu.
- **Opisowo:** udział z ≥ +1 i |z| ≥ 2; p̂ dla każdego roku; podział `n_ref_years` 1–2 / ≥ 3; NDVI osobno; p̂ mediany
  okolicy (zbiór T3; jej klasę pokazuje zdanie 3); p̂ w dniach z glebą w normie (percentyl ERA5-Land w (30; 70), ta sama
  funkcja co karta). Zastrzeżenie: gleba ma normę 1991–2020, a roślinność ostatnie 5 lat z suchymi 2019, 2022 i 2023,
  co sprzyja niskiemu p̂ w tym podzbiorze.
- **Czułość** [D, `W3b_symulacje.py`, 9 sezonów × 25 scen × 13 winnic, wspólna składowa roku 20–60% wariancji]:
  - przy poprawnej kalibracji p̂ wypada w 4–33% (95% archiwów);
  - przedział zawiera 15,9% w 87–93% archiwów;
  - z rozciągnięte 1,3 raza (prawdziwe p ≈ 22%) przedział wykrywa tylko w ok. 7%.

  T1 wykrywa więc tylko rażące rozkalibrowanie. Dlatego jest opisowy, a nie kryterium.

## 5. T2 — szum i najmniejsza wykrywalna zmiana (opisowo, reguła karty)

- **Pary:** ta sama winnica z QC, oba końce z ważnym z, VI–IX; wszystkie pary spełniające regułę:
  - **G5 „ten sam tor”:** ten sam `track`, Δt 4–6 dni;
  - **G13 „różne tory”:** różne `track`, Δt 1–3 dni.
- **Miara:** d = z(t2) − z(t1); MDC95 = 1,96·√(Σd²/n). Wzór obejmuje też stałe przesunięcie torów [W].
- **Założenie:** w ≤ 6 dni stan się nie zmienia; prawdziwe zmiany zawyżają MDC, więc oszacowanie jest ostrożne
  (Laroche-Pinel, s. 7: sceny ≤ 5 dni od pomiaru) [P].
- **Opad:** P = suma `precip_mm` ERA5-Land od t1 do t2 włącznie; para „z opadem” przy P ≥ 5 mm [K]. MDC główne z par
  bez opadu, w których oba końce mają `ref_mode = same_track`.
- **Przedział:** jackknife (§0). Grupa z < 30 parami: „za mało par”, bez MDC.
- **Opisowo:** pary z opadem; NDMI, −CRSWIR, NDVI, NDRE w z i w jednostkach wskaźnika (różnica surowa pokazuje
  przesunięcie torów, ok. 0,4 z, Plan v7).

## 6. T3 — roślinność winnic a czujnik (kryterium zdania 3)

**Cel y(t)**, t = dzień sceny:
1. Dzień czujnika = średnia 20 i 30 cm po A4 W1, tylko gdy obie głębokości mają wartość. Dzień `FAST_DROP` to brak
   danych; dzień cenzurowany ma θ_dno = 0,10 m³/m³ (jak W2+REF) [D].
2. z dzienne: `clim_anomaly` wobec 2016–2024, ±15 dni, min. 20 wartości; **obcięte do [−3; 3]**. Norma obejmuje też
   dzień t i dni późniejsze; wpływ na y(t) < 0,01 z (test w selftescie).
3. y(t) = średnia z z dni **[t−30, t−1]**, ważna przy ≥ 20 dniach (U5). Dzień sceny wyłączony, bo średnia dobowa
   obejmuje godziny po przelocie.
   - Okno wybrane w F4 spośród 5 wariantów (`a3_lag.csv`; zysk wobec dnia sceny +0,055 [−0,045; 0,177], nieistotny) [D].
   - Choi 2017, tab. S2: w Condom r 0,64–0,79 przy przesunięciach 0–30 dni, na wartościach surowych [P].

**Predyktor x(t):** mediana z_woda winnic zbioru T3 (12) w dniu t; dzień ważny przy ≥ 6 winnicach [K].

**Próba:** dni scen VI–IX 2018–2024 z ważnym x i y. Gdy mniej niż 5 sezonów ma ≥ 5 dni: „nierozstrzygnięty”.

**Miara:** ρ Spearmana łącznie dla wszystkich lat (rangi średnie, jak `step_10._spearman`).

**Kryterium zdania 3: dolna granica przedziału jackknife po latach (§0) > 0.**

**Wiersze opisowe** (ta sama tabela, bez kryteriów):
- **Lata:** ρ bez każdego roku (liczone i tak dla jackknife; gdy któreś ≤ 0: „wynik zależy od jednego roku”); ρ wewnątrz
  roku (x i y po odjęciu średniej sezonu); ρ średnich sezonów (n = 7, bez przedziału).
- **Cel:** czujnik A4 W2, W3, W1_05WP, W1_015; ERA5-Land 0–100 cm i SWI T15 (z wobec 2016–2024, to samo okno, te same dni).
- **Kontrola cenzury:** ρ(x, udział dni cenzurowanych w [t−30, t−1]) — czy roślinność śledzi samą cenzurę.
- **Wartości surowe:** mediana surowego NDMI wobec średniej surowego θ (W1) z okna; pokazuje, ile daje cykl sezonowy.
- **Predyktor:** NDVI, NDMI i −CRSWIR osobno; zbiór z VINEYARD_06.

**Nie dodajemy** innych okien (15, 45 dni) ani podziału miesięcy. Każdy taki wiersz to kolejna ścieżka wyboru.

## 7. Wariant wielopasmowy (kryterium przyjęcia)

| | Definicja | Uzasadnienie, źródło |
|---|---|---|
| Cechy | x_b(t) = mediana z_b zbioru T3 dla b ∈ {B04, B06, B8A, B12}; z_b z normy §2 liczonej na średnim odbiciu pasma. Dzień ważny, gdy ≥ 6 winnic ma 4 pasma | Laroche-Pinel 2021, s. 13: 4 pasma dają R² ≈ 0,40, tyle co wszystkie [P]. Anomalie pasm jako cechy: Carletti 2025, s. 6 [P] |
| Cel | y(t) z §6 | |
| Model | OLS z wyrazem wolnym: y = β0 + Σ βb·x_b. Bez regularyzacji i selekcji | Laroche-Pinel, tab. 8: najlepsze modele liniowe [P]. Bez hiperparametrów nie ma czego stroić |
| Walidacja | Kolejno bez każdego roku 2018–2024: uczenie na pozostałych latach (min. 30 dni) | Plan W3b §2a |
| Wynik foldu | s⁽⁻ᵍ⁾(t) = Σ βb⁽⁻ᵍ⁾·x_b(t), **bez β0**, podzielone przez SD tej sumy na dniach uczących | β0 foldu jest ujemnie związany ze średnią roku pominiętego i obciążałby ocenę przeciw wariantowi |
| Ocena | ρ_multi = Spearman(s⁽⁻ᵍ⁾, y) łącznie; ρ_prosty = Spearman(x, y) **na tych samych dniach**; Δρ = ρ_multi − ρ_prosty | |
| **Reguła przyjęcia** | **Dolna granica przedziału jackknife Δρ > 0** (predykcje stałe, bez ponownego dopasowania). Inaczej zostaje z_woda | Plan W3b §2a |

**Gdy przyjęty (U7, wariant A):**
- wagi β1–β4 z lat 2018–2024 zamrażamy;
- wynik okolicy z_mb(t) = (s(t) − średnia)/SD, gdzie s(t) = Σ βb·x_b(t), a średnia i SD z dni VI–IX 2018–2024;
- z_mb zastępuje medianę z_woda **tylko w zdaniu 3** (okolica), bo tylko tam wariant jest sprawdzony; zdanie 2 zostaje
  przy z_woda;
- zdanie 3 pokazujemy, gdy dolna granica przedziału jackknife ρ_multi > 0.

**Ochrona przed wyciekiem:** cechy przyczynowe (norma z lat wcześniejszych); nic nie stroimy w foldzie; β0 poza oceną,
więc standaryzacja celu na 2016–2024 nie zmienia rang; VINEYARD_06 poza próbą. Opisowo: wagi z każdego foldu (czy znak
jest stały), korelacje między x_b, ρ dla każdego roku testowego.

**Zastrzeżenie:** ocena z pominięciem roku uczy też na latach późniejszych, więc sprawdza uogólnienie na nowy rok, a nie
działanie w czasie rzeczywistym. Model uczy się wody w glebie pod trawą, a nie wody w winorośli. Różnica dwóch ρ ma
mniejszą moc niż sam T3 (§12).

## 8. Flaga „możliwa zmiana gospodarowania”

- **Odchylenie od sąsiadów:** d(v,t) = z_woda(v,t) − mediana z_woda pozostałych winnic z QC w dniu t, gdy jest ich ≥ 6.
- **Flaga sezonu (v, Y),** sceny IV–X: ≥ 6 scen z d, z czego ≥ 2/3 ma d ≤ −1 → flaga „−”; ≥ 2/3 ma d ≥ +1 → flaga „+”
  [K, liczbowy zapis „przez cały sezon” z Planu W3b §4]. W bieżącym sezonie od 1 IV do ostatniej sceny.
- **Na karcie:** „porównanie z historią mniej pewne”, gdy flaga jest w roku Y albo w którymkolwiek roku normy Y−5…Y−1.
- **Bez skutków dla danych:** normy nie zmieniamy, z testów niczego nie wyłączamy; raport podaje liczbę sezonów z flagą.
- **Uzasadnienie:** zabiegi zmieniają wskaźniki niezależnie od suszy (Unnisa 2025, s. 16) [P]; ryzyko pomylenia sygnału
  ze zmianą gospodarowania rośnie z czasem (Carletti 2025, s. 11) [P]; w suszy wszystkie winnice są nisko, więc d ≈ 0.
- **Ograniczenie:** zmiana na wielu działkach naraz nie zostanie wykryta.

## 9. Wartości „przed” (przeliczenie F4)

Wartości opublikowane w F4 (VINEYARD_06, IV–X, R Pearsona z przedziałem z bloków 30-dniowych):

| Nr | Miara | F4 | Plik |
|---|---|---|---|
| P1 | r z_NDMI i −z_CRSWIR | 0,97 (n = 344) | `a2_variant_series.csv` |
| P2 | r z_NDMI i z_NDVI | 0,94 | `a2_variant_series.csv` |
| P3 | R z_NDMI wobec z czujnika z dnia sceny | 0,41 (n = 245) | `a3_lag.csv` |
| P4 | R z_NDMI wobec średniej z czujnika z [t−30, t] (≥ 20 dni) | 0,47 (n = 231) | `a3_lag.csv` |
| P5 | R wewnątrz roku / średnich rocznych | 0,30 [0,02; 0,52] / 0,55 (9 lat) | `a5_decomposition.csv` |

**Drabinka dla P4**, VINEYARD_06, IV–X, na dniach wspólnych 2018–2024; miara, okno [t−30, t] i przedział jak w F4;
z czujnika według §6 pkt 1–2:

| Krok | Roślinność | Czujnik | Co pokazuje różnica |
|---|---|---|---|
| a | z_NDMI z F4 (`a2_variant_series.csv`, kolumna `V3a_ndmi_scene`) | A4 W3 (QC sprzed A4) | — |
| b | norma przyczynowa, `S2SR_2.5m` (`veg_anomalies.csv`) | A4 W3 | a→b: wpływ normy, czyli wyciek przyszłych lat |
| c | jak b | A4 W1 | b→c: reguły czujnika |
| d | `S2_10m_buf20` | A4 W1 | c→d: produkt (10 m, pas 20 m) |

- P1–P5 przeliczamy też w konfiguracji d na wszystkich dniach z danymi (IV–X 2018–2024): dla VINEYARD_06 i dla mediany
  zbioru T3.
- Bez kryterium. Przy każdej liczbie n i lata. Dopiero te liczby są wartościami „przed”, także dla Planu v8.
- Skrypty F4 nie odtwarzają dziś liczb F4: ich `VEG_CFG` nie ma kluczy `VEG_CAUSAL` i `VEG_REF_YEARS`, więc dziś
  dostają domyślną normę z lat wcześniejszych zamiast „pozostałych lat”. Krok a bierzemy więc z pliku CSV [D].

## 10. Karta: co pokazujemy na podstawie wyników

| Element | Reguła |
|---|---|
| Zdanie 1 | Klasa gleby z percentyla ERA5-Land 0–100 cm wobec 1991–2020: ≤ 30 sucho, ≥ 70 wilgotno, pomiędzy w normie. Kod USDM i percentyl jako szczegół. Zgodność klas z czujnikami ok. 55% (W2+REF) |
| Zdanie 2 | Klasa z_woda (§3) z najnowszej sceny działki. Scena starsza niż 30 dni → „brak aktualnej sceny”. Działka < 40 pikseli → „działka za mała na wiarygodną anomalię”, bez klasy |
| „k z N winnic” | N = winnice z QC z z_woda w tym samym dniu sceny; k = te w tej samej klasie |
| Zmiana od poprzedniej sceny | „Wyraźna zmiana” tylko przy Δt ≤ 6 dni i \|Δz\| ≥ MDC95 grupy tej pary (G5 albo G13). Przy P ≥ 5 mm dopisek „między scenami padało”. Przy Δt > 6 dni tylko obie wartości z datami. Grupa „za mało par” → bez oceny zmiany |
| Dopiski | flaga §8 → „porównanie z historią mniej pewne”; `n_ref_years` < 3 → „krótka historia (N lat)”; poza VI–IX → „poza okresem sprawdzonym (VI–IX)” (U4); T1 wg §4 |
| Zdanie 3 | Tylko gdy spełnione kryterium §6 (albo §7 przy przyjętym wariancie). Treść: klasa okolicy (mediana z_woda zbioru T3, albo z_mb) i zdanie, że w 2018–2024 szła w parze z wodą w glebie z 30 dni przed sceną (ρ z przedziałem), z dopiskiem „dla pojedynczej działki tego nie sprawdzaliśmy” |
| Na ile ufać | p̂ z T1 z przedziałem, MDC95, ρ z T3 z przedziałem; przy niespełnionym kryterium ρ z napisem „niepotwierdzone” |
| Słowa | wg D-087. Nigdy „stres wodny winorośli”, „wczesne ostrzeżenie” ani „winorośl reaguje po N dniach” |
| Zamrożenie | MDC95, p̂, werdykt T3 i wagi §7 są stałe do następnej wersji protokołu |

## 11. Reguły raportu

1. **Jedna tabela.** Przy każdym wierszu: wartość, przedział 95%, liczba dni scen, lata i liczba winnic.
2. **Tylko 2 kryteria:** T3 (zdanie 3) i przyjęcie §7. Reszta opisowo, bez wybierania „zwycięzcy” i bez korekty na
   wielokrotne porównania.
3. **Wynik negatywny pierwszy** w „Wynik w skrócie”.
4. **Bez zmian po wyniku.** Zmiana definicji = nowa wersja protokołu. Poprawka błędu implementacji (kod nie robi tego,
   co mówi protokół) jest dozwolona: commit i opis w notatce wyników.
5. **QC:** na działkę piksele, sceny przyjęte i odrzucone, dni z 2 scenami, `n_ref`, `ref_mode`, lata w puli, flagi;
   zgodność toru między działkami; dni cenzurowane i `FAST_DROP` w oknach T3; r(x mediany 12 winnic, z_woda
   VINEYARD_06) w dniach T3, czyli ile niezależności daje wyłączenie VINEYARD_06.
6. **Bez porównań z literaturą.** Naszego ρ nie zestawiamy z R² ani r z prac (inne cele albo surowe serie).

## 12. Ograniczenia znane przed liczeniem

- **T3 to sprawdzenie spójności, nie test na nowych danych.** Czujnik, lata 2018–2024, miesiące VI–IX i okno widzieliśmy
  już w F4 (`a2_variants_eval.csv`). Pre-rejestracja chroni tylko przed nowymi wyborami.
- **Cel to nie woda w winorośli.** Punktowy czujnik pod trawą, 136 m od VINEYARD_06; nawadnianie winnic nieznane.
- **Cenzurowanie A4 W1 latem** [D]: w VI–IX 2018–2024 65–113 ze 122 dni sezonu ma ocenzurowaną co najmniej jedną
  głębokość; dzień cenzurowany dostaje z zależne od miesiąca (mediana: VI −1,06; VII −0,50; VIII −0,44; IX −0,30).
  Ranga celu zależy więc od umownego θ_dno: Spearman celu W1 wobec W1_05WP / W1_015 / W3 = 0,91 / 0,88 / 0,89
  [D, `W3b_symulacje.py`]. Artefakt działa głównie wewnątrz roku, więc ρ wewnątrz roku jest w latach z cenzurą
  obciążone w dół.
- **Mała próba i silna autokorelacja celu** [D, `W3b_symulacje.py`]: 7 sezonów (2018 częściowo); autokorelacja celu
  0,96 / 0,87 / 0,54 przy 5 / 10 / 30 dniach (po odjęciu średniej sezonu 0,91 / 0,72 / −0,03); 50% wariancji między
  latami. Symulacja z takim celem (7 sezonów; 16 dni scen na sezon, w 2018 8 — szacunek):

  | Prawdziwe ρ | 0 | 0,2 | 0,3 | 0,45 |
  |---|---|---|---|---|
  | Kryterium T3 spełnione (jackknife) | 2,5% | 16% | 23% | 51% |

  **Najbardziej prawdopodobny wynik T3 to „nierozstrzygnięty”**, także gdy związek istnieje. Wariant wielopasmowy ma moc
  jeszcze mniejszą, bo testuje różnicę dwóch ρ.
- **Norma 5-letnia obejmuje lata suche** (2019, 2022, 2023), więc anomalia znaczy „wobec ostatnich 5 lat”. Carletti 2025,
  s. 11, przestrzega przed kalibracją normy w okresie zaburzeń [P].
- **T1 wykrywa tylko rażące rozkalibrowanie** (§4). df = n_ref − 1 zawyża pewność, gdy zmienność jest głównie
  międzyroczna; wtedy p̂ wyjdzie powyżej 15,9%.
- **Składniki dzielą B8A i B11,** więc wysokie r NDMI–CRSWIR częściowo wynika z konstrukcji.
- **Pas 20 m zakłada eksport metodą najbliższego sąsiada.** Przy innym resamplingu piksel 20 m wystaje dalej.
- **2 z 15 winnic** (0,68 i 0,73 ha) są poza testami; mediana obejmuje 12 winnic, w części dni mniej (chmury per działka).

## 13. Rozstrzygnięcia (U1–U8)

Przyjęte 2026-10-19 rekomendacje, przed pierwszym liczeniem testów na danych Sentinel-2.

| | Wybór | Rozstrzygnięcie | Odrzucona alternatywa |
|---|---|---|---|
| U1 | rola T1 | opisowo + dopisek na karcie (§4): symulacja pokazuje, że T1 nie ma mocy | kryterium „przedział zawiera 15,9%” dla zdania 2 (Plan W3b v5 §3) |
| U2 | minimalna liczba lat w puli | bez progu (jak potok); dopisek „krótka historia” | ≥ 3 lata (Plan v7 A1): T3 traci 2018, zostaje 6 sezonów |
| U3 | cel T3 | A4 W1, jak W2+REF; pozostałe warianty opisowo | W2: usuwa prawie wszystkie suche epizody (A4 §4) |
| U4 | karta w IV–V i X | pokazywać z dopiskiem „poza okresem sprawdzonym” | ukryć zdanie 2 poza VI–IX |
| U5 | drobne progi | okno [t−30, t−1] przy ≥ 20 dniach; z czujnika obcięte do [−3; 3]; opad 5 mm; ≥ 6 winnic; flaga 2/3 z ≥ 6 scen | okno [t−30, t] jak w F4 (korelacja obu wersji 0,999) |
| U6 | zamrożenie testów | ostatnia scena w `S2_DIR` przy pierwszym liczeniu testów (§0), lista plików z SHA-256 | 2026-10-31, ale wtedy testy dopiero po pobraniu scen z końca października |
| U7 | wariant wielopasmowy na karcie | A: tylko zdanie 3 (okolica), bo tylko tam jest sprawdzony | B: także zdanie 2, ale wtedy T1 i MDC95 trzeba liczyć na z_mb jako kryteria |
| U8 | przedział dla kryteriów | jackknife po latach (§0): 2,5% fałszywych zaliczeń w symulacji, bez losowania | bootstrap percentylowy po latach (Plan W3b v5): ok. 3,5% i wynik zależny od ziarna |
