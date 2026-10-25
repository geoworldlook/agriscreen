# Karta wyników warstwy wody (D-070)

Zasada: „przed” i „po” zawsze na tej samej referencji i w tym samym okresie; wynik „bez poprawy” też wpisujemy.
Źródła liczb: `docs/evidence/W2_REF_wyniki.md` (protokół D-083), `docs/evidence/W3a_SWI_1km_satelita.md` §0 pkt 8,
`W3b_wyniki.md`, `W3c_wyniki.md`, `W3d_wyniki.md`. Liczby sprawdzone niezależnym przeliczeniem z plików wynikowych
(audyt 2026-10-20); poprawki opisu po audycie są zaznaczone w notatkach wyników.

## Model ERA5-Land 0–100 cm wobec czujników w gruncie

| Zmiana | Referencja i okres | Przed | Po | Wniosek |
|---|---|---|---|---|
| **W2: kontrola czujników A4** (cenzurowanie W1) | ISMN Condom 20–30 cm, 2016–2024, anomalie klimatologiczne, ten sam protokół | W3 (bez A4): R 0,58 [0,50; 0,67], klasy 56%, FAR 0,46 | W1: R 0,57 [0,48; 0,65], klasy 55%, FAR 0,54 | brak poprawy R; referencja czystsza, liczby uczciwsze (bez artefaktów 0,01–0,05) |
| **REF: druga i trzecia stacja** | Auradé (ICOS 30 cm, 2019–2025), Lusignan (ICOS 20–30 cm, 2023–2026) | jedna stacja | R 0,57 [0,42; 0,70] Auradé; 0,68 [0,62; 0,74] Lusignan (35 d) | Auradé jak Condom (ta sama miara). Lusignan na innej mierze (anomalie 35-dniowe); na tej samej mierze Condom 0,41 [0,33; 0,48], przedziały rozłączne: zgodność zależy od stacji (przyczyny niesprawdzone) |

## Satelita SWI v4 (T = 15) — nowy element (W3a)

| Miara | Wartość | Uwagi |
|---|---|---|
| Zgodność klas z ERA5, 2007–2024 | 63% [59; 68], kappa 0,44 | D-080 |
| R wobec czujników | 0,57 Condom, 0,52 Auradé, 0,53 Lusignan (35 d) | nie dokładniejszy od modelu; wartość: niezależne potwierdzenie |
| „ERA5 i SWI zgodnie suche” wobec samego ERA5 (POD/FAR) | do policzenia | test zapisany w W3a §5 |

## Roślinność działki (W3b, protokół D-089; `docs/evidence/W3b_wyniki.md`)

| Zmiana | Referencja i okres | Przed | Po | Wniosek |
|---|---|---|---|---|
| Norma, czujnik i produkt (drabinka §9) | ISMN Condom 20–30 cm, IV–X 2018–2024, VINEYARD_06, te same 200 dni | NDMI R 0,57 (F4, norma z przyszłymi latami) | 0,44 → 0,54 → 0,52 (norma przyczynowa → A4 → 10 m z pasem 20 m) | krok a → b zmienia naraz normę (bez lat przyszłych), tor i z predykcyjne: spadek o 0,13 nie wynika z samego wycieku; A4 przywraca 0,11; wynik ~0,5 bez wycieku |
| Prosty wskaźnik wody (T3) | ISMN A4 W1, VI–IX 2018–2024, mediana 12 winnic, 140 dni | — | ρ 0,55 [−0,02; 1,00] | kryterium niespełnione: zdanie 3 ukryte; związek głównie między latami |
| Wariant 4 pasm (§7) | jw., lata niewidziane przez model | ρ prostego 0,55 | Δρ −0,01 [−0,18; 0,16] | nieprzyjęty; punkt odniesienia dla Planu v8 |
| Kalibracja z (T1, opisowo) | 13 winnic, VI–IX 2018–2026 | — (wcześniejsza liczba dotyczyła innej działki, okresu i produktu) | 28,0% [4,4; 51,7]; przy glebie w normie 14,1% [0; 29,6] | bez grubego rozkalibrowania (test słaby); po latach od 1% (2021) do 76% (2022). Po teście (poza protokołem): gleba sucha 46%, w normie 14%, wilgotna 7% scen |
| Szum (T2, opisowo) | pary scen bez opadu | — | MDC95 1,03 (ten sam tor) / 1,12 (różne tory) | próg „wyraźnej zmiany” na karcie; typowa różnica dwóch scen ok. 0,5 z |

