"""CLI for double-entry bookkeeping operations.

Usage: python -m src.cli <command> [options]

Commands:
  korrigiere-nummern   Fix Journalnummer (sequential) and Buchungssatznummer (dense rank)
  validiere-journal    Validate journal: balanced bookings, sequential numbering
  validiere-bilanz     Validate balance sheet: Aktiva == Passiva
  betriebsergebnis     Compute operating result (Betriebsergebnis)
  koerperschaftssteuer Compute corporate tax (Koerperschaftsteuer)
  soli                 Compute solidarity surcharge (Solidaritaetszuschlag)
  gewerbesteuer        Compute trade tax (Gewerbesteuer)
  steuern              Compute total taxes
  guv                  Generate income statement (GuV) as CSV
  bilanz               Generate balance sheet as CSV
  eroeffnungsbilanz    Generate opening balance sheet as CSV
  konten               List account balances as CSV
  t-konto              Show T-account detail for one account as CSV
  t-konten             Show T-account detail for all accounts
  jahresabschluss      Perform year-end closing (modifies journal in-place)
  jahreseroeffnung     Create opening entries for next fiscal year
"""

import argparse
import sys
from pathlib import Path

from src import buchhaltung as bh

DEFAULT_KONTEN = str(Path(__file__).parent.parent / "data" / "konten.csv")


def _add_journal(p):
    p.add_argument("journal", help="Path to journal CSV file")


def _add_common(p, start=True, ende=True, hebesatz=False):
    _add_journal(p)
    p.add_argument("--konten", default=DEFAULT_KONTEN, help="Path to konten.csv")
    if start:
        p.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    if ende:
        p.add_argument("--ende", required=True, help="End date (YYYY-MM-DD)")
    if hebesatz:
        p.add_argument("--hebesatz", type=int, default=380, help="Gewerbesteuer Hebesatz (default: 380)")


def cmd_korrigiere_nummern(args):
    bh.korrigiere_nummern(args.journal)
    print(f"Fixed: {args.journal}")


def cmd_validiere_journal(args):
    result = bh.validiere_journal(args.journal, args.konten, args.start, args.ende)
    if result == "":
        print("PASS")
    else:
        print(result)
        sys.exit(1)


def cmd_validiere_bilanz(args):
    result = bh.validiere_bilanz(args.journal, args.konten, args.start, args.ende, args.hebesatz)
    if result == "":
        print("PASS")
    else:
        print(result)
        sys.exit(1)


def cmd_betriebsergebnis(args):
    print(bh.berechne_betriebsergebnis(args.journal, args.konten, args.start, args.ende))


def cmd_koerperschaftssteuer(args):
    print(bh.berechne_koerperschaftssteuer(args.journal, args.konten, args.start, args.ende))


def cmd_soli(args):
    print(bh.berechne_soli(args.journal, args.konten, args.start, args.ende))


def cmd_gewerbesteuer(args):
    print(bh.berechne_gewerbesteuer(args.hebesatz, args.journal, args.konten, args.start, args.ende))


def cmd_steuern(args):
    print(bh.steuern(args.journal, args.konten, args.start, args.ende, args.hebesatz))


def cmd_guv(args):
    df = bh.guv(args.journal, args.konten, args.start, args.ende, args.hebesatz)
    df.write_csv(sys.stdout)


def cmd_bilanz(args):
    df = bh.bilanz(args.journal, args.konten, args.start, args.ende, args.hebesatz)
    df.write_csv(sys.stdout)


def cmd_eroeffnungsbilanz(args):
    df = bh.eroeffnungsbilanz(args.journal, args.konten, args.start, args.ende)
    df.write_csv(sys.stdout)


def cmd_konten(args):
    df = bh.get_konten(args.journal, args.konten, args.start, args.ende)
    df.write_csv(sys.stdout)


def cmd_t_konto(args):
    df = bh.t_konto(args.journal, args.konten, args.start, args.ende, args.hebesatz, args.konto)
    df.write_csv(sys.stdout)


