# W3b — przegląd literatury: wskaźnik „woda w liściach” dla działki (Sentinel-2), wersja 2

> **Status:** 2026-10-19. Zastępuje wersję 1 z 2026-10-18, która cytowała część prac tylko ze streszczeń.
> Plan: `docs/plans/Plan_W3b_moja_winnica.md` (wersja 5). Uzupełnia F3 §6–7.
>
> **Przeczytane w całości:** Ceccato i in. 2001; Laroche-Pinel i in. 2021 (*Remote Sensing*); Unnisa i in. 2025;
> Carletti i in. 2025; Choi i in. 2017. Cztery ostatnie to pliki PDF od użytkownika. Nie trzymamy ich w repozytorium,
> bo są chronione prawem autorskim. Kod FORDEAD sprawdzony w źródłach. Laroche-Pinel 2021 (*OENO One*) i Pantaleoni
> Reluy 2022 przeczytane wcześniej (F3).
>
> **Proces:** każdą pracę czytał osobny agent. Drugi agent sprawdzał każdy cytat i liczbę w tekście, a trzeci
> recenzował syntezę. Liczby oznaczone „nasze przeliczenie” lub „odczyt z wykresu” są przybliżone.
>
> Oznaczenia: [P] pełny tekst; [F3] pełny tekst opisany w F3; [D] nasze dane; [—] nieprzeczytane, nie służy jako
> uzasadnienie.

## Wynik w skrócie

1. **Żadna z prac nie bada tego, co robimy.** Nikt nie sprawdzał anomalii działki winnicy wobec jej własnej historii
   z tej samej pory roku, porównanej z wodą w glebie. Z literatury bierzemy fizykę, metodę i ostrzeżenia, a nie liczby
   do porównania.
2. **Wybór SWIR opiera się na fizyce, nie na dowodzie z winnic.**
   - Ceccato 2001: przy 1600 nm woda w liściu wyjaśnia 36% zmienności odbicia, a po podzieleniu przez NIR 87%.
   - W winnicach pojedyncze wskaźniki NIR–SWIR słabo przewidują stan wody winorośli. Laroche-Pinel 2021: NDII
     (prawie nasze NDMI) R² 0,09, MSI 0,10, NDVI 0,04; dopiero model z kilku pasm daje 0,40.
   - Unnisa 2025 nie badała żadnego wskaźnika SWIR.
   - Czy SWIR daje coś ponad zieleń, rozstrzygną dopiero nasze testy T1–T3.
3. **Wysokie liczby w literaturze w dużej części pochodzą z cyklu sezonowego.**
   - Laroche-Pinel: sama faza rozwoju wyjaśnia ok. 62% zmienności potencjału wodnego (nasze przeliczenie tab. 7),
     a model satelitarny 40%.
   - Choi i Unnisa liczyli korelacje na surowych seriach, w których jest fenologia.
   - Nasza anomalia (ta sama pora roku) usuwa średni cykl sezonowy. Naszych wyników z tymi liczbami nie porównujemy.
4. **U nas NDMI i CRSWIR niosły prawie tę samą informację.** Anomalie obu korelowały na poziomie 0,97 (F4,
   z zastrzeżeniami z pkt 6). U Carletti (rys. 4a, odczyt z wykresu) oba mają zbliżoną skuteczność dla świerka, ale
   autorzy opisują swoje wskaźniki jako słabo skorelowane (tab. A.1 poza PDF). Złożenie daje odporność, a nie nową
   informację.
5. **Okno 30 dni w teście T3 to ustalona z góry konwencja, a nie optimum.**
   - W F4 przewaga średniej z 30 dni nad tym samym dniem była nieistotna: +0,055 [−0,045; 0,177].
   - Choi 2017 pokazuje ten sam kierunek, także dla naszej stacji Condom (lata 2007–2009, MODIS 1 km, surowe wartości):
     r 0,64–0,79 przy wszystkich przesunięciach 0–30 dni, maksimum przy 20 dniach, przedziały ufności się nakładają.
