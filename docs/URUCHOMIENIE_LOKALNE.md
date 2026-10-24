# AgriScreen na własnym komputerze (Windows) — bez Colab

Cel: obliczenia na komputerze, dane na Dysku Google (synchronizowane, wspólne z Colab jako zapasem), wyniki co tydzień
same trafiają na GitHub, a Claude pracuje na tym komputerze i prowadzi projekt.

## 1. Jedno polecenie

Otwórz **PowerShell** (Start → wpisz „PowerShell”, zwykłe okno) i wklej:

```powershell
irm https://raw.githubusercontent.com/geoworldlook/agriscreen/main/scripts/windows/setup_workspace.ps1 | iex
```

Skrypt robi tylko to, czego brakuje, więc można go uruchomić ponownie (np. po zainstalowaniu Dysku Google):

1. instaluje Git, Dysk Google i Miniforge (Python z conda-forge) przez `winget`;
2. tworzy na pulpicie folder **GeoWorldLook** (układ niżej);
3. klonuje kod do `projects\agriscreen`;
4. znajduje dane na Dysku Google (`Mój dysk\GeoWorldLook\agriwatch`) i podpina je jako `data\agriscreen`;
5. zapisuje `projects\agriscreen\local_settings.json` (ścieżka danych; plik poza git);
6. tworzy środowisko Python `agriscreen` (`environment.yml`; pierwszy raz kilka–kilkanaście minut);
7. prosi o jednorazowe logowanie: Earth Engine (przeglądarka) i GitHub (okno Git Credential Manager);
8. dodaje zadanie w Harmonogramie zadań: **co poniedziałek 07:30** (albo zaraz po włączeniu komputera, jeśli był
   wyłączony);
9. pyta o test bez sieci i o instalację Claude Code.

Przed pierwszym uruchomieniem: zaloguj się w aplikacji **Dysk Google** kontem, na którym są dane projektu.
Dla szybkości kliknij prawym przyciskiem `Mój dysk\GeoWorldLook` → *Dostęp offline* → *Dostępne offline* (pliki
leżą wtedy na dysku komputera i nadal się synchronizują).

## 2. Układ folderu na pulpicie

```text
Pulpit\GeoWorldLook\
├── README.txt
├── projects\
│   └── agriscreen\          kod (git): pakiet agriscreen\, notebooks\, docs\, scripts\
├── data\
│   └── agriscreen  ──▶      łącze do Dysku Google: Mój dysk\GeoWorldLook\agriwatch
│                             (data\01_Raw_Sentinel2, data\registry, data\05_Final_Outputs\agriwatch, data\logs …)
└── scripts\
    ├── agriscreen_przebieg_teraz.cmd   przebieg tygodniowy na żądanie (to samo co Harmonogram)
    ├── agriscreen_otworz_panel.cmd     otwiera panel.html z ostatniego przebiegu
    ├── agriscreen_logi.cmd             otwiera folder z logami
    └── agriscreen_konsola.cmd          konsola z aktywnym środowiskiem, w folderze projektu
```

Zasady: kod tylko w `projects\` (GitHub), dane tylko na Dysku (`data\` to łącza), klucze tylko w
`Mój dysk\GeoWorldLook\secrets`. Kolejny projekt: `projects\<nazwa>` + `data\<nazwa>`.

## 3. Co robi przebieg tygodniowy (`python -m agriscreen weekly`)

1. Blokada: drugi przebieg w tym samym czasie (np. Colab) kończy się od razu.
2. `git pull` — nowy kod z GitHub (pomijany, gdy w folderze kodu są niezapisane zmiany).
3. Wszystkie zadania: nowe sceny Sentinel-2, ERA5-Land, SWI, statystyki 15 winnic, gleba, testy W3b, anomalie,
   walidacja, pogoda, panel, raport. Earth Engine bez okna logowania; gdy logowanie wygaśnie, przebieg liczy na
   danych z dysku i zapisuje błąd w logu.
4. Gdy panel powstał: kopia do `docs\showcase`, notatnik na blog, commit **tylko tych plików** i push na `main`.
5. Log: `data\agriscreen\data\logs\weekly_<data>.log`, podsumowanie `last_weekly.json`.

Inne polecenia (w `agriscreen_konsola.cmd`):

| Polecenie | Co robi |
|---|---|
| `python -m agriscreen run` | wszystkie zadania bez publikacji (`--no-ingest`: bez pobierania, `--experiments`: W3c i W3d) |
| `python -m agriscreen publish` | publikacja panelu i notatnika z ostatnich wyników |
| `python -m agriscreen weekly --no-publish` | przebieg tygodniowy bez wysyłania na GitHub |
| `python -m agriscreen selftest` | test bez sieci (kilka minut) |
| `python -m agriscreen settings` | pokaż ustawienia |

## 4. Claude na tym komputerze

Ta sesja w przeglądarce (claude.ai/code) działa w chmurze i nie widzi Twojego komputera. Żeby Claude liczył,
sprawdzał logi i prowadził projekt lokalnie:

- **Claude Code w terminalu:** w `agriscreen_konsola.cmd` (albo PowerShell w `projects\agriscreen`) uruchom `claude`.
  Instalacja: `irm https://claude.ai/install.ps1 | iex` (skrypt z §1 proponuje ją na końcu).
- **Sterowanie z telefonu lub przeglądarki:** w tym samym folderze `claude remote-control` — sesja pojawi się
  w aplikacji Claude (Code). Komputer musi być włączony.
- **Aplikacja Claude Desktop:** zakładka Code → wybierz folder `projects\agriscreen`.

Pierwsza wiadomość do lokalnej sesji: „Przeczytaj docs/URUCHOMIENIE_LOKALNE.md i docs/STAN_I_PLAN.md, sprawdź ostatni
przebieg (last_weekly.json) i zaproponuj plan na ten tydzień.”

## 5. Gdy coś nie działa

| Objaw | Co zrobić |
|---|---|
| Skrypt: „Nie widzę folderu GeoWorldLook\agriwatch” | zaloguj się w Dysku Google, poczekaj na dysk G:, uruchom skrypt ponownie |
| Log: „GEE: brak ważnych poświadczeń” | w konsoli: `earthengine authenticate` |
| Log: „push nieudany” | w konsoli: `git push` (okno logowania GitHub), potem `python -m agriscreen publish` |
| Log: „inny przebieg trwa” | czy nie liczy Colab? jeśli nie — usuń `data\registry\.agriscreen.lock` |
| Przebieg wolny | `Mój dysk\GeoWorldLook` → *Dostępne offline* |
| Środowisko się nie tworzy: „Could not find 'share/conda-launchers/cli-64.exe'” (conda 26.9) | najpierw `conda create -n agriscreen -y python=3.12 conda-launchers`, potem `conda env update -n agriscreen -f environment.yml` (bez `--prune`) |
