"""Payroll accounting (Lohnbuchhaltung) for GmbH.

Computes payroll for employees: Lohnsteuer, Solidaritaetszuschlag,
Kirchensteuer, and generates journal entries (Buchungssaetze).

Supports:
- GmbH-Geschaeftsfuehrer (managing director) with private health insurance
- Minijobber (520 EUR/month, flat-rate tax)
- Regular employees with statutory social insurance
"""

import math
from dataclasses import dataclass, field
from datetime import date

import polars as pl


# ---------------------------------------------------------------------------
# Account constants
# ---------------------------------------------------------------------------

KONTO_GF_GEHALT = "6024"
KONTO_MINIJOB_LOHN = "6035"
KONTO_MINIJOB_PAUSCHSTEUER = "6036"
KONTO_SOZIALE_AUFWENDUNGEN = "6110"
KONTO_FREIWILLIGE_SOZIALE = "6130"
KONTO_VERB_LOHN_GEHALT = "3720"
KONTO_VERB_LOHN_STEUER = "3730"
KONTO_BANK = "1810"


# ---------------------------------------------------------------------------
# Sozialversicherung rates 2024/2025/2026
# ---------------------------------------------------------------------------

@dataclass
class SVSaetze:
    """Social insurance contribution rates (employer + employee shares)."""
    krankenversicherung_ag: float = 0.073     # 7.3% AG
    krankenversicherung_an: float = 0.073     # 7.3% AN
    zusatzbeitrag: float = 0.017              # 1.7% total, split 50/50
    rentenversicherung: float = 0.093         # 9.3% each
    arbeitslosenversicherung: float = 0.013   # 1.3% each
    pflegeversicherung_ag: float = 0.018      # 1.8% AG (2025)
    pflegeversicherung_an: float = 0.018      # 1.8% AN base (kinderlos: +0.6%)
    pflegeversicherung_kinderlos_zuschlag: float = 0.006
    insolvenzgeldumlage: float = 0.006        # 0.06% AG only (U3)
    minijob_pauschale_kv: float = 0.13        # 13% AG KV
    minijob_pauschale_rv: float = 0.15        # 15% AG RV
    minijob_pauschale_steuer: float = 0.02    # 2% pauschale Lohnsteuer
    minijob_umlage_u1: float = 0.011          # U1 Umlage
    minijob_umlage_u2: float = 0.0022         # U2 Umlage


SV_2024 = SVSaetze()
SV_2025 = SVSaetze(zusatzbeitrag=0.017, pflegeversicherung_ag=0.018, pflegeversicherung_an=0.018)
SV_2026 = SVSaetze(zusatzbeitrag=0.017, pflegeversicherung_ag=0.018, pflegeversicherung_an=0.018)


# ---------------------------------------------------------------------------
# Employee types
# ---------------------------------------------------------------------------

@dataclass
class Mitarbeiter:
    """Employee configuration for payroll."""
    name: str
    brutto_monat: float
    steuerklasse: int = 1
    kinderfreibetraege: float = 0
    kirchensteuer_satz: float = 0.0     # 0.08 or 0.09 if applicable
    krankenversicherung: str = "gesetzlich"  # "gesetzlich" or "privat"
    pkv_beitrag_monat: float = 0.0      # monthly private health insurance
    krv: int = 0                        # 0=West, 1=Ost, 2=not insured (GF)
    kinderlos: bool = False
    minijob: bool = False
    konto_gehalt: str = KONTO_GF_GEHALT
    konto_bank: str = KONTO_BANK
    # Stammdaten for payslip
    personal_nr: str = ""
    steuer_id: str = ""
    geburtsdatum: str = ""
    eintritt: str = ""
    strasse: str = ""
    plz: str = ""
    ort: str = ""
    konfession: str = "-"


@dataclass
class Firma:
    """Company details for payslip header."""
    name: str = ""
    strasse: str = ""
    plz: str = ""
    ort: str = ""


