# Plan wdrożenia W3b — „Moja winnica wobec jej historii” (Sentinel-2, 10 m)

Status: **PROPOSED** 2026-10-18, do akceptacji przed kodem. Rozwija specyfikację W3b z Planu v9 §5b (D-073)
o pytanie winiarza z 2026-10-18. Decyzje D-084–D-089 (§8) czekają na zatwierdzenie.

## 0. Wynik w skrócie

1. **Pytanie winiarza:** „Jak wygląda **moja** winnica teraz wobec jej własnej historii?”
2. **Co dziś umiemy powiedzieć wiarygodnie:** jak sucha jest gleba w **okolicy** (~10 km). Walidacja na 3 stacjach
   w W2 + REF dała R 0,57–0,68.
3. **Czego brakuje:** informacji z **samej działki**. Daje ją Sentinel-2 (piksel 10–20 m). Sentinel-2 nie mierzy
   jednak wody w glebie, tylko reakcję roślinności: winorośl i międzyrzędzie razem, z opóźnieniem ok. 1 miesiąca (F7).
4. **Plan:**
   - liczymy anomalię roślinności działki wobec jej własnej historii i wobec sąsiednich winnic;
   - sprawdzamy ją trzema testami zapisanymi przed liczeniem (V1–V3):
     - V1: czy różnica to sygnał, a nie szum;
     - V2: czy „poniżej normy” zdarza się tak rzadko, jak twierdzimy;
     - V3: czy roślinność reaguje na suszę w glebie;
   - pokazujemy wynik na karcie „Moja winnica” od sezonu 2027;
   - w sezonie 2027 zbieramy prawdę terenową w winnicy (V4, metoda wierzchołków pędów IFV).
5. **Uczciwa granica:** do wyniku V4 karta mówi „roślinność działki wygląda gorzej / tak samo / lepiej niż zwykle”.
   Nie mówi „winorośl cierpi na brak wody”. Rozdzielenie winorośli i międzyrzędzia to dalszy krok (Plan v8, moduł 3).
6. **Termin:**
   - zima 2026/27: dane, testy V1–V3, karta;
   - sezon 2027: karta działa w czasie prawie rzeczywistym, zbieramy obserwacje terenowe;
   - po zbiorach 2027: wynik V4 i decyzja, co karta może twierdzić.

## 1. Co Sentinel-2 mówi o winnicy — literatura i nasze wyniki

| Źródło | Co pokazuje | Co z tego bierzemy |
|---|---|---|
| Laroche-Pinel i in. 2021, *Remote Sensing* 13(9): 1837, doi:10.3390/rs13091837 [P] | 36 działek w latach 2018–2020; potencjał wodny pędu (pomiar w terenie) przewidywany z pasm S-2 (czerwone, NIR, red-edge, SWIR): R² = 0,40, RMSE = 0,26 | S-2 niesie umiarkowaną informację o stanie wody winorośli. To związek modelu uczonego na pomiarach terenowych. Prosta anomalia jednego wskaźnika go nie daje. Bez własnych pomiarów nie podajemy stanu wody winorośli |
| Nasze F7 (`docs/evidence/F7_v12/README.md`) | NDMI w tym samym dniu wobec czujnika ISMN w Condom: R 0,40 [0,16; 0,60]; alarm z NDVI bez trafień; indeksy prawie redundantne (NDVI–NDMI 0,92) | roślinność reaguje z opóźnieniem; NDVI i NDMI to nie dwa niezależne potwierdzenia |
| Nasze F4 (`docs/evidence/F4_eksperymenty/`) | wilgotność gleby z S-2 nie dodaje informacji ponad ERA5 | nie liczymy wilgotności gleby z S-2 |
| IFV, metoda wierzchołków pędów (apex), aplikacja ApeX Vigne [W] | ok. 50 wierzchołków na działkę klasyfikowanych jako: pełny wzrost / spowolniony / zatrzymany; indeks wzrostu przypisany przez IFV do poziomów ograniczenia wodnego | tania prawda terenowa, którą może zebrać sam winiarz (V4) |
| Rozdział winorośl / międzyrzędzie z serii LAI S-2 (OENO One 2023) [W]; S-2 w winnicach z zadarnionym międzyrzędziem (UCLouvain) [W] | sygnał działki to suma winorośli i międzyrzędzia; da się je częściowo rozdzielić modelem | do Planu v8, moduł 3; w W3b piszemy wprost, że to sygnał całej działki |