6. **Nasze liczby z F4 są obciążone. Przeliczamy je w kroku K3.** F4 liczyło:
   - normę z „pozostałych lat”, czyli także z przyszłych;
   - na scenach SR 2,5 m, których pasma 20 m nie przeszły kontroli H-SR1;
   - z referencją ISMN sprzed kontroli A4.

   Plan v7 (ustalenie 1) pokazał, że przy normie tylko z lat wcześniejszych R spada z 0,50 do 0,29. Liczby z F4
   (0,97; 0,41; 0,47) mogą więc być zawyżone. W K3 liczymy je od nowa i dopiero to są wartości „przed”.
7. **Ostrzeżenia, które przenosimy:**
   - zmiany gospodarowania (nasadzenia, zadarnienie, zabiegi) dają anomalie niezwiązane z wodą (Unnisa, Carletti);
   - nie piszemy o „wczesnym ostrzeganiu”, bo Unnisa nie pokazała wyprzedzenia;
   - SWIR widzi utratę wody w liściach, czyli raczej silniejszy niedobór (Ceccato).

## 1. Fizyka: Ceccato i in. 2001 [P]

*Remote Sensing of Environment* 77(1): 22–33, doi:10.1016/S0034-4257(01)00191-2. Dane LOPEX93 (37 gatunków) i model
PROSPECT, **poziom liścia**.

- Analiza wrażliwości EFAST (tab. 6): przy 1600 nm woda (EWT) wyjaśnia 36% zmienności odbicia, budowa liścia 41%,
  sucha masa 23%. Przy 820 nm wody nie widać wcale. Iloraz 1600/820 nm podnosi udział wody do 87%, a r² z EWT
  rośnie z 0,77 do 0,92.
- Związek jest logarytmiczny: gdy liść traci wodę, czułość SWIR rośnie.
- Autorzy cytują pracę na słoneczniku: przy umiarkowanym stresie woda na jednostkę powierzchni liścia zmienia się
  mało (Beaumont 1995). Przy umiarkowanym stresie sygnał SWIR może więc być niewidoczny.
- Łanu, gleby i geometrii oświetlenia autorzy nie badali.

**Dla nas:** oba składniki wskaźnika (NDMI, CRSWIR) łączą SWIR z NIR, zgodnie z tym wynikiem. Granicę „widzimy raczej
silniejszy niedobór” piszemy na karcie.

## 2. Laroche-Pinel i in. 2021, *Remote Sensing* 13(9): 1837 [P]

„Towards Vine Water Status Monitoring on a Large Scale Using Sentinel-2 Images”, doi:10.3390/rs13091837.

**Projekt badania:**
- 36 winnic (ok. 1 ha, 67% bez trawy w międzyrzędziu), 103 poletka, Langwedocja i Prowansja, lata 2018–2020.
- Większość pomiarów na Syrah, plus 6 innych odmian.
- Referencja: potencjał wodny łodygi w południe, ponad 3200 pomiarów uśrednionych do 349 obserwacji „poletko × data”.
- 38 scen S-2 bez chmur, nie dalej niż 5 dni od pomiaru (80% w ciągu 2 dni).
- Pięć algorytmów regresji, walidacja przez 10 losowych podziałów 75/25 bez wydzielania lat i działek.

**Wyniki:**

| Dane wejściowe (tab. 8, cały zbiór, najlepszy algorytm) | R² | RMSE [MPa] |
|---|---|---|
| wszystkie pasma S-2 (regresja liniowa, Bayesian Ridge) | 0,40 | 0,26 |
| REP (pozycja red-edge) | 0,19 | 0,30 |
| MSI = B11/B8 | 0,10 | 0,31 |
| **NDII = (B8 − B11)/(B8 + B11)**, prawie nasze NDMI (my B8A) | **0,09** | 0,32 |
| NDRE1 / NDRE2 / IRECI | 0,07 / 0,14 / 0,11 | 0,34 / 0,35 / 0,31 |
| NDVI | 0,04 | 0,33 |

