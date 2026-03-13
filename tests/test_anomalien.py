"""Tests for anomalien: duplicate, outlier, and gap detection."""

import pytest
import polars as pl

from src.buchhaltung import anomalien

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


def journal_row(
    nr: int,
    beleg: str,
    datum: str,
    text: str,
    konto: str,
    typ: str,
    betrag: float,
) -> str:
    return f"{nr},1,{beleg},{datum},{datum},{text},{konto},{typ},{betrag}\n"


# ---------------------------------------------------------------------------


def test_clean_journal_returns_empty(tmp_path):
    rows = [
        journal_row(1, "RE001", "01.01.2024", "Miete Jan", "6310", "Soll", 1000.0),
        journal_row(2, "RE001", "01.01.2024", "Miete Jan", "1200", "Haben", 1000.0),
    ]
    journal = write_journal(tmp_path, rows)
    konten = write_konten(tmp_path, [("6310", "Mietaufwand"), ("1200", "Bank")])

    result = anomalien(journal, konten, START, ENDE)

    assert isinstance(result, pl.DataFrame)
    assert result.is_empty()
    assert result.columns == ["Typ", "Konto", "Bezeichnung", "Belegdatum", "Buchungstext", "Betrag", "Detail"]


def test_duplicate_detection(tmp_path):
    # Two identical Soll rows for 6800 → one duplicate finding for that account.
    # The Haben counterpart on 1200 also duplicates; both are correctly flagged.
    rows = [
        journal_row(1, "RE001", "15.03.2024", "Softwarelizenz", "6800", "Soll", 500.0),
        journal_row(2, "RE002", "15.03.2024", "Softwarelizenz", "6800", "Soll", 500.0),
        journal_row(3, "RE001", "15.03.2024", "Softwarelizenz", "1200", "Haben", 500.0),
        journal_row(4, "RE002", "15.03.2024", "Softwarelizenz", "1200", "Haben", 500.0),
    ]
    journal = write_journal(tmp_path, rows)
    konten = write_konten(tmp_path, [("6800", "EDV-Aufwand"), ("1200", "Bank")])

    result = anomalien(journal, konten, START, ENDE)

    dupes = result.filter(pl.col("Typ") == "Duplikat")
    # Both the Soll (6800) and the Haben (1200) sides are independently flagged
    assert len(dupes) == 2
    konten_flagged = set(dupes["Konto"].to_list())
    assert konten_flagged == {"6800", "1200"}
    for row in dupes.iter_rows(named=True):
        assert row["Betrag"] == 500.0
        assert "2×" in row["Detail"]


def test_duplicate_different_amounts_not_flagged(tmp_path):
    rows = [
        journal_row(1, "RE001", "15.03.2024", "Telefon", "6805", "Soll", 100.0),
        journal_row(2, "RE002", "15.03.2024", "Telefon", "6805", "Soll", 120.0),
    ]
    journal = write_journal(tmp_path, rows)
    konten = write_konten(tmp_path, [("6805", "Telefonkosten")])

    result = anomalien(journal, konten, START, ENDE)

    assert result.filter(pl.col("Typ") == "Duplikat").is_empty()


def test_outlier_detection(tmp_path):
    # Five Soll bookings on same konto+text; one is far above the rest.
    # Normal values: 100, 105, 95, 98 → median ~99.5, IQR small
    # Outlier: 5000 → well beyond q3 + 2*IQR
    rows = [
        journal_row(1, "RE001", "05.01.2024", "Bürobedarf", "6815", "Soll", 100.0),
        journal_row(2, "RE002", "05.02.2024", "Bürobedarf", "6815", "Soll", 105.0),
        journal_row(3, "RE003", "05.03.2024", "Bürobedarf", "6815", "Soll", 95.0),
        journal_row(4, "RE004", "05.04.2024", "Bürobedarf", "6815", "Soll", 98.0),
        journal_row(5, "RE005", "05.05.2024", "Bürobedarf", "6815", "Soll", 5000.0),
    ]
    journal = write_journal(tmp_path, rows)
    konten = write_konten(tmp_path, [("6815", "Bürobedarf")])

    result = anomalien(journal, konten, START, ENDE)

    outliers = result.filter(pl.col("Typ") == "Ausreißer")
    assert len(outliers) == 1
    row = outliers.row(0, named=True)
    assert row["Konto"] == "6815"
    assert row["Betrag"] == 5000.0
    assert "Median" in row["Detail"]
    assert "IQR" in row["Detail"]


def test_outlier_needs_four_bookings(tmp_path):
    # Only 3 bookings — outlier check must not trigger even if one value is extreme
    rows = [
        journal_row(1, "RE001", "05.01.2024", "Porto", "6820", "Soll", 10.0),
        journal_row(2, "RE002", "05.02.2024", "Porto", "6820", "Soll", 12.0),
        journal_row(3, "RE003", "05.03.2024", "Porto", "6820", "Soll", 9999.0),
    ]
    journal = write_journal(tmp_path, rows)
    konten = write_konten(tmp_path, [("6820", "Porto")])

    result = anomalien(journal, konten, START, ENDE)

    assert result.filter(pl.col("Typ") == "Ausreißer").is_empty()