[P] — przeczytany abstrakt i metadane; [W] — z wyszukiwania, do przeczytania w notatce W3b.0.

## 2. Etap 0 — domknięcie warstwy gleby (przed W3b, zgodnie z kolejnością §0 Planu v9)

| Krok | Co | Sesje |
|---|---|---|
| 0a | Test zapisany w W3a §5: czy „ERA5 i SWI zgodnie suche” wykrywa suche dekady lepiej niż sam ERA5 (POD/FAR, bootstrap po sezonach) | 1 |
| 0b | Nagłówek karty: 3 klasy (sucho / w normie / wilgotno) zamiast 5 stopni (D-088); stopień i percentyl niżej jako szczegół | razem z 0a |
| 0c | A5: ponowne oszacowanie prawdopodobieństwa na karcie (Brier na innych latach niż dopasowanie) | 1 |
| 0d | W1b+: sekcja „Jak to liczymy” (źródła, rozdzielczość, opóźnienie, wynik walidacji każdej liczby) | 1 |

## 3. Kroki W3b

| Krok | Co | Wynik | Sesje |
|---|---|---|---|
| **W3b.0** | Notatka metodyczna `docs/evidence/W3b_moja_winnica_metoda.md`: przeczytane źródła z §1, reguły QC działki, definicje anomalii, sformułowania na karcie | notatka + decyzje D-084–D-089 | 1 |
| **W3b.1** | **Protokół walidacji V1–V3** (§4), zapisany i zahaszowany (SHA-256) **przed** policzeniem anomalii działek na 10 m | `docs/evidence/W3b_protokol_walidacji.md` | 1 |
| **W3b.2** | Statystyki działek ze wszystkich scen 2016–2026 (rastry z Dysku): `task_area_stats` — dla 22 działek średnia i mediana NDMI/NDVI z pikseli po zwężeniu obrysu (D-085), odsetek pikseli bezchmurnych, liczba pikseli; przyrostowo per działka i scena | `area_stats.csv` | 1–2 |
| **W3b.3** | Anomalie: (a) z działki wobec **jej własnej historii** (`scene_anomaly`: ten sam tor orbity, ±15 dni, 5 wcześniejszych lat, z predykcyjne z rozkładu t, min. 5 scen); (b) z **na tle sąsiednich winnic** (z działki minus mediana z pozostałych winnic tej sceny, min. 5 winnic); (c) mapa z pikseli działki dla ostatniej sceny; (d) zmiana od poprzedniej sceny | `area_anomalies.csv`, GeoTIFF + PNG mapy | 1–2 |
| **W3b.4** | Przebieg V1–V3 w Colab; notatka wyników `docs/evidence/W3b_wyniki.md`; wiersze w `karta_wynikow.md` | wynik niezależnie od kierunku | 1 |
| **W3b.5** | Karta „Moja winnica” (§5) w dashboardzie, biuletynie (EN), `agriwatch_latest.json`, `run_summary.md`; sekcja notatnika generowana przez `build_colab_master.py`; testy w selfteście | karta | 1–2 |
| **W3b.6** | **Dowolna winnica** (§6): obrys z pliku GeoJSON na Dysku, kontrola wymagań, pobranie scen dla nowej działki tym samym źródłem, ERA5 i SWI w jej punkcie; próba na drugiej winnicy poza obecnym obszarem | działa dla ≥ 2 winnic | 1–2 |
| **W3b.7** | **Prawda terenowa, sezon 2027 (V4):** protokół obserwacji wierzchołków pędów (IFV) i dziennik zabiegów (§4, V4); prośba do IFV Sud-Ouest i Chambre d'agriculture du Gers o dane historyczne | wynik V4 po zbiorach 2027 | 1 + sezon |

