# W3e — protokół „Winnica wobec sąsiadów” (pre-rejestracja)

> **Status:** `REGISTERED` 2026-10-25 (D-092) · SHA-256 sekcji 0–8: `ff20babadf13aa753d940185665cca5431bd6b0533b2eec07134092fc8729b27`
> - Skrót liczy `sed -n '/^## 0\./,$p' docs/evidence/W3e_protokol_sasiedzi.md | sha256sum`. Ten sam skrót
>   notatnik `notebooks/experiments/W3e_sasiedzi.ipynb` liczy i wypisuje przed testami.
> - **Rodzaj:** eksperyment **eksploracyjny** na danych, które w innej postaci już oglądaliśmy. Rozstrzygające
>   potwierdzenie dopiero na sezonie 2027 (lata niewidziane), z tym samym protokołem.
> - **Jawnie, co widzieliśmy przed rejestracją:**
>   - T1 W3b: udział „poniżej swojej normy” 28% wobec 16%, po latach od 1% (2021) do 76% (2022); według gleby
>     w dniu sceny: sucho 46%, w normie 14%, wilgotno 7% (`W3b_wyniki.md` §3 i pkt 3);
>   - flagi zmiany gospodarowania W3b §8 liczone z tej samej różnicy d (§1): VINEYARD_13 2019 (−),
>     VINEYARD_21 2024 (−), VINEYARD_22 2018 (−) i 2022 (+);
>   - kody przesadzeń RPG (VINEYARD_13, 14, 22; `W3c_wyniki.md`).
>
>   Wielkość z_rel (§2) nie była jeszcze liczona. H4 (§6) nie jest więc niezależnym dowodem: trzy z pięciu
>   zdarzeń mają już flagę z tej samej różnicy. Traktujemy go jako sprawdzenie spójności.
> - **Pytanie:** czy porównanie winnicy z sąsiadami tego samego dnia usuwa wspólną pogodę (suchy rok = wszystkie
>   winnice „poniżej normy”) i zostawia to, co dotyczy samej winnicy?
> - **Zdanie dla winiarza (kandydat):** „Twoja winnica jest teraz wyraźnie słabsza niż sąsiednie winnice, licząc
>   względem tego, jak zwykle wypada na ich tle.” Bez oceny stanu winorośli, bez porad.
> - **Literatura (podstawa wyborów):**
>   - porównanie działki z populacją działek tej samej uprawy zamiast z jej własną historią: Mouret i in. 2021,
>     Remote Sensing 13:956 (wykrywanie nietypowego rozwoju upraw, Sentinel-1 i -2, Beauce);
>   - anomalia wobec własnej historii miesza pogodę wspólną dla regionu z czynnikami lokalnymi (badania szkód upałów
>     w winnicach na Sentinel-2; Plan W3b §2);
>   - odporna skala (MAD) zamiast odchylenia standardowego, bo pojedyncze sezony przesadzeń są odstające
>     (Rousseeuw i Croux 1993, JASA 88:1273–1283);
>   - mediana sąsiadów i próg ≥ 6 winnic jak W3b §6 i §8 (`parcel.management_flags`).

## 0. Dane

- `parcel_anomalies.csv` (wynik `task_parcel_anomalies`, Dysk Google): wiersze `index = water` (wskaźnik wody
  z_woda, W3b §3), produkt `S2_10m_buf20`.
- Winnice: 13 z QC W3b (≥ 40 pikseli 10 m w pasie 20 m); VINEYARD_16 i VINEYARD_18 poza.
- Okres testów: sceny VI–IX lat 2018–2026, do daty zamrożenia W3b (`w3b_freeze.json`, 2026-10-18) — ten sam
  wybór scen co T1.
- Gleba w dniu sceny: percentyl ERA5-Land 0–100 cm (`parcel.soil_pct`): ≤ 30 sucho, ≥ 70 wilgotno, pomiędzy
  w normie (jak karta wody i `parcel.t1_by_soil`).
- Przesadzenia: `data/rpg_winnice.csv`, kody `VRN` (młode nasadzenie) i `RVI` (restrukturyzacja), lata ≥ 2018.
- Przedział 95%: jackknife po latach (`parcel.jackknife_ci`, jak W3b §0), udziały przycięte do [0; 1].

## 1. Różnica wobec sąsiadów

- Dla winnicy i w dniu sceny t: d(i, t) = z_woda(i, t) − mediana z_woda pozostałych winnic z QC w dniu t.
- d tylko wtedy, gdy w dniu t jest ≥ 6 pozostałych winnic z wartością (jak W3b §8).
- Jedna scena na dzień (już w `parcel_anomalies.csv`).

