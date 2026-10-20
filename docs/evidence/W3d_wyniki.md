# W3d — wyniki: „miejsce najniżej od 5 lat” (pierwszy przebieg, 2026-10-20)

> Protokół: `docs/evidence/W3d_protokol_miesiace.md`, zarejestrowany 2026-10-20 (D-091), SHA-256
> `599a381bb6d15dfe9fa81186a34436815d2d0ea01970828a5aa90730ff6da30a` — ten sam skrót w `w3d_tests.csv`.
> Dane: archiwum projektu, 419 scen, zamrożenie 2026-10-18 (`w3d_freeze.json`, ta sama lista scen co W3b i W3c,
> SHA-256 `96d70cb4…`); 13 winnic z QC; żadna scena nie wypadła. Kod `ddf26dd` (oznaczenie `+dirty` pochodzi od
> zapisanego w Colab notatnika — kolejny commit, c3783a3, zmienia tylko notatnik).

## Wynik w jednym zdaniu

**Warstwa „Months” nie przeszła kryterium (§5) dla NDVI ani NDMI i nie trafia do panelu.** W zwykłe miesiące
klasa „najniżej od 5 lat” wypada średnio rzadziej niż przypadkiem (0,5 razy), ale w jednym z czterech lat (2020)
ponad 3 razy częściej. Miesięcy z glebą w normie jest za mało (7 miesięcy w 4 latach), więc przedział jest bardzo
szeroki: kalibracji nie potwierdzamy ani nie wykluczamy.

## Liczby (zgodnie z protokołem)

Iloraz = jak często klasa wypada / jak często wypadałaby przypadkiem (1/(N + 1), ok. 17%). 1 = dokładnie jak
przypadek.

| Miesiące VI–IX | NDVI „najniżej” | NDVI „najwyżej” | NDMI „najniżej” | NDMI „najwyżej” |
|---|---|---|---|---|
| **gleba w normie** (79 miesięcy winnic: 12 winnic, 7 miesięcy w latach 2020, 2021, 2023, 2025) — podstawa kryterium | **0,49** [0; 1,92] | **1,16** [0; 3,23] | **0,55** [0; 2,32] | **1,10** [0; 3,70] |
| gleba sucha (< 30; 114) | 2,88 [1,22; 4,54] | 0,05 [0; 0,17] | 2,96 [0,86; 5,06] | 0,01 [0; 0,04] |
| gleba wilgotna (> 70; 88) | 0,30 [0; 1,10] | 3,02 [1,05; 4,99] | 0,28 [0; 1,11] | 2,62 [0,88; 4,37] |
| wszystkie (281) | 1,40 [0; 3,00] | 1,28 [0; 2,66] | 1,45 [0; 3,17] | 1,13 [0; 2,41] |
| **Kryterium:** górna granica ≤ 1,5 dla obu klas | **niespełnione** (1,92; 3,23) | | **niespełnione** (2,32; 3,70) | |

Opisowo (§6): „najniżej” po latach (NDVI): 2020 3,1; 2021 0,4; 2022 3,3; 2023 0,0; 2024 0,6; 2025 0,1;
2026 3,5. Udział powierzchni w plamach przy glebie w normie: „najniżej” 9% (NDVI) i 10% (NDMI), „najwyżej” 20% i 19%.

## Co to znaczy (prosto)

- **Kierunek się zgadza.** W suchych miesiącach „najniżej od 5 lat” wypada prawie 3 razy częściej niż przypadkiem,
  a „najwyżej” prawie nigdy; w wilgotnych odwrotnie. Satelita reaguje na wodę tak, jak powinien.
- **W zwykłe miesiące średnio:** „najniżej” 0,5 razy przypadek, „najwyżej” 1,1 razy. Po latach jednak od 0 do
  ok. 3–4 razy: „najniżej” NDVI 2020 3,1, 2021 0,0, 2023 0,0, 2025 0,2; „najwyżej” 2020 0,0, 2021 3,6, 2023 1,5,
  2025 0,4. Całe lata przesuwają się razem.
