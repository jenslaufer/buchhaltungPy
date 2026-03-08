"""Python backend adapter — calls the Python implementation directly."""

import polars as pl
from src.buchhaltung import (
    berechne_betriebsergebnis as _be,
    berechne_koerperschaftssteuer as _kst,
    berechne_soli as _soli,
    berechne_gewerbesteuer as _gwst,
    steuern as _steuern,
    validiere_journal as _vj,
    guv as _guv,
    bilanz as _bilanz,
    validiere_bilanz as _vb,
    get_konten as _gk,
)


def berechne_betriebsergebnis(
    journal: str, konten: str, start: str, ende: str
) -> float:
    return _be(journal, konten, start, ende)


def berechne_koerperschaftssteuer(
    journal: str, konten: str, start: str, ende: str
) -> float:
    return _kst(journal, konten, start, ende)


def berechne_soli(journal: str, konten: str, start: str, ende: str) -> float:
    return _soli(journal, konten, start, ende)


def berechne_gewerbesteuer(
    hebesatz: int, journal: str, konten: str, start: str, ende: str
) -> float:
    return _gwst(hebesatz, journal, konten, start, ende)


def steuern(
    journal: str, konten: str, start: str, ende: str, hebesatz: int
) -> float:
    return _steuern(journal, konten, start, ende, hebesatz)


def validiere_journal(
    journal: str, konten: str, start: str, ende: str
) -> str:
    return _vj(journal, konten, start, ende)


def guv(
    journal: str, konten: str, start: str, ende: str, hebesatz: int
) -> pl.DataFrame:
    return _guv(journal, konten, start, ende, hebesatz)


def bilanz(
    journal: str, konten: str, start: str, ende: str, hebesatz: int
) -> pl.DataFrame:
    return _bilanz(journal, konten, start, ende, hebesatz)


def validiere_bilanz(
    journal: str, konten: str, start: str, ende: str, hebesatz: int
) -> str:
    return _vb(journal, konten, start, ende, hebesatz)


def get_konten(
    journal: str, konten: str, start: str, ende: str
) -> pl.DataFrame:
    return _gk(journal, konten, start, ende)
