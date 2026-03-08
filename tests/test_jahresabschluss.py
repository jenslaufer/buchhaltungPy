"""Tests for jahresabschluss (year-end closing) and jahreseroeffnung (year opening)."""

import shutil
from pathlib import Path

import polars as pl
import pytest

from tests.conftest import KONTEN_FILE, fixture_path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _copy_fixture(name: str, tmp_path: Path) -> str:
    """Copy a fixture CSV to tmp_path and return the path as string."""
    src = fixture_path(name)
    dst = tmp_path / name
    shutil.copy(src, dst)
    return str(dst)


def _read_journal(path: str) -> pl.DataFrame:
    return pl.read_csv(path, schema_overrides={"Konto": pl.Utf8, "Journalnummer": pl.Int64})


def _has_jeb(journal: pl.DataFrame) -> bool:
    return journal.filter(pl.col("Belegnummer").str.contains("JEB")).height > 0


def _has_jab(journal: pl.DataFrame) -> bool:
    return journal.filter(pl.col("Belegnummer").str.contains("JAB")).height > 0


# ---------------------------------------------------------------------------
# jahresabschluss tests
# ---------------------------------------------------------------------------

class TestJahresabschluss:

    def test_creates_jeb_entries(self, api, tmp_path, backend):
        journal_file = _copy_fixture("01_simple_profit.csv", tmp_path)
        api.jahresabschluss(journal_file, KONTEN_FILE, "2024-01-01", 380)
        journal = _read_journal(journal_file)
        assert _has_jeb(journal), "Journal should contain JEB entries after closing"

    def test_idempotent(self, api, tmp_path, backend):
        journal_file = _copy_fixture("01_simple_profit.csv", tmp_path)
        api.jahresabschluss(journal_file, KONTEN_FILE, "2024-01-01", 380)
        rows_after_first = _read_journal(journal_file).height
        api.jahresabschluss(journal_file, KONTEN_FILE, "2024-01-01", 380)
        rows_after_second = _read_journal(journal_file).height
        assert rows_after_first == rows_after_second

    def test_creates_backup(self, api, tmp_path, backend):
        journal_file = _copy_fixture("01_simple_profit.csv", tmp_path)
        api.jahresabschluss(journal_file, KONTEN_FILE, "2024-01-01", 380)
        backup = Path(journal_file.replace(".csv", "_backup.csv"))
        assert backup.exists()

    def test_backup_contains_original(self, api, tmp_path, backend):
        journal_file = _copy_fixture("01_simple_profit.csv", tmp_path)
        original = _read_journal(journal_file)
        api.jahresabschluss(journal_file, KONTEN_FILE, "2024-01-01", 380)
        backup = _read_journal(journal_file.replace(".csv", "_backup.csv"))
        assert original.height == backup.height

    def test_tax_bookings_present_for_profit(self, api, tmp_path, backend):
        journal_file = _copy_fixture("01_simple_profit.csv", tmp_path)
        api.jahresabschluss(journal_file, KONTEN_FILE, "2024-01-01", 380)
        journal = _read_journal(journal_file)
        jeb = journal.filter(pl.col("Belegnummer").str.contains("JEB"))
        tax_accounts = {"7600", "7608", "7610", "3020", "3035", "3040"}
        jeb_accounts = set(jeb["Konto"].to_list())
        assert tax_accounts.issubset(jeb_accounts), f"Missing tax accounts: {tax_accounts - jeb_accounts}"

    def test_no_tax_bookings_for_loss(self, api, tmp_path, backend):
        if backend == "r":
            pytest.skip("R creates zero-amount tax bookings for losses (known difference)")
        journal_file = _copy_fixture("02_simple_loss.csv", tmp_path)
        api.jahresabschluss(journal_file, KONTEN_FILE, "2024-01-01", 380)
        journal = _read_journal(journal_file)
        jeb = journal.filter(pl.col("Belegnummer").str.contains("JEB"))
        tax_accounts = {"7600", "7608", "7610", "3020", "3035", "3040"}
        jeb_accounts = set(jeb["Konto"].to_list())
        assert not tax_accounts.intersection(jeb_accounts), "Loss should not produce tax bookings"

    def test_closing_entries_have_jeb_belegnummer(self, api, tmp_path, backend):
        journal_file = _copy_fixture("01_simple_profit.csv", tmp_path)
        api.jahresabschluss(journal_file, KONTEN_FILE, "2024-01-01", 380)
        journal = _read_journal(journal_file)
        jeb = journal.filter(pl.col("Belegnummer").str.contains("JEB"))
        belegnummern = jeb["Belegnummer"].unique().to_list()
        assert all(b.startswith("JEB") for b in belegnummern)

    def test_journal_valid_after_closing(self, api, tmp_path, backend):
        """Journal validation (excluding JEB) should still pass after closing."""
        journal_file = _copy_fixture("01_simple_profit.csv", tmp_path)
        api.jahresabschluss(journal_file, KONTEN_FILE, "2024-01-01", 380)
        result = api.validiere_journal(
            journal_file, KONTEN_FILE, "2024-01-01", "2024-12-31"
        )
        assert result == "", f"Journal validation failed: {result}"

    def test_soll_haben_balanced_in_jeb(self, api, tmp_path, backend):
        """Each JEB Buchungssatz must have balanced Soll/Haben."""
        journal_file = _copy_fixture("01_simple_profit.csv", tmp_path)
        api.jahresabschluss(journal_file, KONTEN_FILE, "2024-01-01", 380)
        journal = _read_journal(journal_file)
        jeb = journal.filter(pl.col("Belegnummer").str.contains("JEB"))
        balance = (
            jeb.with_columns(
                pl.when(pl.col("Typ") == "Soll")
                .then(-pl.col("Betrag"))
                .otherwise(pl.col("Betrag"))
                .alias("Signed")
            )
            .group_by("Buchungssatznummer")
            .agg(pl.col("Signed").sum().round(2).alias("Sum"))
        )
        unbalanced = balance.filter(pl.col("Sum").abs() > 0.01)
        assert unbalanced.is_empty(), f"Unbalanced JEB entries: {unbalanced}"

    def test_guv_account_used_for_guv_closings(self, api, tmp_path, backend):
        """GuV accounts should be closed against 00000."""
        journal_file = _copy_fixture("01_simple_profit.csv", tmp_path)
        api.jahresabschluss(journal_file, KONTEN_FILE, "2024-01-01", 380)
        journal = _read_journal(journal_file)
        jeb = journal.filter(pl.col("Belegnummer").str.contains("JEB"))
        assert "00000" in jeb["Konto"].to_list(), "GuV account 00000 should appear in closing entries"

    def test_settlement_account_used_for_bilanz_closings(self, api, tmp_path, backend):
        """Bilanz accounts should be closed against 9000."""
        journal_file = _copy_fixture("01_simple_profit.csv", tmp_path)
        api.jahresabschluss(journal_file, KONTEN_FILE, "2024-01-01", 380)
        journal = _read_journal(journal_file)
        jeb = journal.filter(pl.col("Belegnummer").str.contains("JEB"))
        assert "9000" in jeb["Konto"].to_list(), "Settlement account 9000 should appear in closing entries"

    def test_journalnummer_sequential(self, api, tmp_path, backend):
        journal_file = _copy_fixture("01_simple_profit.csv", tmp_path)
        api.jahresabschluss(journal_file, KONTEN_FILE, "2024-01-01", 380)
        journal = _read_journal(journal_file)
        jn = journal["Journalnummer"].to_list()
        assert jn == list(range(1, len(jn) + 1)), "Journalnummern must be sequential"

    def test_with_vat(self, api, tmp_path, backend):
        """Jahresabschluss should work with VAT fixtures."""
        journal_file = _copy_fixture("10_with_vat.csv", tmp_path)
        api.jahresabschluss(journal_file, KONTEN_FILE, "2024-01-01", 380)
        journal = _read_journal(journal_file)
        assert _has_jeb(journal)

    def test_belegdatum_is_year_end(self, api, tmp_path, backend):
        journal_file = _copy_fixture("01_simple_profit.csv", tmp_path)
        api.jahresabschluss(journal_file, KONTEN_FILE, "2024-01-01", 380)
        journal = _read_journal(journal_file)
        jeb = journal.filter(pl.col("Belegnummer").str.contains("JEB"))
        dates = jeb["Belegdatum"].unique().to_list()
        assert all(d == "31.12.2024" for d in dates), f"JEB dates should be 31.12.2024, got {dates}"


