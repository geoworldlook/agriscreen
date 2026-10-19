# Plan W3b — „Moja winnica wobec jej historii” (wersja 5)

Status: **PROPOSED** 2026-10-19, do akceptacji przed kodem. Wersja 5 = wersja 4 po przeczytaniu w całości 4 prac
(Laroche-Pinel 2021, Unnisa 2025, Carletti 2025, Choi 2017). Literatura:
`docs/evidence/W3b_przeglad_literatury_woda_w_lisciach.md` (wersja 2). Rozwija W3b z Planu v9 §5b (D-073).

**Co zmieniła lektura:**
- Wskaźnik zostaje ten sam, ale uzasadniamy go fizyką, a nie wynikami z innych upraw.
- Doszło 5 doprecyzowań:
  - pas wewnętrzny 20 m w kodzie;
  - kontrola zmian gospodarowania;
  - T3 na czujniku po kontroli A4;
  - przeliczenie liczb z F4 bez wycieku przyszłych lat;
  - ostrożniejsze słowa na karcie.

## 1. Co dostaje rolnik

Karta „Moja winnica” z trzema zdaniami:

1. **Gleba w okolicy** (ERA5 + SWI, ~10 km): sucho / w normie / wilgotno wobec historii. *Już zwalidowane (W2 + REF).*
2. **Twoja działka — woda w liściach** (Sentinel-2, SWIR): poniżej / w normie / powyżej **swojej własnej historii**
   o tej porze roku. Obok: ile winnic w okolicy jest w tym samym stanie. Pod spodem przebieg bieżącego sezonu na tle
   linii ±1 oraz szczegół: NDMI, CRSWIR, zieleń (NDVI), chlorofil (NDRE).
3. **Czy to się zgadza z glebą:** jedno zdanie, pokazywane tylko wtedy, gdy test T3 potwierdzi związek, np.
   „porównujemy z wodą w glebie z ostatnich 30 dni”.

Czego karta nie mówi:
- „winorośl ma stres wodny”;
- „wczesne ostrzeżenie” (żadna praca nie pokazała wyprzedzenia);
- „winorośl reaguje po N dniach”.

Stała uwaga na karcie: „wskaźnik widzi całą działkę (winorośl, międzyrzędzie, glebę); spadek wody w liściach widać
raczej przy silniejszym niedoborze” (Ceccato 2001). Wydzielenie samej winorośli to następny etap (Plan v8).

## 2. Wskaźnik „woda w liściach”

| | Definicja | Uzasadnienie |
|---|---|---|
| **Składniki** | NDMI = (B8A − B11)/(B8A + B11); CRSWIR = B11 / [B8A + (B12 − B8A)·w] (wyższy = mniej wody, w złożeniu ze znakiem −); oba z natywnych pasm 20 m | fizyka: woda pochłania w SWIR, a NIR koryguje budowę liścia (Ceccato 2001: udział wody 36% → 87%). Wzory jak w FORDEAD (INRAE) i u Carletti 2025 |
| **Anomalia składnika** | z wobec własnej historii działki: ten sam tor orbity, ±15 dni roku, 5 wcześniejszych lat, z predykcyjne z rozkładu t (istniejące `scene_anomaly`) | metoda potoku, bez zmian |
| **Złożenie** | z_woda = (z_NDMI + z_−CRSWIR) / √(2·(1 + r)); r ustalone z góry w K1 (jedno, wspólne dla działek, z obcięciem), a nie liczone z kilku scen jednej działki | średnia przeskalowana do skali z |
| **Klasy** | z_woda ≤ −1 „poniżej swojej normy”; ≥ +1 „powyżej”; pomiędzy „w normie” | bez klas bezwzględnych (D-081) |

**Czego literatura nie daje (zapis uczciwości):**
- dowodu, że SWIR jest w winnicach lepszy od zieleni (Laroche-Pinel: pojedyncze wskaźniki słabe, NDII R² 0,09, NDVI
  0,04; Unnisa nie liczyła SWIR);
- liczb porównywalnych z naszymi, bo prace liczą wartości surowe z cyklem sezonowym.

Wskaźnik wybieramy z powodów fizycznych, a T1–T3 sprawdzą, czy daje coś ponad zieleń. NDMI i CRSWIR niosą prawie tę
samą informację (Carletti rys. 4a; nasze F4), więc złożenie daje odporność, a nie nową informację.

## 3. Testy: jedno zdanie, jeden test