def test_outlier_only_for_soll_bookings(tmp_path):
    # Extreme Haben booking — must not be flagged as outlier
    rows = [
        journal_row(1, "RE001", "05.01.2024", "Umsatz", "4400", "Haben", 100.0),
        journal_row(2, "RE002", "05.02.2024", "Umsatz", "4400", "Haben", 105.0),
        journal_row(3, "RE003", "05.03.2024", "Umsatz", "4400", "Haben", 95.0),
        journal_row(4, "RE004", "05.04.2024", "Umsatz", "4400", "Haben", 98.0),
        journal_row(5, "RE005", "05.05.2024", "Umsatz", "4400", "Haben", 50000.0),
    ]
    journal = write_journal(tmp_path, rows)
    konten = write_konten(tmp_path, [("4400", "Umsatzerlöse")])

    result = anomalien(journal, konten, START, ENDE)

    assert result.filter(pl.col("Typ") == "Ausreißer").is_empty()


def test_gap_detection(tmp_path):
    # Monthly Soll bookings Jan–Apr, June–Dec → May missing
    months = [
        ("01", "Jan"), ("02", "Feb"), ("03", "Mär"), ("04", "Apr"),
        # May intentionally absent
        ("06", "Jun"), ("07", "Jul"), ("08", "Aug"), ("09", "Sep"),
        ("10", "Okt"), ("11", "Nov"), ("12", "Dez"),
    ]
    rows = [
        journal_row(i + 1, f"RE{i+1:03}", f"01.{m}.2024", "Miete", "6310", "Soll", 1500.0)
        for i, (m, _) in enumerate(months)
    ]
    journal = write_journal(tmp_path, rows)
    konten = write_konten(tmp_path, [("6310", "Mietaufwand")])

    result = anomalien(journal, konten, START, ENDE)

    gaps = result.filter(pl.col("Typ") == "Lücke")
    assert len(gaps) == 1
    row = gaps.row(0, named=True)
    assert row["Konto"] == "6310"
    assert row["Belegdatum"] == "2024-05"
    assert "fehlt" in row["Detail"]


def test_gap_needs_three_bookings(tmp_path):
    # Only 2 bookings with a gap in between — must not trigger gap detection
    rows = [
        journal_row(1, "RE001", "01.01.2024", "Leasing", "6570", "Soll", 300.0),
        journal_row(2, "RE002", "01.03.2024", "Leasing", "6570", "Soll", 300.0),
    ]
    journal = write_journal(tmp_path, rows)
    konten = write_konten(tmp_path, [("6570", "Leasingkosten")])

    result = anomalien(journal, konten, START, ENDE)

    assert result.filter(pl.col("Typ") == "Lücke").is_empty()


def test_jab_entries_excluded(tmp_path):
    # JAB entries with identical fields would be duplicates if included
    rows = [
        journal_row(1, "JAB2024", "01.01.2024", "Eröffnung", "0800", "Soll", 5000.0),
        journal_row(2, "JAB2024", "01.01.2024", "Eröffnung", "0800", "Soll", 5000.0),
        journal_row(3, "RE001",   "15.06.2024", "Wartung",   "6300", "Soll", 200.0),
    ]
    journal = write_journal(tmp_path, rows)
    konten = write_konten(tmp_path, [("0800", "Anlagevermögen"), ("6300", "Reparaturen")])

    result = anomalien(journal, konten, START, ENDE)

    assert result.filter(pl.col("Typ") == "Duplikat").is_empty()


def test_konto_filter(tmp_path):
    # Two accounts both have outliers; filter to one should return only that account
    rows = [
        journal_row(1,  "RE001", "01.01.2024", "Kosten A", "6310", "Soll", 100.0),
        journal_row(2,  "RE002", "01.02.2024", "Kosten A", "6310", "Soll", 102.0),
        journal_row(3,  "RE003", "01.03.2024", "Kosten A", "6310", "Soll", 98.0),
        journal_row(4,  "RE004", "01.04.2024", "Kosten A", "6310", "Soll", 101.0),
        journal_row(5,  "RE005", "01.05.2024", "Kosten A", "6310", "Soll", 9999.0),  # outlier
        journal_row(6,  "RE006", "01.01.2024", "Kosten B", "6320", "Soll", 50.0),
        journal_row(7,  "RE007", "01.02.2024", "Kosten B", "6320", "Soll", 52.0),
        journal_row(8,  "RE008", "01.03.2024", "Kosten B", "6320", "Soll", 48.0),
        journal_row(9,  "RE009", "01.04.2024", "Kosten B", "6320", "Soll", 51.0),
        journal_row(10, "RE010", "01.05.2024", "Kosten B", "6320", "Soll", 8888.0),  # outlier
    ]
    journal = write_journal(tmp_path, rows)
    konten = write_konten(tmp_path, [("6310", "Miete"), ("6320", "Leasing")])

    result = anomalien(journal, konten, START, ENDE, konto="6310")

    assert all(r == "6310" for r in result["Konto"].to_list())
    assert not result.filter(pl.col("Konto") == "6320").shape[0]
