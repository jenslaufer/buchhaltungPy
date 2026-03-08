"""Double-entry bookkeeping engine — Python/polars reimplementation."""

import math
from datetime import date
from pathlib import Path

import polars as pl

DATA_DIR = Path(__file__).parent.parent / "data"


# ---------------------------------------------------------------------------
# Reference data loaders
# ---------------------------------------------------------------------------

def _read_guvposten(path: str | None = None) -> pl.DataFrame:
    p = path or str(DATA_DIR / "guvposten.csv")
    return pl.read_csv(p).with_row_index("Zeile", offset=1)


def _read_bilanzposten(path: str | None = None) -> pl.DataFrame:
    p = path or str(DATA_DIR / "bilanzposten.csv")
    df = pl.read_csv(p).with_row_index("Zeile", offset=1)
    return df


def _get_bilanzposten(path: str | None = None) -> pl.DataFrame:
    """Replicate R's .get_bilanzposten(): pivot Ebene columns to find the
    most specific Bilanzposten label per row, then right-join back."""
    bp = _read_bilanzposten(path)

    # Unpivot Bilanzseite/Ebene1/Ebene2 into long form
    long = bp.unpivot(
        on=["Bilanzseite", "Ebene1", "Ebene2"],
        index="Zeile",
        variable_name="Ebene",
        value_name="Bilanzposten",
    ).drop_nulls(subset=["Bilanzposten"]).filter(
        pl.col("Bilanzposten") != ""
    )

    # Keep last non-null per Zeile (most specific level)
    last_per_row = long.group_by("Zeile").agg(
        pl.col("Bilanzposten").last()
    )

    # Right-join back to get all original columns + Bilanzposten
    result = last_per_row.join(bp, on="Zeile", how="right")
    return result


# ---------------------------------------------------------------------------
# Journal reading
# ---------------------------------------------------------------------------

def _read_journal(
    journal_file: str,
    filter_kontoschliessung: bool = False,
) -> pl.DataFrame:
    journal = pl.read_csv(
        journal_file,
        schema_overrides={"Konto": pl.Utf8, "Journalnummer": pl.Int64},
    )
    if filter_kontoschliessung:
        journal = journal.filter(
            ~pl.col("Belegnummer").str.contains("JEB")
        )
    return journal


# ---------------------------------------------------------------------------
# Account summarization
# ---------------------------------------------------------------------------

