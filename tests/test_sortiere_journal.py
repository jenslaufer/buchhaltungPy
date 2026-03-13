"""Tests for sortiere_journal — sorts journal rows by Buchungsdatum, keeping
Buchungssätze grouped, and renumbers Journalnummer and Buchungssatznummer."""

import shutil

import polars as pl
import pytest

from src.buchhaltung import sortiere_journal, bilanz, guv
from src.cli import main
from tests.conftest import KONTEN_FILE

START = "2024-01-01"
ENDE = "2024-12-31"
HEBESATZ = 380

HEADER = "Journalnummer,Buchungssatznummer,Belegnummer,Belegdatum,Buchungsdatum,Buchungstext,Konto,Typ,Betrag\n"


def write_journal(path, rows: list[str]) -> str:
    """Write a minimal journal CSV to path and return the path as str."""
    content = HEADER + "".join(r + "\n" for r in rows)
    path.write_text(content, encoding="utf-8")
    return str(path)


# ---------------------------------------------------------------------------
# 1. Already-sorted journal stays unchanged (idempotent)
# ---------------------------------------------------------------------------

def test_idempotent_already_sorted(tmp_path):
    p = write_journal(tmp_path / "j.csv", [
        "1,1,RE001,15.02.2024,15.02.2024,Umsatz,1810,Soll,5000",
        "2,1,RE001,15.02.2024,15.02.2024,Umsatz,4400,Haben,5000",
        "3,2,AW001,31.03.2024,31.03.2024,Aufwand,6300,Soll,2000",
        "4,2,AW001,31.03.2024,31.03.2024,Aufwand,1810,Haben,2000",
    ])
    result = sortiere_journal(p)
    assert result["Buchungsdatum"].to_list() == [
        "15.02.2024", "15.02.2024", "31.03.2024", "31.03.2024"
    ]
    assert result["Journalnummer"].to_list() == [1, 2, 3, 4]
    assert result["Buchungssatznummer"].to_list() == [1, 1, 2, 2]


# ---------------------------------------------------------------------------
# 2. Out-of-order Buchungsdatum gets fixed
# ---------------------------------------------------------------------------

def test_out_of_order_dates_sorted(tmp_path):
    p = write_journal(tmp_path / "j.csv", [
        "1,1,RE002,30.06.2024,30.06.2024,Umsatz Jun,1810,Soll,8000",
        "2,1,RE002,30.06.2024,30.06.2024,Umsatz Jun,4400,Haben,8000",
        "3,2,RE001,15.02.2024,15.02.2024,Umsatz Feb,1810,Soll,5000",
        "4,2,RE001,15.02.2024,15.02.2024,Umsatz Feb,4400,Haben,5000",
    ])
    result = sortiere_journal(p)
    dates = result["Buchungsdatum"].to_list()
    # February must come before June
    assert dates.index("15.02.2024") < dates.index("30.06.2024")


# ---------------------------------------------------------------------------
# 3. Rows within the same Buchungssatznummer stay grouped
# ---------------------------------------------------------------------------

def test_buchungssatz_rows_stay_together(tmp_path):
    # BSN 1 is dated June, BSN 2 is dated February — after sort BSN 2 first,
    # but both rows of each BSN must remain adjacent.
    p = write_journal(tmp_path / "j.csv", [
        "1,1,RE002,30.06.2024,30.06.2024,Umsatz,1810,Soll,7000",
        "2,1,RE002,30.06.2024,30.06.2024,Umsatz,4400,Haben,7000",
        "3,2,AW001,28.02.2024,28.02.2024,Aufwand,6300,Soll,3000",
        "4,2,AW001,28.02.2024,28.02.2024,Aufwand,1810,Haben,3000",
    ])
    result = sortiere_journal(p)
    bsn = result["Buchungssatznummer"].to_list()
    # Rows 0 and 1 must share a Buchungssatznummer, rows 2 and 3 must share one
    assert bsn[0] == bsn[1]
    assert bsn[2] == bsn[3]
    assert bsn[0] != bsn[2]


