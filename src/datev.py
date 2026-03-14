"""DATEV EXTF Buchungsstapel exporter.

Converts internal journal CSV to DATEV-compatible format for import
by tax advisors or DATEV software (Kanzlei-Rechnungswesen, DATEV Unternehmen Online).
"""

import shutil
from datetime import date, datetime
from pathlib import Path
from textwrap import dedent

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
        # M:N — pair matching amounts first, then handle remainder
        remaining_soll = list(soll)
        remaining_haben = list(haben)

        # Pass 1: exact amount matches
        matched_s = set()
        matched_h = set()
        for si, s in enumerate(remaining_soll):
            for hi, h in enumerate(remaining_haben):
                if hi not in matched_h and abs(s["Betrag"] - h["Betrag"]) < 0.005:
                    rows.append(_build_datev_row(
                        umsatz=s["Betrag"],
                        sh="S",
                        konto=s["Konto"],
                        gegenkonto=h["Konto"],
                        belegdatum=belegdatum,
                        belegnummer=belegnummer,
                        buchungstext=s["Buchungstext"],
                    ))
                    matched_s.add(si)
                    matched_h.add(hi)
                    break

        # Pass 2: remaining unmatched entries
        rest_soll = [s for i, s in enumerate(remaining_soll) if i not in matched_s]
        rest_haben = [h for i, h in enumerate(remaining_haben) if i not in matched_h]
        if len(rest_soll) == 1 and rest_haben:
            for h in rest_haben:
                rows.append(_build_datev_row(
                    umsatz=h["Betrag"], sh="S",
                    konto=rest_soll[0]["Konto"], gegenkonto=h["Konto"],
                    belegdatum=belegdatum, belegnummer=belegnummer,
                    buchungstext=rest_soll[0]["Buchungstext"],
                ))
        elif len(rest_haben) == 1 and rest_soll:
            for s in rest_soll:
                rows.append(_build_datev_row(
                    umsatz=s["Betrag"], sh="S",
                    konto=s["Konto"], gegenkonto=rest_haben[0]["Konto"],
                    belegdatum=belegdatum, belegnummer=belegnummer,
                    buchungstext=s["Buchungstext"],
                ))
        else:
            for s in rest_soll:
                for h in rest_haben:
                    rows.append(_build_datev_row(
                        umsatz=s["Betrag"], sh="S",
                        konto=s["Konto"], gegenkonto=h["Konto"],
                        belegdatum=belegdatum, belegnummer=belegnummer,
                        buchungstext=s["Buchungstext"],
                    ))

    # Filter out zero-amount rows (DATEV requires Umsatz > 0)
    return [r for r in rows if r[0] != _format_amount(0)]


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


