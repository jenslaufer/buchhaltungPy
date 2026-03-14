"""Tests for DATEV audit package export: kontenbeschriftungen_export and datev_paket."""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from src.datev import datev_paket, kontenbeschriftungen_export
from tests.conftest import KONTEN_FILE, fixture_path

START = "2024-01-01"
ENDE = "2024-12-31"

JOURNAL_SIMPLE = fixture_path("01_simple_profit.csv")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_kontenbeschriftungen(output: str) -> tuple[str, str, list[list[str]]]:
    """Split Kontenbeschriftungen output into header, column line, and data rows."""
    lines = output.splitlines()
    assert len(lines) >= 2
    header = lines[0]
    columns = lines[1]
    data = [line.split(";") for line in lines[2:] if line.strip()]
    return header, columns, data


def _unquote(val: str) -> str:
    if val.startswith('"') and val.endswith('"'):
        return val[1:-1]
    return val


# ---------------------------------------------------------------------------
# kontenbeschriftungen_export — 1. Header format
# ---------------------------------------------------------------------------

def test_kontenbeschriftungen_header_starts_with_extf():
    out = kontenbeschriftungen_export(KONTEN_FILE)
    header, _, _ = _parse_kontenbeschriftungen(out)
    assert header.startswith('"EXTF"')


def test_kontenbeschriftungen_header_datenkategorie_is_20():
    out = kontenbeschriftungen_export(KONTEN_FILE)
    header, _, _ = _parse_kontenbeschriftungen(out)
    fields = header.split(";")
    assert fields[2] == "20"


def test_kontenbeschriftungen_header_formatname_is_kontenbeschriftungen():
    out = kontenbeschriftungen_export(KONTEN_FILE)
    header, _, _ = _parse_kontenbeschriftungen(out)
    fields = header.split(";")
    assert _unquote(fields[3]) == "Kontenbeschriftungen"


def test_kontenbeschriftungen_header_berater_and_mandanten_nr():
    out = kontenbeschriftungen_export(KONTEN_FILE, berater_nr=2345, mandanten_nr=99)
    header, _, _ = _parse_kontenbeschriftungen(out)
    fields = header.split(";")
    assert fields[10] == "2345"
    assert fields[11] == "99"


def test_kontenbeschriftungen_header_sachkontenlaenge_default_4():
    out = kontenbeschriftungen_export(KONTEN_FILE)
    header, _, _ = _parse_kontenbeschriftungen(out)
    fields = header.split(";")
    assert fields[13] == "4"


def test_kontenbeschriftungen_header_sachkontenlaenge_custom():
    out = kontenbeschriftungen_export(KONTEN_FILE, sachkontenlaenge=5)
    header, _, _ = _parse_kontenbeschriftungen(out)
    fields = header.split(";")
    assert fields[13] == "5"


def test_kontenbeschriftungen_header_is_semicolon_separated_31_fields():
    out = kontenbeschriftungen_export(KONTEN_FILE)
    header, _, _ = _parse_kontenbeschriftungen(out)
    assert len(header.split(";")) == 31


# ---------------------------------------------------------------------------
# kontenbeschriftungen_export — 2. Account data present
# ---------------------------------------------------------------------------

def test_kontenbeschriftungen_contains_konto_column():
    out = kontenbeschriftungen_export(KONTEN_FILE)
    _, columns, _ = _parse_kontenbeschriftungen(out)
    assert "Konto" in columns


def test_kontenbeschriftungen_contains_kontobeschriftung_column():
    out = kontenbeschriftungen_export(KONTEN_FILE)
    _, columns, _ = _parse_kontenbeschriftungen(out)
    assert "Kontobeschriftung" in columns


def test_kontenbeschriftungen_data_rows_not_empty():
    out = kontenbeschriftungen_export(KONTEN_FILE)
    _, _, data = _parse_kontenbeschriftungen(out)
    assert len(data) > 0


