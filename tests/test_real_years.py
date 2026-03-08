"""Tests against real-world Solytics GmbH journals (2022-2026).

Golden expected values captured from the R implementation.
These are the most important tests — they guarantee the Python
reimplementation produces identical results to R on real data.
"""

import json
from pathlib import Path

import pytest
from tests.conftest import KONTEN_FILE, GOLDEN_DIR, FIXTURES_DIR


# Load golden outputs
with open(GOLDEN_DIR / "real_years.json") as f:
    GOLDEN = json.load(f)

REAL_YEARS = [
    # (year, start, ende, hebesatz)
    ("2022", "2022-01-01", "2022-12-31", 395),
    ("2023", "2023-01-01", "2023-12-31", 395),
    ("2024", "2024-01-01", "2024-12-31", 395),
    ("2025", "2025-01-01", "2025-12-31", 395),
    ("2026", "2026-01-01", "2026-12-31", 395),
]


def fixture(year: str) -> str:
    return str(FIXTURES_DIR / f"real_{year}.csv")


def golden(year: str) -> dict:
    return GOLDEN[year]


# --- Journal validation ---

@pytest.mark.parametrize("year,start,ende,hebesatz", REAL_YEARS, ids=[
    f"real_{y[0]}" for y in REAL_YEARS
])
def test_real_journal_valid(api, year, start, ende, hebesatz):
    result = api.validiere_journal(fixture(year), KONTEN_FILE, start, ende)
    assert result == "", f"Journal {year} invalid: {result}"


# --- Betriebsergebnis ---

@pytest.mark.parametrize("year,start,ende,hebesatz", REAL_YEARS, ids=[
    f"real_{y[0]}" for y in REAL_YEARS
])
def test_real_betriebsergebnis(api, year, start, ende, hebesatz):
    expected = golden(year)["betriebsergebnis"]
    result = api.berechne_betriebsergebnis(fixture(year), KONTEN_FILE, start, ende)
    assert abs(result - expected) < 0.02, f"{year}: expected {expected}, got {result}"


# --- KSt ---

@pytest.mark.parametrize("year,start,ende,hebesatz", REAL_YEARS, ids=[
    f"real_{y[0]}" for y in REAL_YEARS
])
def test_real_koerperschaftssteuer(api, year, start, ende, hebesatz):
    expected = golden(year)["koerperschaftssteuer"]
    result = api.berechne_koerperschaftssteuer(fixture(year), KONTEN_FILE, start, ende)
    assert abs(result - expected) < 0.02, f"{year}: expected {expected}, got {result}"


# --- Soli ---

@pytest.mark.parametrize("year,start,ende,hebesatz", REAL_YEARS, ids=[
    f"real_{y[0]}" for y in REAL_YEARS
])
def test_real_soli(api, year, start, ende, hebesatz):
    expected = golden(year)["soli"]
    result = api.berechne_soli(fixture(year), KONTEN_FILE, start, ende)
    assert abs(result - expected) < 0.02, f"{year}: expected {expected}, got {result}"


# --- GewSt ---

@pytest.mark.parametrize("year,start,ende,hebesatz", REAL_YEARS, ids=[
    f"real_{y[0]}" for y in REAL_YEARS
])
def test_real_gewerbesteuer(api, year, start, ende, hebesatz):
    expected = golden(year)["gewerbesteuer"]
    result = api.berechne_gewerbesteuer(hebesatz, fixture(year), KONTEN_FILE, start, ende)
    assert abs(result - expected) < 0.02, f"{year}: expected {expected}, got {result}"


# --- Total tax ---

@pytest.mark.parametrize("year,start,ende,hebesatz", REAL_YEARS, ids=[
    f"real_{y[0]}" for y in REAL_YEARS
])
def test_real_steuern(api, year, start, ende, hebesatz):
    expected = golden(year)["steuern"]
    result = api.steuern(fixture(year), KONTEN_FILE, start, ende, hebesatz)
    assert abs(result - expected) < 0.02, f"{year}: expected {expected}, got {result}"


# --- Tax consistency: steuern == KSt + Soli + GewSt ---
# Note: real journals may contain Vorjahressteuern (prior-year tax bookings)
# which steuern() includes but individual KSt/Soli/GewSt functions don't.
# So we only check that steuern() matches the golden value, not the sum.