def test_multi_row_buchungssatz_not_split(tmp_path):
    # A three-way split booking (Soll, Haben, Haben) must stay intact.
    p = write_journal(tmp_path / "j.csv", [
        "1,1,RE002,30.09.2024,30.09.2024,Umsatz netto,1810,Soll,11900",
        "2,1,RE002,30.09.2024,30.09.2024,Umsatz USt,1776,Haben,1900",
        "3,1,RE002,30.09.2024,30.09.2024,Umsatz brutto,4400,Haben,10000",
        "4,2,AW001,15.03.2024,15.03.2024,Aufwand,6300,Soll,2000",
        "5,2,AW001,15.03.2024,15.03.2024,Aufwand,1810,Haben,2000",
    ])
    result = sortiere_journal(p)
    bsn = result["Buchungssatznummer"].to_list()
    # All three rows of the three-way booking must be consecutive
    re002_bsn = bsn[result["Belegnummer"].to_list().index("RE002")]
    positions = [i for i, b in enumerate(bsn) if b == re002_bsn]
    assert len(positions) == 3
    assert positions == list(range(positions[0], positions[0] + 3))


# ---------------------------------------------------------------------------
# 4. Journalnummern are sequential 1..n after sorting
# ---------------------------------------------------------------------------

def test_journalnummer_sequential(tmp_path):
    p = write_journal(tmp_path / "j.csv", [
        "5,3,RE002,30.06.2024,30.06.2024,Umsatz,1810,Soll,6000",
        "6,3,RE002,30.06.2024,30.06.2024,Umsatz,4400,Haben,6000",
        "1,1,RE001,15.01.2024,15.01.2024,Umsatz,1810,Soll,5000",
        "2,1,RE001,15.01.2024,15.01.2024,Umsatz,4400,Haben,5000",
        "3,2,AW001,28.02.2024,28.02.2024,Aufwand,6300,Soll,1000",
        "4,2,AW001,28.02.2024,28.02.2024,Aufwand,1810,Haben,1000",
    ])
    result = sortiere_journal(p)
    assert result["Journalnummer"].to_list() == list(range(1, result.height + 1))


# ---------------------------------------------------------------------------
# 5. Buchungssatznummern are dense rank after sorting
# ---------------------------------------------------------------------------

def test_buchungssatznummer_dense_rank(tmp_path):
    p = write_journal(tmp_path / "j.csv", [
        "1,10,RE003,31.10.2024,31.10.2024,Umsatz Oct,1810,Soll,4000",
        "2,10,RE003,31.10.2024,31.10.2024,Umsatz Oct,4400,Haben,4000",
        "3,5,RE001,15.01.2024,15.01.2024,Umsatz Jan,1810,Soll,5000",
        "4,5,RE001,15.01.2024,15.01.2024,Umsatz Jan,4400,Haben,5000",
        "5,7,RE002,28.02.2024,28.02.2024,Umsatz Feb,1810,Soll,3000",
        "6,7,RE002,28.02.2024,28.02.2024,Umsatz Feb,4400,Haben,3000",
    ])
    result = sortiere_journal(p)
    bsn = result["Buchungssatznummer"].to_list()
    # Dense rank means values are 1, 2, 3 — no gaps
    unique_bsn = sorted(set(bsn))
    assert unique_bsn == list(range(1, len(unique_bsn) + 1))


def test_buchungssatznummer_starts_at_one(tmp_path):
    p = write_journal(tmp_path / "j.csv", [
        "3,3,RE001,15.03.2024,15.03.2024,Umsatz,1810,Soll,5000",
        "4,3,RE001,15.03.2024,15.03.2024,Umsatz,4400,Haben,5000",
    ])
    result = sortiere_journal(p)
    assert result["Buchungssatznummer"].min() == 1


# ---------------------------------------------------------------------------
# 6. JAB entries remain at start
# ---------------------------------------------------------------------------