def test_kontenbeschriftungen_contains_known_account_1800():
    out = kontenbeschriftungen_export(KONTEN_FILE)
    _, _, data = _parse_kontenbeschriftungen(out)
    konten = [row[0] for row in data]
    assert "1800" in konten


def test_kontenbeschriftungen_contains_known_account_4400():
    out = kontenbeschriftungen_export(KONTEN_FILE)
    _, _, data = _parse_kontenbeschriftungen(out)
    konten = [row[0] for row in data]
    assert "4400" in konten


def test_kontenbeschriftungen_label_matches_bezeichnung_for_1800():
    out = kontenbeschriftungen_export(KONTEN_FILE)
    _, _, data = _parse_kontenbeschriftungen(out)
    row = next(r for r in data if r[0] == "1800")
    label = _unquote(row[1])
    assert "Bank" in label


# ---------------------------------------------------------------------------
# kontenbeschriftungen_export — 3. Internal accounts excluded
# ---------------------------------------------------------------------------

def test_kontenbeschriftungen_excludes_account_00000():
    out = kontenbeschriftungen_export(KONTEN_FILE)
    _, _, data = _parse_kontenbeschriftungen(out)
    konten = [row[0] for row in data]
    assert "00000" not in konten


def test_kontenbeschriftungen_excludes_account_9000():
    out = kontenbeschriftungen_export(KONTEN_FILE)
    _, _, data = _parse_kontenbeschriftungen(out)
    konten = [row[0] for row in data]
    assert "9000" not in konten


# ---------------------------------------------------------------------------
# kontenbeschriftungen_export — 4. Kontobeschriftung is quoted
# ---------------------------------------------------------------------------

def test_kontobeschriftung_is_double_quoted():
    out = kontenbeschriftungen_export(KONTEN_FILE)
    _, _, data = _parse_kontenbeschriftungen(out)
    for row in data:
        label = row[1]
        assert label.startswith('"') and label.endswith('"'), (
            f"Kontobeschriftung not quoted: {label!r}"
        )


def test_kontobeschriftung_not_empty_for_known_account():
    out = kontenbeschriftungen_export(KONTEN_FILE)
    _, _, data = _parse_kontenbeschriftungen(out)
    row = next(r for r in data if r[0] == "1800")
    label = _unquote(row[1])
    assert label != ""


def test_kontobeschriftungen_output_is_string():
    result = kontenbeschriftungen_export(KONTEN_FILE)
    assert isinstance(result, str)


def test_kontobeschriftungen_no_tab_characters():
    out = kontenbeschriftungen_export(KONTEN_FILE)
    assert "\t" not in out


# ---------------------------------------------------------------------------
# datev_paket — 1. Creates output directory
# ---------------------------------------------------------------------------

def test_datev_paket_creates_output_dir(tmp_path):
    out_dir = tmp_path / "datev_export"
    assert not out_dir.exists()
    datev_paket(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE, out_dir)
    assert out_dir.is_dir()


def test_datev_paket_creates_nested_output_dir(tmp_path):
    out_dir = tmp_path / "level1" / "level2" / "datev"
    datev_paket(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE, out_dir)
    assert out_dir.is_dir()


def test_datev_paket_returns_output_dir_path(tmp_path):
    out_dir = tmp_path / "datev_export"
    result = datev_paket(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE, out_dir)
    assert result == out_dir


def test_datev_paket_return_type_is_path(tmp_path):
    out_dir = tmp_path / "datev_export"
    result = datev_paket(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE, out_dir)
    assert isinstance(result, Path)


# ---------------------------------------------------------------------------
# datev_paket — 2. Creates all 4 expected files
# ---------------------------------------------------------------------------

EXPECTED_FILES = [
    "EXTF_Buchungsstapel.csv",
    "EXTF_Kontenbeschriftungen.csv",
    "index.xml",
    "gdpdu-01-09-2002.dtd",
]


@pytest.mark.parametrize("filename", EXPECTED_FILES)
def test_datev_paket_creates_file(tmp_path, filename):
    out_dir = tmp_path / "datev_export"
    datev_paket(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE, out_dir)
    assert (out_dir / filename).exists(), f"Missing file: {filename}"


