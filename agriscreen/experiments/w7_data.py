"""
W7 (protokół docs/evidence/W7_protokol_wskazowki.md, D-093) — pobieranie danych pomiarowych ICOS.

Zasada: zapisujemy oryginalne archiwa ZIP bez zmian i dla każdego pliku wiersz w MANIFEST_W7.csv
(stacja, produkt, identyfikator obiektu, nazwa, adres, data pobrania, SHA-256, rozmiar, licencja).
Odczyt kolumn prosto z archiwum (bez rozpakowywania na Dysk).
"""

from __future__ import annotations

import csv
import hashlib
import io
import os
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd

ICOS_SPARQL = "https://meta.icos-cp.eu/sparql"
ICOS_OBJECTS = "https://data.icos-cp.eu/objects/"
LICENCE = "CC BY 4.0 (ICOS data licence)"

# Reguła protokołu §0: wszystkie stacje ekosystemowe ICOS we Francji z produktem „ETC L2 Fluxnet (half-hourly)”
# (stan 2026-11-01). Typ ekosystemu i położenie wieży z metadanych ICOS (meta.icos-cp.eu), pobierane przy starcie.
STATIONS = ("FR-Aur", "FR-Bil", "FR-Fon", "FR-Gri", "FR-Hes", "FR-Lam", "FR-Lus", "FR-Mej", "FR-Pue", "FR-Tou")
CROPLAND = "Croplands"
SPECS = ("ETC L2 ARCHIVE", "ETC L2 Fluxnet (half-hourly)")
MANIFEST_COLS = ["station", "spec", "object_id", "file_name", "url", "downloaded_utc", "sha256", "bytes", "licence"]


def _post(query: str, session: Any = None, timeout: int = 300) -> List[Dict[str, Any]]:
    import requests
    r = (session or requests).post(ICOS_SPARQL, data={"query": query}, headers={"Accept": "application/json"},
                                   timeout=timeout)
    if r.status_code != 200:
        raise RuntimeError(f"ICOS SPARQL: HTTP {r.status_code}: {r.text[:200]}")
    return r.json()["results"]["bindings"]


def station_meta(session: Any = None) -> pd.DataFrame:
    """Nazwa, typ ekosystemu i położenie wieży (pełna precyzja) dla STATIONS."""
    vals = " ".join(f'"{s}"' for s in STATIONS)
    q = f"""prefix cpmeta: <http://meta.icos-cp.eu/ontologies/cpmeta/>
prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>
select ?id ?name ?eco ?lat ?lon where {{
  VALUES ?id {{ {vals} }}
  ?st cpmeta:hasStationId ?id ; cpmeta:hasName ?name ; cpmeta:hasLatitude ?lat ; cpmeta:hasLongitude ?lon .
  OPTIONAL {{ ?st cpmeta:hasEcosystemType ?e . ?e rdfs:label ?eco }} }}"""
    rows = [{"station": b["id"]["value"], "name": b["name"]["value"], "ecosystem": b.get("eco", {}).get("value", ""),
             "lat": float(b["lat"]["value"]), "lon": float(b["lon"]["value"])} for b in _post(q, session)]
    df = pd.DataFrame(rows).sort_values("station").reset_index(drop=True)
    df["vegetation_test"] = df["ecosystem"] != CROPLAND        # §0: uprawy polowe poza testem roślinności
    return df


def latest_object(station: str, spec: str, session: Any = None) -> Optional[Dict[str, Any]]:
    """Najnowszy (niezastąpiony) obiekt danego produktu stacji: id, nazwa, okres, rozmiar."""
    q = f"""prefix cpmeta: <http://meta.icos-cp.eu/ontologies/cpmeta/>
prefix prov: <http://www.w3.org/ns/prov#>
prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>
select ?d ?fn ?start ?end ?size where {{
  ?s cpmeta:hasStationId "{station}" . ?a prov:wasAssociatedWith ?s ; prov:startedAtTime ?start ; prov:endedAtTime ?end .
  ?d cpmeta:wasAcquiredBy ?a ; cpmeta:hasObjectSpec ?sp ; cpmeta:hasName ?fn ; cpmeta:hasSizeInBytes ?size .
  ?sp rdfs:label "{spec}" . FILTER NOT EXISTS {{ [] cpmeta:isNextVersionOf ?d }} }} order by desc(?end) limit 1"""
    b = _post(q, session)
    if not b:
        return None
    b = b[0]
    return {"station": station, "spec": spec, "id": b["d"]["value"].rsplit("/", 1)[-1], "name": b["fn"]["value"],
            "start": b["start"]["value"][:10], "end": b["end"]["value"][:10], "bytes": int(b["size"]["value"])}


