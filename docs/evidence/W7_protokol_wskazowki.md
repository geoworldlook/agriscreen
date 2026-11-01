# W7 — protokół „Wskazówki AgriScreen potwierdzone pomiarami” (pre-rejestracja)

> **Status:** `DRAFT` 2026-11-01 — czeka na akceptację autora. Po akceptacji: `REGISTERED` (D-093) i SHA-256 sekcji
> 0–9 (`sed -n '/^## 0\./,$p' docs/evidence/W7_protokol_wskazowki.md | sha256sum`).
> - Plan: `docs/plans/Plan_v10_wskazowki_potwierdzone.md`.
> - **Pytanie:** czy wskazówki z panelu („sucho w okolicy”, „roślinność poniżej swojej normy”, przymrozek, upał)
>   trafiają częściej niż przypadek, sprawdzone na rzeczywistych pomiarach naziemnych? Nie sprawdzamy dokładności
>   wilgotności gleby ani stanu wody w winorośli, tylko trafność wskazówki.
> - **Zasada danych:** prawda = wyłącznie wartości zmierzone i oficjalne rejestry. Wartości uzupełnione (z modelu
>   ERA albo metodą MDS) nie są prawdą. Dane syntetyczne nie wchodzą do żadnego wyniku.
> - **Jawnie, co znaliśmy przed rejestracją:** W2/REF (R anomalii gleby: Condom 0,57, Auradé 0,57, Lusignan 0,68),
>   W3b T3 (roślinność 12 winnic a czujnik Condom: ρ 0,55 [−0,02; 1,00]), walidacja pogody w Condom (opad 30 dni
>   R 0,90; progi przymrozku i upału). Nie liczyliśmy dotąd trafień w formie §4, niczego na stacjach Bil, Fon, Gri,
>   Hes, Lam, Mej, Pue i Tou. Przed rejestracją pobrano plik FR-Bil L2 Fluxnet; odczytano tylko nagłówek kolumn.
> - **Literatura (podstawa wyborów):** walidacja produktów gleby wobec sieci czujników i klasy suchości (Gruber
>   i in. 2020, Remote Sensing of Environment 244:111806); parowanie i wymiana CO₂ z wież eddy covariance jako
>   prawda dla roślinności (Pastorello i in. 2020, Scientific Data 7:225 — format FLUXNET, znaczniki QC); wskaźniki
>   SWIR a stan wody roślin (Plan W3b §2; FORDEAD); normy „bez roku ocenianego” (leave-one-year-out) przy krótkich
>   seriach.

## 0. Stacje i dane

**Stacje (reguła ustalona 2026-11-01, przed liczeniem):** wszystkie stacje ekosystemowe ICOS we Francji, które mają
produkt „ETC L2 Fluxnet (half-hourly)”, oraz czujnik ISMN SMOSMANIA Condom i stacje Météo-France z `task_weather`.
Typ ekosystemu z metadanych ICOS.

| Stacja | Ekosystem (ICOS) | Od Condom | L2 Fluxnet | Testy |
|---|---|---|---|---|
| FR-Aur Auradé | uprawy | 74 km | 2019–2025 | gleba, pogoda |
| FR-Lam Lamasquère | uprawy | 86 km | 2020–2024 | gleba, pogoda |
| FR-Tou Toulouse | łąka | 91 km | 2018–2025 | gleba, roślinność, pogoda |
| FR-Bil Bilos | las iglasty | 121 km | 2019–2026 | gleba, roślinność, pogoda |
| FR-Pue Puéchabon | las liściasty zimozielony | 260 km | 2021–2026 | gleba, roślinność, pogoda |
| FR-Lus Lusignan | łąka | 274 km | 2022–2026 | gleba, roślinność, pogoda |
| FR-Mej Méjusseaume | łąka | 492 km | 2019–2025 | gleba, roślinność, pogoda |
| FR-Fon Fontainebleau | las liściasty | 535 km | 2019–2026 | gleba, roślinność, pogoda |
| FR-Gri Grignon | uprawy | 557 km | 2021–2026 | gleba, pogoda |
| FR-Hes Hesse | las liściasty | 734 km | 2022–2026 | gleba, roślinność, pogoda |
| ISMN Condom | przy winnicach (136 m od VINEYARD_06) | 0 km | czujnik 2016–2024 | gleba |
| Météo-France (CONDOM i 2 stacje obok) | — | 0–18 km | dobowe | pogoda |

- Uprawy polowe nie wchodzą do testu roślinności: zmiana uprawy co roku psuje porównanie z własną historią.
- Lata w tabeli to zakres pliku L2; dni bez pomiaru odpadają według §1.

