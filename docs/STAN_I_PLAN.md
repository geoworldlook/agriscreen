# AgriScreen — stan i plan

Stan na 2026-10-20, wersja 1.0. Jedna strona do orientacji; szczegóły w dokumentach z §7.

**Cel:** winiarz widzi, czy jego działka jest teraz nietypowa wobec własnej historii. Nie dajemy zaleceń podlewania
ani zabiegów. Każda liczba ma wynik sprawdzenia i jego rodzaj (status) albo napis „not validated”.

## 1. Wersja 1.0 — produkt

- **Panel AgriScreen (EN)**: 15 winnic w okolicy Condom (Gers). Mapa na zdjęciu satelitarnym z półprzezroczystą
  warstwą: piksele 10 m (NDVI, NDRE, NDMI), strefy wobec reszty działki tego samego dnia albo cała działka wobec
  własnej historii (z). Obok: statystyki, stan działki, gleba w okolicy, pogoda (prognoza, ostatnie dni, przymrozki
  i upały), karta, sezon i „How far to trust it”. Jeden plik `panel.html` + dane `panel_data.json`.
- **Obliczenia na własnym komputerze (1.1):** folder `GeoWorldLook` na pulpicie (projekty, dane z Dysku Google,
  skrypty), przebieg co poniedziałek z Harmonogramu zadań, panel sam trafia na GitHub (`docs/URUCHOMIENIE_LOKALNE.md`).
- **Notatnik monitoringu** (Colab, `notebooks/AgriScreen_Monitor.ipynb`) zostaje jako zapas.
- **Notatnik na blog** (`notebooks/AgriScreen_story.ipynb`) czyta tylko `docs/showcase/` (bez kluczy).
- **Kod:** pakiet `agriscreen/` (`docs/ARCHITEKTURA.md`), test bez sieci `python -m agriscreen.selftest`.
  Przebudowa z modułów `step_*` niczego nie zmieniła w wynikach (regresja na tych samych danych syntetycznych:
  26 plików wynikowych identycznych; `CHANGELOG.md`).
- **Wycofane w 1.0:** super-rozdzielczość SEN2SR, status dekadowy w stylu EDO CDI, polski dashboard i biuletyn,
  gałąź Sentinel-1 (wszystko w historii git, ostatni commit przed 1.0: `82844ae`).

## 2. Co jest sprawdzone

| Co | Wynik | Status w panelu |
|---|---|---|
| Wilgotność gleby 0–100 cm (ERA5-Land) wobec czujników na 3 stacjach | R anomalii 0,57 Condom, 0,57 Auradé, 0,68 Lusignan (anomalie 35-dniowe); ta sama klasa 55–65% dni | checked (bez progu zaliczenia) |
| Satelitarny SWI (ASCAT) | R 0,57 / 0,52 / 0,53; zgodność klas z ERA5 63% | checked |
| Opad 30 dni (ERA5-Land) wobec deszczomierza Condom | R 0,90 | checked |
| Szum wskaźnika wody działki (T2) | MDC95 1,0 z (ten sam tor) / 1,1 z (różne tory) | descriptive |
| Kalibracja klasy „poniżej swojej normy” (T1) | 28% [4; 52] scen wobec 16%; po latach 1–76%; gleba w normie 14% [0; 30] | descriptive |
| Roślinność okolicy a czujnik w gruncie (T3, kryterium zdania 3) | ρ 0,55 [−0,02; 1,00] | not confirmed (zdanie 3 ukryte) |
| Model 4 pasm zamiast prostego wskaźnika (§7) | Δρ −0,01 [−0,18; 0,16] | not adopted |
| Stres wodny winorośli | brak pomiarów w winnicach | not validated |

Przymrozki: za mało zdarzeń do sprawdzenia. Wszystkie testy W3b według protokołu zarejestrowanego przed liczeniem
(D-089), zamrożone 2026-10-18; kolejny test na nowych danych: sezon 2027, te same reguły.

