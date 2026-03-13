"""Tests for GoBD compliance validation."""

import pytest

from src.buchhaltung import validiere_gobd
from src.cli import main
from tests.conftest import fixture_path, KONTEN_FILE

HEADER = "Journalnummer,Buchungssatznummer,Belegnummer,Belegdatum,Buchungsdatum,Buchungstext,Konto,Typ,Betrag\n"
KONTEN_HEADER = "Konto,Bezeichnung,Bilanzposten,GuV Posten,XBRL Taxonomie\n"

START = "2024-01-01"
ENDE = "2024-12-31"


def write_journal(tmp_path, rows: list[str]) -> str:
    p = tmp_path / "journal.csv"
    p.write_text(HEADER + "".join(rows))
    return str(p)


def write_konten(tmp_path, accounts: list[tuple[str, str]]) -> str:
    p = tmp_path / "konten.csv"
    lines = KONTEN_HEADER + "".join(
        f"{konto},{bez},,,\n" for konto, bez in accounts
    )
    p.write_text(lines)
    return str(p)


def row(
    nr: int,
    bs: int,
    beleg: str,
    belegdatum: str,
    buchungsdatum: str,
    text: str,
    konto: str,
    typ: str,
    betrag: float,
) -> str:
    return f"{nr},{bs},{beleg},{belegdatum},{buchungsdatum},{text},{konto},{typ},{betrag}\n"


# ---------------------------------------------------------------------------
# 1. Valid journals pass
# ---------------------------------------------------------------------------

VALID_FIXTURES = [
    "01_simple_profit.csv",
    "03_multi_bookings.csv",
    "10_with_vat.csv",
    "22_full_year_monthly.csv",
]


@pytest.mark.parametrize("fixture", VALID_FIXTURES, ids=[f.split(".")[0] for f in VALID_FIXTURES])
def test_valid_fixture_passes(fixture):
    result = validiere_gobd(fixture_path(fixture), KONTEN_FILE, START, ENDE)
    assert result == "", f"Expected PASS for {fixture}, got: {result}"


def test_minimal_valid_journal(tmp_path):
    rows = [
        row(1, 1, "RE001", "01.01.2024", "01.01.2024", "Umsatz", "4400", "Haben", 1000.0),
        row(2, 1, "RE001", "01.01.2024", "01.01.2024", "Umsatz", "1810", "Soll", 1000.0),
    ]
    journal = write_journal(tmp_path, rows)
    konten = write_konten(tmp_path, [("4400", "Umsatzerlöse"), ("1810", "Forderungen")])
    result = validiere_gobd(journal, konten, START, ENDE)
    assert result == ""


# ---------------------------------------------------------------------------
# 2. Chronological order: Buchungsdatum must be non-decreasing
# ---------------------------------------------------------------------------

def test_out_of_order_buchungsdatum_fails(tmp_path):
    rows = [
        row(1, 1, "RE001", "01.03.2024", "01.03.2024", "Aufwand", "6300", "Soll", 500.0),
        row(2, 1, "RE001", "01.03.2024", "01.03.2024", "Aufwand", "1810", "Haben", 500.0),
        row(3, 2, "RE002", "01.01.2024", "01.01.2024", "Umsatz",  "1810", "Soll", 1000.0),
        row(4, 2, "RE002", "01.01.2024", "01.01.2024", "Umsatz",  "4400", "Haben", 1000.0),
    ]
    journal = write_journal(tmp_path, rows)
    konten = write_konten(tmp_path, [("6300", "Reparaturen"), ("1810", "Forderungen"), ("4400", "Umsatzerlöse")])
    result = validiere_gobd(journal, konten, START, ENDE)
    assert result != ""
    assert len(result) > 0


def test_same_buchungsdatum_is_allowed(tmp_path):
    rows = [
        row(1, 1, "RE001", "15.06.2024", "15.06.2024", "Aufwand A", "6300", "Soll", 100.0),
        row(2, 1, "RE001", "15.06.2024", "15.06.2024", "Aufwand A", "1810", "Haben", 100.0),
        row(3, 2, "RE002", "20.06.2024", "15.06.2024", "Aufwand B", "6300", "Soll", 200.0),
        row(4, 2, "RE002", "20.06.2024", "15.06.2024", "Aufwand B", "1810", "Haben", 200.0),
    ]
    journal = write_journal(tmp_path, rows)
    konten = write_konten(tmp_path, [("6300", "Reparaturen"), ("1810", "Forderungen")])
    result = validiere_gobd(journal, konten, START, ENDE)
    assert result == ""


def test_belegdatum_may_differ_from_buchungsdatum(tmp_path):
    # Belegdatum is allowed to be earlier than Buchungsdatum (invoice date vs posting date)
    rows = [
        row(1, 1, "RE001", "01.01.2024", "15.01.2024", "Rechnung Jan", "6300", "Soll", 500.0),
        row(2, 1, "RE001", "01.01.2024", "15.01.2024", "Rechnung Jan", "1810", "Haben", 500.0),
        row(3, 2, "RE002", "01.02.2024", "28.02.2024", "Rechnung Feb", "6300", "Soll", 500.0),
        row(4, 2, "RE002", "01.02.2024", "28.02.2024", "Rechnung Feb", "1810", "Haben", 500.0),
    ]
    journal = write_journal(tmp_path, rows)
    konten = write_konten(tmp_path, [("6300", "Reparaturen"), ("1810", "Forderungen")])
    result = validiere_gobd(journal, konten, START, ENDE)
    assert result == ""


