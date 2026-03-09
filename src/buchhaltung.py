"""Double-entry bookkeeping engine — Python/polars reimplementation."""

import math
import shutil
from datetime import date
from pathlib import Path

import polars as pl

# ---------------------------------------------------------------------------
# Account number constants
# ---------------------------------------------------------------------------

KONTO_GUV = "00000"           # GuV settlement account
KONTO_SBK = "9000"            # Schlussbilanzkonto / Eröffnungsbilanzkonto
KONTO_GEWINNVORTRAG = "2970"  # Gewinnvortrag / Verlustvortrag
KONTO_GEWERBESTEUER_AUFWAND = "7610"
KONTO_GEWERBESTEUER_RUECKSTELLUNG = "3035"
KONTO_KOERPERSCHAFTSTEUER_AUFWAND = "7600"
KONTO_KOERPERSCHAFTSTEUER_RUECKSTELLUNG = "3040"
KONTO_SOLI_AUFWAND = "7608"
KONTO_SOLI_RUECKSTELLUNG = "3020"

DATA_DIR = Path(__file__).parent.parent / "data"


# ---------------------------------------------------------------------------
# Reference data loaders
# ---------------------------------------------------------------------------

def _read_guvposten() -> pl.DataFrame:
    return pl.read_csv(str(DATA_DIR / "guvposten.csv")).with_row_index("Zeile", offset=1)


def _read_bilanzposten() -> pl.DataFrame:
    return pl.read_csv(str(DATA_DIR / "bilanzposten.csv")).with_row_index("Zeile", offset=1)


# ---------------------------------------------------------------------------
# Journal reading
# ---------------------------------------------------------------------------

def _read_journal(journal_file: str, exclude_jeb: bool = False, only_jab: bool = False) -> pl.DataFrame:
    journal = pl.read_csv(
        journal_file,
        schema_overrides={"Konto": pl.Utf8, "Journalnummer": pl.Int64},
    )
    if exclude_jeb:
        journal = journal.filter(~pl.col("Belegnummer").str.contains("JEB"))
    if only_jab:
        journal = journal.filter(pl.col("Belegnummer").str.contains("JAB"))
    return journal


# ---------------------------------------------------------------------------
# Account summarization
# ---------------------------------------------------------------------------

def _summarise(df: pl.DataFrame) -> pl.DataFrame:
    """Group by account, compute signed saldo, determine Soll/Haben type."""
    return (
        df.with_columns(
            pl.when(pl.col("Typ") == "Soll")
            .then(-pl.col("Betrag"))
            .otherwise(pl.col("Betrag"))
            .alias("Vorzeichenbetrag")
        )
        .group_by(["Konto", "Bezeichnung", "GuV Posten", "Bilanzposten"])
        .agg([
            pl.col("Vorzeichenbetrag").sum().alias("Saldo"),
            pl.struct(
                pl.exclude(["Konto", "Bezeichnung", "GuV Posten", "Bilanzposten", "Vorzeichenbetrag"])
            ).alias("detail"),
        ])
        .with_columns([
            pl.when(pl.col("Saldo") < 0)
            .then(pl.lit("Haben"))
            .otherwise(pl.lit("Soll"))
            .alias("Saldo Typ"),
            pl.col("Saldo").abs(),
        ])
        .with_columns(pl.col("Konto").cast(pl.Int64).alias("_sort"))
        .sort("_sort")
        .select(["Konto", "Bezeichnung", "Saldo", "Saldo Typ", "Bilanzposten", "GuV Posten", "detail"])
    )


def _join_and_summarise(
    journal: pl.DataFrame,
    konten_file: str,
    start: date,
    ende: date,
) -> pl.DataFrame:
    """Join journal with konten mapping, filter by date, summarise per account."""
    konten = pl.read_csv(konten_file, schema_overrides={"Konto": pl.Utf8})
    joined = journal.join(konten, on="Konto", how="left")
    filtered = (
        joined
        .with_columns(
            pl.col("Belegdatum").str.strptime(pl.Date, "%d.%m.%Y").alias("Belegdatum_Datum"),
        )
        .filter(
            (pl.col("Belegdatum_Datum") >= start)
            & (pl.col("Belegdatum_Datum") <= ende)
        )
    )
    return _summarise(filtered)


def _get_konten(
    journal_file: str,
    konten_file: str,
    start: date,
    ende: date,
    exclude_jeb: bool = False,
    only_jab: bool = False,
) -> pl.DataFrame:
    journal = _read_journal(journal_file, exclude_jeb, only_jab)
    return _join_and_summarise(journal, konten_file, start, ende)


def _unnest_details(df: pl.DataFrame) -> pl.DataFrame:
    """Explode detail structs back to individual booking rows."""
    if df.is_empty():
        return pl.DataFrame(schema={
            "Konto": pl.Utf8, "Bezeichnung": pl.Utf8,
            "GuV Posten": pl.Utf8, "Bilanzposten": pl.Utf8,
            "Journalnummer": pl.Int64, "Buchungssatznummer": pl.Int64,
            "Belegnummer": pl.Utf8, "Belegdatum": pl.Utf8,
            "Buchungsdatum": pl.Utf8, "Buchungstext": pl.Utf8,
            "Typ": pl.Utf8, "Betrag": pl.Float64,
            "Belegdatum_Datum": pl.Date,
        })
    return df.explode("detail").unnest("detail").drop(
        ["Saldo", "Saldo Typ", "XBRL Taxonomie"], strict=False
    )


