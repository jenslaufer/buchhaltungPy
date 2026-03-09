"""Tests for E-Bilanz export."""

import configparser
import tempfile
from pathlib import Path

import polars as pl
import pytest

from src import buchhaltung as bh
from src.cli import main
from tests.conftest import fixture_path, KONTEN_FILE

START = "2024-01-01"
ENDE = "2024-12-31"
JOURNAL = fixture_path("01_simple_profit.csv")


def test_ebilanz_creates_csv_and_ini():
    with tempfile.TemporaryDirectory() as td:
        ini_path = bh.ebilanz_export(
            JOURNAL, KONTEN_FILE, START, ENDE,
            output_dir=td,
        )
        assert Path(ini_path).exists()
        csv_path = Path(td) / "bilanz_2024-12-31.csv"
        assert csv_path.exists()
        assert ini_path == str(Path(td) / "bilanz_2024-12-31.ini")


def test_ebilanz_csv_format():
    with tempfile.TemporaryDirectory() as td:
        bh.ebilanz_export(JOURNAL, KONTEN_FILE, START, ENDE, output_dir=td)
        csv_path = Path(td) / "bilanz_2024-12-31.csv"
        df = pl.read_csv(csv_path, separator=";")
        assert list(df.columns) == ["Konto", "Saldo", "Bezeichnung"]
        assert len(df) > 0


def test_ebilanz_csv_soll_positive_haben_negative():
    """Soll balances are positive, Haben balances are negative."""
    with tempfile.TemporaryDirectory() as td:
        bh.ebilanz_export(JOURNAL, KONTEN_FILE, START, ENDE, output_dir=td)
        csv_path = Path(td) / "bilanz_2024-12-31.csv"
        df = pl.read_csv(csv_path, separator=";", schema_overrides={"Konto": pl.Utf8})
        # 1810 is debit-heavy (Aktiva) -> positive
        bank = df.filter(pl.col("Konto") == "1810")
        assert len(bank) == 1
        assert bank["Saldo"][0] > 0
        # 4400 (Erlöse) is credit-heavy -> negative
        revenue = df.filter(pl.col("Konto") == "4400")
        assert len(revenue) == 1
        assert revenue["Saldo"][0] < 0


def test_ebilanz_ini_sections():
    with tempfile.TemporaryDirectory() as td:
        ini_path = bh.ebilanz_export(
            JOURNAL, KONTEN_FILE, START, ENDE, output_dir=td,
        )
        config = configparser.ConfigParser(interpolation=None, delimiters=("=",))
        config.optionxform = str
        config.read(ini_path, encoding="latin-1")
        assert config.has_section("magic")
        assert config.get("magic", "myebilanz") == "true"
        assert config.has_section("csv")
        assert config.get("csv", "filename") == "bilanz_2024-12-31.csv"
        assert config.get("csv", "delimiter") == ";"
        assert config.has_section("period")
        assert config.get("period", "fiscalYearBegin") == "2024-01-01"
        assert config.get("period", "fiscalYearEnd") == "2024-12-31"
        assert config.get("period", "fiscalPreviousYearBegin") == "2023-01-01"


def test_ebilanz_xbrl_mappings():
    with tempfile.TemporaryDirectory() as td:
        ini_path = bh.ebilanz_export(
            JOURNAL, KONTEN_FILE, START, ENDE, output_dir=td,
        )
        config = configparser.ConfigParser(interpolation=None, delimiters=("=",))
        config.optionxform = str
        config.read(ini_path, encoding="latin-1")
        assert config.has_section("xbrl")
        # konten.csv has XBRL mappings, so xbrl section should have entries
        assert len(config.options("xbrl")) > 0
        # All keys should start with de-gaap-ci:
        for key in config.options("xbrl"):
            assert key.startswith("de-gaap-ci:")


def test_ebilanz_with_template():
    """Using a template INI preserves existing sections."""
    with tempfile.TemporaryDirectory() as td:
        # Create a minimal template
        template = Path(td) / "template.ini"
        template.write_text(
            "[general]\ncompany = Test GmbH\n\n[company]\nname = Test GmbH\n",
            encoding="latin-1",
        )
        ini_path = bh.ebilanz_export(
            JOURNAL, KONTEN_FILE, START, ENDE,
            template_ini=str(template),
            output_dir=td,
        )
        config = configparser.ConfigParser(interpolation=None, delimiters=("=",))
        config.optionxform = str
        config.read(ini_path, encoding="latin-1")
        # Template sections preserved
        assert config.get("general", "company") == "Test GmbH"
        assert config.get("company", "name") == "Test GmbH"
        # Dynamic sections still added
        assert config.has_section("magic")
        assert config.has_section("csv")
        assert config.has_section("period")


def test_ebilanz_skips_zero_balances():
    """Accounts with zero balance should not appear in the CSV."""
    with tempfile.TemporaryDirectory() as td:
        bh.ebilanz_export(JOURNAL, KONTEN_FILE, START, ENDE, output_dir=td)
        csv_path = Path(td) / "bilanz_2024-12-31.csv"
        df = pl.read_csv(csv_path, separator=";")
        # No row should have Saldo == 0
        assert df.filter(pl.col("Saldo") == 0).height == 0


def test_ebilanz_cli(capsys):
    with tempfile.TemporaryDirectory() as td:
        main([
            "ebilanz", JOURNAL,
            "--start", START, "--ende", ENDE,
            "--output-dir", td,
        ])
        out = capsys.readouterr().out
        assert "E-Bilanz export:" in out
        assert "bilanz_2024-12-31.ini" in out