# ---------------------------------------------------------------------------
# jahreseroeffnung tests
# ---------------------------------------------------------------------------

class TestJahreseroeffnung:

    def _close_and_open(self, api, fixture: str, tmp_path: Path) -> tuple[str, str]:
        """Close the year and open the next. Returns (closed_journal, new_journal) paths."""
        journal_file = _copy_fixture(fixture, tmp_path)
        api.jahresabschluss(journal_file, KONTEN_FILE, "2024-01-01", 380)
        new_file = api.jahreseroeffnung(journal_file, KONTEN_FILE, "2024-12-31", 380)
        return journal_file, new_file

    def test_creates_new_journal_file(self, api, tmp_path, backend):
        _, new_file = self._close_and_open(api, "01_simple_profit.csv", tmp_path)
        assert Path(new_file).exists()

    def test_new_file_name_contains_next_year(self, api, tmp_path, backend):
        _, new_file = self._close_and_open(api, "01_simple_profit.csv", tmp_path)
        assert "2025" in Path(new_file).name

    def test_new_journal_has_jab_entries(self, api, tmp_path, backend):
        _, new_file = self._close_and_open(api, "01_simple_profit.csv", tmp_path)
        journal = _read_journal(new_file)
        assert _has_jab(journal), "New journal should contain JAB entries"

    def test_no_guv_accounts_carried_forward(self, api, tmp_path, backend):
        """Only balance sheet accounts should appear in opening entries."""
        _, new_file = self._close_and_open(api, "01_simple_profit.csv", tmp_path)
        journal = _read_journal(new_file)
        konten = pl.read_csv(KONTEN_FILE, schema_overrides={"Konto": pl.Utf8})
        guv_konten = konten.filter(pl.col("GuV Posten").is_not_null())["Konto"].to_list()
        jab_konten = journal["Konto"].unique().to_list()
        carried_guv = [k for k in jab_konten if k in guv_konten]
        assert carried_guv == [], f"GuV accounts should not be carried forward: {carried_guv}"

    def test_soll_haben_balanced_in_jab(self, api, tmp_path, backend):
        _, new_file = self._close_and_open(api, "01_simple_profit.csv", tmp_path)
        journal = _read_journal(new_file)
        balance = (
            journal.with_columns(
                pl.when(pl.col("Typ") == "Soll")
                .then(-pl.col("Betrag"))
                .otherwise(pl.col("Betrag"))
                .alias("Signed")
            )
            .group_by("Buchungssatznummer")
            .agg(pl.col("Signed").sum().round(2).alias("Sum"))
        )
        unbalanced = balance.filter(pl.col("Sum").abs() > 0.01)
        assert unbalanced.is_empty(), f"Unbalanced JAB entries: {unbalanced}"

    def test_journalnummer_sequential_in_new(self, api, tmp_path, backend):
        _, new_file = self._close_and_open(api, "01_simple_profit.csv", tmp_path)
        journal = _read_journal(new_file)
        jn = journal["Journalnummer"].to_list()
        assert jn == list(range(1, len(jn) + 1))

    def test_belegdatum_is_jan_first(self, api, tmp_path, backend):
        _, new_file = self._close_and_open(api, "01_simple_profit.csv", tmp_path)
        journal = _read_journal(new_file)
        dates = journal["Belegdatum"].unique().to_list()
        assert all(d == "01.01.2025" for d in dates), f"JAB dates should be 01.01.2025, got {dates}"

    def test_gewinnvortrag_carried_forward(self, api, tmp_path, backend):
        """Jahresüberschuss should be transferred to 2970 (Gewinnvortrag)."""
        _, new_file = self._close_and_open(api, "01_simple_profit.csv", tmp_path)
        journal = _read_journal(new_file)
        assert "2970" in journal["Konto"].to_list(), "Gewinnvortrag account 2970 should be in new journal"

    def test_gewinnvortrag_includes_prior_retained_earnings(self, api, tmp_path, backend):
        """When prior year has Gewinnvortrag, it should be combined with Jahresüberschuss."""
        _, new_file = self._close_and_open(api, "15_with_gewinnvortrag.csv", tmp_path)
        journal = _read_journal(new_file)
        gv_entries = journal.filter(pl.col("Konto") == "2970")
        assert gv_entries.height > 0, "Gewinnvortrag 2970 should be in new journal"
        gv_betrag = gv_entries["Betrag"].sum()
        assert gv_betrag > 25000, f"Gewinnvortrag should exceed prior 25000, got {gv_betrag}"

    def test_settlement_account_nets_to_zero(self, api, tmp_path, backend):
        """Account 9000 should net to zero across all JAB entries."""
        _, new_file = self._close_and_open(api, "01_simple_profit.csv", tmp_path)
        journal = _read_journal(new_file)
        acc_9000 = journal.filter(pl.col("Konto") == "9000")
        signed = (
            acc_9000.with_columns(
                pl.when(pl.col("Typ") == "Soll")
                .then(-pl.col("Betrag"))
                .otherwise(pl.col("Betrag"))
                .alias("Signed")
            )["Signed"].sum()
        )
        assert abs(signed) < 0.01, f"Account 9000 should net to zero, got {signed}"

    def test_loss_carried_forward(self, api, tmp_path, backend):
        """Loss scenario: negative Jahresüberschuss should still be forwarded to 2970."""
        _, new_file = self._close_and_open(api, "02_simple_loss.csv", tmp_path)
        journal = _read_journal(new_file)
        assert "2970" in journal["Konto"].to_list(), "Gewinnvortrag 2970 should be in new journal even for loss"

    def test_with_complex_fixture(self, api, tmp_path, backend):
        """jahresabschluss + jahreseroeffnung should work with complex fixtures."""
        _, new_file = self._close_and_open(api, "22_full_year_monthly.csv", tmp_path)
        journal = _read_journal(new_file)
        assert journal.height > 0
        assert _has_jab(journal)
