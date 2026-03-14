"""DATEV EXTF Buchungsstapel exporter.

Converts internal journal CSV to DATEV-compatible format for import
by tax advisors or DATEV software (Kanzlei-Rechnungswesen, DATEV Unternehmen Online).
"""

from datetime import date, datetime
from pathlib import Path

import polars as pl

# Internal accounts excluded from DATEV export
_INTERNAL_ACCOUNTS = {"00000", "9000"}

# DATEV Buchungsstapel column headers (116 columns)
_DATEV_COLUMNS = [
    "Umsatz (ohne Soll/Haben-Kz)", "Soll/Haben-Kennzeichen",
    "WKZ Umsatz", "Kurs", "Basis-Umsatz", "WKZ Basis-Umsatz",
    "Konto", "Gegenkonto (ohne BU-Schlüssel)", "BU-Schlüssel",
    "Belegdatum", "Belegfeld 1", "Belegfeld 2", "Skonto", "Buchungstext",
    "Postensperre", "Diverse Adressnummer", "Geschäftspartnerbank",
    "Sachverhalt", "Zinssperre", "Beleglink",
    # 21-36: KOST fields and additional info
    "Beleginfo - Art 1", "Beleginfo - Inhalt 1",
    "Beleginfo - Art 2", "Beleginfo - Inhalt 2",
    "Beleginfo - Art 3", "Beleginfo - Inhalt 3",
    "Beleginfo - Art 4", "Beleginfo - Inhalt 4",
    "Beleginfo - Art 5", "Beleginfo - Inhalt 5",
    "Beleginfo - Art 6", "Beleginfo - Inhalt 6",
    "Beleginfo - Art 7", "Beleginfo - Inhalt 7",
    "Beleginfo - Art 8", "Beleginfo - Inhalt 8",
    "KOST1 - Kostenstelle", "KOST2 - Kostenträger", "Kost-Menge",
    "EU-Land u. UStID", "EU-Steuersatz",
    "Abw. Versteuerungsart", "Sachverhalt L+L", "Funktionsergänzung L+L",
    "BU 49 Hauptfunktionstyp", "BU 49 Hauptfunktionsnummer",
    "BU 49 Funktionsergänzung",
    "Zusatzinformation - Art 1", "Zusatzinformation - Inhalt 1",
    "Zusatzinformation - Art 2", "Zusatzinformation - Inhalt 2",
    "Zusatzinformation - Art 3", "Zusatzinformation - Inhalt 3",
    "Zusatzinformation - Art 4", "Zusatzinformation - Inhalt 4",
    "Zusatzinformation - Art 5", "Zusatzinformation - Inhalt 5",
    "Zusatzinformation - Art 6", "Zusatzinformation - Inhalt 6",
    "Zusatzinformation - Art 7", "Zusatzinformation - Inhalt 7",
    "Zusatzinformation - Art 8", "Zusatzinformation - Inhalt 8",
    "Zusatzinformation - Art 9", "Zusatzinformation - Inhalt 9",
    "Zusatzinformation - Art 10", "Zusatzinformation - Inhalt 10",
    "Zusatzinformation - Art 11", "Zusatzinformation - Inhalt 11",
    "Zusatzinformation - Art 12", "Zusatzinformation - Inhalt 12",
    "Zusatzinformation - Art 13", "Zusatzinformation - Inhalt 13",
    "Zusatzinformation - Art 14", "Zusatzinformation - Inhalt 14",
    "Zusatzinformation - Art 15", "Zusatzinformation - Inhalt 15",
    "Zusatzinformation - Art 16", "Zusatzinformation - Inhalt 16",
    "Zusatzinformation - Art 17", "Zusatzinformation - Inhalt 17",
    "Zusatzinformation - Art 18", "Zusatzinformation - Inhalt 18",
    "Zusatzinformation - Art 19", "Zusatzinformation - Inhalt 19",
    "Zusatzinformation - Art 20", "Zusatzinformation - Inhalt 20",
    "Stück", "Gewicht",
    "Zahlweise", "Forderungsart", "Veranlagungsjahr", "Zugeordnete Fälligkeit",
    "Skontotyp",
    "Auftragsnummer", "Buchungstyp", "USt-Schlüssel (Anzahlungen)",
    "EU-Land (Anzahlungen)", "Sachverhalt L+L (Anzahlungen)",
    "EU-Steuersatz (Anzahlungen)", "Erlöskonto (Anzahlungen)",
    "Herkunft-Kz",
    "Buchungs GUID", "KOST-Datum", "SEPA-Mandatsreferenz",
    "Skontosperre", "Gesellschaftername", "Beteiligtennummer",
    "Identifikationsnummer", "Zeichnernummer",
    "Postensperre bis",
    "Bezeichnung SoBil-Sachverhalt", "Kennzeichen SoBil-Buchung",
    "Festschreibung",
    "Leistungsdatum", "Datum Zuord. Steuerperiode",
    "Fälligkeit", "Generalumkehr (GU)",
    "Steuersatz", "Land",
    "Abrechnungsreferenz", "BVV-Position (Betriebsvermögensvergleich)",
    "EU-Land u. UStID (Anzahlungen)", "EU-Steuersatz (Anzahlungen) 2",
    "Abw. USt-Schlüssel (Anzahlungen)",
]

