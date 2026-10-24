"""
Środowisko uruchomienia i rejestr wyników.

- setup_runtime: Colab albo lokalnie — git pull (tylko fast-forward), brakujące pakiety, Google Earth Engine.
- Rejestr: tabele CSV w data/registry/ (na Dysku Google w Colab), zapis według klucza głównego (registry_upsert).
  gwl_observations — statystyki działek ze scen Sentinel-2; gwl_validation_metrics — wyniki walidacji i testów;
  gwl_runs — historia zadań (status, czas, commit kodu, komunikat).
- run_task: uruchamia jedno zadanie, zapisuje jego wynik i błąd w gwl_runs; błąd nie zatrzymuje kolejnych zadań.
"""

from __future__ import annotations

import html
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("agriscreen.runtime")

REGISTRY_SCHEMA: Dict[str, Dict[str, List[str]]] = {
    "gwl_observations": {
        "keys": ["site_id", "product", "variable", "time_utc", "orbit"],
        "columns": ["site_id", "product", "variable", "time_utc", "orbit", "value", "unit", "n_pixels",
                    "qc_flags", "calib_id", "run_id", "ingested_at"],
    },
    "gwl_validation_metrics": {
        # Bez run_id w kluczu: nowa wartość metryki zastępuje wiersz, a run_id wskazuje uruchomienie, które ją policzyło.
        "keys": ["site_id", "product", "reference", "segment", "period", "subset", "metric"],
        "columns": ["site_id", "product", "reference", "segment", "period", "subset", "metric",
                    "value", "ci_low", "ci_high", "n", "date_from", "date_to", "run_id"],
    },
    "gwl_runs": {
        "keys": ["run_id"],
        "columns": ["run_id", "task", "started_at", "finished_at", "duration_s", "status", "git_commit",
                    "pipeline_version", "params_json", "n_new_rows", "message"],
    },
}