# ---------------------------------------------------------------------------
# Tax bookings
# ---------------------------------------------------------------------------

def _make_buchungssatz(
    datum: str, belegnummer: str, buchungstext: str,
    sollkonto: str, habenkonto: str, betrag: float,
) -> pl.DataFrame:
    """Create a 2-row Soll/Haben booking pair."""
    return pl.DataFrame({
        "Journalnummer": [0, 0],
        "Buchungssatznummer": [0, 0],
        "Belegnummer": [belegnummer, belegnummer],
        "Belegdatum": [datum, datum],
        "Buchungsdatum": [datum, datum],
        "Buchungstext": [buchungstext, buchungstext],
        "Konto": [sollkonto, habenkonto],
        "Typ": ["Soll", "Haben"],
        "Betrag": [betrag, betrag],
    })


def _get_steuerbuchungen(
    journal_file: str, konten_file: str,
    start: date, ende: date, hebesatz: int,
) -> pl.DataFrame:
    gwst = berechne_gewerbesteuer(hebesatz, journal_file, konten_file, start, ende)
    kst = berechne_koerperschaftssteuer(journal_file, konten_file, start, ende)
    soli = berechne_soli(journal_file, konten_file, start, ende)

    datum = ende.strftime("%d.%m.%Y")
    bookings = []
    if gwst > 0:
        bookings.append(_make_buchungssatz(datum, "JEB", "Gewerbesteuer", KONTO_GEWERBESTEUER_AUFWAND, KONTO_GEWERBESTEUER_RUECKSTELLUNG, gwst))
    if kst > 0:
        bookings.append(_make_buchungssatz(datum, "JEB", "Körperschaftsteuer", KONTO_KOERPERSCHAFTSTEUER_AUFWAND, KONTO_KOERPERSCHAFTSTEUER_RUECKSTELLUNG, kst))
    if soli > 0:
        bookings.append(_make_buchungssatz(datum, "JEB", "Solidaritätszuschlag", KONTO_SOLI_AUFWAND, KONTO_SOLI_RUECKSTELLUNG, soli))

    if not bookings:
        return pl.DataFrame(schema={
            "Journalnummer": pl.Int64, "Buchungssatznummer": pl.Int64,
            "Belegnummer": pl.Utf8, "Belegdatum": pl.Utf8,
            "Buchungsdatum": pl.Utf8, "Buchungstext": pl.Utf8,
            "Konto": pl.Utf8, "Typ": pl.Utf8, "Betrag": pl.Float64,
        })
    return pl.concat(bookings)


def _get_konten_mit_steuer(
    journal_file: str, konten_file: str,
    start: date, ende: date, hebesatz: int,
) -> pl.DataFrame:
    """Get account balances including computed tax bookings."""
    steuer_buchungen = _get_steuerbuchungen(journal_file, konten_file, start, ende, hebesatz)
    steuer_konten = _join_and_summarise(
        steuer_buchungen, konten_file, start, ende
    ).filter(pl.col("Saldo").round(2) > 0)

    base_konten = _get_konten(journal_file, konten_file, start, ende, True)

    base_rows = _unnest_details(base_konten)
    steuer_rows = _unnest_details(steuer_konten)

    combined = pl.concat([base_rows, steuer_rows], how="diagonal_relaxed")
    return _summarise(combined)


# ---------------------------------------------------------------------------
# Betriebsergebnis and taxes
# ---------------------------------------------------------------------------

def _parse_date(s: str | date) -> date:
    return s if isinstance(s, date) else date.fromisoformat(s)


def _build_guv_base(konten: pl.DataFrame) -> pl.DataFrame:
    """Join account saldos with GuV template, apply sign convention."""
    guvposten = _read_guvposten()
    guv_konten = konten.filter(pl.col("GuV Posten").is_not_null())
    betrag_per_posten = guv_konten.group_by("GuV Posten").agg(
        pl.col("Saldo").sum().alias("Betrag")
    )
    return (
        betrag_per_posten.join(
            guvposten, left_on="GuV Posten", right_on="Posten", how="right"
        )
        .rename({"Posten": "GuV Posten"})
        .sort("Zeile")
        .with_columns(pl.col("Betrag").fill_null(0.0))
        .with_columns(
            pl.when(pl.col("Vorzeichen") == "-")
            .then(-pl.col("Betrag"))
            .otherwise(pl.col("Betrag"))
            .alias("Betrag mit Vorzeichen")
        )
    )


def berechne_betriebsergebnis(
    journal_file: str, konten_file: str, start: str, ende: str
) -> float:
    start_d, ende_d = _parse_date(start), _parse_date(ende)
    konten = _get_konten(journal_file, konten_file, start_d, ende_d, True)
    guv_base = _build_guv_base(konten)
    betriebsergebnis = guv_base.filter(
        pl.col("Summierungsposten") == "Betriebsergebnis"
    )["Betrag mit Vorzeichen"].sum()
    return float(betriebsergebnis)


def berechne_koerperschaftssteuer(
    journal_file: str, konten_file: str, start: str, ende: str
) -> float:
    betriebsergebnis = berechne_betriebsergebnis(journal_file, konten_file, start, ende)
    if round(betriebsergebnis, 2) > 0:
        return round(math.floor(betriebsergebnis) * 0.15, 2)
    return 0.0


def berechne_soli(
    journal_file: str, konten_file: str, start: str, ende: str
) -> float:
    kst = berechne_koerperschaftssteuer(journal_file, konten_file, start, ende)
    return round(kst * 0.055, 2)


