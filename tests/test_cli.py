"""Tests for the CLI tool."""

import shutil
import tempfile

import polars as pl
import pytest

from src.cli import main
from tests.conftest import fixture_path, KONTEN_FILE

START = "2024-01-01"
ENDE = "2024-12-31"
JOURNAL = fixture_path("01_simple_profit.csv")
INVALID_JOURNAL = fixture_path("05_invalid_unbalanced.csv")
MULTI_JOURNAL = fixture_path("03_multi_bookings.csv")


# -- Validation commands --

def test_validiere_journal_pass(capsys):
    main(["validiere-journal", JOURNAL, "--start", START, "--ende", ENDE])
    assert capsys.readouterr().out.strip() == "PASS"


def test_validiere_journal_fail(capsys):
    with pytest.raises(SystemExit, match="1"):
        main(["validiere-journal", INVALID_JOURNAL, "--start", START, "--ende", ENDE])
    assert "FEHLER" in capsys.readouterr().out


def test_validiere_bilanz_pass(capsys):
    main(["validiere-bilanz", JOURNAL, "--start", START, "--ende", ENDE])
    assert capsys.readouterr().out.strip() == "PASS"


# -- Scalar commands --

def test_betriebsergebnis(capsys):
    main(["betriebsergebnis", JOURNAL, "--start", START, "--ende", ENDE])
    result = float(capsys.readouterr().out.strip())
    assert result == 10000.0


def test_koerperschaftssteuer(capsys):
    main(["koerperschaftssteuer", JOURNAL, "--start", START, "--ende", ENDE])
    result = float(capsys.readouterr().out.strip())
    assert result > 0


def test_soli(capsys):
    main(["soli", JOURNAL, "--start", START, "--ende", ENDE])
    result = float(capsys.readouterr().out.strip())
    assert result > 0


def test_gewerbesteuer(capsys):
    main(["gewerbesteuer", JOURNAL, "--start", START, "--ende", ENDE])
    result = float(capsys.readouterr().out.strip())
    assert result > 0


def test_gewerbesteuer_custom_hebesatz(capsys):
    main(["gewerbesteuer", JOURNAL, "--start", START, "--ende", ENDE, "--hebesatz", "200"])
    result = float(capsys.readouterr().out.strip())
    assert result > 0


def test_steuern(capsys):
    main(["steuern", JOURNAL, "--start", START, "--ende", ENDE])
    result = float(capsys.readouterr().out.strip())
    assert result > 0


# -- DataFrame commands --

def test_guv_outputs_csv(capsys):
    main(["guv", JOURNAL, "--start", START, "--ende", ENDE])
    output = capsys.readouterr().out
    assert "GuV Posten" in output
    assert "Betriebsergebnis" in output


def test_bilanz_outputs_csv(capsys):
    main(["bilanz", JOURNAL, "--start", START, "--ende", ENDE])
    output = capsys.readouterr().out
    assert "Bilanzseite" in output
    assert "Aktiva" in output
    assert "Passiva" in output


def test_eroeffnungsbilanz_outputs_csv(capsys):
    main(["eroeffnungsbilanz", JOURNAL, "--start", START, "--ende", ENDE])
    output = capsys.readouterr().out
    assert "Bilanzseite" in output


def test_konten_outputs_csv(capsys):
    main(["konten", JOURNAL, "--start", START, "--ende", ENDE])
    output = capsys.readouterr().out
    assert "Konto" in output
    assert "Saldo" in output


def test_t_konto_outputs_csv(capsys):
    main(["t-konto", JOURNAL, "--start", START, "--ende", ENDE, "--konto", "1810"])
    output = capsys.readouterr().out
    assert "Soll_Betrag" in output


def test_t_konten_outputs_all_accounts(capsys):
    main(["t-konten", JOURNAL, "--start", START, "--ende", ENDE])
    output = capsys.readouterr().out
    assert "# " in output
    assert "Soll_Betrag" in output


# -- Korrigiere-nummern --

def test_korrigiere_nummern(capsys):
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        shutil.copy(fixture_path("26_broken_numbering.csv"), tmp.name)
        main(["korrigiere-nummern", tmp.name])
        result = pl.read_csv(tmp.name)
        assert result["Journalnummer"].to_list() == [1, 2, 3, 4]
        assert result["Buchungssatznummer"].to_list() == [1, 1, 2, 2]
        assert "Fixed" in capsys.readouterr().out


# -- Jahresabschluss --

def test_jahresabschluss(capsys):
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        shutil.copy(MULTI_JOURNAL, tmp.name)
        main(["jahresabschluss", tmp.name, "--start", START])
        assert "done" in capsys.readouterr().out.lower()
        result = pl.read_csv(tmp.name, schema_overrides={"Konto": pl.Utf8})
        assert result.filter(pl.col("Belegnummer").str.contains("JEB")).height > 0


# -- Jahreseroeffnung --

def test_jahreseroeffnung(capsys, tmp_path):
    src = tmp_path / "journal.csv"
    shutil.copy(MULTI_JOURNAL, src)
    # Need closing first
    main(["jahresabschluss", str(src), "--start", START])
    capsys.readouterr()
    main(["jahreseroeffnung", str(src), "--ende", ENDE])
    output = capsys.readouterr().out
    assert "Opening entries written" in output


# -- Default konten --

def test_default_konten_file(capsys):
    """Commands should work without explicit --konten flag."""
    main(["betriebsergebnis", JOURNAL, "--start", START, "--ende", ENDE])
    result = float(capsys.readouterr().out.strip())
    assert isinstance(result, float)


# -- Help and errors --

def test_no_command_shows_help():
    with pytest.raises(SystemExit, match="2"):
        main([])


def test_missing_required_args():
    with pytest.raises(SystemExit, match="2"):
        main(["validiere-journal", JOURNAL])
