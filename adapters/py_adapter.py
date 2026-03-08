"""Python backend adapter — re-exports from the Python implementation."""

from src.buchhaltung import (
    berechne_betriebsergebnis,
    berechne_gewerbesteuer,
    berechne_koerperschaftssteuer,
    berechne_soli,
    bilanz,
    get_konten,
    guv,
    steuern,
    validiere_bilanz,
    validiere_journal,
)

__all__ = [
    "berechne_betriebsergebnis",
    "berechne_gewerbesteuer",
    "berechne_koerperschaftssteuer",
    "berechne_soli",
    "bilanz",
    "get_konten",
    "guv",
    "steuern",
    "validiere_bilanz",
    "validiere_journal",
]
