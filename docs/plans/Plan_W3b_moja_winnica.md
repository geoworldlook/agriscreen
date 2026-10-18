# Plan wdrożenia W3b — „Moja winnica wobec jej historii” (Sentinel-2, 10 m)

Status: **PROPOSED** 2026-10-18 (wersja 2), do akceptacji przed kodem. Rozwija specyfikację W3b z Planu v9 §5b (D-073)
o pytanie winiarza z 2026-10-18. Decyzje D-084–D-089 (§8) czekają na zatwierdzenie.

**Założenia (doprecyzowane 2026-10-18):**
- Walidacji terenowej w winnicy nie ma i nie będzie. Potwierdzamy wynik na danych, które mamy: czujnikach w gruncie
  (ISMN Condom, ICOS FR-Aur i FR-Lus), ERA5-Land i SWI.
- Literatura naukowa uzasadnia, jak połączyć te dane w jedną informację dla rolnika: czy jest anomalia względem
  historii tego pola, czy jej nie ma.
- ERA5 i SWI opisują okolicę. Sentinel-2 daje poziom działki. Docelowo rozplątanie kanałów siecią neuronową
  (Plan v8, moduły 2–3) oddzieli winorośl od międzyrzędzia.

## 0. Wynik w skrócie

1. **Pytanie rolnika:** czy moja działka jest teraz w anomalii względem swojej historii?
2. **Co już jest potwierdzone:** anomalia gleby w okolicy (~10 km). ERA5 i SWI wobec czujników na 3 stacjach dały
   R 0,52–0,68 (W2 + REF).
3. **Co dodaje W3b:** anomalię działki z Sentinel-2 (piksel 10–20 m) wobec jej własnej historii i wobec sąsiednich
   winnic. Sentinel-2 nie mierzy wody w glebie, tylko reakcję roślinności: winorośl i międzyrzędzie razem,
   z opóźnieniem ok. 1 miesiąca (F7, literatura §1).
4. **Jak to potwierdzamy bez pomiarów w winnicy** — trzy testy zapisane przed liczeniem:
   - **V1:** czy anomalia działki to sygnał, a nie szum;
   - **V2:** czy „poniżej normy” zdarza się tak rzadko, jak twierdzimy;
   - **V3:** czy anomalia Sentinel-2 w miejscu czujnika podąża za anomalią wody zmierzoną przez czujnik w gruncie,
     z opóźnieniem z literatury.
5. **Uczciwa granica:** karta mówi, czy roślinność działki jest w anomalii wobec swojej historii i czy zgadza się
   to z wodą w glebie okolicy. Nie mówi „winorośl cierpi na brak wody”, bo tego bez pomiaru w winnicy nie da się
   obronić. Rozplątanie kanałów (Plan v8) ma wydzielić sygnał samej winorośli; ocenimy je tymi samymi testami V1–V3
   (przed / po).
6. **Termin:** zima 2026/27, ok. 7–10 sesji. Karta działa w sezonie 2027 w czasie prawie rzeczywistym.

## 1. Literatura i nasze wyniki — jak łączymy dane

| Źródło | Co pokazuje | Co z tego bierzemy |
|---|---|---|
| Laroche-Pinel i in. 2021, *Remote Sensing* 13(9): 1837, doi:10.3390/rs13091837 [P] | 36 działek w latach 2018–2020; potencjał wodny pędu przewidywany z pasm S-2 (czerwone, NIR, red-edge, SWIR): R² = 0,40, RMSE = 0,26 | S-2 niesie umiarkowaną informację o wodzie winorośli, ale tylko przez model uczony na pomiarach terenowych. Pomiarów nie mamy, więc mówimy o anomalii roślinności, nie o stanie wody winorośli |
| Nasze F7 (`docs/evidence/F7_v12/README.md`) | NDMI w tym samym dniu wobec czujnika ISMN Condom: R 0,40 [0,16; 0,60]; roślinność reaguje z opóźnieniem (post hoc 30–60 dni); NDVI–NDMI korelacja 0,92 | opóźnienie 30–60 dni jako hipoteza do potwierdzenia na danych niewidzianych (V3); NDVI i NDMI to nie dwa niezależne potwierdzenia |
| Nasze F4 (`docs/evidence/F4_eksperymenty/`) | wilgotność gleby z S-2 nie dodaje informacji ponad ERA5 | nie liczymy wilgotności gleby z S-2; glebę opisują ERA5 i SWI |
| Rozdział winorośl / międzyrzędzie z serii LAI S-2 (OENO One 2023) [W]; S-2 w winnicach z zadarnionym międzyrzędziem (UCLouvain) [W] | sygnał działki to suma winorośli i międzyrzędzia; da się je częściowo rozdzielić modelem | uzasadnienie dla rozplątania kanałów (Plan v8, moduł 3); w W3b piszemy wprost, że to sygnał całej działki |