def cmd_t_konten(args):
    entries = bh.t_konten(args.journal, args.konten, args.start, args.ende, args.hebesatz)
    for entry in entries:
        print(f"# {entry['konto']} {entry['bezeichnung']} | Saldo: {entry['saldo']:.2f} {entry['saldo_typ']}")
        entry["detail"].write_csv(sys.stdout)
        print()


def cmd_jahresabschluss(args):
    bh.jahresabschluss(args.journal, args.konten, args.start, args.hebesatz)
    print(f"Year-end closing done: {args.journal}")


def cmd_jahreseroeffnung(args):
    new_file = bh.jahreseroeffnung(args.journal, args.konten, args.ende, args.hebesatz)
    print(f"Opening entries written: {new_file}")


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="buchhaltung",
        description="Double-entry bookkeeping CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # korrigiere-nummern
    p = sub.add_parser("korrigiere-nummern", help="Fix journal/booking numbering")
    _add_journal(p)
    p.set_defaults(func=cmd_korrigiere_nummern)

    # validiere-journal
    p = sub.add_parser("validiere-journal", help="Validate journal integrity")
    _add_common(p)
    p.set_defaults(func=cmd_validiere_journal)

    # validiere-bilanz
    p = sub.add_parser("validiere-bilanz", help="Validate balance sheet")
    _add_common(p, hebesatz=True)
    p.set_defaults(func=cmd_validiere_bilanz)

    # betriebsergebnis
    p = sub.add_parser("betriebsergebnis", help="Compute operating result")
    _add_common(p)
    p.set_defaults(func=cmd_betriebsergebnis)

    # koerperschaftssteuer
    p = sub.add_parser("koerperschaftssteuer", help="Compute corporate tax")
    _add_common(p)
    p.set_defaults(func=cmd_koerperschaftssteuer)

    # soli
    p = sub.add_parser("soli", help="Compute solidarity surcharge")
    _add_common(p)
    p.set_defaults(func=cmd_soli)

    # gewerbesteuer
    p = sub.add_parser("gewerbesteuer", help="Compute trade tax")
    _add_common(p, hebesatz=True)
    p.set_defaults(func=cmd_gewerbesteuer)

    # steuern
    p = sub.add_parser("steuern", help="Compute total taxes")
    _add_common(p, hebesatz=True)
    p.set_defaults(func=cmd_steuern)

    # guv
    p = sub.add_parser("guv", help="Generate income statement (CSV)")
    _add_common(p, hebesatz=True)
    p.set_defaults(func=cmd_guv)

    # bilanz
    p = sub.add_parser("bilanz", help="Generate balance sheet (CSV)")
    _add_common(p, hebesatz=True)
    p.set_defaults(func=cmd_bilanz)

    # eroeffnungsbilanz
    p = sub.add_parser("eroeffnungsbilanz", help="Generate opening balance sheet (CSV)")
    _add_common(p)
    p.set_defaults(func=cmd_eroeffnungsbilanz)

    # konten
    p = sub.add_parser("konten", help="List account balances (CSV)")
    _add_common(p)
    p.set_defaults(func=cmd_konten)

    # t-konto
    p = sub.add_parser("t-konto", help="Show T-account for one account (CSV)")
    _add_common(p, hebesatz=True)
    p.add_argument("--konto", required=True, help="Account number")
    p.set_defaults(func=cmd_t_konto)

    # t-konten
    p = sub.add_parser("t-konten", help="Show T-accounts for all accounts")
    _add_common(p, hebesatz=True)
    p.set_defaults(func=cmd_t_konten)

    # jahresabschluss
    p = sub.add_parser("jahresabschluss", help="Perform year-end closing")
    _add_common(p, ende=False, hebesatz=True)
    p.set_defaults(func=cmd_jahresabschluss)

    # jahreseroeffnung
    p = sub.add_parser("jahreseroeffnung", help="Create opening entries for next year")
    _add_common(p, start=False, hebesatz=True)
    p.set_defaults(func=cmd_jahreseroeffnung)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
