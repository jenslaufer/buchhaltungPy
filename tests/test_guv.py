"""Tests for GuV (Gewinn- und Verlustrechnung)."""

import math

import pytest
from tests.conftest import fixture_path, DEFAULT_START, DEFAULT_ENDE, DEFAULT_HEBESATZ


def get_guv_betrag(guv_df, posten: str) -> float:
    """Extract Betrag for a GuV Posten from polars DataFrame."""
    row = guv_df.filter(guv_df["GuV Posten"] == posten)
    if row.is_empty():
        return 0.0
    return row["Betrag"][0]


def calc_total_tax(be: float, hebesatz: int) -> float:
    if be <= 0:
        return 0.0
    kst = round(math.floor(be) * 0.15, 2)
    soli = round(kst * 0.055, 2)
    gwst = round(math.floor(be / 100) * 100 * hebesatz * 3.5 / 10000, 2)
    return kst + soli + gwst


# --- Structure tests ---

def test_guv_has_required_columns(api, konten):
    result = api.guv(
        fixture_path("01_simple_profit.csv"), konten,
        DEFAULT_START, DEFAULT_ENDE, DEFAULT_HEBESATZ,
    )
    assert "GuV Posten" in result.columns
    assert "Betrag" in result.columns
    assert "Vorzeichen" in result.columns


def test_guv_has_required_rows(api, konten):
    result = api.guv(
        fixture_path("01_simple_profit.csv"), konten,
        DEFAULT_START, DEFAULT_ENDE, DEFAULT_HEBESATZ,
    )
    posten = result["GuV Posten"].to_list()
    assert "1. Umsatzerlöse" in posten
    assert "Betriebsergebnis" in posten
    assert "14. Steuern vom Einkommen und vom Ertrag" in posten
    assert "15. Ergebnis nach Steuern" in posten
    assert "17. Jahresüberschuss/Jahresfehlbetrag" in posten


# --- Value tests ---

GUV_CASES = [
    # (fixture, expected_be, expected_taxes_zero)
    ("01_simple_profit.csv", 10000.0, False),
    ("02_simple_loss.csv", -15000.0, True),
    ("03_multi_bookings.csv", 7000.0, False),
    ("07_breakeven.csv", 0.0, True),
    ("12_personnel_costs.csv", 31000.0, False),
    ("13_depreciation.csv", 19200.0, False),
    ("14_multiple_revenue_streams.csv", 30000.0, False),
    ("18_many_expense_categories.csv", 87149.11, False),
    ("22_full_year_monthly.csv", 84000.0, False),
]


@pytest.mark.parametrize("fixture,expected_be,taxes_zero", GUV_CASES, ids=[
    c[0].split(".")[0] for c in GUV_CASES
])
def test_guv_betriebsergebnis(api, konten, fixture, expected_be, taxes_zero):
    result = api.guv(
        fixture_path(fixture), konten,
        DEFAULT_START, DEFAULT_ENDE, DEFAULT_HEBESATZ,
    )
    be = get_guv_betrag(result, "Betriebsergebnis")
    assert abs(be - expected_be) < 0.02, f"BE: expected {expected_be}, got {be}"


@pytest.mark.parametrize("fixture,expected_be,taxes_zero", GUV_CASES, ids=[
    c[0].split(".")[0] for c in GUV_CASES
])
def test_guv_taxes_and_jahresueberschuss(api, konten, fixture, expected_be, taxes_zero):
    result = api.guv(
        fixture_path(fixture), konten,
        DEFAULT_START, DEFAULT_ENDE, DEFAULT_HEBESATZ,
    )
    steuern = get_guv_betrag(result, "14. Steuern vom Einkommen und vom Ertrag")
    ju = get_guv_betrag(result, "17. Jahresüberschuss/Jahresfehlbetrag")

    if taxes_zero:
        assert abs(steuern) < 0.01, f"Expected 0 taxes, got {steuern}"
    else:
        assert steuern > 0, f"Expected positive taxes, got {steuern}"
        expected_tax = calc_total_tax(expected_be, DEFAULT_HEBESATZ)
        assert abs(steuern - expected_tax) < 0.02, f"Tax: expected {expected_tax}, got {steuern}"

    # JÜ = BE - taxes (for simple cases without financial income)
    expected_ju = expected_be - steuern
    assert abs(ju - expected_ju) < 0.02, f"JÜ: expected {expected_ju}, got {ju}"


# --- GuV with financial income (goes to Ergebnis nach Steuern, not BE) ---

def test_guv_financial_income(api, konten):
    """Zinserträge (7100) mapped to '11. Sonstige Zinsen' → financial income,
    excluded from Betriebsergebnis (only 20000 Umsatz)."""
    result = api.guv(
        fixture_path("20_financial_income.csv"), konten,
        DEFAULT_START, DEFAULT_ENDE, DEFAULT_HEBESATZ,
    )
    be = get_guv_betrag(result, "Betriebsergebnis")
    assert abs(be - 20000.0) < 0.01, f"BE should exclude Zinserträge, got {be}"


# --- GuV with provisions release (sonstige betriebliche Erträge) ---

def test_guv_provisions_release(api, konten):
    result = api.guv(
        fixture_path("21_provisions_release.csv"), konten,
        DEFAULT_START, DEFAULT_ENDE, DEFAULT_HEBESATZ,
    )
    be = get_guv_betrag(result, "Betriebsergebnis")
    # 30000 revenue + 5000 provisions release = 35000 BE
    assert abs(be - 35000.0) < 0.01, f"BE should include provision release, got {be}"


# --- GuV with multiple revenue categories ---

def test_guv_multiple_revenue_streams(api, konten):
    result = api.guv(
        fixture_path("14_multiple_revenue_streams.csv"), konten,
        DEFAULT_START, DEFAULT_ENDE, DEFAULT_HEBESATZ,
    )
    be = get_guv_betrag(result, "Betriebsergebnis")
    # 15000 + 12000 Umsatzerlöse + 3000 Provisionsumsätze (sonstige betr. Erträge)
    assert abs(be - 30000.0) < 0.01


# --- Personnel cost categories in GuV ---

def test_guv_personnel_categories(api, konten):
    result = api.guv(
        fixture_path("12_personnel_costs.csv"), konten,
        DEFAULT_START, DEFAULT_ENDE, DEFAULT_HEBESATZ,
    )
    posten = result["GuV Posten"].to_list()
    assert "6. Personalaufwand" in posten
    personal = get_guv_betrag(result, "6. Personalaufwand")
    assert abs(personal - 19000.0) < 0.01  # 2*8000 GF + 2*1500 SV
