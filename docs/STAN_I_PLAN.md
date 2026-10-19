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

## 2. Wprowadzamy teraz — „Moja winnica” (W3b, zima 2026/27, 5–6 sesji)

Na karcie pojawią się 3 zdania:
1. **Gleba w okolicy:** sucho / w normie / wilgotno. To już mamy; nagłówek przechodzi na 3 klasy.
2. **Twoja działka:** wskaźnik wody w roślinności (pasma SWIR) poniżej / w normie / powyżej jej własnej historii,
   ile winnic w okolicy jest w tym samym stanie oraz przebieg sezonu.
3. **Okolica:** czy roślinność winnic idzie w parze z wodą w glebie. To zdanie pokazujemy tylko, jeśli test to
   potwierdzi.

| Krok | Co | Wynik |
|---|---|---|
| K1 | zapisanie testów i reguł przed liczeniem (skrót SHA-256); szkic gotowy, czeka na wybory U1–U8 | protokół |
| K2 | statystyki 15 winnic z archiwum (pas 20 m od brzegu, min. 40 pikseli — spełnia 13 z 15) | dane działek |
| K3 | anomalie i testy: T1 kalibracja, T2 szum, T3 zgodność z czujnikiem w gruncie; poprawione liczby „przed”; **wariant wielopasmowy** (4 pasma z pracy Laroche-Pinel, wagi uczone na czujniku, ocena na latach niewidzianych przez model) | notatka wyników |
| K4 | karta w dashboardzie, biuletynie i notatniku | karta „Moja winnica” |

**Reguła dla wariantu wielopasmowego:** zastępuje prosty wskaźnik tylko wtedy, gdy jest pewnie lepszy na latach
testowych. Jeśli nie, zostaje prosty wskaźnik, a wynik i tak służy jako punkt odniesienia dla sieci neuronowej.

**Spodziewany wynik:** test T3 (zdanie 3) najpewniej wyjdzie nierozstrzygnięty, bo mamy ok. 7 sezonów; symulacja daje
ok. 1 szansę na 4 przy umiarkowanym związku. Zdania 1 i 2 działają niezależnie od tego.

**Do zatwierdzenia:** decyzje D-084–D-089 (Plan W3b §6) i wybory U1–U8 (protokół §13).

**Drobne dokończenia warstwy gleby** (Plan v9, robione przy okazji):
- test „ERA5 i SWI zgodnie suche”;
- ponowne oszacowanie prawdopodobieństwa na karcie (A5);
- sekcja „Jak to liczymy”.

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
