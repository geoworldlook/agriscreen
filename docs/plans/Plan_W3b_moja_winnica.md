# Plan W3b — „Moja winnica wobec jej historii” (wersja 5)

Status: **PROPOSED** 2026-10-19, do akceptacji przed kodem. Wersja 5 powstała po przeczytaniu w całości 4 prac
(Laroche-Pinel 2021, Unnisa 2025, Carletti 2025, Choi 2017) i po niezależnej weryfikacji liczb. Literatura:
`docs/evidence/W3b_przeglad_literatury_woda_w_lisciach.md` (wersja 2). Rozwija W3b z Planu v9 §5b (D-073) i zastępuje
tam opis obiektów, wskaźnika, klas i testu.

**Co zmieniła lektura:**
- Wskaźnik zostaje ten sam (NDMI + CRSWIR), ale uzasadnia go fizyka, a nie wyniki z innych upraw.
- Doprecyzowania:
  - pas wewnętrzny 20 m i minimalna wielkość działki;
  - flaga możliwej zmiany gospodarowania;
  - T3 na czujniku po kontroli A4, z jednym kryterium zapisanym z góry;
  - przeliczenie liczb z F4 bez wycieku przyszłych lat;
  - ostrożniejsze słowa na karcie.

## 1. Co dostaje rolnik

Karta „Moja winnica” z trzema zdaniami:

1. **Gleba w okolicy** (ERA5 + SWI, ~10 km): sucho / w normie / wilgotno wobec historii. Sprawdzone wobec czujników
   (W2 + REF): R 0,52–0,68; ta sama klasa w ok. 55% dni (kappa ok. 0,3).
2. **Twoja działka — wskaźnik wody w roślinności (SWIR)**: poniżej / w normie / powyżej **swojej własnej historii**
   o tej porze roku.
   - Obok: ile winnic w okolicy jest w tym samym stanie.
   - Pod spodem: przebieg bieżącego sezonu na tle linii ±1 oraz szczegół (NDMI, CRSWIR, zieleń NDVI, chlorofil NDRE).
3. **Okolica: roślinność a gleba** — jedno zdanie, pokazywane tylko gdy T3 spełni kryterium z K1, np. „W okolicy
   woda w roślinności winnic zwykle idzie w parze z wodą w glebie z ostatnich 30 dni; dla pojedynczej działki tego
   nie sprawdzaliśmy”.

**Stałe uwagi na karcie:**
- „Wskaźnik widzi całą działkę: winorośl, międzyrzędzie i glebę. Zmienia się zwykle razem z zielenią.”
- „Spadek wody w roślinności widać raczej przy silniejszym niedoborze” (nasz wniosek z badań na poziomie liścia,
  Ceccato 2001).

**Czego karta nie mówi:**
- „winorośl ma stres wodny”;
- „wczesne ostrzeżenie” (żadna z przeczytanych prac nie pokazała wyprzedzenia wobec gleby);
- „winorośl reaguje po N dniach”.

## 2. Wskaźnik

| | Definicja | Uzasadnienie |
|---|---|---|
| **Składniki** | NDMI = (B8A − B11)/(B8A + B11); CRSWIR = B11 / [B8A + (B12 − B8A)·w] (wyższy = mniej wody, w złożeniu ze znakiem −); oba z natywnych pasm 20 m | fizyka: woda pochłania w SWIR, a NIR koryguje budowę liścia (Ceccato 2001: udział wody 36% → 87%). Wzory jak w FORDEAD (INRAE) i u Carletti 2025 |
| **Anomalia składnika** | z wobec własnej historii działki (istniejące `scene_anomaly`): ten sam tor orbity, ±15 dni roku, 5 wcześniejszych lat, z predykcyjne, min. 5 scen odniesienia | metoda potoku, bez zmian |
| **Złożenie** | z_woda = (z_NDMI + z_−CRSWIR) / 2 | przy korelacji składników ≥ 0,9 skala różni się od z o mniej niż 3%, zachowawczo |
| **Klasy** | z_woda ≤ −1 „poniżej swojej normy”; ≥ +1 „powyżej”; pomiędzy „w normie” | bez klas bezwzględnych (D-081) |

**Czego literatura nie daje (zapis uczciwości):**
- dowodu, że SWIR jest w winnicach lepszy od zieleni. U Laroche-Pinel pojedyncze wskaźniki wypadły słabo (NDII R²
  0,09, NDVI 0,04), a Unnisa SWIR nie liczyła;
