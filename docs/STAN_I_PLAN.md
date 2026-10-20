# AgriScreen — co mamy, co wprowadzamy, co później

Stan na 2026-10-19. Jedna strona do orientacji. Szczegóły są w dokumentach z §5.

**Cel:** rolnik widzi, czy jego pole jest teraz w anomalii względem własnej historii. Nie dajemy zaleceń podlewania
ani zabiegów. Każda liczba na karcie ma wynik sprawdzenia albo napis „niezwalidowane”.

## 1. Mamy (działa)

### Sprawdzone wobec pomiarów naziemnych

| Co | Źródło | Wynik sprawdzenia |
|---|---|---|
| Woda w glebie okolicy (~10 km) | model ERA5-Land, 0–100 cm | wobec czujników na 3 stacjach: R 0,57 (Condom), 0,57 (Auradé), 0,68 (Lusignan); ta sama klasa sucho / norma / wilgotno w ok. 55% dni; suchą dekadę czujnik potwierdza w ok. połowie przypadków |
| Satelitarne potwierdzenie gleby | CLMS SWI 0,1° (radar), od 2007 r. | wobec czujników R 0,52–0,57; zgodność klas z ERA5 63% |
| Opad 30 dni, SPI-3 | ERA5-Land | wobec deszczomierza Météo-France w Condom: R 0,90 / 0,87 |
| Temperatura, upały | ERA5-Land | błąd Tmin / Tmax ok. 1 °C; upały wykryte w 68%, fałszywe 9% |
| Kontrola czujników | reguły A4, stacje ICOS | wadliwe odczyty czujnika w Condom są oznaczone i nie zawyżają ocen |

### Działa, ale bez potwierdzenia albo tylko informacyjnie

- **Przymrozki wiosenne:** za mało zdarzeń, żeby je sprawdzić.
- **Roślinność Twojej winnicy (Sentinel-2):** NDVI, NDMI, NDRE i CRSWIR liczone tylko dla VINEYARD_06. Pokazywane
  informacyjnie. Dotychczasowe liczby zgodności (R ≈ 0,4) są zawyżone, bo norma brała też lata przyszłe — do
  przeliczenia.
- **Alarm z NDVI:** bez trafień, więc tylko w sekcji informacyjnej.

### Produkt i dane

- **Karta „Woda w winnicy”** z sekcją „Na ile ufać”, dashboard, biuletyn i notatnik Colab sterujący całością.
- **Archiwum Sentinel-2 na Dysku:** 414 scen 2016–2026, 15 winnic i 5 sadów w obszarze 4 × 4,4 km.

## 2. „Moja winnica” (W3b): wdrożone, pierwszy przebieg 2026-10-20 (`docs/evidence/W3b_wyniki.md`)

Karta ma 3 zdania:
1. **Gleba w okolicy:** sucho / w normie / wilgotno. Nagłówek gleby w 3 klasach.
2. **Twoja działka:** wskaźnik wody w roślinności (pasma SWIR) poniżej / w normie / powyżej jej własnej historii,
   ile winnic w okolicy jest w tym samym stanie oraz przebieg sezonu.
3. **Okolica:** czy roślinność winnic idzie w parze z wodą w glebie. To zdanie pokazujemy tylko, jeśli test to
   potwierdzi (w pierwszym przebiegu: nie).

| Krok | Co | Wynik |
|---|---|---|
| K1 ✓ | zapisanie testów i reguł przed liczeniem: protokół zarejestrowany 2026-10-19 (SHA-256, D-089) | protokół |
| K2 ✓ | statystyki 15 winnic z archiwum (pas 20 m od brzegu, min. 40 pikseli — spełnia 13 z 15) | dane działek |
| K3 ✓ | anomalie i testy: T1 kalibracja, T2 szum, T3 zgodność z czujnikiem w gruncie; poprawione liczby „przed”; **wariant wielopasmowy** (4 pasma z pracy Laroche-Pinel, wagi uczone na czujniku, ocena na latach niewidzianych przez model) | `W3b_wyniki.md` |
| K4 ✓ | karta w dashboardzie, biuletynie i notatniku | karta „Moja winnica” |

**Wynik pierwszego przebiegu:**
- T3 ρ 0,55 [−0,02; 1,00] — kryterium niespełnione, więc zdanie 3 jest ukryte;
- wariant 4 pasm nieprzyjęty;
- T1 bez grubego rozkalibrowania;
- szum ok. 1 z.

Karta działa ze zdaniami 1–2. Kolejny test na nowych danych: sezon 2027, te same reguły.

**Reguła dla wariantu wielopasmowego:** zastępuje prosty wskaźnik tylko wtedy, gdy jest pewnie lepszy na latach
testowych. Jeśli nie, zostaje prosty wskaźnik, a wynik i tak służy jako punkt odniesienia dla sieci neuronowej.

**Przewidywanie przed liczeniem** (spełnione): T3 najpewniej nierozstrzygnięty przy ok. 7 sezonach.

**Decyzje:** D-084–D-089 przyjęte do wdrożenia 2026-10-19 (Plan W3b §6), wybory U1–U8 według rekomendacji
(protokół §13). Protokół bez zmian po rejestracji.

**Drobne dokończenia warstwy gleby** (Plan v9, robione przy okazji):
- test „ERA5 i SWI zgodnie suche”;
- ponowne oszacowanie prawdopodobieństwa na karcie (A5);
- sekcja „Jak to liczymy”.

