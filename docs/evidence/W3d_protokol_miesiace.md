# W3d — protokół „Miejsce najniżej od 5 lat” (pre-rejestracja)

> **Status:** `REGISTERED` 2026-10-20 (D-091) · SHA-256 sekcji 0–8: `599a381bb6d15dfe9fa81186a34436815d2d0ea01970828a5aa90730ff6da30a`
> - Skrót liczy `sed -n '/^## 0\./,$p' docs/evidence/W3d_protokol_miesiace.md | sha256sum`. Ten sam skrót
>   `task_months` zapisuje w `w3d_tests.csv`.
> - **Jawnie:** pomysł powstał po wynikach W3c (`W3c_wyniki.md`): układ wewnątrz winnic zmienia się między latami,
>   a przesadzenia w rejestrze RPG pokrywają się z najbardziej „niespokojnymi” winnicami. Kody RPG (13, 14, 22)
>   widzieliśmy przed rejestracją; reguła §3 używa ich mechanicznie, dla wszystkich winnic. Wielkość z §2 nie była
>   jeszcze liczona. Zmiana przed pierwszym liczeniem w Colab = nowa wersja protokołu i nowy skrót.
> - **Zdanie dla winiarza:** „W lipcu 2026 to miejsce miało najniższą zieleń od 5 lat.” Bez oceny stanu winorośli,
>   bez porad.
> - **Literatura (podstawa wyborów):** porównanie miejsca z jego własną historią z tej samej pory roku — VCI (Kogan),
>   FORDEAD (INRAE), CCDC (Zhu i Woodcock 2014); stabilność układu w winnicy do zmiany w uprawie (Kazmierski i in.
>   2011, OENO One 45:61–73); piksel Sentinel-2 w winnicy miesza krzewy i międzyrzędzia (Khaliq i in. 2019,
>   Remote Sensing 11:436). Kod: `step_14_months.py`.

## 0. Dane i zamrożenie

- Sentinel-2 L2A z archiwum projektu (`S2_DIR`), miesiące IV–X; 13 winnic z QC W3b (≥ 40 pikseli w pasie 20 m).
- Rejestr upraw RPG (IGN, deklaracje rolników) w punkcie wewnątrz każdej winnicy, lata 2015–2024:
  `data/rpg_winnice.csv`. Lata bez danych RPG traktujemy jak „bez przesadzenia”.
- Zamrożenie testów: `W3D_FREEZE` = data ostatniej sceny przy pierwszym liczeniu (`w3d_freeze.json`). Test (§5)
  tylko na scenach ≤ tej daty; mapa także na nowszych.
- Gleba w normie: średni percentyl ERA5-Land 0–100 cm w miesiącu 30–70 (jak karta wody).
- Przedział 95%: jackknife po latach (jak W3b §0).

## 1. Kwadraty

- Piksele 10 m ze środkiem ≥ 20 m od brzegu winnicy (pas jak W3b).
- Wartość kwadratu w scenie: średnia wskaźnika z okna 3×3 pikseli (30 × 30 m), tylko z czystych pikseli pasa,
  gdy jest ich ≥ 5 z 9. Czysta scena winnicy: ≥ 90% pikseli pasa bez chmur; jedna scena na dzień.
- Wskaźniki: NDVI (zieleń) i NDMI (woda w roślinności), każdy osobno.

## 2. Miesiąc i porównanie z historią

1. **Wartość miesiąca:** mediana wartości kwadratu z czystych dni miesiąca kalendarzowego; potrzebne ≥ 2 dni.
2. **Historia:** ten sam kwadrat, ten sam miesiąc, lata Y−5…Y−1 z wartością miesiąca (bez lat wykluczonych w §3).
   Potrzebne N ≥ 4 lata; inaczej „za mało historii”.
3. **Klasa:**
   - **najniżej od N lat:** wartość niższa niż w każdym z N lat historii;
   - **najwyżej od N lat:** wyższa niż w każdym z N lat;
   - **w zakresie:** pomiędzy.
