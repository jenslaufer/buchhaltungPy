"""Tests for the zeitreihe (monthly time series) function and CLI command."""

import io

import polars as pl
import pytest

from src.buchhaltung import zeitreihe
from src.cli import main
from tests.conftest import fixture_path, KONTEN_FILE

START = "2024-01-01"
ENDE = "2024-12-31"

EXPECTED_COLUMNS = ["Monat", "Umsatz", "Aufwand", "Ergebnis", "Anzahl_Buchungen"]

JOURNAL_HEADER = (
    "Journalnummer,Buchungssatznummer,Belegnummer,Belegdatum,"
    "Buchungsdatum,Buchungstext,Konto,Typ,Betrag\n"
)


def write_journal(tmp_path, rows: list[str]) -> str:
    p = tmp_path / "journal.csv"
    p.write_text(JOURNAL_HEADER + "".join(rows))
    return str(p)


# ---------------------------------------------------------------------------
# Column structure
# ---------------------------------------------------------------------------


def test_zeitreihe_has_required_columns():
    result = zeitreihe(
        fixture_path("22_full_year_monthly.csv"), KONTEN_FILE, START, ENDE
    )
    assert isinstance(result, pl.DataFrame)
    for col in EXPECTED_COLUMNS:
        assert col in result.columns, f"Missing column: {col}"


def test_zeitreihe_exact_columns():
    """Result must have exactly the specified columns, no extras."""
    result = zeitreihe(
        fixture_path("22_full_year_monthly.csv"), KONTEN_FILE, START, ENDE
    )
    assert set(result.columns) == set(EXPECTED_COLUMNS)


# ---------------------------------------------------------------------------
# Row count: one row per active month
# ---------------------------------------------------------------------------


def test_zeitreihe_full_year_returns_12_months():
    """Full-year monthly fixture has bookings in all 12 months."""
    result = zeitreihe(
        fixture_path("22_full_year_monthly.csv"), KONTEN_FILE, START, ENDE
    )
    assert result.height == 12


def test_zeitreihe_single_month_range():
    """Date range covering only January 2024 returns exactly one row."""
    result = zeitreihe(
        fixture_path("22_full_year_monthly.csv"),
        KONTEN_FILE,
        "2024-01-01",
        "2024-01-31",
    )
    assert result.height == 1


def test_zeitreihe_partial_year_returns_correct_count():
    """fixture 14_multiple_revenue_streams has bookings in Jan, Feb, Mar."""
    result = zeitreihe(
        fixture_path("14_multiple_revenue_streams.csv"), KONTEN_FILE, START, ENDE
    )
    assert result.height == 3


# ---------------------------------------------------------------------------
# Monat ordering
# ---------------------------------------------------------------------------


def test_zeitreihe_monat_sorted_ascending():
    result = zeitreihe(
        fixture_path("22_full_year_monthly.csv"), KONTEN_FILE, START, ENDE
    )
    months = result["Monat"].to_list()
    assert months == sorted(months)


def test_zeitreihe_monat_sorted_ascending_sparse(tmp_path):
    """Months that are not sequential must still be sorted ascending."""
    rows = [
        # January booking
        "1,1,RE001,15.01.2024,15.01.2024,Umsatz Jan,1810,Soll,5000\n",
        "2,1,RE001,15.01.2024,15.01.2024,Umsatz Jan,4400,Haben,5000\n",
        # March booking (February absent)
        "3,2,RE002,20.03.2024,20.03.2024,Umsatz Mar,1810,Soll,8000\n",
        "4,2,RE002,20.03.2024,20.03.2024,Umsatz Mar,4400,Haben,8000\n",
        # June booking
        "5,3,RE003,10.06.2024,10.06.2024,Umsatz Jun,1810,Soll,3000\n",
        "6,3,RE003,10.06.2024,10.06.2024,Umsatz Jun,4400,Haben,3000\n",
    ]
    journal = write_journal(tmp_path, rows)
    result = zeitreihe(journal, KONTEN_FILE, START, ENDE)
    months = result["Monat"].to_list()
    assert months == sorted(months)
    assert result.height == 3