## 2b. Pokazanie na blogu (2026-10-20)

- **Panel AgriScreen** (EN, układ jak Wago z projektu ESA WineEO): lista winnic, mapa na zdjęciu satelitarnym Esri
  z półprzezroczystą warstwą — piksele 10 m wewnątrz winnic (NDVI, NDRE, NDMI; 16 ostatnich bezchmurnych scen),
  strefy (piksel minus mediana działki tego samego dnia, bez pierścienia 10 m przy brzegu) albo z całej działki wobec
  własnej historii (anomalia tylko dla całej działki, jak w protokole W3b) — statystyki działki, stan, gleba w okolicy (wskaźnik), pogoda (prognoza
  7 dni, ostatnie 10 dni, opad 30/90 dni, przymrozki i upały), karta, sezon, „How far to trust it” —
  `docs/showcase/agriscreen_panel.html`, w Colab sekcja 6b. Mapy pikseli opisują działkę, nie są porównywane z normą
  ani walidowane.
- **Notatnik-opowieść** (EN) z wynikami i zapisanymi wykresami — `notebooks/AgriScreen_story.ipynb`.
- Instrukcja publikacji: `docs/showcase/README.md`.

## 3. Później (osobne decyzje)

| Co | Po czym | Uwagi |
|---|---|---|
| **Rozplątanie sygnału siecią neuronową** (Plan v8, moduły 2–3): maska rzędów z ortofotomapy, oddzielenie winorośli od międzyrzędzia na wszystkich pasmach, w tym SWIR | po W3b | oceniane tymi samymi testami T1–T3; punkt odniesienia: prosty wskaźnik i wariant wielopasmowy |
| Najbliższe 7 dni (W4), perspektywa 30 dni (W5), faza winorośli (W6) | po W3b | z Planu v9 |
| Dowolna działka (rolnik wgrywa obrys), mapa stref w działce | po W3b | wymagania: ok. 0,4 ha, 5 lat tej samej uprawy |
| Publikacja na GeoWorldLook i automatyczna aktualizacja (W3, W7) | po prototypie | |
| Ryzyko chorób winorośli | po W6 | kandydat |
| Wskaźnik red-edge (REP), norma harmoniczna jak w FORDEAD | po K3 | tylko eksploracyjnie |

## 4. Czego nie robimy

- Nie mówimy „winorośl ma stres wodny” ani „wczesne ostrzeżenie” — tego nie da się obronić bez pomiarów w winnicy.
- Nie przenosimy wprost modelu z artykułu Laroche-Pinel: nie ma współczynników, a uczono go na pomiarach, których nie
  mamy. Bierzemy tylko zestaw pasm.
- Nie używamy danych spoza Copernicusa, wody w łanie z SL2P, temperatury liści 1 km ani absolutnych progów
  „zdrowe / stres”.

## 5. Gdzie co jest

| Temat | Dokument |
|---|---|
| Plan „Moja winnica” | `docs/plans/Plan_W3b_moja_winnica.md` |
| Plan wdrożenia K1–K4 (kod, testy, sesje) | `docs/plans/W3b_plan_wdrozenia.md` |
| Protokół walidacji W3b (szkic do zatwierdzenia) i symulacje | `docs/evidence/W3b_protokol_walidacji.md`, `docs/evidence/W3b_symulacje.py` |
| Literatura do W3b | `docs/evidence/W3b_przeglad_literatury_woda_w_lisciach.md` |
| Wyniki walidacji gleby (3 stacje) | `docs/evidence/W2_REF_wyniki.md`, `docs/evidence/karta_wynikow.md` |
| Plan modułu „Woda w winnicy” (W1–W7) | `docs/plans/Plan_v9_woda_w_winnicy.md` |
| Rozplątanie sygnału (sieć neuronowa) | `docs/plans/Plan_v8_cloud_native_dl.md` |
| Kod i zadania | `docs/ARCHITEKTURA.md` |

## 2c. W3c — strefa gorsza niż zwykle (2026-10-20)

Pytanie: czy to miejsce w winnicy jest dziś słabsze (suchsze) względem reszty działki, niż zwykle o tej porze?
Bez oceny stanu winorośli i bez porad.

| Krok | Co | Wynik |
|---|---|---|
| Z0 ✓ | protokół zarejestrowany przed liczeniem (SHA-256, D-090), wybory U1–U7 przyjęte | `docs/evidence/W3c_protokol_strefy.md` |
| Z1 | kod: strefa dnia (piksel − mediana działki, 30 m), norma miejsca z 5 lat, test szumu (pary scen bez deszczu), strefy ≥ 4 komórki, „nowa / potwierdzona”, kryterium pokazania | `step_13_zones.py`, `task_zones` |
| Z2 | pierwsze liczenie w Colab na archiwum projektu | `w3c_tests.csv`, notatka wyników |
| Z3 | warstwa „Zones vs usual” w panelu — tylko gdy kryterium §6 jest spełnione | panel |

**Decyzja D-090:** warstwa historii stref według protokołu W3c; pokazujemy ją winiarzom tylko po przejściu trzech
warunków (próg z testu szumu, szum < ½ zróżnicowania działki, ≤ 5% komórek w strefach przy glebie w normie).