# ---------------------------------------------------------------------------
# Lohnsteuer computation via BMF PAP
# ---------------------------------------------------------------------------

def _get_lohnsteuer_class(jahr: int):
    """Import the BMF Lohnsteuer calculator for the given year."""
    if jahr == 2026:
        from src.lohnsteuer.lst2026 import Lohnsteuer
        return Lohnsteuer
    elif jahr == 2025:
        from src.lohnsteuer.lst2025 import Lohnsteuer
        return Lohnsteuer
    elif jahr == 2024:
        from src.lohnsteuer.lst2024 import Lohnsteuer
        return Lohnsteuer
    elif jahr == 2023:
        from src.lohnsteuer.lst2023 import Lohnsteuer
        return Lohnsteuer
    raise ValueError(f"No Lohnsteuer calculator for year {jahr}. Available: 2023-2026")


def berechne_lohnsteuer(
    brutto_monat: float,
    steuerklasse: int = 1,
    kirchensteuer_satz: float = 0.0,
    krv: int = 2,
    pkv: int = 1,
    kinderfreibetraege: float = 0,
    jahr: int = 2024,
) -> dict:
    """Compute monthly Lohnsteuer, Soli, and Kirchensteuer.

    Args:
        brutto_monat: Monthly gross salary in EUR
        steuerklasse: Tax class (1-6)
        kirchensteuer_satz: Church tax rate (0.0, 0.08, or 0.09)
        krv: Pension insurance flag (0=West, 1=East, 2=not insured)
        pkv: Private health insurance flag (0=gesetzlich, 1=privat)
        kinderfreibetraege: Number of child allowances
        jahr: Tax year

    Returns:
        Dict with lohnsteuer, soli, kirchensteuer, gesamt (all in EUR)
    """
    Lst = _get_lohnsteuer_class(jahr)
    re4 = int(brutto_monat * 100)  # BMF expects cents

    lst = Lst(RE4=re4, KRV=krv, LZZ=2, STKL=steuerklasse, PKV=pkv, ZKV=kinderfreibetraege)
    lst.MAIN()

    # 2025+ PAPs removed getStv/getSolzv (Versorgungsbezuege fields)
    stv = float(lst.getStv()) if hasattr(lst, 'getStv') else 0.0
    solzv = float(lst.getSolzv()) if hasattr(lst, 'getSolzv') else 0.0

    lohnsteuer = math.floor(
        float(lst.getLstlzz()) + stv + float(lst.getSts())
    ) / 100
    soli = math.floor(
        float(lst.getSolzlzz()) + float(lst.getSolzs()) + solzv
    ) / 100
    kirchensteuer = round(lohnsteuer * kirchensteuer_satz, 2)

    return {
        "lohnsteuer": lohnsteuer,
        "soli": soli,
        "kirchensteuer": kirchensteuer,
        "gesamt": round(lohnsteuer + soli + kirchensteuer, 2),
    }


# ---------------------------------------------------------------------------
# SV computation
# ---------------------------------------------------------------------------

def berechne_sv_ag(brutto_monat: float, kinderlos: bool = False, sv: SVSaetze | None = None) -> dict:
    """Compute employer social insurance contributions.

    Returns dict with kv, rv, av, pv, insolvenz, gesamt (all in EUR).
    """
    if sv is None:
        sv = SV_2024
    kv = round(brutto_monat * (sv.krankenversicherung_ag + sv.zusatzbeitrag / 2), 2)
    rv = round(brutto_monat * sv.rentenversicherung, 2)
    av = round(brutto_monat * sv.arbeitslosenversicherung, 2)
    pv = round(brutto_monat * sv.pflegeversicherung_ag, 2)
    insolvenz = round(brutto_monat * sv.insolvenzgeldumlage, 2)
    gesamt = round(kv + rv + av + pv + insolvenz, 2)
    return {"kv": kv, "rv": rv, "av": av, "pv": pv, "insolvenz": insolvenz, "gesamt": gesamt}