- **Pasma:** wszystkie pasma były istotne (p < 0,05). Eliminacja wsteczna pokazała, że wystarczą 4: **B4, B6, B8A,
  B12** (s. 13), które dają tyle co wszystkie (R² ≈ 0,40).
  B8 i B11 odpadły, B12 dodaje ok. 0,07 R² (odczyt z rys. 10). Przy silnie skorelowanych B11 i B12 wybór B12 może
  być przypadkowy, dlatego mówimy „SWIR”, a nie „B12”.
- **Rola sezonu:**
  - Potencjał wodny spada od −0,47…−0,63 MPa w fazie grochu do −1,14…−1,34 MPa w dojrzewaniu.
  - Odchylenie standardowe wewnątrz fazy i roku wynosi 0,09–0,28 MPa (tab. 7).
  - Nasze przeliczenie: sama faza wyjaśnia ok. 62% zmienności, faza × rok ok. 66%.
  - Bez danych z dojrzewania najlepsze R² to 0,30 (s. 18).
- **Trawa w międzyrzędziu:** bez trawy R² 0,48, wszystkie działki 0,40 (tab. 9). To nie kontrolowany test, bo rok
  2019 to tylko działki bez trawy. Autorzy proponują sprawdzić to w Bordelais i Burgundii, gdzie trawy jest więcej.
- **Zalecenia autorów, nietestowane:** pas wewnętrzny co najmniej 5 m, wystarczająca liczba pikseli w całości wewnątrz
  działki, uwzględnienie międzyrzędzia i gleby (s. 18).
- **Ograniczenia:**
  - losowe podziały zawyżają wynik;
  - do −1,4 MPa model lekko zawyża potencjał, poniżej −1,4 MPa przewidywania się spłaszczają (efekt progowy, s. 14);
  - stanu nawadniania działek nie podano.

**Dla nas:**
- Praca **nie wspiera** NDMI jako miary stanu wody winorośli w porównaniu między działkami. Daje pośrednie wsparcie
  dla SWIR i red-edge w modelu wielopasmowym.
- Kierunek „kilka pasm naraz” zgadza się z planowanym rozplątaniem kanałów (Plan v8).
- Modelu nie odtwarzamy: nie ma opublikowanych współczynników, model skalibrowano w Langwedocji, a my nie mamy pomiarów.
- Przejmujemy regułę pasa wewnętrznego w metrach i minimalnej liczby pikseli.

## 3. Unnisa, Ogutu, Dash 2025, *RSASE* 39: 101690 [P]

„Potential of sentinel 2-derived canopy water content as an indicator of flash drought: Case studies from European
cereal crop areas”, doi:10.1016/j.rsase.2025.101690.

**Projekt badania:**
- 3 regiony: Andaluzja (pszenica), dolina Padu (kukurydza), wschodnie Węgry (kukurydza bez nawadniania); wg autorów
  ok. 10 000 km² każdy (liczba niespójna z podaną liczbą pikseli).
- Odniesienie: wskaźnik stresu parowania ESI (ALEXI, 4 km, tygodniowy).
- Porównanie jednego roku suszy z jednym rokiem normalnym.

**Wyniki:**
- **CWC to produkt sieci neuronowej SL2P** (LEAF Toolbox w GEE, kolekcja S2_SR_HARMONIZED — ta sama co u nas),
  uczonej na symulacjach modelu PROSAIL. Żadnego wskaźnika SWIR nie liczono; jedynym wskaźnikiem był NDVI.
- **Korelacje z ESI w roku suszy** (tab. 3, s. 11):

  | Zmienna | Andaluzja, pszenica | Dolina Padu, kukurydza | Węgry, kukurydza bez nawadniania |
  |---|---|---|---|
  | CWC | 0,59 | 0,66 | 0,40 |
  | NDVI | 0,75 | 0,72 | 0,05 |

  W regionach nawadnianych NDVI korelował z ESI silniej niż CWC, co przeczy wnioskowi autorów z s. 13. Korelacje
  liczono na surowych seriach z cyklem sezonowym; p i n nie podano. W roku normalnym na Węgrzech r = 0,75–0,91, po
  części z samej zbieżności z fenologią.