Razem: ok. 8–11 sesji pracy oraz sezon obserwacji 2027.

## 4. Walidacja — co sprawdzamy i jak (szkic protokołu W3b.1)

Brakuje pomiaru wody winorośli w działce, dlatego każdy test odpowiada na węższe pytanie. Karta podaje tylko to,
co testy potwierdziły.

| Test | Pytanie | Jak | Co trafia na kartę |
|---|---|---|---|
| **V1 Powtarzalność** | Czy różnica między działką a jej normą to sygnał, czy szum? | pary bezchmurnych scen w odstępie ≤ 5 dni (z różnych torów orbity): korelacja z działek między scenami w parze; najmniejsza wykrywalna zmiana (MDC95 = 1,96·√2·SEM) | „zmiana od poprzedniej sceny” tylko powyżej MDC95; strefy w działce tylko, gdy utrzymują się w 2 kolejnych scenach |
| **V2 Kalibracja** | Czy „poniżej swojej normy” zdarza się tak często, jak mówi statystyka? | sceny, gdy gleba ERA5 jest w normie (percentyl 30–70) w dniu sceny i 45 dni wcześniej: odsetek z ≤ −1 i ≤ −1,5 wobec oczekiwanego z rozkładu t; CI z bootstrapu po latach | jeśli odsetek jest wyraźnie za wysoki, słowa na karcie łagodniejsze („odbiega od normy” zamiast „rzadko spotykane”) |
| **V3 Reakcja na suszę w glebie** | Czy roślinność winnic reaguje na suszę w glebie z opóźnieniem? | ρ Spearmana: mediana z winnic obszaru wobec anomalii gleby ERA5 średnio 30–60 dni wcześniej, VI–IX, bootstrap po sezonach; to samo dla SWI i ISMN (do 2024) | wiersz „Na ile ufać”: „roślinność winnic w okolicy reaguje na suszę w glebie z opóźnieniem ok. 1–2 miesięcy (ρ = …)” |
| **V4 Prawda terenowa** (2027) | Czy anomalia działki mówi coś o wodzie winorośli? | co tydzień od kwitnienia do zmiany barwy jagód: wierzchołki pędów (IFV, 50 pędów) w Twojej winnicy i, jeśli się da, w 2–3 sąsiednich; ρ z działki (najbliższa scena ≤ 3 dni) wobec indeksu wzrostu | dopiero po V4 decyzja, czy karta może mówić o wodzie winorośli |

**Co już widzieliśmy (zapis uczciwości):** F7 policzyło VINEYARD_06 wobec ISMN w latach 2018–2024 (NDVI, NDRE, NDMI;
SR 2,5 m), a sprawdzenie opóźnienia 30–60 dni było post hoc. Dlatego w V3:
- **miarą główną** jest mediana pozostałych 14 winnic na 10 m wobec ERA5;
- VINEYARD_06 raportujemy osobno jako „nie niezależny”;
- **potwierdzeniem** są sezony 2025–2026, których F7 nie widziało.

**Zakłócenia, które opisujemy wprost:** koszenie lub uprawa międzyrzędzia, ogławianie, zbiór i opadanie liści dają
zmiany niezwiązane z wodą. Częściowo usuwa je porównanie z sąsiadami (wspólna pogoda i orbita). Zabiegów w działce
nie usuwa — dlatego dziennik zabiegów winiarza (data, rodzaj). Sceny do 10 dni po zabiegu są na karcie oznaczone
„po zabiegu — porównanie niepewne”.