def test_jab_entries_remain_at_start(tmp_path):
    p = write_journal(tmp_path / "j.csv", [
        "1,1,JAB1,01.01.2024,01.01.2024,Eroeffnung Bank,1810,Soll,50000",
        "2,1,JAB1,01.01.2024,01.01.2024,Eroeffnung Bank,9000,Haben,50000",
        "3,2,RE001,15.06.2024,15.06.2024,Umsatz,1810,Soll,10000",
        "4,2,RE001,15.06.2024,15.06.2024,Umsatz,4400,Haben,10000",
        "5,3,RE000,20.02.2024,20.02.2024,Umsatz Feb,1810,Soll,3000",
        "6,3,RE000,20.02.2024,20.02.2024,Umsatz Feb,4400,Haben,3000",
    ])
    result = sortiere_journal(p)
    # JAB rows must occupy the first positions
    jab_rows = result.filter(pl.col("Belegnummer").str.starts_with("JAB"))
    non_jab_rows = result.filter(~pl.col("Belegnummer").str.starts_with("JAB"))
    jab_max_jnr = jab_rows["Journalnummer"].max()
    non_jab_min_jnr = non_jab_rows["Journalnummer"].min()
    assert jab_max_jnr < non_jab_min_jnr


def test_multiple_jab_buchungssaetze_stay_grouped(tmp_path):
    p = write_journal(tmp_path / "j.csv", [
        "1,1,JAB1,01.01.2024,01.01.2024,Eroeffnung Bank,1810,Soll,50000",
        "2,1,JAB1,01.01.2024,01.01.2024,Eroeffnung Bank,9000,Haben,50000",
        "3,2,JAB2,01.01.2024,01.01.2024,Eroeffnung Kapital,9000,Soll,30000",
        "4,2,JAB2,01.01.2024,01.01.2024,Eroeffnung Kapital,2900,Haben,30000",
        "5,3,RE001,31.07.2024,31.07.2024,Umsatz,1810,Soll,8000",
        "6,3,RE001,31.07.2024,31.07.2024,Umsatz,4400,Haben,8000",
    ])
    result = sortiere_journal(p)
    belnr = result["Belegnummer"].to_list()
    # Both JAB entries must precede RE001
    re_idx = next(i for i, b in enumerate(belnr) if b == "RE001")
    jab_indices = [i for i, b in enumerate(belnr) if b.startswith("JAB")]
    assert all(idx < re_idx for idx in jab_indices)


# ---------------------------------------------------------------------------
# 7. JEB entries remain at end
# ---------------------------------------------------------------------------

def test_jeb_entries_remain_at_end(tmp_path):
    p = write_journal(tmp_path / "j.csv", [
        "1,1,RE001,15.03.2024,15.03.2024,Umsatz,1810,Soll,10000",
        "2,1,RE001,15.03.2024,15.03.2024,Umsatz,4400,Haben,10000",
        "3,2,JEB1,31.12.2024,31.12.2024,Jahresabschluss,4400,Soll,10000",
        "4,2,JEB1,31.12.2024,31.12.2024,Jahresabschluss,00000,Haben,10000",
        "5,3,RE002,30.11.2024,30.11.2024,Umsatz Nov,1810,Soll,7000",
        "6,3,RE002,30.11.2024,30.11.2024,Umsatz Nov,4400,Haben,7000",
    ])
    result = sortiere_journal(p)
    jeb_rows = result.filter(pl.col("Belegnummer").str.starts_with("JEB"))
    non_jeb_rows = result.filter(~pl.col("Belegnummer").str.starts_with("JEB"))
    jeb_min_jnr = jeb_rows["Journalnummer"].min()
    non_jeb_max_jnr = non_jeb_rows["Journalnummer"].max()
    assert jeb_min_jnr > non_jeb_max_jnr


def test_jeb_after_non_jeb_same_date(tmp_path):
    """JEB entries sort after regular entries even when sharing the same date."""
    p = write_journal(tmp_path / "j.csv", [
        "1,1,RE001,31.12.2024,31.12.2024,Dezember Umsatz,1810,Soll,5000",
        "2,1,RE001,31.12.2024,31.12.2024,Dezember Umsatz,4400,Haben,5000",
        "3,2,JEB1,31.12.2024,31.12.2024,Jahresabschluss,4400,Soll,5000",
        "4,2,JEB1,31.12.2024,31.12.2024,Jahresabschluss,00000,Haben,5000",
    ])
    result = sortiere_journal(p)
    belnr = result["Belegnummer"].to_list()
    assert belnr == ["RE001", "RE001", "JEB1", "JEB1"]


