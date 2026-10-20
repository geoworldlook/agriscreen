"""
================================================================================
AgriWatch - KROK 12: PANEL „AGRISCREEN” DO PUBLIKACJI (15 WINNIC, EN)
================================================================================
Jeden samodzielny plik HTML (bez zewnętrznych bibliotek i kafli mapy): mapa 15 winnic w SVG kolorowana wybraną warstwą
(woda w roślinności SWIR, NDVI, NDRE, NDMI, CRSWIR) w wybranym dniu sceny, karta „My vineyard” wybranej winnicy
(zdania ze step_09.parcel_card_lines, ta sama logika co dashboard), przebieg sezonu na tle pozostałych winnic, wilgotność
gleby ERA5-Land i tabela „How far to trust it” z wynikami walidacji (W2 + REF, protokół W3b).
Ten sam plik pokazuje notatnik Colab (show_dashboard) i trafia na blog GeoWorldLook.
Dane: wyniki zadań step_05 w OUTPUT_DIR (parcel_anomalies.csv, parcel_area.csv, parcel_flags.csv, w3b_tests.csv,
era5_daily_anomalies.csv, validation_reference.csv, validation_weather.csv) i plik działek.
================================================================================
"""

from __future__ import annotations

import html
import json
import os
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

LAYERS = (("water", "Vegetation water (SWIR)", 1.0,
           "Mean of NDMI and sign-flipped CRSWIR anomalies: water in the whole parcel's vegetation (vines and inter-rows)"),
          ("ndvi", "Greenness (NDVI)", 1.0, "Green leaf cover of vines and inter-rows"),
          ("ndre", "Chlorophyll (NDRE)", 1.0, "Red-edge index, leaf greenness"),
          ("ndmi", "NDMI (SWIR/NIR)", 1.0, "Short-wave infrared moisture index"),
          ("crswir", "CRSWIR (sign flipped)", -1.0, "Continuum-removed SWIR; sign flipped so that lower = less water"))


def _opt(path: str, **kw) -> Optional[pd.DataFrame]:
    return pd.read_csv(path, **kw) if os.path.exists(path) and os.path.getsize(path) > 1 else None


def _r(x: Any, nd: int = 2) -> Optional[float]:
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return round(x, nd) if np.isfinite(x) else None


def _parcel_shapes(cfg: Dict[str, Any], sites: List[str]) -> Dict[str, Any]:
    """Obrysy winnic jako ścieżki SVG (rzut równoodległościowy z cos(φ), skala wspólna dla wszystkich działek)."""
    import geopandas as gpd
    p = gpd.read_file(cfg["PARCELS_PATH"]).to_crs(4326)
    p = p[p["Typ"] == cfg["PARCEL_TYPE"]].copy()
    p["site_id"] = [f"VINEYARD_{int(f):02d}" for f in p["fid"]]
    p = p[p["site_id"].isin(sites) | (len(sites) == 0)]
    x0, y0, x1, y1 = p.total_bounds
    k = np.cos(np.radians((y0 + y1) / 2))
    w, h = (x1 - x0) * k, (y1 - y0)
    scale = 1000.0 / max(w, h)
    pad = 20

    def xy(lon, lat):
        return pad + (lon - x0) * k * scale, pad + (y1 - lat) * scale
    shapes = []
    for r in p.itertuples():
        polys = list(r.geometry.geoms) if r.geometry.geom_type == "MultiPolygon" else [r.geometry]
        d = ""
        for poly in polys:
            pts = [xy(lon, lat) for lon, lat in poly.exterior.coords]
            d += "M" + "L".join(f"{a:.1f},{b:.1f}" for a, b in pts) + "Z"
        c = r.geometry.representative_point()
        cx, cy = xy(c.x, c.y)
        area = float(gpd.GeoSeries([r.geometry], crs=4326).to_crs(cfg["EPSG"]).area.iloc[0] / 1e4)
        shapes.append({"id": r.site_id, "fid": int(r.fid), "d": d, "cx": round(cx, 1), "cy": round(cy, 1),
                       "area_ha": round(area, 2)})
    return {"shapes": sorted(shapes, key=lambda s: s["fid"]), "width": round(pad * 2 + w * scale),
            "height": round(pad * 2 + h * scale)}