## 5. Karta „Moja winnica” (zaraz pod kartą wody)

| Element | Treść (przykład) | Podstawa |
|---|---|---|
| **Gleba w okolicy** | „Sucho w glebie (percentyl 8); satelita potwierdza” | W2 + REF, W3a |
| **Twoja winnica** | „Roślinność działki (winorośl i międzyrzędzie) wyraźnie poniżej swojej normy z tej pory roku: NDMI z = −1,6 (scena 21.09)” | V1, V2 |
| **Na tle sąsiadów** | „9 z 15 winnic w okolicy też poniżej normy; Twoja 4. najniżej” — gdy wszyscy są niżej, to raczej pogoda niż działka | V2 |
| **Zmiana** | „Od poprzedniej sceny (16.09) bez istotnej zmiany” / „pogorszenie powyżej progu szumu” | V1 |
| **Mapa działki** | piksele z w obrysie; strefy opisane tylko, gdy utrzymują się w 2 scenach; „szczegół ok. 20 m (pasmo SWIR)” | V1 |
| **Zgodność gleby i roślinności** | stałe reguły: oba sucho → „spójny obraz suszy”; gleba sucha, roślinność w normie → „roślinność jeszcze nie reaguje albo korzenie sięgają głębiej — nie rozstrzygamy”; gleba w normie, roślinność niżej → „przyczyna raczej w działce (zabieg, choroba, uprawa międzyrzędzia) — sprawdź na miejscu” | V3 |
| **Na ile ufać** | wyniki V1–V3; „stanu wody samej winorośli nie mierzymy — sprawdzamy to w sezonie 2027” | — |
| **Stopka** | data sceny, wiek danych, odsetek pikseli bezchmurnych, „bez zaleceń zabiegów” | — |

Bez klas bezwzględnych „zdrowe / stres” (D-081).

## 6. „Dowolna winnica” — wymagania wobec działki

AgriScreen ma działać dla dowolnego pola. Działka musi jednak spełnić minimum, bez którego anomalia „wobec własnej
historii” nie ma sensu:
- **wielkość:** po zwężeniu obrysu o 20 m co najmniej 10 pikseli 20 m (ok. 0,4 ha);
- **historia:** co najmniej 5 lat tej samej uprawy. Nowe nasadzenie albo karczowanie niszczy normę. Kontrola: skok
  mediany sezonowej NDVI wobec lat wcześniejszych → „historia niejednorodna, porównanie z normą wyłączone”;
- **sąsiedzi:** porównanie „na tle sąsiadów” tylko przy ≥ 5 bezchmurnych winnicach w tej samej scenie;
- **dane:** to samo źródło i ta sama maska chmur dla historii i dla bieżącej sceny (D-084).

Obrys winiarz wgrywa jako GeoJSON do `MyDrive/GeoWorldLook/fields/`. Potok liczy wtedy kartę wody (ERA5, SWI w punkcie
działki) i kartę „Moja winnica”.

## 7. Kiedy uznajemy temat za domknięty

1. Każda liczba na karcie „Moja winnica” ma wynik walidacji (V1–V3) albo napis „niezwalidowane”.
2. Wyniki V1–V3 opisane w `W3b_wyniki.md` niezależnie od kierunku; wiersze w karcie wyników.
3. Karta działa dla co najmniej 2 winnic (VINEYARD_06 i jednej spoza obecnego obszaru).
4. Czas prawie rzeczywisty: karta aktualizuje się w przebiegu po pojawieniu się nowej bezchmurnej sceny i podaje
   jej wiek.
5. Po sezonie 2027 jest wynik V4. Jeśli V4 pokaże związek, karta może mówić ostrożnie o wodzie winorośli. Jeśli nie
   pokaże, karta zostaje przy „reakcja roślinności działki”, a próbą poprawy jest rozdzielenie winorośli
   i międzyrzędzia (Plan v8, moduł 3).