def test_betrag_two_decimal_places(tmp_path):
    """Written CSV has exactly two decimal places for Betrag."""
    p = write_journal(tmp_path / "j.csv", [
        "1,1,RE001,15.03.2024,15.03.2024,Umsatz,1810,Soll,10000",
        "2,1,RE001,15.03.2024,15.03.2024,Umsatz,4400,Haben,10000",
    ])
    sortiere_journal(p)
    from pathlib import Path
    lines = Path(p).read_text().strip().split("\n")[1:]  # skip header
    for line in lines:
        betrag = line.split(",")[-1]
        assert "." in betrag
        assert len(betrag.split(".")[-1]) == 2, f"Expected 2 decimals: {betrag}"


# ---------------------------------------------------------------------------
# 8. Bilanz before == Bilanz after sorting
# ---------------------------------------------------------------------------

def test_bilanz_unchanged_after_sort(tmp_path):
    src = tmp_path / "j.csv"
    # Reverse-ordered multi-month journal with JAB entries
    src.write_text(
        HEADER
        + "1,1,JAB1,01.01.2024,01.01.2024,Eroeffnung Bank,1810,Soll,50000\n"
        + "2,1,JAB1,01.01.2024,01.01.2024,Eroeffnung Bank,9000,Haben,50000\n"
        + "3,2,JAB2,01.01.2024,01.01.2024,Eroeffnung Kapital,9000,Soll,50000\n"
        + "4,2,JAB2,01.01.2024,01.01.2024,Eroeffnung Kapital,2900,Haben,50000\n"
        + "5,3,RE003,31.10.2024,31.10.2024,Umsatz Okt,1810,Soll,12000\n"
        + "6,3,RE003,31.10.2024,31.10.2024,Umsatz Okt,4400,Haben,12000\n"
        + "7,4,RE001,28.02.2024,28.02.2024,Umsatz Feb,1810,Soll,8000\n"
        + "8,4,RE001,28.02.2024,28.02.2024,Umsatz Feb,4400,Haben,8000\n",
        encoding="utf-8",
    )
    before = bilanz(str(src), KONTEN_FILE, START, ENDE, HEBESATZ)
    sortiere_journal(str(src))
    after = bilanz(str(src), KONTEN_FILE, START, ENDE, HEBESATZ)

    def parse_de(s):
        return float(s.replace(".", "").replace(",", "."))

    def get_total(b, seite):
        return parse_de(b.filter(
            (pl.col("Bilanzseite") == seite) & (pl.col("Ebene1") == "NA")
        )["Betrag"][0])

    assert abs(get_total(before, "Aktiva") - get_total(after, "Aktiva")) < 0.01
    assert abs(get_total(before, "Passiva") - get_total(after, "Passiva")) < 0.01


# ---------------------------------------------------------------------------
# 9. GuV before == GuV after sorting
# ---------------------------------------------------------------------------

def test_guv_unchanged_after_sort(tmp_path):
    src = tmp_path / "j.csv"
    src.write_text(
        HEADER
        + "1,1,RE003,30.09.2024,30.09.2024,Umsatz Sep,1810,Soll,9000\n"
        + "2,1,RE003,30.09.2024,30.09.2024,Umsatz Sep,4400,Haben,9000\n"
        + "3,2,RE001,31.01.2024,31.01.2024,Umsatz Jan,1810,Soll,5000\n"
        + "4,2,RE001,31.01.2024,31.01.2024,Umsatz Jan,4400,Haben,5000\n"
        + "5,3,AW001,28.02.2024,28.02.2024,Aufwand Feb,6300,Soll,2000\n"
        + "6,3,AW001,28.02.2024,28.02.2024,Aufwand Feb,1810,Haben,2000\n",
        encoding="utf-8",
    )
    before = guv(str(src), KONTEN_FILE, START, ENDE, HEBESATZ)
    sortiere_journal(str(src))
    after = guv(str(src), KONTEN_FILE, START, ENDE, HEBESATZ)

    ergebnis_before = before.filter(
        pl.col("GuV Posten") == "Betriebsergebnis"
    )["Betrag"].sum()
    ergebnis_after = after.filter(
        pl.col("GuV Posten") == "Betriebsergebnis"
    )["Betrag"].sum()
    assert abs(ergebnis_before - ergebnis_after) < 0.01