**Dane i pochodzenie:** ICOS L2 Fluxnet (półgodzinne) i L2 Meteo (+ NRT po końcu L2, tylko do monitoringu §8),
licencja CC BY 4.0; ISMN A4 W1 (jak W3b); Météo-France dobowe (jak `weather.py`); Sentinel-2 L2A i ERA5-Land jak
w produkcie. Każdy pobrany plik ma wiersz w `data/09_Reference_Stations/MANIFEST_W7.csv` (Dysk): adres lub
identyfikator obiektu, data pobrania, SHA-256, licencja.

**Okres i zamrożenie:** `W7_FREEZE = 2026-09-30`. Testy (§5) tylko na dniach ≤ tej daty. Gleba i pogoda: miesiące
IV–X (sezon winorośli, `S2_MONTHS`); przymrozek w `FROST_SEASON`, upał w `HEAT_SEASON`; roślinność: sceny VI–IX
(`PARCEL_TEST_MONTHS`, jak W3b).

**Przedział 95%:** jackknife po latach (`parcel.jackknife_ci`), łącznie dla wszystkich stacji: usuwamy cały rok
ze wszystkich stacji naraz (rok suchy działa na wszystkie stacje jednocześnie).

## 1. Prawda z pomiarów (tylko wartości zmierzone)

- **Gleba:** wilgotność gleby z ICOS L2 Meteo po regułach jakości W2/REF §2 (zakres 0–0,60, FAST_DROP,
  ≥ 24 półgodzin na dobę); warstwa 0–100 cm ważona miąższością (`reference.profile_series`), głębokości z plików
  VARINFO_METEO stacji. Condom: ISMN A4 W1, 20–30 cm (jak W3b).
- **Roślinność (parowanie):** `LE_F_MDS` tylko w półgodzinach z `LE_F_MDS_QC = 0` (pomiar), tylko w dzień
  (`SW_IN_POT > 0`). Doba ważna, gdy zmierzono ≥ 70% półgodzin dziennych; wartość doby = średnia zmierzonych.
- **Pogoda:** opad `P` (pomiar; nie `P_ERA` ani `P_F`), doba ważna tylko przy 48/48 półgodzinach; temperatura
  `TA_F_MDS` z `TA_F_MDS_QC = 0`, doba ważna przy ≥ 44/48, Tmin i Tmax z tych półgodzin. Météo-France: `rr`, `tn`,
  `tx` z filtrem jakości `weather.py`.
- **Opisowo (nie prawda główna):** `GPP_NT_VUT_REF` (fotosynteza wyliczona z pomiaru NEE, gdy `NEE_VUT_REF_QC = 0`
  w ≥ 70% półgodzin dziennych) i udział parowania w energii EF = LE/(LE+H) w godzinach 11–15.

## 2. Norma pomiaru (bez roku ocenianego)

- Dla stacji, zmiennej i dnia d roku y: norma = mediana wartości z **innych lat** (≠ y), z dni w oknie ±15 dni
  kalendarzowych wokół d. Wymagane ≥ 2 inne lata i ≥ 20 wartości; inaczej dzień odpada.
- Gleba: wartość z dnia d wobec normy. Roślinność: średnia z okna [t−3, t+3] wokół dnia sceny t (≥ 5 ważnych dób)
  wobec mediany takich średnich z innych lat. Przymrozek: zmierzona Tmin ≤ 0 °C; upał: zmierzona Tmax ≥ 35 °C.
- Zdarzenie „poniżej normy”: wartość < norma; „powyżej normy”: wartość > norma.

## 3. Wskazówki produktu (dokładnie jak w panelu)

- **G-sucho / G-mokro:** percentyl ERA5-Land 0–100 cm wobec 1991–2020 (±15 dni) w punkcie stacji ≤ 30 / ≥ 70
  (`SWI_DRY_PCT`, `WATER_WET_PCT`, jak karta).
- **R-poniżej / R-powyżej:** z_woda ≤ −1 / ≥ +1 (W3b §2–3, `parcel.water_index`), liczone dla kwadratu
  300 × 300 m o środku w położeniu wieży (metadane ICOS), bez pasa 20 m od brzegu (`PARCEL_INNER_M`), z regułami
  produktu: ≥ 40 pikseli (`PARCEL_MIN_PX`), scena czysta ≥ 90% (`VEG_MIN_CLEAR_FRAC`), jedna scena na dzień,
  norma przyczynowa z lat wcześniejszych (`metrics.scene_anomaly`).
