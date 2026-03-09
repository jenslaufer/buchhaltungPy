"""Tests for Journalnummer and Buchungssatznummer correction."""

import shutil
import tempfile

import polars as pl
import pytest

from src.buchhaltung import korrigiere_nummern
from tests.conftest import fixture_path


def test_fixes_journalnummer_sequence():
    """Journalnummer should become 1, 2, 3, 4 regardless of input."""
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        shutil.copy(fixture_path("26_broken_numbering.csv"), tmp.name)
        korrigiere_nummern(tmp.name)
        result = pl.read_csv(tmp.name)
        assert result["Journalnummer"].to_list() == [1, 2, 3, 4]


def test_fixes_buchungssatznummer_dense_rank():
    """Buchungssatznummer should be dense-ranked preserving original order."""
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        shutil.copy(fixture_path("26_broken_numbering.csv"), tmp.name)
        korrigiere_nummern(tmp.name)
        result = pl.read_csv(tmp.name)
        assert result["Buchungssatznummer"].to_list() == [1, 1, 2, 2]


def test_rounds_betrag():
    """Betrag should be rounded to 2 decimal places."""
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        shutil.copy(fixture_path("26_broken_numbering.csv"), tmp.name)
        korrigiere_nummern(tmp.name)
        result = pl.read_csv(tmp.name)
        for val in result["Betrag"].to_list():
            assert round(val, 2) == val


def test_preserves_row_order():
    """Row order and other columns must remain unchanged."""
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        shutil.copy(fixture_path("26_broken_numbering.csv"), tmp.name)
        korrigiere_nummern(tmp.name)
        result = pl.read_csv(tmp.name, schema_overrides={"Konto": pl.Utf8})
        assert result["Konto"].to_list() == ["1810", "4400", "6300", "1810"]
        assert result["Belegnummer"].to_list() == ["RE001", "RE001", "RE002", "RE002"]


def test_already_correct_is_idempotent():
    """Running on an already-correct journal should not change anything."""
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        shutil.copy(fixture_path("03_multi_bookings.csv"), tmp.name)
        before = pl.read_csv(tmp.name)
        korrigiere_nummern(tmp.name)
        after = pl.read_csv(tmp.name)
        assert before.equals(after)


def test_non_contiguous_buchungssatznummer():
    """Gaps in Buchungssatznummer (e.g. 1,1,5,5) should become 1,1,2,2."""
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        shutil.copy(fixture_path("26_broken_numbering.csv"), tmp.name)
        # Input has BSN 3,3,7,7 -> should become 1,1,2,2
        korrigiere_nummern(tmp.name)
        result = pl.read_csv(tmp.name)
        assert result["Buchungssatznummer"].to_list() == [1, 1, 2, 2]