# Kolumny techniczne: ich zmiana nie oznacza zmiany danych (wiersz z tą samą wartością nie jest nadpisywany)
_META_COLUMNS = {"run_id", "ingested_at", "updated_at"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _git(project_dir: str, *args: str) -> str:
    try:
        out = subprocess.run(["git", "-C", project_dir, *args], capture_output=True, text=True, timeout=120)
        return (out.stdout or out.stderr).strip()
    except Exception as e:
        return f"git niedostępny ({e})"


def _git_commit(project_dir: str) -> str:
    """Skrót commita + '+dirty', jeśli w repozytorium są niezatwierdzone zmiany w kodzie."""
    if not os.path.exists(os.path.join(project_dir, ".git")):
        return "no-git"
    commit = _git(project_dir, "rev-parse", "--short", "HEAD")
    dirty = _git(project_dir, "status", "--porcelain", "--untracked-files=no")
    return commit + ("+dirty" if dirty else "")


def setup_runtime(
    project_dir: Optional[str] = None,
    gee_project: str = "ee-geoworldlook",
    pull: bool = True,
    install: bool = True,
    init_gee: bool = True,
    data_dir: Optional[str] = None,
    allow_auth: bool = True,
) -> Dict[str, Any]:
    """
    Przygotowuje środowisko (Colab lub lokalnie) i zwraca słownik `rt` przekazywany do zadań.
    Dysk Google montuje komórka notatnika przed importem pakietu (kod leży na Dysku).

    Kroki: git pull (tylko fast-forward) -> instalacja brakujących pakietów (tylko Colab)
    -> inicjalizacja GEE -> katalog rejestru. data_dir: katalog danych, gdy jest inny niż katalog kodu (rejestr
    leży w <data_dir>/data/registry; ten sam katalog podaj do make_config).
    """
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    project_dir = os.path.abspath(project_dir or os.getcwd())
    in_colab = "google.colab" in sys.modules

    if pull and os.path.exists(os.path.join(project_dir, ".git")):
        # lokalne zmiany blokują pull --ff-only; stash je zachowuje (git stash list)
        if _git(project_dir, "status", "--porcelain", "--untracked-files=no"):
            logger.info(f"git stash: {_git(project_dir, 'stash', 'push', '-m', 'colab-autostash')}")
        logger.info(f"git pull: {_git(project_dir, 'pull', '--ff-only')}")

    if install and in_colab:
        import importlib.util
        needed = {"ee": "earthengine-api", "geemap": "geemap", "geedim": "geedim", "rasterio": "rasterio",
                  "geopandas": "geopandas"}            # geedim: pobieranie obrazów przez geemap
        missing = [pkg for mod, pkg in needed.items() if importlib.util.find_spec(mod) is None]
        if missing:
            logger.info(f"Instalacja: {' '.join(missing)}")
            subprocess.run([sys.executable, "-m", "pip", "install", "-q", *missing], check=True)

    if init_gee:
        from agriscreen.ingest import initialize_earth_engine
        initialize_earth_engine(project_id=gee_project, allow_auth=allow_auth)

    data_root = os.path.abspath(data_dir or project_dir)
    rt = {
        "PROJECT_DIR": project_dir,
        "DATA_ROOT": data_root,
        "DATA_DIR": os.path.join(data_root, "data"),
        "REGISTRY_DIR": os.path.join(data_root, "data", "registry"),
        "GEE_PROJECT": gee_project,
        "IN_COLAB": in_colab,
        "GIT_COMMIT": _git_commit(project_dir),
    }
    os.makedirs(rt["REGISTRY_DIR"], exist_ok=True)
    logger.info(f"Środowisko gotowe: {project_dir} (commit {rt['GIT_COMMIT']}, Colab={in_colab})")
    return rt


def _registry_path(rt: Dict[str, Any], table: str) -> str:
    if table not in REGISTRY_SCHEMA:
        raise KeyError(f"Nieznana tabela rejestru: {table}. Dostępne: {sorted(REGISTRY_SCHEMA)}")
    return os.path.join(rt["REGISTRY_DIR"], f"{table}.csv")


def registry_read(rt: Dict[str, Any], table: str) -> pd.DataFrame:
    """Czyta tabelę rejestru; brak pliku = pusta tabela z kolumnami ze schematu."""
    path = _registry_path(rt, table)
    cols = REGISTRY_SCHEMA[table]["columns"]
    if not os.path.exists(path):
        return pd.DataFrame(columns=cols)
    df = pd.read_csv(path, low_memory=False)
    return df.reindex(columns=cols)


def _canon(df: pd.DataFrame) -> pd.DataFrame:
    """Tekstowa postać kanoniczna (porównanie kluczy i wartości niezależne od typu po odczycie CSV)."""
    def one(v: Any) -> str:
        if v is None or v is pd.NA or v is pd.NaT or (isinstance(v, float) and not np.isfinite(v)):
            return ""
        if isinstance(v, (float, np.floating)):
            return str(int(v)) if float(v).is_integer() else f"{float(v):.10g}"
        if isinstance(v, (int, np.integer, bool, np.bool_)):
            return str(int(v))
        if isinstance(v, str):
            return "" if v.lower() == "nan" else v
        return str(v)
    return df.apply(lambda col: col.map(one))


def registry_upsert(rt: Dict[str, Any], table: str, df: pd.DataFrame) -> Dict[str, int]:
    """
    Dopisuje wiersze do tabeli rejestru według klucza głównego:
      - nowy klucz -> wiersz dopisany,
      - istniejący klucz ze zmienioną wartością -> wiersz zastąpiony,
      - istniejący klucz bez zmian -> zostaje stary wiersz (z pierwotnym run_id i ingested_at).
    Zapis atomowy (plik tymczasowy + zamiana). Zwraca liczniki {"new", "changed", "unchanged"}.
    """
    keys = REGISTRY_SCHEMA[table]["keys"]
    cols = REGISTRY_SCHEMA[table]["columns"]
    missing = [k for k in keys if k not in df.columns]
    if missing:
        raise ValueError(f"{table}: brak kolumn klucza {missing}")
    extra = [c for c in df.columns if c not in cols]
    if extra:
        logger.warning(f"{table}: kolumny spoza schematu pominięte: {extra}")
    new = df.reindex(columns=cols)
    new_c = _canon(new)
    new_key = new_c[keys].agg("\x1f".join, axis=1)
    dup = new_key.duplicated(keep="last")
    if dup.any():
        logger.warning(f"{table}: {int(dup.sum())} zduplikowanych kluczy w nowych danych — zostaje ostatni.")
        new, new_c, new_key = new[~dup.values], new_c[~dup.values], new_key[~dup.values]

    old = registry_read(rt, table)
    old_c = _canon(old)
    old_key = old_c[keys].agg("\x1f".join, axis=1) if len(old) else pd.Series([], dtype=str)

    in_old = new_key.isin(set(old_key))
    value_cols = [c for c in cols if c not in keys and c not in _META_COLUMNS]
    changed_keys = set()
    if in_old.any():
        a = new_c[in_old.values].set_index(new_key[in_old].to_numpy())[value_cols]
        b = old_c.set_index(old_key.to_numpy())[value_cols].loc[a.index]
        changed_keys = set(a.index[(a != b).any(axis=1).values])

    write_mask = (~in_old.values) | new_key.isin(changed_keys).values
    keep_old = ~old_key.isin(changed_keys).values if len(old) else np.array([], bool)
    out = pd.concat([old[keep_old], new[write_mask]], ignore_index=True)
    out_key = _canon(out[keys]).agg("\x1f".join, axis=1) if len(out) else pd.Series([], dtype=str)
    out = out.iloc[np.argsort(out_key.to_numpy(), kind="stable")]

    path = _registry_path(rt, table)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    out.to_csv(tmp, index=False)
    os.replace(tmp, path)
    counts = {"new": int((~in_old).sum()), "changed": len(changed_keys),
              "unchanged": int(in_old.sum()) - len(changed_keys)}
    logger.info(f"Rejestr {table}: +{counts['new']} nowych, {counts['changed']} zmienionych, "
                f"{counts['unchanged']} bez zmian (razem {len(out)}).")
    return counts


def _short_repr(v: Any, limit: int = 300) -> str:
    s = repr(v)
    return s if len(s) <= limit else s[:limit] + "..."


def run_task(
    rt: Dict[str, Any],
    name: str,
    fn: Callable[..., Any],
    *args: Any,
    raise_errors: bool = False,
    **kwargs: Any,
) -> Any:
    """
    Uruchamia jedno zadanie i zapisuje je w gwl_runs.

    Kontrakt zadania: fn(*args, **kwargs) może zwrócić słownik z kluczami:
      "registry": {tabela: DataFrame} -> wiersze trafiają do rejestru (z run_id tego uruchomienia),
      "skipped": True                 -> zadanie nie miało nic do zrobienia (status "skipped"),
      "pipeline_version": str         -> wersja modułu zapisana w gwl_runs.
    Błąd nie przerywa "Uruchom wszystko" (chyba że raise_errors=True): jest zapisany w gwl_runs i wypisany.
    """
    started = _utc_now()
    run_id = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}_{name}"
    t0 = time.time()
    status, message, n_new, result, error = "ok", "", 0, None, None
    logger.info(f"=== ZADANIE {name} (run_id={run_id}) ===")
    try:
        result = fn(*args, **kwargs)
        if isinstance(result, dict):
            message = str(result.get("message", ""))       # komunikat zadania widać w wydruku i w gwl_runs
            if result.get("skipped"):
                status = "skipped"
            parts = []
            for table, df in (result.get("registry") or {}).items():
                df = df.copy()
                if "run_id" in REGISTRY_SCHEMA[table]["columns"]:
                    df["run_id"] = run_id
                c = registry_upsert(rt, table, df)
                n_new += c["new"]
                parts.append(f"{table}: +{c['new']}/~{c['changed']}")
            if parts:
                message = (message + "; " if message else "") + ", ".join(parts)
    except Exception as e:
        status, message, error = "error", f"{type(e).__name__}: {e}", e
        logger.exception(f"Zadanie {name} zakończone błędem")

    params = {"args": [_short_repr(a) for a in args], "kwargs": {k: _short_repr(v) for k, v in kwargs.items()}}
    run_row = pd.DataFrame([{
        "run_id": run_id, "task": name, "started_at": started, "finished_at": _utc_now(),
        "duration_s": round(time.time() - t0, 1), "status": status, "git_commit": rt.get("GIT_COMMIT", ""),
        "pipeline_version": result.get("pipeline_version", "") if isinstance(result, dict) else "",
        "params_json": json.dumps(params, ensure_ascii=False), "n_new_rows": n_new, "message": message[:2000],
    }])
    registry_upsert(rt, "gwl_runs", run_row)
    print(f"[{status.upper()}] {name} ({run_row['duration_s'].iat[0]} s) {message}")
    if error is not None and raise_errors:
        raise error
    return result


