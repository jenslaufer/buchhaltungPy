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
  ebilanz              Export E-Bilanz CSV + INI for myEBilanz
  lohn-berechnen       Compute payroll for an employee
  lohn-buchungen       Generate journal entries for a payroll
  lohn-zettel          Generate payslip as HTML
  lohn-zettel-journal  Generate payslips from journal data
"""

import argparse
import sys
from datetime import date
from pathlib import Path

import polars as pl

from src import buchhaltung as bh
from src import lohnbuchhaltung as lb

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


def cmd_ebilanz(args):
    ini_path = bh.ebilanz_export(
        args.journal, args.konten, args.start, args.ende,
        args.hebesatz,
        template_ini=args.template,
        output_dir=args.output_dir,
    )
    print(f"E-Bilanz export: {ini_path}")


# ---------------------------------------------------------------------------
# Payroll commands
# ---------------------------------------------------------------------------

def _build_mitarbeiter(args) -> lb.Mitarbeiter:
    return lb.Mitarbeiter(
        name=args.name,
        brutto_monat=args.brutto,
        steuerklasse=args.steuerklasse,
        kinderfreibetraege=args.kinderfreibetraege,
        kirchensteuer_satz=args.kirchensteuer,
        krankenversicherung=args.krankenversicherung,
        krv=args.krv,
        alv=args.alv,
        kinderlos=args.kinderlos,
        minijob=args.minijob,
        konto_gehalt=args.konto_gehalt,
        konto_bank=args.konto_bank,
        personal_nr=getattr(args, "personal_nr", ""),
        steuer_id=getattr(args, "steuer_id", ""),
        geburtsdatum=getattr(args, "geburtsdatum", ""),
        eintritt=getattr(args, "eintritt", ""),
        strasse=getattr(args, "strasse", ""),
        plz=getattr(args, "plz", ""),
        ort=getattr(args, "ort", ""),
        konfession=getattr(args, "konfession", "-"),
        sv_nummer=getattr(args, "sv_nummer", ""),
    )


def _add_lohn_args(p):
    p.add_argument("--name", required=True, help="Employee name")
    p.add_argument("--brutto", type=float, required=True, help="Monthly gross salary (EUR)")
    p.add_argument("--monat", required=True, help="Month (YYYY-MM-DD, first of month)")
    p.add_argument("--steuerklasse", type=int, default=1, help="Tax class 1-6 (default: 1)")
    p.add_argument("--kinderfreibetraege", type=float, default=0, help="Child allowances (default: 0)")
    p.add_argument("--kirchensteuer", type=float, default=0.0, help="Church tax rate, e.g. 0.09 (default: 0)")
    p.add_argument("--krankenversicherung", choices=["gesetzlich", "privat"], default="privat", help="Health insurance type (default: privat)")
    p.add_argument("--krv", type=int, default=1, help="Pension insurance: 0=gesetzlich, 1=nicht versichert (default: 1)")
    p.add_argument("--alv", type=int, default=1, help="Unemployment insurance: 0=versichert, 1=nicht (default: 1)")
    p.add_argument("--kinderlos", action="store_true", help="Childless surcharge for Pflegeversicherung")
    p.add_argument("--minijob", action="store_true", help="Minijob (520 EUR basis, flat-rate tax)")
    p.add_argument("--konto-gehalt", default="6024", help="Salary expense account (default: 6024)")
    p.add_argument("--konto-bank", default="1810", help="Bank account (default: 1810)")


def cmd_lohn_berechnen(args):
    ma = _build_mitarbeiter(args)
    monat = date.fromisoformat(args.monat)
    abr = lb.berechne_lohnabrechnung(ma, monat)
    df = pl.DataFrame([abr.to_dict()])
    df.write_csv(sys.stdout)


def cmd_lohn_buchungen(args):
    ma = _build_mitarbeiter(args)
    monat = date.fromisoformat(args.monat)
    abr = lb.berechne_lohnabrechnung(ma, monat)
    df = lb.erzeuge_buchungssaetze(abr, monat, konto_gehalt=args.konto_gehalt, konto_bank=args.konto_bank)
    df.write_csv(sys.stdout)


def _add_lohnzettel_args(p):
    """Add payslip-specific args on top of standard lohn args."""
    _add_lohn_args(p)
    p.add_argument("--personal-nr", default="", help="Personnel number")
    p.add_argument("--steuer-id", default="", help="Tax ID")
    p.add_argument("--geburtsdatum", default="", help="Date of birth (DD.MM.YYYY)")
    p.add_argument("--eintritt", default="", help="Employment start date (DD.MM.YYYY)")
    p.add_argument("--strasse", default="", help="Employee street address")
    p.add_argument("--plz", default="", help="Employee postal code")
    p.add_argument("--ort", default="", help="Employee city")
    p.add_argument("--konfession", default="-", help="Confession (default: -)")
    p.add_argument("--sv-nummer", default="", help="Social insurance number")
    p.add_argument("--firma-name", default="", help="Company name")
    p.add_argument("--firma-strasse", default="", help="Company street")
    p.add_argument("--firma-plz", default="", help="Company postal code")
    p.add_argument("--firma-ort", default="", help="Company city")
    p.add_argument("--show-ag-kosten", action="store_true", help="Show employer costs on payslip")
    p.add_argument("-o", "--output", default="", help="Output file path (default: stdout)")


def cmd_lohn_zettel(args):
    ma = _build_mitarbeiter(args)
    monat = date.fromisoformat(args.monat)
    abr = lb.berechne_lohnabrechnung(ma, monat)
    firma = lb.Firma(
        name=args.firma_name,
        strasse=args.firma_strasse,
        plz=args.firma_plz,
        ort=args.firma_ort,
    )
    content = lb.lohnzettel(ma, abr, firma, show_ag_kosten=args.show_ag_kosten)
    if args.output:
        Path(args.output).write_text(content, encoding="utf-8")
        print(f"Payslip written: {args.output}")
    else:
        print(content)


def cmd_lohn_zettel_journal(args):
    ma = _build_mitarbeiter(args)
    firma = lb.Firma(
        name=args.firma_name,
        strasse=args.firma_strasse,
        plz=args.firma_plz,
        ort=args.firma_ort,
    )
    paths = lb.lohnzettel_aus_journal(
        args.journal,
        mitarbeiter=ma,
        firma=firma,
        output_dir=args.output_dir,
        show_ag_kosten=args.show_ag_kosten,
    )
    for p in paths:
        print(f"Written: {p}")


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

    # ebilanz
    p = sub.add_parser("ebilanz", help="Export E-Bilanz for myEBilanz")
    _add_common(p, hebesatz=True)
    p.add_argument("--template", default="", help="Path to myEBilanz template INI")
    p.add_argument("--output-dir", default="", help="Output directory for CSV and INI")
    p.set_defaults(func=cmd_ebilanz)

    # lohn-berechnen
    p = sub.add_parser("lohn-berechnen", help="Compute payroll for an employee (CSV)")
    _add_lohn_args(p)
    p.set_defaults(func=cmd_lohn_berechnen)

    # lohn-buchungen
    p = sub.add_parser("lohn-buchungen", help="Generate payroll journal entries (CSV)")
    _add_lohn_args(p)
    p.set_defaults(func=cmd_lohn_buchungen)

    # lohn-zettel
    p = sub.add_parser("lohn-zettel", help="Generate payslip as HTML (print to PDF)")
    _add_lohnzettel_args(p)
    p.set_defaults(func=cmd_lohn_zettel)

    # lohn-zettel-journal
    p = sub.add_parser("lohn-zettel-journal", help="Generate payslips from journal data")
    _add_lohnzettel_args(p)
    _add_journal(p)
    p.add_argument("--output-dir", default="", help="Output directory for payslip HTML files")
    p.set_defaults(func=cmd_lohn_zettel_journal)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
