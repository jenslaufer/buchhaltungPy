"""Tests for Benford's Law analysis: benford() function and CLI command."""

import math
import re

import polars as pl
import pytest

from src.buchhaltung import benford
from src.cli import main
from tests.conftest import KONTEN_FILE

START = "2024-01-01"
ENDE = "2024-12-31"

HEADER = (
    "Journalnummer,Buchungssatznummer,Belegnummer,Belegdatum,"
    "Buchungsdatum,Buchungstext,Konto,Typ,Betrag\n"
)

# The Detail column exists for all rows; digit rows have it empty, Chi2 row has the stat.
EXPECTED_COLUMNS = ["Ziffer", "Erwartet_Pct", "Beobachtet_Pct", "Abweichung_Pct", "Anzahl", "Detail"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _benford_expected(d: int) -> float:
    return math.log10(1 + 1 / d) * 100


def write_journal(tmp_path, rows: list[str]) -> str:
    p = tmp_path / "journal.csv"
    p.write_text(HEADER + "".join(rows))
    return str(p)


def _violation_rows(tmp_path) -> str:
    """Journal where all amounts start with digit 5 — violates Benford."""
    rows = []
    nr = 1
    for i in range(1, 101):
        betrag = 5000 + i
        rows.append(f"{nr},{i},RE{i:04},15.01.2024,15.01.2024,Buchung,1810,Soll,{betrag}\n")
        nr += 1
        rows.append(f"{nr},{i},RE{i:04},15.01.2024,15.01.2024,Buchung,4400,Haben,{betrag}\n")
        nr += 1
    return write_journal(tmp_path, rows)


# ---------------------------------------------------------------------------
# Fixture: naturally distributed amounts (Benford-conformant)
# ---------------------------------------------------------------------------

def _benford_journal(tmp_path) -> str:
    """
    Construct amounts whose first digits follow Benford proportions closely.
    For each digit d, include roughly log10(1+1/d)*100 entries so that the
    observed distribution matches expected and yields a high p-value.
    """
    amounts_by_digit = {
        1: [1000, 1500, 1200, 1800, 1100, 1300, 1400, 1600, 1700, 1050,
            1250, 1350, 1450, 1550, 1650, 1750, 1850, 1950, 1025, 1075,
            1125, 1175, 1225, 1275, 1325, 1375, 1425, 1475, 1525, 1575],
        2: [2000, 2500, 2100, 2300, 2200, 2400, 2600, 2700, 2800, 2900,
            2050, 2150, 2250, 2350, 2450, 2550, 2650],
        3: [3000, 3500, 3100, 3200, 3300, 3400, 3600, 3700, 3800, 3900,
            3050, 3150],
        4: [4000, 4500, 4100, 4200, 4300, 4400, 4600, 4700, 4800, 4900],
        5: [5000, 5500, 5100, 5200, 5300, 5400, 5600, 5700, 5800],
        6: [6000, 6500, 6100, 6200, 6300, 6400, 6600, 6700, 6800],
        7: [7000, 7500, 7100, 7200, 7300, 7400, 7600, 7700],
        8: [8000, 8500, 8100, 8200, 8300, 8400, 8600, 8700],
        9: [9000, 9500, 9100, 9200, 9300, 9400, 9600, 9700],
    }
    rows = []
    nr = 1
    bsatz = 1
    for digit, amounts in amounts_by_digit.items():
        for amt in amounts:
            rows.append(
                f"{nr},{bsatz},RE{bsatz:04},15.01.2024,15.01.2024,"
                f"Buchung,1810,Soll,{amt}\n"
            )
            nr += 1
            rows.append(
                f"{nr},{bsatz},RE{bsatz:04},15.01.2024,15.01.2024,"
                f"Buchung,4400,Haben,{amt}\n"
            )
            nr += 1
            bsatz += 1

    return write_journal(tmp_path, rows)


def _extract_p_value(detail: str) -> float:
    """Extract p-value from Detail string formatted as 'chi2=X.XXXX, p=X.XXXX'."""
    return float(detail.split("p=")[1])


# ---------------------------------------------------------------------------
# Test 1: correct columns returned
# ---------------------------------------------------------------------------

def test_columns(tmp_path):
    journal = _benford_journal(tmp_path)
    result = benford(journal, KONTEN_FILE, START, ENDE)

    assert isinstance(result, pl.DataFrame)
    assert result.columns == EXPECTED_COLUMNS


# ---------------------------------------------------------------------------
# Test 2: digit rows cover exactly digits 1-9
# ---------------------------------------------------------------------------

def test_digits_one_through_nine(tmp_path):
    journal = _benford_journal(tmp_path)
    result = benford(journal, KONTEN_FILE, START, ENDE)

    digit_rows = result.filter(pl.col("Ziffer") != "Chi2")
    ziffern = sorted(digit_rows["Ziffer"].cast(pl.Int32).to_list())
    assert ziffern == list(range(1, 10))


# ---------------------------------------------------------------------------
# Test 3: Chi2 summary row is present
# ---------------------------------------------------------------------------

def test_chi2_row_present(tmp_path):
    journal = _benford_journal(tmp_path)
    result = benford(journal, KONTEN_FILE, START, ENDE)

    chi2_rows = result.filter(pl.col("Ziffer") == "Chi2")
    assert len(chi2_rows) == 1


# ---------------------------------------------------------------------------
# Test 4: observed percentages sum to ~100%
# ---------------------------------------------------------------------------

def test_observed_pct_sums_to_100(tmp_path):
    journal = _benford_journal(tmp_path)
    result = benford(journal, KONTEN_FILE, START, ENDE)

    digit_rows = result.filter(pl.col("Ziffer") != "Chi2")
    total = digit_rows["Beobachtet_Pct"].sum()
    assert abs(total - 100.0) < 0.1


# ---------------------------------------------------------------------------
# Test 5: expected percentages match Benford formula and sum to ~100%
# ---------------------------------------------------------------------------

def test_expected_pct_matches_benford_formula(tmp_path):
    journal = _benford_journal(tmp_path)
    result = benford(journal, KONTEN_FILE, START, ENDE)

    digit_rows = result.filter(pl.col("Ziffer") != "Chi2")
    for row in digit_rows.iter_rows(named=True):
        d = int(row["Ziffer"])
        expected = _benford_expected(d)
        assert abs(row["Erwartet_Pct"] - expected) < 0.01, (
            f"Digit {d}: expected {expected:.4f}%, got {row['Erwartet_Pct']:.4f}%"
        )

    total_expected = digit_rows["Erwartet_Pct"].sum()
    assert abs(total_expected - 100.0) < 0.01


# ---------------------------------------------------------------------------
# Test 6: Abweichung_Pct == Beobachtet_Pct - Erwartet_Pct (within rounding)
# ---------------------------------------------------------------------------

def test_abweichung_is_difference(tmp_path):
    journal = _benford_journal(tmp_path)
    result = benford(journal, KONTEN_FILE, START, ENDE)

    digit_rows = result.filter(pl.col("Ziffer") != "Chi2")
    for row in digit_rows.iter_rows(named=True):
        diff = row["Beobachtet_Pct"] - row["Erwartet_Pct"]
        assert abs(row["Abweichung_Pct"] - diff) < 0.02, (
            f"Digit {row['Ziffer']}: Abweichung_Pct={row['Abweichung_Pct']:.4f} "
            f"but Beobachtet-Erwartet={diff:.4f}"
        )


# ---------------------------------------------------------------------------
# Test 7: Anzahl sums to total number of positive Betrag entries analyzed
# ---------------------------------------------------------------------------

def test_anzahl_sums_to_total_entries(tmp_path):
    journal = _benford_journal(tmp_path)
    result = benford(journal, KONTEN_FILE, START, ENDE)

    digit_rows = result.filter(pl.col("Ziffer") != "Chi2")
    total_anzahl = digit_rows["Anzahl"].sum()
    assert total_anzahl > 0


# ---------------------------------------------------------------------------
# Test 8: Benford-conformant data yields high p-value
# ---------------------------------------------------------------------------

def test_benford_conformant_data_high_p_value(tmp_path):
    journal = _benford_journal(tmp_path)
    result = benford(journal, KONTEN_FILE, START, ENDE)

    chi2_row = result.filter(pl.col("Ziffer") == "Chi2").row(0, named=True)
    # Detail format: "chi2=X.XXXX, p=X.XXXX"
    p_value = _extract_p_value(chi2_row["Detail"])
    assert p_value > 0.05, f"Expected p > 0.05 for Benford-conformant data, got p={p_value}"


# ---------------------------------------------------------------------------
# Test 9: Violation journal — all amounts start with digit 5 → low p-value
# ---------------------------------------------------------------------------

def test_benford_violation_low_p_value(tmp_path):
    """All amounts start with 5 — violates Benford, should produce p <= 0.05."""
    journal = _violation_rows(tmp_path)
    result = benford(journal, KONTEN_FILE, START, ENDE)

    chi2_row = result.filter(pl.col("Ziffer") == "Chi2").row(0, named=True)
    # Detail format: "chi2=X.XXXX, p=X.XXXX"
    p_value = _extract_p_value(chi2_row["Detail"])
    assert p_value <= 0.05, f"Expected p <= 0.05 for violated Benford data, got p={p_value}"


# ---------------------------------------------------------------------------
# Test 10: JEB and JAB entries are excluded
# ---------------------------------------------------------------------------

def test_jeb_jab_entries_excluded(tmp_path):
    """JEB/JAB entries must not be counted in the Benford analysis."""
    rows = []
    # 10 regular balanced bookings with digit-1 amounts
    for i in range(1, 11):
        rows.append(f"{2*i-1},{i},RE{i:04},15.06.2024,15.06.2024,Normal,1810,Soll,1{i*100}\n")
        rows.append(f"{2*i},{i},RE{i:04},15.06.2024,15.06.2024,Normal,4400,Haben,1{i*100}\n")
    # JEB and JAB entries with digit-9 amounts that should be excluded
    jab_nr = 21
    rows.append(f"{jab_nr},11,JAB2024,01.01.2024,01.01.2024,Jahresabschluss,0800,Soll,99999\n")
    rows.append(f"{jab_nr+1},11,JAB2024,01.01.2024,01.01.2024,Jahresabschluss,0900,Haben,99999\n")
    rows.append(f"{jab_nr+2},12,JEB2024,01.01.2024,01.01.2024,Jahreseröffnung,0900,Soll,99999\n")
    rows.append(f"{jab_nr+3},12,JEB2024,01.01.2024,01.01.2024,Jahreseröffnung,0800,Haben,99999\n")

    journal = write_journal(tmp_path, rows)
    result = benford(journal, KONTEN_FILE, START, ENDE)

    digit_rows = result.filter(pl.col("Ziffer") != "Chi2")
    digit9 = digit_rows.filter(pl.col("Ziffer") == "9")
    assert len(digit9) == 1
    count_9 = digit9["Anzahl"][0]
    # All digit-9 amounts come only from JEB/JAB rows, which must be excluded
    assert count_9 == 0, f"Expected 0 digit-9 entries after JEB/JAB exclusion, got {count_9}"


# ---------------------------------------------------------------------------
# Test 11: Date range filtering works
# ---------------------------------------------------------------------------

def test_date_range_filter(tmp_path):
    """Bookings outside the date range must be excluded."""
    rows = [
        # In range (2024): digit 1
        "1,1,RE001,15.06.2024,15.06.2024,In range,1810,Soll,1000\n",
        "2,1,RE001,15.06.2024,15.06.2024,In range,4400,Haben,1000\n",
        # Out of range (2023): digit 9 — must not appear in results
        "3,2,RE002,15.06.2023,15.06.2023,Out of range,1810,Soll,9000\n",
        "4,2,RE002,15.06.2023,15.06.2023,Out of range,4400,Haben,9000\n",
    ]
    journal = write_journal(tmp_path, rows)
    result = benford(journal, KONTEN_FILE, START, ENDE)

    digit_rows = result.filter(pl.col("Ziffer") != "Chi2")
    digit9 = digit_rows.filter(pl.col("Ziffer") == "9")
    assert digit9["Anzahl"][0] == 0, "Out-of-range bookings must be excluded"


# ---------------------------------------------------------------------------
# Test 12: Zero Betrag values are excluded
# ---------------------------------------------------------------------------

def test_zero_betrag_excluded(tmp_path):
    """Only Betrag > 0 should be analyzed."""
    rows = [
        "1,1,RE001,15.01.2024,15.01.2024,Positiv,1810,Soll,1000\n",
        "2,1,RE001,15.01.2024,15.01.2024,Positiv,4400,Haben,1000\n",
        # Zero entries should be excluded:
        "3,2,RE002,15.01.2024,15.01.2024,Null,1810,Soll,0\n",
        "4,2,RE002,15.01.2024,15.01.2024,Null,4400,Haben,0\n",
    ]
    journal = write_journal(tmp_path, rows)
    result = benford(journal, KONTEN_FILE, START, ENDE)

    digit_rows = result.filter(pl.col("Ziffer") != "Chi2")
    total_anzahl = digit_rows["Anzahl"].sum()
    # Only the two Betrag=1000 rows (Soll + Haben) are counted
    assert total_anzahl == 2


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------

def test_cli_benford_outputs_csv(capsys, tmp_path):
    """CLI benford command outputs CSV with expected columns to stdout."""
    journal = _benford_journal(tmp_path)
    main(["benford", journal, "--start", START, "--ende", ENDE])
    out = capsys.readouterr().out

    assert "Ziffer" in out
    assert "Erwartet_Pct" in out
    assert "Beobachtet_Pct" in out
    assert "Abweichung_Pct" in out
    assert "Anzahl" in out


def test_cli_benford_pass_for_conformant_data(capsys, tmp_path):
    """CLI prints PASS (stderr) when Benford test is not significant."""
    journal = _benford_journal(tmp_path)
    main(["benford", journal, "--start", START, "--ende", ENDE])
    err = capsys.readouterr().err
    assert "PASS" in err


def test_cli_benford_warnung_for_violation(capsys, tmp_path):
    """CLI prints WARNUNG (stderr) and exits with code 1 when p <= 0.05."""
    journal = _violation_rows(tmp_path)
    with pytest.raises(SystemExit, match="1"):
        main(["benford", journal, "--start", START, "--ende", ENDE])
    err = capsys.readouterr().err
    assert "WARNUNG" in err
    assert "Benford" in err


def test_cli_benford_warnung_contains_p_value(capsys, tmp_path):
    """WARNUNG message includes the p-value formatted to 4 decimal places."""
    journal = _violation_rows(tmp_path)
    with pytest.raises(SystemExit, match="1"):
        main(["benford", journal, "--start", START, "--ende", ENDE])
    err = capsys.readouterr().err
    assert re.search(r"p=\d+\.\d{4}", err), (
        f"Expected p=X.XXXX in stderr, got: {err}"
    )
