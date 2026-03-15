"""Tests for DATEV EXTF Buchungsstapel exporter."""

import pytest

from src.datev import datev_export
from tests.conftest import fixture_path, KONTEN_FILE

START = "2024-01-01"
ENDE = "2024-12-31"

JOURNAL_SIMPLE = fixture_path("01_simple_profit.csv")
JOURNAL_VAT = fixture_path("10_with_vat.csv")
JOURNAL_VAT_EXPENSE = fixture_path("11_with_vat_and_expense.csv")
JOURNAL_WITH_JAB = fixture_path("15_with_gewinnvortrag.csv")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _unquote(val: str) -> str:
    """Strip surrounding DATEV quotes."""
    if val.startswith('"') and val.endswith('"'):
        return val[1:-1]
    return val


def parse_output(output: str) -> tuple[str, str, list[list[str]]]:
    """Split DATEV output into header line, column line, and data rows.

    Text fields are unquoted for easier assertions.
    """
    lines = output.splitlines()
    assert len(lines) >= 2
    header = lines[0]
    columns = lines[1]
    data = [
        [_unquote(f) for f in line.split(";")]
        for line in lines[2:] if line.strip()
    ]
    return header, columns, data


# ---------------------------------------------------------------------------
# 1. Header format
# ---------------------------------------------------------------------------

def test_header_starts_with_extf():
    out = datev_export(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE)
    header, _, _ = parse_output(out)
    assert header.startswith('"EXTF"')


def test_header_is_semicolon_separated():
    out = datev_export(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE)
    header, _, _ = parse_output(out)
    fields = header.split(";")
    assert len(fields) == 31


def test_header_format_code_is_700():
    out = datev_export(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE)
    header, _, _ = parse_output(out)
    fields = header.split(";")
    assert fields[1] == "700"


def test_header_data_category_is_21():
    out = datev_export(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE)
    header, _, _ = parse_output(out)
    fields = header.split(";")
    assert fields[2] == "21"


def test_header_contains_berater_and_mandanten_nr():
    out = datev_export(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE,
                       berater_nr=1234, mandanten_nr=5678)
    header, _, _ = parse_output(out)
    fields = header.split(";")
    assert fields[10] == "1234"
    assert fields[11] == "5678"


def test_header_wirtschaftsjahr_start_present():
    out = datev_export(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE)
    header, _, _ = parse_output(out)
    fields = header.split(";")
    assert fields[12] == "20240101"


# ---------------------------------------------------------------------------
# 2. Column headers line
# ---------------------------------------------------------------------------

def test_column_line_has_umsatz_and_sh_kennzeichen():
    out = datev_export(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE)
    _, columns, _ = parse_output(out)
    assert "Umsatz" in columns
    assert "Soll/Haben-Kennzeichen" in columns


def test_output_has_at_least_116_columns():
    out = datev_export(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE)
    _, columns, _ = parse_output(out)
    assert len(columns.split(";")) >= 116


# ---------------------------------------------------------------------------
# 3. Simple 1:1 booking (01_simple_profit.csv)
# ---------------------------------------------------------------------------

def test_simple_booking_produces_one_data_row():
    out = datev_export(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE)
    _, _, data = parse_output(out)
    assert len(data) == 1


def test_simple_booking_sh_kennzeichen_is_s():
    out = datev_export(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE)
    _, _, data = parse_output(out)
    assert data[0][1] == "S"


def test_simple_booking_konto_is_soll_account():
    out = datev_export(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE)
    _, _, data = parse_output(out)
    assert data[0][6] == "1810"


def test_simple_booking_gegenkonto_is_haben_account():
    out = datev_export(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE)
    _, _, data = parse_output(out)
    assert data[0][7] == "4400"


def test_simple_booking_umsatz_is_correct():
    out = datev_export(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE)
    _, _, data = parse_output(out)
    assert data[0][0] == "10000,00"


def test_simple_booking_wkz_is_eur():
    out = datev_export(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE)
    _, _, data = parse_output(out)
    assert data[0][2] == "EUR"


# ---------------------------------------------------------------------------
# 4. Compound booking with VAT / 1:N (10_with_vat.csv)
# ---------------------------------------------------------------------------