_NUM_COLUMNS = len(_DATEV_COLUMNS)  # 125 (DATEV format version 13)

# Column indices that are purely numeric (no quoting needed)
# Numeric field names (no quoting needed).
# Everything else is a text field and must be quoted with "...".
_NUMERIC_FIELD_NAMES = {
    "Umsatz (ohne Soll/Haben-Kz)",
    "Kurs",
    "Basis-Umsatz",
    "Konto",
    "Gegenkonto (ohne BU-Schlüssel)",
    "Belegdatum",
    "Skonto",
}
_NUMERIC_COLUMNS = {
    i for i, name in enumerate(_DATEV_COLUMNS) if name in _NUMERIC_FIELD_NAMES
}


def _format_amount(betrag: float) -> str:
    """Format amount with comma decimal separator, 2 decimal places."""
    return f"{betrag:.2f}".replace(".", ",")


def _format_belegdatum(datum_str: str) -> str:
    """Convert DD.MM.YYYY to DDMM (DATEV Belegdatum format)."""
    parts = datum_str.split(".")
    return parts[0] + parts[1]


def _detect_sachkontenlaenge(konten: list[str]) -> int:
    """Detect account number length from the accounts used in the journal."""
    max_len = 0
    for konto in konten:
        k = konto.lstrip("0") or "0"
        if len(k) > max_len:
            max_len = len(k)
    return max(4, max_len)


def _build_header(
    start: str,
    ende: str,
    sachkontenlaenge: int,
    berater_nr: int = 1001,
    mandanten_nr: int = 1,
) -> str:
    """Build DATEV EXTF header line."""
    start_d = date.fromisoformat(start)
    ende_d = date.fromisoformat(ende)
    wj_beginn = start_d.strftime("%Y%m%d")
    datum_von = start_d.strftime("%Y%m%d")
    datum_bis = ende_d.strftime("%Y%m%d")
    created = datetime.now().strftime("%Y%m%d%H%M%S") + "000"

    fields = [
        '"EXTF"',                   # 1: DATEV-Format-KZ (in Hochkommas)
        "700",                      # 2: Versionsnummer
        "21",                       # 3: Datenkategorie (Buchungsstapel)
        '"Buchungsstapel"',         # 4: Formatname
        "13",                       # 5: Formatversion
        created,                    # 6: Erzeugt am
        "",                         # 7: Importiert am
        "",                         # 8: Herkunftskennzeichen
        '"buchhaltungPy"',          # 9: Exportiert von
        "",                         # 10: Importiert von
        str(berater_nr),            # 11: Berater (numerisch)
        str(mandanten_nr),          # 12: Mandant (numerisch)
        wj_beginn,                  # 13: WJ-Beginn (YYYYMMDD)
        str(sachkontenlaenge),      # 14: Sachkontenlänge (4-8)
        datum_von,                  # 15: Datum von (YYYYMMDD)
        datum_bis,                  # 16: Datum bis (YYYYMMDD)
        '"Buchungsstapel"',         # 17: Bezeichnung
        "",                         # 18: Diktatkürzel (max 2 Zeichen)
        "1",                        # 19: Buchungstyp (1=Fibu)
        "0",                        # 20: Rechnungslegungszweck
        "0",                        # 21: Festschreibung
        '"EUR"',                    # 22: WKZ
        "",                         # 23: reserviert
        "",                         # 24: Derivatskennzeichen
        "",                         # 25: reserviert
        "",                         # 26: reserviert
        "",                         # 27: SKR
        "",                         # 28: Branchenlösung-Id
        "",                         # 29: reserviert
        "",                         # 30: reserviert
        "",                         # 31: Anwendungsinformation
    ]
    return ";".join(fields)


def _quote(value: str) -> str:
    """Wrap value in DATEV text quotes, escaping inner quotes."""
    return '"' + value.replace('"', '""') + '"'


def _build_datev_row(
    umsatz: float,
    sh: str,
    konto: str,
    gegenkonto: str,
    belegdatum: str,
    belegnummer: str,
    buchungstext: str,
) -> list[str]:
    """Build a single DATEV data row (125 columns)."""
    row = [""] * _NUM_COLUMNS
    row[0] = _format_amount(umsatz)
    row[1] = sh
    row[2] = "EUR"
    # 3-5: Kurs, Basis-Umsatz, WKZ Basis-Umsatz — empty
    row[6] = konto
    row[7] = gegenkonto
    # 8: BU-Schlüssel — empty (explicit postings)
    row[9] = _format_belegdatum(belegdatum)
    row[10] = belegnummer
    # 11-12: Belegfeld 2, Skonto — empty
    row[13] = buchungstext[:60]
    # Quote all non-numeric columns
    for i in range(_NUM_COLUMNS):
        if i not in _NUMERIC_COLUMNS:
            if row[i]:
                row[i] = _quote(row[i])
            else:
                row[i] = '""'
    return row


