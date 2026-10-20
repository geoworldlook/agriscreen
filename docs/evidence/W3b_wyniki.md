# W3b „Moja winnica” — wyniki pierwszego przebiegu (zamrożenie 2026-10-18)

> **Status:** wynik protokołu `docs/evidence/W3b_protokol_walidacji.md` (D-089, SHA-256 `f01b74a8…`, status
> `REGISTERED`, skrót w wynikach zgodny z zarejestrowanym), bez zmian protokołu po rejestracji.
> - Przebieg w Colab 2026-10-20, kod `54cc586`; notatnik z wynikami: commit `2d2fcbe`.
> - Flaga `+dirty`: kopia repozytorium na Dysku ma lokalne zmiany w plikach śledzonych. Ta flaga pojawiała się też
>   w poprzednich przebiegach. Kod `step_*.py` pochodzi z `git pull` tego samego commita.
> - Zamrożenie: 419 scen 2016-04-11 – 2026-10-18; SHA-256 listy scen `96d70cb4…`, bez zmian od zamrożenia.
> - Pełna tabela: `w3b_tests.csv` (247 wierszy) w `data/05_Final_Outputs/agriwatch/` na Dysku.
>
> Przedziały 95%: jackknife po latach (§0), przycięte do zakresu statystyki. Górna granica 1,00 oznacza przycięcie,
> a nie pewność.

## Wynik w skrócie

1. **T3 — kryterium zdania 3 niespełnione (wynik nierozstrzygnięty).**
   - ρ = 0,55 [−0,02; 1,00] między medianą wskaźnika wody 12 winnic a czujnikiem w gruncie (30 dni przed sceną),
     VI–IX 2018–2024, 140 dni scen.
   - Dolna granica jest o 0,02 poniżej zera, więc zdanie 3 na karcie zostaje ukryte. Tak przewidziała symulacja (§12).
   - W VI–IX związek jest prawie w całości **między latami**: ρ średnich sezonów 0,64 (n = 7), wewnątrz roku 0,06
     [−0,65; 0,76]. Roślinność okolicy dobrze odróżnia suchy sezon od mokrego. W szczycie lata nie śledzi tygodniowych
     zmian wody w glebie. W całym sezonie IV–X związek wewnątrz roku jest słabo dodatni (P5: 0,27–0,41).
   - Bez 2022 ρ spada do 0,32. Ten jeden suchy rok niesie dużą część związku.
2. **Wariant wielopasmowy (4 pasma) nieprzyjęty.**
   - Δρ = −0,01 [−0,18; 0,16]; ρ na latach niewidzianych przez model 0,54 [0,10; 0,97].
   - W roku testowym 2022, najsuchszym, model wypadł najgorzej: ρ = −0,90.
   - Cechy są parami prawie identyczne (B06–B8A r = 0,97, B04–B12 r = 0,95), a wagi par mają przeciwne znaki. Model
     ma w praktyce 2 niezależne wymiary.
   - Zostaje prosty wskaźnik; ten wynik jest punktem odniesienia dla sieci neuronowej (Plan v8).
3. **T1 — kalibracja: nie wykryto grubego rozkalibrowania, ale udział klasy „poniżej” jest wysoki.**
   - 28,0% scen [4,4; 51,7] wobec zakładanych 15,9%.
   - Rozkład po latach pokazuje przyczynę — prawdziwe susze: 2022 76%, 2026 59%, 2020 36%, a 2021 1% i 2023 2%.
   - W dniach z glebą w normie (percentyl ERA5 30–70) udział wynosi 14,1% [0,0; 29,6], czyli blisko oczekiwanych 15,9%.
   - Klasa nie zapala się więc „sama z siebie”, tylko w latach suchych.
4. **T2 — szum:** najmniejsza wyraźna zmiana z między scenami to 1,03 [0,59; 1,47] dla tego samego toru (4–6 dni)
   i 1,12 [0,77; 1,46] dla różnych torów (1–3 dni). Przy opadzie ≥ 5 mm rośnie do ok. 1,6. Wskaźnik wody jest mniej
   zaszumiony niż NDVI (1,38 / 1,24).
