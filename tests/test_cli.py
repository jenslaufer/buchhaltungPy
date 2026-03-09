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


# -- Payroll commands --

LOHN_ARGS = [
    "--name", "Max Mustermann",
    "--brutto", "8000",
    "--monat", "2024-01-01",
    "--steuerklasse", "1",
    "--krankenversicherung", "privat",
    "--krv", "2",
]


def test_lohn_berechnen(capsys):
    main(["lohn-berechnen"] + LOHN_ARGS)
    output = capsys.readouterr().out
    assert "Mitarbeiter" in output
    assert "Brutto" in output
    assert "Netto" in output
    assert "8000" in output


def test_lohn_berechnen_minijob(capsys):
    main(["lohn-berechnen", "--name", "Mini", "--brutto", "520", "--monat", "2024-01-01", "--minijob"])
    output = capsys.readouterr().out
    assert "520" in output
    assert "Netto" in output


def test_lohn_buchungen(capsys):
    main(["lohn-buchungen"] + LOHN_ARGS)
    output = capsys.readouterr().out
    assert "Konto" in output
    assert "Typ" in output
    assert "Betrag" in output
    assert "6024" in output


def test_lohn_buchungen_balanced(capsys):
    main(["lohn-buchungen"] + LOHN_ARGS)
    output = capsys.readouterr().out
    import io
    df = pl.read_csv(io.StringIO(output))
    soll = df.filter(pl.col("Typ") == "Soll")["Betrag"].sum()
    haben = df.filter(pl.col("Typ") == "Haben")["Betrag"].sum()
    assert abs(soll - haben) < 0.01


def test_lohn_berechnen_missing_args():
    with pytest.raises(SystemExit, match="2"):
        main(["lohn-berechnen", "--name", "Test"])


# -- Lohnzettel --

ZETTEL_ARGS = LOHN_ARGS + [
    "--personal-nr", "1",
    "--steuer-id", "12 345 678 901",
    "--firma-name", "Test GmbH",
    "--firma-strasse", "Teststr. 1",
    "--firma-plz", "12345",
    "--firma-ort", "Teststadt",
]


def test_lohn_zettel_stdout(capsys):
    main(["lohn-zettel"] + ZETTEL_ARGS)
    output = capsys.readouterr().out
    assert "<!DOCTYPE html>" in output
    assert "Lohnabrechnung" in output
    assert "Max Mustermann" in output
    assert "Nettolohn" in output
    assert "Test GmbH" in output


def test_lohn_zettel_to_file(capsys, tmp_path):
    out = tmp_path / "lohnzettel.html"
    main(["lohn-zettel"] + ZETTEL_ARGS + ["-o", str(out)])
    assert out.exists()
    content = out.read_text()
    assert "<!DOCTYPE html>" in content
    assert "Max Mustermann" in content
    assert "<style>" in content


def test_lohn_zettel_has_stammdaten(capsys):
    main(["lohn-zettel"] + ZETTEL_ARGS)
    output = capsys.readouterr().out
    assert "12 345 678 901" in output
    assert "Personal-Nr" in output
