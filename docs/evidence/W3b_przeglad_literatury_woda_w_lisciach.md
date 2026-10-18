# W3b — przegląd literatury: wskaźnik „woda w liściach” dla działki (Sentinel-2)

> Status: przegląd do planu `docs/plans/Plan_W3b_moja_winnica.md` (wersja 4), 2026-10-18. Uzupełnia
> `docs/evidence/F3_przeglad_literatury_platforma.md` §6–7, nie powtarza go. Oznaczenia: [P] przeczytany pełny tekst
> lub abstrakt ze strony wydawcy / repozytorium; [F3] pełny tekst opisany w F3; [W] tylko streszczenie z wyszukiwania,
> do potwierdzenia przed cytowaniem w publikacji; [D] nasze dane.

## Wynik w skrócie

1. **Fizyka przemawia za SWIR.** Woda w liściach pochłania promieniowanie w podczerwieni krótkofalowej (SWIR,
   1,6 i 2,2 µm). Sam SWIR zależy jednak też od budowy liścia i suchej masy, dlatego potrzebne jest odniesienie
   do NIR (Ceccato i in. 2001). Oba nasze składniki to robią: NDMI dzieli przez NIR, a CRSWIR odnosi B11 do linii
   między NIR i SWIR-2.
2. **W suszy wskaźniki wody reagują wcześniej niż wskaźniki zieleni.** Woda w łanie z Sentinel-2 zareagowała
   na suszę błyskawiczną wcześniej niż LAI i fAPAR (zboża w Europie, lata 2022–2023). To uzasadnia SWIR jako wskaźnik
   główny, a NDVI tylko jako tło.
3. **W winnicach dowody są umiarkowane.** Pasma S-2 (w tym SWIR) wyjaśniają ok. 40% zmienności potencjału wodnego
   winorośli (Laroche-Pinel 2021), a dwie winnice w Belgii dały R² ok. 0,6–0,7 (praca konferencyjna). Żadna praca
   nie testowała CRSWIR w winnicach — będziemy pierwsi, więc wynik opisujemy jako nasz test, nie jako wiedzę z literatury.
4. **Nasze dane: NDMI i CRSWIR to prawie to samo.** Anomalie obu korelują na VINEYARD_06 na poziomie 0,97 (VI–IX:
   0,968). Średnia z dwóch wskaźników zmniejsza szum tylko nieznacznie (wariancja (1 + r)/2 = 0,985). Złożenie
   uzasadniamy **odpornością** (dwa różne sposoby pomiaru tej samej absorpcji, CRSWIR mniej zależny od jasności tła),
   a nie dodatkową informacją.
5. **Opóźnienie reakcji ok. 1 miesiąca** ma wsparcie w literaturze (uprawy: ok. 25 dni; MODIS, 132 miejsca) i w naszym
   F4: najlepiej i stabilnie, w każdym roku walidacji krzyżowej, działała średnia anomalia gleby z 30 dni przed sceną.
6. **Tło w winnicy:** przy rzadkim łanie SWIR widzi też suchą glebę i trawę międzyrzędzia. Wskaźnik działki mierzy więc
   „suchość działki” (winorośl + międzyrzędzie). Dla pytania „czy działka jest w anomalii” to wystarcza. Dla pytania
   „co dzieje się z samą winoroślą” potrzebne jest rozplątanie kanałów (Plan v8).

## 1. Fizyka: dlaczego SWIR i dlaczego razem z NIR

