# W3c — protokół „Strefa gorsza niż zwykle” (pre-rejestracja)

> **Status:** `REGISTERED` 2026-10-20 (D-090) · SHA-256 sekcji 0–9: `45708189b130b6c87edded38b32691b8fc20a9659a772e57693da43424dab326`
> - Skrót liczy `sed -n '/^## 0\./,$p' docs/evidence/W3c_protokol_strefy.md | sha256sum`. Ten sam skrót `task_zones`
>   zapisuje w `w3c_tests.csv` i ostrzega, gdy treść sekcji 0–9 różni się od zarejestrowanej.
> - Wybory U1–U7 przyjęte 2026-10-20 („zatwierdzam”). Przed rejestracją dopisany trzeci warunek kryterium (§6.3):
>   test szumu z par scen nie widzi błędu samej normy (w parach kilka dni od siebie norma prawie się nie zmienia), więc
>   sprawdzamy też, jak często mapa świeci, gdy gleba jest w normie. Warunek tylko utrudnia pokazanie warstwy.
> - Rejestracja przed pierwszym liczeniem na danych Sentinel-2 (liczy dopiero notatnik w Colab). Zmiana po rejestracji
>   = nowa wersja protokołu, nowy skrót i opis, co i dlaczego zmieniono.
> - **Pytanie, na które odpowiada warstwa:** czy to miejsce w winnicy jest **dziś słabsze (albo suchsze) względem
>   reszty tej samej działki, niż zwykle bywa o tej porze roku**.
> - **Czego nie mówi:** nie mówi, że winorośl cierpi z braku wody, i nie daje porady nawadniania. Nie mamy pomiarów
>   w winnicach; warstwa porównuje satelitę z satelitą.
> - **Podstawa:** W3b (D-084–D-089): te same sceny, działki, pas 20 m, okno normy i reguła toru. Panel: strefy
>   „piksel minus mediana działki” (`step_12`, commit 8d6beb4) — tu dochodzi do nich historia. Kod: `step_13_zones.py`.
>
> **Oznaczenia:** [P] praca źródłowa; [D] nasze dane, kod albo dokument; [K] konwencja, nie wynik z danych;
> [W] wiedza ogólna; **(U1–U7)** — wybory w §9.

## 0. Dane i zamrożenie

- Sentinel-2 L2A z archiwum projektu (`S2_DIR`, `COPERNICUS/S2_SR_HARMONIZED`, `step_01`), miesiące IV–X; pasma 20 m
  zapisane na siatce 10 m (bloki 2×2) [D].
- Wszystkie sceny czytamy w tym samym oknie wokół winnic. Scena, której siatka jest przesunięta względem pierwszej
  sceny o > 1 m, wypada; ich liczbę raportujemy [K].
- Zamrożenie testów: `W3C_FREEZE` = data ostatniej sceny w `S2_DIR` przy pierwszym liczeniu; zapis w
  `w3c_freeze.json` razem z SHA-256 listy plików. Testy (§3, §5, §6) liczymy tylko na scenach ≤ tej daty. Mapa
  pokazuje też sceny nowsze, z tym samym progiem.
- Opad do par scen: `precip_mm` ERA5-Land, jak W3b §5. Gleba w normie: percentyl ERA5-Land 0–100 cm 30–70, jak
  karta wody.
- Przedział 95%: jackknife po latach, jak W3b §0 (rok sceny; w parach rok pierwszej sceny).

## 1. Działki i piksele

- Winnice z QC W3b (13 z 15; ≥ 40 pikseli w pasie 20 m) [D].
- Piksele: środek ≥ 20 m od brzegu (pas jak W3b §1). Piksel 20 m wystaje wtedy poza działkę najwyżej ok. 1 m [D].
  Pas 10 m z panelu zostaje tylko w opisowej warstwie stref bez historii.
- Czysta scena działki: ≥ 90% pikseli pasa bez chmur (`VEG_MIN_CLEAR_FRAC`) i wszystkie 10 pasm skończone; jedna
  scena na dzień — ta z większym udziałem czystych pikseli (W3b §1). Tor orbity: `step_04.track_ids` (jak W3b).
