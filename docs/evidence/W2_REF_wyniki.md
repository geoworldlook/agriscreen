# W2 + REF — wyniki pierwszego przebiegu (dane do 2026-10-16)

> **Status:** wynik protokołu `docs/evidence/W2_REF_protokol_walidacji.md` (D-083, SHA-256 `e2a1503a…`), bez zmian
> protokołu po rejestracji. Przebieg w Colab, commit z wynikami `25b3a99`; tabela pełna: `validation_reference.csv`
> w `data/05_Final_Outputs/agriwatch/` na Dysku. Reguły A4: D-060–D-063 (SHA-256 sekcji 3–4 `e69a6f99…`).

## Wynik w skrócie

1. **Model ERA5-Land (kategoria karty) zgadza się z czujnikami w gruncie umiarkowanie i podobnie na trzech stacjach:**
   R anomalii 0,57 [0,48; 0,65] w Condom, 0,57 [0,42; 0,70] w Auradé i 0,68 [0,62; 0,74] w Lusignan (tam: anomalie
   35-dniowe). Metoda nie jest dopasowana do jednej stacji.
2. **Kategoria jest mniej pewna niż anomalia.** Ta sama klasa (sucho / norma / wilgotno) co czujnik: 55% dni
   (kappa 0,31–0,32) w Condom i Auradé. Suchą dekadę modelu czujnik potwierdza w około połowie przypadków
   (46% Condom, 48% Auradé).
3. **Satelita (SWI v4, T = 15) nie jest dokładniejszy od modelu:** R 0,57 / 0,52 / 0,53. Jego wartością jest
   niezależność od modelu, nie większa trafność.
4. **A4:** cenzurowanie (W1) prawie nie zmienia R wobec referencji bez nowej kontroli (0,57 wobec 0,58). Wykluczenie
   dni oznaczonych (W2) obniża R do 0,48 i POD do 0,34 — tak, jak przewidziała notatka A4 (usuwa suche epizody).
5. **Rozbieżność, którą zapisujemy wprost:** na anomaliach 35-dniowych model zgadza się z Lusignan znacznie lepiej
   niż z Condom — 0,68 [0,62; 0,74] wobec 0,41 [0,33; 0,48]; przedziały ufności są rozłączne. Możliwe przyczyny
   (niesprawdzone): pojedynczy czujnik w pęczniejącej glinie (Condom) wobec średniej z 4 profili (Lusignan), inna
   gleba, inna skala porównania.

## 1. Miara główna każdego miejsca (protokół §4)

| Miejsce, warstwa | Produkt | R [95% CI] | ρ [95% CI] | n dni | Ta sama klasa | kappa | POD | FAR |
|---|---|---|---|---|---|---|---|---|
| Condom, ISMN 20–30 cm po A4 (W1), anomalie klimatologiczne 2016–2024 | ERA5-Land 0–100 cm | 0,57 [0,48; 0,65] | 0,61 [0,51; 0,69] | 2924 | 55% | 0,31 | 0,58 | 0,54 |
| | SWI T = 15 | 0,57 [0,48; 0,64] | 0,59 [0,50; 0,66] | 2835 | 52% | 0,25 | 0,53 | 0,57 |
| Auradé, ICOS 30 cm, anomalie klimatologiczne 2019–2025 | ERA5-Land 0–100 cm | 0,57 [0,42; 0,70] | 0,57 [0,41; 0,70] | 2003 | 55% | 0,32 | 0,65 | 0,52 |
| | SWI T = 15 | 0,52 [0,39; 0,63] | 0,53 [0,39; 0,65] | 1890 | 49% | 0,22 | 0,45 | 0,56 |
| Lusignan, ICOS 20–30 cm, anomalie 35-dniowe 2023–2026 | ERA5-Land 0–100 cm | 0,68 [0,62; 0,74] | 0,73 [0,68; 0,77] | 1342 | 65%* | 0,47* | 0,50* | 0,62* |
| | SWI T = 15 | 0,53 [0,42; 0,63] | 0,50 [0,39; 0,60] | 1294 | 60%* | 0,38* | 0,44* | 0,70* |

\* Lusignan: klasy i dekady liczone wobec 4-letniej normy czujników — wg protokołu tylko orientacyjnie.

## 2. Kontrola czujników A4 (Condom; ERA5-Land, anomalie klimatologiczne)