def fetch(obj: Dict[str, Any], dest_dir: str, manifest: str, session: Any = None) -> str:
    """Archiwum ZIP obiektu do dest_dir (bez zmian, z akceptacją licencji CC BY 4.0) i wiersz w MANIFEST.
    Gdy plik już jest i jego SHA-256 zgadza się z manifestem, nie pobieramy ponownie."""
    import requests
    os.makedirs(dest_dir, exist_ok=True)
    path = os.path.join(dest_dir, obj["name"])
    done = read_manifest(manifest)
    row = done[(done["object_id"] == obj["id"])] if len(done) else done
    if os.path.exists(path) and len(row) and sha256(path) == row["sha256"].iat[-1]:
        return path
    r = (session or requests).get(ICOS_OBJECTS + obj["id"], cookies={"CpLicenseAcceptedFor": obj["id"]}, timeout=1800)
    if r.status_code != 200 or r.content[:2] != b"PK":
        raise RuntimeError(f"ICOS: pobranie {obj['name']} nieudane (HTTP {r.status_code})")
    with open(path, "wb") as f:
        f.write(r.content)
    new = {"station": obj["station"], "spec": obj["spec"], "object_id": obj["id"], "file_name": obj["name"],
           "url": ICOS_OBJECTS + obj["id"], "downloaded_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "sha256": sha256(path), "bytes": os.path.getsize(path), "licence": LICENCE}
    exists = os.path.exists(manifest)
    with open(manifest, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=MANIFEST_COLS)
        if not exists:
            w.writeheader()
        w.writerow(new)
    return path


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_manifest(manifest: str) -> pd.DataFrame:
    return pd.read_csv(manifest, dtype=str) if os.path.exists(manifest) else pd.DataFrame(columns=MANIFEST_COLS)


def zip_members(path: str) -> List[str]:
    with zipfile.ZipFile(path) as z:
        return z.namelist()


SQUARES_M = {1: 300, 2: 200, 3: 500}     # fid → bok kwadratu [m]; 300 m = protokół §3, 200 i 500 m = §6 (opisowo)
SQUARE_TYPE = "w7_kwadrat"


def utm_epsg(lon: float, lat: float) -> int:
    """Strefa UTM wieży (jak ingest.load_aoi_geometry): 326xx na półkuli północnej."""
    return 32600 + int((lon + 180) // 6) + 1 if lat >= 0 else 32700 + int((lon + 180) // 6) + 1


def write_squares(station: str, lat: float, lon: float, dest_dir: str) -> Dict[str, Any]:
    """Kwadraty o środku w wieży (boki SQUARES_M) w strefie UTM wieży, zapis GeoJSON WGS84: działki i zasięg (500 m)."""
    import geopandas as gpd
    from shapely.geometry import Point, box
    os.makedirs(dest_dir, exist_ok=True)
    epsg = utm_epsg(lon, lat)
    c = gpd.GeoSeries([Point(lon, lat)], crs=4326).to_crs(epsg).iloc[0]
    rows = [{"fid": fid, "Typ": SQUARE_TYPE, "side_m": side, "station": station,
             "geometry": box(c.x - side / 2, c.y - side / 2, c.x + side / 2, c.y + side / 2)}
            for fid, side in SQUARES_M.items()]
    g = gpd.GeoDataFrame(rows, crs=epsg).to_crs(4326)
    squares = os.path.join(dest_dir, f"{station}_kwadraty.geojson")
    aoi = os.path.join(dest_dir, f"{station}_zasieg.geojson")
    g.to_file(squares, driver="GeoJSON")
    g[g["fid"] == 3].to_file(aoi, driver="GeoJSON")
    return {"squares": squares, "aoi": aoi, "epsg": epsg}


def station_config(code_dir: str, station: str, lat: float, lon: float, root: str) -> Dict[str, Any]:
    """CONFIG produktu bez zmian metody; podmienione tylko: działki (kwadraty), zasięg, strefa UTM, katalog danych.
    AOI_BUFFER_M 100 m: zasięg pobierania wokół kwadratu 500 m (nie zmienia pikseli w kwadratach)."""
    from agriscreen.config import make_config
    sdir = os.path.join(root, station)
    sq = write_squares(station, lat, lon, sdir)
    return make_config(code_dir, {"PARCELS_PATH": sq["squares"], "AOI_PATH": sq["aoi"], "AOI_BUFFER_M": 100,
                                  "PARCEL_TYPE": SQUARE_TYPE, "EPSG": sq["epsg"]}, data_dir=sdir)


def run_s2_station(code_dir: str, station: str, lat: float, lon: float, root: str) -> Dict[str, Any]:
    """Sentinel-2 i statystyki kwadratów tymi samymi zadaniami co winnice (task_ingest_s2, task_parcel_stats)."""
    from agriscreen import pipeline
    from agriscreen.runtime import setup_runtime
    cfg = station_config(code_dir, station, lat, lon, root)
    rt = setup_runtime(code_dir, pull=False, install=False, init_gee=True, data_dir=cfg["DATA_ROOT"], allow_auth=False)
    a = pipeline.task_ingest_s2(rt, cfg)
    b = pipeline.task_parcel_stats(rt, cfg)
    return {"station": station, "ingest": a.get("message"), "stats": b.get("message")}


def run_era5_station(station: str, lat: float, lon: float, root: str, start: str = "1991-01-01",
                     end: Optional[str] = None) -> str:
    """ERA5-Land dobowe w punkcie wieży (ta sama funkcja co produkt: ingest.sync_era5_land_point); zapis CSV."""
    from agriscreen import ingest
    end = end or pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d")
    df = ingest.sync_era5_land_point(lat, lon, start, end, os.path.join(root, "era5_cache", station))
    path = os.path.join(root, f"{station}_era5_land_daily.csv")
    df.to_csv(path, index=False)
    return path


def douane_gers(douane_dir: str) -> pd.DataFrame:
    """Oficjalny rejestr (deklaracje celne): departament 32 Gers, kolumna 2 = powierzchnia winnic w produkcji [ha],
    kolumna 20 = produkcja całkowita [hl] (układ identyczny w plikach 2016–2025). Plon = produkcja / powierzchnia."""
    import glob
    import warnings
    rows = []
    for p in sorted(glob.glob(os.path.join(douane_dir, "douane_releve_departement_*.xls*"))):
        year = int(os.path.splitext(os.path.basename(p))[0].rsplit("_", 1)[-1])
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            df = pd.read_excel(p, sheet_name=0, header=None)
        hit = df[df.iloc[:, 0].astype(str).str.match(r"^\s*32\s+GERS", case=False)]
        if len(hit) != 1:
            raise ValueError(f"{os.path.basename(p)}: {len(hit)} wierszy Gers")
        r = hit.iloc[0]
        rows.append({"year": year, "declarations": int(r.iloc[1]), "area_ha": float(r.iloc[2]),
                     "total_hl": float(r.iloc[20])})
    out = pd.DataFrame(rows).sort_values("year").reset_index(drop=True)
    out["yield_hl_ha"] = out["total_hl"] / out["area_ha"]
    return out


def read_member(path: str, pattern: str, usecols: Optional[List[str]] = None, **kw) -> pd.DataFrame:
    """CSV z archiwum: pierwszy plik, którego nazwa zawiera `pattern` (wielkość liter bez znaczenia)."""
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist() if pattern.lower() in n.lower() and n.lower().endswith(".csv")]
        if not names:
            raise FileNotFoundError(f"{os.path.basename(path)}: brak pliku z „{pattern}”")
        with z.open(names[0]) as f:
            data = io.BytesIO(f.read())
    if usecols is not None:
        cols = pd.read_csv(data, nrows=0).columns
        data.seek(0)
        usecols = [c for c in usecols if c in cols]
    return pd.read_csv(data, usecols=usecols, na_values=[-9999, "-9999", -9999.0], **kw)
