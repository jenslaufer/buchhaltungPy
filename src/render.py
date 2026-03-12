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

    P = "p-2.5"
    R = "text-align: right; padding: 10px"

    def cat_row(a_label, a_seite, a_e1, p_label, p_seite, p_e1):
        """Category row: subtotal in col 2/5, label bold."""
        a_val = get_betrag(a_seite, a_e1) if a_seite else ""
        p_val = get_betrag(p_seite, p_e1) if p_seite else ""
        return (f'<tr>'
                f'<td class="{P}"><b>{a_label}</b></td>'
                f'<td class="{P}" style="{R}">{a_val}</td><td></td>'
                f'<td class="{P}"><b>{p_label}</b></td>'
                f'<td class="{P}" style="{R}">{p_val}</td><td></td>'
                f'</tr>')

    def det_row(a_label, a_seite, a_e1, a_e2, p_label, p_seite, p_e1, p_e2):
        """Detail row: value in col 3/6."""
        a_val = get_betrag(a_seite, a_e1, a_e2) if a_seite else ""
        p_val = get_betrag(p_seite, p_e1, p_e2) if p_seite else ""
        return (f'<tr>'
                f'<td class="{P}">{a_label}</td><td></td>'
                f'<td class="{P}" style="{R}">{a_val}</td>'
                f'<td class="{P}">{p_label}</td><td></td>'
                f'<td class="{P}" style="{R}">{p_val}</td>'
                f'</tr>')

    spacer = '<tr><td colspan="6">&nbsp;</td></tr>'

    html += '<table class="w-full table-fixed">'
    html += (f'<colgroup>'
             f'<col style="width:30%"><col style="width:10%"><col style="width:10%">'
             f'<col style="width:30%"><col style="width:10%"><col style="width:10%">'
             f'</colgroup>'
             f'<tr><td colspan="3" class="{P} font-bold text-lg">Aktiva</td>'
             f'<td colspan="3" class="{P} font-bold text-lg">Passiva</td></tr>')

    # A. Anlagevermögen | A. Eigenkapital
    html += cat_row("A. Anlagevermögen", "Aktiva", "A. Anlagevermögen",
                     "A. Eigenkapital", "Passiva", "A. Eigenkapital")
    html += det_row("I. Immaterielle Vermögensgegenstände",
                     "Aktiva", "A. Anlagevermögen", "I. Immaterielle Vermögensgegenstände",
                     "I. Gezeichnetes Kapital",
                     "Passiva", "A. Eigenkapital", "I. Gezeichnetes Kapital")
    html += det_row("II. Sachanlagen",
                     "Aktiva", "A. Anlagevermögen", "II. Sachanlagen",
                     "II. Kapitalrücklage",
                     "Passiva", "A. Eigenkapital", "II. Kapitalrücklage")
    html += det_row("III. Finanzanlagen",
                     "Aktiva", "A. Anlagevermögen", "III. Finanzanlagen",
                     "III. Gewinnrücklagen",
                     "Passiva", "A. Eigenkapital", "III. Gewinnrücklagen")
    html += det_row("", None, None, None,
                     "IV. Gewinnvortrag/Verlustvortrag",
                     "Passiva", "A. Eigenkapital", "IV. Gewinnvortrag/Verlustvortrag")
    html += det_row("", None, None, None,
                     "V. Jahresüberschuss/Jahresfehlbetrag",
                     "Passiva", "A. Eigenkapital", "V. Jahresüberschuß/Jahresfehlbetrag")
    html += spacer

    # B. Umlaufvermögen | B. Rückstellungen
    html += cat_row("B. Umlaufvermögen", "Aktiva", "B. Umlaufvermögen",
                     "B. Rückstellungen", "Passiva", "B. Rückstellungen")
    html += det_row("I. Vorräte",
                     "Aktiva", "B. Umlaufvermögen", "I. Vorräte",
                     "", None, None, None)
    html += det_row("II. Forderungen und sonstige Vermögensgegenstände",
                     "Aktiva", "B. Umlaufvermögen", "II. Forderungen und sonstige Vermögensgegenstände",
                     "", None, None, None)
    html += det_row("III. Wertpapiere",
                     "Aktiva", "B. Umlaufvermögen", "III. Wertpapiere",
                     "", None, None, None)
    html += det_row("IV. Kassenbestand, Bundesbankguthaben, Guthaben bei Kreditinstituten und Schecks",
                     "Aktiva", "B. Umlaufvermögen", "IV. Kassenbestand, Bundesbankguthaben, Guthaben bei Kreditinstituten und Schecks",
                     "", None, None, None)
    html += spacer

    # C. Rechnungsabgrenzungsposten | C. Verbindlichkeiten
    html += cat_row("C. Rechnungsabgrenzungsposten", "Aktiva", "C. Rechnungsabgrenzungsposten",
                     "C. Verbindlichkeiten", "Passiva", "C. Verbindlichkeiten")
    html += spacer

    # D. Aktive latente Steuern | D. Rechnungsabgrenzungsposten
    html += cat_row("D. Aktive latente Steuern", "Aktiva", "D. Aktive latente Steuern",
                     "D. Rechnungsabgrenzungsposten", "Passiva", "D. Rechnungsabgrenzungsposten")
    html += spacer

    # E. Aktiver Unterschiedsbetrag | E. Passive latente Steuern
    html += cat_row("E. Aktiver Unterschiedsbetrag aus der Vermögensverrechnung",
                     "Aktiva", "E. Aktiver Unterschiedsbetrag aus der Vermögensverrechnung",
                     "E. Passive latente Steuern", "Passiva", "E. Passive latente Steuern")

    # Totals
    a_total = get_betrag("Aktiva")
    p_total = get_betrag("Passiva")
    html += (f'<tr style="border-top: 2px solid">'
             f'<td></td><td class="{P}" style="{R}"><b>{a_total}</b></td>'
             f'<td colspan="2"></td>'
             f'<td class="{P}" style="{R}"><b>{p_total}</b></td><td></td>'
             f'</tr>')
    html += '</table>'
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