def panel_data(out_dir: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Dane panelu z plików wynikowych: warstwy z dla 15 winnic w dniach scen, karty (EN), gleba, walidacja."""
    import step_09_panels as s9
    import step_11_parcel as s11
    pa = pd.read_csv(os.path.join(out_dir, "parcel_anomalies.csv"), parse_dates=["time"])
    pa["day"] = pa["time"].dt.normalize()
    tests = _opt(os.path.join(out_dir, "w3b_tests.csv"))
    summ = s11.tests_summary(tests)
    area = _opt(os.path.join(out_dir, "parcel_area.csv"))
    flags = _opt(os.path.join(out_dir, "parcel_flags.csv"))
    sites = sorted(pa["site_id"].unique())
    qc = pa.groupby("site_id")["qc_ok"].first().map(lambda v: str(v).strip().lower() in ("true", "1"))
    npx = pd.to_numeric(pa["n_pixels"], errors="coerce").groupby(pa["site_id"]).max()

    water = pa[(pa["index"] == "water") & pa["z"].notna()]
    first = water["day"].min()
    days = sorted(pa.loc[pa["z"].notna() & (pa["day"] >= first), "day"].unique())
    dix = {pd.Timestamp(d): i for i, d in enumerate(days)}
    layers = {}
    for key, _, sign, _ in LAYERS:
        sub = pa[(pa["index"] == key) & pa["z"].notna()]
        layers[key] = {}
        for sid, g in sub.groupby("site_id"):
            arr: List[Optional[float]] = [None] * len(days)
            for d, z in zip(g["day"], g["z"]):
                i = dix.get(pd.Timestamp(d))
                if i is not None:
                    arr[i] = _r(sign * z)
            layers[key][sid] = arr

    # gleba: percentyl ERA5-Land 0–100 cm wobec 1991–2020 (ta sama definicja co karta wody)
    soil_pct = pd.Series(dtype=float)
    e = _opt(os.path.join(out_dir, "era5_daily_anomalies.csv"), header=[0, 1], index_col=0, parse_dates=True)
    if e is not None and ("ERA5L_SM_RZ", "percentile") in e:
        soil_pct = e[("ERA5L_SM_RZ", "percentile")].dropna()
        soil_pct = soil_pct[soil_pct.index >= pd.Timestamp(first).replace(month=1, day=1)]
    last = pd.Timestamp(days[-1]) if days else pd.Timestamp.now().normalize()
    soil = None
    if len(soil_pct):
        sd = soil_pct[soil_pct.index <= last + pd.Timedelta(days=1)]
        if len(sd):
            p = float(sd.iat[-1])
            code, label, _ = s9.water_category(p, cfg)
            soil = {"soil_class": s9._swi_class(p, cfg), "percentile": p, "category": {"code": code, "label": label},
                    "date": sd.index[-1], "clim_ref": (str(cfg["CLIM_REF"][0])[:4], str(cfg["CLIM_REF"][1])[:4])}

    cards = {}
    for sid in sites:
        card = s9.parcel_card(pa, area, flags, summ, soil, cfg, sid, today=last)
        lines = s9.parcel_card_lines(card, "en")
        cards[sid] = {"sentences": lines["sentences"], "notes": lines["notes"], "trust": lines["trust"],
                      "detail": lines["detail"], "fixed": lines["fixed"], "state": card["state"],
                      "date": card["date"].strftime("%Y-%m-%d") if card["date"] is not None else None}

    return {"generated": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d"), "last_scene": last.strftime("%Y-%m-%d"),
            "freeze": (summ or {}).get("freeze", ""), "protocol": ((summ or {}).get("protocol_sha256") or "")[:12],
            "map": _parcel_shapes(cfg, sites),
            "sites": {sid: {"qc_ok": bool(qc.get(sid, False)), "n_pixels": _r(npx.get(sid), 0)} for sid in sites},
            "dates": [pd.Timestamp(d).strftime("%Y-%m-%d") for d in days],
            "layers": layers, "layer_info": [{"key": k, "label": lab, "about": about} for k, lab, _, about in LAYERS],
            "soil": {"dates": [d.strftime("%Y-%m-%d") for d in soil_pct.index],
                     "pct": [int(round(v)) for v in soil_pct.to_numpy()]},
            "cards": cards, "trust": trust_rows(out_dir, cfg, summ, tests),
            "main_site": cfg.get("MAIN_SITE", "VINEYARD_06")}


def trust_rows(out_dir: str, cfg: Dict[str, Any], summ: Optional[Dict[str, Any]],
               tests: Optional[pd.DataFrame]) -> List[Dict[str, str]]:
    """Tabela „How far to trust it”: co, wynik, status (validated / partly / not confirmed / not validated)."""
    import step_09_panels as s9
    rows: List[Dict[str, str]] = []

    def f(x, nd=2):
        return "—" if x is None or not np.isfinite(float(x)) else f"{float(x):.{nd}f}"
    ref = _opt(os.path.join(out_dir, "validation_reference.csv"))
    if ref is not None:
        for prod, what in (("ERA5L_SM_RZ", "Soil moisture 0–100 cm (ERA5-Land model, ~9 km)"),
                           (f"SWI_v4_T{int(cfg.get('SWI_T', 15)):03d}", "Soil water index (ASCAT satellite, ~10 km)")):
            parts, agree = [], []
            for site, reference, seg, _, name in s9.REF_TRUST_SITES:
                q = ref[(ref["site_id"] == site) & (ref["reference"] == reference) & (ref["product"] == prod)]
                r = q[(q["segment"] == seg) & (q["metric"] == "pearson_r")]
                a = q[(q["segment"] == "class_agreement") & (q["metric"] == "agreement")]
                if len(r):
                    parts.append(f"{name.split(' (')[0]} R {f(r['value'].iat[0])}")
                if len(a):
                    agree.append(f"{100 * a['value'].iat[0]:.0f}%")
            if parts:
                rows.append({"what": what, "against": "in situ soil sensors at 3 stations (ISMN Condom, ICOS Auradé "
                                                      "and Lusignan)",
                             "result": "; ".join(parts) + (f"; same dry/normal/wet class on {', '.join(agree)} of days"
                                                           if agree else ""),
                             "status": "validated"})
    wv = _opt(os.path.join(out_dir, "validation_weather.csv"))
    if wv is not None:
        q = wv[(wv["product"] == "ERA5L_PRECIP") & (wv["segment"] == "sum_30d") & (wv["period"].astype(str) == "all")
               & (wv["metric"] == "pearson_r")]
        if len(q):
            rows.append({"what": "Rainfall, 30-day sums (ERA5-Land)", "against": f"rain gauge {q['subset'].iat[0]}",
                         "result": f"R {f(q['value'].iat[0])}", "status": "validated"})
    if summ:
        t2 = summ["mdc"]
        g5, g13 = (t2.get("G5") or {}).get("value"), (t2.get("G13") or {}).get("value")
        rows.append({"what": "Parcel vegetation water index: noise between scenes",
                     "against": "pairs of scenes a few days apart without rain",
                     "result": f"smallest clear change: {f(g5, 1)} z (same orbit), {f(g13, 1)} z (different orbits)",
                     "status": "validated"})
        t1 = summ["t1"]
        normal = None
        if tests is not None:
            q = tests[tests["subset"].astype(str).str.startswith("gleba w normie")]
            normal = q["value"].iat[0] if len(q) else None
        rows.append({"what": "Parcel index: how often “below its own normal” appears",
                     "against": "all scenes June–September, 13 vineyards (expected 16%, 1 in 6)",
                     "result": f"{100 * t1['value']:.0f}% [{100 * t1['lo']:.0f}–{100 * t1['hi']:.0f}%], mostly in dry "
                               f"years" + (f"; {100 * normal:.0f}% when soil is near normal" if normal is not None else ""),
                     "status": "validated"})
        t3 = summ["t3"]
        rows.append({"what": "Area vegetation follows soil water of the previous 30 days",
                     "against": "ISMN sensor at Condom, June–September 2018–2024 (pre-registered test)",
                     "result": f"ρ {f(t3['value'])} [{f(t3['lo'])}; {f(t3['hi'])}]; mostly between years, not within "
                               f"a season", "status": "confirmed" if t3.get("passed") else "not confirmed"})
        d = summ["p7"].get("delta") or {}
        rows.append({"what": "4-band model (red, red-edge, NIR, SWIR) instead of the simple index",
                     "against": "same test, years unseen by the model",
                     "result": f"no gain: Δρ {f(d.get('value'))} [{f(d.get('lo'))}; {f(d.get('hi'))}]",
                     "status": "accepted" if summ["p7"].get("accepted") else "not adopted"})
    rows.append({"what": "Vine water stress", "against": "no measurements inside the vineyards",
                 "result": "not assessed; the index sees the whole parcel, vines and inter-rows", "status": "not validated"})
    return rows


_CSS = """
/* Layout: control bar, then map + card side by side, season charts, evidence table. Earth/leaf palette. */
:root{--bg:#f3f5f0;--panel:#ffffff;--ink:#1d2621;--muted:#5d6a62;--line:#d9dfd6;--accent:#466b35;
--wb:#7a4a0e;--b:#c08a3e;--n:#e9e6dc;--a:#5fa69b;--wa:#1f6a62;--nd:#f0f0ec;--focus:#2d5fa8;
--ok:#2f7a45;--warn:#a26b00;--bad:#9b3b2e;--soil:#8a6a3d;
--display:"Literata",Georgia,"Times New Roman",serif;--body:"Public Sans",system-ui,-apple-system,"Segoe UI",sans-serif;
--mono:"IBM Plex Mono",ui-monospace,Menlo,Consolas,monospace}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#141a16;--panel:#1c241f;--ink:#e6ece6;
--muted:#9aa89f;--line:#2f3a33;--accent:#9cc47f;--wb:#d39a4f;--b:#a8773a;--n:#3a3f37;--a:#3f8c81;--wa:#7fd1c4;
--nd:#232a25;--focus:#8ab4ff;--ok:#7cc48f;--warn:#e0b45a;--bad:#e08a7c;--soil:#c9a46b;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#141a16;--panel:#1c241f;--ink:#e6ece6;--muted:#9aa89f;--line:#2f3a33;--accent:#9cc47f;
--wb:#d39a4f;--b:#a8773a;--n:#3a3f37;--a:#3f8c81;--wa:#7fd1c4;--nd:#232a25;--focus:#8ab4ff;--ok:#7cc48f;
--warn:#e0b45a;--bad:#e08a7c;--soil:#c9a46b;color-scheme:dark}
body{background:var(--bg);color:var(--ink);font-family:var(--body);font-size:15px;line-height:1.5;margin:0}
.wrap{max-width:1180px;margin:0 auto;padding-block:20px 40px;padding-left:max(16px,env(safe-area-inset-left,0px));
padding-right:max(16px,env(safe-area-inset-right,0px));display:grid;gap:18px}
h1{font-family:var(--display);font-weight:600;font-size:1.9rem;margin:0;text-wrap:balance}
h2{font-family:var(--display);font-weight:600;font-size:1.2rem;margin:0 0 8px;text-wrap:balance}
.sub{color:var(--muted);max-width:70ch;margin:4px 0 0}
.bar{display:flex;flex-wrap:wrap;gap:10px 16px;align-items:center;background:var(--panel);border:1px solid var(--line);
border-radius:8px;padding:10px 14px}
.bar label{font-size:.78rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);display:flex;gap:8px;
align-items:center}
select,button{font:inherit;color:var(--ink);background:var(--bg);border:1px solid var(--line);border-radius:6px;
padding:5px 9px;cursor:pointer}
input[type=range]{width:min(320px,60vw);accent-color:var(--accent)}
:focus-visible{outline:2px solid var(--focus);outline-offset:2px}
.date{font-family:var(--mono);font-variant-numeric:tabular-nums;font-size:.95rem;min-width:9ch}
.main{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(0,1fr);gap:18px}
@media (max-width:820px){.main{grid-template-columns:1fr}}
.box{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:14px;min-width:0}
svg text{fill:var(--muted);font-family:var(--mono);font-size:11px}
.parcel{stroke:var(--ink);stroke-width:1;cursor:pointer;transition:stroke-width .15s}
.parcel.sel{stroke:var(--focus);stroke-width:7}
.plabel{font-size:26px;font-weight:500;fill:var(--ink);paint-order:stroke;stroke:var(--panel);stroke-width:5px;stroke-linejoin:round}
.parcel.small{stroke-dasharray:4 3}
.legend{display:flex;flex-wrap:wrap;gap:6px 12px;font-size:.8rem;color:var(--muted);margin-top:8px}
.sw{display:inline-block;width:12px;height:12px;border-radius:2px;border:1px solid var(--line);vertical-align:-2px;margin-right:4px}
.status{font-size:.92rem;margin-top:6px}
.card h2 .ha{font-family:var(--mono);font-size:.85rem;color:var(--muted);font-weight:400}
.card ol{padding-left:20px;margin:8px 0;display:grid;gap:6px}
.chip{display:inline-block;font-size:.72rem;letter-spacing:.05em;text-transform:uppercase;padding:2px 8px;
border-radius:10px;border:1px solid currentColor}
.notes{color:var(--warn);font-size:.88rem;margin:6px 0;padding-left:18px}
.small{color:var(--muted);font-size:.82rem}
.charts{display:grid;gap:4px}
.tbl{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:.88rem}
th,td{text-align:left;padding:7px 8px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);font-weight:600}
.st-validated,.st-confirmed,.st-accepted{color:var(--ok)}.st-not-confirmed,.st-not-adopted{color:var(--warn)}
.st-not-validated{color:var(--bad)}
footer{color:var(--muted);font-size:.82rem;max-width:90ch}
footer a,.sub a{color:var(--accent)}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
"""

_JS = r"""
const D = JSON.parse(document.getElementById('panel-data').textContent);
const $ = id => document.getElementById(id);
const fmt = d => new Date(d + 'T00:00:00Z').toLocaleDateString('en-GB', {day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC'});
const cls = z => z == null ? 'nd' : z <= -1.5 ? 'wb' : z <= -1 ? 'b' : z < 1 ? 'n' : z < 1.5 ? 'a' : 'wa';
const CLS_TXT = {wb: 'well below its normal', b: 'below its normal', n: 'within its normal', a: 'above its normal',
                 wa: 'well above its normal', nd: 'no clear scene'};
const color = c => `var(--${c})`;
const esc = t => String(t).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
let S = {layer: 'water', di: D.dates.length - 1, site: D.main_site};
const sel = $('layer');
D.layer_info.forEach(l => { const o = document.createElement('option'); o.value = l.key; o.textContent = l.label; sel.appendChild(o); });
const rng = $('day'); rng.max = D.dates.length - 1;

// map
const svg = $('map'); svg.setAttribute('viewBox', `0 0 ${D.map.width} ${D.map.height}`);
const NS = 'http://www.w3.org/2000/svg';
D.map.shapes.forEach(s => {
  const p = document.createElementNS(NS, 'path'); p.setAttribute('d', s.d); p.setAttribute('class', 'parcel');
  p.setAttribute('id', 'p-' + s.id); p.setAttribute('tabindex', '0'); p.setAttribute('role', 'button');
  if (!D.sites[s.id] || !D.sites[s.id].qc_ok) p.classList.add('small');
  const t = document.createElementNS(NS, 'title'); p.appendChild(t);
  p.addEventListener('click', () => { S.site = s.id; draw(); });
  p.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { S.site = s.id; draw(); e.preventDefault(); } });
  svg.appendChild(p);
  const tx = document.createElementNS(NS, 'text'); tx.setAttribute('x', s.cx); tx.setAttribute('y', s.cy);
  tx.setAttribute('text-anchor', 'middle'); tx.setAttribute('dominant-baseline', 'middle'); tx.setAttribute('pointer-events', 'none');
  tx.setAttribute('class', 'plabel');
  tx.textContent = String(s.fid).padStart(2, '0'); svg.appendChild(tx);
});
const shape = id => D.map.shapes.find(s => s.id === id);
const val = (site, i) => ((D.layers[S.layer] || {})[site] || [])[i] ?? null;
const qcSites = () => Object.keys(D.sites).filter(s => D.sites[s].qc_ok);
function median(a) { a = a.filter(v => v != null).sort((x, y) => x - y); if (!a.length) return null;
  const m = a.length >> 1; return a.length % 2 ? a[m] : (a[m - 1] + a[m]) / 2; }