- liczb porównywalnych z naszymi. Laroche-Pinel, Choi i Unnisa liczą wartości surowe z cyklem sezonowym, a Carletti
  liczy anomalie, ale dla zamierania lasu.

Złożenie daje odporność, a nie nową informację, bo u nas anomalie NDMI i −CRSWIR korelowały na poziomie 0,97 (F4, do
przeliczenia).

## 3. Testy: jedno zdanie, jeden test

| Zdanie na karcie | Test (zapisany przed liczeniem, K1) | Dane |
|---|---|---|
| 1. Gleba w okolicy | zrobione (W2 + REF) | ERA5, SWI, ISMN, ICOS |
| 2. „Działka poniżej swojej normy” | **T1 kalibracja:** w całym archiwum (VI–IX) z_woda ≤ −1 w ok. 15,9% scen; tolerancja w K1. Wariant „gdy gleba w normie” tylko jednostronnie: nie częściej niż 15,9% | archiwum S-2 na Dysku (2016–2026), ERA5 |
| 2. „Zmiana od poprzedniej sceny” | **T2 szum:** najmniejsza wykrywalna zmiana osobno dla par „ten sam tor, 5 dni” i „różne tory, 1–3 dni”; pary z opadem między scenami oznaczone | archiwum S-2 na Dysku, opad ERA5 |
| 3. „Okolica: roślinność a gleba” | **T3:** ρ Spearmana między medianą anomalii winnic spełniających QC (bez VINEYARD_06, bo na niej w F4 wybierano okno) a średnią anomalią czujnika ISMN 20–30 cm z 30 dni przed sceną; VI–IX; czujnik po kontroli A4 (W1). **Kryterium zdania 3: dolna granica 95% CI ρ > 0** (bootstrap blokowy po latach) | archiwum S-2, ISMN 2016–2024 |

**Zapisujemy też w K1:**
1. **Okno 30 dni i progi są stałe, bez zmian po wyniku.** Okno to konwencja z F4 (przewaga nad tym samym dniem była
   nieistotna).
2. **Opisowo, w tej samej tabeli:**
   - ρ wewnątrz roku (w F4 związek był głównie między latami);
   - warianty A4 W2 i W3;
   - ERA5 i SWI zamiast czujnika;
   - wiersz kontrolny: ρ na wartościach surowych obok ρ na anomaliach. Pokazuje, ile daje sam cykl sezonowy;
   - T1–T3 dla NDVI. Przy ok. 7 sezonach nie oczekujemy rozstrzygnięcia, czy SWIR daje coś ponad zieleń; pokażemy
     tylko, czy wyniki są podobne.
3. **Liczba scen odniesienia i rodzaj normy** (ten sam tor lub awaryjnie wszystkie tory) przy każdej scenie.
4. **Mała próba.** T3 ma w pełni sezony 2019–2024, a 2018 tylko częściowo (ok. połowa scen, norma ze wszystkich
   torów). Przedziały ufności są więc orientacyjne.
5. **Naszego ρ nie zestawiamy z R² ani r z literatury.**
6. **Słaby T3 nie przekreśla potoku.** Możliwe przyczyny:
   - nieznany status nawadniania;
   - lata mokre;
   - czujnik punktowy pod trawą z artefaktami A4;
   - głębokie korzenie winorośli.

   Poprawność potoku sprawdzają T1, T2 i QC.
7. **Wartości „przed”:** liczby z F4 (korelacja NDMI–CRSWIR 0,97, R z czujnikiem 0,41 i 0,47) liczono z normą
   z przyszłych lat, na SR 2,5 m i z czujnikiem sprzed A4. W K3 przeliczamy je poprawnie; dopiero to jest punkt
   odniesienia.

## 4. Kontrola jakości działki (K2)