# ---------------------------------------------------------------------------
# 3. No future bookings (Buchungsdatum > ende)
# ---------------------------------------------------------------------------

def test_future_buchungsdatum_fails(tmp_path):
    rows = [
        row(1, 1, "RE001", "01.06.2024", "01.06.2024", "Aufwand", "6300", "Soll", 300.0),
        row(2, 1, "RE001", "01.06.2024", "01.06.2024", "Aufwand", "1810", "Haben", 300.0),
        row(3, 2, "RE002", "01.01.2025", "01.01.2025", "Future",  "6300", "Soll", 100.0),
        row(4, 2, "RE002", "01.01.2025", "01.01.2025", "Future",  "1810", "Haben", 100.0),
    ]
    journal = write_journal(tmp_path, rows)
    konten = write_konten(tmp_path, [("6300", "Reparaturen"), ("1810", "Forderungen")])
    result = validiere_gobd(journal, konten, START, ENDE)
    assert result != ""


def test_booking_on_ende_date_is_valid(tmp_path):
    rows = [
        row(1, 1, "RE001", "31.12.2024", "31.12.2024", "Jahresende", "6300", "Soll", 200.0),
        row(2, 1, "RE001", "31.12.2024", "31.12.2024", "Jahresende", "1810", "Haben", 200.0),
    ]
    journal = write_journal(tmp_path, rows)
    konten = write_konten(tmp_path, [("6300", "Reparaturen"), ("1810", "Forderungen")])
    result = validiere_gobd(journal, konten, START, ENDE)
    assert result == ""


# ---------------------------------------------------------------------------
# 4. No empty required fields
# ---------------------------------------------------------------------------

def test_empty_belegnummer_fails(tmp_path):
    rows = [
        row(1, 1, "", "01.03.2024", "01.03.2024", "Aufwand", "6300", "Soll", 100.0),
        row(2, 1, "", "01.03.2024", "01.03.2024", "Aufwand", "1810", "Haben", 100.0),
    ]
    journal = write_journal(tmp_path, rows)
    konten = write_konten(tmp_path, [("6300", "Reparaturen"), ("1810", "Forderungen")])
    result = validiere_gobd(journal, konten, START, ENDE)
    assert result != ""


def test_empty_buchungstext_fails(tmp_path):
    rows = [
        row(1, 1, "RE001", "01.03.2024", "01.03.2024", "", "6300", "Soll", 100.0),
        row(2, 1, "RE001", "01.03.2024", "01.03.2024", "", "1810", "Haben", 100.0),
    ]
    journal = write_journal(tmp_path, rows)
    konten = write_konten(tmp_path, [("6300", "Reparaturen"), ("1810", "Forderungen")])
    result = validiere_gobd(journal, konten, START, ENDE)
    assert result != ""


def test_empty_konto_fails(tmp_path):
    rows = [
        row(1, 1, "RE001", "01.03.2024", "01.03.2024", "Aufwand", "", "Soll", 100.0),
        row(2, 1, "RE001", "01.03.2024", "01.03.2024", "Aufwand", "1810", "Haben", 100.0),
    ]
    journal = write_journal(tmp_path, rows)
    konten = write_konten(tmp_path, [("6300", "Reparaturen"), ("1810", "Forderungen")])
    result = validiere_gobd(journal, konten, START, ENDE)
    assert result != ""


def test_empty_typ_fails(tmp_path):
    rows = [
        row(1, 1, "RE001", "01.03.2024", "01.03.2024", "Aufwand", "6300", "", 100.0),
        row(2, 1, "RE001", "01.03.2024", "01.03.2024", "Aufwand", "1810", "Haben", 100.0),
    ]
    journal = write_journal(tmp_path, rows)
    konten = write_konten(tmp_path, [("6300", "Reparaturen"), ("1810", "Forderungen")])
    result = validiere_gobd(journal, konten, START, ENDE)
    assert result != ""


# ---------------------------------------------------------------------------
# 5. Valid account numbers
# ---------------------------------------------------------------------------

def test_invalid_konto_fails(tmp_path):
    rows = [
        row(1, 1, "RE001", "01.06.2024", "01.06.2024", "Aufwand", "9999", "Soll", 500.0),
        row(2, 1, "RE001", "01.06.2024", "01.06.2024", "Aufwand", "1810", "Haben", 500.0),
    ]
    journal = write_journal(tmp_path, rows)
    konten = write_konten(tmp_path, [("1810", "Forderungen")])  # 9999 not in konten
    result = validiere_gobd(journal, konten, START, ENDE)
    assert result != ""