5. **Wartości „przed” z F4 (VINEYARD_06):**
   - Wyciek przyszłych lat zawyżał R o 0,13: krok a 0,57 → krok b 0,44 na tych samych 200 dniach.
   - Kontrola czujników A4 przywraca 0,11 (krok c 0,54), produkt 10 m z pasem 20 m daje 0,52 (krok d).
   - Po obu poprawkach R z czujnikiem jest podobne do opublikowanego w F4 (0,47), ale już bez wycieku.

## 1. Kryteria (§11 pkt 2)

| Kryterium | Wartość [95%] | n | Lata | Werdykt | Skutek na karcie |
|---|---|---|---|---|---|
| T3: ρ mediana 12 winnic (bez VINEYARD_06) a ISMN A4 W1 [t−30, t−1] | 0,55 [−0,02; 1,00] | 140 | 2018–2024 | niespełnione | zdanie 3 ukryte; „Na ile ufać”: ρ z napisem „niepotwierdzone” |
| §7: Δρ = ρ_multi − ρ_prosty | −0,01 [−0,18; 0,16] | 140 | 2018–2024 | nieprzyjęty | karta zostaje przy prostym wskaźniku |

## 2. T3 — wiersze opisowe (te same dni co wiersz główny)

| Wiersz | ρ [95%] | Uwagi |
|---|---|---|
| bez roku 2018 / 2019 / 2020 / 2021 / 2022 / 2023 / 2024 | 0,58 / 0,61 / 0,61 / 0,50 / **0,32** / 0,58 / 0,52 | wszystkie > 0; bez 2022 najsłabiej |
| wewnątrz roku | 0,06 [−0,65; 0,76] | brak związku w trakcie sezonu |
| średnie sezonów (n = 7) | 0,64 | związek między latami |
| cel ERA5-Land 0–100 cm | 0,56 [−0,19; 1,00] | jak czujnik |
| cel SWI T15 | 0,69 [0,20; 1,00] | jedyny cel z dolną granicą > 0 (opisowo, nie kryterium) |
| cel A4 W2 / W3 / W1_05WP / W1_015 | 0,27 (36 dni) / 0,41 / 0,50 / 0,48 | ranga zależy od reguł czujnika (§12) |
| kontrola: udział dni cenzurowanych w oknie | −0,21 [−1,00; 0,58] | roślinność nie śledzi samej cenzury |
| wartości surowe (z cyklem sezonowym) | 0,42 [−0,30; 1,00] | cykl sezonowy nie poprawia zgodności |
| predyktor NDVI / NDMI / −CRSWIR | 0,60 [0,16; 1,00] / 0,55 / 0,55 | zieleń nie gorsza od wskaźnika wody — zgodnie z literaturą (Plan W3b §2) |
| zbiór z VINEYARD_06 | 0,56 [0,01; 1,00] | r(mediana 12 winnic, VINEYARD_06) = 0,87: wyłączenie VINEYARD_06 daje mało niezależności |

## 3. T1 i T2

| Miara | Wartość [95%] | n |
|---|---|---|
| udział z ≤ −1, 13 winnic, VI–IX 2018–2026 | 28,0% [4,4; 51,7] | 2469 |
| udział z ≥ +1 / \|z\| ≥ 2 | 20,4% [4,9; 35,9] / 12,1% [0,0; 24,3] | 2469 |
| z ≤ −1 przy glebie w normie (percentyl 30–70) | 14,1% [0,0; 29,6] | 839 |
| z ≤ −1: 1–2 lata w normie / ≥ 3 lata | 16,8% / 29,6% | 303 / 2166 |
| z ≤ −1: NDVI | 24,7% [5,1; 44,3] | 2469 |
| z ≤ −1: mediana okolicy | 25,8% [0,0; 53,9] | 194 |
| MDC95 wskaźnika wody: G5 / G13 bez opadu | 1,03 [0,59; 1,47] / 1,12 [0,77; 1,46] | 638 / 799 par |
| MDC95: pary z opadem ≥ 5 mm (G5 / G13) | 1,64 / 1,56 | 242 / 121 par |
| MDC95 w jednostkach: NDMI G5 / G13 | 0,058 / 0,082 | |

## 4. Wartości „przed” (§9), VINEYARD_06, IV–X 2018–2024

