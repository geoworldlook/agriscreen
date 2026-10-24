"""
Uruchamianie na własnym komputerze (Windows, macOS, Linux) bez Colab: ustawienia lokalne, przebieg tygodniowy
i publikacja panelu na GitHub.

Układ: kod w klonie repozytorium (np. C:\\Users\\...\\agriscreen), dane w katalogu danych — zwykle zsynchronizowany
Dysk Google (np. G:\\Mój dysk\\GeoWorldLook\\agriwatch) z tym samym układem `data/...` co w Colab, więc Colab dalej
działa jako zapas. Klucze: <katalog danych>\\..\\secrets (jak w Colab).

Ustawienia: plik `local_settings.json` w katalogu kodu (poza git), np.
    {"data_dir": "G:\\\\Mój dysk\\\\GeoWorldLook\\\\agriwatch", "gee_project": "ee-geoworldlook",
     "branch": "main", "publish": true, "experiments": false}

Przebieg tygodniowy (`python -m agriscreen weekly`):
  1. blokada (drugi przebieg w tym samym czasie kończy się od razu),
  2. git pull --ff-only (kod z GitHub; pominięte przy lokalnych zmianach w plikach śledzonych),
  3. wszystkie zadania (pipeline.run_all), Earth Engine bez okna logowania,
  4. gdy panel powstał: kopia do docs/showcase, notatnik na blog, commit wyłącznie tych plików i push na `branch`.
Log: <katalog danych>/data/logs/weekly_<data>.log.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import os
import runpy
import shutil
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("agriscreen.local")

CODE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTINGS_FILE = "local_settings.json"
DEFAULTS: Dict[str, Any] = {"data_dir": None, "gee_project": "ee-geoworldlook", "branch": "main", "publish": True,
                            "experiments": False, "remote": "origin"}
# Pliki publikowane po przebiegu: (plik w OUTPUT_DIR, plik w repozytorium)
PUBLISH = (("panel.html", "docs/showcase/agriscreen_panel.html"),
           ("panel_data.json", "docs/showcase/agriscreen_data.json"),
           ("w3b_tests.csv", "docs/showcase/w3b_tests.csv"))
PUBLISH_EXPERIMENTS = (("w3c_tests.csv", "docs/showcase/w3c_tests.csv"),
                       ("w3d_tests.csv", "docs/showcase/w3d_tests.csv"))
STORY = "notebooks/AgriScreen_story.ipynb"
LOCK_MAX_HOURS = 12


def load_settings(code_dir: str = CODE_DIR, **overrides: Any) -> Dict[str, Any]:
    """Ustawienia: DEFAULTS ← local_settings.json ← zmienne AGRISCREEN_DATA_DIR / EE_PROJECT ← argumenty."""
    s = dict(DEFAULTS)
    path = os.path.join(code_dir, SETTINGS_FILE)
    if os.path.exists(path):
        with open(path, encoding="utf-8-sig") as f:
            s.update(json.load(f))                 # utf-8-sig: plik zapisany w Windows może mieć BOM
    if os.environ.get("AGRISCREEN_DATA_DIR"):
        s["data_dir"] = os.environ["AGRISCREEN_DATA_DIR"]
    if os.environ.get("EE_PROJECT"):
        s["gee_project"] = os.environ["EE_PROJECT"]
    s.update({k: v for k, v in overrides.items() if v is not None})
    s["data_dir"] = os.path.abspath(s["data_dir"] or code_dir)
    return s


# ==============================================================================
# git
# ==============================================================================

def git(code_dir: str, *args: str, check: bool = True) -> str:
    r = subprocess.run(["git", "-C", code_dir, *args], capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {(r.stderr or r.stdout).strip()}")
    return r.stdout.strip()


def git_pull(code_dir: str, remote: str, branch: str) -> str:
    """Pobiera kod (tylko fast-forward). Przy lokalnych zmianach w plikach śledzonych albo innej gałęzi — pomija."""
    if git(code_dir, "rev-parse", "--abbrev-ref", "HEAD") != branch:
        return f"pominięte: bieżąca gałąź to nie {branch}"
    if git(code_dir, "status", "--porcelain", "--untracked-files=no"):
        return "pominięte: lokalne zmiany w plikach śledzonych (kod zostaje jak jest)"
    for i in range(4):
        try:
            git(code_dir, "pull", "--ff-only", remote, branch)
            return f"kod {git(code_dir, 'rev-parse', '--short', 'HEAD')}"
        except RuntimeError as e:
            if i == 3:
                return f"błąd: {e}"
            time.sleep(2 ** (i + 1))
    return "błąd"


def git_publish(code_dir: str, paths: List[str], message: str, remote: str, branch: str) -> str:
    """Commit wyłącznie podanych plików i push na `branch` (4 próby). Zwraca opis wyniku."""
    if git(code_dir, "rev-parse", "--abbrev-ref", "HEAD") != branch:
        return f"bez publikacji: bieżąca gałąź to nie {branch}"
    git(code_dir, "add", "--", *paths)
    if subprocess.run(["git", "-C", code_dir, "diff", "--cached", "--quiet", "--", *paths]).returncode == 0:
        return "bez zmian do publikacji"
    git(code_dir, "commit", "-m", message, "--", *paths)
    for i in range(4):
        try:
            git(code_dir, "push", remote, f"HEAD:{branch}")
            return f"opublikowano {git(code_dir, 'rev-parse', '--short', 'HEAD')} na {remote}/{branch}"
        except RuntimeError as e:
            if i == 3:
                return f"commit lokalnie, push nieudany: {e}"
            time.sleep(2 ** (i + 1))
    return "push nieudany"


# ==============================================================================
# Przebieg i publikacja
# ==============================================================================

def run(settings: Dict[str, Any], ingest_data: bool = True, experiments: Optional[bool] = None) -> Dict[str, Any]:
    """Wszystkie zadania na danych z katalogu danych. Zwraca wyniki zadań (run_all) i cfg."""
    from agriscreen import pipeline
    from agriscreen.config import make_config
    from agriscreen.runtime import setup_runtime
    try:
        rt = setup_runtime(CODE_DIR, gee_project=settings["gee_project"], pull=False, install=False,
                           init_gee=ingest_data, data_dir=settings["data_dir"], allow_auth=False)
    except Exception as e:                      # bez GEE: liczymy na danych z dysku, pobieranie S2 i ERA5 pominięte
        logger.error(f"Earth Engine niedostępny ({e}); przebieg bez pobierania Sentinel-2 i ERA5-Land")
        rt = setup_runtime(CODE_DIR, pull=False, install=False, init_gee=False, data_dir=settings["data_dir"])
        ingest_data = False
    cfg = make_config(CODE_DIR, data_dir=settings["data_dir"])
    exp = settings["experiments"] if experiments is None else experiments
    results = pipeline.run_all(rt, cfg, ingest_data=ingest_data, experiments=exp)
    if not ingest_data:                          # SWI (Copernicus Data Space) nie zależy od GEE
        from agriscreen.runtime import run_task
        results["ingest_swi"] = run_task(rt, "ingest_swi", pipeline.task_ingest_swi, rt, cfg)
    return {"results": results, "cfg": cfg, "rt": rt, "experiments": exp}


def publish(cfg: Dict[str, Any], settings: Dict[str, Any], experiments: bool = False,
            message: Optional[str] = None) -> str:
    """Kopiuje panel i testy do docs/showcase, odświeża notatnik na blog i publikuje je na GitHub."""
    out = cfg["OUTPUT_DIR"]
    if not os.path.exists(os.path.join(out, "panel.html")):
        return "bez publikacji: brak panel.html"
    paths = []
    for src, dst in PUBLISH + (PUBLISH_EXPERIMENTS if experiments else ()):
        p = os.path.join(out, src)
        if os.path.exists(p):
            shutil.copyfile(p, os.path.join(CODE_DIR, dst))
            paths.append(dst)
    try:                                        # notatnik na blog czyta docs/showcase
        runpy.run_path(os.path.join(CODE_DIR, "notebooks", "build_story.py"), run_name="__main__")
        paths.append(STORY)
    except Exception as e:
        logger.warning(f"Notatnik na blog nie powstał ({type(e).__name__}: {e}); publikuję sam panel")
    data = json.load(open(os.path.join(out, "panel_data.json"), encoding="utf-8"))
    msg = message or (f"auto: przebieg tygodniowy {dt.date.today():%Y-%m-%d} (ostatnia scena {data.get('last_scene')})")
    if not settings.get("publish", True):
        return f"publikacja wyłączona w ustawieniach; pliki skopiowane: {', '.join(paths)}"
    return git_publish(CODE_DIR, paths, msg, settings["remote"], settings["branch"])


class Lock:
    """Blokada w katalogu danych: drugi przebieg w tym samym czasie (np. Colab i komputer) kończy się od razu."""

    def __init__(self, data_dir: str):
        self.path = os.path.join(data_dir, "data", "registry", ".agriscreen.lock")

    def __enter__(self) -> "Lock":
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        if os.path.exists(self.path) and time.time() - os.path.getmtime(self.path) < LOCK_MAX_HOURS * 3600:
            raise RuntimeError(f"inny przebieg trwa (blokada {self.path}); usuń plik, jeśli to pozostałość")
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(f"{os.getpid()} {dt.datetime.now():%Y-%m-%d %H:%M}\n")
        return self

    def __exit__(self, *exc: Any) -> None:
        try:
            os.remove(self.path)
        except OSError:
            pass


def _log_to_file(data_dir: str) -> str:
    d = os.path.join(data_dir, "data", "logs")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, f"weekly_{dt.datetime.now():%Y%m%d_%H%M}.log")
    h = logging.FileHandler(path, encoding="utf-8")
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.getLogger().addHandler(h)
    logging.getLogger().setLevel(logging.INFO)
    return path


def weekly(settings: Dict[str, Any], ingest_data: bool = True, do_publish: bool = True,
           pull: bool = True) -> Dict[str, Any]:
    """Przebieg tygodniowy: pull → zadania → publikacja. Zwraca podsumowanie (też w logu i last_weekly.json)."""
    log = _log_to_file(settings["data_dir"])
    summary: Dict[str, Any] = {"log": log, "started": f"{dt.datetime.now():%Y-%m-%d %H:%M}"}
    with Lock(settings["data_dir"]):
        if pull:
            try:
                before = git(CODE_DIR, "rev-parse", "HEAD")
                summary["pull"] = git_pull(CODE_DIR, settings["remote"], settings["branch"])
                changed = git(CODE_DIR, "rev-parse", "HEAD") != before
            except Exception as e:
                summary["pull"], changed = f"błąd: {e}", False
            logger.info(f"git pull: {summary['pull']}")
            if changed:                      # nowy kod: liczymy w nowym procesie, nie starymi modułami z pamięci
                args = [sys.executable, "-m", "agriscreen", "weekly", "--no-pull"]
                args += [] if ingest_data else ["--no-ingest"]
                args += [] if do_publish else ["--no-publish"]
                Lock(settings["data_dir"]).__exit__()
                code = subprocess.run(args, cwd=CODE_DIR).returncode
                return {"log": log, "pull": summary["pull"], "restarted": code}
        else:
            summary["pull"] = "pominięte (--no-pull)"
        res = run(settings, ingest_data=ingest_data)
        status = {k: ("ok" if isinstance(v, dict) and not v.get("skipped") else "skipped" if isinstance(v, dict)
                      else "error") for k, v in res["results"].items()}
        summary["tasks"] = status
        if do_publish and status.get("panel") == "ok":
            summary["publish"] = publish(res["cfg"], settings, experiments=res["experiments"])
        else:
            summary["publish"] = "bez publikacji" + ("" if do_publish else " (--no-publish)") + \
                                 ("" if status.get("panel") == "ok" else ": panel nie powstał")
    logger.info(f"Podsumowanie: {json.dumps(summary, ensure_ascii=False)}")
    with open(os.path.join(os.path.dirname(log), "last_weekly.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)
    return summary