# ---------------------------------------------------------------------------
# Value correctness
# ---------------------------------------------------------------------------


def test_zeitreihe_umsatz_per_month():
    """Each month in fixture 22 has 10000 Haben on 4400."""
    result = zeitreihe(
        fixture_path("22_full_year_monthly.csv"), KONTEN_FILE, START, ENDE
    )
    for umsatz in result["Umsatz"].to_list():
        assert abs(umsatz - 10000.0) < 0.01, f"Expected 10000, got {umsatz}"


def test_zeitreihe_aufwand_per_month():
    """Each month in fixture 22 has 3000 Soll on 6300 (expense account)."""
    result = zeitreihe(
        fixture_path("22_full_year_monthly.csv"), KONTEN_FILE, START, ENDE
    )
    for aufwand in result["Aufwand"].to_list():
        assert abs(aufwand - 3000.0) < 0.01, f"Expected 3000, got {aufwand}"


def test_zeitreihe_ergebnis_equals_umsatz_minus_aufwand():
    """Ergebnis must equal Umsatz - Aufwand for every row."""
    result = zeitreihe(
        fixture_path("22_full_year_monthly.csv"), KONTEN_FILE, START, ENDE
    )
    for row in result.iter_rows(named=True):
        expected = row["Umsatz"] - row["Aufwand"]
        assert abs(row["Ergebnis"] - expected) < 0.01, (
            f"Ergebnis mismatch for {row['Monat']}: "
            f"{row['Umsatz']} - {row['Aufwand']} != {row['Ergebnis']}"
        )


def test_zeitreihe_ergebnis_positive_for_profitable_month():
    """fixture 01 has 10000 revenue and no expense — Ergebnis must be positive."""
    result = zeitreihe(
        fixture_path("01_simple_profit.csv"), KONTEN_FILE, START, ENDE
    )
    assert result.height == 1
    assert result["Ergebnis"][0] > 0


def test_zeitreihe_ergebnis_negative_for_loss_month():
    """fixture 02 has only expense entries — Ergebnis must be negative."""
    result = zeitreihe(
        fixture_path("02_simple_loss.csv"), KONTEN_FILE, START, ENDE
    )
    assert result.height == 1
    assert result["Ergebnis"][0] < 0


def test_zeitreihe_umsatz_includes_multiple_revenue_accounts(tmp_path):
    """Revenue on 4400 and another 4xxx account (e.g. 4560) both count as Umsatz."""
    rows = [
        # 4400 revenue
        "1,1,RE001,15.01.2024,15.01.2024,Beratung,1810,Soll,10000\n",
        "2,1,RE001,15.01.2024,15.01.2024,Beratung,4400,Haben,10000\n",
        # 4560 revenue (Provisionsumsätze)
        "3,2,PR001,15.01.2024,15.01.2024,Provision,1810,Soll,2000\n",
        "4,2,PR001,15.01.2024,15.01.2024,Provision,4560,Haben,2000\n",
    ]
    journal = write_journal(tmp_path, rows)
    result = zeitreihe(journal, KONTEN_FILE, START, ENDE)
    assert result.height == 1
    assert abs(result["Umsatz"][0] - 12000.0) < 0.01