| Zdanie na karcie | Test (zapisany przed liczeniem, K1) | Dane |
|---|---|---|
| 1. Gleba w okolicy | zrobione: R 0,52–0,68 wobec czujników na 3 stacjach | ERA5, SWI, ISMN, ICOS |
| 2. „Działka poniżej swojej normy” | **T1 kalibracja:** gdy gleba w okolicy jest w normie, „poniżej” zdarza się tak często, jak wynika z rozkładu t dla każdej sceny. Oczekiwaną częstość i tolerancję zapisujemy w K1 | archiwum S-2 na Dysku, ERA5 (2016–2026) |
| 2. „Zmiana od poprzedniej sceny” | **T2 szum:** najmniejsza wykrywalna zmiana osobno dla par „ten sam tor, 5 dni” i „różne tory, 1–3 dni”; pary z opadem między scenami oznaczone | archiwum S-2 na Dysku, opad ERA5 |
| 3. „Spójne z suszą w glebie” | **T3 związek z czujnikiem:** ρ Spearmana między medianą anomalii 14 winnic (bez VINEYARD_06) a średnią anomalią czujnika ISMN 20–30 cm z 30 dni przed sceną; VI–IX; czujnik po kontroli A4 (W1 główny, W2 i W3 obok); bootstrap po latach wspólny dla wszystkich działek | archiwum S-2, ISMN 2016–2024 |

**Doprecyzowania T1–T3 (zapisujemy w K1):**
1. **Jedno okno i jedne progi, bez zmian po wyniku.** Okno 30 dni to konwencja ustalona z góry; w F4 przewaga nad
   tym samym dniem była nieistotna.
2. **ρ łączne i ρ wewnątrz roku.** W F4 związek był głównie między latami (wewnątrz roku 0,30, średnie roczne 0,55).
3. **Raportujemy liczbę scen odniesienia i rodzaj normy** (ten sam tor lub awaryjnie wszystkie tory). T1 osobno dla
   obu rodzajów.
4. **Realna próba jest mała:** T3 ma sezony 2018–2024 (pełna norma 5 lat dopiero od 2021), a 15 winnic dzieli jedną
   pogodę i jeden czujnik.
5. **Tabela wrażliwości, tylko opisowa:**
   - ERA5 0–100 cm i SWI zamiast czujnika;
   - czujnik 10 cm na wspólnych dniach (dane do XI 2020);
   - okno wstecz 15 i 45 dni;
   - VI–VII i VIII–IX osobno;
   - wiersz kontrolny: ρ na wartościach surowych obok ρ na anomaliach. Pokazuje, ile daje sam cykl sezonowy.
6. **Naszego ρ nie zestawiamy z R² ani r z literatury.**
7. **Słaby T3 nie przekreśla potoku.** Możliwe przyczyny:
   - nieznany status nawadniania;
   - lata mokre;
   - czujnik punktowy pod trawą z artefaktami A4;
   - głębokie korzenie winorośli.

   Poprawność potoku sprawdzają T1, T2 i QC.
8. **Wartości „przed”:** liczby z F4 (r NDMI–CRSWIR 0,97, R z czujnikiem 0,41 i 0,47) były liczone z normą z przyszłych
   lat, na SR 2,5 m i z czujnikiem sprzed A4. W K3 przeliczamy je poprawnie (lata wcześniejsze, 20 m, po A4); dopiero
   to jest punkt odniesienia.

## 4. Kontrola jakości działki (K2)

| Reguła | Dlaczego |
|---|---|
| Pas wewnętrzny **20 m** ustawiony jawnie (dziś kod robi 1 piksel = 10 m, `step_04.site_stats`) | piksel SWIR (20 m) zapisany na siatce 10 m wystaje przy pasie 10 m nawet ok. 11 m poza działkę; przy 20 m najwyżej ok. 1 m. Laroche-Pinel zaleca co najmniej 5 m i dość pikseli w całości wewnątrz działki |
| Liczymy pełne piksele 20 m w zwężonym obrysie; próg minimalny i to, czy małe działki wchodzą do mediany, zapisujemy w K1 (propozycja: ≥ 10 pikseli) | po pasie 20 m dwie najmniejsze winnice (0,68–0,73 ha) mają ok. 3–4 piksele, VINEYARD_06 ok. 34 |
| Wyłączone awaryjne `all_touched` dla W3b | po cichu przywraca piksele brzegowe |
| ≥ 80% pikseli bez chmur w działce | jak w wersji 4 |
| **Zmiany gospodarowania w latach odniesienia:** trwała zmiana poziomu na jednej działce przy braku zmiany na pozostałych → przegląd obrazu RGB → wyłączenie tego roku z normy tej działki. Ciągły trend (np. VINEYARD_06) tylko jako zastrzeżenie. Próg w K1 | Unnisa i Carletti: zabiegi i zmiana gospodarowania dają anomalie niezwiązane z suszą. Nie wykrywamy po „niskim NDVI całego sezonu”, bo wypadłyby prawdziwe lata suche (2022) |
| Waga CRSWIR ujednolicona z FORDEAD | różnica 0,002 (inne środki pasm) |