def _convert_buchungssatz(entries: list[dict]) -> list[list[str]]:
    """Convert one Buchungssatz (group of journal entries) to DATEV rows.

    Pairs Soll/Haben entries into Konto/Gegenkonto combinations.
    """
    soll = [e for e in entries if e["Typ"] == "Soll"]
    haben = [e for e in entries if e["Typ"] == "Haben"]

    if not soll or not haben:
        return []

    rows = []
    belegnummer = entries[0]["Belegnummer"]
    belegdatum = entries[0]["Belegdatum"]

    if len(soll) == 1 and len(haben) == 1:
        # 1:1 — simple booking
        rows.append(_build_datev_row(
            umsatz=soll[0]["Betrag"],
            sh="S",
            konto=soll[0]["Konto"],
            gegenkonto=haben[0]["Konto"],
            belegdatum=belegdatum,
            belegnummer=belegnummer,
            buchungstext=soll[0]["Buchungstext"],
        ))
    elif len(soll) == 1:
        # 1:N — one Soll, multiple Haben
        for h in haben:
            rows.append(_build_datev_row(
                umsatz=h["Betrag"],
                sh="S",
                konto=soll[0]["Konto"],
                gegenkonto=h["Konto"],
                belegdatum=belegdatum,
                belegnummer=belegnummer,
                buchungstext=h["Buchungstext"],
            ))
    elif len(haben) == 1:
        # N:1 — multiple Soll, one Haben
        for s in soll:
            rows.append(_build_datev_row(
                umsatz=s["Betrag"],
                sh="S",
                konto=s["Konto"],
                gegenkonto=haben[0]["Konto"],
                belegdatum=belegdatum,
                belegnummer=belegnummer,
                buchungstext=s["Buchungstext"],
            ))
    else:
        # M:N — distribute each Soll against each Haben proportionally
        haben_total = sum(h["Betrag"] for h in haben)
        for s in soll:
            for h in haben:
                anteil = s["Betrag"] * h["Betrag"] / haben_total
                if anteil > 0:
                    rows.append(_build_datev_row(
                        umsatz=round(anteil, 2),
                        sh="S",
                        konto=s["Konto"],
                        gegenkonto=h["Konto"],
                        belegdatum=belegdatum,
                        belegnummer=belegnummer,
                        buchungstext=s["Buchungstext"],
                    ))

    return rows


def datev_export(
    journal_file: str,
    konten_file: str,
    start: str,
    ende: str,
    berater_nr: int = 1001,
    mandanten_nr: int = 1,
) -> str:
    """Export journal to DATEV EXTF Buchungsstapel format.

    Returns the complete DATEV file content as a string.
    """
    journal = pl.read_csv(
        journal_file,
        schema_overrides={"Konto": pl.Utf8, "Belegnummer": pl.Utf8},
    )

    # Parse dates and filter by date range
    start_d = date.fromisoformat(start)
    ende_d = date.fromisoformat(ende)

    journal = journal.with_columns(
        pl.col("Buchungsdatum").str.strptime(pl.Date, "%d.%m.%Y").alias("_buchungsdatum_parsed"),
    ).filter(
        (pl.col("_buchungsdatum_parsed") >= start_d)
        & (pl.col("_buchungsdatum_parsed") <= ende_d)
    )

    # Filter out bookings involving internal accounts
    internal_buchungssaetze = journal.filter(
        pl.col("Konto").is_in(list(_INTERNAL_ACCOUNTS))
    )["Buchungssatznummer"].unique().to_list()

    journal = journal.filter(
        ~pl.col("Buchungssatznummer").is_in(internal_buchungssaetze)
    )

    # Detect Sachkontenlänge from accounts used
    all_konten = journal["Konto"].unique().to_list()
    sachkontenlaenge = _detect_sachkontenlaenge(all_konten) if all_konten else 4

    # Build header
    header = _build_header(start, ende, sachkontenlaenge, berater_nr, mandanten_nr)

    # Build column headers line
    col_line = ";".join(_DATEV_COLUMNS)

    # Group by Buchungssatznummer and convert
    data_rows = []
    if not journal.is_empty():
        for bsnr in journal["Buchungssatznummer"].unique().sort().to_list():
            group = journal.filter(pl.col("Buchungssatznummer") == bsnr)
            entries = group.to_dicts()
            datev_rows = _convert_buchungssatz(entries)
            data_rows.extend(datev_rows)

    # Assemble output
    lines = [header, col_line]
    for row in data_rows:
        lines.append(";".join(row))

    return "\n".join(lines) + "\n"