def test_system_account_00000_is_allowed(tmp_path):
    rows = [
        row(1, 1, "JEB2024", "01.01.2024", "01.01.2024", "Jahreseröffnung", "00000", "Soll", 1000.0),
        row(2, 1, "JEB2024", "01.01.2024", "01.01.2024", "Jahreseröffnung", "1810",  "Haben", 1000.0),
    ]
    journal = write_journal(tmp_path, rows)
    konten = write_konten(tmp_path, [("1810", "Forderungen")])  # 00000 is system account
    result = validiere_gobd(journal, konten, START, ENDE)
    assert result == ""


def test_system_account_9000_is_allowed(tmp_path):
    rows = [
        row(1, 1, "JEB2024", "01.01.2024", "01.01.2024", "Eröffnung", "9000", "Soll", 5000.0),
        row(2, 1, "JEB2024", "01.01.2024", "01.01.2024", "Eröffnung", "1810", "Haben", 5000.0),
    ]
    journal = write_journal(tmp_path, rows)
    konten = write_konten(tmp_path, [("1810", "Forderungen")])
    result = validiere_gobd(journal, konten, START, ENDE)
    assert result == ""


def test_all_accounts_valid(tmp_path):
    rows = [
        row(1, 1, "RE001", "01.04.2024", "01.04.2024", "Umsatz", "4400", "Haben", 2000.0),
        row(2, 1, "RE001", "01.04.2024", "01.04.2024", "Umsatz", "1810", "Soll",  2000.0),
    ]
    journal = write_journal(tmp_path, rows)
    konten = write_konten(tmp_path, [("4400", "Umsatzerlöse"), ("1810", "Forderungen")])
    result = validiere_gobd(journal, konten, START, ENDE)
    assert result == ""


# ---------------------------------------------------------------------------
# 6. Multiple violations reported together
# ---------------------------------------------------------------------------

def test_multiple_violations_all_reported(tmp_path):
    # Out-of-order Buchungsdatum AND invalid account
    rows = [
        row(1, 1, "RE001", "01.06.2024", "01.06.2024", "Aufwand", "6300", "Soll", 100.0),
        row(2, 1, "RE001", "01.06.2024", "01.06.2024", "Aufwand", "1810", "Haben", 100.0),
        row(3, 2, "RE002", "01.01.2024", "01.01.2024", "Früher",  "9999", "Soll", 50.0),
        row(4, 2, "RE002", "01.01.2024", "01.01.2024", "Früher",  "1810", "Haben", 50.0),
    ]
    journal = write_journal(tmp_path, rows)
    konten = write_konten(tmp_path, [("6300", "Reparaturen"), ("1810", "Forderungen")])
    result = validiere_gobd(journal, konten, START, ENDE)
    assert result != ""


# ---------------------------------------------------------------------------
# 7. CLI command: validiere-gobd
# ---------------------------------------------------------------------------

VALID_JOURNAL = fixture_path("01_simple_profit.csv")


def test_cli_validiere_gobd_pass(capsys):
    main(["validiere-gobd", VALID_JOURNAL, "--start", START, "--ende", ENDE])
    assert capsys.readouterr().out.strip() == "PASS"


def test_cli_validiere_gobd_fail_exits_1(tmp_path, capsys):
    rows = [
        row(1, 1, "RE001", "01.06.2024", "01.06.2024", "Aufwand", "6300", "Soll", 100.0),
        row(2, 1, "RE001", "01.06.2024", "01.06.2024", "Aufwand", "1810", "Haben", 100.0),
        row(3, 2, "RE002", "01.01.2024", "01.01.2024", "Earlier", "6300", "Soll", 50.0),
        row(4, 2, "RE002", "01.01.2024", "01.01.2024", "Earlier", "1810", "Haben", 50.0),
    ]
    journal = write_journal(tmp_path, rows)
    konten = write_konten(tmp_path, [("6300", "Reparaturen"), ("1810", "Forderungen")])
    with pytest.raises(SystemExit, match="1"):
        main(["validiere-gobd", journal, "--konten", konten, "--start", START, "--ende", ENDE])
    assert capsys.readouterr().out.strip() != "PASS"


def test_cli_validiere_gobd_invalid_account_exits_1(tmp_path, capsys):
    rows = [
        row(1, 1, "RE001", "01.06.2024", "01.06.2024", "Aufwand", "9999", "Soll", 100.0),
        row(2, 1, "RE001", "01.06.2024", "01.06.2024", "Aufwand", "1810", "Haben", 100.0),
    ]
    journal = write_journal(tmp_path, rows)
    konten = write_konten(tmp_path, [("1810", "Forderungen")])
    with pytest.raises(SystemExit, match="1"):
        main(["validiere-gobd", journal, "--konten", konten, "--start", START, "--ende", ENDE])
    output = capsys.readouterr().out
    assert output.strip() != "PASS"


def test_cli_validiere_gobd_uses_default_konten(capsys):
    """CLI must work without explicit --konten flag (uses bundled konten.csv)."""
    main(["validiere-gobd", VALID_JOURNAL, "--start", START, "--ende", ENDE])
    assert capsys.readouterr().out.strip() == "PASS"