## 5. Kroki

| Krok | Co | Sesje |
|---|---|---|
| **K1** | Protokół: wskaźnik (§2), T1–T3 i doprecyzowania (§3), progi QC (§4); skrót SHA-256 przed liczeniem | 1 |
| **K2** | Statystyki 15 winnic z archiwum na Dysku (414 scen, bez nowego pobierania) z regułami §4 | 1 |
| **K3** | Anomalie + T1–T3 w Colab; przeliczone wartości „przed” z F4; notatka wyników z tabelą wszystkich wskaźników; wiersze w karcie wyników | 1–2 |
| **K4** | Karta „Moja winnica” w dashboardzie, biuletynie i notatniku; przebieg sezonu na tle ±1; nagłówek gleby w 3 klasach | 1–2 |

Razem 4–6 sesji. Bieżące sceny dochodzą tym samym potokiem, więc karta działa w sezonie 2027 na bieżąco.

**Potem:** rozplątanie kanałów siecią neuronową (Plan v8, moduły 2–3), oceniane tymi samymi T1–T3 przed i po.
Wniosek dla Planu v8: Laroche-Pinel pokazuje, że więcej informacji dają pasma razem (B4, B6, B8A, B12) niż pojedyncze
wskaźniki. Rozplątanie musi więc objąć pasma SWIR (B8A, B11, B12), a nie tylko czerwień i NIR (dziś F5).

**Opcjonalnie, tylko po K3 i bez zmiany karty:**
- z dla wskaźnika red-edge (REP) i dla (B8A − B12)/(B8A + B12);
- norma harmoniczna działki jak w FORDEAD (tylko lata wcześniejsze, osobno dla torów).

**Świadomie poza planem:**
- model potencjału wodnego Laroche-Pinel;
- CWC z SL2P;
- test „woda przed zielenią”;
- kompozyty 8- i 16-dniowe;
- podział winnic według międzyrzędzia;
- temperatura liści (Copernicus: 1 km);
- dane spoza Copernicusa;
- mapa stref w działce;
- stacje ICOS w Sentinel-2;
- wgrywanie dowolnej działki.

## 6. Decyzje do zatwierdzenia

- **D-084 Dane:** archiwum S-2 z Dysku i obecny potok (jedno źródło dla historii i bieżących scen).
- **D-085 Wskaźnik i QC:**
  - „woda w liściach” = przeskalowana średnia anomalii NDMI i −CRSWIR, z r ustalonym w K1; klasy ±1;
  - NDMI, CRSWIR, NDVI, NDRE jako szczegół;
  - pas wewnętrzny 20 m, minimalna liczba pełnych pikseli 20 m, bez `all_touched`, ≥ 80% pikseli bez chmur;
  - kontrola zmian gospodarowania w latach odniesienia.
- **D-086 Walidacja:** T1–T3 z doprecyzowaniami z §3:
  - czujnik po A4;
  - ρ łączne i wewnątrz roku;
  - przeliczone wartości „przed” z F4;
  - zapisane i zahaszowane przed liczeniem.
- **D-087 Słowa:**
  - „woda w liściach działki (winorośl i międzyrzędzie)”;
  - nigdy „stres wodny winorośli” ani „wczesne ostrzeżenie”;
  - stała uwaga o silniejszym niedoborze;
  - nagłówek gleby w 3 klasach.

## 7. Źródła

Pełna lista, cytaty i strony: `docs/evidence/W3b_przeglad_literatury_woda_w_lisciach.md` (wersja 2). Najważniejsze:
- Ceccato i in. 2001 — fizyka SWIR + NIR;
- Laroche-Pinel i in. 2021 — winnice: pojedyncze wskaźniki słabe, pasma razem R² 0,40;
- Carletti i in. 2025 — FORDEAD, NDMI ≈ CRSWIR, zmiany gospodarowania;
- Unnisa i in. 2025 — brak wyprzedzenia, zabiegi;
- Choi i in. 2017 — kierunek zgodny z oknem T3, także na stacji Condom;
- dane własne F4 (do przeliczenia), Plan v7 (ustalenia 1 i 8), A4.
