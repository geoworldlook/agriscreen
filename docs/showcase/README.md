# AgriScreen na blog GeoWorldLook

Pliki do publikacji (dane z przebiegu 2026-10-20, testy zamrożone 2026-10-18):

| Plik | Co to jest | Skąd |
|---|---|---|
| `agriscreen_panel.html` | interaktywny panel 15 winnic (EN, układ jak Wago z projektu ESA WineEO), jeden samodzielny plik | `task_panel` (`panel.html` w `OUTPUT_DIR`) |
| `agriscreen_data.json` | dane panelu i notatnika | `task_panel` (`panel_data.json`) |
| `w3b_tests.csv` | zamrożone testy W3b | `task_parcel_tests` |
| `../../notebooks/AgriScreen_story.ipynb` | notatnik-opowieść (EN) z zapisanymi wykresami | `python build_story_notebook.py` |

**Co jest w panelu:**
- lista winnic (okolica Condom, Gers) z kolorem stanu przy ostatniej scenie,
- mapa Leaflet na zdjęciu satelitarnym Esri World Imagery z półprzezroczystą warstwą (suwak „Opacity”):
  - *Inside the parcel · 10 m pixels*: NDVI, NDRE, NDMI z 16 ostatnich bezchmurnych scen — gdzie w działce jest
    zieleniej, słabiej, wilgotniej; opis, bez normy i bez walidacji,
  - *Zones · pixel vs the rest of the parcel, same day*: piksel minus mediana tej samej działki w tym samym dniu
    (NDVI, NDRE, NDMI) — słabsze i mocniejsze strefy działki bez porównywania lat, więc przesunięcia zdjęć między
    latami nie mają znaczenia; pierścień 10 m przy brzegu pominięty (mieszane piksele); opis, bez walidacji,
  - *Zones vs usual* (W3c, `step_13`): to samo miejsce wobec swoich 5 poprzednich lat, względem reszty działki;
    próg z testu szumu; pojawi się dopiero po liczeniu w Colab i tylko, jeśli przejdzie trzy warunki protokołu
    (`docs/evidence/W3c_protokol_strefy.md` §6) — w tej wersji pokazowej jeszcze go nie ma,
  - *Against its own history · whole parcel*: z całej działki wobec tej samej działki w 5 poprzednich latach
    (tylko dla całej działki — to jest wielkość sprawdzona w protokole W3b; anomalia pojedynczego piksela byłaby
    zbyt zaszumiona: przesunięcia zdjęć o ok. piksel, pasma 20 m, mało scen w normie),
- pod mapą statystyki (średnia, 10. i 90. percentyl, rozrzut, liczba pikseli w pasie 20 m od brzegu) albo tabela
  wszystkich winnic,
- po prawej: stan działki, gleba w okolicy (wskaźnik, ERA5-Land), pogoda (prognoza 7 dni Open-Meteo, ostatnie
  10 dni, opad 30/90 dni z SPI, przymrozki i upały sezonu), dane działki,
- niżej: zdania karty, sezon, „How far to trust it”.

Pod kaflami Esri leży obraz Sentinel-2 w barwach naturalnych. Widać go, gdy kafle się nie wczytają (np. podgląd
bez sieci) albo po wyborze „Sentinel-2 natural colour”. Biblioteka Leaflet 1.9.4 ładuje się z unpkg; jej arkusz
stylów jest wbudowany w plik (`assets/leaflet-1.9.4.css`, licencja BSD-2).

**Uwaga o tej wersji pokazowej:** mapy pikseli w tym pliku powstały z kopii tych samych produktów Copernicus
Sentinel-2 L2A w AWS Open Data (kolekcja `sentinel-2-c1-l2a`, sceny z tych samych dni co szereg działek), bo
archiwum `S2_DIR` jest na Dysku Google. Prognoza i ostatnie 10 dni ERA5-Land pochodzą z dashboardu tego samego
przebiegu (prognoza z 20.10.2026). W Colab `task_panel` liczy wszystko z archiwum projektu i pobiera świeżą prognozę.

**Publikacja:**
1. Panel: skopiuj `agriscreen_panel.html` do strony (np. `public/agriscreen/index.html` w projekcie na Vercel).
2. Notatnik: link do GitHub (`notebooks/AgriScreen_story.ipynb`) albo „Open in Colab”:
   `https://colab.research.google.com/github/geoworldlook/agriscreen/blob/main/notebooks/AgriScreen_story.ipynb`.

**Odświeżenie po nowym przebiegu:**
1. W Colab uruchom notatnik monitoringu (sekcja 6b tworzy `panel.html` i `panel_data.json`).
2. Skopiuj te pliki tutaj jako `agriscreen_panel.html` i `agriscreen_data.json`, razem z `w3b_tests.csv`.
3. Uruchom `python build_story_notebook.py`.