[P] — przeczytany abstrakt i metadane; [W] — z wyszukiwania, do przeczytania w notatce W3b.0. Notatka W3b.0 uzupełnia
literaturę o opóźnienie reakcji roślinności na suszę w glebie i o NDMI jako wskaźnik wody w liściach.

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
| **W3b.0** | Notatka metodyczna `docs/evidence/W3b_moja_winnica_metoda.md`: przeczytane źródła z §1, reguły QC działki, definicje anomalii, reguły łączenia gleby i roślinności, sformułowania na karcie | notatka + decyzje D-084–D-089 | 1 |
| **W3b.1** | **Protokół walidacji V1–V3** (§4), zapisany i zahaszowany (SHA-256) **przed** policzeniem anomalii działek na 10 m i przed pobraniem scen dla stacji ICOS | `docs/evidence/W3b_protokol_walidacji.md` | 1 |
| **W3b.2** | Statystyki działek z **już pobranych** scen 2016–2026 (414 rastrów na Dysku, bez nowego pobierania): istniejące `task_scene_stats` + `step_04.site_stats` liczą dziś tylko VINEYARD_06 i stację Condom (poligon i bufor 50 m); rozszerzamy listę obiektów do wszystkich 15 winnic i 5 sadów z `1_AOI_GBOV_CONDOM.geojson` (klucz `VINEYARDS`) i dodajemy zwężenie obrysu o 20 m dla NDMI (D-085; dziś 1 piksel = 10 m). Odsetek pikseli bezchmurnych (`clear_frac`) potok już zapisuje | wiersze w rejestrze obserwacji dla 20 działek | 1 |
| **W3b.3** | Sceny S-2 dla otoczenia czujników ICOS (FR-Aur, FR-Lus): ten sam potok i ta sama maska chmur (D-084), mały zasięg wokół stacji, 2017–dziś | statystyki w miejscu czujników | 1 |
| **W3b.4** | Anomalie: (a) z działki wobec **jej własnej historii** (`scene_anomaly`: ten sam tor orbity, ±15 dni, 5 wcześniejszych lat, z predykcyjne z rozkładu t, min. 5 scen); (b) z **na tle sąsiednich winnic** (z działki minus mediana z pozostałych winnic tej sceny, min. 5 winnic); (c) mapa z pikseli działki dla ostatniej sceny; (d) zmiana od poprzedniej sceny | `area_anomalies.csv`, GeoTIFF + PNG mapy | 1–2 |
| **W3b.5** | Przebieg V1–V3 w Colab; notatka wyników `docs/evidence/W3b_wyniki.md`; wiersze w `karta_wynikow.md` | wynik niezależnie od kierunku | 1 |
| **W3b.6** | Karta „Moja winnica” (§5) w dashboardzie, biuletynie (EN), `agriwatch_latest.json`, `run_summary.md`; sekcja notatnika generowana przez `build_colab_master.py`; testy w selfteście | karta | 1–2 |
| **W3b.7** | **Dowolna winnica** (§6): obrys z pliku GeoJSON na Dysku, kontrola wymagań, pobranie scen dla nowej działki tym samym źródłem, ERA5 i SWI w jej punkcie; próba na drugiej winnicy poza obecnym obszarem | działa dla ≥ 2 winnic | 1 |