| Źródło | Co mówi | Wniosek dla nas |
|---|---|---|
| Ceccato P., Flasse S., Tarantola S., Jacquemoud S., Grégoire J.-M. 2001. *Remote Sensing of Environment* 77(1): 22–33, doi:10.1016/S0034-4257(01)00191-2 [W] | SWIR jest czuły na ekwiwalentną grubość wody w liściu (EWT), ale budowa liścia i sucha masa też zmieniają odbicie w SWIR. Sam SWIR nie wystarcza; NIR, mało czuły na wodę, służy jako odniesienie | wskaźnik musi łączyć SWIR z NIR; oba składniki spełniają ten warunek |
| Ceccato i in. 2002. *Remote Sensing of Environment* 82: 188–197 (GVMI, cz. 1) [W] | projekt wskaźnika wody roślinności (GVMI) z korektą atmosfery i tła | GVMI zostaje kandydatem z F3 §7; nie dodajemy go teraz (to też NIR–SWIR-1, czyli trzeci wariant tej samej informacji) |
| Gao B.-C. 1996. *Remote Sensing of Environment* 58(3): 257–266, doi:10.1016/S0034-4257(96)00067-3 [W] | NDWI Gao używa 0,86 i **1,24 µm** | **Korekta nazewnictwa:** Sentinel-2 nie ma pasma 1,24 µm. Nasze NDMI = (B8A − B11)/(B8A + B11) to NDII (Hardisky i in. 1983 [—]), nie NDWI Gao. F3 §6.1 łączy te nazwy — poprawić przy najbliższej zmianie F3 |

## 2. Składniki wskaźnika

| Wskaźnik | Wzór w potoku (`step_04.compute_indices`) | Pochodzenie i dowody | Rola |
|---|---|---|---|
| **NDMI** (NDII) | (B8A − B11)/(B8A + B11) | szeroko stosowany wskaźnik wody w łanie; TerraNIS (model Laroche-Pinel) używa B11 [F3] | składnik 1 |
| **CRSWIR** | B11 / [B8A + (B12 − B8A)·(1610 − 865)/(2190 − 865)]; wyższy = mniej wody (w złożeniu ze znakiem −) | INRAE, pakiet FORDEAD (Dutrieux, Ose, de Boissieu, Féret; wersja 1.3.0 z 2021, doi:10.15454/4TEO6H; Zenodo doi:10.5281/zenodo.12802456) do wykrywania zamierania lasów jako anomalii piksela wobec własnej sezonowości [W]. Najlepszy wskaźnik dla zamierania świerka we Francji: R² 0,54, trafność 77% (European Journal of Remote Sensing 2025) [W]. Brak prac w winnicach | składnik 2; ta sama logika „anomalia piksela wobec własnej historii” co u nas |
| NDVI | (B08 − B04)/(B08 + B04) | ilość zieleni; w winnicy 10 m widać tylko silne uszkodzenia; w normalnym, gorącym roku 28% pikseli fałszywie „uszkodzonych” (Pantaleoni Reluy i in. 2022) [F3] | szczegół (tło: ile zieleni) |
| NDRE | (B8A − B05)/(B8A + B05) | chlorofil i azot, nie woda wprost [F3] | szczegół (żółknięcie liści) |

## 3. Czy wskaźniki wody działają w suszy i w winnicach