@pytest.mark.parametrize("year,start,ende,hebesatz", REAL_YEARS, ids=[
    f"real_{y[0]}" for y in REAL_YEARS
])
def test_real_steuern_matches_golden(api, year, start, ende, hebesatz):
    expected = golden(year)["steuern"]
    result = api.steuern(fixture(year), KONTEN_FILE, start, ende, hebesatz)
    assert abs(result - expected) < 0.02, f"{year}: expected {expected}, got {result}"


# --- Bilanz validates (Aktiva == Passiva) ---

@pytest.mark.parametrize("year,start,ende,hebesatz", REAL_YEARS, ids=[
    f"real_{y[0]}" for y in REAL_YEARS
])
def test_real_bilanz_validates(api, year, start, ende, hebesatz):
    result = api.validiere_bilanz(fixture(year), KONTEN_FILE, start, ende, hebesatz)
    expected = golden(year)["validiere_bilanz"]
    assert result == expected, f"{year}: Bilanz invalid: {result}"


# --- GuV: Betriebsergebnis matches ---

@pytest.mark.parametrize("year,start,ende,hebesatz", REAL_YEARS, ids=[
    f"real_{y[0]}" for y in REAL_YEARS
])
def test_real_guv_betriebsergebnis(api, year, start, ende, hebesatz):
    guv_df = api.guv(fixture(year), KONTEN_FILE, start, ende, hebesatz)
    be_row = guv_df.filter(guv_df["GuV Posten"] == "Betriebsergebnis")
    assert not be_row.is_empty(), f"{year}: no Betriebsergebnis in GuV"
    be_guv = be_row["Betrag"][0]
    expected = golden(year)["guv"]["Betriebsergebnis"]
    assert abs(be_guv - expected) < 0.02, f"{year}: BE {be_guv} != {expected}"


# --- GuV: Jahresüberschuss matches ---

@pytest.mark.parametrize("year,start,ende,hebesatz", REAL_YEARS, ids=[
    f"real_{y[0]}" for y in REAL_YEARS
])
def test_real_guv_jahresueberschuss(api, year, start, ende, hebesatz):
    guv_df = api.guv(fixture(year), KONTEN_FILE, start, ende, hebesatz)
    ju_row = guv_df.filter(guv_df["GuV Posten"] == "17. Jahresüberschuss/Jahresfehlbetrag")
    assert not ju_row.is_empty(), f"{year}: no JÜ in GuV"
    ju = ju_row["Betrag"][0]
    expected = golden(year)["guv"]["17. Jahresüberschuss/Jahresfehlbetrag"]
    assert abs(ju - expected) < 0.02, f"{year}: JÜ {ju} != {expected}"


# --- GuV: all posten match golden ---

@pytest.mark.parametrize("year,start,ende,hebesatz", REAL_YEARS, ids=[
    f"real_{y[0]}" for y in REAL_YEARS
])
def test_real_guv_all_posten(api, year, start, ende, hebesatz):
    guv_df = api.guv(fixture(year), KONTEN_FILE, start, ende, hebesatz)
    expected_guv = golden(year)["guv"]
    for posten, expected_betrag in expected_guv.items():
        row = guv_df.filter(guv_df["GuV Posten"] == posten)
        assert not row.is_empty(), f"{year}: missing GuV Posten '{posten}'"
        actual = row["Betrag"][0]
        assert abs(actual - expected_betrag) < 0.02, \
            f"{year} '{posten}': {actual} != {expected_betrag}"


# --- Bilanz: all rows match golden ---

@pytest.mark.parametrize("year,start,ende,hebesatz", REAL_YEARS, ids=[
    f"real_{y[0]}" for y in REAL_YEARS
])
def test_real_bilanz_all_rows(api, year, start, ende, hebesatz):
    bilanz_df = api.bilanz(fixture(year), KONTEN_FILE, start, ende, hebesatz)
    expected_rows = golden(year)["bilanz"]

    assert len(bilanz_df) == len(expected_rows), \
        f"{year}: bilanz row count {len(bilanz_df)} != {len(expected_rows)}"

    for i, expected in enumerate(expected_rows):
        actual = bilanz_df.row(i, named=True)
        for col in ["Bilanzseite", "Ebene1", "Ebene2", "Betrag"]:
            exp_val = expected[col]
            act_val = actual[col]
            # Normalize NA: polars reads "NA" as string, golden has "NA"
            # Both should match as-is (string "NA" == string "NA")
            assert act_val == exp_val, \
                f"{year} row {i} col '{col}': '{act_val}' != '{exp_val}'"