Razem: ok. 8–10 sesji. Nowe sceny pobieramy tylko przyrostowo (bieżący sezon, czas prawie rzeczywisty), dla otoczenia
stacji ICOS (W3b.3) i dla winnic spoza obecnego obszaru (W3b.7).

**Potem:** rozplątanie kanałów siecią neuronową (Plan v8, moduły 2–3). Miara sukcesu: te same testy V1–V3
na tych samych danych, przed i po (D-070).

## 4. Walidacja na danych, które mamy (szkic protokołu W3b.1)

Pomiaru wody winorośli w działce nie mamy. Potwierdzamy więc to, co da się potwierdzić danymi: że anomalia działki
nie jest szumem, że jest dobrze skalibrowana i że w miejscach z czujnikiem w gruncie podąża za zmierzoną wodą w glebie.

| Test | Pytanie | Dane | Jak | Co trafia na kartę |
|---|---|---|---|---|
| **V1 Powtarzalność** | Czy anomalia działki to sygnał, czy szum? | archiwum S-2, 20 działek | pary bezchmurnych scen w odstępie ≤ 5 dni (z różnych torów orbity): korelacja z działek w parach; najmniejsza wykrywalna zmiana (MDC95 = 1,96·√2·SEM) | „zmiana od poprzedniej sceny” tylko powyżej MDC95; strefy w działce tylko, gdy utrzymują się w 2 kolejnych scenach |
| **V2 Kalibracja** | Czy „poniżej swojej normy” zdarza się tak często, jak mówi statystyka? | archiwum S-2, ERA5 | sceny, gdy gleba ERA5 jest w normie (percentyl 30–70) w dniu sceny i 45 dni wcześniej: odsetek z ≤ −1 i ≤ −1,5 wobec oczekiwanego z rozkładu t; CI z bootstrapu po latach | jeśli odsetek jest wyraźnie za wysoki, łagodniejsze słowa („odbiega od normy” zamiast „rzadko spotykane”) |
| **V3 Zgodność z czujnikiem w gruncie** | Czy anomalia S-2 w miejscu czujnika podąża za anomalią wody zmierzoną przez czujnik? | czujniki: Condom (ISMN, po A4, 2016–2024), FR-Lus (ICOS, 2023–dziś), FR-Aur (ICOS, 2019–2025); S-2 w otoczeniu czujnika | ρ Spearmana: anomalia NDMI wobec własnej historii piksela a anomalia czujnika średnio 30–60 dni wcześniej (okno z F7 i literatury, ustalone przed liczeniem), VI–IX, bootstrap po sezonach; obok ta sama miara dla ERA5 i SWI zamiast czujnika | wiersz „Na ile ufać”: „anomalia roślinności podąża za wodą w glebie zmierzoną w gruncie z opóźnieniem ok. 1–2 miesięcy (ρ = … na 3 stacjach)” |
| **V3b Spójność w obszarze** | Czy winnice obszaru razem reagują na suszę w glebie okolicy? | archiwum S-2, 15 winnic, ERA5, SWI | ρ: mediana z winnic a anomalia gleby ERA5 i SWI 30–60 dni wcześniej, VI–IX, bootstrap po sezonach | wiersz „Na ile ufać” |

**Co już widzieliśmy (zapis uczciwości):** F7 policzyło VINEYARD_06 wobec ISMN Condom w latach 2018–2024 (SR 2,5 m),
a opóźnienie 30–60 dni sprawdzono post hoc. Dlatego:
- **miarą główną V3** są stacje ICOS (FR-Lus, FR-Aur), których z Sentinel-2 jeszcze nie liczyliśmy;
- Condom raportujemy obok jako „częściowo widziany wcześniej”;
- w V3b miarą główną jest mediana 14 winnic bez VINEYARD_06, potwierdzeniem sezony 2025–2026.

