# W3c — wyniki: „strefa gorsza niż zwykle” (pierwszy przebieg, 2026-10-20)

> Protokół: `docs/evidence/W3c_protokol_strefy.md`, zarejestrowany 2026-10-20 (D-090), SHA-256
> `45708189b130b6c87edded38b32691b8fc20a9659a772e57693da43424dab326` — ten sam skrót w `w3c_tests.csv`.
> Dane: archiwum projektu, 419 scen, zamrożenie 2026-10-18 (`w3c_freeze.json`, SHA-256 listy scen `96d70cb4…`);
> 13 winnic z QC; żadna scena nie wypadła z powodu innej siatki. Kod `a52d7a1` (oznaczenie `+dirty` w pliku wyników
> pochodzi od zapisanego w Colab notatnika — kolejny commit, acc201b, zmienia tylko notatnik).

## Wynik w jednym zdaniu

**Warstwa „Zones vs usual” nie przeszła kryterium dla żadnego wskaźnika i nie trafia do panelu ani raportów.**
Szum satelity jest mały, ale „zwykły układ” miejsc w działkach zmienia się z roku na rok tak bardzo, że mapa
świeciłaby na ok. 15% powierzchni działek nawet wtedy, gdy gleba jest w normie (oczekiwane przy samym szumie: ok. 1%).

## Liczby (zgodnie z protokołem)

| | NDVI | NDMI |
|---|---|---|
| Z1: szum, MDC95 z par G5 (689 par, 2019–2026) | 0,033 [0,025; 0,041] | 0,023 [0,017; 0,029] |
| Z1: to samo z par G13 (848 par) | 0,035 [0,028; 0,042] | 0,024 [0,020; 0,029] |
| Próg mapy T | 0,033 | 0,023 |
| Typowy rozstęp p90 − p10 strefy dnia w działce (mediana 2878 scen działek) | 0,092 | 0,049 |
| **Warunek 1** (≥ 30 par) | spełniony | spełniony |
| **Warunek 2** (MDC95 górna < ½ rozstępu) | **spełniony** (0,041 < 0,046) | **niespełniony** (0,029 ≥ 0,025) |
| Z2: komórki w strefach przy glebie w normie (741 scen, 2019–2025) | 15,4% [9,9; 20,9] | 15,5% [10,3; 20,6] |
| — w tym słabsze / mocniejsze | 9,1% / 6,3% | 8,8% / 6,6% |
| — przed U6 (te same progi, bez minimalnej strefy) | 16,1% | 16,1% |
| — wszystkie dni VI–IX (2166 scen) | 15,5% [12,2; 18,9] | 14,9% [11,5; 18,2] |
| **Warunek 3** (Z2 górna ≤ 5%) | **niespełniony** | **niespełniony** |
| **Decyzja** | nie pokazujemy | nie pokazujemy |

Opisowo (§3): MDC per rok NDVI 0,020–0,042, NDMI 0,016–0,032; najniższe w 2022 i 2024, bez wyraźnego trendu.

## Co to znaczy (prosto)

- **Szum zdjęć jest mały.** Dwa zdjęcia tej samej winnicy z odstępem kilku dni, bez deszczu, różnią się w układzie
  wewnątrz działki o mniej niż ok. 0,03 NDVI w 95% przypadków (MDC95; typowa różnica ok. 0,017). Dla NDVI to mniej
  niż połowa typowego zróżnicowania działki (warunek 2 przeszedł).
- **Problemem jest „zwykle”.** W dni z glebą w normie, kiedy działka nie powinna mieć powodu, by wyglądać inaczej
  niż zwykle, ok. 15% komórek i tak wychodzi poza próg. Te miejsca tworzą duże plamy, nie pojedyncze piksele:
  minimalna strefa (U6) prawie nic nie zmienia (16% → 15%). Układ wewnątrz działki naprawdę zmienia się między latami.
- **Dlaczego trzeci warunek był potrzebny.** Test szumu porównuje zdjęcia z odstępem kilku dni, więc nie widzi
  różnic między latami. Bez warunku 3 warstwa NDVI zostałaby pokazana i oznaczałaby jako „słabsze niż zwykle”
  ok. 9% powierzchni działek w zwykłe dni.

## Skąd to się bierze (analiza po fakcie — opis, nie zmienia decyzji)

Policzone z `w3c_summary.csv` po zobaczeniu wyników; służy tylko do planowania, nie do poprawiania tej wersji.

| Rozbicie | NDVI | NDMI |
|---|---|---|
| Lata: 2019 → 2024–2026 | 22% → 10–13% | 22% → 9–15% |
| Winnice „spokojne” (06, 07, 09, 10, 15, 21) | 3–7% | 4–9% |
| Winnice „niespokojne” (12, 13, 14, 17, 22) | 21–31% | 17–28% |
| Pozostałe (08, 11) | 12–15% | 14–15% |
| Sceny bez żadnej strefy / mediana / 10% scen z najwięcej | 40% / 7% / ≥ 39% działki | 41% / 7% / ≥ 39% działki |