def berechne_sv_an(brutto_monat: float, kinderlos: bool = False, sv: SVSaetze | None = None) -> dict:
    """Compute employee social insurance contributions.

    Returns dict with kv, rv, av, pv, gesamt (all in EUR).
    """
    if sv is None:
        sv = SV_2024
    kv = round(brutto_monat * (sv.krankenversicherung_an + sv.zusatzbeitrag / 2), 2)
    rv = round(brutto_monat * sv.rentenversicherung, 2)
    av = round(brutto_monat * sv.arbeitslosenversicherung, 2)
    pv_rate = sv.pflegeversicherung_an
    if kinderlos:
        pv_rate += sv.pflegeversicherung_kinderlos_zuschlag
    pv = round(brutto_monat * pv_rate, 2)
    gesamt = round(kv + rv + av + pv, 2)
    return {"kv": kv, "rv": rv, "av": av, "pv": pv, "gesamt": gesamt}


def berechne_minijob_ag(brutto_monat: float, sv: SVSaetze | None = None) -> dict:
    """Compute employer costs for a Minijob (520 EUR basis).

    Returns dict with pauschale_kv, pauschale_rv, pauschale_steuer, umlage_u1, umlage_u2, insolvenz, gesamt.
    """
    if sv is None:
        sv = SV_2024
    kv = round(brutto_monat * sv.minijob_pauschale_kv, 2)
    rv = round(brutto_monat * sv.minijob_pauschale_rv, 2)
    steuer = round(brutto_monat * sv.minijob_pauschale_steuer, 2)
    u1 = round(brutto_monat * sv.minijob_umlage_u1, 2)
    u2 = round(brutto_monat * sv.minijob_umlage_u2, 2)
    insolvenz = round(brutto_monat * sv.insolvenzgeldumlage, 2)
    gesamt = round(kv + rv + steuer + u1 + u2 + insolvenz, 2)
    return {
        "pauschale_kv": kv, "pauschale_rv": rv, "pauschale_steuer": steuer,
        "umlage_u1": u1, "umlage_u2": u2, "insolvenz": insolvenz, "gesamt": gesamt,
    }


# ---------------------------------------------------------------------------
# Lohnabrechnung (payslip)
# ---------------------------------------------------------------------------

@dataclass
class Lohnabrechnung:
    """Complete payroll result for one employee and one month."""
    mitarbeiter: str
    monat: str              # "MM.YYYY"
    brutto: float
    lohnsteuer: float
    soli: float
    kirchensteuer: float
    sv_an: float            # employee SV contributions
    sv_ag: float            # employer SV contributions
    netto: float            # net pay
    ag_kosten: float        # total employer cost

    def to_dict(self) -> dict:
        return {
            "Mitarbeiter": self.mitarbeiter,
            "Monat": self.monat,
            "Brutto": self.brutto,
            "Lohnsteuer": self.lohnsteuer,
            "Soli": self.soli,
            "Kirchensteuer": self.kirchensteuer,
            "SV_AN": self.sv_an,
            "SV_AG": self.sv_ag,
            "Netto": self.netto,
            "AG_Kosten": self.ag_kosten,
        }