- **„CWC reaguje najwcześniej”** opiera się na jednym przypadku pszenicy: spadek zaczął się razem z początkiem suszy
  wg ESI, a w następnym akapicie autorzy piszą o opóźnieniu o tydzień (s. 11). CWC nie wyprzedziło ESI.
- **Uwagi samych autorów:**
  - zaufanie do CWC z SL2P jest niskie (Djamai i in. 2019);
  - progi −1σ i −2σ są umowne;
  - zabiegi uprawowe zmieniają zmienne niezależnie od suszy;
  - wskaźniki działały przy w pełni rozwiniętym łanie.

**Dla nas:** praca nie uzasadnia SWIR. Bierzemy z niej:
- zakaz pisania o „wczesnym ostrzeganiu”;
- kontrolę zmian gospodarowania w latach odniesienia;
- wiersz kontrolny w raporcie: korelacja na wartościach surowych obok korelacji na anomaliach. Pokazuje on, ile daje
  sam sezon.

CWC z SL2P nie dodajemy, bo bierze te same pasma SWIR, ma niską wiarygodność, a łan rzędowy łamie założenia modelu
(F3 §7.2).

## 4. Carletti i in. 2025, *European Journal of Remote Sensing* 58(1): 2547386 [P]

„Sentinel-2 time series reveal species-specific responses in temperate conifer dieback”, doi:10.1080/22797254.2025.2547386
(wersja po korekcie; załączniki A.x nie są w PDF). Wśród autorów zespół FORDEAD (Dutrieux, Féret).

**Projekt badania:**
- 742 czyste i 949 mieszanych drzewostanów (inwentaryzacja leśna NFI plus 191 powierzchni dobranych celowo w rejonach
  zamierania), lata 2018–2023, 1186 scen S-2 (MAJA).
- Prawda terenowa: stopień zamierania drzew (posusz i defoliacja), nie woda w liściach.
- Do oceny wybrano tylko powierzchnie bez zabiegów przez ostatnie 5 lat (s. 3).

**Metoda normy (FORDEAD, s. 6):**
- dla każdego piksela model harmoniczny dopasowany do lat 2016–2017;
- anomalia = wartość minus przewidywanie modelu, w jednostkach wskaźnika, a nie z;
- anomalię uśredniano najpierw w pikselu, potem po powierzchni i po „okresie integracji” 1–40 miesięcy.

**Wyniki dla drzewostanów czystych** (s. 7):

| Gatunek | Najlepszy wskaźnik i okres | R² | OA / BA |
|---|---|---|---|
| świerk | CRSWIR, 1 miesiąc | 0,54 | 77% / 74% |
| jodła | IRECI, 15 miesięcy | 0,34 | 61% / 63% |
| sosna | CRRE, 4 miesiące | 0,16 | 64% / 62% |

- R² policzono w próbie, po wyborze najlepszej kombinacji wskaźnika i okresu z wielu wariantów, więc wynik jest
  optymistyczny. OA/BA pochodzą z walidacji krzyżowej.
- Najlepszy wskaźnik zależy od gatunku. Narzucenie CRSWIR obniża R² jodły z 0,34 do 0,19.
- CRSWIR powstał w tym samym zespole do zamierania świerka, więc jego wygrana dla świerka nie jest niezależnym testem.
- **NDMI ma w pracy dokładnie nasz wzór** (tab. 1). Dla świerka NDMI i CRSWIR mają prawie identyczne R² (rys. 4a).
- U świerka poniżej 50% zamierania nie ma wyraźnej różnicy od drzewostanów zdrowych (s. 8). W mieszanych
  drzewostanach wykrywanie jest słabe. Rozrzut anomalii zdrowych powierzchni jest duży (rys. 5).
- Autorzy ostrzegają, że z czasem rośnie ryzyko pomylenia sygnału ze zmianą gospodarowania (s. 11).

