"""Tests for HTML rendering of Bilanz, GuV, and T-Konten."""

import subprocess
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
KONTEN_FILE = str(Path(__file__).parent.parent / "data" / "konten.csv")
RENDER_SCRIPT = str(Path(__file__).parent.parent / "src" / "render.py")


@pytest.fixture
def real_journal():
    return str(FIXTURES / "real_2024.csv")


def run_render(report, journal, tmp_path, extra_args=None):
    cmd = [
        "python", RENDER_SCRIPT, report,
        "--journal", journal,
        "--jahr", "2024",
        "--hebesatz", "380",
        "--output-dir", str(tmp_path),
    ]
    if extra_args:
        cmd.extend(extra_args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return result


class TestGuV:
    def test_creates_html_file(self, real_journal, tmp_path):
        run_render("guv", real_journal, tmp_path)
        assert (tmp_path / "guv.html").exists()

    def test_contains_umsatzerloese(self, real_journal, tmp_path):
        run_render("guv", real_journal, tmp_path)
        content = (tmp_path / "guv.html").read_text()
        assert "Umsatzerlöse" in content

    def test_contains_jahresueberschuss(self, real_journal, tmp_path):
        run_render("guv", real_journal, tmp_path)
        content = (tmp_path / "guv.html").read_text()
        assert "Jahresüberschuss" in content

    def test_contains_firma(self, real_journal, tmp_path):
        run_render("guv", real_journal, tmp_path, ["--firma", "Test GmbH"])
        content = (tmp_path / "guv.html").read_text()
        assert "Test GmbH" in content

    def test_contains_signature(self, real_journal, tmp_path):
        run_render("guv", real_journal, tmp_path, ["--name", "Max", "--position", "GF", "--ort", "Berlin"])
        content = (tmp_path / "guv.html").read_text()
        assert "Max" in content
        assert "Berlin" in content


class TestBilanz:
    def test_creates_html_file(self, real_journal, tmp_path):
        run_render("bilanz", real_journal, tmp_path)
        assert (tmp_path / "bilanz.html").exists()

    def test_contains_aktiva_passiva(self, real_journal, tmp_path):
        run_render("bilanz", real_journal, tmp_path)
        content = (tmp_path / "bilanz.html").read_text()
        assert "Aktiva" in content
        assert "Passiva" in content

    def test_contains_eigenkapital(self, real_journal, tmp_path):
        run_render("bilanz", real_journal, tmp_path)
        content = (tmp_path / "bilanz.html").read_text()
        assert "Eigenkapital" in content


class TestTKonten:
    def test_creates_html_file(self, real_journal, tmp_path):
        run_render("t-konten", real_journal, tmp_path)
        assert (tmp_path / "t-konten.html").exists()

    def test_contains_soll_haben(self, real_journal, tmp_path):
        run_render("t-konten", real_journal, tmp_path)
        content = (tmp_path / "t-konten.html").read_text()
        assert "Soll" in content
        assert "Haben" in content

    def test_contains_saldo(self, real_journal, tmp_path):
        run_render("t-konten", real_journal, tmp_path)
        content = (tmp_path / "t-konten.html").read_text()
        assert "Saldo" in content


class TestAll:
    def test_creates_single_file(self, real_journal, tmp_path):
        run_render("all", real_journal, tmp_path)
        assert (tmp_path / "jahresabschluss_2024.html").exists()

    def test_contains_all_sections(self, real_journal, tmp_path):
        run_render("all", real_journal, tmp_path)
        content = (tmp_path / "jahresabschluss_2024.html").read_text()
        assert "bilanz" in content.lower()
        assert "GuV" in content
        assert "T-Konten" in content
        assert "Soll" in content
        assert "Aktiva" in content

    def test_standalone_html(self, real_journal, tmp_path):
        run_render("guv", real_journal, tmp_path)
        content = (tmp_path / "guv.html").read_text()
        assert content.startswith("<!DOCTYPE html>")
        assert "</html>" in content
