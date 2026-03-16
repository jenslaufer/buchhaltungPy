# buchhaltungPy

Double-entry bookkeeping CLI for German GmbH. Handles journal validation, financial statements (Bilanz, GuV), tax computation, payroll, year-end closing, E-Bilanz export, and DATEV export.

Built on SKR04 (Kontenrahmen). All amounts in EUR.

## Install

```bash
pip install -e .
```

Requires Python ≥ 3.11 and [polars](https://pola.rs).

## Usage

```bash
python -m src.cli <command> [options]
```

### Financial Statements

| Command | Description |
|---|---|
| `bilanz` | Balance sheet (CSV) |
| `eroeffnungsbilanz` | Opening balance sheet (CSV) |
| `guv` | Income statement (CSV) |
| `konten` | Account balances (CSV) |
| `susa` | Summen- und Saldenliste / trial balance |
| `t-konto --konto <nr>` | T-account for one account (CSV) |
| `t-konten` | T-accounts for all accounts |

### Tax Computation

| Command | Description |
|---|---|
| `betriebsergebnis` | Operating result |
| `koerperschaftssteuer` | Corporate tax (KSt) |
| `soli` | Solidarity surcharge |
| `gewerbesteuer` | Trade tax (GewSt) |
| `steuern` | All taxes combined |

### Validation

| Command | Description |
|---|---|
| `validiere-journal` | Balanced bookings, sequential numbering |
| `validiere-bilanz` | Aktiva == Passiva |
| `validiere-gobd` | GoBD compliance (chronological order, no empty fields, valid accounts) |
| `korrigiere-nummern` | Fix journal/booking numbering |
| `sortiere-journal` | Sort journal by Buchungsdatum (GoBD chronological order) |

### Audit (Betriebsprüfung)

| Command | Description |
|---|---|
| `benford` | Benford's Law first-digit analysis (chi-squared test) |
| `zeitreihe` | Monthly time series of revenue, expenses, result |
| `anomalien` | Detect duplicates, outliers, regularity gaps |

### Year-End

| Command | Description |
|---|---|
| `jahresabschluss` | Year-end closing (modifies journal) |
| `jahreseroeffnung` | Opening entries for next fiscal year |
| `ebilanz` | E-Bilanz export (CSV + INI for myEBilanz) |
| `datev-export` | DATEV EXTF Buchungsstapel export |
| `datev-kontenbeschriftungen` | DATEV EXTF Kontenbeschriftungen export |
| `datev-paket` | Complete DATEV/GDPdU audit package |
| `gdpdu-journal` | GDPdU journal (plain CSV for IDEA) |

### Payroll

| Command | Description |
|---|---|
| `lohn-berechnen` | Compute payroll for an employee (CSV) |
| `lohn-buchungen` | Generate payroll journal entries (CSV) |
| `lohn-zettel` | Generate payslip as HTML |
| `lohn-zettel-journal` | Generate payslips from journal data |

### Example

```bash
# Validate and generate statements
python -m src.cli validiere-journal journal.csv --start 2024-01-01 --ende 2024-12-31
python -m src.cli bilanz journal.csv --start 2024-01-01 --ende 2024-12-31 > bilanz.csv
python -m src.cli guv journal.csv --start 2024-01-01 --ende 2024-12-31 > guv.csv

# Year-end closing and E-Bilanz
python -m src.cli jahresabschluss journal.csv --start 2024-01-01
python -m src.cli ebilanz journal.csv --start 2024-01-01 --ende 2024-12-31 --output-dir ./ebilanz

# DATEV export for Steuerberater
python -m src.cli datev-export journal.csv --start 2024-01-01 --ende 2024-12-31 -o EXTF_Buchungsstapel.csv
python -m src.cli datev-paket journal.csv --start 2024-01-01 --ende 2024-12-31 --output-dir ./datev

# Trial balance
python -m src.cli susa journal.csv --start 2024-01-01 --ende 2024-12-31

# Payroll
python -m src.cli lohn-berechnen --name "Max Mustermann" --brutto 3500 --monat 2024-01-01
```

## Project Structure

```
src/
  buchhaltung.py      Core bookkeeping logic (Bilanz, GuV, taxes, year-end, E-Bilanz)
  cli.py              CLI with 31 subcommands
  datev.py            DATEV EXTF exporter, GDPdU, SuSa, Kontenbeschriftungen
  lohnbuchhaltung.py  Payroll: Lohnsteuer (BMF PAP), SV, journal entries, payslips
  lohnsteuer/         Generated BMF PAP calculators (2023–2026)
  render.py           HTML rendering for Bilanz, GuV, T-Konten
data/
  konten.csv          SKR04 chart of accounts with XBRL taxonomy mappings
  bilanzposten.csv    Balance sheet line items
  guvposten.csv       Income statement line items
tests/
  fixtures/           25 synthetic journals + 5 real-year journals (2022–2026)
  test_*.py           347 tests covering all modules
```

## Journal Format

CSV with columns: `Journalnummer`, `Buchungssatznummer`, `Belegnummer`, `Belegdatum`, `Buchungsdatum`, `Buchungstext`, `Konto`, `Typ`, `Betrag`

Each booking entry has `Typ` = `Soll` or `Haben`. Bookings within the same `Buchungssatznummer` must balance (sum Soll == sum Haben).

## Tests

```bash
python -m pytest tests/
```

388 tests across 16 test modules. Tests run against synthetic fixtures and real journal data from 2022–2026.

## Dependencies

- [polars](https://pola.rs) — DataFrame operations
- Python ≥ 3.11

Dev: pytest