def test_vat_booking_produces_two_data_rows():
    out = datev_export(JOURNAL_VAT, KONTEN_FILE, START, ENDE)
    _, _, data = parse_output(out)
    assert len(data) == 2


def test_vat_booking_konto_is_soll_account_for_all_rows():
    out = datev_export(JOURNAL_VAT, KONTEN_FILE, START, ENDE)
    _, _, data = parse_output(out)
    for row in data:
        assert row[6] == "1810"


def test_vat_booking_gegenkonten_are_haben_accounts():
    out = datev_export(JOURNAL_VAT, KONTEN_FILE, START, ENDE)
    _, _, data = parse_output(out)
    gegenkonten = {row[7] for row in data}
    assert "4400" in gegenkonten
    assert "3806" in gegenkonten


def test_vat_booking_amounts_match_haben_entries():
    out = datev_export(JOURNAL_VAT, KONTEN_FILE, START, ENDE)
    _, _, data = parse_output(out)
    amounts = {row[7]: row[0] for row in data}
    assert amounts["4400"] == "10000,00"
    assert amounts["3806"] == "1900,00"


def test_vat_booking_all_sh_kennzeichen_are_s():
    out = datev_export(JOURNAL_VAT, KONTEN_FILE, START, ENDE)
    _, _, data = parse_output(out)
    for row in data:
        assert row[1] == "S"


# ---------------------------------------------------------------------------
# 5. Compound booking with Vorsteuer / N:1 (11_with_vat_and_expense.csv)
# ---------------------------------------------------------------------------

def test_expense_booking_n_to_1_produces_four_rows():
    """Buchungssatz 1: 2 rows (1:N), Buchungssatz 2: 2 rows (N:1) = 4 total."""
    out = datev_export(JOURNAL_VAT_EXPENSE, KONTEN_FILE, START, ENDE)
    _, _, data = parse_output(out)
    assert len(data) == 4


def test_expense_booking_gegenkonto_is_haben_account():
    out = datev_export(JOURNAL_VAT_EXPENSE, KONTEN_FILE, START, ENDE)
    _, _, data = parse_output(out)
    expense_rows = [row for row in data if row[6] in ("6837", "1406")]
    assert len(expense_rows) == 2
    for row in expense_rows:
        assert row[7] == "1810"


def test_expense_booking_amounts_match_soll_entries():
    out = datev_export(JOURNAL_VAT_EXPENSE, KONTEN_FILE, START, ENDE)
    _, _, data = parse_output(out)
    expense_rows = {row[6]: row[0] for row in data if row[6] in ("6837", "1406")}
    assert expense_rows["6837"] == "500,00"
    assert expense_rows["1406"] == "95,00"


# ---------------------------------------------------------------------------
# 6. Date format: DD.MM.YYYY → DDMM
# ---------------------------------------------------------------------------

def test_belegdatum_format_is_ddmm():
    out = datev_export(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE)
    _, _, data = parse_output(out)
    assert data[0][9] == "0101"


def test_belegdatum_for_mid_month_date():
    out = datev_export(JOURNAL_VAT, KONTEN_FILE, START, ENDE)
    _, _, data = parse_output(out)
    for row in data:
        assert row[9] == "1501"


# ---------------------------------------------------------------------------
# 7. Amount formatting
# ---------------------------------------------------------------------------

def test_amount_uses_comma_decimal_separator():
    out = datev_export(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE)
    _, _, data = parse_output(out)
    umsatz = data[0][0]
    assert "," in umsatz
    assert "." not in umsatz


def test_amount_two_decimal_places():
    out = datev_export(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE)
    _, _, data = parse_output(out)
    decimal_part = data[0][0].split(",")[1]
    assert len(decimal_part) == 2


def test_fractional_amount_formatted_correctly():
    out = datev_export(JOURNAL_VAT_EXPENSE, KONTEN_FILE, START, ENDE)
    _, _, data = parse_output(out)
    vst_row = next(row for row in data if row[6] == "1406")
    assert vst_row[0] == "95,00"


# ---------------------------------------------------------------------------
# 8. Belegnummer in Belegfeld 1
# ---------------------------------------------------------------------------

def test_belegfeld1_contains_belegnummer():
    out = datev_export(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE)
    _, _, data = parse_output(out)
    assert data[0][10] == "RE001"