# ---------------------------------------------------------------------------
# 10. Soll == Haben per Buchungssatz preserved after sort
# ---------------------------------------------------------------------------

def test_buchungssatz_balance_preserved(tmp_path):
    p = write_journal(tmp_path / "j.csv", [
        "1,1,RE002,31.08.2024,31.08.2024,Umsatz Aug,1810,Soll,15000",
        "2,1,RE002,31.08.2024,31.08.2024,Umsatz Aug,4400,Haben,15000",
        "3,2,RE001,15.01.2024,15.01.2024,Umsatz Jan,1810,Soll,5000",
        "4,2,RE001,15.01.2024,15.01.2024,Umsatz Jan,4400,Haben,5000",
        "5,3,AW001,31.03.2024,31.03.2024,Aufwand,6300,Soll,3000",
        "6,3,AW001,31.03.2024,31.03.2024,Aufwand,1810,Haben,3000",
    ])
    result = sortiere_journal(p)

    for bsn in result["Buchungssatznummer"].unique().to_list():
        group = result.filter(pl.col("Buchungssatznummer") == bsn)
        soll = group.filter(pl.col("Typ") == "Soll")["Betrag"].sum()
        haben = group.filter(pl.col("Typ") == "Haben")["Betrag"].sum()
        assert abs(soll - haben) < 0.01, f"BSN {bsn}: Soll {soll} != Haben {haben}"


def test_soll_haben_balance_multi_row_buchungssatz(tmp_path):
    # Three-row booking: one Soll, two Haben
    p = write_journal(tmp_path / "j.csv", [
        "1,1,RE002,30.11.2024,30.11.2024,Einnahme brutto,1810,Soll,11900",
        "2,1,RE002,30.11.2024,30.11.2024,Einnahme USt,1776,Haben,1900",
        "3,1,RE002,30.11.2024,30.11.2024,Einnahme netto,4400,Haben,10000",
        "4,2,AW001,15.04.2024,15.04.2024,Aufwand Apr,6300,Soll,4000",
        "5,2,AW001,15.04.2024,15.04.2024,Aufwand Apr,1810,Haben,4000",
    ])
    result = sortiere_journal(p)

    for bsn in result["Buchungssatznummer"].unique().to_list():
        group = result.filter(pl.col("Buchungssatznummer") == bsn)
        soll = group.filter(pl.col("Typ") == "Soll")["Betrag"].sum()
        haben = group.filter(pl.col("Typ") == "Haben")["Betrag"].sum()
        assert abs(soll - haben) < 0.01


# ---------------------------------------------------------------------------
# 11. Stable sort — relative order of same-date Buchungssätze preserved
# ---------------------------------------------------------------------------

def test_same_date_relative_order_preserved(tmp_path):
    # Three Buchungssätze all on the same date: original order BSN A, B, C
    # After sort they should remain A, B, C (stable).
    p = write_journal(tmp_path / "j.csv", [
        "1,1,FIRST,31.05.2024,31.05.2024,First,1810,Soll,1000",
        "2,1,FIRST,31.05.2024,31.05.2024,First,4400,Haben,1000",
        "3,2,SECOND,31.05.2024,31.05.2024,Second,1810,Soll,2000",
        "4,2,SECOND,31.05.2024,31.05.2024,Second,4400,Haben,2000",
        "5,3,THIRD,31.05.2024,31.05.2024,Third,1810,Soll,3000",
        "6,3,THIRD,31.05.2024,31.05.2024,Third,4400,Haben,3000",
    ])
    result = sortiere_journal(p)
    belnr = [b for b in result["Belegnummer"].to_list() if b in ("FIRST", "SECOND", "THIRD")]
    # Drop duplicates preserving order
    seen = []
    for b in belnr:
        if b not in seen:
            seen.append(b)
    assert seen == ["FIRST", "SECOND", "THIRD"]


