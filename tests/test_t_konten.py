"""Tests for T-Konten (ledger account) functions."""

import polars as pl

from src.buchhaltung import t_konto, t_konten
from tests.conftest import KONTEN_FILE, fixture_path, DEFAULT_START, DEFAULT_ENDE, DEFAULT_HEBESATZ


FIXTURE = fixture_path("01_simple_profit.csv")


class TestTKonto:

    def test_returns_dataframe(self):
        result = t_konto(FIXTURE, KONTEN_FILE, DEFAULT_START, DEFAULT_ENDE, DEFAULT_HEBESATZ, "1810")
        assert isinstance(result, pl.DataFrame)

    def test_has_soll_haben_columns(self):
        result = t_konto(FIXTURE, KONTEN_FILE, DEFAULT_START, DEFAULT_ENDE, DEFAULT_HEBESATZ, "1810")
        for col in ["Soll_Betrag", "Haben_Betrag", "Soll_Buchungstext", "Haben_Buchungstext"]:
            assert col in result.columns, f"Missing column: {col}"

    def test_nonexistent_account_returns_empty(self):
        result = t_konto(FIXTURE, KONTEN_FILE, DEFAULT_START, DEFAULT_ENDE, DEFAULT_HEBESATZ, "9999")
        assert result.is_empty()

    def test_saldo_row_present(self):
        result = t_konto(FIXTURE, KONTEN_FILE, DEFAULT_START, DEFAULT_ENDE, DEFAULT_HEBESATZ, "1810")
        texts = result["Soll_Buchungstext"].to_list() + result["Haben_Buchungstext"].to_list()
        assert "Saldo" in texts, "Saldo row should be present"

    def test_soll_equals_haben_with_saldo(self):
        """Total Soll (incl. saldo) should equal total Haben (incl. saldo)."""
        result = t_konto(FIXTURE, KONTEN_FILE, DEFAULT_START, DEFAULT_ENDE, DEFAULT_HEBESATZ, "1810")
        soll_total = result["Soll_Betrag"].sum()
        haben_total = result["Haben_Betrag"].sum()
        assert abs(soll_total - haben_total) < 0.01, f"Soll {soll_total} != Haben {haben_total}"


class TestTKonten:

    def test_returns_list(self):
        result = t_konten(FIXTURE, KONTEN_FILE, DEFAULT_START, DEFAULT_ENDE, DEFAULT_HEBESATZ)
        assert isinstance(result, list)

    def test_each_entry_has_required_keys(self):
        result = t_konten(FIXTURE, KONTEN_FILE, DEFAULT_START, DEFAULT_ENDE, DEFAULT_HEBESATZ)
        for entry in result:
            assert "konto" in entry
            assert "bezeichnung" in entry
            assert "saldo" in entry
            assert "detail" in entry
            assert isinstance(entry["detail"], pl.DataFrame)

    def test_only_nonzero_accounts(self):
        result = t_konten(FIXTURE, KONTEN_FILE, DEFAULT_START, DEFAULT_ENDE, DEFAULT_HEBESATZ)
        for entry in result:
            assert round(entry["saldo"], 2) != 0

    def test_includes_tax_accounts_for_profit(self):
        result = t_konten(FIXTURE, KONTEN_FILE, DEFAULT_START, DEFAULT_ENDE, DEFAULT_HEBESATZ)
        konten_list = [e["konto"] for e in result]
        assert "7600" in konten_list or "7610" in konten_list, "Tax accounts should be included"

    def test_complex_fixture(self):
        result = t_konten(
            fixture_path("22_full_year_monthly.csv"),
            KONTEN_FILE, DEFAULT_START, DEFAULT_ENDE, DEFAULT_HEBESATZ,
        )
        assert len(result) > 3
