"""
Polecenia AgriScreen z wiersza poleceń (komputer lokalny, bez Colab):

    python -m agriscreen run        [--data-dir DIR] [--no-ingest] [--experiments]   wszystkie zadania
    python -m agriscreen publish    [--data-dir DIR]                                 panel i notatnik na GitHub
    python -m agriscreen weekly     [--no-pull] [--no-ingest] [--no-publish]         przebieg tygodniowy (harmonogram)
    python -m agriscreen selftest   [--out DIR]                                      test bez sieci
    python -m agriscreen settings                                                    pokaż ustawienia

Katalog danych: --data-dir, zmienna AGRISCREEN_DATA_DIR albo local_settings.json (agriscreen/local.py).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m agriscreen", description="AgriScreen: polecenia lokalne")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("run", "publish", "weekly", "settings"):
        p = sub.add_parser(name)
        p.add_argument("--data-dir", default=None, help="katalog danych (np. Dysk Google ...\\GeoWorldLook\\agriwatch)")
        if name in ("run", "weekly"):
            p.add_argument("--no-ingest", action="store_true", help="bez pobierania danych (tylko dane z dysku)")
        if name == "run":
            p.add_argument("--experiments", action="store_true", help="także eksperymenty W3c i W3d")
        if name == "weekly":
            p.add_argument("--no-pull", action="store_true", help="bez git pull")
            p.add_argument("--no-publish", action="store_true", help="bez commit i push")
    p = sub.add_parser("selftest")
    p.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    for noisy in ("matplotlib", "PIL", "urllib3", "googleapiclient", "rasterio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    if a.cmd == "selftest":
        from agriscreen import selftest
        selftest.main(a.out or selftest.os.path.join(selftest.PROJECT_DIR, "data", "_selftest"))
        return 0
    from agriscreen import local
    s = local.load_settings(data_dir=a.data_dir)
    if a.cmd == "settings":
        print(json.dumps(dict(s, code_dir=local.CODE_DIR), ensure_ascii=False, indent=1))
        return 0
    if a.cmd == "run":
        res = local.run(s, ingest_data=not a.no_ingest, experiments=a.experiments or None)
        bad = [k for k, v in res["results"].items() if not isinstance(v, dict)]
        print(f"Zadania z błędem: {', '.join(bad) or 'brak'}; wyniki: {res['cfg']['OUTPUT_DIR']}")
        return 1 if bad else 0
    if a.cmd == "publish":
        from agriscreen.config import make_config
        print(local.publish(make_config(local.CODE_DIR, data_dir=s["data_dir"]), s))
        return 0
    if a.cmd == "weekly":
        summ = local.weekly(s, ingest_data=not a.no_ingest, do_publish=not a.no_publish, pull=not a.no_pull)
        print(json.dumps(summ, ensure_ascii=False, indent=1))
        return 0 if "restarted" not in summ else int(summ["restarted"])
    return 2


if __name__ == "__main__":
    sys.exit(main())
