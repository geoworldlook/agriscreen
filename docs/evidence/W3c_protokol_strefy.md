# W3c — protokół „Strefa gorsza niż zwykle” (pre-rejestracja)

> **Status:** `DRAFT` 2026-10-20 — do akceptacji. Po akceptacji: `REGISTERED`, SHA-256 sekcji 0–9 w tym nagłówku i w
> pliku wyników; dopiero potem liczymy cokolwiek na danych. Zmiana po rejestracji = nowa wersja i nowy skrót.
> - Skrót liczy `sed -n '/^## 0\./,$p' docs/evidence/W3c_protokol_strefy.md | sha256sum`.
> - **Pytanie, na które odpowiada warstwa:** czy to miejsce w winnicy jest **dziś słabsze (albo suchsze) względem
>   reszty tej samej działki, niż zwykle bywa o tej porze roku**.
> - **Czego nie mówi:** nie mówi, że winorośl cierpi z braku wody, i nie daje porady nawadniania. Nie mamy pomiarów
>   w winnicach; warstwa porównuje satelitę z satelitą.
> - **Podstawa:** W3b (D-084–D-089): te same sceny, działki, pas 20 m, okno normy i reguła toru. Panel: strefy
>   „piksel minus mediana działki” (`step_12`, commit 8d6beb4) — tu dochodzi do nich historia.
>
> **Oznaczenia:** [P] praca źródłowa; [D] nasze dane, kod albo dokument; [K] konwencja, nie wynik z danych;
> [W] wiedza ogólna; **(U1–U5)** — wybór do akceptacji w §9.

## 0. Dane i zamrożenie

- Sentinel-2 L2A z archiwum projektu (`S2_DIR`, `COPERNICUS/S2_SR_HARMONIZED`, `step_01`), miesiące IV–X; pasma 20 m
  zapisane na siatce 10 m (bloki 2×2) [D].
- Zamrożenie testów: `W3C_FREEZE` = data ostatniej sceny w `S2_DIR` przy pierwszym liczeniu; zapis w
  `w3c_freeze.json` razem z SHA-256 listy plików i commitem kodu. Testy liczymy tylko na scenach ≤ tej daty.
- Opad do par scen: `precip_mm` ERA5-Land, jak w W3b §5.
- Przedział 95%: jackknife po latach, jak W3b §0.

## 1. Działki i piksele

- Winnice z QC W3b (13 z 15; ≥ 40 pikseli w pasie 20 m) [D].
- Piksele: środek ≥ 20 m od brzegu (pas jak W3b §1). Piksel 20 m wystaje wtedy poza działkę najwyżej ok. 1 m [D].
  Pas 10 m z panelu zostaje tylko w opisowej warstwie stref bez historii.
- Czysta scena działki: ≥ 90% pikseli pasa bez chmur (`VEG_MIN_CLEAR_FRAC`), jedna scena na dzień (W3b §1).
- Wskaźniki **(U4):** NDVI (zieleń) i NDMI (woda w roślinności, B8A/B11).

## 2. Wielkość mierzona

Dla działki P, sceny t i wskaźnika I:

1. **Strefa dnia:** r(x, t) = I(x, t) − mediana I w pasie działki P w scenie t (tylko czyste piksele).
   Odejmowanie mediany tego samego dnia usuwa pogodę i stan całej działki; zostaje układ wewnątrz działki.
2. **Wygładzenie (U1):** średnia r z okna 3×3 piksele (30 m) wokół x, tylko z pikseli pasa; wartość istnieje, gdy
   w oknie jest ≥ 5 z 9 ważnych pikseli. Powód: przesunięcie zdjęć między datami rzędu piksela i pasma 20 m [W, D].
3. **Norma miejsca:** μ(x) = średnia r(x, ·) ze scen tej samej działki z lat Y−5…Y−1, w oknie ±15 dni roku, ten sam
   tor orbity, gdy ma ≥ 5 scen, inaczej oba tory (jak W3b §2).
   **Minimum (U5):** ≥ 5 scen i ≥ 3 różne lata; inaczej brak wartości („za krótka historia”).
4. **Odchylenie strefy:** Δ(x, t) = r(x, t) − μ(x), w jednostkach wskaźnika (nie z). Powód: odchylenie standardowe
   z kilku scen w jednym miejscu jest niestabilne; dzielenie przez nie wzmacniałoby szum [K].

## 3. Z1 — szum i próg (opisowo, ustala regułę mapy)

- **Pary scen:** ta sama działka, VI–IX, oba końce z ważnym Δ, suma opadu P < 5 mm od t1 do t2; grupy jak W3b §5:
  **G5** ten sam tor, Δt 4–6 dni; **G13** różne tory, Δt 1–3 dni.