| Reguła | Dlaczego |
|---|---|
| Pas wewnętrzny **20 m** (dziś kod zwęża o 1 piksel = 10 m, `step_04.site_stats`) | piksel SWIR 20 m zapisany na siatce 10 m wystaje przy pasie 10 m nawet ok. 11 m poza działkę, przy 20 m najwyżej ok. 1 m. Laroche-Pinel zaleca co najmniej 5 m i dość pikseli wewnątrz działki |
| Działka liczona, gdy w zwężonym obrysie jest **≥ 40 pikseli 10 m** (ok. 10 pikseli 20 m) | spełnia to 13 z 15 winnic. Dwie najmniejsze (0,68 i 0,73 ha, 16 i 19 pikseli) dostają na karcie „działka za mała na wiarygodną anomalię”. VINEYARD_06 ma 141 pikseli |
| ≥ 90% pikseli bez chmur w działce | próg potoku (`VEG_MIN_CLEAR_FRAC`), bez zmian |
| **Flaga „możliwa zmiana gospodarowania”:** gdy działka na tle mediany pozostałych winnic jest przez cały sezon ≤ −1 lub ≥ +1, karta dopisuje „porównanie z historią mniej pewne”. Normy nie zmieniamy | Unnisa i Carletti: zabiegi i zmiana gospodarowania dają anomalie niezwiązane z suszą. Flaga nie wyłącza lat suchych, bo w suszy niżej są wszystkie winnice naraz |

W K2 dodatkowo: ujednolicić stałą CRSWIR z FORDEAD (różnica wagi 0,002, kosmetyka).

## 5. Kroki

| Krok | Co | Sesje |
|---|---|---|
| **K1** | Protokół: wskaźnik (§2), T1–T3 z kryterium (§3), progi QC (§4); skrót SHA-256 przed liczeniem | 1 |
| **K2** | Statystyki 15 winnic z archiwum na Dysku (414 scen, bez nowego pobierania) z regułami §4 | 1 |
| **K3** | Anomalie + T1–T3 w Colab; przeliczone wartości „przed” z F4; notatka wyników; wiersze w karcie wyników | 1–2 |
| **K4** | Karta „Moja winnica” w dashboardzie, biuletynie i notatniku; nagłówek gleby w 3 klasach | 1–2 |

Razem 4–6 sesji. Bieżące sceny dochodzą tym samym potokiem, więc karta działa w sezonie 2027 na bieżąco.

**Potem:** rozplątanie sygnału winnicy (Plan v8, F5), oceniane tymi samymi T1–T3 przed i po. Wniosek z Laroche-Pinel
dla F5 (więcej informacji w kilku pasmach razem, w tym SWIR) jest zapisany w Planie v8.

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
- wgrywanie dowolnej działki;
- wskaźnik red-edge (REP), (B8A − B12)/(B8A + B12), norma harmoniczna jak w FORDEAD — ewentualnie później,
  eksploracyjnie.

## 6. Decyzje do zatwierdzenia

- **D-084 Dane:** archiwum S-2 z Dysku i obecny potok (jedno źródło dla historii i bieżących scen).
- **D-085 Wskaźnik i QC:**
  - wskaźnik wody w roślinności = średnia anomalii NDMI i −CRSWIR, klasy ±1;
  - NDMI, CRSWIR, NDVI, NDRE jako szczegół;
  - pas wewnętrzny 20 m, ≥ 40 pikseli 10 m w zwężonym obrysie, ≥ 90% pikseli bez chmur;
  - flaga możliwej zmiany gospodarowania.
- **D-086 Walidacja:** T1–T3 jak w §3:
  - czujnik po A4;
  - jedno kryterium zdania 3 (dolna granica 95% CI ρ > 0);
  - reszta opisowo;
  - przeliczone wartości „przed” z F4;
  - zapisane i zahaszowane przed liczeniem.
- **D-087 Słowa:**
  - „wskaźnik wody w roślinności działki (SWIR; winorośl i międzyrzędzie)”;
  - nigdy „stres wodny winorośli” ani „wczesne ostrzeżenie”;
  - zdanie 3 tylko na poziomie okolicy;
  - nagłówek gleby w 3 klasach.

## 7. Źródła

Pełna lista, cytaty i strony: `docs/evidence/W3b_przeglad_literatury_woda_w_lisciach.md` (wersja 2). Najważniejsze:
- Ceccato i in. 2001 — fizyka SWIR + NIR;
- Laroche-Pinel i in. 2021 — winnice: pojedyncze wskaźniki słabe, pasma razem R² 0,40;
- Carletti i in. 2025 — FORDEAD, wzór CRSWIR, zmiany gospodarowania;
- Unnisa i in. 2025 — brak wyprzedzenia, zabiegi;
- Choi i in. 2017 — kierunek zgodny z oknem T3, także na stacji Condom;
- dane własne F4 (do przeliczenia), Plan v7 (ustalenia 1 i 8), A4.