- **Lata:** w pierwszych latach norma jest krótsza, a nałożenie zdjęć do ok. 2021 r. słabsze (ograniczenie z §8).
- **Działki:** różnice między winnicami są duże. Dwie z „niespokojnych” (13 i 22) miały już flagę „możliwa zmiana
  gospodarowania” w W3b. Najbardziej prawdopodobne przyczyny to zmiany w uprawie części działki: koszenie albo
  uprawa co drugiego międzyrzędzia, okrywa, dosadzenia. Satelita widzi to tak samo jak zmianę kondycji.
- **Czy to na pewno winnice?** Tak. Rejestr upraw RPG (deklaracje rolników, IGN `apicarto.ign.fr/api/rpg/v2`,
  punkt w środku każdej działki, lata 2015–2024, `data/rpg_winnice.csv`): wszystkie 15 to **VRC** (winorośl na
  wino). Wyjątki: winnica 13 w 2019–2020 r. **VRN** (winorośl jeszcze nie owocująca, czyli młode nasadzenie),
  winnica 14 w 2016 r. **RVI** (restrukturyzacja: wykarczowanie i ponowne nasadzenie), winnica 22 w 2018 r. RVI
  oraz VRN w 2019 i 2022 r. Kod przesadzenia mają więc 3 z 5 „niespokojnych” winnic (13, 14, 22) i żadna z 8
  pozostałych; 12 i 17 są „niespokojne” bez takiego kodu. To jest zgodne z wyjaśnieniem przez zmiany w uprawie, ale
  go nie dowodzi (analiza po fakcie, jeden punkt na działkę — część działki mogła mieć inną deklarację).
- **Nawet „spokojne” winnice** (3–7%) są powyżej ok. 1% oczekiwanego przy samym szumie.

## Audyt (2026-10-20, przed wersją 1.0)

Niezależne przeliczenie Z2 i rozbić z `w3c_summary.csv` potwierdziło liczby tej notatki. Audyt znalazł jedną
niezgodność kodu z protokołem i jedno ograniczenie:

- **Gleba w normie.** Protokół (§0) odsyła do karty wody: percentyl w przedziale (30; 70). Kod pierwszego przebiegu
  liczył [30; 70], czyli z dniami o percentylu dokładnie 30 lub 70. Kod poprawiony w wersji 1.0. Z tą poprawką:
  728 zamiast 741 scen, Z2 NDVI 15,3% [9,8; 20,8], NDMI 15,6% [10,1; 21,2]. Decyzja bez zmian (warunek 3
  niespełniony). Liczby w tabeli wyżej zostają jako zapis pierwszego przebiegu.
- **Tory orbit a zamrożenie.** Numery torów (`track_ids`) są dopasowywane do wszystkich scen w magazynie, także tych
  po dacie zamrożenia. Nowe sceny mogą więc w zasadzie przesunąć przypisanie torów i zmienić zamrożone Z1 i Z2.
  Dotąd ponowne przebiegi dawały identyczne wyniki. Przy powtórce w 2027 r. sprawdzimy to wprost.

## Co pokazujemy

- Panel: bez warstwy „Zones vs usual”. W „How far to trust it” dwa wiersze ze statusem `experimental, not shown`
  i powodem. W wersji 1.0 kod W3c jest modułem eksperymentalnym (`agriscreen/experiments/zones.py`), domyślnie
  wyłączonym.
- Bez zmian zostają: mapy pikseli (opis), strefy wobec reszty działki tego samego dnia (opis) i cała działka
  wobec własnej historii (W3b).
- Ten wynik sam jest informacją na blog: sprawdziliśmy, zanim pokazaliśmy, i warstwa nie przeszła.

## Co dalej (do decyzji, bez zmian w tej wersji)

Protokół zabrania poprawiania metody po zobaczeniu wyniku w tej wersji. Każda nowa próba to nowy protokół,
zarejestrowany przed liczeniem i sprawdzony na **nowych danych** (sezon 2027), bo obecne wyniki już znamy.
Możliwe kierunki:

1. **Próg z własnej zmienności miejsca między latami** zamiast szumu z kilku dni: kolorować tylko to, co wykracza
   poza zwykłe wahania tego miejsca. Odpowiada wprost na znalezioną przyczynę.
2. **Pomijanie działek i sezonów z flagą zmiany gospodarowania**: prostsze, ale nie wyłapie zmian w części działki.
3. **Zostawić jak jest**: historia działki tylko dla całej działki (W3b), strefy tylko na dany dzień.
