"""Tests for Konten (account balances)."""

import pytest
from tests.conftest import fixture_path, DEFAULT_START, DEFAULT_ENDE


def get_konto_saldo(konten_df, konto: str) -> tuple[float, str]:
    """Get (Saldo, Saldo Typ) for a Konto from polars DataFrame."""
    row = konten_df.filter(konten_df["Konto"] == konto)
    if row.is_empty():
        return 0.0, ""
    return row["Saldo"][0], row["Saldo Typ"][0]


def test_konten_has_required_columns(api, konten):
    result = api.get_konten(
        fixture_path("01_simple_profit.csv"), konten, DEFAULT_START, DEFAULT_ENDE
    )
    assert "Konto" in result.columns
    assert "Saldo" in result.columns
    assert "Saldo Typ" in result.columns
    assert "Bezeichnung" in result.columns


def test_konten_simple_profit_bank(api, konten):
    result = api.get_konten(
        fixture_path("01_simple_profit.csv"), konten, DEFAULT_START, DEFAULT_ENDE
    )
    saldo, typ = get_konto_saldo(result, "1810")
    assert abs(saldo - 10000.0) < 0.01
    # Bank account with Soll booking -> positive bank balance


def test_konten_simple_profit_revenue(api, konten):
    result = api.get_konten(
        fixture_path("01_simple_profit.csv"), konten, DEFAULT_START, DEFAULT_ENDE
    )
    saldo, typ = get_konto_saldo(result, "4400")
    assert abs(saldo - 10000.0) < 0.01


def test_konten_loss_bank_negative(api, konten):
    """Loss scenario: bank has net outflow.
    Soll booking on bank = debit = cash in. Haben = credit = cash out.
    -20000 Haben + 5000 Soll = -15000 → Saldo 15000, Typ depends on sign convention."""
    result = api.get_konten(
        fixture_path("02_simple_loss.csv"), konten, DEFAULT_START, DEFAULT_ENDE
    )
    saldo, typ = get_konto_saldo(result, "1810")
    assert abs(saldo - 15000.0) < 0.01


def test_konten_multiple_banks(api, konten):
    result = api.get_konten(
        fixture_path("16_multiple_bank_accounts.csv"), konten, DEFAULT_START, DEFAULT_ENDE
    )
    s1810, _ = get_konto_saldo(result, "1810")
    s1820, _ = get_konto_saldo(result, "1820")
    # 1810: +8000 +5000 = 13000 Soll
    assert abs(s1810 - 13000.0) < 0.01
    # 1820: +12000 -5000 = 7000 Soll
    assert abs(s1820 - 7000.0) < 0.01


def test_konten_vat_accounts(api, konten):
    result = api.get_konten(
        fixture_path("11_with_vat_and_expense.csv"), konten, DEFAULT_START, DEFAULT_ENDE
    )
    # USt 19% should have 1900 Haben saldo
    s_ust, t_ust = get_konto_saldo(result, "3806")
    assert abs(s_ust - 1900.0) < 0.01
    # VSt 19% should have 95 Soll saldo
    s_vst, t_vst = get_konto_saldo(result, "1406")
    assert abs(s_vst - 95.0) < 0.01


def test_konten_period_filter(api, konten):
    result = api.get_konten(
        fixture_path("25_mixed_periods.csv"), konten, DEFAULT_START, DEFAULT_ENDE
    )
    # Only 2024 booking (10000) should count, not 2023 or 2025
    s_bank, _ = get_konto_saldo(result, "1810")
    assert abs(s_bank - 10000.0) < 0.01