def run_history(rt: Dict[str, Any], n: int = 20) -> pd.DataFrame:
    """Ostatnie uruchomienia (najnowsze na górze)."""
    runs = registry_read(rt, "gwl_runs")
    cols = ["run_id", "task", "status", "duration_s", "n_new_rows", "git_commit", "message"]
    return runs.sort_values("started_at", ascending=False).head(n)[cols].reset_index(drop=True)


def registry_summary(rt: Dict[str, Any]) -> pd.DataFrame:
    """Liczba wierszy i rozmiar każdej tabeli rejestru."""
    rows = []
    for table in REGISTRY_SCHEMA:
        path = _registry_path(rt, table)
        exists = os.path.exists(path)
        rows.append({"table": table, "rows": len(registry_read(rt, table)) if exists else 0,
                     "size_kb": round(os.path.getsize(path) / 1024, 1) if exists else 0.0})
    return pd.DataFrame(rows)


def show_html(path: str, height: int = 3400):
    """Wyświetla stronę HTML (panel) w komórce Colab / Jupyter. Ramka dopasowuje wysokość do strony po załadowaniu
    (onload); `height` to wysokość startowa, gdy przeglądarka nie pozwala odczytać treści ramki."""
    from IPython.display import HTML, display
    fit = "try{this.style.height=(this.contentDocument.documentElement.scrollHeight+20)+'px'}catch(e){}"
    display(HTML(f'<iframe srcdoc="{html.escape(open(path, encoding="utf-8").read())}" onload="{fit}" '
                 f'style="width:100%;height:{height}px;border:0"></iframe>'))