# ---------------------------------------------------------------------------
# 12. Written file matches returned DataFrame
# ---------------------------------------------------------------------------

def test_written_file_matches_returned_dataframe(tmp_path):
    p = write_journal(tmp_path / "j.csv", [
        "1,1,RE002,30.06.2024,30.06.2024,Umsatz Jun,1810,Soll,6000",
        "2,1,RE002,30.06.2024,30.06.2024,Umsatz Jun,4400,Haben,6000",
        "3,2,RE001,15.01.2024,15.01.2024,Umsatz Jan,1810,Soll,5000",
        "4,2,RE001,15.01.2024,15.01.2024,Umsatz Jan,4400,Haben,5000",
    ])
    result = sortiere_journal(p)
    on_disk = pl.read_csv(p, schema_overrides={"Konto": pl.Utf8, "Journalnummer": pl.Int64})
    assert result["Journalnummer"].to_list() == on_disk["Journalnummer"].to_list()
    assert result["Buchungssatznummer"].to_list() == on_disk["Buchungssatznummer"].to_list()
    assert result["Buchungsdatum"].to_list() == on_disk["Buchungsdatum"].to_list()


# ---------------------------------------------------------------------------
# 13. CLI command sortiere-journal works
# ---------------------------------------------------------------------------

def test_cli_sortiere_journal(tmp_path, capsys):
    src = tmp_path / "j.csv"
    src.write_text(
        HEADER
        + "1,1,RE002,30.06.2024,30.06.2024,Umsatz Jun,1810,Soll,6000\n"
        + "2,1,RE002,30.06.2024,30.06.2024,Umsatz Jun,4400,Haben,6000\n"
        + "3,2,RE001,15.01.2024,15.01.2024,Umsatz Jan,1810,Soll,5000\n"
        + "4,2,RE001,15.01.2024,15.01.2024,Umsatz Jan,4400,Haben,5000\n",
        encoding="utf-8",
    )
    main(["sortiere-journal", str(src)])
    output = capsys.readouterr().out
    assert str(src) in output or "Sorted" in output or "sorted" in output

    result = pl.read_csv(str(src), schema_overrides={"Konto": pl.Utf8, "Journalnummer": pl.Int64})
    dates = result["Buchungsdatum"].to_list()
    assert dates.index("15.01.2024") < dates.index("30.06.2024")
    assert result["Journalnummer"].to_list() == list(range(1, result.height + 1))


def test_cli_sortiere_journal_jab_jeb(tmp_path, capsys):
    src = tmp_path / "j.csv"
    src.write_text(
        HEADER
        + "1,1,RE001,15.06.2024,15.06.2024,Umsatz,1810,Soll,10000\n"
        + "2,1,RE001,15.06.2024,15.06.2024,Umsatz,4400,Haben,10000\n"
        + "3,2,JAB1,01.01.2024,01.01.2024,Eroeffnung,1810,Soll,20000\n"
        + "4,2,JAB1,01.01.2024,01.01.2024,Eroeffnung,9000,Haben,20000\n"
        + "5,3,JEB1,31.12.2024,31.12.2024,Abschluss,4400,Soll,10000\n"
        + "6,3,JEB1,31.12.2024,31.12.2024,Abschluss,00000,Haben,10000\n",
        encoding="utf-8",
    )
    main(["sortiere-journal", str(src)])
    capsys.readouterr()

    result = pl.read_csv(str(src), schema_overrides={"Konto": pl.Utf8, "Journalnummer": pl.Int64})
    belnr = result["Belegnummer"].to_list()
    # JAB first, JEB last
    jab_indices = [i for i, b in enumerate(belnr) if b.startswith("JAB")]
    jeb_indices = [i for i, b in enumerate(belnr) if b.startswith("JEB")]
    re_indices = [i for i, b in enumerate(belnr) if b.startswith("RE")]
    assert max(jab_indices) < min(re_indices)
    assert min(jeb_indices) > max(re_indices)