def berechne_gewerbesteuer(
    hebesatz: int, journal_file: str, konten_file: str, start: str, ende: str
) -> float:
    betriebsergebnis = berechne_betriebsergebnis(journal_file, konten_file, start, ende)
    if round(betriebsergebnis, 2) > 0:
        return round(math.floor(betriebsergebnis / 100) * 100 * hebesatz * 3.5 / 10000, 2)
    return 0.0


def steuern(
    journal_file: str, konten_file: str, start: str, ende: str, hebesatz: int
) -> float:
    start_d, ende_d = _parse_date(start), _parse_date(ende)
    konten = _get_konten_mit_steuer(journal_file, konten_file, start_d, ende_d, hebesatz)
    tax_konten = konten.filter(
        pl.col("GuV Posten") == "14. Steuern vom Einkommen und vom Ertrag"
    )
    if tax_konten.is_empty():
        return 0.0
    return float(tax_konten["Saldo"].sum())


# ---------------------------------------------------------------------------
# Journal validation
# ---------------------------------------------------------------------------

def validiere_journal(
    journal_file: str, konten_file: str = "", start: str = "", ende: str = ""
) -> str:
    journal = _read_journal(journal_file, exclude_jeb=True)

    # Check 1: Soll/Haben balance per Buchungssatz
    balance = (
        journal
        .with_columns(
            pl.when(pl.col("Typ") == "Soll")
            .then(-pl.col("Betrag"))
            .otherwise(pl.col("Betrag"))
            .alias("VorzeichenBetrag")
        )
        .group_by("Buchungssatznummer")
        .agg(pl.col("VorzeichenBetrag").sum().round(2).alias("Betrag"))
    )
    summe_null = abs(float(balance["Betrag"].sum())) < 1e-9

    # Check 2: Journalnummer sequential
    jn = journal["Journalnummer"].to_list()
    jn_correct = jn == list(range(1, len(jn) + 1))

    # Check 3: Buchungssatznummer matches sorted group rank
    # R's cur_group_id() assigns IDs based on sorted order of group keys
    bsn = journal["Buchungssatznummer"].to_list()
    unique_sorted = sorted(set(bsn))
    rank_map = {v: i + 1 for i, v in enumerate(unique_sorted)}
    expected_bsn = [rank_map[b] for b in bsn]
    bsn_correct = bsn == expected_bsn

    if summe_null and jn_correct and bsn_correct:
        return ""
    return f"FEHLER:  SummeNullBuchungssaetze: {str(summe_null).upper()}, JournalnummerKorrekt: {str(jn_correct).upper()}, BuchungssatznummerKorrekt: {str(bsn_correct).upper()}"


# ---------------------------------------------------------------------------
# GuV
# ---------------------------------------------------------------------------

def guv(
    journal_file: str, konten_file: str, start: str, ende: str, hebesatz: int
) -> pl.DataFrame:
    start_d, ende_d = _parse_date(start), _parse_date(ende)
    konten = _get_konten(journal_file, konten_file, start_d, ende_d, True)
    guv_df = _build_guv_base(konten)

    def summiere(df: pl.DataFrame, summierungsposten: str) -> pl.DataFrame:
        df = df.with_columns(
            pl.when(pl.col("Vorzeichen") == "-")
            .then(-pl.col("Betrag"))
            .otherwise(pl.col("Betrag"))
            .alias("Betrag mit Vorzeichen")
        )
        summe = float(
            df.filter(pl.col("Summierungsposten") == summierungsposten)["Betrag mit Vorzeichen"].sum()
        )
        return df.with_columns(
            pl.when(pl.col("GuV Posten") == summierungsposten)
            .then(pl.lit(summe))
            .otherwise(pl.col("Betrag"))
            .alias("Betrag")
        )

    guv_df = summiere(guv_df, "Betriebsergebnis")

    tax_total = steuern(journal_file, konten_file, start, ende, hebesatz)
    guv_df = guv_df.with_columns(
        pl.when(pl.col("GuV Posten") == "14. Steuern vom Einkommen und vom Ertrag")
        .then(pl.lit(tax_total))
        .otherwise(pl.col("Betrag"))
        .alias("Betrag")
    )

    guv_df = summiere(guv_df, "15. Ergebnis nach Steuern")
    guv_df = summiere(guv_df, "17. Jahresüberschuss/Jahresfehlbetrag")

    return guv_df.select(["GuV Posten", "Betrag", "Vorzeichen"])


# ---------------------------------------------------------------------------
# Bilanz
# ---------------------------------------------------------------------------

def _build_bilanzposten_lookup() -> pl.DataFrame:
    """Map any Bilanzposten name (Ebene1 or Ebene2) to its Bilanzseite/Ebene1/Ebene2."""
    bp_raw = _read_bilanzposten()
    ebene2_lookup = (
        bp_raw.filter(pl.col("Ebene2").is_not_null())
        .select(["Bilanzseite", "Ebene1", "Ebene2"])
        .with_columns(pl.col("Ebene2").alias("Bilanzposten"))
        .unique()
    )
    ebene1_lookup = (
        bp_raw.filter(pl.col("Ebene1").is_not_null())
        .select(["Bilanzseite", "Ebene1"])
        .unique()
        .with_columns([
            pl.col("Ebene1").alias("Bilanzposten"),
            pl.lit(None).cast(pl.Utf8).alias("Ebene2"),
        ])
    )
    return pl.concat(
        [ebene2_lookup, ebene1_lookup], how="diagonal_relaxed"
    ).unique(subset=["Bilanzposten"])


