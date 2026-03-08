"""R backend adapter — calls Rscript with the CLI wrapper."""

import os
import subprocess
import tempfile
from pathlib import Path

import polars as pl

WRAPPER = Path(__file__).parent / "r_wrapper.R"


def _run(command: str, args: list[str]) -> str:
    """Run an R command and return stdout."""
    result = subprocess.run(
        ["Rscript", "--vanilla", str(WRAPPER), command, *args],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"R command '{command}' failed:\n{result.stderr}")
    return result.stdout.strip()


def _run_csv(command: str, args: list[str]) -> pl.DataFrame:
    """Run an R command that writes CSV output, return as DataFrame."""
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
        out = f.name
    try:
        _run(command, [*args, out])
        return pl.read_csv(out)
    finally:
        os.unlink(out)


def berechne_betriebsergebnis(
    journal: str, konten: str, start: str, ende: str
) -> float:
    return float(_run("betriebsergebnis", [journal, konten, start, ende]))


def berechne_koerperschaftssteuer(
    journal: str, konten: str, start: str, ende: str
) -> float:
    return float(_run("koerperschaftssteuer", [journal, konten, start, ende]))


def berechne_soli(journal: str, konten: str, start: str, ende: str) -> float:
    return float(_run("soli", [journal, konten, start, ende]))


def berechne_gewerbesteuer(
    hebesatz: int, journal: str, konten: str, start: str, ende: str
) -> float:
    return float(
        _run("gewerbesteuer", [str(hebesatz), journal, konten, start, ende])
    )


def steuern(
    journal: str, konten: str, start: str, ende: str, hebesatz: int
) -> float:
    return float(
        _run("steuern", [journal, konten, start, ende, str(hebesatz)])
    )


def validiere_journal(
    journal: str, konten: str, start: str, ende: str
) -> str:
    return _run("validiere_journal", [journal, konten, start, ende])


def guv(
    journal: str, konten: str, start: str, ende: str, hebesatz: int
) -> pl.DataFrame:
    return _run_csv("guv", [journal, konten, start, ende, str(hebesatz)])


def bilanz(
    journal: str, konten: str, start: str, ende: str, hebesatz: int
) -> pl.DataFrame:
    return _run_csv("bilanz", [journal, konten, start, ende, str(hebesatz)])


def validiere_bilanz(
    journal: str, konten: str, start: str, ende: str, hebesatz: int
) -> str:
    return _run(
        "validiere_bilanz", [journal, konten, start, ende, str(hebesatz)]
    )


def get_konten(
    journal: str, konten: str, start: str, ende: str
) -> pl.DataFrame:
    return _run_csv("konten", [journal, konten, start, ende])