def test_zeitreihe_aufwand_includes_multiple_expense_ranges(tmp_path):
    """Expense accounts 5xxx, 6xxx, and 7xxx all contribute to Aufwand."""
    rows = [
        # 6xxx expense
        "1,1,AW001,10.01.2024,10.01.2024,Miete,6310,Soll,1000\n",
        "2,1,AW001,10.01.2024,10.01.2024,Miete,1810,Haben,1000\n",
        # 5xxx expense (Wareneinsatz)
        "3,2,AW002,10.01.2024,10.01.2024,Wareneinsatz,5000,Soll,500\n",
        "4,2,AW002,10.01.2024,10.01.2024,Wareneinsatz,1810,Haben,500\n",
        # 7xxx expense (Zinsaufwand)
        "5,3,AW003,10.01.2024,10.01.2024,Zinsen,7310,Soll,200\n",
        "6,3,AW003,10.01.2024,10.01.2024,Zinsen,1810,Haben,200\n",
        # Revenue to keep the journal sensible
        "7,4,RE001,10.01.2024,10.01.2024,Umsatz,1810,Soll,5000\n",
        "8,4,RE001,10.01.2024,10.01.2024,Umsatz,4400,Haben,5000\n",
    ]
    journal = write_journal(tmp_path, rows)
    result = zeitreihe(journal, KONTEN_FILE, START, ENDE)
    assert result.height == 1
    assert abs(result["Aufwand"][0] - 1700.0) < 0.01


# ---------------------------------------------------------------------------
# Anzahl_Buchungen
# ---------------------------------------------------------------------------


def test_zeitreihe_anzahl_buchungen_counts_unique_buchungssatznummer():
    """fixture 22 has 2 Buchungssatznummern per month (one revenue, one expense)."""
    result = zeitreihe(
        fixture_path("22_full_year_monthly.csv"), KONTEN_FILE, START, ENDE
    )
    for row in result.iter_rows(named=True):
        assert row["Anzahl_Buchungen"] == 2, (
            f"Expected 2 bookings for {row['Monat']}, got {row['Anzahl_Buchungen']}"
        )


def test_zeitreihe_anzahl_buchungen_correct_for_multi_booking_month(tmp_path):
    rows = [
        "1,1,RE001,05.03.2024,05.03.2024,Umsatz A,1810,Soll,3000\n",
        "2,1,RE001,05.03.2024,05.03.2024,Umsatz A,4400,Haben,3000\n",
        "3,2,RE002,12.03.2024,12.03.2024,Umsatz B,1810,Soll,2000\n",
        "4,2,RE002,12.03.2024,12.03.2024,Umsatz B,4400,Haben,2000\n",
        "5,3,AW001,20.03.2024,20.03.2024,Kosten,6310,Soll,500\n",
        "6,3,AW001,20.03.2024,20.03.2024,Kosten,1810,Haben,500\n",
    ]
    journal = write_journal(tmp_path, rows)
    result = zeitreihe(journal, KONTEN_FILE, START, ENDE)
    assert result.height == 1
    assert result["Anzahl_Buchungen"][0] == 3


# ---------------------------------------------------------------------------
# Non-negativity where expected
# ---------------------------------------------------------------------------


def test_zeitreihe_umsatz_non_negative():
    """Umsatz (sum of revenue Haben) is always >= 0."""
    result = zeitreihe(
        fixture_path("18_many_expense_categories.csv"), KONTEN_FILE, START, ENDE
    )
    for umsatz in result["Umsatz"].to_list():
        assert umsatz >= 0, f"Umsatz must not be negative, got {umsatz}"


def test_zeitreihe_aufwand_non_negative():
    """Aufwand (sum of expense Soll) is always >= 0."""
    result = zeitreihe(
        fixture_path("18_many_expense_categories.csv"), KONTEN_FILE, START, ENDE
    )
    for aufwand in result["Aufwand"].to_list():
        assert aufwand >= 0, f"Aufwand must not be negative, got {aufwand}"


def test_zeitreihe_anzahl_buchungen_positive():
    result = zeitreihe(
        fixture_path("22_full_year_monthly.csv"), KONTEN_FILE, START, ENDE
    )
    for count in result["Anzahl_Buchungen"].to_list():
        assert count > 0, f"Anzahl_Buchungen must be positive, got {count}"


# ---------------------------------------------------------------------------
# Date range filtering
# ---------------------------------------------------------------------------