def _summarise(df: pl.DataFrame) -> pl.DataFrame:
    """Group by account, compute signed saldo, determine Soll/Haben type."""
    saldo = (
        df.with_columns(
            pl.when(pl.col("Typ") == "Soll")
            .then(-pl.col("Betrag"))
            .otherwise(pl.col("Betrag"))
            .alias("Vorzeichenbetrag")
        )
        .group_by(["Konto", "Bezeichnung", "GuV Posten", "Bilanzposten"])
        .agg([
            pl.col("Vorzeichenbetrag").sum().alias("Saldo"),
            # Collect all detail rows for potential unnesting later
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
        .with_columns(
            pl.col("Konto").cast(pl.Int64).alias("Konto numerisch")
        )
        .sort("Konto numerisch")
        .select(["Konto", "Bezeichnung", "Saldo", "Saldo Typ", "Bilanzposten", "GuV Posten", "detail"])
    )
    return saldo


def _get_konten_fuer_buchungssaetze(
    journal: pl.DataFrame,
    konten_file: str,
    periode_start: date,
    periode_ende: date,
) -> pl.DataFrame:
    konten = pl.read_csv(konten_file, schema_overrides={"Konto": pl.Utf8})
    joined = journal.join(konten, on="Konto", how="left")

    # Parse dates and filter by period
    filtered = (
        joined
        .with_columns([
            pl.col("Belegdatum").str.strptime(pl.Date, "%d.%m.%Y").alias("Belegdatum_Datum"),
        ])
        .filter(
            (pl.col("Belegdatum_Datum") >= periode_start)
            & (pl.col("Belegdatum_Datum") <= periode_ende)
        )
    )
    return _summarise(filtered)


def _get_konten(
    journal_file: str,
    konten_file: str,
    periode_start: date,
    periode_ende: date,
    filter_kontoschliessung: bool = False,
) -> pl.DataFrame:
    journal = _read_journal(journal_file, filter_kontoschliessung)
    return _get_konten_fuer_buchungssaetze(journal, konten_file, periode_start, periode_ende)


# ---------------------------------------------------------------------------
# Tax bookings
# ---------------------------------------------------------------------------

def _make_buchungssatz(
    buchungsdatum: str,
    belegdatum: str,
    belegnummer: str,
    buchungstext: str,
    sollkonto: str,
    habenkonto: str,
    betrag: float,
) -> pl.DataFrame:
    """Create a 2-row Soll/Haben booking pair."""
    return pl.DataFrame({
        "Journalnummer": [0, 0],
        "Buchungssatznummer": [0, 0],
        "Belegnummer": [belegnummer, belegnummer],
        "Belegdatum": [belegdatum, belegdatum],
        "Buchungsdatum": [buchungsdatum, buchungsdatum],
        "Buchungstext": [buchungstext, buchungstext],
        "Konto": [sollkonto, habenkonto],
        "Typ": ["Soll", "Haben"],
        "Betrag": [betrag, betrag],
    })


def _get_steuerbuchungen(
    journal_file: str,
    konten_file: str,
    periode_start: date,
    periode_ende: date,
    hebesatz: int,
) -> pl.DataFrame:
    gwst = berechne_gewerbesteuer(hebesatz, journal_file, konten_file, periode_start, periode_ende)
    kst = berechne_koerperschaftssteuer(journal_file, konten_file, periode_start, periode_ende)
    soli = berechne_soli(journal_file, konten_file, periode_start, periode_ende)

    buchungsdatum = periode_ende.strftime("%d.%m.%Y")

    bookings = []
    if gwst > 0:
        bookings.append(_make_buchungssatz(buchungsdatum, buchungsdatum, "JEB", "Gewerbesteuer", "7610", "3035", gwst))
    if kst > 0:
        bookings.append(_make_buchungssatz(buchungsdatum, buchungsdatum, "JEB", "Körperschaftsteuer", "7600", "3040", kst))
    if soli > 0:
        bookings.append(_make_buchungssatz(buchungsdatum, buchungsdatum, "JEB", "Solidaritätszuschlag", "7608", "3020", soli))

    if not bookings:
        # Return empty DataFrame with correct schema
        return pl.DataFrame(schema={
            "Journalnummer": pl.Int64,
            "Buchungssatznummer": pl.Int64,
            "Belegnummer": pl.Utf8,
            "Belegdatum": pl.Utf8,
            "Buchungsdatum": pl.Utf8,
            "Buchungstext": pl.Utf8,
            "Konto": pl.Utf8,
            "Typ": pl.Utf8,
            "Betrag": pl.Float64,
        })
    return pl.concat(bookings)


def _get_konten_mit_steuer(
    journal_file: str,
    konten_file: str,
    periode_start: date,
    periode_ende: date,
    hebesatz: int,
    filter_kontoschliessung: bool = False,
) -> pl.DataFrame:
    """Get account balances including tax bookings."""
    steuer_buchungen = _get_steuerbuchungen(
        journal_file, konten_file, periode_start, periode_ende, hebesatz
    )
    steuer_konten = _get_konten_fuer_buchungssaetze(
        steuer_buchungen, konten_file, periode_start, periode_ende
    ).filter(pl.col("Saldo").round(2) > 0)

    base_konten = _get_konten(
        journal_file, konten_file, periode_start, periode_ende, True
    )

    # Unnest detail structs, combine, re-summarise
    def _unnest_details(df: pl.DataFrame) -> pl.DataFrame:
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

    base_rows = _unnest_details(base_konten)
    steuer_rows = _unnest_details(steuer_konten)

    combined = pl.concat([base_rows, steuer_rows], how="diagonal_relaxed")
    return _summarise(combined)


# ---------------------------------------------------------------------------
# Betriebsergebnis and taxes
# ---------------------------------------------------------------------------

def _parse_date(s: str | date) -> date:
    if isinstance(s, date):
        return s
    return date.fromisoformat(s)


def berechne_betriebsergebnis(
    journal_file: str, konten_file: str, start: str, ende: str
) -> float:
    ps, pe = _parse_date(start), _parse_date(ende)
    konten = _get_konten(journal_file, konten_file, ps, pe, True)
    guvposten = _read_guvposten()

    # Filter to accounts with GuV mapping, group by GuV Posten
    guv_konten = konten.filter(pl.col("GuV Posten").is_not_null())
    betrag_per_posten = guv_konten.group_by("GuV Posten").agg(
        pl.col("Saldo").sum().alias("Betrag")
    )

    # Right-join with guvposten
    joined = betrag_per_posten.join(
        guvposten, left_on="GuV Posten", right_on="Posten", how="right"
    ).rename({"Posten": "GuV Posten"}).with_columns(
        pl.col("Betrag").fill_null(0.0)
    ).with_columns(
        pl.when(pl.col("Vorzeichen") == "-")
        .then(-pl.col("Betrag"))
        .otherwise(pl.col("Betrag"))
        .alias("Betrag mit Vorzeichen")
    )

    # Sum only Betriebsergebnis components
    be = joined.filter(
        pl.col("Summierungsposten") == "Betriebsergebnis"
    )["Betrag mit Vorzeichen"].sum()

    return float(be)


def berechne_koerperschaftssteuer(
    journal_file: str, konten_file: str, start: str, ende: str
) -> float:
    be = berechne_betriebsergebnis(journal_file, konten_file, start, ende)
    if round(be, 2) > 0:
        return round(math.floor(be) * 0.15, 2)
    return 0.0


def berechne_soli(
    journal_file: str, konten_file: str, start: str, ende: str
) -> float:
    kst = berechne_koerperschaftssteuer(journal_file, konten_file, start, ende)
    return round(kst * 0.055, 2)


def berechne_gewerbesteuer(
    hebesatz: int, journal_file: str, konten_file: str, start: str, ende: str
) -> float:
    be = berechne_betriebsergebnis(journal_file, konten_file, start, ende)
    if round(be, 2) > 0:
        return round(math.floor(be / 100) * 100 * hebesatz * 3.5 / 10000, 2)
    return 0.0


def steuern(
    journal_file: str, konten_file: str, start: str, ende: str, hebesatz: int
) -> float:
    ps, pe = _parse_date(start), _parse_date(ende)
    konten = _get_konten_mit_steuer(
        journal_file, konten_file, ps, pe, hebesatz, True
    )
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
    journal_file: str, konten_file: str, start: str, ende: str
) -> str:
    journal = _read_journal(journal_file, filter_kontoschliessung=True)

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
    summe_null = float(balance["Betrag"].sum()) == 0

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
    ps, pe = _parse_date(start), _parse_date(ende)
    konten = _get_konten(journal_file, konten_file, ps, pe, True)
    guvposten = _read_guvposten()

    guv_konten = konten.filter(pl.col("GuV Posten").is_not_null())
    betrag_per_posten = guv_konten.group_by("GuV Posten").agg(
        pl.col("Saldo").sum().alias("Betrag")
    )

    guv_df = (
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

    # Helper to compute summation row
    def summiere(df: pl.DataFrame, summierungsposten: str) -> pl.DataFrame:
        # Recalculate Betrag mit Vorzeichen from current Betrag
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

    # Insert actual tax amount
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

def bilanz(
    journal_file: str, konten_file: str, start: str, ende: str, hebesatz: int
) -> pl.DataFrame:
    ps, pe = _parse_date(start), _parse_date(ende)
    konten = _get_konten_mit_steuer(journal_file, konten_file, ps, pe, hebesatz, True)

    # Get Jahresüberschuss from GuV
    guv_df = guv(journal_file, konten_file, start, ende, hebesatz)
    ju_row = guv_df.filter(pl.col("GuV Posten") == "17. Jahresüberschuss/Jahresfehlbetrag")
    jahresueberschuss = float(ju_row["Betrag"][0]) if not ju_row.is_empty() else 0.0

    # Build lookup: map any Bilanzposten name (Ebene1 or Ebene2) to structure
    bp_raw = _read_bilanzposten()
    # Ebene2 entries: Bilanzposten is Ebene2, keep Ebene2 as both Bilanzposten and Ebene2
    ebene2_lookup = (
        bp_raw.filter(pl.col("Ebene2").is_not_null())
        .select(["Bilanzseite", "Ebene1", "Ebene2"])
        .with_columns(pl.col("Ebene2").alias("Bilanzposten"))
        .unique()
    )
    # Ebene1-only lookup for accounts mapped to Ebene1 names
    ebene1_as_bp = (
        bp_raw.filter(pl.col("Ebene1").is_not_null())
        .select(["Bilanzseite", "Ebene1"])
        .unique()
        .with_columns([
            pl.col("Ebene1").alias("Bilanzposten"),
            pl.lit(None).cast(pl.Utf8).alias("Ebene2"),
        ])
    )
    bp_lookup = pl.concat([ebene2_lookup, ebene1_as_bp], how="diagonal_relaxed").unique(subset=["Bilanzposten"])

    # Filter to bilanz accounts (those with Bilanzposten mapping)
    bilanz_konten = konten.filter(pl.col("Bilanzposten").is_not_null())

    # Join with bp_lookup to get Bilanzseite
    bilanz_konten = bilanz_konten.join(bp_lookup, on="Bilanzposten", how="left")

    # Reconstruct signed saldo: _summarise stores abs(sum) as Saldo.
    # Saldo Typ "Haben" → original sum was negative (more Soll/debit bookings)
    # Saldo Typ "Soll" → original sum was non-negative (more Haben/credit bookings)
    # For Aktiva: debit balance = asset exists → Saldo Typ "Haben" → +Saldo
    #             credit balance = asset reduced → Saldo Typ "Soll" → -Saldo
    # For Passiva: credit balance = liability exists → Saldo Typ "Soll" → +Saldo
    #              debit balance = liability reduced → Saldo Typ "Haben" → -Saldo
    bilanz_konten = bilanz_konten.with_columns(
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
        .alias("Signed Betrag")
    )

    bilanz_by_posten = (
        bilanz_konten
        .group_by("Bilanzposten")
        .agg(pl.col("Signed Betrag").sum().alias("Betrag"))
    )

    # Add Jahresüberschuss row
    ju_df = pl.DataFrame({
        "Bilanzposten": ["V. Jahresüberschuß/Jahresfehlbetrag"],
        "Betrag": [jahresueberschuss],
    })
    bilanz_by_posten = pl.concat([bilanz_by_posten, ju_df])

    # Join with lookup to get Bilanzseite/Ebene1/Ebene2
    bilanz_structured = bilanz_by_posten.join(
        bp_lookup, on="Bilanzposten", how="left"
    ).select(
        ["Bilanzseite", "Ebene1", "Ebene2", "Betrag"]
    ).unique()

    # Build output from template, computing Betrag at each level
    bp_template = _read_bilanzposten()
    # Sort: within each Bilanzseite, total (null Ebene1) first,
    # then within each Ebene1, summary (null Ebene2) first, then Ebene2 details
    rows = (
        bp_template
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

    # For each template row, compute its Betrag
    result_rows = []
    for row in rows.iter_rows(named=True):
        bs = row["Bilanzseite"]
        e1 = row["Ebene1"]
        e2 = row["Ebene2"]

        if e2 is not None:
            # Ebene2 row: sum data matching this exact Ebene2
            betrag = float(
                bilanz_structured
                .filter(
                    (pl.col("Bilanzseite") == bs)
                    & (pl.col("Ebene1") == e1)
                    & (pl.col("Ebene2") == e2)
                )["Betrag"].sum()
            )
        elif e1 is not None:
            # Ebene1 row: sum all data under this Ebene1
            betrag = float(
                bilanz_structured
                .filter(
                    (pl.col("Bilanzseite") == bs)
                    & (pl.col("Ebene1") == e1)
                )["Betrag"].sum()
            )
        else:
            # Bilanzseite total: sum all data for this side
            betrag = float(
                bilanz_structured
                .filter(pl.col("Bilanzseite") == bs)["Betrag"].sum()
            )

        result_rows.append({
            "Bilanzseite": bs,
            "Ebene1": e1,
            "Ebene2": e2,
            "Betrag": betrag,
        })

    result = pl.DataFrame(result_rows)

    # Replace null with "NA" to match R output
    result = result.with_columns([
        pl.col("Ebene1").fill_null("NA"),
        pl.col("Ebene2").fill_null("NA"),
    ])

    # Format Betrag as German number
    result = result.with_columns(
        pl.col("Betrag").map_elements(
            lambda x: _format_german_number(x), return_dtype=pl.Utf8
        ).alias("Betrag")
    )

    return result


def _format_german_number(value: float) -> str:
    """Format a number in German style: 1.234,56"""
    rounded = round(value, 2)
    # Use Python formatting, then swap delimiters
    formatted = f"{rounded:,.2f}"
    # Swap , and . for German format
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    return formatted


def validiere_bilanz(
    journal_file: str, konten_file: str, start: str, ende: str, hebesatz: int
) -> str:
    b = bilanz(journal_file, konten_file, start, ende, hebesatz)

    def get_betrag(bilanzseite: str) -> str:
        filtered = b.with_columns([
            pl.col("Bilanzseite").fill_null(""),
            pl.col("Ebene1").fill_null(""),
            pl.col("Ebene2").fill_null(""),
        ]).filter(
            (pl.col("Bilanzseite") == bilanzseite)
            & (pl.col("Ebene1") == "")
            & (pl.col("Ebene2") == "")
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
    ps, pe = _parse_date(start), _parse_date(ende)
    result = _get_konten(journal_file, konten_file, ps, pe, True)
    return result.drop("detail")
