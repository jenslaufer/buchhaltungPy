"""Render Bilanz, GuV, and T-Konten as standalone HTML files."""

import argparse
from html import escape
from pathlib import Path

from buchhaltung import (
    bilanz,
    eroeffnungsbilanz,
    guv,
    t_konten,
    validiere_bilanz,
    validiere_journal,
    _format_german_number,
)


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>{title}</title>
<script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="font-sans m-10 text-sm">
{body}
</body>
</html>"""


SIGNATURE_TEMPLATE = """
<table class="mt-40">
<tr>
  <td class="w-96">{ort}, den {ende_str}</td>
  <td class="w-48 border-b border-black">&nbsp;</td>
</tr>
<tr>
  <td></td>
  <td>{name}, {position}</td>
</tr>
</table>"""


PAGE_BREAK = '<div class="break-after-page mt-32"></div>\n'


def _render_guv_body(journal_file, konten_file, start, ende, hebesatz, firma):
    g = guv(journal_file, konten_file, start, ende, hebesatz)
    start_str = f"01.01.{start[:4]}"
    ende_str = f"31.12.{ende[:4]}"

    bold_rows = {"Betriebsergebnis", "15. Ergebnis nach Steuern", "17. Jahresüberschuss/Jahresfehlbetrag"}

    html = f'<h2 class="text-xl font-bold mb-6">{escape(firma)} &mdash; GuV {start_str} &ndash; {ende_str}</h2>\n'
    html += '<table class="w-full">'

    for row in g.iter_rows(named=True):
        posten = escape(row["GuV Posten"])
        betrag = row["Betrag"]
        vorzeichen = escape(row["Vorzeichen"])
        betrag_str = _format_german_number(betrag) if betrag != 0 else ""
        bold = row["GuV Posten"] in bold_rows
        fw = " font-bold" if bold else ""

        html += f"""<tr>
      <td class="p-2.5 w-[500px]{fw}">{posten}</td>
      <td class="p-2.5{fw}">{vorzeichen}</td>
      <td class="p-2.5 text-right{fw}">{betrag_str}</td>
    </tr>"""

    html += '</table>'
    return html


def _render_bilanz_body(firma, titel, bilanz_df, journal_valid="", bilanz_valid=""):
    b = bilanz_df

    html = f'<h2 class="text-xl font-bold mb-6">{escape(firma)} &mdash; {escape(titel)}</h2>\n'

    if journal_valid:
        html += f'<p class="mb-2"><b>Journal-Validierung:</b> {escape(journal_valid)}</p>\n'
    if bilanz_valid:
        html += f'<p class="mb-2"><b>Bilanz-Validierung:</b> {escape(bilanz_valid)}</p>\n'

    def get_betrag(seite, ebene1="NA", ebene2="NA"):
        row = b.filter(
            (b["Bilanzseite"] == seite) & (b["Ebene1"] == ebene1) & (b["Ebene2"] == ebene2)
        )
        if row.is_empty():
            return ""
        val = row["Betrag"][0]
        return "" if val == "0,00" else val

    INDENT_CLS = {0: "", 1: "pl-4", 2: "pl-8"}

    def bilanz_row(seite, ebene1, ebene2, label, indent=0):
        val = get_betrag(seite, ebene1, ebene2)
        bold = ebene2 == "NA" and ebene1 != "NA"
        total = ebene1 == "NA"
        fw = " font-bold" if bold or total else ""
        border = " border-t-2 border-black" if total else ""
        ind = INDENT_CLS.get(indent, "")
        return f"""<tr>
      <td class="p-1 {ind}{fw}">{label}</td>
      <td class="p-2.5 text-right{fw}{border}">{val}</td>
    </tr>"""

    aktiva_rows = [
        ("Aktiva", "A. Anlagevermögen", "I. Immaterielle Vermögensgegenstände", "I. Immaterielle Vermögensgegenstände", 2),
        ("Aktiva", "A. Anlagevermögen", "II. Sachanlagen", "II. Sachanlagen", 2),
        ("Aktiva", "A. Anlagevermögen", "III. Finanzanlagen", "III. Finanzanlagen", 2),
        ("Aktiva", "A. Anlagevermögen", "NA", "A. Anlagevermögen", 1),
        ("Aktiva", "B. Umlaufvermögen", "I. Vorräte", "I. Vorräte", 2),
        ("Aktiva", "B. Umlaufvermögen", "II. Forderungen und sonstige Vermögensgegenstände", "II. Forderungen und sonstige Vermögensgegenstände", 2),
        ("Aktiva", "B. Umlaufvermögen", "III. Wertpapiere", "III. Wertpapiere", 2),
        ("Aktiva", "B. Umlaufvermögen", "IV. Kassenbestand, Bundesbankguthaben, Guthaben bei Kreditinstituten und Schecks", "IV. Kassenbestand und Bankguthaben", 2),
        ("Aktiva", "B. Umlaufvermögen", "NA", "B. Umlaufvermögen", 1),
        ("Aktiva", "C. Rechnungsabgrenzungsposten", "NA", "C. Rechnungsabgrenzungsposten", 1),
        ("Aktiva", "NA", "NA", "Summe Aktiva", 0),
    ]

    passiva_rows = [
        ("Passiva", "A. Eigenkapital", "I. Gezeichnetes Kapital", "I. Gezeichnetes Kapital", 2),
        ("Passiva", "A. Eigenkapital", "II. Kapitalrücklage", "II. Kapitalrücklage", 2),
        ("Passiva", "A. Eigenkapital", "III. Gewinnrücklagen", "III. Gewinnrücklagen", 2),
        ("Passiva", "A. Eigenkapital", "IV. Gewinnvortrag/Verlustvortrag", "IV. Gewinnvortrag/Verlustvortrag", 2),
        ("Passiva", "A. Eigenkapital", "V. Jahresüberschuß/Jahresfehlbetrag", "V. Jahresüberschuss/Jahresfehlbetrag", 2),
        ("Passiva", "A. Eigenkapital", "NA", "A. Eigenkapital", 1),
        ("Passiva", "B. Rückstellungen", "NA", "B. Rückstellungen", 1),
        ("Passiva", "C. Verbindlichkeiten", "NA", "C. Verbindlichkeiten", 1),
        ("Passiva", "D. Rechnungsabgrenzungsposten", "NA", "D. Rechnungsabgrenzungsposten", 1),
        ("Passiva", "NA", "NA", "Summe Passiva", 0),
    ]

    html += '<div class="grid grid-cols-2 gap-8">'

    html += '<div><table class="w-full">'
    html += '<tr><td colspan="2" class="p-2.5 text-center border-b-2 border-black font-bold">Aktiva</td></tr>'
    for seite, e1, e2, label, indent in aktiva_rows:
        html += bilanz_row(seite, e1, e2, label, indent)
    html += '</table></div>'

    html += '<div><table class="w-full">'
    html += '<tr><td colspan="2" class="p-2.5 text-center border-b-2 border-black font-bold">Passiva</td></tr>'
    for seite, e1, e2, label, indent in passiva_rows:
        html += bilanz_row(seite, e1, e2, label, indent)
    html += '</table></div>'

    html += '</div>'
    return html


def _render_t_konten_body(journal_file, konten_file, start, ende, hebesatz, firma):
    accounts = t_konten(journal_file, konten_file, start, ende, hebesatz)
    ende_str = f"31.12.{ende[:4]}"

    def fmt(val):
        if val is None:
            return ""
        return _format_german_number(val)

    html = f'<h2 class="text-xl font-bold mb-6">{escape(firma)} &mdash; T-Konten zum {ende_str}</h2>\n'

    for entry in accounts:
        konto = escape(entry["konto"])
        bezeichnung = escape(entry["bezeichnung"])
        detail = entry["detail"]

        html += '<table class="w-full mb-10 table-fixed">'
        html += f"""<tr>
      <td colspan="6" class="pb-3 text-center font-bold">{konto} &ndash; {bezeichnung}</td>
    </tr>
    <tr>
      <td colspan="3" class="p-1 border-b-2 border-black text-center w-1/2 font-bold">Soll</td>
      <td colspan="3" class="p-1 border-b-2 border-black text-center w-1/2 font-bold">Haben</td>
    </tr>"""

        soll_total = 0.0
        haben_total = 0.0

        for row in detail.iter_rows(named=True):
            raw_s_text = row.get("Soll_Buchungstext") or ""
            raw_h_text = row.get("Haben_Buchungstext") or ""
            s_datum = escape(row.get("Soll_Belegdatum") or "")
            s_text = escape(raw_s_text)
            s_betrag = row.get("Soll_Betrag")
            h_datum = escape(row.get("Haben_Belegdatum") or "")
            h_text = escape(raw_h_text)
            h_betrag = row.get("Haben_Betrag")

            if s_betrag is not None:
                soll_total += s_betrag
            if h_betrag is not None:
                haben_total += h_betrag

            is_saldo = raw_s_text == "Saldo" or raw_h_text == "Saldo"
            fw = " font-bold" if is_saldo else ""

            html += f"""<tr>
          <td class="p-1 w-[80px]">{s_datum}</td>
          <td class="p-1{fw}">{s_text}</td>
          <td class="p-2.5 border-r-2 border-black text-right w-[100px]{fw}">{fmt(s_betrag)}</td>
          <td class="p-1 w-[80px]">{h_datum}</td>
          <td class="p-1{fw}">{h_text}</td>
          <td class="p-2.5 text-right w-[100px]{fw}">{fmt(h_betrag)}</td>
        </tr>"""

        summe = _format_german_number(round(max(soll_total, haben_total), 2))
        html += f"""<tr>
      <td colspan="2" class="border-t-[3px] border-black"></td>
      <td class="p-2.5 border-t-[3px] border-r-2 border-black text-right font-bold">{summe}</td>
      <td colspan="2" class="border-t-[3px] border-black"></td>
      <td class="p-2.5 border-t-[3px] border-black text-right font-bold">{summe}</td>
    </tr>"""
        html += '</table>'

    return html


def _wrap_html(title, body):
    return HTML_TEMPLATE.format(title=escape(title), body=body)


def _signature(ort, ende_str, name, position):
    return SIGNATURE_TEMPLATE.format(
        ort=escape(ort), ende_str=escape(ende_str),
        name=escape(name), position=escape(position),
    )


def render_guv(journal_file, konten_file, start, ende, hebesatz, firma, ort, name, position):
    ende_str = f"31.12.{ende[:4]}"
    body = _render_guv_body(journal_file, konten_file, start, ende, hebesatz, firma)
    body += _signature(ort, ende_str, name, position)
    return _wrap_html(f"GuV {firma}", body)


def render_bilanz(journal_file, konten_file, start, ende, hebesatz, firma, ort, name, position):
    ende_str = f"31.12.{ende[:4]}"
    b = bilanz(journal_file, konten_file, start, ende, hebesatz)
    jv = validiere_journal(journal_file, konten_file, start, ende)
    bv = validiere_bilanz(journal_file, konten_file, start, ende, hebesatz)
    body = _render_bilanz_body(firma, f"Bilanz zum {ende_str}", b, jv, bv)
    body += _signature(ort, ende_str, name, position)
    return _wrap_html(f"Bilanz {firma}", body)


def render_t_konten(journal_file, konten_file, start, ende, hebesatz, firma):
    return _wrap_html(
        f"T-Konten {firma}",
        _render_t_konten_body(journal_file, konten_file, start, ende, hebesatz, firma),
    )


def render_all(journal_file, konten_file, start, ende, hebesatz, firma, ort, name, position):
    jahr = start[:4]
    ende_str = f"31.12.{jahr}"
    start_str = f"01.01.{jahr}"

    # Eröffnungsbilanz (only JAB entries)
    eb = eroeffnungsbilanz(journal_file, konten_file, start, ende)
    body = _render_bilanz_body(firma, f"Eröffnungsbilanz zum {start_str}", eb)
    body += _signature(ort, start_str, name, position)
    body += PAGE_BREAK

    # Schlussbilanz (full year)
    sb = bilanz(journal_file, konten_file, start, ende, hebesatz)
    jv = validiere_journal(journal_file, konten_file, start, ende)
    bv = validiere_bilanz(journal_file, konten_file, start, ende, hebesatz)
    body += _render_bilanz_body(firma, f"Schlussbilanz zum {ende_str}", sb, jv, bv)
    body += _signature(ort, ende_str, name, position)
    body += PAGE_BREAK

    # GuV
    body += _render_guv_body(journal_file, konten_file, start, ende, hebesatz, firma)
    body += _signature(ort, ende_str, name, position)
    body += PAGE_BREAK

    # T-Konten
    body += _render_t_konten_body(journal_file, konten_file, start, ende, hebesatz, firma)
    return _wrap_html(f"Jahresabschluss {firma} {start[:4]}", body)


def main():
    parser = argparse.ArgumentParser(description="Render bookkeeping reports as HTML")
    parser.add_argument("report", choices=["bilanz", "guv", "t-konten", "all"])
    parser.add_argument("--journal", required=True)
    parser.add_argument("--konten", default=str(Path(__file__).parent.parent / "data" / "konten.csv"))
    parser.add_argument("--jahr", type=int, required=True)
    parser.add_argument("--hebesatz", type=int, required=True)
    parser.add_argument("--firma", default="")
    parser.add_argument("--ort", default="")
    parser.add_argument("--name", default="")
    parser.add_argument("--position", default="")
    parser.add_argument("--output-dir", default=".")
    args = parser.parse_args()

    start = f"{args.jahr}-01-01"
    ende = f"{args.jahr}-12-31"
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    if args.report == "all":
        content = render_all(args.journal, args.konten, start, ende, args.hebesatz,
                             args.firma, args.ort, args.name, args.position)
        outfile = out / f"jahresabschluss_{args.jahr}.html"
        outfile.write_text(content, encoding="utf-8")
        print(f"  {outfile}")
    else:
        renderers = {
            "guv": (lambda: render_guv(args.journal, args.konten, start, ende, args.hebesatz,
                                       args.firma, args.ort, args.name, args.position), "guv.html"),
            "bilanz": (lambda: render_bilanz(args.journal, args.konten, start, ende, args.hebesatz,
                                             args.firma, args.ort, args.name, args.position), "bilanz.html"),
            "t-konten": (lambda: render_t_konten(args.journal, args.konten, start, ende,
                                                  args.hebesatz, args.firma), "t-konten.html"),
        }
        render_fn, filename = renderers[args.report]
        outfile = out / filename
        outfile.write_text(render_fn(), encoding="utf-8")
        print(f"  {outfile}")


if __name__ == "__main__":
    main()