def _bilanz_signed_betrag(bilanz_konten: pl.DataFrame) -> pl.DataFrame:
    """Apply bilanz sign convention to account saldos.

    _summarise computes sum(Haben) - sum(Soll). A negative sum means more
    Soll/debit activity, stored as abs() with Saldo Typ = "Haben" (meaning
    "needs a Haben entry to close" = debit-heavy = normal for Aktiva).
    Conversely, Saldo Typ = "Soll" means credit-heavy = normal for Passiva.

    Therefore:
    Aktiva + "Haben" (debit-heavy, normal) → +Saldo
    Aktiva + "Soll" (credit-heavy, unusual) → -Saldo
    Passiva + "Soll" (credit-heavy, normal) → +Saldo
    Passiva + "Haben" (debit-heavy, unusual) → -Saldo
    """
    return bilanz_konten.with_columns(
        pl.when(
            (pl.col("Bilanzseite") == "Aktiva") & (pl.col("Saldo Typ") == "Haben")
        ).then(pl.col("Saldo"))
        .when(
            (pl.col("Bilanzseite") == "Aktiva") & (pl.col("Saldo Typ") == "Soll")
        ).then(-pl.col("Saldo"))
        .when(
            (pl.col("Bilanzseite") == "Passiva") & (pl.col("Saldo Typ") == "Soll")
        ).then(pl.col("Saldo"))
        .when(
            (pl.col("Bilanzseite") == "Passiva") & (pl.col("Saldo Typ") == "Haben")
        ).then(-pl.col("Saldo"))
        .otherwise(pl.col("Saldo"))
        .alias("Betrag")
    )


def _format_bilanz(konten: pl.DataFrame, jahresueberschuss: float = 0.0) -> pl.DataFrame:
    """Format account data into bilanz structure with Bilanzseite/Ebene1/Ebene2/Betrag."""
    bp_lookup = _build_bilanzposten_lookup()

    bilanz_konten = (
        konten.filter(pl.col("Bilanzposten").is_not_null())
        .join(bp_lookup, on="Bilanzposten", how="left")
    )
    bilanz_konten = _bilanz_signed_betrag(bilanz_konten)

    bilanz_by_posten = bilanz_konten.group_by("Bilanzposten").agg(
        pl.col("Betrag").sum()
    )

    if abs(round(jahresueberschuss, 2)) > 0:
        bilanz_by_posten = pl.concat([
            bilanz_by_posten,
            pl.DataFrame({
                "Bilanzposten": ["V. Jahresüberschuß/Jahresfehlbetrag"],
                "Betrag": [jahresueberschuss],
            }),
        ])

    bilanz_structured = bilanz_by_posten.join(
        bp_lookup, on="Bilanzposten", how="left"
    ).select(["Bilanzseite", "Ebene1", "Ebene2", "Betrag"]).unique()

    template = (
        _read_bilanzposten()
        .unique(subset=["Bilanzseite", "Ebene1", "Ebene2"], keep="first")
        .with_columns([
            pl.col("Ebene1").is_null().alias("_e1_null"),
            pl.col("Ebene2").is_null().alias("_e2_null"),
        ])
        .sort(
            ["Bilanzseite", "_e1_null", "Ebene1", "_e2_null", "Zeile"],
            descending=[False, True, False, True, False],
        )
        .drop(["_e1_null", "_e2_null"])
    )

    result_rows = []
    for row in template.iter_rows(named=True):
        bilanzseite, ebene1, ebene2 = row["Bilanzseite"], row["Ebene1"], row["Ebene2"]
        if ebene2 is not None:
            betrag = float(bilanz_structured.filter(
                (pl.col("Bilanzseite") == bilanzseite)
                & (pl.col("Ebene1") == ebene1)
                & (pl.col("Ebene2") == ebene2)
            )["Betrag"].sum())
        elif ebene1 is not None:
            betrag = float(bilanz_structured.filter(
                (pl.col("Bilanzseite") == bilanzseite)
                & (pl.col("Ebene1") == ebene1)
            )["Betrag"].sum())
        else:
            betrag = float(bilanz_structured.filter(
                pl.col("Bilanzseite") == bilanzseite
            )["Betrag"].sum())
        result_rows.append({
            "Bilanzseite": bilanzseite,
            "Ebene1": ebene1,
            "Ebene2": ebene2,
            "Betrag": betrag,
        })

    result = pl.DataFrame(result_rows)
    result = result.with_columns([
        pl.col("Ebene1").fill_null("NA"),
        pl.col("Ebene2").fill_null("NA"),
    ])
    result = result.with_columns(
        pl.col("Betrag").map_elements(
            lambda x: _format_german_number(x), return_dtype=pl.Utf8
        ).alias("Betrag")
    )
    return result


def bilanz(
    journal_file: str, konten_file: str, start: str, ende: str, hebesatz: int
) -> pl.DataFrame:
    start_d, ende_d = _parse_date(start), _parse_date(ende)
    konten = _get_konten_mit_steuer(journal_file, konten_file, start_d, ende_d, hebesatz)

    guv_df = guv(journal_file, konten_file, start, ende, hebesatz)
    ju_row = guv_df.filter(pl.col("GuV Posten") == "17. Jahresüberschuss/Jahresfehlbetrag")
    jahresueberschuss = float(ju_row["Betrag"][0]) if not ju_row.is_empty() else 0.0

    return _format_bilanz(konten, jahresueberschuss)