def berechne_lohnabrechnung(
    mitarbeiter: Mitarbeiter,
    monat: date,
    jahr: int | None = None,
    sv: SVSaetze | None = None,
) -> Lohnabrechnung:
    """Compute full payroll for one employee and one month.

    Args:
        mitarbeiter: Employee configuration
        monat: First day of the month (e.g. date(2024, 1, 1))
        jahr: Tax year (defaults to monat.year)
        sv: Social insurance rates (defaults to SV_2024)

    Returns:
        Lohnabrechnung with all computed values
    """
    if jahr is None:
        jahr = monat.year

    brutto = mitarbeiter.brutto_monat
    monat_str = monat.strftime("%m.%Y")

    if mitarbeiter.minijob:
        ag = berechne_minijob_ag(brutto, sv)
        return Lohnabrechnung(
            mitarbeiter=mitarbeiter.name,
            monat=monat_str,
            brutto=brutto,
            lohnsteuer=0.0,
            soli=0.0,
            kirchensteuer=0.0,
            sv_an=0.0,
            sv_ag=ag["gesamt"],
            netto=brutto,
            ag_kosten=round(brutto + ag["gesamt"], 2),
        )

    # Lohnsteuer
    pkv = 1 if mitarbeiter.krankenversicherung == "privat" else 0
    steuer = berechne_lohnsteuer(
        brutto,
        steuerklasse=mitarbeiter.steuerklasse,
        kirchensteuer_satz=mitarbeiter.kirchensteuer_satz,
        krv=mitarbeiter.krv,
        pkv=pkv,
        kinderfreibetraege=mitarbeiter.kinderfreibetraege,
        jahr=jahr,
    )

    # Social insurance
    if mitarbeiter.krankenversicherung == "privat" and mitarbeiter.krv == 2:
        # GF with private insurance: no statutory SV
        sv_an_total = 0.0
        sv_ag_total = 0.0
    else:
        sv_an = berechne_sv_an(brutto, mitarbeiter.kinderlos, sv)
        sv_ag = berechne_sv_ag(brutto, mitarbeiter.kinderlos, sv)
        sv_an_total = sv_an["gesamt"]
        sv_ag_total = sv_ag["gesamt"]

    netto = round(brutto - steuer["gesamt"] - sv_an_total, 2)
    ag_kosten = round(brutto + sv_ag_total, 2)

    return Lohnabrechnung(
        mitarbeiter=mitarbeiter.name,
        monat=monat_str,
        brutto=brutto,
        lohnsteuer=steuer["lohnsteuer"],
        soli=steuer["soli"],
        kirchensteuer=steuer["kirchensteuer"],
        sv_an=sv_an_total,
        sv_ag=sv_ag_total,
        netto=netto,
        ag_kosten=ag_kosten,
    )


# ---------------------------------------------------------------------------
# Journal entry generation
# ---------------------------------------------------------------------------

def erzeuge_buchungssaetze(
    abrechnung: Lohnabrechnung,
    monat: date,
    konto_gehalt: str = KONTO_GF_GEHALT,
    konto_bank: str = KONTO_BANK,
) -> pl.DataFrame:
    """Generate journal entries for a payroll.

    Creates booking entries:
    1. Brutto salary expense (Soll) vs net pay + tax + SV liabilities (Haben)
    2. AG SV expense (Soll) vs bank (Haben) — if applicable
    3. Minijob flat-rate tax (Soll) vs bank (Haben) — if minijob

    Returns:
        DataFrame with journal columns (without Journalnummer/Buchungssatznummer)
    """
    datum = monat.strftime("%d.%m.%Y")
    letzter = _letzter_tag(monat).strftime("%d.%m.%Y")
    rows = []

    steuer_total = round(abrechnung.lohnsteuer + abrechnung.soli + abrechnung.kirchensteuer, 2)

    if abrechnung.brutto > 0:
        # Gehalt: Aufwand an Verb. Lohn + Verb. Steuer + Bank
        belegnummer = f"GH{monat.strftime('%m%y')}"

        # Soll: Gehaltsaufwand
        rows.append(_row(letzter, belegnummer, f"Gehalt {abrechnung.mitarbeiter}", konto_gehalt, "Soll", abrechnung.brutto))

        # Haben: Nettolohn -> Bank
        rows.append(_row(letzter, belegnummer, f"Gehalt {abrechnung.mitarbeiter}", konto_bank, "Haben", abrechnung.netto))

        # Haben: Lohnsteuer + Soli + KiSt -> Verb. Steuer
        if steuer_total > 0:
            rows.append(_row(letzter, belegnummer, f"Gehalt {abrechnung.mitarbeiter}", KONTO_VERB_LOHN_STEUER, "Haben", steuer_total))

        # Haben: SV AN -> Verb. Lohn
        if abrechnung.sv_an > 0:
            rows.append(_row(letzter, belegnummer, f"Gehalt {abrechnung.mitarbeiter}", KONTO_VERB_LOHN_GEHALT, "Haben", abrechnung.sv_an))

    # AG SV contributions
    if abrechnung.sv_ag > 0:
        belegnummer_sv = f"SV{monat.strftime('%m%y')}"
        rows.append(_row(letzter, belegnummer_sv, f"AG-Anteil SV {abrechnung.mitarbeiter}", KONTO_SOZIALE_AUFWENDUNGEN, "Soll", abrechnung.sv_ag))
        rows.append(_row(letzter, belegnummer_sv, f"AG-Anteil SV {abrechnung.mitarbeiter}", konto_bank, "Haben", abrechnung.sv_ag))

    return pl.DataFrame(rows, schema={
        "Belegnummer": pl.Utf8, "Belegdatum": pl.Utf8, "Buchungsdatum": pl.Utf8,
        "Buchungstext": pl.Utf8, "Konto": pl.Utf8, "Typ": pl.Utf8, "Betrag": pl.Float64,
    })


