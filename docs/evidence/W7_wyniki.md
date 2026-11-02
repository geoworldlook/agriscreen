# W7 „Wskazówki AgriScreen potwierdzone pomiarami” — wyniki (zamrożenie 2026-09-30)

> **Status:** wynik protokołu `docs/evidence/W7_protokol_wskazowki.md` (D-093, SHA-256 `a6689c13…`, status
> `REGISTERED`, zarejestrowany w commicie `cf2dfcf` przed liczeniem), bez zmian protokołu po rejestracji.
> - Przebieg 2026-11-02 na komputerze lokalnym; notatnik z wynikami: `notebooks/experiments/W7_wskazowki.ipynb`
>   (generator `build_w7.py`, kod `agriscreen/experiments/w7.py` i `w7_data.py`).
> - Dane: archiwa ICOS L2 10 stacji, czujnik ISMN Condom (A4 W1), Météo-France, deklaracje celne Gers 2016–2025;
>   pochodzenie każdego pliku (adres, data, SHA-256, licencja) w `data/09_Reference_Stations/MANIFEST_W7.csv` na Dysku.
> - Tylko wartości zmierzone (znacznik jakości 0); wartości uzupełnione modelem odrzucone. Bez danych syntetycznych.

## Wynik w skrócie

| Test | Trafność wskazówki | Przypadek | Przewaga [95%] | Liczba | Werdykt |
|---|---|---|---|---|---|
| **K1** „gleba sucha” → czujnik w gruncie poniżej swojej normy | **81,2%** [74,6; 87,8] | 49,3% | +31,8 pp [+11,9; +51,8] | 4783 dni, 11 stanowisk, 11 lat | **potwierdzone** |
| **K2** „roślinność poniżej normy” → zmierzone parowanie poniżej normy | 67,1% [33,0; 100] | 51,7% | +15,3 pp [−4,4; +35,1] | 82 sceny, 7 stacji, 8 lat | **niepotwierdzone** |

**Co to znaczy dla klienta:** gdy AgriScreen mówi „gleba w okolicy jest sucha”, czujniki w gruncie potwierdziły, że
gleba była suchsza niż zwykle w **8 na 10** takich dni (przypadkiem byłoby 5 na 10). Wskazówka o roślinności nie ma
jeszcze takiego potwierdzenia.

## 1. K1 — gleba (rozstrzygające, spełnione)

- Każda stacja osobno daje ten sam kierunek:

  | Stanowisko | Dni | Dni „sucho” | Trafność | Przypadek |
  |---|---|---|---|---|
  | FR-Aur Auradé (uprawy, 74 km) | 1079 | 365 | 80,0% | 50,8% |
  | FR-Bil Bilos (las, 121 km) | 1300 | 464 | 87,1% | 52,0% |
  | FR-Fon Fontainebleau (las) | 1345 | 581 | 84,9% | 50,6% |
  | FR-Gri Grignon (uprawy) | 804 | 211 | 75,8% | 52,5% |
  | FR-Hes Hesse (las) | 949 | 461 | 83,7% | 50,6% |
  | FR-Lam Lamasquère (uprawy, 86 km) | 713 | 342 | 90,4% | 52,7% |
  | FR-Lus Lusignan (łąka) | 759 | 323 | 85,8% | 50,7% |
  | FR-Mej Méjusseaume (łąka) | 1067 | 409 | 93,9% | 53,2% |
  | FR-Pue Puéchabon (las zimozielony) | 950 | 320 | 81,6% | 48,3% |
  | FR-Tou Toulouse (łąka, 91 km) | 1699 | 624 | 86,5% | 50,8% |
  | ISMN Condom (przy winnicach) | 1720 | 683 | 55,2% | 38,0% |

- Najsłabiej w Condom (+17 pp zamiast +25–40 pp). Czujnik punktowy na 20–30 cm pod trawą, wartości niskie
  cenzurowane regułą A4 W1, a produkt opisuje warstwę 0–100 cm; przyczyn nie rozstrzygamy (wiersz opisowy).
- Opisowo: „gleba wilgotna” → czujnik powyżej normy w 89,8% dni [76,5; 100] wobec 48,4% przypadkiem.

## 2. K2 — roślinność (rozstrzygające, niespełnione)