function chart(el, pts, med, year, opt) {
  // pts: [{d, v}] for the vineyard; med: [{d, v}] others' median; x = day of season (1 Apr–31 Oct)
  const W = 720, H = opt.h, L = 38, R = 10, T = 10, B = 22;
  const t0 = Date.UTC(year, 3, 1), t1 = Date.UTC(year, 9, 31);
  const X = d => L + (Date.parse(d + 'T00:00:00Z') - t0) / (t1 - t0) * (W - L - R);
  const Y = v => T + (opt.max - Math.max(opt.min, Math.min(opt.max, v))) / (opt.max - opt.min) * (H - T - B);
  let s = `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="${opt.label}">`;
  (opt.bands || []).forEach(b => s += `<rect x="${L}" width="${W - L - R}" y="${Y(b[1])}" height="${Y(b[0]) - Y(b[1])}" fill="${b[2]}" opacity="0.18"/>`);
  opt.ticks.forEach(v => s += `<line x1="${L}" x2="${W - R}" y1="${Y(v)}" y2="${Y(v)}" stroke="var(--line)" ${v === 0 ? '' : 'stroke-dasharray="3 3"'}/><text x="${L - 6}" y="${Y(v) + 4}" text-anchor="end">${v}</text>`);
  ['Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct'].forEach((m, i) => { const d = `${year}-${String(i + 4).padStart(2, '0')}-01`;
    s += `<text x="${X(d)}" y="${H - 6}">${m}</text>`; });
  if (opt.marker) s += `<line x1="${X(opt.marker)}" x2="${X(opt.marker)}" y1="${T}" y2="${H - B}" stroke="var(--focus)" stroke-width="1.5"/>`;
  if (med && med.length) s += `<polyline fill="none" stroke="var(--muted)" stroke-width="1.5" points="${med.map(p => `${X(p.d).toFixed(1)},${Y(p.v).toFixed(1)}`).join(' ')}"/>`;
  if (opt.line) s += `<polyline fill="none" stroke="${opt.line}" stroke-width="2" points="${pts.map(p => `${X(p.d).toFixed(1)},${Y(p.v).toFixed(1)}`).join(' ')}"/>`;
  else pts.forEach(p => s += `<circle cx="${X(p.d).toFixed(1)}" cy="${Y(p.v).toFixed(1)}" r="4" fill="${color(cls(p.v))}" stroke="var(--ink)" stroke-width=".6"><title>${fmt(p.d)}: z ${p.v.toFixed(1)}</title></circle>`);
  return el.innerHTML = s + '</svg>';
}