**Dla nas:**
- potwierdza ideę „anomalia wobec własnej historii” (D-081) i wzór CRSWIR;
- nie daje dowodu dla wody winorośli;
- przejmujemy kontrolę zmian gospodarowania w latach odniesienia;
- normę harmoniczną traktujemy tylko jako możliwą później eksplorację. Dopasowano ją dla drzew zimozielonych przez
  cały rok; w winnicy w oknie IV–X jest słabo wyznaczona.

## 5. Choi i in. 2017, *TAO* 28(3): 437–462 [P]

„Ecosystem-dynamics link to hydrologic variations for different land-cover types”, Choi M., Mu Q., Kim H., Hwang K.,
Hur J., doi:10.3319/TAO.2016.09.13.01.

**Projekt badania:**
- 132 stacje, w tym 64 w uprawach (36 w australijskiej sieci OzNet, w tym 30 w uprawach).
- Czujniki na 5–10 cm; NDVI z MODIS MOD13A2 (16-dniowe kompozyty, 1 km).
- r Pearsona na wartościach surowych, w sezonie wegetacji: V–IX, a dla OzNet (Australia) XI–III.
- 16-dniowe okna gleby przesuwane o 0–30 dni co 5 dni, więc sąsiednie okna mają wspólne 11 z 16 dni.

**Wyniki:**
- „25 dni dla upraw, 10 dla lasów i łąk” to jakościowe podsumowanie autorów („Generally”, s. 450). Nasze przeliczenie
  tab. S2: w uprawach mediana optimum to 20 dni; średnie r jest prawie płaskie między 10 a 30 dniami, a zysk wobec
  0 dni to ok. +0,08.
- **Nasza stacja Condom jest w próbie** (COND, tab. S1: uprawy; tab. 1: SMOSMANIA, czujnik 10 cm, lata 2007–2009;
  ok. 27–28 kompozytów 16-dniowych — nasze oszacowanie).
  - r przy przesunięciach 0/5/10/15/20/25/30 dni: 0,64/0,70/0,75/0,76/0,79/0,76/0,78 (tab. S2).
  - Przedziały ufności się nakładają ([0,34; 0,82] dla 0,64 i [0,59; 0,90] dla 0,79; nasze przeliczenie, Fisher z,
    n ≈ 27). Testu różnic w pracy nie ma.
- Stacje SMOSMANIA w Gers i okolicach Tuluzy (PEY, SAV, MON, SFL): optimum przy 20–30 dniach; LAH ma słaby związek.
  Stacje z płd.-wsch. Francji (BER, CAB) mają optimum przy 10 dniach.
- W części wilgotnych upraw płd.-wsch. USA (AAM, EAF, PER, SAR, NOI) r ≈ 0 lub ujemne, ale inne stacje z tego regionu
  mają r 0,5–0,65 (HAR, SCO). Wzorzec nie jest jednolity (nasza interpretacja).
- Autorzy tłumaczą opóźnienie cyklem sezonowym: wiosenny wzrost, jesienne zasychanie (s. 450). Wniosek, że nie jest
  to reakcja anomalii, jest nasz, bo korelacje liczono na surowych seriach.

**Dla nas:**
- Choi pokazuje ten sam kierunek co nasz T3: gleba z poprzednich 2–4 tygodni wiąże się z roślinnością co najmniej tak
  dobrze jak bieżąca. Liczb dla anomalii winnic stąd nie bierzemy.
- Środek naszego okna [t − 30, t] odpowiada przesunięciu ok. 15 dni u Choi.

## 6. Nasze dane z F4 — co z nich zostaje