def eroeffnungsbilanz(
    journal_file: str, konten_file: str, start: str, ende: str,
) -> pl.DataFrame:
    """Opening balance sheet using only JAB entries."""
    start_d, ende_d = _parse_date(start), _parse_date(ende)
    konten = _get_konten(journal_file, konten_file, start_d, ende_d, only_jab=True)
    return _format_bilanz(konten)


def _format_german_number(value: float) -> str:
    """Format a number in German style: 1.234,56"""
    formatted = f"{round(value, 2):,.2f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def validiere_bilanz(
    journal_file: str, konten_file: str, start: str, ende: str, hebesatz: int
) -> str:
    bilanz_df = bilanz(journal_file, konten_file, start, ende, hebesatz)

    def get_betrag(bilanzseite: str) -> str:
        filtered = bilanz_df.filter(
            (pl.col("Bilanzseite") == bilanzseite)
            & (pl.col("Ebene1") == "NA")
            & (pl.col("Ebene2") == "NA")
        )
        if filtered.is_empty():
            return "0,00"
        return filtered["Betrag"][0]

    aktiva = get_betrag("Aktiva")
    passiva = get_betrag("Passiva")
    if aktiva == passiva:
        return ""
    return "FEHLER: Bilanzsummen von Passiva und Aktiva nicht gleich"


def get_konten(
    journal_file: str, konten_file: str, start: str, ende: str
) -> pl.DataFrame:
    start_d, ende_d = _parse_date(start), _parse_date(ende)
    return _get_konten(journal_file, konten_file, start_d, ende_d, True).drop("detail")


# ---------------------------------------------------------------------------
# T-Konten (ledger accounts)
# ---------------------------------------------------------------------------

def t_konto(
    journal_file: str, konten_file: str, start: str, ende: str,
    hebesatz: int, konto: str,
) -> pl.DataFrame:
    """Return T-account detail for a single account: Soll/Haben side-by-side."""
    start_d, ende_d = _parse_date(start), _parse_date(ende)
    konten = _get_konten_mit_steuer(journal_file, konten_file, start_d, ende_d, hebesatz)
    row = konten.filter(pl.col("Konto") == konto)
    if row.is_empty():
        return pl.DataFrame(schema={
            "Soll_Belegdatum": pl.Utf8, "Soll_Buchungstext": pl.Utf8, "Soll_Betrag": pl.Float64,
            "Haben_Belegdatum": pl.Utf8, "Haben_Buchungstext": pl.Utf8, "Haben_Betrag": pl.Float64,
        })

    saldo = float(row["Saldo"][0])
    saldo_typ = row["Saldo Typ"][0]
    details = _unnest_details(row)

    soll = (
        details.filter(pl.col("Typ") == "Soll")
        .select([
            pl.col("Belegdatum").alias("Soll_Belegdatum"),
            pl.col("Buchungstext").alias("Soll_Buchungstext"),
            pl.col("Betrag").alias("Soll_Betrag"),
        ])
        .with_row_index("_idx")
    )
    haben = (
        details.filter(pl.col("Typ") == "Haben")
        .select([
            pl.col("Belegdatum").alias("Haben_Belegdatum"),
            pl.col("Buchungstext").alias("Haben_Buchungstext"),
            pl.col("Betrag").alias("Haben_Betrag"),
        ])
        .with_row_index("_idx")
    )

    # Pad the shorter side so we get a clean zip
    max_rows = max(soll.height, haben.height)
    if soll.height < max_rows:
        pad = pl.DataFrame({"_idx": list(range(soll.height, max_rows))}).cast({"_idx": pl.UInt32})
        soll = pl.concat([soll, pad], how="diagonal_relaxed")
    if haben.height < max_rows:
        pad = pl.DataFrame({"_idx": list(range(haben.height, max_rows))}).cast({"_idx": pl.UInt32})
        haben = pl.concat([haben, pad], how="diagonal_relaxed")

    merged = soll.join(haben, on="_idx", how="left").drop("_idx")

    # Append saldo row on the opposite side to balance the account
    if round(saldo, 2) != 0:
        on_soll = saldo_typ == "Soll"  # credit balance → saldo on Soll side to balance
        saldo_row = pl.DataFrame({
            "Soll_Belegdatum": [""],
            "Soll_Buchungstext": ["Saldo"] if on_soll else [""],
            "Soll_Betrag": [saldo] if on_soll else [None],
            "Haben_Belegdatum": [""],
            "Haben_Buchungstext": [""] if on_soll else ["Saldo"],
            "Haben_Betrag": [None] if on_soll else [saldo],
        })
        merged = pl.concat([merged, saldo_row], how="diagonal_relaxed")

    return merged


def t_konten(
    journal_file: str, konten_file: str, start: str, ende: str,
    hebesatz: int,
) -> list[dict]:
    """Return T-account data for all accounts with non-zero balances.

    Returns list of dicts: {konto, bezeichnung, saldo, saldo_typ, detail: DataFrame}.
    """
    start_d, ende_d = _parse_date(start), _parse_date(ende)
    konten = _get_konten_mit_steuer(journal_file, konten_file, start_d, ende_d, hebesatz)
    konten = konten.filter(pl.col("Saldo").round(2) != 0)

    result = []
    for row in konten.iter_rows(named=True):
        detail = t_konto(journal_file, konten_file, start, ende, hebesatz, row["Konto"])
        result.append({
            "konto": row["Konto"],
            "bezeichnung": row["Bezeichnung"],
            "saldo": row["Saldo"],
            "saldo_typ": row["Saldo Typ"],
            "detail": detail,
        })
    return result


