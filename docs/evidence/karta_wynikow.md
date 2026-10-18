# Karta wyników warstwy wody (D-070)

Zasada: „przed” i „po” zawsze na tej samej referencji i w tym samym okresie; wynik „bez poprawy” też wpisujemy.
Źródła liczb: `docs/evidence/W2_REF_wyniki.md` (protokół D-083), `docs/evidence/W3a_SWI_1km_satelita.md` §0 pkt 8.

## Model ERA5-Land 0–100 cm wobec czujników w gruncie

| Zmiana | Referencja i okres | Przed | Po | Wniosek |
|---|---|---|---|---|
| **W2: kontrola czujników A4** (cenzurowanie W1) | ISMN Condom 20–30 cm, 2016–2024, anomalie klimatologiczne, ten sam protokół | W3 (bez A4): R 0,58 [0,50; 0,67], klasy 56%, FAR 0,46 | W1: R 0,57 [0,48; 0,65], klasy 55%, FAR 0,54 | brak poprawy R; referencja czystsza, liczby uczciwsze (bez artefaktów 0,01–0,05) |
| **REF: druga i trzecia stacja** | Auradé (ICOS 30 cm, 2019–2025), Lusignan (ICOS 20–30 cm, 2023–2026) | jedna stacja | R 0,57 [0,42; 0,70] Auradé; 0,68 [0,62; 0,74] Lusignan (35 d) | metoda działa poza Condom z podobną lub lepszą zgodnością |

## Satelita SWI v4 (T = 15) — nowy element (W3a)

| Miara | Wartość | Uwagi |
|---|---|---|
| Zgodność klas z ERA5, 2007–2024 | 63% [59; 68], kappa 0,44 | D-080 |
| R wobec czujników | 0,57 Condom, 0,52 Auradé, 0,53 Lusignan (35 d) | nie dokładniejszy od modelu; wartość: niezależne potwierdzenie |
| „ERA5 i SWI zgodnie suche” wobec samego ERA5 (POD/FAR) | do policzenia | test zapisany w W3a §5 |

## Kolejne wiersze

| Krok | Co porównamy |
|---|---|
| A5 | Brier prawdopodobieństwa i ρ na referencji po A4 (inne lata niż Brier) |
| W4 | błąd zmiany niedoboru w 7 dni wobec „bez zmian” |
| W5 | Brier „susza za 30 dni” wobec klimatologii i trwałości |