| Liczba z F4 (VINEYARD_06) | Wartość | Obciążenie | Co robimy |
|---|---|---|---|
| korelacja anomalii NDMI i −CRSWIR | 0,97 (VI–IX 0,968) | SR 2,5 m; norma z pozostałych lat; bez rozdziału torów orbity (wspólne przesunięcie torów, ok. 0,4 z, może zawyżać korelację) | przeliczyć w K3 na natywnych 20 m, z normą z lat wcześniejszych i z rozdziałem torów |
| korelacja anomalii NDMI i NDVI | 0,94 | jw. | jw. |
| NDMI wobec ISMN w tym samym dniu | R 0,41 | jw. + ISMN sprzed A4 | przeliczyć w K3 po A4 |
| NDMI wobec średniej gleby z 30 dni | R 0,47; zysk wobec tego samego dnia +0,055 [−0,045; 0,177] | jw.; walidacja z pominięciem roku wybrała okno 30 dni w 9/9 lat dla NDMI i złożenia, w 8/9 dla NDVI | okno 30 dni jako konwencja ustalona z góry |
| związek wewnątrz roku i między latami | NDMI: wewnątrz roku 0,30 [0,02; 0,52], średnie roczne 0,55 (n = 9) | jw. | w T3 raportować ρ łączne i wewnątrz roku |

## 7. Składniki wskaźnika

| Wskaźnik | Wzór w potoku (`step_04.compute_indices`) | Źródło wzoru i dowody | Rola |
|---|---|---|---|
| **NDMI** (NDII z B8A) | (B8A − B11)/(B8A + B11) | ten sam wzór w Carletti 2025 (tab. 1) i jako „NDWI” w kodzie FORDEAD (nie mylić z NDWI Gao ani NDWI McFeeters z pasmem zielonym, którego używa Carletti); w winnicach NDII (z B8) R² 0,09 wobec potencjału wodnego (Laroche-Pinel 2021, porównanie między działkami) | składnik 1 |
| **CRSWIR** | B11 / [B8A + (B12 − B8A)·w], w = (1610 − 865)/(2190 − 865) = 0,5623; wyższy = mniej wody (w złożeniu ze znakiem −) | kod FORDEAD (`fordead/preprocess.py`): `B11/(B8A+((B12-B8A)/(2185.7-864))*(1610.4-864))`, w = 0,5647 (różnica pomijalna, ujednolicić w K2); budowa wzoru jak w Carletti (tab. 1). Teza „CRSWIR mniej zależny od jasności tła” to nasza hipoteza, bez źródła | składnik 2 |
| NDVI | (B08 − B04)/(B08 + B04) | ilość zieleni; Laroche-Pinel: R² 0,04 wobec potencjału wodnego | szczegół |
| NDRE | (B8A − B05)/(B8A + B05) | chlorofil; najbliższy wskaźnikom red-edge, które u Laroche-Pinel wypadły najlepiej z pojedynczych (REP 0,19) | szczegół |

**Nazewnictwo:** NDWI Gao (1996) używa pasma 1,24 µm, którego Sentinel-2 nie ma, więc nasze NDMI to nie NDWI Gao.
Pracy Gao nie czytaliśmy w całości [—]; opis pasma pochodzi z bazy indeksów i streszczeń.

## 8. Czego nie bierzemy i dlaczego

| Kandydat | Powód |
|---|---|
| model potencjału wodnego Laroche-Pinel | brak współczynników, kalibracja w Langwedocji, brak naszych pomiarów polowych |
| CWC z SL2P (Unnisa) | te same pasma SWIR, niska wiarygodność (autorzy), łan rzędowy łamie założenia modelu |
| test „woda w liściach reaguje przed zielenią” | Unnisa nie pokazała wyprzedzenia; u nas anomalie NDMI i NDVI są silnie skorelowane, a sezonów jest mało |
| kompozyty 8- i 16-dniowe | mieszają tory orbity, opóźniają kartę; w F4 średnia 30-dniowa z nie dała zysku (0,390 wobec 0,433) |
| podział winnic wg typu międzyrzędzia | przewaga działek bez trawy u Laroche-Pinel jest zakłócona składem lat; stan międzyrzędzia zmienia się co roku |
| temperatura liści | w Copernicusie tylko Sentinel-3, 1 km (D-048) |
| GVMI, NMDI, MSI | kolejne warianty NIR–SWIR; ewentualnie jako wejście do rozplątania kanałów (Plan v8) |
| ESI/ALEXI, MOD16, GPCP | spoza Copernicusa (D-048) |