function draw() {
  const i = S.di, day = D.dates[i], year = +day.slice(0, 4);
  $('dlabel').textContent = fmt(day); rng.value = i; sel.value = S.layer;
  const info = D.layer_info.find(l => l.key === S.layer);
  $('about').textContent = info.about;
  let n = 0, below = 0;
  D.map.shapes.forEach(s => {
    const z = val(s.id, i), c = cls(z), p = $('p-' + s.id), qc = D.sites[s.id] && D.sites[s.id].qc_ok;
    p.style.fill = qc ? color(c) : 'var(--nd)';
    p.classList.toggle('sel', s.id === S.site);
    p.firstChild.textContent = `Vineyard ${String(s.fid).padStart(2, '0')} · ${s.area_ha} ha · ` +
      (qc ? (z == null ? 'no clear scene' : `z ${z.toFixed(1)}, ${CLS_TXT[c]}`) : 'too small for a reliable anomaly');
    if (qc && z != null) { n++; if (z <= -1) below++; }
  });
  $('status').textContent = n ? `${fmt(day)}: ${below} of ${n} vineyards below their own normal (${info.label}).` : `${fmt(day)}: no clear scene for this layer.`;
  // card
  const sh = shape(S.site), C = D.cards[S.site] || {sentences: [], notes: [], trust: [], fixed: [], detail: ''};
  $('cname').innerHTML = `Vineyard ${String(sh.fid).padStart(2, '0')} <span class="ha">${sh.area_ha} ha</span>`;
  const z = val(S.site, i), qc = D.sites[S.site] && D.sites[S.site].qc_ok;
  $('cnow').innerHTML = qc ? (z == null ? `${fmt(day)}: no clear scene.` :
     `${fmt(day)} · ${info.label}: <span class="chip" style="color:${color(cls(z))}">${CLS_TXT[cls(z)]}</span> z ${z.toFixed(1)}`) :
     'Too small for a reliable anomaly (fewer than 40 pixels after removing the 20 m edge strip).';
  $('clatest').textContent = C.date ? `Latest scene ${fmt(C.date)}` : 'Latest scene';
  $('csent').innerHTML = C.sentences.map(t => `<li>${esc(t)}</li>`).join('');
  $('cnotes').innerHTML = C.notes.map(t => `<li>${esc(t)}</li>`).join(''); $('cnotes').hidden = !C.notes.length;
  $('cfixed').textContent = C.fixed.join(' ');
  $('cdetail').textContent = C.detail || '';
  // season chart
  const yi = D.dates.map((d, k) => [d, k]).filter(([d]) => +d.slice(0, 4) === year);
  const pts = yi.map(([d, k]) => ({d, v: val(S.site, k)})).filter(p => p.v != null);
  const others = qcSites().filter(s => s !== S.site);
  const med = yi.map(([d, k]) => ({d, v: median(others.map(s => val(s, k)))})).filter(p => p.v != null);
  $('stitle').textContent = `${year} season · ${info.label}: vineyard ${String(sh.fid).padStart(2, '0')} (dots) and the median of the other vineyards (grey line)`;
  chart($('season'), pts, med, year, {h: 230, min: -3, max: 3, ticks: [-2, -1, 0, 1, 2], marker: day, label: 'season chart',
    bands: [[-3, -1, 'var(--b)'], [1, 3, 'var(--a)']]});
  const sp = D.soil.dates.map((d, k) => ({d, v: D.soil.pct[k]}))
    .filter(p => +p.d.slice(0, 4) === year && +p.d.slice(5, 7) >= 4 && +p.d.slice(5, 7) <= 10);
  $('soiltitle').textContent = `${year} · soil moisture 0–100 cm in the area (ERA5-Land percentile vs 1991–2020; ≤ 30 dry, ≥ 70 wet)`;
  chart($('soil'), sp, null, year, {h: 150, min: 0, max: 100, ticks: [0, 30, 70, 100], marker: day, line: 'var(--soil)',
    label: 'soil moisture chart', bands: [[0, 30, 'var(--b)'], [70, 100, 'var(--a)']]});
  try { localStorage.setItem('agriscreen', JSON.stringify({layer: S.layer, site: S.site})); } catch (e) {}
}
try { const m = JSON.parse(localStorage.getItem('agriscreen') || '{}'); if (m.layer) S.layer = m.layer; if (m.site && D.cards[m.site]) S.site = m.site; } catch (e) {}
sel.addEventListener('change', () => { S.layer = sel.value; draw(); });
rng.addEventListener('input', () => { S.di = +rng.value; draw(); });
$('prev').addEventListener('click', () => { S.di = Math.max(0, S.di - 1); draw(); });
$('next').addEventListener('click', () => { S.di = Math.min(D.dates.length - 1, S.di + 1); draw(); });
$('latest').addEventListener('click', () => { S.di = D.dates.length - 1; draw(); });
// trust table
$('trust').innerHTML = D.trust.map(r => `<tr><td>${esc(r.what)}</td><td>${esc(r.against)}</td><td>${esc(r.result)}</td><td class="st-${r.status.replace(/ /g, '-')}">${esc(r.status)}</td></tr>`).join('');
draw();
"""


def panel_html(data: Dict[str, Any], standalone: bool = True) -> str:
    """Strona panelu. standalone=True: pełny dokument (Colab, blog); False: bez szkieletu (podgląd Artifact)."""
    esc = html.escape
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"), default=str).replace("</", "<\\/")
    legend = "".join(f'<span><span class="sw" style="background:var(--{c})"></span>{t}</span>' for c, t in (
        ("wb", "≤ −1.5"), ("b", "−1.5 to −1 (below normal)"), ("n", "within normal"), ("a", "+1 to +1.5"), ("wa", "≥ +1.5"),
        ("nd", "no clear scene or parcel too small")))
    body = f"""<title>AgriScreen Vineyard Panel</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Literata:opsz,wght@7..72,600&family=Public+Sans:wght@400;600&display=swap">
