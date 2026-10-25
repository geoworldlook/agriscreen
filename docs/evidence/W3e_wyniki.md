# W3e „Winnica wobec sąsiadów” — wyniki pierwszego przebiegu

> **Status:** wynik protokołu `docs/evidence/W3e_protokol_sasiedzi.md` (D-092, SHA-256 `ff20baba…`, status
> `REGISTERED`, zarejestrowany w commicie `2e37a38` przed liczeniem z_rel), bez zmian protokołu po rejestracji.
> - Przebieg 2026-10-25 na komputerze lokalnym; notatnik z wynikami: `notebooks/experiments/W3e_sasiedzi.ipynb`
>   (generator `build_w3e.py`). Dane: `parcel_anomalies.csv` z przebiegu 2026-10-25, sceny VI–IX do zamrożenia W3b
>   (2026-10-18).
> - Eksperyment **eksploracyjny**: lata testów już oglądaliśmy w T1 i flagach W3b. Potwierdzenie: sezon 2027.

## Wynik w skrócie

**Decyzja (§7): nie dodajemy — wielkość skalibrowana, ale sygnał samej winnicy (H4) niepokazany.**

| Test | z_rel (wobec sąsiadów) | z_woda, te same sceny | Kryterium | Werdykt |
|---|---|---|---|---|
| H1 kalibracja: udział ≤ −1 | 15,9% [8,9; 22,8] | 31,1% [0,2; 61,9] | 10–22% i przedział zawiera 15,9% | spełnione |
| H2 rozstęp między latami | 19,1 pp | 74,4 pp | ≤ 25 pp | spełnione |
| H3 \|sucho − wilgotno\| | 3,6 pp | 49,4 pp | ≤ 10 pp | spełnione |
| H4 przesadzenia RPG | ranga 0,81, p = 0,070 (2 zdarzenia z 5) | — | ranga ≥ 0,75 i p ≤ 0,05 | niespełnione |

Zbiór testów: 1941 scen, 13 winnic, lata 2020–2026. 455 scen VI–IX z lat 2018–2026 poza testami (brak skali
z ≥ 2 lat wcześniejszych).

## 1. Co pokazały H1–H3

- **Wspólna pogoda znika.** Udział „poniżej” po latach:

  | Rok | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
  |---|---|---|---|---|---|---|---|
  | z_woda | 35,9% | 1,3% | 75,7% | 2,3% | 7,2% | 10,5% | 60,0% |
  | z_rel | 24,0% | 21,1% | 22,3% | 13,0% | 13,5% | 13,4% | 4,9% |

  Według gleby w dniu sceny: z_woda sucho 55,0% / w normie 14,4% / wilgotno 5,6%; z_rel 13,0% / 19,2% / 16,6%.
- **Związek z pogodą okolicy usunięty:** r(z_woda, mediana sąsiadów) = 0,80; r(d, mediana sąsiadów) = −0,14.
- **Przykład (VINEYARD_06, wykres w notatniku §8):** w 2022 r. z_woda około −2 (susza), z_rel około +1 — winnica
  zniosła suchy rok lepiej niż sąsiednie. z_woda mówi „sucho w okolicy”, z_rel mówi „jak ta winnica na tle innych”.
- **Uwaga do 2026 r.:** z_rel ≤ −1 tylko w 4,9% scen (najmniej). Przyczyna niesprawdzona; możliwe, że w roku
  suchym winnice reagują podobniej (mniejszy rozrzut d) niż w latach skali.

## 2. Dlaczego H4 nie przeszedł

- Z 5 zdarzeń RPG (VINEYARD_13 2019, 2020; VINEYARD_22 2018, 2019, 2022) miarę mają tylko 2. Trzy wcześniejsze
  przypadają na lata, w których z_rel nie istnieje: skala wymaga ≥ 2 lat d wcześniej, a d wymaga z_woda, które samo
  potrzebuje lat normy. **To była wada planu, widoczna przed liczeniem:** przy tych regułach H4 miał w praktyce
  2 zdarzenia, a przy 2 zdarzeniach p ≤ 0,05 wymaga obu w górnych ok. 20% sezonów.
- Z dwóch zdarzeń: VINEYARD_22 2022 ranga 0,95 (wyraźnie nietypowy sezon, mediana z_rel +1,55), VINEYARD_13 2020
  ranga 0,68.
- Skala winnic z przesadzeniami jest zawyżona przez same przesadzenia (VINEYARD_13: 3,23 w 2021 r. wobec
  0,4–0,9 u innych; VINEYARD_22: 1,1–2,6). MAD nie chroni, gdy odstające są całe sezony. Późniejsze zmiany w tych
  winnicach będą przez to słabiej widoczne.

## 3. Co z tego wynika

- **Nie zmieniamy karty ani panelu** (reguła §7). Wynik negatywny dotyczy H4, nie kalibracji.
- **Wiemy więcej niż przed testem:** porównanie z sąsiadami jest skalibrowane i niezależne od roku i gleby
  (H1–H3 z dużym zapasem), czego z_woda nie ma. To odpowiada na problem z T1 W3b („w suchym roku wszystkie winnice
  poniżej normy”).
- **Nie wiemy:** czy z_rel wskazuje zdarzenia w samej winnicy. Do tego potrzeba więcej zdarzeń z datą niż 2.

## 4. Propozycje (osobne decyzje, nie część tego protokołu)

1. Sezon 2027: powtórka H1–H3 bez zmian (potwierdzenie na latach niewidzianych).
2. Nowa wersja testu sygnału (W3e v2, nowa rejestracja): zdarzenia, które da się zmierzyć — np. zmiany w RPG
   2025–2026 (gdy IGN je opublikuje) albo zdarzenia zgłoszone przez winiarzy; skala bez sezonów z kodem przesadzenia.
3. Opisowo w panelu (bez nowego zdania na karcie) można rozważyć wykres „Twoja winnica na tle sąsiadów” jako
   ilustrację, oznaczony „not validated”. Wymaga decyzji.