def test_datev_paket_buchungsstapel_not_empty(tmp_path):
    out_dir = tmp_path / "datev_export"
    datev_paket(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE, out_dir)
    content = (out_dir / "EXTF_Buchungsstapel.csv").read_bytes()
    assert len(content) > 0


def test_datev_paket_kontenbeschriftungen_not_empty(tmp_path):
    out_dir = tmp_path / "datev_export"
    datev_paket(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE, out_dir)
    content = (out_dir / "EXTF_Kontenbeschriftungen.csv").read_bytes()
    assert len(content) > 0


def test_datev_paket_index_xml_not_empty(tmp_path):
    out_dir = tmp_path / "datev_export"
    datev_paket(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE, out_dir)
    content = (out_dir / "index.xml").read_bytes()
    assert len(content) > 0


def test_datev_paket_dtd_not_empty(tmp_path):
    out_dir = tmp_path / "datev_export"
    datev_paket(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE, out_dir)
    content = (out_dir / "gdpdu-01-09-2002.dtd").read_bytes()
    assert len(content) > 0


# ---------------------------------------------------------------------------
# datev_paket — 3. index.xml is valid XML
# ---------------------------------------------------------------------------

def test_datev_paket_index_xml_is_valid_xml(tmp_path):
    out_dir = tmp_path / "datev_export"
    datev_paket(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE, out_dir)
    xml_bytes = (out_dir / "index.xml").read_bytes()
    # Must not raise
    ET.fromstring(xml_bytes)


def test_datev_paket_index_xml_root_element(tmp_path):
    out_dir = tmp_path / "datev_export"
    datev_paket(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE, out_dir)
    root = ET.fromstring((out_dir / "index.xml").read_bytes())
    # GDPdU index root is typically "DataSet" or "Root"
    assert root.tag is not None
    assert root.tag != ""


def test_datev_paket_index_xml_encoded_as_utf8(tmp_path):
    out_dir = tmp_path / "datev_export"
    datev_paket(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE, out_dir)
    raw = (out_dir / "index.xml").read_bytes()
    # UTF-8 BOM optional, but must decode cleanly as UTF-8
    raw.lstrip(b"\xef\xbb\xbf").decode("utf-8")


# ---------------------------------------------------------------------------
# datev_paket — 4. index.xml references both CSV files
# ---------------------------------------------------------------------------

def test_datev_paket_index_xml_references_buchungsstapel(tmp_path):
    out_dir = tmp_path / "datev_export"
    datev_paket(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE, out_dir)
    xml_text = (out_dir / "index.xml").read_bytes().decode("utf-8")
    assert "EXTF_Buchungsstapel.csv" in xml_text


def test_datev_paket_index_xml_references_kontenbeschriftungen(tmp_path):
    out_dir = tmp_path / "datev_export"
    datev_paket(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE, out_dir)
    xml_text = (out_dir / "index.xml").read_bytes().decode("utf-8")
    assert "EXTF_Kontenbeschriftungen.csv" in xml_text


def test_datev_paket_index_xml_references_dtd(tmp_path):
    out_dir = tmp_path / "datev_export"
    datev_paket(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE, out_dir)
    xml_text = (out_dir / "index.xml").read_bytes().decode("utf-8")
    assert "gdpdu-01-09-2002.dtd" in xml_text


# ---------------------------------------------------------------------------
# datev_paket — 5. EXTF files are encoded in CP1252
# ---------------------------------------------------------------------------

def test_datev_paket_buchungsstapel_encoded_cp1252(tmp_path):
    out_dir = tmp_path / "datev_export"
    datev_paket(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE, out_dir)
    raw = (out_dir / "EXTF_Buchungsstapel.csv").read_bytes()
    # Must decode cleanly as CP1252
    text = raw.decode("cp1252")
    assert "EXTF" in text