def test_zeitreihe_date_range_excludes_out_of_range():
    """fixture 25 has bookings in Dec 2023, Jan 2024, Jan 2025.
    With 2024 range, only Jan 2024 should appear."""
    result = zeitreihe(
        fixture_path("25_mixed_periods.csv"), KONTEN_FILE, START, ENDE
    )
    assert result.height == 1
    months = result["Monat"].to_list()
    assert all("2024" in str(m) for m in months)


def test_zeitreihe_single_month_range_values():
    """Restrict to February 2024 in the full-year fixture — only Feb row returned."""
    result = zeitreihe(
        fixture_path("22_full_year_monthly.csv"),
        KONTEN_FILE,
        "2024-02-01",
        "2024-02-29",
    )
    assert result.height == 1
    assert abs(result["Umsatz"][0] - 10000.0) < 0.01
    assert abs(result["Aufwand"][0] - 3000.0) < 0.01
    assert abs(result["Ergebnis"][0] - 7000.0) < 0.01


# ---------------------------------------------------------------------------
# JAB / JEB exclusion
# ---------------------------------------------------------------------------


def test_zeitreihe_excludes_jab_entries():
    """JAB entries in fixture 15 must not contribute to Umsatz or Aufwand."""
    result = zeitreihe(
        fixture_path("15_with_gewinnvortrag.csv"), KONTEN_FILE, START, ENDE
    )
    # fixture 15 has JAB entries in Jan and one real booking (4400 Haben 10000) in Feb
    assert result.height == 1
    months = result["Monat"].to_list()
    assert all("2024-02" in str(m) for m in months)
    assert abs(result["Umsatz"][0] - 10000.0) < 0.01


def test_zeitreihe_excludes_jeb_entries(tmp_path):
    """JEB (Jahresabschluss) entries must be excluded from the time series."""
    rows = [
        # Regular booking in March
        "1,1,RE001,15.03.2024,15.03.2024,Umsatz,1810,Soll,8000\n",
        "2,1,RE001,15.03.2024,15.03.2024,Umsatz,4400,Haben,8000\n",
        # JEB closing entries (year-end) — must be excluded
        "3,2,JEB2024,31.12.2024,31.12.2024,Jahresabschluss GuV,4400,Soll,8000\n",
        "4,2,JEB2024,31.12.2024,31.12.2024,Jahresabschluss GuV,9000,Haben,8000\n",
    ]
    journal = write_journal(tmp_path, rows)
    result = zeitreihe(journal, KONTEN_FILE, START, ENDE)
    # Only March should appear; December JEB must not create a row or inflate values
    assert result.height == 1
    assert abs(result["Umsatz"][0] - 8000.0) < 0.01


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------


def test_cli_zeitreihe_outputs_csv(capsys):
    main(["zeitreihe", fixture_path("22_full_year_monthly.csv"),
          "--start", START, "--ende", ENDE])
    output = capsys.readouterr().out
    assert "Monat" in output
    assert "Umsatz" in output
    assert "Aufwand" in output
    assert "Ergebnis" in output
    assert "Anzahl_Buchungen" in output


def test_cli_zeitreihe_parseable_csv(capsys):
    """CLI output must be valid CSV that can be parsed by polars."""
    main(["zeitreihe", fixture_path("22_full_year_monthly.csv"),
          "--start", START, "--ende", ENDE])
    output = capsys.readouterr().out
    df = pl.read_csv(io.StringIO(output))
    assert df.height == 12
    for col in EXPECTED_COLUMNS:
        assert col in df.columns


def test_cli_zeitreihe_single_month(capsys):
    main(["zeitreihe", fixture_path("01_simple_profit.csv"),
          "--start", START, "--ende", ENDE])
    output = capsys.readouterr().out
    df = pl.read_csv(io.StringIO(output))
    assert df.height == 1
    assert df["Umsatz"][0] > 0


def test_cli_zeitreihe_requires_start_and_ende():
    with pytest.raises(SystemExit, match="2"):
        main(["zeitreihe", fixture_path("01_simple_profit.csv")])