4. **Co jest normalne:** gdyby w miejscu nic się nie zmieniało, każdy z N + 1 lat ma te same szanse być najniższy,
   więc „najniżej od N lat” wypada w ok. 1/(N + 1) kwadratów (1 na 6 przy N = 5) czysto przypadkiem [W].

## 3. Przesadzenia (reset historii)

- Rok z kodem RPG **RVI** (restrukturyzacja: karczowanie i nasadzenie) albo **VRN** (winorośl jeszcze nie
  owocująca) to rok przesadzenia.
- Do historii roku Y wchodzą tylko lata **po** ostatnim roku przesadzenia przed Y. Rok Y będący rokiem przesadzenia
  nie dostaje klasy („przesadzana”).

## 4. Mapa

- Brąz: najniżej od N lat; zieleń (NDVI) / błękit (NDMI): najwyżej od N lat; „w zakresie”: bez koloru;
  „za mało historii” i „przesadzana”: szare.
- Pokazujemy tylko plamy ≥ 4 sąsiadujących pikseli (bokiem lub rogiem, ok. 400 m²); mniejsze bez koloru.
- Przy mapie stałe zdanie: „Przy samym przypadku ok. 1 na 6 miejsc jest najniżej od 5 lat. Ważne są duże plamy,
  które powtarzają się w kolejnych miesiącach.”

## 5. Test D1 — czy „najniżej / najwyżej od N lat” zdarza się tak często, jak powinno

- Kwadraty z klasą, miesiące VI–IX, lata ≤ zamrożenia, **miesiące z glebą w normie** (gdy takie miesiące są w < 3
  latach: wszystkie miesiące VI–IX).
- Miara: iloraz R = (udział kwadratów „najniżej”) / (średnie oczekiwane 1/(N + 1)); osobno R dla „najwyżej”.
  Liczone przed filtrem plam (§4), bo oczekiwanie dotyczy pojedynczych kwadratów. Przedział: jackknife po latach.
- **Kryterium pokazania wskaźnika:** górna granica przedziału R ≤ 1,5 **dla obu klas** i dane z ≥ 3 lat [K].
  Spełnione: warstwa trafia do panelu. Niespełnione: nie pokazujemy, a panel podaje liczby.
- Przy R = 1 mapa mówi prawdę o rzadkości: „najniżej od 5 lat” naprawdę zdarza się ok. raz na 6 lat w danym miejscu.
  R wyraźnie > 1 w zwykłe miesiące oznacza, że miejsca trwale się zmieniają (trend, uprawa) i klasa myli.

## 6. Opisowo (bez wpływu na decyzję)

- R w miesiącach suchych (percentyl < 30) i wilgotnych (> 70).
- Udział powierzchni w plamach (po §4); R po latach i po winnicach.
- Ile kwadratów nie ma klasy (za mało historii, przesadzenie).

## 7. Co pokazujemy

- Grupa warstw „Months vs own history” z wyborem miesiąca (IV–X, od pierwszego roku z historią).
- Pod mapą: udział winnicy „najniżej” i „najwyżej od N lat”, N, liczba dni w miesiącu i oczekiwany udział
  przypadkowy (1/(N + 1)).
- „How far to trust it”: R obu klas z przedziałem, status `calibration-tested, not validated in the field` albo
  `not shown`.

## 8. Ograniczenia znane przed liczeniem

- Piksel Sentinel-2 w winnicy widzi krzewy i międzyrzędzia; koszenie lub uprawa międzyrzędzi zmienia wartość tak
  samo jak zmiana kondycji krzewów.
- RPG sprawdzamy w jednym punkcie winnicy; przesadzenie części działki może nie mieć kodu. Lata 2025–2026 bez RPG.
- 2016 r. ma mało zdjęć (jeden satelita), wrzesień 2017 żadnego czystego; takie miesiące często bez wartości.
- „Najniżej od 5 lat” mówi o kolejności, nie o wielkości różnicy: miejsce może być najniżej o bardzo mało.
- Brak prawdy terenowej: test sprawdza rzadkość klasy, nie to, czy dotyczy wody lub zdrowia winorośli.