**Ograniczenia stacji ICOS, zapisane przed liczeniem:**
- FR-Lus to łąka, którą się kosi. Koszenie daje spadki NDMI niezwiązane z wodą, a dat koszenia nie znamy.
  Możliwa kontrola: metadane zabiegów w danych ICOS (do sprawdzenia w W3b.0).
- FR-Aur to pole uprawne z płodozmianem. „Własna historia piksela” miesza różne uprawy, więc anomalię liczymy tylko
  wobec lat z tą samą uprawą, jeśli dane ICOS o uprawach na to pozwolą; inaczej FR-Aur tylko opisowo.
- Łąka i pole to nie winnica: V3 sprawdza, czy metoda anomalii S-2 wiąże się z wodą w glebie, nie reakcję winorośli.

**Zakłócenia w winnicach:** koszenie lub uprawa międzyrzędzia, ogławianie, zbiór i opadanie liści. Część usuwa
porównanie z sąsiednimi winnicami (wspólna pogoda i orbita); resztę opisujemy regułą zgodności gleba–roślinność (§5).

## 5. Karta „Moja winnica” (zaraz pod kartą wody)

| Element | Treść (przykład) | Podstawa |
|---|---|---|
| **Gleba w okolicy** | „Sucho w glebie (percentyl 8); satelita potwierdza” | W2 + REF, W3a |
| **Twoja działka** | „Roślinność działki (winorośl i międzyrzędzie) wyraźnie poniżej swojej normy z tej pory roku: NDMI z = −1,6 (scena 21.09)” albo „w normie” | V1, V2 |
| **Na tle sąsiadów** | „9 z 15 winnic w okolicy też poniżej normy; Twoja 4. najniżej” — gdy wszyscy są niżej, przyczyną jest raczej pogoda niż działka | V2, V3b |
| **Zmiana** | „Od poprzedniej sceny (16.09) bez istotnej zmiany” albo „pogorszenie powyżej progu szumu” | V1 |
| **Mapa działki** | piksele z w obrysie; strefy opisane tylko, gdy utrzymują się w 2 scenach; „szczegół ok. 20 m (pasmo SWIR)” | V1 |
| **Zgodność gleby i działki** | stałe reguły: oba sucho → „spójny obraz suszy”; gleba sucha, działka w normie → „roślinność jeszcze nie reaguje (opóźnienie ok. 1–2 miesięcy) albo korzenie sięgają głębiej — nie rozstrzygamy”; gleba w normie, działka niżej → „przyczyna raczej w samej działce (zabieg, uprawa międzyrzędzia, choroba)” | V3, V3b |
| **Na ile ufać** | wyniki V1–V3; „wody w samej winorośli nie mierzymy” | — |
| **Stopka** | data sceny, wiek danych, odsetek pikseli bezchmurnych, „bez zaleceń zabiegów” | — |

Bez klas bezwzględnych „zdrowe / stres” (D-081).

## 6. „Dowolna winnica” — wymagania wobec działki

Anomalia „wobec własnej historii” ma sens tylko wtedy, gdy działka spełnia minimum:
- **wielkość:** po zwężeniu obrysu o 20 m co najmniej 10 pikseli 20 m (ok. 0,4 ha);
- **historia:** co najmniej 5 lat tej samej uprawy. Nowe nasadzenie albo karczowanie niszczy normę. Kontrola: skok
  mediany sezonowej NDVI wobec lat wcześniejszych → „historia niejednorodna, porównanie z normą wyłączone”;
- **sąsiedzi:** porównanie „na tle sąsiadów” tylko przy ≥ 5 bezchmurnych winnicach w tej samej scenie;
- **dane:** to samo źródło i ta sama maska chmur dla historii i dla bieżącej sceny (D-084).

Obrys rolnik wgrywa jako GeoJSON do `MyDrive/GeoWorldLook/fields/`. Potok liczy wtedy kartę wody (ERA5 i SWI w punkcie
działki) i kartę „Moja winnica”.

## 7. Kiedy uznajemy temat za domknięty