## 3. Anomalie miejsc wewnątrz winnicy — dwie próby, obie nie przeszły

| Próba | Pytanie | Wynik | Gdzie |
|---|---|---|---|
| W3c (D-090) | czy to miejsce jest dziś słabsze niż zwykle, względem reszty działki? | szum mały, ale w zwykłe dni mapa świeciłaby na ok. 15% powierzchni (limit 5%) | `docs/evidence/W3c_wyniki.md` |
| W3d (D-091) | czy kwadrat 30 m jest najniżej od 5 lat w tym miesiącu? | kierunek suchy / wilgotny poprawny; kalibracji nie da się ocenić (4 lata, 7 miesięcy z glebą w normie) | `docs/evidence/W3d_wyniki.md` |

W 1.0 to moduł eksperymentalny (`agriscreen/experiments/`, domyślnie wyłączony). Panel nie rysuje tych warstw;
pokazuje tylko wynik testu. Powtórka po sezonie 2027 z tymi samymi regułami.

## 4. Audyt wyników przed 1.0 (2026-10-20)

Niezależne przeliczenie z plików wynikowych potwierdziło liczby T1, T2, T3, §7, Z2 i D1. Poprawki objęły opis,
nie werdykty:

- statusy w panelu: „checked” i „descriptive” zamiast „validated” tam, gdzie nie było progu zaliczenia;
- T1 bez wybranej listy „lat suszy”; zamiast niej analiza dodatkowa według gleby w dniu sceny;
- W3d: 4 lata (nie 6), 12 winnic, bez „nie przesadza”;
- W3c i W3d: gleba w normie (30; 70) jak w protokołach (W3c Z2 15,4% → 15,3%, decyzja bez zmian).

Szczegóły: sekcje „Audyt” w `W3b_wyniki.md`, `W3c_wyniki.md`, `W3d_wyniki.md`.

## 5. Później (osobne decyzje)

| Co | Po czym | Uwagi |
|---|---|---|
| Powtórka W3b, W3c, W3d na sezonie 2027 | po sezonie 2027 | te same protokoły, nowe zamrożenie |
| Rozplątanie sygnału siecią neuronową (Plan v8): rzędy winorośli z ortofotomapy, winorośl a międzyrzędzie | po 1.0 | oceniane testami T1–T3; punkt odniesienia: prosty wskaźnik i model 4 pasm |
| Raport tygodniowy dla winiarza (mapa jako dowód, bez zaleceń) | po blogu i monitoringu na żywo | |
| Najbliższe 7 dni (W4), perspektywa 30 dni (W5), faza winorośli (W6) | po 1.0 | z Planu v9 |
| Dowolna działka (obrys od winiarza) | po 1.0 | wymagania: ok. 0,4 ha, 5 lat tej samej uprawy |
| Potok bez Colab (STAC, Docker, GitHub Actions) | po 1.0 | Plan v8 |

## 6. Czego nie robimy

- Nie mówimy „winorośl ma stres wodny” ani „wczesne ostrzeżenie” — tego nie da się obronić bez pomiarów w winnicy.
- Nie przenosimy wprost modelu z artykułu Laroche-Pinel: nie ma współczynników, a uczono go na pomiarach, których
  nie mamy. Bierzemy tylko zestaw pasm.
- Dane satelitarne tylko z programu Copernicus (D-048).

## 7. Gdzie co jest

| Temat | Dokument |
|---|---|
| Kod, moduły i zadania | `docs/ARCHITEKTURA.md` |
| Zmiany wersji | `CHANGELOG.md` |
| Wszystkie wyniki w jednej tabeli | `docs/evidence/karta_wynikow.md` |
| Protokoły i wyniki | `docs/evidence/W2_REF_*`, `W3b_*`, `W3c_*`, `W3d_*` |
| Publikacja na blogu | `docs/showcase/README.md` |
| Plany | `docs/plans/` (Plan v9, Plan W3b, Plan v8) |