# ---------------------------------------------------------------------------
# Jahresabschluss (year-end closing)
# ---------------------------------------------------------------------------

def _add_jahresendbuchung(
    datum: str, konto: str, saldo: float, saldo_typ: str,
    bilanzposten: str | None, guv_posten: str | None,
) -> pl.DataFrame:
    """Create a closing entry for one account."""
    # Determine counter-account and description
    if bilanzposten is None or bilanzposten == "":
        gegenkonto = KONTO_GUV
        text = guv_posten or ""
    else:
        gegenkonto = KONTO_SBK
        text = bilanzposten or ""

    # Determine Soll/Haben: reverse the balance
    if saldo_typ == "Soll":
        sollkonto, habenkonto = konto, gegenkonto
    else:
        sollkonto, habenkonto = gegenkonto, konto

    return _make_buchungssatz(datum, "JEB", text, sollkonto, habenkonto, saldo)


def jahresabschluss(
    journal_file: str, konten_file: str, start: str, hebesatz: int,
) -> None:
    """Perform year-end closing: calculate taxes, create closing entries, update journal."""
    start_d = _parse_date(start)
    year = start_d.year
    ende_d = date(year, 12, 31)
    datum_str = ende_d.strftime("%d.%m.%Y")

    journal = _read_journal(journal_file)

    # Idempotent: skip if already closed
    if journal.filter(pl.col("Belegnummer").str.contains("JEB")).height > 0:
        return

    backup_file = journal_file.replace(".csv", "_backup.csv")
    shutil.copy(journal_file, backup_file)

    # Get all accounts including tax bookings
    konten = _get_konten_mit_steuer(journal_file, konten_file, start_d, ende_d, hebesatz)

    # Create closing entries for each non-zero account
    closing_entries = []
    for row in konten.filter(pl.col("Saldo").round(2) != 0).iter_rows(named=True):
        entry = _add_jahresendbuchung(
            datum_str, row["Konto"], row["Saldo"], row["Saldo Typ"],
            row["Bilanzposten"], row["GuV Posten"],
        )
        closing_entries.append(entry)

    if not closing_entries:
        return

    schlussbuchungen = pl.concat(closing_entries)

    # Transfer GuV account net balance to settlement account
    guv_rows = schlussbuchungen.filter(pl.col("Konto") == KONTO_GUV)
    if guv_rows.height > 0:
        guv_signed = guv_rows.with_columns(
            pl.when(pl.col("Typ") == "Soll")
            .then(-pl.col("Betrag"))
            .otherwise(pl.col("Betrag"))
            .alias("Signed")
        )["Signed"].sum()
        guv_saldo = abs(guv_signed)
        if round(guv_saldo, 2) > 0:
            if guv_signed < 0:
                transfer = _make_buchungssatz(datum_str, "JEB", "GuV Abschluss", KONTO_GUV, KONTO_SBK, guv_saldo)
            else:
                transfer = _make_buchungssatz(datum_str, "JEB", "GuV Abschluss", KONTO_SBK, KONTO_GUV, guv_saldo)
            schlussbuchungen = pl.concat([schlussbuchungen, transfer])

    # Assign sequential Buchungssatznummer (continuing from journal)
    max_bsn = int(journal["Buchungssatznummer"].max()) if journal.height > 0 else 0
    # Group pairs by their position (every 2 rows = 1 Buchungssatz)
    n_rows = schlussbuchungen.height
    bsn_list = []
    for i in range(n_rows):
        bsn_list.append(max_bsn + 1 + i // 2)
    schlussbuchungen = schlussbuchungen.with_columns(
        pl.Series("Buchungssatznummer", bsn_list)
    )

    # Assign Belegnummer = JEB{Buchungssatznummer - max_bsn}
    schlussbuchungen = schlussbuchungen.with_columns(
        (pl.lit("JEB") + (pl.col("Buchungssatznummer") - max_bsn).cast(pl.Utf8)).alias("Belegnummer")
    )

    # Assign sequential Journalnummer (continuing from journal)
    max_jn = int(journal["Journalnummer"].max()) if journal.height > 0 else 0
    schlussbuchungen = schlussbuchungen.with_columns(
        pl.Series("Journalnummer", list(range(max_jn + 1, max_jn + 1 + n_rows)))
    )

    # Append to journal and write
    combined = pl.concat([journal, schlussbuchungen], how="diagonal_relaxed")
    combined = combined.select(journal.columns)
    combined = combined.with_columns(
        pl.col("Betrag").round(2)
    )
    combined.write_csv(journal_file)


# ---------------------------------------------------------------------------
# Jahreseröffnung (year opening)
# ---------------------------------------------------------------------------

def _add_jahreseroeffnungsbuchung(
    datum: str, konto: str, saldo: float, saldo_typ: str,
) -> pl.DataFrame:
    """Create an opening entry for one balance sheet account."""
    if saldo_typ == "Soll":
        # "Soll" = credit-heavy → re-establish credit balance: debit SBK, credit Konto
        sollkonto, habenkonto = KONTO_SBK, konto
    else:
        # "Haben" = debit-heavy → re-establish debit balance: debit Konto, credit SBK
        sollkonto, habenkonto = konto, KONTO_SBK
    return _make_buchungssatz(datum, "JAB", "Übertrag aus Vorjahr", sollkonto, habenkonto, saldo)


def jahreseroeffnung(
    journal_file: str, konten_file: str, ende: str, hebesatz: int,
) -> str:
    """Create opening entries for next fiscal year. Returns path to new journal."""
    ende_d = _parse_date(ende)
    current_year = ende_d.year
    new_year = current_year + 1
    start_d = date(current_year, 1, 1)
    datum_str = f"01.01.{new_year}"

    # Get all accounts with taxes from current year
    konten = _get_konten_mit_steuer(journal_file, konten_file, start_d, ende_d, hebesatz)
    konten = konten.filter(pl.col("Saldo").round(2) != 0)

    # Get Jahresüberschuss from GuV
    guv_df = guv(journal_file, konten_file, str(start_d), str(ende_d), hebesatz)
    ju_row = guv_df.filter(pl.col("GuV Posten") == "17. Jahresüberschuss/Jahresfehlbetrag")
    jahresueberschuss = float(ju_row["Betrag"][0]) if not ju_row.is_empty() else 0.0

    # Get existing Gewinnvortrag
    gv_rows = konten.filter(pl.col("Bilanzposten").str.contains("Gewinnvortrag/Verlustvortrag"))
    gewinnvortrag = float(gv_rows["Saldo"].sum()) if gv_rows.height > 0 else 0.0

    # Opening entries for all balance sheet accounts except Gewinnvortrag
    opening_entries = []
    bilanz_konten = konten.filter(
        pl.col("Bilanzposten").is_not_null()
        & ~pl.col("Bilanzposten").str.contains("Gewinnvortrag/Verlustvortrag")
    )
    for row in bilanz_konten.iter_rows(named=True):
        entry = _add_jahreseroeffnungsbuchung(
            datum_str, row["Konto"], row["Saldo"], row["Saldo Typ"],
        )
        opening_entries.append(entry)

    if opening_entries:
        buchungen = pl.concat(opening_entries)
    else:
        buchungen = pl.DataFrame(schema={
            "Journalnummer": pl.Int64, "Buchungssatznummer": pl.Int64,
            "Belegnummer": pl.Utf8, "Belegdatum": pl.Utf8,
            "Buchungsdatum": pl.Utf8, "Buchungstext": pl.Utf8,
            "Konto": pl.Utf8, "Typ": pl.Utf8, "Betrag": pl.Float64,
        })

    # Assign sequential numbering
    n_rows = buchungen.height
    bsn_list = []
    for i in range(n_rows):
        bsn_list.append(1 + i // 2)

    if n_rows > 0:
        buchungen = buchungen.with_columns([
            pl.Series("Journalnummer", list(range(1, n_rows + 1))),
            pl.Series("Buchungssatznummer", bsn_list),
        ])
        buchungen = buchungen.with_columns(
            (pl.lit("JAB") + pl.col("Buchungssatznummer").cast(pl.Utf8)).alias("Belegnummer")
        )

    # Add Gewinnvortrag entry (Jahresüberschuss + existing Gewinnvortrag → 2970)
    gv_total = jahresueberschuss + gewinnvortrag
    if abs(round(gv_total, 2)) > 0:
        next_bsn = (n_rows // 2 + 1) if n_rows > 0 else 1
        next_jn = n_rows + 1

        if gv_total > 0:
            gv_entry = _make_buchungssatz(datum_str, "JAB", "Übertrag aus Vorjahr", KONTO_SBK, KONTO_GEWINNVORTRAG, abs(gv_total))
        else:
            gv_entry = _make_buchungssatz(datum_str, "JAB", "Übertrag aus Vorjahr", KONTO_GEWINNVORTRAG, KONTO_SBK, abs(gv_total))

        gv_entry = gv_entry.with_columns([
            pl.Series("Journalnummer", [next_jn, next_jn + 1]),
            pl.Series("Buchungssatznummer", [next_bsn, next_bsn]),
            pl.lit(f"JAB{next_bsn}").alias("Belegnummer"),
        ])
        buchungen = pl.concat([buchungen, gv_entry], how="diagonal_relaxed")

    # Write new journal file
    base = Path(journal_file)
    new_file = str(base.parent / f"{base.stem}_{new_year}.csv")
    if Path(new_file).exists():
        shutil.copy(new_file, new_file.replace(".csv", "_backup.csv"))

    buchungen = buchungen.with_columns(pl.col("Betrag").round(2))
    buchungen = buchungen.select([
        "Journalnummer", "Buchungssatznummer", "Belegnummer",
        "Belegdatum", "Buchungsdatum", "Buchungstext",
        "Konto", "Typ", "Betrag",
    ])
    buchungen.write_csv(new_file)
    return new_file


# ---------------------------------------------------------------------------
# Journalnummer / Buchungssatznummer correction
# ---------------------------------------------------------------------------

def korrigiere_nummern(journal_file: str) -> None:
    """Fix Journalnummer (sequential) and Buchungssatznummer (dense rank) in-place."""
    journal = pl.read_csv(
        journal_file,
        schema_overrides={"Konto": pl.Utf8, "Journalnummer": pl.Int64},
    )

    # Journalnummer: sequential 1..n
    journal = journal.with_columns(
        pl.arange(1, journal.height + 1, eager=True).alias("Journalnummer")
    )

    # Buchungssatznummer: dense rank preserving original appearance order
    bsn = journal["Buchungssatznummer"].to_list()
    seen: dict[int, int] = {}
    rank = 0
    new_bsn = []
    for b in bsn:
        if b not in seen:
            rank += 1
            seen[b] = rank
        new_bsn.append(seen[b])
    journal = journal.with_columns(
        pl.Series("Buchungssatznummer", new_bsn)
    )

    # Round Betrag to 2 decimal places
    journal = journal.with_columns(pl.col("Betrag").round(2))

    journal.write_csv(journal_file)


# ---------------------------------------------------------------------------
# E-Bilanz export (myEBilanz format)
# ---------------------------------------------------------------------------

def ebilanz_export(
    journal_file: str, konten_file: str, start: str, ende: str,
    hebesatz: int = 380,
    template_ini: str = "",
    output_dir: str = "",
) -> str:
    """Generate E-Bilanz CSV and INI for myEBilanz.

    Args:
        journal_file: Path to journal CSV
        konten_file: Path to konten.csv
        start: Fiscal year start (YYYY-MM-DD)
        ende: Fiscal year end (YYYY-MM-DD)
        hebesatz: Trade tax Hebesatz
        template_ini: Path to myEBilanz template INI (with [xbrl] mappings)
        output_dir: Output directory for CSV and INI

    Returns:
        Path to generated INI file.
    """
    import configparser
    import uuid

    start_d, ende_d = _parse_date(start), _parse_date(ende)

    # Get account balances including tax bookings
    konten_df = _get_konten_mit_steuer(
        journal_file, konten_file, start_d, ende_d, hebesatz
    )

    # Build CSV: Konto;Saldo;Bezeichnung
    rows = []
    for row in konten_df.iter_rows(named=True):
        saldo = row["Saldo"]
        if row["Saldo Typ"] == "Haben":
            # "Haben" = debit-heavy (normal for Aktiva) → positive
            saldo = abs(saldo)
        else:
            # "Soll" = credit-heavy (normal for Passiva/revenue) → negative
            saldo = -abs(saldo)
        if abs(saldo) >= 0.005:
            rows.append({
                "Konto": row["Konto"],
                "Saldo": round(saldo, 2),
                "Bezeichnung": row["Bezeichnung"],
            })

    saldo_df = pl.DataFrame(rows)

    # Determine output paths
    out_dir = Path(output_dir) if output_dir else Path(".")
    ende_str = ende_d.isoformat()
    csv_name = f"bilanz_{ende_str}.csv"
    ini_name = f"bilanz_{ende_str}.ini"
    csv_path = out_dir / csv_name
    ini_path = out_dir / ini_name

    # Write CSV with semicolon delimiter
    saldo_df.write_csv(csv_path, separator=";", quote_style="always")

    # Build INI from template or scratch
    if template_ini and Path(template_ini).exists():
        # Read raw to preserve encoding quirks
        ini_content = Path(template_ini).read_text(encoding="latin-1")
        config = configparser.ConfigParser(interpolation=None, delimiters=("=",))
        config.optionxform = str  # preserve case
        config.read_string(ini_content)
    else:
        config = configparser.ConfigParser(interpolation=None, delimiters=("=",))
        config.optionxform = str

    # Update dynamic fields
    if not config.has_section("magic"):
        config.add_section("magic")
    config.set("magic", "myebilanz", "true")
    config.set("magic", "guid", str(uuid.uuid4()).upper())

    if not config.has_section("csv"):
        config.add_section("csv")
    config.set("csv", "filename", csv_name)
    config.set("csv", "delimiter", ";")
    config.set("csv", "fieldKto", "1")
    config.set("csv", "fieldValue", "2")
    config.set("csv", "fieldName", "3")
    config.set("csv", "fieldValueDebit", "0")
    config.set("csv", "fieldValueCredit", "0")
    config.set("csv", "fieldXBRL", "0")

    if not config.has_section("period"):
        config.add_section("period")
    jahr = start_d.year
    config.set("period", "fiscalYearBegin", start_d.isoformat())
    config.set("period", "fiscalYearEnd", ende_d.isoformat())
    prev_start = date(jahr - 1, 1, 1).isoformat()
    prev_end = date(jahr - 1, 12, 31).isoformat()
    config.set("period", "fiscalPreviousYearBegin", prev_start)
    config.set("period", "fiscalPreviousYearEnd", prev_end)
    config.set("period", "balSheetClosingDatePreviousYear", prev_end)
    config.set("period", "balSheetClosingDate", ende_d.isoformat())

    # Update XBRL mappings from konten.csv taxonomie column
    konten_raw = pl.read_csv(konten_file, schema_overrides={"Konto": pl.Utf8})
    if "XBRL Taxonomie" in konten_raw.columns:
        tax_map = (
            konten_raw
            .filter(pl.col("XBRL Taxonomie").is_not_null() & (pl.col("XBRL Taxonomie") != ""))
            .group_by("XBRL Taxonomie")
            .agg(pl.col("Konto").sort_by("Konto"))
        )
        if not config.has_section("xbrl"):
            config.add_section("xbrl")
        for row in tax_map.iter_rows(named=True):
            key = f"de-gaap-ci:{row['XBRL Taxonomie']}"
            val = ",".join(row["Konto"])
            config.set("xbrl", key, val)

    # Write INI
    with open(ini_path, "w", encoding="latin-1") as f:
        config.write(f)

    return str(ini_path)
