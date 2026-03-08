"""Shared fixtures and backend parametrization."""

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"
GOLDEN_DIR = PROJECT_ROOT / "tests" / "golden"
KONTEN_FILE = str(PROJECT_ROOT / "data" / "konten.csv")

DEFAULT_START = "2024-01-01"
DEFAULT_ENDE = "2024-12-31"
DEFAULT_HEBESATZ = 380


def pytest_addoption(parser):
    parser.addoption(
        "--backend",
        action="store",
        default="r",
        choices=["r", "python", "both"],
        help="Which backend to test: r, python, or both",
    )


def pytest_generate_tests(metafunc):
    if "backend" in metafunc.fixturenames:
        choice = metafunc.config.getoption("backend")
        if choice == "both":
            metafunc.parametrize("backend", ["r", "python"])
        else:
            metafunc.parametrize("backend", [choice])


@pytest.fixture
def api(backend):
    """Return the adapter module for the selected backend."""
    if backend == "r":
        from adapters import r_adapter
        return r_adapter
    else:
        from adapters import py_adapter
        return py_adapter


@pytest.fixture
def konten():
    return KONTEN_FILE


def fixture_path(name: str) -> str:
    """Return absolute path to a fixture CSV."""
    return str(FIXTURES_DIR / name)
