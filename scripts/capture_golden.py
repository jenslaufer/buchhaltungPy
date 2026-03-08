"""Capture golden outputs from R for real-world journals."""

import json
import os
import sys
sys.path.insert(0, ".")

from pathlib import Path
from adapters import r_adapter
from tests.conftest import KONTEN_FILE

PROJECT_ROOT = Path(__file__).parent.parent.resolve()

REAL_YEARS = {
    "2022": {"start": "2022-01-01", "ende": "2022-12-31", "hebesatz": 395},
    "2023": {"start": "2023-01-01", "ende": "2023-12-31", "hebesatz": 395},
    "2024": {"start": "2024-01-01", "ende": "2024-12-31", "hebesatz": 395},
    "2025": {"start": "2025-01-01", "ende": "2025-12-31", "hebesatz": 395},
    "2026": {"start": "2026-01-01", "ende": "2026-12-31", "hebesatz": 395},
}

golden = {}

for year, params in REAL_YEARS.items():
    print(f"Capturing {year}...")
    fixture = str(PROJECT_ROOT / f"tests/fixtures/real_{year}.csv")
    s, e, h = params["start"], params["ende"], params["hebesatz"]

    try:
        be = r_adapter.berechne_betriebsergebnis(fixture, KONTEN_FILE, s, e)
        kst = r_adapter.berechne_koerperschaftssteuer(fixture, KONTEN_FILE, s, e)
        soli = r_adapter.berechne_soli(fixture, KONTEN_FILE, s, e)
        gwst = r_adapter.berechne_gewerbesteuer(h, fixture, KONTEN_FILE, s, e)
        total_tax = r_adapter.steuern(fixture, KONTEN_FILE, s, e, h)
        validation = r_adapter.validiere_journal(fixture, KONTEN_FILE, s, e)
        bilanz_valid = r_adapter.validiere_bilanz(fixture, KONTEN_FILE, s, e, h)

        # GuV
        guv_df = r_adapter.guv(fixture, KONTEN_FILE, s, e, h)
        guv_dict = {row["GuV Posten"]: row["Betrag"] for row in guv_df.to_dicts()}

        # Bilanz
        bilanz_df = r_adapter.bilanz(fixture, KONTEN_FILE, s, e, h)
        bilanz_dict = bilanz_df.to_dicts()

        golden[year] = {
            "betriebsergebnis": be,
            "koerperschaftssteuer": kst,
            "soli": soli,
            "gewerbesteuer": gwst,
            "steuern": total_tax,
            "validiere_journal": validation,
            "validiere_bilanz": bilanz_valid,
            "guv": guv_dict,
            "bilanz": bilanz_dict,
        }
        print(f"  BE={be}, KSt={kst}, Soli={soli}, GewSt={gwst}, Tax={total_tax}")
        print(f"  Journal valid: '{validation}', Bilanz valid: '{bilanz_valid}'")
    except Exception as ex:
        print(f"  ERROR: {ex}")
        golden[year] = {"error": str(ex)}

with open("tests/golden/real_years.json", "w") as f:
    json.dump(golden, f, indent=2, ensure_ascii=False)

print(f"\nGolden outputs saved to tests/golden/real_years.json")