def test_datev_paket_buchungsstapel_not_utf8_bom(tmp_path):
    out_dir = tmp_path / "datev_export"
    datev_paket(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE, out_dir)
    raw = (out_dir / "EXTF_Buchungsstapel.csv").read_bytes()
    # CP1252 files must not start with a UTF-8 BOM
    assert not raw.startswith(b"\xef\xbb\xbf")


def test_datev_paket_kontenbeschriftungen_encoded_cp1252(tmp_path):
    out_dir = tmp_path / "datev_export"
    datev_paket(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE, out_dir)
    raw = (out_dir / "EXTF_Kontenbeschriftungen.csv").read_bytes()
    text = raw.decode("cp1252")
    assert "EXTF" in text


def test_datev_paket_kontenbeschriftungen_not_utf8_bom(tmp_path):
    out_dir = tmp_path / "datev_export"
    datev_paket(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE, out_dir)
    raw = (out_dir / "EXTF_Kontenbeschriftungen.csv").read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")


def test_datev_paket_buchungsstapel_contains_extf_header(tmp_path):
    out_dir = tmp_path / "datev_export"
    datev_paket(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE, out_dir)
    text = (out_dir / "EXTF_Buchungsstapel.csv").read_bytes().decode("cp1252")
    assert text.startswith('"EXTF"')


def test_datev_paket_kontenbeschriftungen_contains_extf_header(tmp_path):
    out_dir = tmp_path / "datev_export"
    datev_paket(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE, out_dir)
    text = (out_dir / "EXTF_Kontenbeschriftungen.csv").read_bytes().decode("cp1252")
    assert text.startswith('"EXTF"')


def test_datev_paket_kontenbeschriftungen_datenkategorie_20_in_file(tmp_path):
    out_dir = tmp_path / "datev_export"
    datev_paket(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE, out_dir)
    text = (out_dir / "EXTF_Kontenbeschriftungen.csv").read_bytes().decode("cp1252")
    header_line = text.splitlines()[0]
    fields = header_line.split(";")
    assert fields[2] == "20"


def test_datev_paket_buchungsstapel_datenkategorie_21_in_file(tmp_path):
    out_dir = tmp_path / "datev_export"
    datev_paket(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE, out_dir)
    text = (out_dir / "EXTF_Buchungsstapel.csv").read_bytes().decode("cp1252")
    header_line = text.splitlines()[0]
    fields = header_line.split(";")
    assert fields[2] == "21"


# ---------------------------------------------------------------------------
# datev_paket — 6. DTD file content
# ---------------------------------------------------------------------------

def test_datev_paket_dtd_contains_gdpdu_marker(tmp_path):
    out_dir = tmp_path / "datev_export"
    datev_paket(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE, out_dir)
    content = (out_dir / "gdpdu-01-09-2002.dtd").read_text(errors="replace")
    # GDPdU DTD identifies itself by its element declarations
    assert "DataSet" in content or "gdpdu" in content.lower() or "<!ELEMENT" in content


def test_datev_paket_dtd_is_readable_text(tmp_path):
    out_dir = tmp_path / "datev_export"
    datev_paket(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE, out_dir)
    dtd_path = out_dir / "gdpdu-01-09-2002.dtd"
    # Must be a non-empty text file
    text = dtd_path.read_text(encoding="utf-8", errors="replace")
    assert len(text.strip()) > 0


# ---------------------------------------------------------------------------
# datev_paket — 7. berater_nr / mandanten_nr propagated to both EXTF files
# ---------------------------------------------------------------------------

def test_datev_paket_berater_nr_in_buchungsstapel(tmp_path):
    out_dir = tmp_path / "datev_export"
    datev_paket(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE, out_dir, berater_nr=7777)
    text = (out_dir / "EXTF_Buchungsstapel.csv").read_bytes().decode("cp1252")
    header_fields = text.splitlines()[0].split(";")
    assert header_fields[10] == "7777"