def test_belegfeld1_for_second_document():
    out = datev_export(JOURNAL_VAT_EXPENSE, KONTEN_FILE, START, ENDE)
    _, _, data = parse_output(out)
    expense_rows = [row for row in data if row[6] in ("6837", "1406")]
    for row in expense_rows:
        assert row[10] == "RE002"


# ---------------------------------------------------------------------------
# 9. Buchungstext
# ---------------------------------------------------------------------------

def test_buchungstext_present():
    out = datev_export(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE)
    _, _, data = parse_output(out)
    assert data[0][13] != ""


def test_buchungstext_truncated_to_60_chars(tmp_path):
    long_text = "A" * 80
    journal_path = tmp_path / "journal.csv"
    journal_path.write_text(
        "Journalnummer,Buchungssatznummer,Belegnummer,Belegdatum,Buchungsdatum,"
        "Buchungstext,Konto,Typ,Betrag\n"
        f"1,1,RE001,01.03.2024,01.03.2024,{long_text},1810,Soll,1000\n"
        f"2,1,RE001,01.03.2024,01.03.2024,{long_text},4400,Haben,1000\n"
    )
    out = datev_export(str(journal_path), KONTEN_FILE, START, ENDE)
    _, _, data = parse_output(out)
    assert len(data[0][13]) <= 60


# ---------------------------------------------------------------------------
# 10. Encoding
# ---------------------------------------------------------------------------

def test_output_is_string():
    result = datev_export(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE)
    assert isinstance(result, str)


def test_records_are_semicolon_separated():
    out = datev_export(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE)
    _, _, data = parse_output(out)
    assert len(data[0]) > 1


def test_no_tab_characters_in_output():
    out = datev_export(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE)
    assert "\t" not in out


# ---------------------------------------------------------------------------
# 11. Sachkontenlänge detection
# ---------------------------------------------------------------------------

def test_sachkontenlaenge_4_for_standard_skr04():
    out = datev_export(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE)
    header, _, _ = parse_output(out)
    fields = header.split(";")
    assert fields[13] == "4"


def test_sachkontenlaenge_5_for_5digit_accounts(tmp_path):
    journal_path = tmp_path / "journal.csv"
    journal_path.write_text(
        "Journalnummer,Buchungssatznummer,Belegnummer,Belegdatum,Buchungsdatum,"
        "Buchungstext,Konto,Typ,Betrag\n"
        "1,1,RE001,10.04.2024,10.04.2024,Umsatz,18100,Soll,5000\n"
        "2,1,RE001,10.04.2024,10.04.2024,Umsatz,44000,Haben,5000\n"
    )
    out = datev_export(str(journal_path), KONTEN_FILE, START, ENDE)
    header, _, _ = parse_output(out)
    fields = header.split(";")
    assert fields[13] == "5"


# ---------------------------------------------------------------------------
# 12. Internal accounts filtered out
# ---------------------------------------------------------------------------

def test_internal_account_00000_excluded(tmp_path):
    journal_path = tmp_path / "journal.csv"
    journal_path.write_text(
        "Journalnummer,Buchungssatznummer,Belegnummer,Belegdatum,Buchungsdatum,"
        "Buchungstext,Konto,Typ,Betrag\n"
        "1,1,JEB2024,01.01.2024,01.01.2024,Jahreseroeffnung,00000,Soll,10000\n"
        "2,1,JEB2024,01.01.2024,01.01.2024,Jahreseroeffnung,1810,Haben,10000\n"
        "3,2,RE001,15.03.2024,15.03.2024,Umsatz,1810,Soll,5000\n"
        "4,2,RE001,15.03.2024,15.03.2024,Umsatz,4400,Haben,5000\n"
    )
    out = datev_export(str(journal_path), KONTEN_FILE, START, ENDE)
    _, _, data = parse_output(out)
    konten_in_output = {row[6] for row in data} | {row[7] for row in data}
    assert "00000" not in konten_in_output


def test_internal_account_9000_excluded():
    out = datev_export(JOURNAL_WITH_JAB, KONTEN_FILE, START, ENDE)
    _, _, data = parse_output(out)
    konten_in_output = {row[6] for row in data} | {row[7] for row in data}
    assert "9000" not in konten_in_output


