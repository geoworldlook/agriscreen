# AgriScreen - przygotowanie komputera z Windows (jednorazowo; mozna uruchamiac wielokrotnie).
# W PowerShell (zwykle okno, bez uprawnien administratora):
#   irm https://raw.githubusercontent.com/geoworldlook/agriscreen/main/scripts/windows/setup_workspace.ps1 | iex
#
# Co robi (tylko to, czego brakuje):
#   1. instaluje Git, Dysk Google i Miniforge (winget),
#   2. tworzy na pulpicie folder roboczy GeoWorldLook: projects\, data\, scripts\,
#   3. klonuje kod do projects\agriscreen,
#   4. znajduje dane na Dysku Google (Moj dysk\GeoWorldLook\agriwatch) i podpina je jako data\agriscreen,
#   5. zapisuje ustawienia (local_settings.json), tworzy srodowisko Python "agriscreen" (conda),
#   6. logowanie: Earth Engine i GitHub (raz, w przegladarce),
#   7. zadanie w Harmonogramie Windows: co poniedzialek 07:30 przebieg tygodniowy (liczy, publikuje panel na GitHub),
#   8. opcjonalnie: test bez sieci i Claude Code.

function Install-AgriScreenWorkspace {
    $ErrorActionPreference = 'Stop'
    $RepoUrl  = 'https://github.com/geoworldlook/agriscreen.git'
    $Desktop  = [Environment]::GetFolderPath('Desktop')
    $WS       = Join-Path $Desktop 'GeoWorldLook'
    $Proj     = Join-Path $WS 'projects\agriscreen'
    $Scripts  = Join-Path $WS 'scripts'
    $TaskName = 'AgriScreen - przebieg tygodniowy'

    function Step($t) { Write-Host "`n== $t" -ForegroundColor Green }
    function Info($t) { Write-Host "   $t" }
    function Warn($t) { Write-Host "   UWAGA: $t" -ForegroundColor Yellow }
    function Have($c) { [bool](Get-Command $c -ErrorAction SilentlyContinue) }
    function Refresh-Path {
        $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
    }
    function Ask($q) { (Read-Host "$q [t/N]") -match '^(t|y|tak|yes)$' }
    function Write-Utf8($path, $text) { [IO.File]::WriteAllText($path, $text, (New-Object Text.UTF8Encoding($false))) }

    # ------------------------------------------------------------------------------------------------------------------
    Step '1. Programy: Git, Dysk Google, Miniforge'
    $wingetOk = Have 'winget'
    function Install-App($id, $present) {
        if ($present) { Info "$id - jest"; return }
        if (-not $wingetOk) { Warn "brak winget: zainstaluj $id recznie i uruchom skrypt ponownie"; return }
        Info "instaluje $id ..."
        winget install --id $id -e --silent --accept-source-agreements --accept-package-agreements | Out-Null
    }
    Install-App 'Git.Git' (Have 'git')
    Install-App 'Google.GoogleDrive' ((Test-Path "$env:ProgramFiles\Google\Drive File Stream") -or (Get-Process -Name 'GoogleDriveFS' -ErrorAction SilentlyContinue))
    $condaCands = @("$env:USERPROFILE\miniforge3", "$env:LOCALAPPDATA\miniforge3", "$env:ProgramData\miniforge3",
                    "$env:USERPROFILE\miniconda3", "$env:USERPROFILE\anaconda3", "$env:ProgramData\anaconda3")
    $CondaRoot = $condaCands | Where-Object { Test-Path (Join-Path $_ 'Scripts\conda.exe') } | Select-Object -First 1
    Install-App 'CondaForge.Miniforge3' ([bool]$CondaRoot)
    Refresh-Path
    if (-not $CondaRoot) { $CondaRoot = $condaCands | Where-Object { Test-Path (Join-Path $_ 'Scripts\conda.exe') } | Select-Object -First 1 }
    if (-not (Have 'git')) { throw 'Git nie jest dostepny. Zamknij PowerShell, otworz ponownie i uruchom skrypt jeszcze raz.' }

    # ------------------------------------------------------------------------------------------------------------------
    Step "2. Folder roboczy na pulpicie: $WS"
    foreach ($d in 'projects', 'data', 'scripts') { New-Item -ItemType Directory -Force -Path (Join-Path $WS $d) | Out-Null }
    $readme = @"
GeoWorldLook - folder roboczy (utworzony przez setup_workspace.ps1)

projects\<projekt>   kod z GitHub (git). AgriScreen: projects\agriscreen
data\<projekt>       dane projektu = link do Dysku Google (synchronizowane, wspolne z Colab)
scripts\             uruchamianie: przebieg teraz, otworz panel, logi; zadanie tygodniowe w Harmonogramie zadan

Klucze (cdse.env itd.) leza tylko na Dysku Google: Moj dysk\GeoWorldLook\secrets - nie kopiuj ich tutaj.
Nowy projekt: projects\<nazwa> (repozytorium) + data\<nazwa> (dane na Dysku).
"@
    Write-Utf8 (Join-Path $WS 'README.txt') $readme
    Info 'projects\, data\, scripts\ i README.txt gotowe'

    # ------------------------------------------------------------------------------------------------------------------
    Step '3. Kod: projects\agriscreen'
    if (Test-Path (Join-Path $Proj '.git')) {
        git -C $Proj pull --ff-only
    } else {
        git clone $RepoUrl $Proj
    }
    Info "kod: $(git -C $Proj log -1 --format='%h %s')"

    # ------------------------------------------------------------------------------------------------------------------
    Step '4. Dane na Dysku Google'
    $cands = @()
    foreach ($drv in Get-PSDrive -PSProvider FileSystem) {
        foreach ($n in 'My Drive', 'Moj dysk', ('M' + [char]0x00F3 + 'j dysk')) { $cands += Join-Path $drv.Root "$n\GeoWorldLook\agriwatch" }
    }
    foreach ($n in 'My Drive', ('M' + [char]0x00F3 + 'j dysk')) { $cands += Join-Path $env:USERPROFILE "$n\GeoWorldLook\agriwatch" }
    $Data = $cands | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $Data) {
        Warn 'Nie widze folderu GeoWorldLook\agriwatch na Dysku Google.'
        Info 'Otworz aplikacje Dysk Google (ikona w zasobniku), zaloguj sie kontem z danymi projektu,'
        Info 'poczekaj, az pojawi sie dysk G: (Moj dysk), i uruchom ten skrypt ponownie.'
        return
    }
    Info "dane: $Data"
    $link = Join-Path $WS 'data\agriscreen'
    if (-not (Test-Path $link)) {
        try {
            New-Item -ItemType Junction -Path $link -Target $Data | Out-Null
            Info 'data\agriscreen -> Dysk Google (lacze)'
        } catch {
            $sh = (New-Object -ComObject WScript.Shell).CreateShortcut("$link.lnk")
            $sh.TargetPath = $Data; $sh.Save()
            Info 'data\agriscreen.lnk -> Dysk Google (skrot)'
        }
    }
    if (-not (Test-Path (Join-Path (Split-Path $Data) 'secrets'))) { Warn 'brak folderu GeoWorldLook\secrets na Dysku (klucze CDSE do SWI)' }
    Info 'Dla szybkosci: w Eksploratorze kliknij prawym na Moj dysk\GeoWorldLook -> Dostep offline -> Dostepne offline.'

    $settings = [ordered]@{ data_dir = $Data; gee_project = 'ee-geoworldlook'; branch = 'main'; publish = $true; experiments = $false; remote = 'origin' }
    Write-Utf8 (Join-Path $Proj 'local_settings.json') ($settings | ConvertTo-Json)
    Info 'projects\agriscreen\local_settings.json zapisany'

    # ------------------------------------------------------------------------------------------------------------------
    Step '5. Srodowisko Python "agriscreen" (conda-forge; pierwszy raz kilka minut)'
    if (-not $CondaRoot) { throw 'Brak conda (Miniforge). Zamknij PowerShell, otworz ponownie i uruchom skrypt jeszcze raz.' }
    $conda = Join-Path $CondaRoot 'Scripts\conda.exe'
    $envs = & $conda env list
    if ($envs -match '^agriscreen\s') {
        & $conda env update -n agriscreen -f (Join-Path $Proj 'environment.yml') --prune
    } else {
        & $conda env create -f (Join-Path $Proj 'environment.yml')
    }
    function Py { & $conda run -n agriscreen --no-capture-output --cwd $Proj python @args }
    Py -c "import rasterio, geopandas, ee; print('   biblioteki OK')"

    # ------------------------------------------------------------------------------------------------------------------
    Step '6. Logowanie (raz): Earth Engine i GitHub'
    if (-not (Test-Path "$env:USERPROFILE\.config\earthengine\credentials")) {
        Info 'Earth Engine: otworzy sie przegladarka - zaloguj sie kontem Google z projektem ee-geoworldlook.'
        & $conda run -n agriscreen --no-capture-output earthengine authenticate
    } else { Info 'Earth Engine: poswiadczenia sa' }
    if (-not (git -C $Proj config user.email)) {
        git -C $Proj config user.name  (Read-Host 'Imie i nazwisko do commitow')
        git -C $Proj config user.email (Read-Host 'E-mail do commitow (ten z GitHub)')
    }
    Info 'GitHub: proba wyslania bez zmian (przy pierwszym razie okno logowania Git Credential Manager).'
    git -C $Proj push --dry-run origin main

    # ------------------------------------------------------------------------------------------------------------------
    Step '7. Skrypty i zadanie tygodniowe'
    $activate = Join-Path $CondaRoot 'Scripts\activate.bat'
    $runCmd = @"
