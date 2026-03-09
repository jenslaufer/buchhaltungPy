---
format:
    html:
        embed-resources: true
editor:
    render-on-save: true
execute:
    echo: false
    warning: false
---

# Buchhaltung CLI

Command-line tool for double-entry bookkeeping operations.

## Usage

```bash
python -m src.cli <command> [options]
```

All commands run from the project root `/home/jens/Repos/buchhaltungPy`.

## Common Options

| Option | Default | Description |
|--------|---------|-------------|
| `journal` | (required) | Path to journal CSV file |
| `--konten` | `data/konten.csv` | Path to chart of accounts CSV |
| `--start` | (required*) | Start date, ISO format `YYYY-MM-DD` |
| `--ende` | (required*) | End date, ISO format `YYYY-MM-DD` |
| `--hebesatz` | `380` | Gewerbesteuer Hebesatz (trade tax multiplier) |

*Some commands only need `--start` or `--ende`. See per-command docs below.

## Commands

### Validation

**`validiere-journal`** -- Check journal integrity (balanced bookings, sequential numbering).

```bash
python -m src.cli validiere-journal journal.csv --start 2024-01-01 --ende 2024-12-31
```

Prints `PASS` (exit 0) or error message (exit 1).

**`validiere-bilanz`** -- Check balance sheet (Aktiva == Passiva).

```bash
python -m src.cli validiere-bilanz journal.csv --start 2024-01-01 --ende 2024-12-31
```

Prints `PASS` (exit 0) or error message (exit 1).

### Corrections

**`korrigiere-nummern`** -- Fix Journalnummer (sequential 1..n) and Buchungssatznummer (dense rank). Rounds Betrag to 2 decimals. Modifies the file in-place.

```bash
python -m src.cli korrigiere-nummern journal.csv
```

### Tax Calculations

All return a single float to stdout.

```bash
python -m src.cli betriebsergebnis     journal.csv --start 2024-01-01 --ende 2024-12-31
python -m src.cli koerperschaftssteuer journal.csv --start 2024-01-01 --ende 2024-12-31
python -m src.cli soli                 journal.csv --start 2024-01-01 --ende 2024-12-31
python -m src.cli gewerbesteuer        journal.csv --start 2024-01-01 --ende 2024-12-31 --hebesatz 380
python -m src.cli steuern              journal.csv --start 2024-01-01 --ende 2024-12-31 --hebesatz 380
```

### Reports (CSV to stdout)

Pipe output to a file or another tool.

**`guv`** -- Income statement (Gewinn- und Verlustrechnung).

```bash
python -m src.cli guv journal.csv --start 2024-01-01 --ende 2024-12-31 > guv.csv
```

Columns: `GuV Posten`, `Betrag`, `Vorzeichen`

**`bilanz`** -- Balance sheet.

```bash
python -m src.cli bilanz journal.csv --start 2024-01-01 --ende 2024-12-31 > bilanz.csv
```

Columns: `Bilanzseite`, `Ebene1`, `Ebene2`, `Betrag`

**`eroeffnungsbilanz`** -- Opening balance sheet (JAB entries only).

```bash
python -m src.cli eroeffnungsbilanz journal.csv --start 2024-01-01 --ende 2024-12-31 > eb.csv
```

**`konten`** -- Account balances.

```bash
python -m src.cli konten journal.csv --start 2024-01-01 --ende 2024-12-31 > konten.csv
```

Columns: `Konto`, `Bezeichnung`, `Saldo`, `Saldo Typ`, `Bilanzposten`, `GuV Posten`

**`t-konto`** -- T-account detail for a single account.

```bash
python -m src.cli t-konto journal.csv --start 2024-01-01 --ende 2024-12-31 --konto 1810
```

Columns: `Soll_Belegdatum`, `Soll_Buchungstext`, `Soll_Betrag`, `Haben_Belegdatum`, `Haben_Buchungstext`, `Haben_Betrag`

**`t-konten`** -- T-account detail for all accounts with non-zero balance. Prints comment headers (`# konto bezeichnung | Saldo: ...`) followed by CSV blocks.

```bash
python -m src.cli t-konten journal.csv --start 2024-01-01 --ende 2024-12-31
```

### Year-End / Year-Opening

**`jahresabschluss`** -- Perform year-end closing. Appends JEB entries to the journal. Creates a `_backup.csv` first. Idempotent (skips if JEB entries exist).

```bash
python -m src.cli jahresabschluss journal.csv --start 2024-01-01
```

Note: only needs `--start`. Ende is derived as Dec 31 of the same year.

**`jahreseroeffnung`** -- Create opening entries for the next fiscal year. Writes a new journal file (`journal_YYYY.csv`).

```bash
python -m src.cli jahreseroeffnung journal.csv --ende 2024-12-31
```

Note: only needs `--ende`. Start is derived. Returns the path to the new journal file.

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Validation failed (validiere-journal, validiere-bilanz) |
| 2 | Usage error (missing arguments) |

## Journal CSV Format

```
Journalnummer,Buchungssatznummer,Belegnummer,Belegdatum,Buchungsdatum,Buchungstext,Konto,Typ,Betrag
1,1,RE001,15.01.2024,15.01.2024,Umsatz Jan,1810,Soll,10000
2,1,RE001,15.01.2024,15.01.2024,Umsatz Jan,4400,Haben,10000
```

- `Journalnummer`: sequential row number (1-based)
- `Buchungssatznummer`: groups Soll/Haben pairs (dense ranked)
- `Belegdatum`/`Buchungsdatum`: `DD.MM.YYYY`
- `Konto`: account number (string, e.g. `1810`)
- `Typ`: `Soll` (debit) or `Haben` (credit)
- `Betrag`: positive float, rounded to 2 decimals

## Examples

Validate, compute taxes, generate reports for fiscal year 2024:

```bash
# Validate
python -m src.cli validiere-journal data/journal.csv --start 2024-01-01 --ende 2024-12-31

# Fix numbering if validation fails on numbering
python -m src.cli korrigiere-nummern data/journal.csv

# Tax overview
python -m src.cli steuern data/journal.csv --start 2024-01-01 --ende 2024-12-31

# Generate reports
python -m src.cli guv    data/journal.csv --start 2024-01-01 --ende 2024-12-31 > guv_2024.csv
python -m src.cli bilanz data/journal.csv --start 2024-01-01 --ende 2024-12-31 > bilanz_2024.csv

# Year-end closing and opening next year
python -m src.cli jahresabschluss  data/journal.csv --start 2024-01-01
python -m src.cli jahreseroeffnung data/journal.csv --ende 2024-12-31
```
