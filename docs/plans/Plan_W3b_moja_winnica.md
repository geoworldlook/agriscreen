# Plan W3b — „Moja winnica wobec jej historii” (wersja 3, uproszczona)

Status: **PROPOSED** 2026-10-18, do akceptacji przed kodem. Zastępuje wersje 1 i 2 tego pliku (historia w git).
Rozwija W3b z Planu v9 §5b (D-073).

## 1. Co dostaje rolnik

Karta „Moja winnica” z trzema zdaniami:

1. **Gleba w okolicy** (ERA5 + SWI, ~10 km): sucho / w normie / wilgotno wobec historii. *Już zwalidowane (W2 + REF).*
2. **Twoja działka** (Sentinel-2, NDMI): roślinność działki poniżej / w normie / powyżej **swojej własnej historii**
   o tej porze roku; obok, ile winnic w okolicy jest w tym samym stanie.
3. **Czy to się zgadza:** jedno zdanie łączące 1 i 2, pokazywane tylko wtedy, gdy test T3 potwierdzi związek.

Czego karta nie mówi: „winorośl ma stres wodny”. Bez pomiaru w winnicy nie da się tego obronić. Wydzielenie sygnału
samej winorośli to następny etap (Plan v8: rozplątanie kanałów siecią neuronową).

## 2. Dlaczego to się obroni: jedno zdanie, jeden test

| Zdanie na karcie | Test (zapisany przed liczeniem) | Dane |
|---|---|---|
| 1. Gleba w okolicy | zrobione: R 0,52–0,68 wobec czujników na 3 stacjach | ERA5, SWI, ISMN, ICOS |
| 2. „Działka poniżej swojej normy” | **T1 kalibracja:** gdy gleba w okolicy jest w normie, „poniżej” zdarza się tak często, jak mówi statystyka (ok. 1 scena na 6) | archiwum S-2 na Dysku, ERA5 |
| 2. „Zmiana od poprzedniej sceny” | **T2 szum:** dwie sceny w odstępie ≤ 5 dni dają to samo; zmiana mniejsza niż szum = „bez zmian” | archiwum S-2 na Dysku |
| 3. „Spójne z suszą w glebie” | **T3 związek z czujnikiem:** anomalia winnic wokół Condom podąża za wodą zmierzoną przez czujnik ISMN (136 m od Twojej winnicy) z opóźnieniem 30–60 dni (literatura, F7) | archiwum S-2, ISMN 2016–2024, ERA5 |

**Uczciwość T3:** F7 liczyło już Twoją winnicę (VINEYARD_06) wobec czujnika. Dlatego miarą główną T3 jest mediana
pozostałych 14 winnic. Jeśli T3 wyjdzie słabo, zdanie 3 nie pojawia się na karcie, a zdanie 2 opisuje tylko
roślinność działki.

## 3. Kroki

| Krok | Co | Sesje |
|---|---|---|
| **K1** | Protokół T1–T3: definicje, progi, okno VI–IX, opóźnienie 30–60 dni; skrót SHA-256 przed liczeniem | 1 |
| **K2** | Statystyki działek z archiwum na Dysku (414 scen 2016–2026, bez nowego pobierania): istniejące `task_scene_stats` rozszerzone z VINEYARD_06 na wszystkie 15 winnic; obrys zwężony o 20 m | 1 |
| **K3** | Anomalie działek (istniejące `scene_anomaly`: własna historia, ten sam tor orbity, ±15 dni, 5 wcześniejszych lat) + przebieg T1–T3 w Colab; notatka wyników, wiersze w karcie wyników | 1–2 |
| **K4** | Karta „Moja winnica” w dashboardzie, biuletynie i notatniku; nagłówek gleby w 3 klasach | 1–2 |

Razem 4–6 sesji. Bieżące sceny dochodzą przyrostowo tym samym potokiem, więc karta działa w sezonie 2027 na bieżąco.

**Potem:** rozplątanie kanałów (Plan v8, moduły 2–3). Ocena: te same T1–T3, przed i po.

**Świadomie poza tym planem** (osobne decyzje później): sceny S-2 przy stacjach ICOS, mapa stref w działce,
wgrywanie dowolnej działki przez rolnika.

## 4. Decyzje do zatwierdzenia

- **D-084 Dane:** archiwum S-2 z Dysku i obecny potok (jedno źródło dla historii i bieżących scen).
- **D-085 Wskaźnik i klasy działki:** NDMI; z ≤ −1 „poniżej swojej normy”, z ≥ +1 „powyżej”, pomiędzy „w normie”;
  działka liczona, gdy ≥ 80% pikseli bez chmur.
- **D-086 Walidacja:** T1–T3 jak w §2, zapisane i zahaszowane przed liczeniem.
- **D-087 Słowa:** „roślinność działki (winorośl i międzyrzędzie)”, nigdy „stres wodny winorośli”; nagłówek gleby
  w 3 klasach (sucho / w normie / wilgotno).

## 5. Źródła

- Laroche-Pinel E. i in. 2021. Towards Vine Water Status Monitoring on a Large Scale Using Sentinel-2 Images.
  *Remote Sensing* 13(9): 1837. https://doi.org/10.3390/rs13091837 — S-2 wyjaśnia ok. 40% zmienności potencjału
  wodnego winorośli, i to tylko przez model uczony na pomiarach terenowych; dlatego nie podajemy stanu wody winorośli.
- `docs/evidence/F7_v12/README.md` — opóźnienie reakcji roślinności na suszę w glebie (30–60 dni, post hoc).
- `docs/evidence/W2_REF_wyniki.md` — walidacja warstwy gleby.
