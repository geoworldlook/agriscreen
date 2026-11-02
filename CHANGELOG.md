# Changelog

## Repository history — 2026-11-02

The git history was rewritten (decision D-094), in two passes on the same day. Removed from all commits: the raw ISMN
sensor files and a daily ISMN sensor series (the ISMN terms forbid passing the data on), and private notes of the
author (two planning notes, private parts of a few archived plans, local file paths, an e-mail address in the author
field of 31 commits, now the author's GitHub address). Commit order, dates, messages, code, results and protocols are
unchanged; protocol files are identical, so their registered SHA-256 sums still match. Commit IDs changed: original →
intermediate → new in `docs/evidence/historia_git_mapa.csv`, details in `docs/evidence/historia_git.md`.

## 1.3.1 — 2026-11-02

- Fix: the weekly job could wait for hours at `git push`. The conda environment had its own git (conda-forge), and
  its default opens a “select a credential helper” window. Nobody clicks it in a scheduled run. `git` is removed from
  `environment.yml`, so the system Git (Git for Windows, installed by the setup script) with its saved login is used.
  Git calls in `agriscreen/local.py` never ask for a login (`GIT_TERMINAL_PROMPT=0`, `GCM_INTERACTIVE=never`):
  a missing login is an error in the log, the commit stays local, and the next run pushes it.
- Panel “How far to trust it”: the W7 rows now say “the measurement agreed on X% of hint days” (K2: “hint scenes”).
  The old text (“confirmed by the measurement on…”) sounded like a confirmation next to the status “not confirmed”.
- Data citations: the 10 ICOS data objects are cited with persistent identifiers in `docs/evidence/W7_wyniki.md` §7,
  and the list of downloaded W7 files with SHA-256 checksums is published as `docs/evidence/W7_zrodla.csv`. README:
  Copernicus and ERA5-Land notices, Météo-France licence; product card: “each layer says how it was checked”.

## 1.3.0 — 2026-11-02

- **W7 (protocol D-093, registered before computing): product hints vs real ground measurements.**
  “Dry soil” hint confirmed: in situ sensors below their usual level on 81.2% [74.6; 87.8] of 4,783 hint days vs
  49.3% by chance (10 ICOS stations in France + ISMN Condom). “Vegetation below its own normal” vs measured
  evapotranspiration: 67.1% vs 51.7%, interval includes chance — not confirmed. Results:
  `docs/evidence/W7_wyniki.md`; notebook `notebooks/experiments/W7_wskazowki.ipynb`.
- Code: `agriscreen/experiments/w7_data.py` (ICOS L2 archives, customs data, station squares, manifest with SHA-256
  and licence), `w7.py` (measured-only truth, hints, hit rates, panel rows). Panel “How far to trust it” shows K1 and
  K2; `w7_tests.csv` is published weekly to `docs/showcase/`.
- **ISMN licence:** raw ISMN sensor files removed from the public repository (ISMN terms forbid redistribution);
  `ISMN_DIR` now points to the data folder (identical content, frozen W3b results unchanged). Selftest and CI use a
  synthetic sensor in the ISMN file format. README: licence note and references.

## 1.2.1 — 2026-11-01

- Live panel: `docs/` is served by GitHub Pages; the weekly job already updates `docs/showcase/`, so
  https://geoworldlook.github.io/agriscreen/showcase/agriscreen_panel.html is always the latest panel. The website
  links to it as “Live demo”.
- CI (`.github/workflows/selftest.yml`): ruff and the offline end-to-end test on every push and pull request
  (weekly panel commits are skipped).
- README: product card (problem, user, solution, evidence, status, limits, next), W3e result.
- Docs: older plans moved to `docs/archive/plans/` (protocol hashes unchanged); experiment W3e (D-092) notebook and
  results in `notebooks/experiments/` and `docs/evidence/`.

## 1.2.0 — 2026-10-24

- Local Jupyter notebook to look at the results, modelled on the Colab notebook: `notebooks/build_local.py` makes
  `notebooks/AgriScreen_Local.ipynb` (not in git, so saved outputs do not block `git pull` in the weekly job).
  By default it only reads the outputs from Drive: last run and log, a table of the 15 vineyards (z of the last
  scene), a z chart for one vineyard, W3b tests, water layer validation, the panel, the run report and the registry.
  With `RECOMPUTE = True` it runs everything like `python -m agriscreen run` (with the lock, no publishing).
- `environment.yml`: `jupyterlab`. `setup_workspace.ps1` also writes `scripts\agriscreen_jupyter.cmd`.
- Guide: `docs/URUCHOMIENIE_LOKALNE.md` §3a.

## 1.1.2 — 2026-10-24

- Fix: the panel had no 7-day forecast since 1.0. `panel.weather_data` calls `weather.fetch_forecast`, but the
  function stayed in the old `step_06_dashboard.py` and was not moved to the package. It is now in
  `agriscreen/weather.py`, unchanged (Open-Meteo: rain, Tmin, Tmax, ET0 FAO). The self-test did not catch it,
  because it passes a ready forecast.
- `config.py`: no `SyntaxWarning` from a Windows path in a docstring.

## 1.1.1 — 2026-10-24

- Fix: the panel failed on Windows (`ValueError: Invalid format string`): the date format `%-d` works only on
  Linux and macOS. `fmt_date` now builds the date by hand; the text is the same on every system ("5 October 2024").
- Guide (`docs/URUCHOMIENIE_LOKALNE.md`): what to do when conda 26.9 stops with
  "Could not find 'share/conda-launchers/cli-64.exe'".

## 1.1.0 — 2026-10-24

Runs on your own computer instead of Colab.

- `python -m agriscreen run | weekly | publish | selftest | settings` (`agriscreen/local.py`, `agriscreen/__main__.py`).
- Code and data can live in different folders: `make_config(project_dir, data_dir=...)`,
  `setup_runtime(..., data_dir=...)`. Colab keeps working with the old layout (data next to the code on Drive).
- Weekly job: lock against parallel runs, `git pull`, all tasks (Earth Engine without a login window), then a commit
  of only the published files (panel, its data, W3b tests, blog notebook) and a push to `main`. Log in
  `data/logs/` on the data drive.
- Windows setup in one PowerShell command (`scripts/windows/setup_workspace.ps1`): Git, Google Drive and Miniforge,
  a `GeoWorldLook` folder on the desktop (`projects/`, `data/` linked to Google Drive, `scripts/`), the conda
  environment (`environment.yml`), logins, and a Task Scheduler job every Monday at 07:30. Guide:
  `docs/URUCHOMIENIE_LOKALNE.md`.
- Fix: the panel task message no longer uses a relative path (it failed on Windows when code and data are on
  different drives).

## 1.0.0 — 2026-10-20

First product version: an English panel for 15 vineyards near Condom (Gers) and its JSON data, with every number
labelled by the kind of check behind it.

### Code
- New Python package `agriscreen/` replaces the `step_*.py` modules (last commit with them: `2b8df9d`). Functions
  were moved without changes to their logic. Module map: `docs/ARCHITEKTURA.md` §6.
- Regression check: the same synthetic inputs as the old self-test, run through the old and the new code, give
  identical outputs in 26 files (parcel statistics, anomalies and flags; W3b, W3c and W3d tests and stores; soil,
  reference and weather validation; panel data). The only differences are intended: the experiment rows in the trust
  table now read “experimental, not shown”, and the panel data no longer carry the experiment layers.
- `python -m agriscreen.selftest`: one offline end-to-end test (synthetic data, all tasks, unit tests of each module).
- `pyproject.toml` (dependencies, ruff rules), `requirements.txt`.
- Notebooks are generated by `notebooks/build_monitor.py` and `notebooks/build_story.py`. The Colab notebook is now
  `notebooks/AgriScreen_Monitor.ipynb` (no GPU needed).

### Product
- The panel is the product (`panel.html` + `panel_data.json`). Removed: the Polish dashboard and bulletin, the
  EDO-style 10-day status, SEN2SR super-resolution (same validation result as 10 m), the Sentinel-1 branch.
- W3c (zones vs usual) and W3d (lowest in five years) are an experimental module, off by default
  (`run_all(..., experiments=True)`). The panel shows only their test results.
- “How far to trust it” has a status legend. Statuses follow the protocols: `checked` for comparisons without a pass
  threshold (soil, rainfall), `descriptive` for T1 and T2, `confirmed` / `not confirmed` only for tests with a
  criterion. Lusignan's correlation is labelled as 35-day anomalies.
- Clearer wording: the z-score note says that about one scene in six is below −1 by construction; drought classes
  are “US Drought Monitor percentile thresholds on the ERA5-Land percentile”, not the USDM product; z next to the
  ±1 boundary is shown with two decimals.
- With the Sentinel-2 background selected, Esri tiles are removed from the map (no requests, no Esri attribution).
- `panel_data.json` has an `explore` section: share of scenes below normal by soil state on the scene day, computed
  after the tests (exploratory, not shown in the panel; used by the blog notebook).

### Results (audit before 1.0)
- An independent recomputation from the output files confirmed T1, T2, T3, the 4-band test, W3c Z2 and W3d D1.
- Fixed to match the registered protocols: W3c and W3d count “normal soil” as percentile in (30, 70), as the
  water card does (the first run used [30, 70]). W3d does not change; W3c Z2 changes from 15.4% to 15.3% (NDVI),
  decision unchanged.
- Results notes corrected where the text said more than the data: T1 without a hand-picked list of drought years,
  W3d with 4 years (not 6) and 12 vineyards, no “does not exaggerate”, the §9 leakage step described as several
  changes at once, RPG replanting codes listed in full. Details in the “Audyt” sections of
  `docs/evidence/W3b_wyniki.md`, `W3c_wyniki.md` and `W3d_wyniki.md`.