## 9. Stan czytania

| Źródło | Stan |
|---|---|
| Ceccato i in. 2001 | przeczytany w całości (PDF ze strony IPGP) |
| Laroche-Pinel i in. 2021, *Remote Sensing*; Unnisa i in. 2025; Carletti i in. 2025; Choi i in. 2017 | przeczytane w całości (PDF od użytkownika, 2026-10-19), cytaty i liczby sprawdzone przez drugiego agenta |
| kod FORDEAD | sprawdzony w źródłach (GitLab INRAE) |
| Laroche-Pinel i in. 2021, *OENO One*; Pantaleoni Reluy i in. 2022 | przeczytane wcześniej (F3) |
| Gao 1996; Ceccato i in. 2002; Hunt i Rock 1989; Ardö i in. 2017; Hardisky i in. 1983 | nieprzeczytane (płatne) — nie służą jako uzasadnienie [—] |
| Delval i in., EGU22-3908 | tylko streszczenie konferencyjne [F3] |

**Do przeczytania później (z bibliografii Laroche-Pinel):** Laroche-Pinel i in. 2021, *Remote Sensing* 13: 536
(otwarty dostęp) oraz Cohen i in. 2019.

## Źródła

- Ceccato P., Flasse S., Tarantola S., Jacquemoud S., Grégoire J.-M. 2001. Detecting vegetation leaf water content using
  reflectance in the optical domain. *Remote Sensing of Environment* 77(1): 22–33. doi:10.1016/S0034-4257(01)00191-2 [P]
- Laroche-Pinel E., Duthoit S., Albughdadi M., Costard A. D., Rousseau J., Chéret V., Clenet H. 2021. Towards Vine Water
  Status Monitoring on a Large Scale Using Sentinel-2 Images. *Remote Sensing* 13(9): 1837. doi:10.3390/rs13091837 [P]
- Unnisa Z., Ogutu B., Dash J. 2025. Potential of sentinel 2-derived canopy water content as an indicator of flash
  drought: Case studies from European cereal crop areas. *Remote Sensing Applications: Society and Environment* 39:
  101690. doi:10.1016/j.rsase.2025.101690 [P]
- Carletti H., Gégout J.-C., Dutrieux R., Féret J.-B., Vega C., Belouard T., Jolly A., Cansell J., Piedallu C. 2025.
  Sentinel-2 time series reveal species-specific responses in temperate conifer dieback. *European Journal of Remote
  Sensing* 58(1): 2547386. doi:10.1080/22797254.2025.2547386 [P]
- Choi M., Mu Q., Kim H., Hwang K., Hur J. 2017. Ecosystem-dynamics link to hydrologic variations for different
  land-cover types. *Terrestrial, Atmospheric and Oceanic Sciences* 28(3): 437–462. doi:10.3319/TAO.2016.09.13.01 [P]
- Dutrieux R., Ose K., de Boissieu F., Féret J.-B. fordead: a python package for vegetation anomalies detection from
  SENTINEL-2 images. https://zenodo.org/records/12802457 ; kod: https://gitlab.com/fordead/fordead_package [P, kod]
- Laroche-Pinel E. i in. 2021. *OENO One* 55(4): 115–127. doi:10.20870/oeno-one.2021.55.4.4752 [F3]
- Pantaleoni Reluy N. i in. 2022. *OENO One* 56(1): 145–159. doi:10.20870/oeno-one.2022.56.1.4632 [F3]
- Gao B.-C. 1996. *Remote Sensing of Environment* 58(3): 257–266. doi:10.1016/S0034-4257(96)00067-3 [—]
- Dane własne: `docs/evidence/F4_eksperymenty/A_roslinnosc/` (`a2_variant_series.csv`, `a2_variants_eval.csv`,
  `a3_lag.csv`, `a5_decomposition.csv`), `docs/plans/Plan_v7_precyzja.md` (ustalenia 1 i 8),
  `docs/evidence/A4_QC_czujnikow_ISMN.md`.