- **P-przymrozek / P-upał:** ERA5-Land w punkcie stacji: Tmin ≤ `FROST_TMIN` (0 °C) w `FROST_SEASON`;
  Tmax ≥ `HEAT_TMAX` (35 °C) w `HEAT_SEASON` (progi nominalne produktu; w Condom progi z panelu).
- Kod i parametry produktu bez zmian. Zmiana któregokolwiek = nowa wersja protokołu.

## 4. Miara: trafienie wobec przypadku

- Trafność p = udział dni ze wskazówką, w których zaszło zdarzenie z pomiaru (G-sucho → gleba poniżej normy;
  G-mokro → powyżej; R-poniżej → parowanie poniżej normy; R-powyżej → powyżej; P-przymrozek → zmierzony
  przymrozek; P-upał → zmierzony upał).
- Przypadek b = udział tego zdarzenia we **wszystkich** ocenianych dniach tych samych stacji i okresu.
- Przewaga Δ = p − b (i iloraz p/b) z przedziałem jackknife po latach (§0).

## 5. Testy rozstrzygające i kryteria

| Test | Wskazówka | Zbiór | Kryterium |
|---|---|---|---|
| **K1** | G-sucho | gleba: 10 stacji ICOS + ISMN Condom, IV–X ≤ zamrożenia | dolna granica Δ > 0 **i** p ≥ 0,60 |
| **K2** | R-poniżej | roślinność: 7 stacji bez upraw, sceny VI–IX ≤ zamrożenia | dolna granica Δ > 0 **i** p ≥ 0,60 |

- p ≥ 0,60 to próg praktyczny: wskazówka ma się potwierdzać co najmniej w 6 na 10 przypadków.
- Minimum: ≥ 30 dni (K1) / ≥ 30 scen (K2) ze wskazówką i ≥ 3 lata; inaczej „za mało danych” (niepotwierdzone).
- Dwa testy rozstrzygające, każdy na poziomie 95%. Żaden wiersz z §6 nie zmienia werdyktu.

## 6. Opisowo (bez wpływu na werdykt)

- G-mokro, R-powyżej, P-przymrozek i P-upał (trafność, POD, FAR), wyniki każdej stacji osobno, osobny wiersz Condom.
- ρ Spearmana z_woda a anomalia parowania: wewnątrz sezonu i między sezonami; GPP i EF zamiast parowania;
  kwadrat 200 i 500 m zamiast 300 m.
- **Winnice w Gers (oficjalny rejestr):** plon wina hl/ha = produkcja / powierzchnia w produkcji, departament Gers,
  deklaracje celne (douane, open data), lata 2017–2025, wobec mediany z_woda 13 winnic w VI–IX. Tylko ρ, bez
  kryterium (9 lat; plon zależy też od przymrozków, gradu i chorób).

## 7. Co pokazujemy

- K1, K2 spełnione: zdanie w panelu („How far to trust it”), w README i na stronie, np. „Gdy AgriScreen mówi
  »sucho«, czujniki gleby na 11 stanowiskach potwierdziły to w p% dni (przypadkiem b%)”, status `confirmed (W7)`.
- Niespełnione: ten sam wiersz z liczbami i statusem `not confirmed`. Wynik negatywny pokazujemy tak samo.
- Zawsze z granicą: wieże nie stoją w winnicach; K2 potwierdza metodę na lasach i łąkach, nie stan wody winorośli.

## 8. Monitoring po zamrożeniu

- Po zamrożeniu te same obliczenia co tydzień na nowych danych (ICOS NRT, Météo-France) jako „historia trafień”
  w panelu, osobno od werdyktu. Parowanie z NRT tylko tam, gdzie produkt bieżący ma pomiar LE ze znacznikiem
  jakości; inaczej czekamy na L2.
- Sezon 2027: te same reguły na latach niewidzianych (potwierdzenie).

## 9. Ograniczenia znane przed liczeniem

- Żadna wieża nie stoi w winnicy; las i łąka reagują na wodę inaczej niż winorośl w rzędach z międzyrzędziami.
- Zasięg pomiaru wieży zmienia się z wiatrem; kwadrat 300 m jest stały. Komórka ERA5-Land (ok. 9 km) a punkt.
- Krótkie serie (Lus, Hes: 5 lat; Pue: 6) dają niepewną normę; wynik łączny ważą stacje z dłuższą serią.
- Gospodarka na stacjach (koszenie i wypas na łąkach, trzebieże w lesie) może zmieniać roślinność niezależnie
  od wody. FR-Tou: łąka przy Tuluzie, nawadnianie nieznane — zostaje w zbiorze (reguła), opis per stacja.
- ISMN Condom kończy się na 2024 r.; parowanie tylko w dzień; przymrozków i upałów jest mało (opisowo).