- **Miara:** dla każdej komórki x w obu scenach d(x) = Δ(x, t2) − Δ(x, t1); MDC95 = 1,96·√(średnia d²) ze wszystkich
  komórek i par grupy. Przedział: jackknife po latach. Grupa z < 30 parami: „za mało par”.
- **Założenie:** w ≤ 6 dni bez deszczu układ w działce się nie zmienia; prawdziwe zmiany zawyżają MDC, więc próg jest
  ostrożny [W3b §5].
- **Opisowo:** MDC osobno dla lat testowych (czy starsze lata, ze słabszym nałożeniem zdjęć, są głośniejsze).

## 4. Reguła mapy (U2)

- Próg T = MDC95 z grupy G5 (gdy G5 ma „za mało par” — z G13), osobno dla NDVI i NDMI.
- **Słabsze niż zwykle:** Δ ≤ −T. **Mocniejsze niż zwykle:** Δ ≥ +T. Pomiędzy: „jak zwykle” (bez koloru).
- Przy samym szumie |Δ| ≥ T zdarza się rzadko: T to 1,96·√2 odchylenia pojedynczego pomiaru [W].
- Komórka bez normy (U5): szara, „za krótka historia”.

## 5. Z2 — jak często mapa coś pokazuje (opisowo)

- Udział komórek z Δ ≤ −T we wszystkich scenach VI–IX lat testowych; osobno w dniach, gdy gleba okolicy jest w normie
  (percentyl ERA5-Land 0–100 cm 30–70, jak karta wody).
- Oczekiwane przy samym szumie: rzędu 1%. Dużo więcej przy glebie w normie oznacza, że norma miejsca źle pasuje
  (np. zmiany gospodarowania) — raportujemy, nie poprawiamy po fakcie.

## 6. Kryterium: czy pokazujemy warstwę winiarzom (U3)

Warstwa trafia do panelu i raportu **tylko gdy oba warunki są spełnione** dla danego wskaźnika:

1. Z1 ma ≥ 30 par w G5 albo G13;
2. górna granica przedziału MDC95 jest **mniejsza niż połowa** typowego zróżnicowania działki: mediany (po działkach
   i scenach VI–IX) rozstępu p90 − p10 wartości r. Inaczej szum jest porównywalny z tym, co mapa ma pokazać [K].

Niespełnione: panel pokazuje dalej tylko strefy bez historii, a blog i raport piszą „warstwa historii stref nie
przeszła testu szumu (MDC … wobec zróżnicowania …)”.

## 7. Co pokazujemy

- Mapa: komórki „słabsze niż zwykle” (brąz) i „mocniejsze niż zwykle” (zieleń / błękit), reszta przezroczysta.
- Pod mapą: udział pasa działki słabszy niż zwykle, próg T, liczba scen i lat w normie.
- Zdanie: „Ta część działki jest dziś słabsza względem reszty działki niż zwykle o tej porze (próg T = …, z testu
  szumu). To porównanie zdjęć satelitarnych, nie pomiar stanu winorośli.”
- Tabela „How far to trust it”: wiersz Z1 (MDC, n par), Z2 (udział), status `descriptive — noise-tested, not
  validated in the field`.

## 8. Ograniczenia znane przed liczeniem

- **Zmiany gospodarowania** (koszenie albo uprawa części międzyrzędzi, wymiana krzewów, nowe nasadzenia) wyglądają
  jak strefa słabsza niż zwykle. Flaga W3b §8 działa dla całej działki, nie dla części.
- **Nałożenie zdjęć** do 2021 r. było słabsze; norma z tych lat może być przesunięta. Wygładzenie 30 m i opis Z1 po
  latach to sprawdzają tylko częściowo [W].
- **Kąt widzenia:** różne tory widzą rzędy pod innym kątem; reguła toru jak W3b.
- **Brak prawdy terenowej:** test szumu mówi, kiedy zmiana jest większa niż szum satelity, a nie że dotyczy wody
  w winorośli.
- **Historia:** pełna 5-letnia norma od ok. 2021 r.; wcześniej wiele komórek bez normy (U5).

## 9. Wybory do akceptacji (U1–U5)

| | Wybór | Rekomendacja | Alternatywa |
|---|---|---|---|
| U1 | Wygładzenie | okno 3×3 (30 m), ≥ 5 z 9 pikseli | bez wygładzenia (10 m, głośniej) albo 5×5 (50 m, mniej szczegółu) |
| U2 | Próg mapy | T = MDC95 z testu szumu (G5) | stały próg, np. 0,05 (bez związku z szumem) |
| U3 | Kryterium pokazania | MDC95 (górna granica) < ½ typowego rozstępu p90 − p10 w działce | bez kryterium (zawsze pokazujemy) |
| U4 | Wskaźniki | NDVI i NDMI | także NDRE |
| U5 | Minimum historii | ≥ 5 scen i ≥ 3 lata | jak W3b: ≥ 5 scen, bez progu lat |
