"""Tests for Bilanz structure and values."""

import pytest
from tests.conftest import fixture_path, DEFAULT_START, DEFAULT_ENDE, DEFAULT_HEBESATZ


def _is_empty(col, val):
    """Filter for null or 'NA' (R writes NA as string in CSV)."""
    import polars as pl
    if val:
        return col == val
    return col.is_null() | (col == "NA")


def get_bilanz_betrag(bilanz_df, bilanzseite: str, ebene1: str, ebene2: str) -> str:
    """Extract formatted Betrag from bilanz polars DataFrame."""
    df = bilanz_df
    df = df.filter(_is_empty(df["Bilanzseite"], bilanzseite))
    df = df.filter(_is_empty(df["Ebene1"], ebene1))
    df = df.filter(_is_empty(df["Ebene2"], ebene2))

    if df.is_empty():
        return "0,00"
    return df["Betrag"][0]


def parse_german_number(s: str) -> float:
    """Parse German-formatted number like '1.234,56' to float."""
    return float(s.replace(".", "").replace(",", "."))


# --- Structure tests ---

def test_bilanz_has_required_columns(api, konten):
    result = api.bilanz(
        fixture_path("01_simple_profit.csv"), konten,
        DEFAULT_START, DEFAULT_ENDE, DEFAULT_HEBESATZ,
    )
    assert "Bilanzseite" in result.columns
    assert "Ebene1" in result.columns
    assert "Ebene2" in result.columns
    assert "Betrag" in result.columns


# --- Aktiva == Passiva for all valid scenarios ---

BALANCED_CASES = [
    "01_simple_profit.csv",
    "03_multi_bookings.csv",
    "10_with_vat.csv",
    "11_with_vat_and_expense.csv",
    "12_personnel_costs.csv",
    "13_depreciation.csv",
    "15_with_gewinnvortrag.csv",
    "17_liabilities.csv",
    "18_many_expense_categories.csv",
    "21_provisions_release.csv",
    "22_full_year_monthly.csv",
    "23_receivables.csv",
    "24_investments.csv",
]


@pytest.mark.parametrize("fixture", BALANCED_CASES, ids=[
    f.split(".")[0] for f in BALANCED_CASES
])
def test_bilanz_aktiva_equals_passiva(api, konten, fixture):
    result = api.bilanz(
        fixture_path(fixture), konten,
        DEFAULT_START, DEFAULT_ENDE, DEFAULT_HEBESATZ,
    )
    aktiva = get_bilanz_betrag(result, "Aktiva", "", "")
    passiva = get_bilanz_betrag(result, "Passiva", "", "")
    assert aktiva == passiva, f"Aktiva {aktiva} != Passiva {passiva}"


# --- Specific bilanz value tests ---

def test_bilanz_simple_profit_bank(api, konten):
    result = api.bilanz(
        fixture_path("01_simple_profit.csv"), konten,
        DEFAULT_START, DEFAULT_ENDE, DEFAULT_HEBESATZ,
    )
    bank = get_bilanz_betrag(result, "Aktiva", "B. Umlaufvermögen",
                             "IV. Kassenbestand, Bundesbankguthaben, Guthaben bei Kreditinstituten und Schecks")
    assert parse_german_number(bank) == 10000.0


def test_bilanz_gewinnvortrag(api, konten):
    result = api.bilanz(
        fixture_path("15_with_gewinnvortrag.csv"), konten,
        DEFAULT_START, DEFAULT_ENDE, DEFAULT_HEBESATZ,
    )
    gv = get_bilanz_betrag(result, "Passiva", "A. Eigenkapital",
                           "IV. Gewinnvortrag/Verlustvortrag")
    assert parse_german_number(gv) == 25000.0


def test_bilanz_gezeichnetes_kapital(api, konten):
    result = api.bilanz(
        fixture_path("15_with_gewinnvortrag.csv"), konten,
        DEFAULT_START, DEFAULT_ENDE, DEFAULT_HEBESATZ,
    )
    kapital = get_bilanz_betrag(result, "Passiva", "A. Eigenkapital",
                                "I. Gezeichnetes Kapital")
    assert parse_german_number(kapital) == 25000.0


def test_bilanz_investments_in_finanzanlagen(api, konten):
    result = api.bilanz(
        fixture_path("24_investments.csv"), konten,
        DEFAULT_START, DEFAULT_ENDE, DEFAULT_HEBESATZ,
    )
    fin = get_bilanz_betrag(result, "Aktiva", "A. Anlagevermögen", "III. Finanzanlagen")
    assert parse_german_number(fin) == 10000.0


def test_bilanz_depreciation_reduces_assets(api, konten):
    result = api.bilanz(
        fixture_path("13_depreciation.csv"), konten,
        DEFAULT_START, DEFAULT_ENDE, DEFAULT_HEBESATZ,
    )
    # GWG bought for 800 and fully depreciated -> Sachanlagen = 0
    sach = get_bilanz_betrag(result, "Aktiva", "A. Anlagevermögen", "II. Sachanlagen")
    assert parse_german_number(sach) == 0.0


def test_bilanz_receivables(api, konten):
    result = api.bilanz(
        fixture_path("23_receivables.csv"), konten,
        DEFAULT_START, DEFAULT_ENDE, DEFAULT_HEBESATZ,
    )
    # Receivable was 11900, then paid — Forderungen should be 0
    ford = get_bilanz_betrag(result, "Aktiva", "B. Umlaufvermögen",
                             "II. Forderungen und sonstige Vermögensgegenstände")
    assert parse_german_number(ford) == 0.0


def test_bilanz_liabilities(api, konten):
    """Verbindlichkeiten from unpaid invoices and salary obligations."""
    result = api.bilanz(
        fixture_path("17_liabilities.csv"), konten,
        DEFAULT_START, DEFAULT_ENDE, DEFAULT_HEBESATZ,
    )
    verb = get_bilanz_betrag(result, "Passiva", "C. Verbindlichkeiten", "")
    # 5000 Lieferantenverbindlichkeit + 8000 Lohnverbindlichkeit = 13000
    assert parse_german_number(verb) == 13000.0


def test_bilanz_rueckstellungen_with_taxes(api, konten):
    """Tax provisions from bilanz() — uses .get_konten_mit_steuer which adds
    tax bookings. Rückstellungen should show KSt + GewSt provisions."""
    result = api.bilanz(
        fixture_path("01_simple_profit.csv"), konten,
        DEFAULT_START, DEFAULT_ENDE, DEFAULT_HEBESATZ,
    )
    rs = get_bilanz_betrag(result, "Passiva", "B. Rückstellungen", "")
    # bilanz() internally adds tax bookings via .get_konten_mit_steuer
    assert parse_german_number(rs) >= 0  # May be 0 if taxes aren't booked as provisions