def _build_header_kb(
    sachkontenlaenge: int,
    berater_nr: int = 1001,
    mandanten_nr: int = 1,
) -> str:
    """Build DATEV EXTF header for Kontenbeschriftungen (Datenkategorie 20)."""
    created = datetime.now().strftime("%Y%m%d%H%M%S") + "000"
    fields = [
        '"EXTF"',                   # 1: DATEV-Format-KZ
        "700",                      # 2: Versionsnummer
        "20",                       # 3: Datenkategorie (Kontenbeschriftungen)
        '"Kontenbeschriftungen"',   # 4: Formatname
        "2",                        # 5: Formatversion
        created,                    # 6: Erzeugt am
        "",                         # 7: Importiert am
        "",                         # 8: Herkunftskennzeichen
        '"buchhaltungPy"',          # 9: Exportiert von
        "",                         # 10: Importiert von
        str(berater_nr),            # 11: Berater
        str(mandanten_nr),          # 12: Mandant
        "",                         # 13: WJ-Beginn (not needed for KB)
        str(sachkontenlaenge),      # 14: Sachkontenlänge
        "",                         # 15: Datum von
        "",                         # 16: Datum bis
        '"SKR04"',                  # 17: Bezeichnung
        "",                         # 18: Diktatkürzel
        "",                         # 19: Buchungstyp
        "",                         # 20: Rechnungslegungszweck
        "",                         # 21: Festschreibung
        "",                         # 22: WKZ
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


def kontenbeschriftungen_export(
    konten_file: str,
    sachkontenlaenge: int = 4,
    berater_nr: int = 1001,
    mandanten_nr: int = 1,
) -> str:
    """Export chart of accounts in DATEV EXTF Kontenbeschriftungen format."""
    konten = pl.read_csv(konten_file, schema_overrides={"Konto": pl.Utf8})

    # Filter internal accounts
    konten = konten.filter(~pl.col("Konto").is_in(list(_INTERNAL_ACCOUNTS)))

    header = _build_header_kb(sachkontenlaenge, berater_nr, mandanten_nr)
    col_line = "Konto;Kontobeschriftung;Sprach-ID"

    lines = [header, col_line]
    for row in konten.to_dicts():
        konto = row["Konto"]
        bezeichnung = _quote(row["Bezeichnung"])
        lines.append(f'{konto};{bezeichnung};"de-DE"')

    return "\n".join(lines) + "\n"


_GDPDU_DTD = dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <!-- GDPdU DTD Version 01.09.2002 -->
    <!ELEMENT DataSet (Version, DataSupplier?, Media+)>
    <!ELEMENT Version (#PCDATA)>
    <!ELEMENT DataSupplier (Name, Location?, Comment?)>
    <!ELEMENT Name (#PCDATA)>
    <!ELEMENT Location (#PCDATA)>
    <!ELEMENT Comment (#PCDATA)>
    <!ELEMENT Media (Name?, Table+)>
    <!ELEMENT Table (URL, Name?, Description?, Validity?, DecimalSymbol?, DigitGroupingSymbol?, (VariableLength | FixedLength))>
    <!ELEMENT URL (#PCDATA)>
    <!ELEMENT Description (#PCDATA)>
    <!ELEMENT Validity (Range)>
    <!ELEMENT Range (From, To)>
    <!ELEMENT From (#PCDATA)>
    <!ELEMENT To (#PCDATA)>
    <!ELEMENT DecimalSymbol (#PCDATA)>
    <!ELEMENT DigitGroupingSymbol (#PCDATA)>
    <!ELEMENT VariableLength (ColumnDelimiter?, RecordDelimiter?, TextEncapsulator?, (VariableColumn | VariablePrimaryKey | ForeignKey)+)>
    <!ELEMENT ColumnDelimiter (#PCDATA)>
    <!ELEMENT RecordDelimiter (#PCDATA)>
    <!ELEMENT TextEncapsulator (#PCDATA)>
    <!ELEMENT VariableColumn (Name, Description?, (Numeric | AlphaNumeric | Date)?, Map*)>
    <!ELEMENT VariablePrimaryKey (Name, Description?, (Numeric | AlphaNumeric | Date)?, Map*)>
    <!ELEMENT ForeignKey (Name, References)>
    <!ELEMENT References (URL, Name)>
    <!ELEMENT Numeric (Accuracy?, ImpliedAccuracy?)>
    <!ELEMENT Accuracy (#PCDATA)>
    <!ELEMENT ImpliedAccuracy (#PCDATA)>
    <!ELEMENT AlphaNumeric (MaxLength?)>
    <!ELEMENT MaxLength (#PCDATA)>
    <!ELEMENT Date (Format)>
    <!ELEMENT Format (#PCDATA)>
    <!ELEMENT Map (From, To, Description?)>
    <!ELEMENT FixedLength (RecordDelimiter?, (FixedColumn | FixedPrimaryKey | ForeignKey)+)>
    <!ELEMENT FixedColumn (Name, Description?, (Numeric | AlphaNumeric | Date)?, Map*, FixedRange)>
    <!ELEMENT FixedPrimaryKey (Name, Description?, (Numeric | AlphaNumeric | Date)?, Map*, FixedRange)>
    <!ELEMENT FixedRange (From, (To | Length))>
    <!ELEMENT Length (#PCDATA)>
""")


def _build_index_xml(start: str, ende: str) -> str:
    """Build GDPdU index.xml referencing the export CSV files."""
    return dedent(f"""\
        <?xml version="1.0" encoding="utf-8"?>
        <!DOCTYPE DataSet SYSTEM "gdpdu-01-09-2002.dtd">
        <DataSet>
          <Version>1.0</Version>
          <DataSupplier>
            <Name>buchhaltungPy</Name>
            <Location>DATEV-Export</Location>
            <Comment>GDPdU export for tax audit</Comment>
          </DataSupplier>
          <Media>
            <Name>DATEV-Export</Name>
            <Table>
              <URL>EXTF_Buchungsstapel.csv</URL>
              <Name>Buchungsstapel</Name>
              <Description>DATEV EXTF Buchungsstapel</Description>
              <Validity>
                <Range>
                  <From>{start}</From>
                  <To>{ende}</To>
                </Range>
              </Validity>
              <DecimalSymbol>,</DecimalSymbol>
              <DigitGroupingSymbol>.</DigitGroupingSymbol>
              <VariableLength>
                <ColumnDelimiter>;</ColumnDelimiter>
                <RecordDelimiter>&#10;</RecordDelimiter>
                <TextEncapsulator>"</TextEncapsulator>
                <VariableColumn>
                  <Name>Umsatz</Name>
                  <Description>Betrag</Description>
                  <Numeric><Accuracy>2</Accuracy></Numeric>
                </VariableColumn>
                <VariableColumn>
                  <Name>Soll/Haben-Kennzeichen</Name>
                  <AlphaNumeric><MaxLength>1</MaxLength></AlphaNumeric>
                </VariableColumn>
                <VariableColumn>
                  <Name>WKZ</Name>
                  <AlphaNumeric><MaxLength>3</MaxLength></AlphaNumeric>
                </VariableColumn>
                <VariableColumn>
                  <Name>Konto</Name>
                  <AlphaNumeric><MaxLength>8</MaxLength></AlphaNumeric>
                </VariableColumn>
                <VariableColumn>
                  <Name>Gegenkonto</Name>
                  <AlphaNumeric><MaxLength>8</MaxLength></AlphaNumeric>
                </VariableColumn>
                <VariableColumn>
                  <Name>Belegdatum</Name>
                  <AlphaNumeric><MaxLength>4</MaxLength></AlphaNumeric>
                </VariableColumn>
                <VariableColumn>
                  <Name>Belegfeld1</Name>
                  <Description>Belegnummer</Description>
                  <AlphaNumeric><MaxLength>36</MaxLength></AlphaNumeric>
                </VariableColumn>
                <VariableColumn>
                  <Name>Buchungstext</Name>
                  <AlphaNumeric><MaxLength>60</MaxLength></AlphaNumeric>
                </VariableColumn>
              </VariableLength>
            </Table>
            <Table>
              <URL>EXTF_Kontenbeschriftungen.csv</URL>
              <Name>Kontenbeschriftungen</Name>
              <Description>DATEV EXTF Kontenbeschriftungen (SKR04)</Description>
              <VariableLength>
                <ColumnDelimiter>;</ColumnDelimiter>
                <RecordDelimiter>&#10;</RecordDelimiter>
                <TextEncapsulator>"</TextEncapsulator>
                <VariablePrimaryKey>
                  <Name>Konto</Name>
                  <AlphaNumeric><MaxLength>8</MaxLength></AlphaNumeric>
                </VariablePrimaryKey>
                <VariableColumn>
                  <Name>Kontobeschriftung</Name>
                  <AlphaNumeric><MaxLength>100</MaxLength></AlphaNumeric>
                </VariableColumn>
                <VariableColumn>
                  <Name>Sprach-ID</Name>
                  <AlphaNumeric><MaxLength>5</MaxLength></AlphaNumeric>
                </VariableColumn>
              </VariableLength>
            </Table>
          </Media>
        </DataSet>
    """)


def _copy_documents(src_dirs: list[Path], dest_dir: Path) -> int:
    """Copy PDF files from source directories into dest_dir. Returns count."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for src in src_dirs:
        if not src.is_dir():
            continue
        for pdf in sorted(src.glob("*.pdf")):
            shutil.copy2(pdf, dest_dir / pdf.name)
            count += 1
    return count


def datev_paket(
    journal_file: str,
    konten_file: str,
    start: str,
    ende: str,
    output_dir,
    berater_nr: int = 1001,
    mandanten_nr: int = 1,
    belege_dirs: list[str] | None = None,
    kontoauszuege_dir: str | None = None,
) -> Path:
    """Create a complete DATEV/GDPdU audit package.

    Writes EXTF_Buchungsstapel.csv, EXTF_Kontenbeschriftungen.csv,
    index.xml, gdpdu-01-09-2002.dtd, and copies Belege/Kontoauszüge PDFs.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Buchungsstapel
    bs = datev_export(journal_file, konten_file, start, ende, berater_nr, mandanten_nr)
    (output_dir / "EXTF_Buchungsstapel.csv").write_text(bs, encoding="cp1252")

    # Kontenbeschriftungen
    kb = kontenbeschriftungen_export(konten_file, berater_nr=berater_nr, mandanten_nr=mandanten_nr)
    (output_dir / "EXTF_Kontenbeschriftungen.csv").write_text(kb, encoding="cp1252")

    # Copy Belege
    if belege_dirs:
        _copy_documents([Path(d) for d in belege_dirs], output_dir / "Belege")

    # Copy Kontoauszüge
    if kontoauszuege_dir:
        _copy_documents([Path(kontoauszuege_dir)], output_dir / "Kontoauszuege")

    # GDPdU index.xml
    index_xml = _build_index_xml(start, ende)
    (output_dir / "index.xml").write_text(index_xml, encoding="utf-8")

    # GDPdU DTD
    (output_dir / "gdpdu-01-09-2002.dtd").write_text(_GDPDU_DTD, encoding="utf-8")

    return output_dir
