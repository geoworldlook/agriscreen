# Przebieg tygodniowy w GitHub Actions

Od wersji 1.4.0 główną ścieżką jest workflow `.github/workflows/weekly.yml` (poniedziałek i czwartek, 05:30 UTC,
także ręcznie: *Actions → weekly → Run workflow*). Komputer z Harmonogramem zadań i Colab zostają zapasem.

## Jak to działa

1. Workflow pobiera kod (to repozytorium) i dane z **prywatnego** repozytorium `geoworldlook/agriscreen-data`
   (ten sam układ co folder `GeoWorldLook/agriwatch` na Dysku: `data/01_Raw_Sentinel2`, `data/registry`, `data/ismn` …).
   Dane są prywatne, bo licencja ISMN zabrania ich udostępniania.
2. Klucze z sekretów GitHub trafiają do folderu `secrets/` obok danych (poza oboma repozytoriami) i są kasowane na końcu.
3. `python -m agriscreen weekly --no-pull`: wszystkie zadania, Earth Engine przez konto serwisowe
   (`EE_SERVICE_ACCOUNT_KEY`), panel do `docs/showcase` i commit w tym repozytorium (GitHub Pages).
4. Kontrola podsumowania `data/logs/last_weekly.json`: zadanie z błędem albo nieopublikowany panel = przebieg nieudany.
5. Nowy stan (sceny, cache, rejestr, logi) wraca commitem do `agriscreen-data`.
6. Nieudany przebieg otwiera issue „Weekly run failed”; udany je zamyka.

## Konfiguracja (raz, robi autor)

### 1. Prywatne repozytorium danych

1. Utwórz na GitHubie repozytorium `agriscreen-data`, **Private**, bez README.
2. W PowerShell (ścieżkę do Dysku popraw, jeśli inna):

```powershell
cd $HOME\Desktop
git clone https://github.com/geoworldlook/agriscreen-data.git
robocopy "G:\Mój dysk\GeoWorldLook\agriwatch" agriscreen-data /E /XD logs _selftest /XF .agriscreen.lock
cd agriscreen-data
"data/registry/.agriscreen.lock`ndata/_selftest/" | Out-File -Encoding utf8 .gitignore
git add -A
git commit -m "initial data from Google Drive"
git push
```

Plik większy niż 100 MB GitHub odrzuci (sprawdź: `Get-ChildItem -Recurse | Where Length -gt 100MB`). Całość
najlepiej poniżej 2 GB. Folderu `secrets` **nie** kopiuj.

### 2. Token do repozytorium danych

1. <https://github.com/settings/personal-access-tokens/new> (fine-grained token).
2. *Repository access*: **Only select repositories** → `agriscreen-data`.
3. *Permissions → Repository permissions → Contents*: **Read and write**.
4. Ważność: 1 rok (przypomnienie w kalendarzu: po wygaśnięciu przebieg zgłosi błąd checkout).
5. W repozytorium `agriscreen`: *Settings → Secrets and variables → Actions → New repository secret*,
   nazwa `AGRISCREEN_DATA_TOKEN`, wartość: token.

### 3. Konto serwisowe Earth Engine

1. <https://console.cloud.google.com/iam-admin/serviceaccounts?project=ee-geoworldlook> → *Create service account*,
   nazwa `agriscreen-actions`.
2. Role: **Earth Engine Resource Viewer** i **Service Usage Consumer**.
3. Konto → *Keys → Add key → Create new key → JSON*; plik się pobierze.
4. Sekret `EE_SERVICE_ACCOUNT_KEY`: wklej **całą zawartość** pliku JSON. Potem usuń plik z dysku.

Jeśli projekt GEE nie nazywa się `ee-geoworldlook`, dodaj zmienną (zakładka *Variables*) `EE_PROJECT`.

### 4. Copernicus Data Space (SWI)

Z pliku `GeoWorldLook/secrets/cdse.env` na Dysku przepisz dwa sekrety: `CDSE_CLIENT_ID` i `CDSE_CLIENT_SECRET`.

### 5. Pierwszy przebieg i wyłączenie Harmonogramu

1. *Actions → weekly → Run workflow*. Pierwszy przebieg może trwać dłużej (sceny od ostatniego przebiegu lokalnego).
2. Po udanym przebiegu wyłącz zadanie na komputerze, żeby dwa przebiegi nie pisały do różnych kopii danych:
   `Disable-ScheduledTask -TaskName 'AgriScreen - przebieg tygodniowy'`.

## Zapas: komputer albo Colab

Dane na Dysku przestają być aktualizowane. Przed przebiegiem zapasowym ustaw katalog danych na klon
`agriscreen-data` (np. `$env:AGRISCREEN_DATA_DIR = "$HOME\Desktop\agriscreen-data"`), a po nim zrób w nim commit i push. Klucze
czytane są z folderu `secrets` obok katalogu danych (`..\secrets`).