- Wskaźniki **(U4):** NDVI (zieleń) i NDMI (woda w roślinności, B8A/B11).

## 2. Wielkość mierzona

Dla działki P, czystej sceny t i wskaźnika I:

1. **Strefa dnia:** r(x, t) = I(x, t) − mediana I z czystych pikseli pasa działki P w scenie t.
   Odejmowanie mediany tego samego dnia usuwa pogodę i stan całej działki; zostaje układ wewnątrz działki.
2. **Wygładzenie (U1):** średnia r z okna 3×3 piksele (30 m) wokół x, tylko z czystych pikseli pasa; wartość
   istnieje, gdy w oknie jest ≥ 5 z 9 takich pikseli. Dalej „r” oznacza wartość wygładzoną. Powód: przesunięcie
   zdjęć między datami rzędu piksela i pasma 20 m [W, D].
3. **Norma miejsca:** μ(x) = średnia r(x, ·) z czystych scen tej samej działki z lat Y−5…Y−1, w oknie ±15 dni roku;
   ten sam tor orbity, gdy w puli dla tej działki jest ≥ 5 takich scen, inaczej oba tory (jak W3b §2).
   **Minimum (U5):** w komórce x ≥ 5 scen z wartością i ≥ 3 różne lata; inaczej brak wartości („za krótka historia”).
4. **Odchylenie strefy:** Δ(x, t) = r(x, t) − μ(x), w jednostkach wskaźnika (nie z). Powód: odchylenie standardowe
   z kilku scen w jednym miejscu jest niestabilne; dzielenie przez nie wzmacniałoby szum [K].

## 3. Z1 — szum i próg (opisowo, ustala regułę mapy)

- **Pary scen:** ta sama działka, VI–IX, obie sceny czyste, suma opadu < 5 mm od t1 do t2 włącznie; grupy jak
  W3b §5: **G5** ten sam tor, Δt 4–6 dni; **G13** różne tory, Δt 1–3 dni.
- **Miara:** dla każdej komórki z Δ w obu scenach d(x) = Δ(x, t2) − Δ(x, t1); MDC95 = 1,96·√(średnia d²) ze
  wszystkich komórek i par grupy. Przedział: jackknife po latach. Grupa z < 30 parami: „za mało par”.
- **Założenie:** w ≤ 6 dni bez deszczu układ w działce się nie zmienia; prawdziwe zmiany zawyżają MDC, więc próg jest
  ostrożny (W3b §5). Błąd samej normy prawie się tu znosi — sprawdza go §6.3.
- **Opisowo:** MDC osobno dla każdego roku (czy starsze lata, ze słabszym nałożeniem zdjęć, są głośniejsze).

## 4. Reguła mapy (U2, U6, U7)

- **Próg (U2):** T = MDC95 z grupy G5 (gdy G5 ma „za mało par” — z G13), osobno dla NDVI i NDMI.
- **Komórka słabsza niż zwykle:** Δ ≤ −T; **mocniejsza niż zwykle:** Δ ≥ +T; pomiędzy: „jak zwykle” (bez koloru).
- **Strefa (U6):** zwarta grupa ≥ 4 komórek tego samego kierunku, sąsiadujących bokiem lub rogiem (8 sąsiadów).
  Mniejsze grupy nie są pokazywane ani liczone jako strefa.
- **Nowa czy potwierdzona (U7):** komórka strefy jest „potwierdzona”, gdy w innej czystej scenie tej działki z
  ostatnich 10 dni przed t była w strefie tego samego kierunku; inaczej „nowa”. Patrzymy tylko wstecz (tak działa
  monitoring na bieżąco).
- Komórka bez normy (U5): szara, „za krótka historia”.

## 5. Z2 — jak często mapa coś pokazuje (opisowo)

- Udział komórek w strefach (po U6) wśród wszystkich komórek z Δ, w scenach VI–IX: osobno „słabsze”, „mocniejsze”,
  razem; osobno w dniach z glebą w normie i we wszystkich dniach; także przed U6 (same progi).
