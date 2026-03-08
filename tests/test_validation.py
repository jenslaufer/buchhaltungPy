"""Tests for journal and bilanz validation."""

import pytest
from tests.conftest import fixture_path, DEFAULT_START, DEFAULT_ENDE, DEFAULT_HEBESATZ


VALID_JOURNALS = [
    "01_simple_profit.csv",
    "02_simple_loss.csv",
    "03_multi_bookings.csv",
    "04_rounding.csv",
    "06_zero_revenue.csv",
    "07_breakeven.csv",
    "08_one_cent.csv",
    "09_large_amount.csv",
    "10_with_vat.csv",
    "11_with_vat_and_expense.csv",
    "12_personnel_costs.csv",
    "13_depreciation.csv",
    "14_multiple_revenue_streams.csv",
    "15_with_gewinnvortrag.csv",
    "16_multiple_bank_accounts.csv",
    "17_liabilities.csv",
    "18_many_expense_categories.csv",
    "19_boundary_rounding_99.csv",
    "20_financial_income.csv",
    "21_provisions_release.csv",
    "22_full_year_monthly.csv",
    "23_receivables.csv",
    "24_investments.csv",
    "25_mixed_periods.csv",
]


@pytest.mark.parametrize("fixture", VALID_JOURNALS, ids=[
    f.split(".")[0] for f in VALID_JOURNALS
])
def test_valid_journals(api, konten, fixture):
    result = api.validiere_journal(
        fixture_path(fixture), konten, DEFAULT_START, DEFAULT_ENDE
    )
    assert result == "", f"Expected valid, got: {result}"


INVALID_JOURNALS = [
    "05_invalid_unbalanced.csv",
]


@pytest.mark.parametrize("fixture", INVALID_JOURNALS, ids=[
    f.split(".")[0] for f in INVALID_JOURNALS
])
def test_invalid_journals(api, konten, fixture):
    result = api.validiere_journal(
        fixture_path(fixture), konten, DEFAULT_START, DEFAULT_ENDE
    )
    assert len(result) > 0, "Expected error message for invalid journal"
    assert "FEHLER" in result, f"Expected FEHLER in: {result}"


# --- Bilanz validation (Aktiva == Passiva) ---

BILANZ_VALID_JOURNALS = [
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


@pytest.mark.parametrize("fixture", BILANZ_VALID_JOURNALS, ids=[
    f.split(".")[0] for f in BILANZ_VALID_JOURNALS
])
def test_bilanz_validates(api, konten, fixture):
    result = api.validiere_bilanz(
        fixture_path(fixture), konten, DEFAULT_START, DEFAULT_ENDE, DEFAULT_HEBESATZ
    )
    assert result == "", f"Bilanz invalid: {result}"