def _row(datum: str, belegnummer: str, text: str, konto: str, typ: str, betrag: float) -> dict:
    return {
        "Belegnummer": belegnummer,
        "Belegdatum": datum,
        "Buchungsdatum": datum,
        "Buchungstext": text,
        "Konto": konto,
        "Typ": typ,
        "Betrag": round(betrag, 2),
    }


def _letzter_tag(monat: date) -> date:
    """Return last day of the month."""
    if monat.month == 12:
        return date(monat.year, 12, 31)
    return date(monat.year, monat.month + 1, 1).replace(day=1) - __import__("datetime").timedelta(days=1)


# ---------------------------------------------------------------------------
# Lohnzettel (payslip) generation
# ---------------------------------------------------------------------------

MONATE_DE = [
    "", "Januar", "Februar", "Maerz", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
]


def _fmt(value: float) -> str:
    """Format EUR amount German style: 1.234,56"""
    formatted = f"{value:,.2f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def _esc(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def lohnzettel(
    mitarbeiter: Mitarbeiter,
    abrechnung: Lohnabrechnung,
    firma: Firma | None = None,
) -> str:
    """Generate a payslip as standalone HTML with Tailwind CSS 4.

    Returns the file content as string. Open in a browser and print to PDF.
    """
    if firma is None:
        firma = Firma()

    monat_parts = abrechnung.monat.split(".")
    monat_nr = int(monat_parts[0])
    jahr = monat_parts[1]
    monat_name = MONATE_DE[monat_nr]

    steuer_total = round(abrechnung.lohnsteuer + abrechnung.soli + abrechnung.kirchensteuer, 2)
    abzuege_total = round(steuer_total + abrechnung.sv_an, 2)

    # Firma
    firma_zeile = ""
    if firma.name:
        parts = [firma.name]
        if firma.strasse:
            parts.append(firma.strasse)
        if firma.plz and firma.ort:
            parts.append(f"{firma.plz} {firma.ort}")
        firma_zeile = ", ".join(parts)

    # Stammdaten rows
    stamm = []
    if mitarbeiter.personal_nr:
        stamm.append(("Personal-Nr.", mitarbeiter.personal_nr))
    if mitarbeiter.steuer_id:
        stamm.append(("Steuer-ID", mitarbeiter.steuer_id))
    stamm.append(("Steuerklasse", str(mitarbeiter.steuerklasse)))
    stamm.append(("Kinderfreibetr.", str(mitarbeiter.kinderfreibetraege)))
    stamm.append(("Konfession", mitarbeiter.konfession))
    stamm.append(("KV", mitarbeiter.krankenversicherung))
    if mitarbeiter.geburtsdatum:
        stamm.append(("Geb.-Datum", mitarbeiter.geburtsdatum))
    if mitarbeiter.eintritt:
        stamm.append(("Eintritt", mitarbeiter.eintritt))

    stamm_rows = "\n".join(
        f'<tr><td class="pr-8 py-0.5 text-gray-500">{_esc(k)}</td><td class="text-gray-800">{_esc(v)}</td></tr>'
        for k, v in stamm
    )

    # Abrechnung rows
    abr_rows = [
        _abr_row("Gehalt", _fmt(abrechnung.brutto), bold=True),
    ]
    abr_rows.append(_abr_row("Lohnsteuer", f"-{_fmt(abrechnung.lohnsteuer)}"))
    if abrechnung.soli > 0:
        abr_rows.append(_abr_row("Solidaritaetszuschlag", f"-{_fmt(abrechnung.soli)}"))
    if abrechnung.kirchensteuer > 0:
        abr_rows.append(_abr_row("Kirchensteuer", f"-{_fmt(abrechnung.kirchensteuer)}"))
    if abrechnung.sv_an > 0:
        abr_rows.append(_abr_row("Sozialversicherung (AN)", f"-{_fmt(abrechnung.sv_an)}"))

    abr_html = "\n".join(abr_rows)

    # AG rows
    ag_rows = [_abr_row("Bruttolohn", _fmt(abrechnung.brutto))]
    if abrechnung.sv_ag > 0:
        ag_rows.append(_abr_row("Sozialversicherung (AG)", _fmt(abrechnung.sv_ag)))
    ag_html = "\n".join(ag_rows)

    # Build stammdaten as 2-column grid (4 columns visually: label val | label val)
    stamm_left = stamm[: (len(stamm) + 1) // 2]
    stamm_right = stamm[(len(stamm) + 1) // 2:]
    stamm_grid = ""
    for i in range(max(len(stamm_left), len(stamm_right))):
        lk, lv = stamm_left[i] if i < len(stamm_left) else ("", "")
        rk, rv = stamm_right[i] if i < len(stamm_right) else ("", "")
        stamm_grid += (
            f'<tr>'
            f'<td style="color:#666;padding:2px 12px 2px 0">{_esc(lk)}</td>'
            f'<td style="padding:2px 30px 2px 0">{_esc(lv)}</td>'
            f'<td style="color:#666;padding:2px 12px 2px 0">{_esc(rk)}</td>'
            f'<td style="padding:2px 0">{_esc(rv)}</td>'
            f'</tr>'
        )

    # Abrechnung rows
    abr_html = "\n".join(abr_rows)

    # AG rows
    ag_html = "\n".join(ag_rows)

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Lohnabrechnung {monat_name} {jahr}</title>
<style>
@page {{ size: A4; margin: 18mm; }}
@media print {{
  body {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
}}
body {{
  font-family: Arial, Helvetica, sans-serif;
  font-size: 12px;
  color: #222;
  max-width: 210mm;
  margin: 0 auto;
  padding: 40px;
  background: #fff;
  line-height: 1.5;
}}
@media print {{ body {{ padding: 0; }} }}
h1 {{ font-size: 18px; font-weight: bold; margin: 0; }}
.header {{ border-bottom: 2px solid #222; padding-bottom: 12px; margin-bottom: 20px; }}
.header-sub {{ font-size: 13px; color: #555; margin-top: 2px; }}
.addr-grid {{ display: table; width: 100%; margin-bottom: 18px; }}
.addr-cell {{ display: table-cell; width: 50%; vertical-align: top; }}
.addr-label {{ font-size: 10px; color: #888; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px; }}
.addr-name {{ font-weight: bold; }}
.section {{ margin-bottom: 18px; }}
.section-title {{ font-size: 10px; color: #888; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; border-bottom: 1px solid #ccc; padding-bottom: 3px; }}
table.abr {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
table.abr th {{ text-align: left; padding: 6px 0; border-bottom: 2px solid #222; font-weight: bold; font-size: 11px; }}
table.abr th.right {{ text-align: right; }}
table.abr td {{ padding: 5px 0; }}
table.abr td.right {{ text-align: right; font-variant-numeric: tabular-nums; }}
table.abr tr.row {{ border-bottom: 1px solid #e5e5e5; }}
table.abr tr.subtotal {{ border-top: 1px solid #999; }}
table.abr tr.subtotal td {{ padding-top: 8px; color: #666; }}
table.abr tr.total {{ border-top: 2px solid #222; }}
table.abr tr.total td {{ padding-top: 10px; font-weight: bold; font-size: 14px; }}
table.abr .neg {{ color: #c00; }}
table.abr .bold {{ font-weight: bold; }}
table.stamm {{ border-collapse: collapse; font-size: 12px; width: 100%; }}
.footer {{ margin-top: 40px; padding-top: 10px; border-top: 1px solid #ccc; font-size: 10px; color: #999; display: flex; justify-content: space-between; }}
</style>
</head>
<body>

<div class="header">
  <h1>Lohnabrechnung</h1>
  <div class="header-sub">{monat_name} {jahr}</div>
</div>

<div class="addr-grid">
  <div class="addr-cell">
    <div class="addr-label">Arbeitgeber</div>
    {f'<div class="addr-name">{_esc(firma.name)}</div>' if firma.name else ''}
    {f'<div>{_esc(firma.strasse)}</div>' if firma.strasse else ''}
    {f'<div>{_esc(firma.plz)} {_esc(firma.ort)}</div>' if firma.plz and firma.ort else ''}
  </div>
  <div class="addr-cell">
    <div class="addr-label">Arbeitnehmer</div>
    <div class="addr-name">{_esc(mitarbeiter.name)}</div>
    {f'<div>{_esc(mitarbeiter.strasse)}</div>' if mitarbeiter.strasse else ''}
    {f'<div>{_esc(mitarbeiter.plz)} {_esc(mitarbeiter.ort)}</div>' if mitarbeiter.plz and mitarbeiter.ort else ''}
  </div>
</div>

<div class="section">
  <div class="section-title">Stammdaten</div>
  <table class="stamm">
    {stamm_grid}
  </table>
</div>

<div class="section">
  <div class="section-title">Abrechnung</div>
  <table class="abr">
    <thead>
      <tr><th>Position</th><th class="right">Betrag</th></tr>
    </thead>
    <tbody>
      {abr_html}
      <tr class="subtotal">
        <td>Gesetzliche Abzuege</td>
        <td class="right neg">-{_fmt(abzuege_total)} EUR</td>
      </tr>
    </tbody>
    <tfoot>
      <tr class="total">
        <td>Nettolohn</td>
        <td class="right">{_fmt(abrechnung.netto)} EUR</td>
      </tr>
    </tfoot>
  </table>
</div>

<div class="section">
  <div class="section-title">Arbeitgeberkosten</div>
  <table class="abr">
    <tbody>
      {ag_html}
    </tbody>
    <tfoot>
      <tr class="total">
        <td>Gesamtkosten AG</td>
        <td class="right">{_fmt(abrechnung.ag_kosten)} EUR</td>
      </tr>
    </tfoot>
  </table>
</div>

<div class="footer">
  <span>{_esc(firma_zeile) if firma_zeile else ''}</span>
  <span>Erstellt am {date.today().strftime("%d.%m.%Y")}</span>
</div>

</body>
</html>"""


def _abr_row(label: str, betrag: str, bold: bool = False) -> str:
    cls = ' class="bold"' if bold else ''
    return (
        f'<tr class="row">'
        f'<td{cls}>{label}</td>'
        f'<td class="right{"  bold" if bold else ""}">{betrag} EUR</td>'
        f'</tr>'
    )
