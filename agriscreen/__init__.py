"""
AgriScreen v1 — winnice wobec własnej historii z otwartych danych Copernicus.

Produkt: panel EN dla 15 winnic w okolicy Condom (Gers) i jego dane JSON (panel.html, panel_data.json).
Uruchomienie w Colab (notatnik notebooks/AgriScreen_Monitor.ipynb) albo lokalnie:

    from agriscreen.runtime import setup_runtime
    from agriscreen.pipeline import run_all
    rt = setup_runtime(PROJECT_DIR)
    run_all(rt)

Moduły: config (ustawienia), runtime (środowisko, rejestr), ingest (dane), metrics (wskaźniki, anomalie),
stations (czujniki ISMN), reference (walidacja gleby), weather (pogoda), parcel (W3b), card (zdania karty),
panel (produkt), pipeline (zadania), experiments (W3c, W3d; wyłączone), selftest (test na danych syntetycznych).
"""

__version__ = "1.1.1"