- Przy samym szumie oczekujemy rzędu 1% (T to 1,96·√2 odchylenia pojedynczego pomiaru) [W].

## 6. Kryterium: czy pokazujemy warstwę (U3)

Warstwa „Zones vs usual” trafia do panelu i raportów **tylko gdy dla danego wskaźnika spełnione są trzy warunki**:

1. Z1 ma ≥ 30 par w G5 albo G13 (jest próg T).
2. Górna granica przedziału MDC95 (z grupy użytej do progu) jest **mniejsza niż połowa** typowego zróżnicowania
   działki: mediany po działkach i scenach VI–IX rozstępu p90 − p10 wartości r (§2.2) w pasie [K].
3. W dniach z glebą w normie górna granica przedziału udziału komórek w strefach (oba kierunki, po U6) wynosi
   **≤ 5%** [K]. Gdy dni z glebą w normie są w < 3 latach, liczymy na wszystkich dniach VI–IX (ostrożniej, bo
   wchodzą prawdziwe zmiany).

Niespełnione: panel dalej pokazuje strefy bez historii, a w „How far to trust it” pisze, który warunek nie przeszedł
i z jakimi liczbami. Nie poprawiamy metody po zobaczeniu wyniku w tej wersji protokołu.

## 7. Co pokazujemy

- Mapa: strefy „słabsze niż zwykle” (brąz) i „mocniejsze niż zwykle” (zieleń / błękit); potwierdzone pełnym kolorem,
  nowe jaśniej; reszta przezroczysta; komórki bez normy szare.
- Pod mapą: udział pasa działki w strefach (słabsze / mocniejsze, w tym potwierdzone), próg T, liczba scen i lat
  w normie.
- Zdanie: „Ta część działki jest dziś słabsza względem reszty działki niż zwykle o tej porze (próg T = …, z testu
  szumu). To porównanie zdjęć satelitarnych, nie pomiar stanu winorośli.”
- „How far to trust it”: Z1 (MDC, n par), Z2 (udział przy glebie w normie), status
  `noise-tested, not validated in the field`.

## 8. Ograniczenia znane przed liczeniem

- **Zmiany gospodarowania** (koszenie albo uprawa części międzyrzędzi, wymiana krzewów, nowe nasadzenia) wyglądają
  jak strefa inna niż zwykle. Flaga W3b §8 działa dla całej działki, nie dla części.
- **Nałożenie zdjęć** do ok. 2021 r. było słabsze; norma z tych lat może być przesunięta. Wygładzenie 30 m i opis Z1
  po latach sprawdzają to tylko częściowo [W].
- **Kąt widzenia:** różne tory widzą rzędy pod innym kątem; reguła toru jak W3b.
- **Brak prawdy terenowej:** test szumu mówi, kiedy zmiana jest większa niż szum satelity, a nie że dotyczy wody
  w winorośli.
- **Historia:** pełna 5-letnia norma od ok. 2021 r.; wcześniej wiele komórek bez normy (U5).
- **Wiele komórek:** nawet rzadki szum zapala co tydzień kilka komórek; ogranicza to U6, a Z2 podaje skalę.

## 9. Wybory (U1–U7), przyjęte 2026-10-20

| | Wybór | Przyjęte | Alternatywa |
|---|---|---|---|
| U1 | Wygładzenie | okno 3×3 (30 m), ≥ 5 z 9 pikseli | bez wygładzenia (10 m) albo 5×5 (50 m) |
| U2 | Próg mapy | T = MDC95 z testu szumu (G5, inaczej G13) | stały próg, np. 0,05 |
| U3 | Kryterium pokazania | trzy warunki z §6 | bez kryterium |
| U4 | Wskaźniki | NDVI i NDMI | także NDRE |
| U5 | Minimum historii | ≥ 5 scen i ≥ 3 lata w komórce | ≥ 5 scen, bez progu lat |
| U6 | Minimalna strefa | ≥ 4 komórki, 8 sąsiadów | pojedyncze komórki |
| U7 | Nowa / potwierdzona | ta sama strefa w innej czystej scenie z ostatnich 10 dni | bez etykiety |