- **Cztery lata to za mało, żeby ocenić kalibrację.** Miesięcy z glebą w normie jest 7 (VIII 2020, VII 2021,
  VII–VIII 2023, VI–VIII 2025), a cała okolica zmienia się razem, więc przedział sięga od 0 do 2–4 razy przypadek
  (jackknife z 4 lat). Reguła wymaga górnej granicy ≤ 1,5, więc warstwy nie pokazujemy.

## Czy to są konkretne miejsca, czy całe winnice? (analiza po fakcie — opis, nie zmienia decyzji)

Z `w3d_summary.csv`, miesiące VI–IX, 281 miesięcy winnic:

| Udział winnicy „najniżej od N lat” | NDVI | NDMI |
|---|---|---|
| 0% | 63% miesięcy | 65% |
| 1–10% | 2% | 2% |
| **10–90% (konkretne miejsca)** | **17%** | **14%** |
| > 90% (cała winnica) | 17% | 20% |

W 2 z 25 miesięcy (NDVI; NDMI: 4 z 25) ponad połowa winnic jest „najniżej” na ponad 90% powierzchni naraz; przy
progu „ponad połowa powierzchni” takich miesięcy jest 7 (NDVI) i 6 (NDMI) z 25. Klasa często oddaje więc stan całej
winnicy i okolicy (pogoda danego roku — to już pokazuje karta W3b), a rzadziej konkretne miejsca.

## Razem z W3c: co wiemy o anomaliach wewnątrz winnicy

1. **W3c** (miejsce wobec reszty działki, próg z szumu): układ wewnątrz winnic zmienia się między latami, głównie
   (zgodne z uprawą i przesadzeniami) — mapa świeciłaby na ok. 15% powierzchni działek w zwykłe dni.
2. **W3d** (miejsce wobec samego siebie, ranking): kierunek suchy/wilgotny poprawny; kalibracji w zwykłe miesiące
   nie potwierdzono ani nie wykluczono (za mało lat), a sygnał dotyczy często całych winnic.
3. Wniosek dla Sentinel-2 (10–30 m) w tych winnicach: zmienność z roku na rok widać głównie na poziomie całej
   winnicy; anomalie konkretnych miejsc są na razie nie do pokazania jako wiarygodne.

## Audyt (2026-10-20, przed wersją 1.0)

Niezależne przeliczenie D1 z `w3d_summary.csv` potwierdziło tabelę. Poprawki opisu po audycie: liczba lat w podstawie
kryterium (4, nie 6), liczba winnic (12: VINEYARD_22 nie dostaje klasy, bo po przesadzeniach w 2018, 2019 i 2022 r.
ma mniej niż 4 lata historii), udział miesięcy „cała okolica naraz” i brak sformułowania „nie przesadza”. Dwa
zastrzeżenia do interpretacji ilorazu:

- **Nierówna jakość lat w historii.** W 2016–2017 mediany miesięcy powstają z 1,5–3 czystych dni, później z 5–7.
  Lata bardziej zaszumione częściej bywają skrajne, więc dla historii sięgających tych lat iloraz „najniżej” może
  wychodzić poniżej 1 nawet bez prawdziwego sygnału.
- **„Kwadraty 30 m” nachodzą na siebie:** to okna 3×3 wokół każdego piksela 10 m, a nie rozłączne kwadraty.
  Sąsiednie „kwadraty” nie są niezależne (przedział liczymy i tak po latach, nie po kwadratach).

Kod (`agriscreen/experiments/months.py`): gleba w normie liczona jako (30; 70), jak w protokole; żaden miesiąc nie
miał średniej dokładnie 30 ani 70, więc wynik się nie zmienia.

## Co dalej (do decyzji)

1. **Ten sam test za rok:** protokół bez zmian, nowe zamrożenie po sezonie 2027 (7 lat w teście). Przedział zwęża
   się powoli; wynik niepewny.
2. **Pokazać na blogu jako przykład z wyraźnym podpisem** „warstwa nie przeszła testu; ilustracja” — tylko w tekście
   wpisu, nie w panelu i nie w raporcie dla winiarza.
3. **Prawda terenowa:** krótkie odpowiedzi winiarza („tak, tu słabiej / tu kosiłem”) dałyby pierwszy test na samej
   winorośli, a nie tylko na szumie i kalibracji.