## Strefa gorsza niż zwykle (W3c, protokół D-090; `docs/evidence/W3c_wyniki.md`)

| Zmiana | Referencja i okres | Przed | Po | Wniosek |
|---|---|---|---|---|
| Szum strefy (Z1) | pary scen bez opadu, 13 winnic, VI–IX 2019–2026, 689 par G5 | — | MDC95 NDVI 0,033 [0,025; 0,041], NDMI 0,023 [0,017; 0,029] | szum mały; NDVI < ½ zróżnicowania działki, NDMI nie |
| Mapa w zwykłe dni (Z2) | dni z glebą w normie, 741 scen 2019–2025 | oczekiwane ok. 1% | NDVI 15,4% [9,9; 20,9], NDMI 15,5% [10,3; 20,6] (po poprawce przedziału gleby do (30; 70) jak w protokole: 728 scen, 15,3% i 15,6%) | „zwykły układ” działek zmienia się między latami; warstwa nie przeszła (warunek 3), nie pokazujemy |

## Miejsce najniżej od 5 lat (W3d, protokół D-091; `docs/evidence/W3d_wyniki.md`)

| Zmiana | Referencja i okres | Przed | Po | Wniosek |
|---|---|---|---|---|
| Kalibracja klasy (D1) | miesiące VI–IX z glebą w normie: 12 winnic, 7 miesięcy w 4 latach (2020, 2021, 2023, 2025), 79 miesięcy winnic | oczekiwane 1,0 × przypadek | NDVI najniżej 0,49 [0; 1,92], najwyżej 1,16 [0; 3,23]; NDMI 0,55 [0; 2,32], 1,10 [0; 3,70] | nie potwierdzono ani nie wykluczono (w 2020 „najniżej” 3,1 ×); przedział za szeroki: nie pokazujemy |
| Kierunek (opisowo) | miesiące suche / wilgotne | — | suche: najniżej ok. 2,9 ×; wilgotne: najwyżej ok. 2,6–3,0 × | reakcja na wodę we właściwą stronę; sygnał głównie całych winnic |

## Winnica wobec sąsiadów (W3e, protokół D-092; `docs/evidence/W3e_wyniki.md`)

| Zmiana | Referencja i okres | Przed | Po | Wniosek |
|---|---|---|---|---|
| z_rel = (z_woda − mediana sąsiadów) / skala z lat wcześniejszych | 13 winnic, VI–IX 2020–2026, 1941 scen (te same dla obu) | z_woda: ≤ −1 w 31,1% scen; po latach 1–76%; sucho − wilgotno 49 pp | z_rel: 15,9% [8,9; 22,8]; po latach 5–24%; sucho − wilgotno 4 pp | H1–H3 spełnione: wspólna pogoda usunięta, kalibracja zgodna z 1 na 6 |
| Sygnał przesadzeń RPG (H4) | sezony winnic z kodem VRN / RVI | — | 2 z 5 zdarzeń mierzalne; ranga 0,81, p = 0,070 | niespełnione (za mało zdarzeń — wada planu); nie dodajemy do karty |

## Kolejne wiersze

| Krok | Co porównamy |
|---|---|
| A5 | Brier prawdopodobieństwa i ρ na referencji po A4 (inne lata niż Brier) |
| W4 | błąd zmiany niedoboru w 7 dni wobec „bez zmian” |
| W5 | Brier „susza za 30 dni” wobec klimatologii i trwałości |