1. Każda liczba na karcie „Moja winnica” ma wynik testu (V1–V3) albo napis „niezwalidowane”.
2. Wyniki V1–V3 opisane w `W3b_wyniki.md` niezależnie od kierunku; wiersze w karcie wyników.
3. Karta działa dla co najmniej 2 winnic (VINEYARD_06 i jednej spoza obecnego obszaru).
4. Czas prawie rzeczywisty: karta aktualizuje się po pojawieniu się nowej bezchmurnej sceny i podaje jej wiek.
5. Wynik V1–V3 jest punktem „przed” dla rozplątania kanałów (Plan v8, moduły 2–3).

## 8. Decyzje do zatwierdzenia

- **D-084:** jedno źródło scen dla historii, bieżącej sceny, stacji ICOS i nowych działek: obecny potok i pobrane już
  archiwum (Sentinel-2 L2A zharmonizowany, maska chmur s2cloudless; 414 scen 2016–2026 na Dysku). Copernicus Data
  Space tylko jako zapas, po teście zgodności na wspólnym okresie (lekcja z wersji SWI).
- **D-085:** QC działki — zwężenie obrysu o 20 m dla NDMI (o 10 m dla NDVI), ≥ 80% pikseli bezchmurnych w działce,
  ≥ 10 pikseli 20 m; okno testów VI–IX.
- **D-086:** walidacja bez pomiarów w winnicy: testy V1–V3 na czujnikach w gruncie (Condom, FR-Lus, FR-Aur), ERA5
  i SWI, zapisane i zahaszowane przed liczeniem (W3b.1); miarą główną V3 są stacje ICOS.
- **D-087:** sformułowania — „roślinność działki (winorośl i międzyrzędzie)”, nigdy „stres wodny winorośli”; zmiana
  tylko powyżej MDC95; strefy tylko po 2 scenach; NDMI domyślnie, NDVI jako szczegół (nie jako drugie potwierdzenie).
- **D-088:** nagłówek karty wody w 3 klasach (sucho / w normie / wilgotno); stopień USDM i percentyl jako szczegół
  (propozycja z 2026-10-18).
- **D-089:** wymagania „dowolnej winnicy” z §6.

## 9. Ryzyka

| Ryzyko | Skutek | Co robimy |
|---|---|---|
| Chmury | bieżąca scena może mieć kilka–kilkanaście dni | wiek sceny na karcie; bez interpolacji |
| Mało winnic w scenie | brak porównania z sąsiadami | warunek ≥ 5; inaczej tylko własna historia |
| Zabiegi w działce (koszenie, uprawa) | fałszywe „poniżej normy” | porównanie z sąsiadami, reguła zgodności gleba–działka |
| Koszenie FR-Lus, płodozmian FR-Aur | słabszy V3 z przyczyn niezwiązanych z wodą | zapisane przed liczeniem; Condom obok |
| V3 wyjdzie słabo | anomalia S-2 nie podąża za wodą w glebie | wpisujemy wynik; karta pokazuje działkę tylko jako opis roślinności, a rozplątanie kanałów ma to poprawić |

## 10. Źródła

- Laroche-Pinel E., Duthoit S., Albughdadi M., Costard A. D., Rousseau J., Chéret V., Clenet H. 2021. Towards Vine Water
  Status Monitoring on a Large Scale Using Sentinel-2 Images. *Remote Sensing* 13(9): 1837.
  https://doi.org/10.3390/rs13091837 (HAL: https://hal.inrae.fr/hal-03247343) [P]
- Rozdział winorośl / międzyrzędzie z serii LAI Sentinel-2, OENO One 2023: https://oeno-one.eu/article/view/7703 [W]
- Zmienność stanu wody winorośli w działce z Sentinel-2, dwie winnice w Belgii (UCLouvain):
  https://research.dial.uclouvain.be/handle/2078.5/240791 [W]
- Wewnętrzne: Plan v9 §5b, `docs/evidence/F7_v12/README.md`, `docs/evidence/F4_eksperymenty/`,
  `docs/evidence/W2_REF_wyniki.md`, `docs/evidence/REF_obszar_pomocniczy_ICOS.md`.