@echo off
rem AgriScreen: przebieg tygodniowy (Harmonogram zadan albo dwuklik). Log: dane\data\logs
call "$activate" agriscreen
cd /d "$Proj"
python -m agriscreen weekly
"@
    Write-Utf8 (Join-Path $Scripts 'agriscreen_przebieg_teraz.cmd') $runCmd
    Write-Utf8 (Join-Path $Scripts 'agriscreen_otworz_panel.cmd') "@echo off`r`nstart `"`" `"$Data\data\05_Final_Outputs\agriwatch\panel.html`"`r`n"
    Write-Utf8 (Join-Path $Scripts 'agriscreen_logi.cmd') "@echo off`r`nstart `"`" `"$Data\data\logs`"`r`n"
    $shell = "@echo off`r`ncall `"$activate`" agriscreen`r`ncd /d `"$Proj`"`r`ncmd /k`r`n"
    Write-Utf8 (Join-Path $Scripts 'agriscreen_konsola.cmd') $shell
    $jup = "@echo off`r`nrem AgriScreen: notatnik Jupyter z podgladem wynikow. Zamkniecie: Ctrl+C w tym oknie.`r`ncall `"$activate`" agriscreen`r`ncd /d `"$Proj`"`r`nif not exist notebooks\AgriScreen_Local.ipynb python notebooks\build_local.py`r`njupyter lab notebooks\AgriScreen_Local.ipynb`r`n"
    Write-Utf8 (Join-Path $Scripts 'agriscreen_jupyter.cmd') $jup

    $action   = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument "/c `"$(Join-Path $Scripts 'agriscreen_przebieg_teraz.cmd')`"" -WorkingDirectory $Proj
    $trigger  = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At '07:30'
    $settingsT = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 6)
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settingsT -Force `
        -Description 'AgriScreen: nowe sceny Sentinel-2, przeliczenie, panel na GitHub (python -m agriscreen weekly)' | Out-Null
    Info "zadanie '$TaskName': poniedzialek 07:30 (gdy komputer byl wylaczony - po wlaczeniu)"

    # ------------------------------------------------------------------------------------------------------------------
    Step '8. Opcjonalnie'
    if (Ask 'Uruchomic test bez sieci (kilka minut)?') { Py -m agriscreen selftest --out (Join-Path $env:TEMP 'agriscreen_selftest') }
    if (-not (Have 'claude')) {
        if (Ask 'Zainstalowac Claude Code (Claude bedzie mogl pracowac na tym komputerze)?') {
            Invoke-RestMethod https://claude.ai/install.ps1 | Invoke-Expression
        }
    }

    Step 'Gotowe'
    Info "Folder roboczy: $WS"
    Info 'Przebieg teraz: scripts\agriscreen_przebieg_teraz.cmd (pierwszy raz moze trwac dlugo).'
    Info 'Claude na tym komputerze: w folderze projects\agriscreen uruchom "claude" albo "claude remote-control".'
}

Install-AgriScreenWorkspace