| Źródło | Wynik | Wniosek |
|---|---|---|
| Unnisa, Ogutu, Dash 2025. *Remote Sensing Applications: Society and Environment*, art. 101690 (University of Southampton, https://eprints.soton.ac.uk/506068) [W] | woda w łanie (CWC) z S-2 zareagowała na suszę błyskawiczną 2022–2023 **wcześniej niż LAI i fAPAR** (pszenica i kukurydza, Hiszpania, Włochy, Węgry); korelacja z indeksem stresu parowania r = 0,59–0,66 | SWIR jako wskaźnik główny, zieleń jako szczegół |
| Laroche-Pinel i in. 2021. *Remote Sensing* 13(9): 1837, doi:10.3390/rs13091837 [P] | 36 działek 2018–2020, model z pasm S-2 (wg pełnego tekstu w F3: B4, B8, B6, B11) przewiduje potencjał wodny pędu: R² 0,40, RMSE 0,26 MPa | SWIR (B11) niesie informację o wodzie winorośli, ale umiarkowaną i przez model uczony na pomiarach |
| Laroche-Pinel i in. 2021. *OENO One* 55(4): 115–127, doi:10.20870/oeno-one.2021.55.4.4752 [F3] | 170 działek: mapy spójne z nawadnianiem, upałem i deszczem; ok. 1 bezchmurna scena na 7 dni w VI–IX | oczekiwana częstość danych w sezonie |
| Delval i in., EGU22-3908 (dwie winnice w Belgii, trawa w międzyrzędziu) [F3, konferencja] | NDWI/EVI: R² 0,67 z potencjałem przedświtowym; NDWI 0,64 | wskaźnik wody z SWIR działa także przy zadarnionym międzyrzędziu |

## 4. Kiedy roślinność reaguje

| Źródło | Wynik | Wniosek |
|---|---|---|
| Choi i in. 2017. *Terrestrial, Atmospheric and Oceanic Sciences* (MODIS NDVI, 132 miejsca) [W] | najsilniejszy związek NDVI z wilgotnością gleby przy opóźnieniu ok. **25 dni** w uprawach i zaroślach, ok. 10 dni w lasach i na łąkach | reakcja z ok. miesięcznym opóźnieniem |
| Ardö i in. 2017 (Sahel) [W] | NDVI najlepiej wiąże się z wilgotnością gleby sprzed 1 miesiąca | jw. |
| [D] F4, `docs/evidence/F4_eksperymenty/A_roslinnosc/a3_lag.csv` | NDMI wobec ISMN: w tym samym dniu R 0,41; wobec średniej anomalii gleby z 30 dni przed sceną R 0,47 [0,25; 0,63]; walidacja z pominięciem roku wybrała tę wersję w każdym z 9 lat | **T3 w planie:** anomalia działki wobec średniej anomalii gleby z 30 dni przed sceną. F4 widziało VINEYARD_06, więc miarą główną jest 14 pozostałych winnic |

## 5. Tło: gleba i międzyrzędzie

- Przy małym LAI wilgotność gleby silnie zmienia odbicie we wszystkich pasmach SWIR (modelowanie gleba–liść–łan dla
  pasm MODIS) [W]. Na początku sezonu SWIR widzi głównie wierzchnią warstwę gleby, później wodę w liściach [W].
- W winnicy latem w kadrze są rzędy, sucha gleba i trawa. Wskaźnik działki jest więc sumą stanu winorośli i tła.
  Pantaleoni Reluy 2022 i Laroche-Pinel 2021 uznały wpływ międzyrzędzia latem na południu Francji za mały [F3], ale
  w Gers międzyrzędzia bywają zadarnione — tego nie wiemy dla każdej działki.
- Wniosek: wskaźnik opisuje **„suchość działki wobec jej historii”**. To uczciwa odpowiedź na pytanie o anomalię.
  Wydzielenie winorośli (rozplątanie kanałów, Plan v8; podstawy w F3 §7.2) to kolejny etap.

## 6. Czy łączyć wskaźniki — nasze dane

Korelacje anomalii z (VINEYARD_06, 2016–2024, sceny SR 2,5 m z F4, `a2_variant_series.csv`) [D]:

| | NDMI | −CRSWIR | NDVI | NDRE |
|---|---|---|---|---|
| NDMI | 1 | 0,97 (VI–IX 0,968) | 0,94 (VI–IX 0,935) | — |
| NDVI | 0,94 | 0,90 | 1 | 0,98 |

- Średnia dwóch z o korelacji r ma wariancję (1 + r)/2. Przy r = 0,97 to 0,985: szum spada o mniej niż 1%.
- Złożenie NDVI + NDMI + CRSWIR (F4, V3d) dało R z ISMN 0,41 — tyle co samo NDMI (0,41) i NDVI (0,43).
- **Wniosek:** złożony wskaźnik „woda w liściach” (NDMI + CRSWIR) nie da więcej informacji niż NDMI. Daje odporność:
  jeśli jeden składnik zawiedzie w danej scenie (np. jasne tło po uprawie gleby), drugi to wyrówna. NDVI i NDRE
  pokazujemy jako szczegół i **nie** jako niezależne potwierdzenia.
- **Zastrzeżenie:** dane F4 to SR 2,5 m, a pasma 20 m po SR nie przeszły kontroli H-SR1. W W3b liczymy na natywnych
  10/20 m i raportujemy korelację składników od nowa.

## 7. Czego nie bierzemy i dlaczego

| Kandydat | Powód |
|---|---|
| Temperatura liści (najbezpośredniejszy sygnał stresu) | w Copernicusie tylko Sentinel-3, piksel 1 km — poziom okolicy, nie działki (D-048: tylko Copernicus) |
| GVMI, NMDI, MSI | kolejne warianty NIR–SWIR; przy r ≈ 0,97 między NDMI i CRSWIR nie wniosą nowej informacji; GVMI i NMDI zostają w F3 §7 jako kandydaci do rozplątania kanałów |
| CWC z modelu PROSAIL | brak produktu operacyjnego; łan rzędowy łamie założenia modelu [F3 §7.2] |
| Wilgotność gleby z S-2 (OPTRAM, STR) | F4: nie dodaje informacji ponad ERA5 |

## Źródła

- Ceccato P. i in. 2001. Detecting vegetation leaf water content using reflectance in the optical domain.
  *Remote Sensing of Environment* 77(1): 22–33. https://www.ipgp.fr/~jacquemoud/publications/ceccato2001.pdf [W]
- Gao B.-C. 1996. NDWI — A normalized difference water index for remote sensing of vegetation liquid water from space.
  *Remote Sensing of Environment* 58(3): 257–266. https://doi.org/10.1016/S0034-4257(96)00067-3 [W]
- Dutrieux R., Ose K., de Boissieu F., Féret J.-B. fordead: a python package for vegetation anomalies detection from
  SENTINEL-2 images. https://zenodo.org/records/12802457 ; opis: https://www.theia-land.fr/en/blog/product/fordead-a-python-package-for-vegetation-anomalies-detection-from-sentinel-2-images/ [W]
- Zamieranie świerka, CRSWIR najlepszym wskaźnikiem, *European Journal of Remote Sensing* 2025:
  https://hal.univ-lorraine.fr/ADEME/hal-05223935v1 [W]
- Unnisa, Ogutu, Dash 2025. Potential of Sentinel-2 derived Canopy Water Content as an Indicator of Flash Drought.
  *Remote Sensing Applications: Society and Environment*, 101690. https://eprints.soton.ac.uk/506068 [W]
- Laroche-Pinel E. i in. 2021. *Remote Sensing* 13(9): 1837. https://doi.org/10.3390/rs13091837 [P]
- Laroche-Pinel E. i in. 2021. *OENO One* 55(4): 115–127. https://doi.org/10.20870/oeno-one.2021.55.4.4752 [F3]
- Pantaleoni Reluy N. i in. 2022. *OENO One* 56(1): 145–159. https://doi.org/10.20870/oeno-one.2022.56.1.4632 [F3]
- Choi i in. 2017, *Terrestrial, Atmospheric and Oceanic Sciences*: https://doaj.org/article/ee067c2ae7454f6799e52f5a16286f6e [W]
- Ardö i in. 2017 (Sahel): https://www.nateko.lu.se/jonas-ardo/publication/5f714462-9c5c-481b-9ead-c9e5c7d3a6bb [W]
- Wpływ wilgotności gleby na pasma SWIR przy małym LAI (MODIS, model gleba–liść–łan): streszczenie z bazy publikacji
  zespołu MODIS; dokładny tytuł i autorów ustalić w W3b.0 [W]
- Hardisky M. A., Klemas V., Smart R. M. 1983 (NDII) — cytowane z pamięci, do sprawdzenia [—]
- Dane własne: `docs/evidence/F4_eksperymenty/A_roslinnosc/` (`a2_variant_series.csv`, `a2_variants_eval.csv`,
  `a3_lag.csv`), `docs/evidence/F7_v12/README.md`.
