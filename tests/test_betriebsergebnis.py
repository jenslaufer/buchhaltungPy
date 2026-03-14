"""Tests for berechne_betriebsergebnis across all fixtures."""

import pytest
from tests.conftest import fixture_path, DEFAULT_START, DEFAULT_ENDE


CASES = [
    # (fixture, start, ende, expected_be)
    ("01_simple_profit.csv", DEFAULT_START, DEFAULT_ENDE, 10000.0),
    ("02_simple_loss.csv", DEFAULT_START, DEFAULT_ENDE, -15000.0),
    ("03_multi_bookings.csv", DEFAULT_START, DEFAULT_ENDE, 7000.0),
    ("04_rounding.csv", DEFAULT_START, DEFAULT_ENDE, 1234.56),
    ("06_zero_revenue.csv", DEFAULT_START, DEFAULT_ENDE, -500.0),
    ("07_breakeven.csv", DEFAULT_START, DEFAULT_ENDE, 0.0),
    ("08_one_cent.csv", DEFAULT_START, DEFAULT_ENDE, 0.01),
    ("09_large_amount.csv", DEFAULT_START, DEFAULT_ENDE, 1000000.0),
    ("10_with_vat.csv", DEFAULT_START, DEFAULT_ENDE, 10000.0),
    ("11_with_vat_and_expense.csv", DEFAULT_START, DEFAULT_ENDE, 9500.0),
    ("12_personnel_costs.csv", DEFAULT_START, DEFAULT_ENDE, 31000.0),
    ("13_depreciation.csv", DEFAULT_START, DEFAULT_ENDE, 19200.0),
    ("14_multiple_revenue_streams.csv", DEFAULT_START, DEFAULT_ENDE, 30000.0),
    ("15_with_gewinnvortrag.csv", DEFAULT_START, DEFAULT_ENDE, 10000.0),
    ("16_multiple_bank_accounts.csv", DEFAULT_START, DEFAULT_ENDE, 20000.0),
    ("17_liabilities.csv", DEFAULT_START, DEFAULT_ENDE, 17000.0),
    ("19_boundary_rounding_99.csv", DEFAULT_START, DEFAULT_ENDE, 99.99),
    # Zinserträge (7100) mapped to "11. Sonstige Zinsen" → excluded from BE (financial income, not operating)
    ("20_financial_income.csv", DEFAULT_START, DEFAULT_ENDE, 20000.0),
    ("22_full_year_monthly.csv", DEFAULT_START, DEFAULT_ENDE, 84000.0),
    ("24_investments.csv", DEFAULT_START, DEFAULT_ENDE, 50000.0),
    # Period filtering
    ("03_multi_bookings.csv", "2024-01-01", "2024-01-31", 10000.0),
    ("03_multi_bookings.csv", "2024-03-01", "2024-03-31", -3000.0),
    ("25_mixed_periods.csv", DEFAULT_START, DEFAULT_ENDE, 10000.0),
    # Q1 only of full year
    ("22_full_year_monthly.csv", "2024-01-01", "2024-03-31", 21000.0),
    # Single month
    ("22_full_year_monthly.csv", "2024-06-01", "2024-06-30", 7000.0),
]


@pytest.mark.parametrize("fixture,start,ende,expected", CASES, ids=[
    f"{c[0].split('.')[0]}_{c[1]}_{c[2]}" for c in CASES
])
def test_betriebsergebnis(api, konten, fixture, start, ende, expected):
    result = api.berechne_betriebsergebnis(
        fixture_path(fixture), konten, start, ende
    )
    assert abs(result - expected) < 0.02, f"Expected {expected}, got {result}"
