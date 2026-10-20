# AgriScreen na blog GeoWorldLook

Pliki do publikacji (dane z przebiegu 2026-10-20, testy zamrożone 2026-10-18):

| Plik | Co to jest | Skąd |
|---|---|---|
| `agriscreen_panel.html` | interaktywny panel 15 winnic (EN), jeden samodzielny plik, bez bibliotek | `task_panel` (`panel.html` w `OUTPUT_DIR`) |
| `agriscreen_data.json` | dane panelu i notatnika | `task_panel` (`panel_data.json`) |
| `w3b_tests.csv` | zamrożone testy W3b | `task_parcel_tests` |
| `../../notebooks/AgriScreen_story.ipynb` | notatnik-opowieść (EN) z zapisanymi wykresami | `python build_story_notebook.py` |

**Publikacja:**
1. Panel: skopiuj `agriscreen_panel.html` do strony (np. `public/agriscreen/index.html` w projekcie na Vercel).
2. Notatnik: link do GitHub (`notebooks/AgriScreen_story.ipynb`) albo „Open in Colab”:
   `https://colab.research.google.com/github/geoworldlook/agriscreen/blob/main/notebooks/AgriScreen_story.ipynb`.

**Odświeżenie po nowym przebiegu:**
1. W Colab uruchom notatnik monitoringu (sekcja 6b tworzy `panel.html` i `panel_data.json`).
2. Skopiuj te pliki tutaj jako `agriscreen_panel.html` i `agriscreen_data.json`, razem z `w3b_tests.csv`.
3. Uruchom `python build_story_notebook.py`.