def test_regular_bookings_after_jab_are_exported():
    out = datev_export(JOURNAL_WITH_JAB, KONTEN_FILE, START, ENDE)
    _, _, data = parse_output(out)
    konten_in_output = {row[6] for row in data}
    assert "1810" in konten_in_output


def test_only_internal_accounts_produces_empty_output(tmp_path):
    journal_path = tmp_path / "journal.csv"
    journal_path.write_text(
        "Journalnummer,Buchungssatznummer,Belegnummer,Belegdatum,Buchungsdatum,"
        "Buchungstext,Konto,Typ,Betrag\n"
        "1,1,JEB2024,01.01.2024,01.01.2024,Eroeffnung,00000,Soll,1000\n"
        "2,1,JEB2024,01.01.2024,01.01.2024,Eroeffnung,9000,Haben,1000\n"
    )
    out = datev_export(str(journal_path), KONTEN_FILE, START, ENDE)
    _, _, data = parse_output(out)
    assert data == []


# ---------------------------------------------------------------------------
# 13. Date range filtering
# ---------------------------------------------------------------------------

def test_mn_booking_no_zero_amounts(tmp_path):
    """M:N booking with same account on both sides must not produce 0,00 rows."""
    journal_path = tmp_path / "journal.csv"
    journal_path.write_text(
        "Journalnummer,Buchungssatznummer,Belegnummer,Belegdatum,Buchungsdatum,"
        "Buchungstext,Konto,Typ,Betrag\n"
        "1,1,S21,01.12.2024,01.12.2024,USt-Voranmeldung,3806,Soll,2617.25\n"
        "2,1,S21,01.12.2024,01.12.2024,USt-Voranmeldung,3820,Haben,2617.25\n"
        "3,1,S21,01.12.2024,01.12.2024,USt-Voranmeldung,3820,Soll,2.33\n"
        "4,1,S21,01.12.2024,01.12.2024,USt-Voranmeldung,1406,Haben,2.33\n"
    )
    out = datev_export(str(journal_path), KONTEN_FILE, START, ENDE)
    _, _, data = parse_output(out)
    amounts = [row[0] for row in data]
    assert "0,00" not in amounts
    assert len(data) == 2


def test_mn_booking_pairs_matching_amounts(tmp_path):
    """M:N booking pairs entries with matching amounts correctly."""
    journal_path = tmp_path / "journal.csv"
    journal_path.write_text(
        "Journalnummer,Buchungssatznummer,Belegnummer,Belegdatum,Buchungsdatum,"
        "Buchungstext,Konto,Typ,Betrag\n"
        "1,1,S21,01.12.2024,01.12.2024,USt-Voranmeldung,3806,Soll,2617.25\n"
        "2,1,S21,01.12.2024,01.12.2024,USt-Voranmeldung,3820,Haben,2617.25\n"
        "3,1,S21,01.12.2024,01.12.2024,USt-Voranmeldung,3820,Soll,2.33\n"
        "4,1,S21,01.12.2024,01.12.2024,USt-Voranmeldung,1406,Haben,2.33\n"
    )
    out = datev_export(str(journal_path), KONTEN_FILE, START, ENDE)
    _, _, data = parse_output(out)
    pairs = {(row[6], row[7]): row[0] for row in data}
    assert pairs[("3806", "3820")] == "2617,25"
    assert pairs[("3820", "1406")] == "2,33"


def test_bookings_outside_date_range_excluded(tmp_path):
    journal_path = tmp_path / "journal.csv"
    journal_path.write_text(
        "Journalnummer,Buchungssatznummer,Belegnummer,Belegdatum,Buchungsdatum,"
        "Buchungstext,Konto,Typ,Betrag\n"
        "1,1,RE001,15.06.2023,15.06.2023,Vorjahr,1810,Soll,1000\n"
        "2,1,RE001,15.06.2023,15.06.2023,Vorjahr,4400,Haben,1000\n"
        "3,2,RE002,15.06.2024,15.06.2024,Aktuell,1810,Soll,2000\n"
        "4,2,RE002,15.06.2024,15.06.2024,Aktuell,4400,Haben,2000\n"
    )
    out = datev_export(str(journal_path), KONTEN_FILE, START, ENDE)
    _, _, data = parse_output(out)
    assert len(data) == 1
    assert data[0][0] == "2000,00"