| Krok | Roślinność | Czujnik | R [95%] | n |
|---|---|---|---|---|
| a | z_NDMI z F4 (norma „pozostałe lata”) | QC sprzed A4 (W3) | 0,57 [0,38; 0,71] | 200 |
| b | norma przyczynowa, SR 2,5 m | W3 | 0,44 [0,15; 0,65] | 200 |
| c | jak b | A4 W1 | 0,54 [0,35; 0,69] | 200 |
| d | S2_10m_buf20 | A4 W1 | 0,52 [0,31; 0,67] | 200 |

W konfiguracji d, wszystkie dni:

| Miara | VINEYARD_06 | Mediana 12 winnic |
|---|---|---|
| P1 r z_NDMI i −z_CRSWIR | 0,97 | 0,98 |
| P2 r z_NDMI i z_NDVI | 0,92 | 0,93 |
| P3 R z czujnikiem w dniu sceny | 0,42 [0,23; 0,58] | 0,42 [0,27; 0,55] |
| P4 R ze średnią [t−30, t] | 0,51 [0,30; 0,66] | 0,45 [0,26; 0,59] |
| P5 R wewnątrz roku / średnich sezonów | 0,41 [0,23; 0,55] / 0,60 | 0,27 [0,04; 0,46] / 0,68 |

Uwaga do porównania z T3:
- R z przedziałem z bloków 30-dniowych (metoda F4) daje dodatnią dolną granicę także wewnątrz roku.
- Jackknife po latach (kryterium W3b) jest dużo ostrożniejszy, bo traktuje rok jako jednostkę niezależną.

## 5. Kontrola jakości (§11 pkt 5)

- **Działki:**
  - 13 z 15 winnic z QC; VINEYARD_16 (19 px) i VINEYARD_18 (16 px) są poza testami;
  - sceny przyjęte (≥ 90% pikseli czystych): 367–379 z 419 na działkę.
- **Normy:**
  - z tego samego toru w 91% scen VI–IX;
  - z < 3 lat w puli w 12%;
  - tor różny między działkami w 1,4% dni;
  - dni z 2 scenami działki: 24.
- **Flagi zmiany gospodarowania (4 sezony):**
  - VINEYARD_13 w 2019 (−);
  - VINEYARD_21 w 2024 (−);
  - VINEYARD_22 w 2018 (−) i 2022 (+).

  Dla VINEYARD_06 flagi nie ma.
- **Czujnik:** w oknach 30 dni przed scenami T3 jest 537 dni cenzurowanych na 910 dni z danymi (59%) i 19 dni
  FAST_DROP. Cel T3 latem jest w większości cenzurowany (§12).

## 6. Co zmienia się na karcie i czego nie zmieniamy

- **Zdanie 3 (okolica) ukryte.** Pokazujemy tylko gleba w okolicy (zdanie 1) i wskaźnik wody działki wobec jej
  historii (zdanie 2), z „k z N winnic” i progiem zmiany 1,0 / 1,1 z.
- **„Na ile ufać”** podaje T1 28% [4; 52], MDC95 i ρ T3 z dopiskiem „niepotwierdzone”.
- **Bez zmian po wyniku (§11 pkt 4):**
  - nie przechodzimy na SWI ani NDVI, mimo lepszych wierszy opisowych;
  - nie zmieniamy okna ani miesięcy.

  To byłby wybór po wyniku. Ewentualna zmiana wymaga nowej wersji protokołu i nowych danych (sezon 2027 jako lata
  niewidziane).

## 7. Interpretacja i ograniczenia

- **Co to mówi rolnikowi:**
  - wskaźnik wody działki jest stabilny (szum ok. 1 z) i skalibrowany w latach normalnych;
  - w latach suchych (2022, 2026) większość winnic jest poniżej normy naraz;
  - porównanie „Twoja działka a sąsiedzi” (k z N) jest więc ważniejsze niż sama klasa.
- **Czego nie możemy powiedzieć:**
  - że roślinność śledzi tydzień po tygodniu wodę w glebie w szczycie lata (ρ wewnątrz roku VI–IX 0,06);
  - że SWIR mówi więcej niż zieleń (NDVI 0,60 wobec 0,55).
- **Ograniczenia (§12):** 7 sezonów, cel punktowy pod trawą i w 59% cenzurowany, nieznane nawadnianie. Sprawdzamy
  spójność na danych już oglądanych w F4, a nie na nowych danych.
- **Następny test na nowych danych:** sezon 2027 — te same reguły, bez zmian.
