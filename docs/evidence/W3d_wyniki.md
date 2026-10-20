# W3d — wyniki: „miejsce najniżej od 5 lat” (pierwszy przebieg, 2026-10-20)

> Protokół: `docs/evidence/W3d_protokol_miesiace.md`, zarejestrowany 2026-10-20 (D-091), SHA-256
> `599a381bb6d15dfe9fa81186a34436815d2d0ea01970828a5aa90730ff6da30a` — ten sam skrót w `w3d_tests.csv`.
> Dane: archiwum projektu, 419 scen, zamrożenie 2026-10-18 (`w3d_freeze.json`, ta sama lista scen co W3b i W3c,
> SHA-256 `96d70cb4…`); 13 winnic z QC; żadna scena nie wypadła. Kod `ddf26dd` (oznaczenie `+dirty` pochodzi od
> zapisanego w Colab notatnika — kolejny commit, c3783a3, zmienia tylko notatnik).

## Wynik w jednym zdaniu

**Warstwa „Months” nie przeszła kryterium (§5) dla NDVI ani NDMI i nie trafia do panelu.** Inaczej niż W3c:
w zwykłe miesiące klasa „najniżej od 5 lat” nie pojawia się częściej niż przypadkiem (średnio nawet rzadziej),
ale przy 6 latach danych przedział niepewności jest tak szeroki, że nie da się tego potwierdzić.

## Liczby (zgodnie z protokołem)

Iloraz = jak często klasa wypada / jak często wypadałaby przypadkiem (1/(N + 1), ok. 17%). 1 = dokładnie jak
przypadek.

| Miesiące VI–IX | NDVI „najniżej” | NDVI „najwyżej” | NDMI „najniżej” | NDMI „najwyżej” |
|---|---|---|---|---|
| **gleba w normie** (79 miesięcy winnic, 2020–2025) — podstawa kryterium | **0,49** [0; 1,92] | **1,16** [0; 3,23] | **0,55** [0; 2,32] | **1,10** [0; 3,70] |
| gleba sucha (< 30; 114) | 2,88 [1,22; 4,54] | 0,05 [0; 0,17] | 2,96 [0,86; 5,06] | 0,01 [0; 0,04] |
| gleba wilgotna (> 70; 88) | 0,30 [0; 1,10] | 3,02 [1,05; 4,99] | 0,28 [0; 1,11] | 2,62 [0,88; 4,37] |
| wszystkie (281) | 1,40 [0; 3,00] | 1,28 [0; 2,66] | 1,45 [0; 3,17] | 1,13 [0; 2,41] |
| **Kryterium:** górna granica ≤ 1,5 dla obu klas | **niespełnione** (1,92; 3,23) | | **niespełnione** (2,32; 3,70) | |

Opisowo (§6): „najniżej” po latach (NDVI): 2020 3,1; 2021 0,4; 2022 3,3; 2023 0,0; 2024 0,6; 2025 0,1;
2026 3,5. Udział powierzchni w plamach przy glebie w normie: „najniżej” 9% (NDVI) i 10% (NDMI), „najwyżej” 20% i 19%.

## Co to znaczy (prosto)

- **Kierunek się zgadza.** W suchych miesiącach „najniżej od 5 lat” wypada prawie 3 razy częściej niż przypadkiem,
  a „najwyżej” prawie nigdy; w wilgotnych odwrotnie. Satelita reaguje na wodę tak, jak powinien.
- **W zwykłe miesiące mapa nie przesadza:** średnio „najniżej” 0,5 razy przypadek, „najwyżej” 1,1 razy.
- **Ale 6 lat to za mało, żeby to potwierdzić.** Lata bardzo się różnią (2022 i 2026 suche, 2023 i 2025 nie),
  a cała okolica zmienia się razem, więc przedział sięga od 0 do 2–4 razy przypadek. Reguła wymaga górnej granicy
  ≤ 1,5, więc warstwy nie pokazujemy.

## Czy to są konkretne miejsca, czy całe winnice? (analiza po fakcie — opis, nie zmienia decyzji)

Z `w3d_summary.csv`, miesiące VI–IX, 281 miesięcy winnic:

| Udział winnicy „najniżej od N lat” | NDVI | NDMI |
|---|---|---|
| 0% | 63% miesięcy | 65% |
| 1–10% | 2% | 2% |
| **10–90% (konkretne miejsca)** | **17%** | **14%** |
| > 90% (cała winnica) | 17% | 20% |

W ok. 1/4 miesięcy ponad połowa winnic jest „najniżej” prawie w całości naraz. Klasa najczęściej oddaje więc stan
całej winnicy i okolicy (pogoda danego roku — to już pokazuje karta W3b), a rzadziej konkretne miejsca.

## Razem z W3c: co wiemy o anomaliach wewnątrz winnicy

1. **W3c** (miejsce wobec reszty działki, próg z szumu): układ wewnątrz winnic zmienia się między latami, głównie
   przez uprawę i przesadzenia — mapa świeciłaby na 15% działek w zwykłe dni.
2. **W3d** (miejsce wobec samego siebie, ranking): w zwykłe miesiące bez przesady, kierunek suchy/wilgotny poprawny,
   ale za mało lat, żeby to potwierdzić, a sygnał dotyczy głównie całych winnic.
3. Wniosek dla Sentinel-2 (10–30 m) w tych winnicach: zmienność z roku na rok widać głównie na poziomie całej
   winnicy; anomalie konkretnych miejsc są na razie nie do pokazania jako wiarygodne.

## Co dalej (do decyzji)

1. **Ten sam test za rok:** protokół bez zmian, nowe zamrożenie po sezonie 2027 (7 lat w teście). Przedział zwęża
   się powoli; wynik niepewny.
2. **Pokazać na blogu jako przykład z wyraźnym podpisem** „warstwa nie przeszła testu; ilustracja” — tylko w tekście
   wpisu, nie w panelu i nie w raporcie dla winiarza.
3. **Prawda terenowa:** krótkie odpowiedzi winiarza („tak, tu słabiej / tu kosiłem”) dałyby pierwszy test na samej
   winorośli, a nie tylko na szumie i kalibracji.
