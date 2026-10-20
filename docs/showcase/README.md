# AgriScreen na blog GeoWorldLook

Pliki do publikacji (dane z przebiegu w Colab 2026-10-20, testy zamrożone 2026-10-18; panel zbudowany pakietem
`agriscreen` 1.0):

| Plik | Co to jest | Skąd |
|---|---|---|
| `agriscreen_panel.html` | interaktywny panel 15 winnic (EN, układ jak Wago z projektu ESA WineEO), jeden samodzielny plik | `task_panel` (`panel.html`) |
| `agriscreen_data.json` | dane panelu i notatnika | `task_panel` (`panel_data.json`) |
| `agriscreen_panel.jpg` | zrzut panelu z tłem Sentinel-2 (do README i wpisu) | zrzut przeglądarki, kafle Esri wyłączone |
| `w3b_tests.csv` | zamrożone testy W3b | `task_parcel_tests` |
| `w3c_tests.csv`, `w3d_tests.csv` | testy eksperymentów W3c i W3d (oba nie przeszły; zapis pierwszego przebiegu) | `experiments.task_zones`, `task_months` |
| `../../notebooks/AgriScreen_story.ipynb` | notatnik-opowieść (EN) z zapisanymi wykresami | `python notebooks/build_story.py` |

**Co jest w panelu:**
- lista winnic (okolica Condom, Gers) z kolorem stanu przy ostatniej scenie;
- mapa Leaflet na zdjęciu satelitarnym Esri World Imagery (albo na obrazie Sentinel-2 w barwach naturalnych)
  z półprzezroczystą warstwą (suwak „Opacity”):
  - *Inside the parcel · 10 m pixels*: NDVI, NDRE, NDMI z 16 ostatnich bezchmurnych scen — gdzie w działce jest
    zieleniej, słabiej, wilgotniej; opis, bez normy i bez walidacji,
  - *Zones · pixel vs the rest of the parcel, same day*: piksel minus mediana tej samej działki w tym samym dniu;
    pierścień 10 m przy brzegu pominięty; opis, bez walidacji,
  - *Against its own history · whole parcel*: z całej działki wobec tej samej działki w 5 poprzednich latach
    (wielkość sprawdzona w protokole W3b);
- pod mapą statystyki (średnia, 10. i 90. percentyl, liczba pikseli w pasie 20 m od brzegu) albo tabela winnic;
- po prawej: stan działki, gleba w okolicy (ERA5-Land), pogoda (prognoza 7 dni Open-Meteo, ostatnie 10 dni,
  opad 30/90 dni z SPI, przymrozki i upały sezonu), dane działki;
- niżej: zdania karty, sezon, „How far to trust it” z legendą statusów (confirmed / checked / descriptive /
  experimental / not validated).

Warstw eksperymentów W3c („Zones vs usual”) i W3d („Lowest in N years”) panel nie rysuje — nie przeszły
zarejestrowanych testów (`docs/evidence/W3c_wyniki.md`, `W3d_wyniki.md`); w „How far to trust it” są tylko ich
wyniki ze statusem `experimental, not shown`. Wiersze W3c pokazują liczby pierwszego przebiegu (Z2 NDVI 15,4%);
po poprawce przedziału gleby w kodzie 1.0 następny przebieg da 15,3% (decyzja bez zmian).

Biblioteka Leaflet 1.9.4 ładuje się z unpkg; arkusz stylów jest wbudowany w plik (`agriscreen/assets/`, BSD-2).
Kafle Esri są pobierane tylko w przeglądarce oglądającego (nie zapisujemy ich).

**Uwaga o tej wersji pokazowej:** mapy pikseli powstały z kopii tych samych produktów Copernicus Sentinel-2 L2A
w AWS Open Data (kolekcja `sentinel-2-c1-l2a`), bo archiwum `S2_DIR` jest na Dysku Google. Daty 16 map różnią się
od panelu z Colab w 3 przypadkach (tu 23 VII, 28 VII, 2 VIII; w Colab 9 VIII, 21 IX, 28 IX) — inny zbiór scen
bezchmurnych. Prognoza i ostatnie 10 dni ERA5-Land pochodzą z tego samego przebiegu (prognoza z 20.10.2026).
W Colab `task_panel` liczy wszystko z archiwum projektu i pobiera świeżą prognozę.

**Publikacja:**
1. Panel: skopiuj `agriscreen_panel.html` do strony (np. `public/agriscreen/index.html` w projekcie na Vercel).
2. Notatnik: link do GitHub (`notebooks/AgriScreen_story.ipynb`) albo „Open in Colab”:
   `https://colab.research.google.com/github/geoworldlook/agriscreen/blob/main/notebooks/AgriScreen_story.ipynb`.

**Odświeżenie po nowym przebiegu:**
1. W Colab uruchom `notebooks/AgriScreen_Monitor.ipynb` (sekcja 7 tworzy `panel.html` i `panel_data.json`).
2. Skopiuj te pliki tutaj jako `agriscreen_panel.html` i `agriscreen_data.json`, razem z `w3b_tests.csv`
   (i `w3c_tests.csv`, `w3d_tests.csv`, jeśli eksperymenty były włączone).
3. Uruchom `python notebooks/build_story.py`.