## 8. Decyzje do zatwierdzenia

- **D-084:** jedno źródło scen dla historii, bieżącej sceny i nowych działek: obecny potok (Sentinel-2 L2A
  zharmonizowany, maska chmur s2cloudless). Copernicus Data Space tylko jako zapas, po teście zgodności na wspólnym
  okresie (lekcja z wersji SWI).
- **D-085:** QC działki — zwężenie obrysu o 20 m dla NDMI (o 10 m dla NDVI), ≥ 80% pikseli bezchmurnych w działce,
  ≥ 10 pikseli 20 m; okno testów VI–IX.
- **D-086:** testy V1–V3 zapisane i zahaszowane przed liczeniem (W3b.1); V4 w sezonie 2027 z protokołem zapisanym
  przed sezonem.
- **D-087:** sformułowania — „roślinność działki (winorośl i międzyrzędzie)”, nigdy „stres wodny winorośli” przed
  V4; zmiana tylko powyżej MDC95; strefy tylko po 2 scenach; NDMI domyślnie, NDVI jako szczegół (nie jako drugie
  potwierdzenie).
- **D-088:** nagłówek karty wody w 3 klasach (sucho / w normie / wilgotno); stopień USDM i percentyl jako szczegół
  (propozycja z 2026-10-18).
- **D-089:** wymagania „dowolnej winnicy” z §6.

## 9. Ryzyka

| Ryzyko | Skutek | Co robimy |
|---|---|---|
| Chmury | bieżąca scena może mieć kilka–kilkanaście dni | wiek sceny na karcie; bez interpolacji |
| Mało winnic w scenie | brak porównania z sąsiadami | warunek ≥ 5; inaczej tylko własna historia |
| Zabiegi bez dziennika | fałszywe „poniżej normy” | porównanie z sąsiadami, dziennik od 2027, reguła zgodności gleba–roślinność |
| V4 to 1–3 działki × ~12 tygodni | test pilotażowy, mała moc | raportujemy jako pilotaż; prośba o dane IFV / Chambre d'agriculture |
| V3 wyjdzie słabo | roślinność winnic nie odzwierciedla suszy w glebie | wpisujemy wynik; karta pokazuje roślinność tylko jako opis działki |

## 10. Źródła

- Laroche-Pinel E., Duthoit S., Albughdadi M., Costard A. D., Rousseau J., Chéret V., Clenet H. 2021. Towards Vine Water
  Status Monitoring on a Large Scale Using Sentinel-2 Images. *Remote Sensing* 13(9): 1837.
  https://doi.org/10.3390/rs13091837 (HAL: https://hal.inrae.fr/hal-03247343) [P]
- IFV, aplikacja ApeX Vigne: https://www.vignevin.com/wp-content/uploads/2019/06/Appli_ApeX_Vigne_Site.pdf [W]
- Chambre d'agriculture de Tarn-et-Garonne, Bulletin agroécologie APEX VIGNE 2024 (przykład sieci obserwacji):
  https://agri82.chambre-agriculture.fr/fileadmin/user_upload/Occitanie/075_Inst-Tarn-et-Garonne/6-PDF_PAGES_STATIQUES/1-Productions_et_techniques/Viticulture-oenologie/Agroecologie_vigne/Bulletin_agroeco_APEX_VIGNE_2024_vf.pdf [W]
- Rozdział winorośl / międzyrzędzie z serii LAI Sentinel-2, OENO One 2023: https://oeno-one.eu/article/view/7703 [W]
- Zmienność stanu wody winorośli w działce z Sentinel-2, dwie winnice w Belgii (UCLouvain):
  https://research.dial.uclouvain.be/handle/2078.5/240791 [W]
- Wewnętrzne: Plan v9 §5b, `docs/evidence/F7_v12/README.md`, `docs/evidence/F4_eksperymenty/`,
  `docs/evidence/W2_REF_wyniki.md`.