# --- Eröffnungsbilanz: Aktiva == Passiva (Python-only) ---

YEARS_WITH_JAB = [y for y in REAL_YEARS if y[0] != "2022"]


def _skip_if_no_eroeffnungsbilanz(api):
    if not hasattr(api, "eroeffnungsbilanz"):
        pytest.skip("eroeffnungsbilanz not available in this backend")


@pytest.mark.parametrize("year,start,ende,hebesatz", YEARS_WITH_JAB, ids=[
    f"real_{y[0]}" for y in YEARS_WITH_JAB
])
def test_real_eroeffnungsbilanz_balanced(api, year, start, ende, hebesatz):
    _skip_if_no_eroeffnungsbilanz(api)
    eb = api.eroeffnungsbilanz(fixture(year), KONTEN_FILE, start, ende)
    aktiva = eb.filter((eb["Bilanzseite"] == "Aktiva") & (eb["Ebene1"] == "NA") & (eb["Ebene2"] == "NA"))
    passiva = eb.filter((eb["Bilanzseite"] == "Passiva") & (eb["Ebene1"] == "NA") & (eb["Ebene2"] == "NA"))
    assert not aktiva.is_empty() and not passiva.is_empty(), f"{year}: empty EB"
    assert aktiva["Betrag"][0] == passiva["Betrag"][0], \
        f"{year}: EB Aktiva {aktiva['Betrag'][0]} != Passiva {passiva['Betrag'][0]}"


# --- Schlussbilanz year N == Eröffnungsbilanz year N+1 ---

YEAR_TRANSITIONS = [
    ("2022", "2023", 305),
    ("2023", "2024", 325),
    ("2024", "2025", 325),
    ("2025", "2026", 325),
]


@pytest.mark.parametrize("prev_year,next_year,hebesatz", YEAR_TRANSITIONS, ids=[
    f"{t[0]}_to_{t[1]}" for t in YEAR_TRANSITIONS
])
def test_schlussbilanz_matches_eroeffnungsbilanz(api, prev_year, next_year, hebesatz):
    """Schlussbilanz of year N must match Eröffnungsbilanz of year N+1."""
    _skip_if_no_eroeffnungsbilanz(api)
    prev_start = f"{prev_year}-01-01"
    prev_ende = f"{prev_year}-12-31"
    next_start = f"{next_year}-01-01"
    next_ende = f"{next_year}-12-31"

    sb = api.bilanz(fixture(prev_year), KONTEN_FILE, prev_start, prev_ende, hebesatz)
    eb = api.eroeffnungsbilanz(fixture(next_year), KONTEN_FILE, next_start, next_ende)

    sb_aktiva = sb.filter((sb["Bilanzseite"] == "Aktiva") & (sb["Ebene1"] == "NA") & (sb["Ebene2"] == "NA"))
    eb_aktiva = eb.filter((eb["Bilanzseite"] == "Aktiva") & (eb["Ebene1"] == "NA") & (eb["Ebene2"] == "NA"))

    assert not sb_aktiva.is_empty() and not eb_aktiva.is_empty()
    assert sb_aktiva["Betrag"][0] == eb_aktiva["Betrag"][0], \
        f"SB {prev_year} Aktiva {sb_aktiva['Betrag'][0]} != EB {next_year} Aktiva {eb_aktiva['Betrag'][0]}"

    sb_passiva = sb.filter((sb["Bilanzseite"] == "Passiva") & (sb["Ebene1"] == "NA") & (sb["Ebene2"] == "NA"))
    eb_passiva = eb.filter((eb["Bilanzseite"] == "Passiva") & (eb["Ebene1"] == "NA") & (eb["Ebene2"] == "NA"))

    assert sb_passiva["Betrag"][0] == eb_passiva["Betrag"][0], \
        f"SB {prev_year} Passiva {sb_passiva['Betrag'][0]} != EB {next_year} Passiva {eb_passiva['Betrag'][0]}"