| Wariant | R [95% CI] | ρ | n | Ta sama klasa | kappa | POD | FAR | SWI T = 15: R |
|---|---|---|---|---|---|---|---|---|
| **W1 cenzurowanie (główny)** | 0,57 [0,48; 0,65] | 0,61 | 2924 | 55% | 0,31 | 0,58 | 0,54 | 0,57 |
| W2 wykluczenie | 0,48 [0,35; 0,58] | 0,46 | 1934 | 48% | 0,21 | 0,34 | 0,56 | 0,51 |
| W3 bez nowej kontroli | 0,58 [0,50; 0,67] | 0,60 | 2976 | 56% | 0,34 | 0,53 | 0,46 | 0,55 |
| W1, próg 0,5·WP | 0,53 [0,42; 0,62] | 0,57 | 2924 | 52% | 0,26 | 0,58 | 0,61 | 0,54 |
| W1, próg 0,15 | 0,52 [0,42; 0,61] | 0,56 | 2924 | 50% | 0,24 | 0,55 | 0,65 | 0,53 |

- Dni oznaczone 2016–2024: 20 cm — FAST_DROP 38, średnia < 0,10: 784; 30 cm — FAST_DROP 26, < 0,10: 931.
- Interpretacja: artefakty utraty kontaktu przypadają głównie na okresy rzeczywiście suche, więc ich ranga (najsuchsze
  dni) zostaje taka sama przy cenzurowaniu — stąd R prawie bez zmian. FAR w W1 jest wyższy niż w W3 (0,54 wobec
  0,46): podniesienie artefaktów do θ_dno osłabia część suchych dekad czujnika. Wynik wpisany bez wybierania wariantu.

## 3. Wrażliwość (protokół §1, §3)

- **T satelity:** R dla T = 10 / 15 / 40 — Condom 0,58 / 0,57 / 0,49; Auradé 0,52 / 0,52 / 0,51; Lusignan
  0,58 / 0,53 / 0,41. T = 10 jest nieznacznie lepsze w dwóch miejscach, w granicach przedziałów ufności. T = 15 zostaje:
  ustalono je przed wynikiem, a zmiana teraz byłaby dopasowaniem do stacji.
- **Warstwa 0–1 m (ważona):** ERA5 wobec Auradé 0,54 [0,35; 0,70]; wobec Lusignan 0,76 [0,70; 0,82] (anomalie 35 dni).
- **Auradé od zmiany czujnika (2020-10-19):** w `validation_reference.csv`; w raporcie od następnego przebiegu.

## 4. Przenośność metody (protokół §5)

- Condom i Auradé (ta sama miara, ten sam region): przedziały się pokrywają — wynik spójny.
- Condom i Lusignan: miary główne różne. Na tej samej mierze (anomalie 35-dniowe) przedziały są rozłączne
  (pkt 5 w skrócie). To ograniczenie, nie dowód przeciw metodzie: lepsza zgodność występuje na stacji z lepszą
  referencją (4 profile). Tabela tej samej miary we wszystkich miejscach jest w raporcie od następnego przebiegu.

## 5. Kontrola bieżąca Lusignan (protokół §6, 2026-10-16)

Czujnik 20–30 cm: anomalia 35-dniowa +0,006 m³/m³ (lekko wilgotniej niż w ostatnich tygodniach). SWI wobec normy
2007–2024: T = 15 sucho (percentyl 15), T = 10 norma (30), T = 40 sucho (1). ERA5 nie był porównany, bo kończył się
6 dni wcześniej — poprawione: każdy produkt porównujemy w ostatnim wspólnym dniu z czujnikiem.

## 6. Co zmienia się na karcie

„Na ile ufać” podaje teraz model i satelitę wobec czujników na trzech stacjach (miara główna z protokołu) zamiast
jednego wiersza z Condom sprzed kontroli A4. Wcześniejsza liczba „czujnik potwierdzał suchą dekadę w 43%” pochodziła
ze statusu i referencji bez A4; po protokole: 46% (Condom) i 48% (Auradé). Prawdopodobieństwo na karcie (ρ = 0,58)
zostaje oznaczone „w rewizji” do kroku A5.

## 7. Ograniczenia i następne kroki

- Łąka i pole uprawne to nie winnica; Lusignan ma pełne lata dopiero od 2023 r.; Condom — dane ISMN do 2024 r.
- Test zapisany 2026-10-14 w notatce W3a §5: czy reguła „ERA5 i SWI zgodnie suche” wykrywa suche dekady lepiej niż sam
  ERA5 (POD/FAR na tej samej referencji, bootstrap po sezonach).
- A5: ponowne oszacowanie ρ i Brier prawdopodobieństwa na referencji po A4, na innych latach niż Brier.