## 2. Wielkość z_rel (skala z historii, bez przyszłości)

- Dla winnicy i i roku y: s(i, y) = 1,4826 · MAD wartości d(i, ·) ze scen VI–IX wszystkich lat < y.
- Warunek: ≥ 30 wartości d z ≥ 2 lat wcześniejszych. Bez tego z_rel nie istnieje (scena poza testami).
- z_rel(i, t) = d(i, t) / s(i, y(t)). Bez odejmowania średniej: z_woda jest już liczone wobec własnej normy winnicy.
- Klasa „słabiej niż zwykle na tle sąsiadów”: z_rel ≤ −1; „lepiej”: z_rel ≥ +1.

## 3. Zbiór testów

- Sceny z §0 z istniejącym z_rel (§2). Liczba scen, winnic i lat podana przy wynikach.
- Ta sama definicja dla wskaźnika porównawczego „przed”: z_woda ≤ −1 **na tych samych scenach** (żeby różnica
  zbioru nie udawała poprawy).

## 4. H1 — kalibracja

- Udział z_rel ≤ −1 łącznie, z przedziałem jackknife po latach.
- **Kryterium:** wartość w [10%; 22%] **i** przedział zawiera 15,9% (udział N(0,1) ≤ −1).

## 5. H2 i H3 — niezależność od roku i od gleby

- **H2:** udział z_rel ≤ −1 w każdym roku osobno; rozstęp = max − min po latach.
  **Kryterium:** rozstęp ≤ 25 punktów procentowych.
- **H3:** udział z_rel ≤ −1 w scenach z glebą suchą i wilgotną (§0).
  **Kryterium:** |sucho − wilgotno| ≤ 10 punktów procentowych.
- Dla porównania (opisowo) te same miary dla z_woda na tych samych scenach.

## 6. H4 — czy zostaje sygnał samej winnicy (spójność)

- Sezon winnicy = winnica × rok, sceny VI–IX z z_rel, tylko sezony z ≥ 6 scenami.
- Miara sezonu: mediana |z_rel|.
- Zdarzenia: sezony z kodem `VRN` lub `RVI` (§0) wśród sezonów z miarą. Zdarzenia bez miary wypisujemy i pomijamy.
- Statystyka: średnia ranga percentylowa miar zdarzeń wśród wszystkich sezonów (0 = najmniej, 1 = najbardziej
  nietypowy).
- p: test permutacyjny jednostronny, 10 000 losowań zbioru sezonów tej samej liczności, ziarno 92.
- **Kryterium:** średnia ranga ≥ 0,75 **i** p ≤ 0,05.

## 7. Decyzja

- H1, H2, H3 i H4 spełnione → z_rel jest kandydatem na zdanie „wobec sąsiadów” na karcie i w panelu. Pokazujemy
  je dopiero po potwierdzeniu na sezonie 2027 (te same reguły, nowe zamrożenie).
- H1–H3 spełnione, H4 nie → wielkość skalibrowana, ale bez pokazanego sygnału winnicy: nie dodajemy.
- H1, H2 lub H3 niespełnione → nie przyjmujemy.
- Wynik negatywny zapisujemy tak samo jak pozytywny (`W3e_wyniki.md`, `karta_wynikow.md`).

## 8. Opisowo i ograniczenia znane przed liczeniem

- Opisowo: udziały z_rel ≥ +1 i |z_rel| ≥ 2; korelacja d z medianą sąsiadów; przebieg z_woda i z_rel dla
  VINEYARD_06; tabela sezonów zdarzeń.
- 13 winnic w promieniu kilku km: „sąsiedzi” dzielą pogodę i glebę, ale mogą też dzielić sposób uprawy (np. ten sam
  winiarz). Wspólna zmiana uprawy wielu winnic zniknie z z_rel.
- Mediana sąsiadów nie jest niezależna od winnicy przy wielu winnicach o podobnym przebiegu (W3b: r = 0,87).
- MAD z pierwszych lat (2 lata) jest niepewny; pierwsze lata testów mają słabszą skalę.
- Nawadnianie nieznane; brak pomiarów w winnicach. To nie jest walidacja stanu winorośli, tylko kalibracji
  i spójności wielkości.
- Lata testów to te same lata, które oglądaliśmy w T1 i flagach (wyżej). Potwierdzenie: sezon 2027.