def test_datev_paket_berater_nr_in_kontenbeschriftungen(tmp_path):
    out_dir = tmp_path / "datev_export"
    datev_paket(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE, out_dir, berater_nr=7777)
    text = (out_dir / "EXTF_Kontenbeschriftungen.csv").read_bytes().decode("cp1252")
    header_fields = text.splitlines()[0].split(";")
    assert header_fields[10] == "7777"


def test_datev_paket_mandanten_nr_in_buchungsstapel(tmp_path):
    out_dir = tmp_path / "datev_export"
    datev_paket(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE, out_dir, mandanten_nr=42)
    text = (out_dir / "EXTF_Buchungsstapel.csv").read_bytes().decode("cp1252")
    header_fields = text.splitlines()[0].split(";")
    assert header_fields[11] == "42"


def test_datev_paket_mandanten_nr_in_kontenbeschriftungen(tmp_path):
    out_dir = tmp_path / "datev_export"
    datev_paket(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE, out_dir, mandanten_nr=42)
    text = (out_dir / "EXTF_Kontenbeschriftungen.csv").read_bytes().decode("cp1252")
    header_fields = text.splitlines()[0].split(";")
    assert header_fields[11] == "42"


# ---------------------------------------------------------------------------
# datev_paket — 8. Belege and Kontoauszüge copied
# ---------------------------------------------------------------------------

def _create_pdf(path):
    """Create a minimal dummy PDF."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"%PDF-1.4 dummy")


def test_datev_paket_copies_belege(tmp_path):
    belege_dir = tmp_path / "belege"
    _create_pdf(belege_dir / "RE001.pdf")
    _create_pdf(belege_dir / "RE002.pdf")
    out_dir = tmp_path / "export"
    datev_paket(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE, out_dir,
                belege_dirs=[str(belege_dir)])
    assert (out_dir / "Belege" / "RE001.pdf").exists()
    assert (out_dir / "Belege" / "RE002.pdf").exists()


def test_datev_paket_copies_kontoauszuege(tmp_path):
    ko_dir = tmp_path / "kontoauszuege"
    _create_pdf(ko_dir / "KO01.pdf")
    out_dir = tmp_path / "export"
    datev_paket(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE, out_dir,
                kontoauszuege_dir=str(ko_dir))
    assert (out_dir / "Kontoauszuege" / "KO01.pdf").exists()


def test_datev_paket_copies_multiple_belege_dirs(tmp_path):
    ein_dir = tmp_path / "eingang"
    aus_dir = tmp_path / "ausgang"
    _create_pdf(ein_dir / "E1.pdf")
    _create_pdf(aus_dir / "A1.pdf")
    out_dir = tmp_path / "export"
    datev_paket(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE, out_dir,
                belege_dirs=[str(ein_dir), str(aus_dir)])
    assert (out_dir / "Belege" / "E1.pdf").exists()
    assert (out_dir / "Belege" / "A1.pdf").exists()


def test_datev_paket_no_belege_no_error(tmp_path):
    """No belege_dirs → no Belege subdirectory, no error."""
    out_dir = tmp_path / "export"
    datev_paket(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE, out_dir)
    assert not (out_dir / "Belege").exists()


def test_datev_paket_no_kontoauszuege_no_error(tmp_path):
    """No kontoauszuege_dir → no Kontoauszuege subdirectory, no error."""
    out_dir = tmp_path / "export"
    datev_paket(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE, out_dir)
    assert not (out_dir / "Kontoauszuege").exists()


def test_datev_paket_ignores_non_pdf_files(tmp_path):
    belege_dir = tmp_path / "belege"
    _create_pdf(belege_dir / "RE001.pdf")
    (belege_dir / "notes.txt").write_text("some notes")
    out_dir = tmp_path / "export"
    datev_paket(JOURNAL_SIMPLE, KONTEN_FILE, START, ENDE, out_dir,
                belege_dirs=[str(belege_dir)])
    assert (out_dir / "Belege" / "RE001.pdf").exists()
    assert not (out_dir / "Belege" / "notes.txt").exists()