# ---------------------------------------------------------------------------
# 14. Buchungsdatum unified within BSN (earliest date wins)
# ---------------------------------------------------------------------------

def test_buchungsdatum_unified_within_bsn(tmp_path):
    """Rows of the same BSN with different Buchungsdaten get unified to the earliest."""
    p = write_journal(tmp_path / "j.csv", [
        "1,1,A16,13.06.2024,13.06.2024,Beratung,1810,Soll,5000",
        "2,1,A16,13.09.2024,15.09.2024,Beratung,4400,Haben,3000",
        "3,1,A16,13.09.2024,15.09.2024,Beratung,3806,Haben,2000",
    ])
    result = sortiere_journal(p)
    dates = result["Buchungsdatum"].to_list()
    # All three rows must have the earliest date
    assert dates == ["13.06.2024", "13.06.2024", "13.06.2024"]


def test_buchungsdatum_unified_no_change_when_consistent(tmp_path):
    """BSN with already consistent Buchungsdatum stays unchanged."""
    p = write_journal(tmp_path / "j.csv", [
        "1,1,E1,15.03.2024,15.03.2024,Aufwand,6300,Soll,1000",
        "2,1,E1,15.03.2024,15.03.2024,Aufwand,1810,Haben,1000",
    ])
    result = sortiere_journal(p)
    dates = result["Buchungsdatum"].to_list()
    assert dates == ["15.03.2024", "15.03.2024"]


def test_buchungsdatum_unified_sort_uses_earliest(tmp_path):
    """After unification, BSN sorts by its earliest date, not the later one."""
    p = write_journal(tmp_path / "j.csv", [
        # BSN 1: rows have dates 13.06 and 15.09 -> unified to 13.06
        "1,1,A16,13.06.2024,13.06.2024,Beratung,1810,Soll,5000",
        "2,1,A16,13.09.2024,15.09.2024,Beratung,4400,Haben,5000",
        # BSN 2: date 14.06 -> should come after BSN 1 (13.06)
        "3,2,KO17,14.06.2024,14.06.2024,Transfer,1830,Soll,3000",
        "4,2,KO17,14.06.2024,14.06.2024,Transfer,1810,Haben,3000",
    ])
    result = sortiere_journal(p)
    # BSN 1 (13.06) should be before BSN 2 (14.06)
    assert result["Buchungssatznummer"].to_list() == [1, 1, 2, 2]
    # All BSN 1 rows unified to 13.06
    bsn1 = result.filter(pl.col("Buchungssatznummer") == 1)
    assert bsn1["Buchungsdatum"].unique().to_list() == ["13.06.2024"]


def test_buchungsdatum_unified_gobd_chronology(tmp_path):
    """After unification + sort, Buchungsdatum is monotonically non-decreasing."""
    p = write_journal(tmp_path / "j.csv", [
        # BSN 1: mixed dates 13.06 and 15.09
        "1,1,A16,13.06.2024,13.06.2024,Beratung,1810,Soll,5000",
        "2,1,A16,13.09.2024,15.09.2024,Beratung,4400,Haben,5000",
        # BSN 2: date 14.06
        "3,2,KO17,14.06.2024,14.06.2024,Transfer,1830,Soll,3000",
        "4,2,KO17,14.06.2024,14.06.2024,Transfer,1810,Haben,3000",
        # BSN 3: date 01.03
        "5,3,E5,01.03.2024,01.03.2024,Aufwand,6300,Soll,1000",
        "6,3,E5,01.03.2024,01.03.2024,Aufwand,1810,Haben,1000",
    ])
    result = sortiere_journal(p)
    dates = result.with_columns(
        pl.col("Buchungsdatum").str.strptime(pl.Date, "%d.%m.%Y").alias("_d")
    )["_d"].to_list()
    # Dates must be non-decreasing
    for i in range(1, len(dates)):
        assert dates[i] >= dates[i-1], f"Row {i}: {dates[i]} < {dates[i-1]}"