<style>{_CSS}</style>
<div class="wrap">
<header>
<h1>AgriScreen · vineyards near Condom, Gers</h1>
<p class="sub">How each of 15 vineyards compares with its own recent history (the previous five years, same time of
year), from Sentinel-2 satellite images. Soil moisture comes from the ERA5-Land model for the area. Last scene
{esc(fmt_date(data['last_scene']))}. Tests were registered before computing (protocol {esc(data['protocol'])}…,
frozen {esc(data['freeze'])}).</p>
</header>
<div class="bar" role="group" aria-label="Map controls">
<label for="layer">Layer <select id="layer"></select></label>
<label for="day">Scene <input id="day" type="range" min="0" step="1"></label>
<span class="date" id="dlabel"></span>
<button id="prev" type="button" aria-label="Previous scene">◀</button>
<button id="next" type="button" aria-label="Next scene">▶</button>
<button id="latest" type="button">Latest</button>
</div>
<div class="main">
<section class="box" aria-labelledby="maph">
<h2 id="maph">Vineyards against their own normal</h2>
<svg id="map" width="100%" role="img" aria-label="Map of 15 vineyards coloured by anomaly"></svg>
<div class="legend">{legend}</div>
<p class="status" id="status"></p>
<p class="small" id="about"></p>
<p class="small">Click a vineyard to open its card. Dashed outline: parcel too small after removing a 20 m edge strip.
Values are z-scores against the same parcel in the previous five years.</p>
</section>
<section class="box card" aria-labelledby="cname">
<h2 id="cname"></h2>
<p id="cnow"></p>
<div class="small" id="clatest"></div>
<ol id="csent"></ol>
<ul class="notes" id="cnotes"></ul>
<p class="small" id="cfixed"></p>
<p class="small" id="cdetail"></p>
</section>
</div>
<section class="box charts" aria-labelledby="stitle">
<h2>Season</h2>
<p class="small" id="stitle"></p>
<div id="season"></div>
<p class="small" id="soiltitle"></p>
<div id="soil"></div>
</section>
<section class="box" aria-labelledby="trusth">
<h2 id="trusth">How far to trust it</h2>
<div class="tbl"><table><thead><tr><th>What</th><th>Checked against</th><th>Result</th><th>Status</th></tr></thead>
<tbody id="trust"></tbody></table></div>
</section>
<footer>Data: Copernicus Sentinel-2 L2A, ERA5-Land and CLMS Soil Water Index; reference sensors ISMN (SMOSMANIA
Condom) and ICOS (Auradé, Lusignan); rain gauges Météo-France. The vegetation index sees the whole parcel (vines,
inter-rows and soil), so it is not a diagnosis of vine water stress and gives no irrigation advice. Method, protocol and
code: <a href="https://github.com/geoworldlook/agriscreen" rel="noopener">github.com/geoworldlook/agriscreen</a>.
Generated {esc(data['generated'])}.</footer>
</div>
<script type="application/json" id="panel-data">{payload}</script>
<script>{_JS}</script>"""
    if not standalone:
        return body
    return (f'<!doctype html>\n<html lang="en"><head><meta charset="utf-8">\n<meta name="viewport" '
            f'content="width=device-width, initial-scale=1, viewport-fit=cover">\n</head><body>\n{body}\n</body></html>')


def fmt_date(d: str) -> str:
    return pd.Timestamp(d).strftime("%-d %B %Y") if d else ""


def build_panel(out_dir: str, cfg: Dict[str, Any], path: Optional[str] = None, standalone: bool = True) -> str:
    """Zapisuje panel (panel.html w OUTPUT_DIR) i dane (panel_data.json) — te same dane czyta notatnik na blog."""
    data = panel_data(out_dir, cfg)
    path = path or os.path.join(out_dir, "panel.html")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(panel_html(data, standalone))
    with open(os.path.join(os.path.dirname(path), "panel_data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"), default=str)
    return path