- Trafność 67% wobec 52% przypadkiem, ale dolna granica przewagi −4,4 pp: kryterium niespełnione.
- Stacje różnią się bardzo (wiersze opisowe, bez wpływu na werdykt):

  | Stacja | Typ | Sceny | „Poniżej” | Trafność | Przypadek | ρ z_woda–anomalia parowania |
  |---|---|---|---|---|---|---|
  | FR-Lus | łąka | 58 | 16 | 93,8% | 56,9% | 0,75 |
  | FR-Tou | łąka | 64 | 22 | 81,8% | 62,5% | 0,56 |
  | FR-Mej | łąka | 98 | 19 | 78,9% | 43,9% | 0,55 |
  | FR-Bil | las iglasty | 23 | 2 | 50,0% | 52,2% | 0,51 |
  | FR-Fon | las liściasty | 31 | 6 | 50,0% | 45,2% | −0,06 |
  | FR-Pue | las zimozielony | 18 | 3 | 33,3% | 55,6% | 0,01 |
  | FR-Hes | las liściasty | 85 | 14 | 14,3% | 50,6% | −0,44 |

- **Obserwacja po teście (nie wniosek):** na łąkach wskazówka zgadza się z pomiarem, w lasach nie. Możliwe
  przyczyny: w zwartym lesie wskaźnik SWIR reaguje na strukturę i fenologię korony, a głębokie korzenie buforują
  suszę. Winnica (krzewy w rzędach z trawą w międzyrzędziach) leży pomiędzy; tego test nie rozstrzyga.
- Opisowo: kwadrat 200 m 65,9% i 500 m 67,8% (wynik nie zależy od wielkości kwadratu); udział parowania w energii
  (EF) 76,0% przy n = 50 i szerokim przedziale; fotosynteza (GPP) tylko 6 scen ze wskazówką — za mało.
  ρ wewnątrz sezonu 0,12, średnich sezonów 0,33 (40 sezonów): jak w W3b, związek głównie między latami.

## 3. Pogoda i plon (opisowo)

- **Upał** (ERA5-Land, próg z panelu) wobec stacji Météo-France CONDOM: wykryte 70% dni upału, 15% fałszywych
  alarmów (70 trafień, 12 fałszywych, 30 pominiętych). BEAUCAIRE i REAUP: wykrycie 50–58%, fałszywe 5–7%.
  Na stacjach ICOS wynik zależy od stacji (np. Lamasquère: 33 fałszywe alarmy, brak zmierzonego upału).
- **Przymrozek:** mało zdarzeń (0–33 na stację); wyniki niejednoznaczne, bez wniosku.
- **Plon wina w Gers** (deklaracje celne): ρ z medianą z_woda 13 winnic 0,29 (8 lat). Rok 2022: najniższy indeks
  (−1,81) i jeden z najniższych plonów (60 hl/ha); rok 2021: indeks wysoki, plon niski po kwietniowym przymrozku.
  Wskaźnik roślinności nie przewiduje plonu i nie twierdzimy, że przewiduje.

## 4. Co zmienia się w produkcie (§7)

- Panel „How far to trust it”: wiersz K1 `confirmed (W7)` i wiersz K2 `not confirmed`, z liczbami
  (`w7.trust_rows`, plik `w7_tests.csv` publikowany co tydzień do `docs/showcase/`).
- README i strona: zdanie o wskazówce „gleba sucha” (8 na 10) i uczciwy opis wskazówki roślinności.
- Karta winnicy bez zmian: zdanie o roślinności zostaje opisem obserwacji satelitarnej, bez obietnicy co do
  stanu roślin.

## 5. Uwagi wykonawcze (nie zmieniają protokołu)

- Dane ICOS pobrane jako pełne archiwum stacji („ETC L2 ARCHIVE”): zawiera te same produkty L2 (FLUXNET
  półgodzinny, Meteo) oraz głębokości czujników (VARINFO_METEO), których nie ma w osobnych plikach.
- Sentinel-2 dla kwadratów: te same zadania co winnice (`task_ingest_s2`, `task_parcel_stats`); strefa UTM wieży;
  zasięg pobierania 100 m wokół kwadratu 500 m (nie zmienia pikseli w kwadratach). Hesse leży na styku kafli,
  stąd 1486 plików.
- W trakcie pobierania omyłkowo usunięto i pobrano ponownie sceny Puéchabon (bez wpływu na dane). Pusty wiersz
  opisowy Météo-France (niezgodny typ numeru stacji) poprawiono przed ostatnim przebiegiem; werdykty bez zmian.

## 6. Ograniczenia

- Żadna wieża ICOS nie stoi w winnicy; K1 potwierdza wskazówkę o glebie w regionie i we Francji, nie stan winorośli.
- K2 łączy różne typy roślinności; po teście widać różnicę łąka / las, ale to obserwacja, nie wynik.
- Lata po zamrożeniu i sezon 2027: te same reguły jako potwierdzenie (§8); dla roślinności — nowy protokół
  z podziałem na typ roślinności, zapisany przed sezonem 2027.
