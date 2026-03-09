# Wertpapiergewinne in der GmbH verbuchen (SKR04)

## Relevante Konten

### Bestandskonten (Bilanz)

| Konto     | Bezeichnung                                      |
|-----------|--------------------------------------------------|
| 0900-0920 | Wertpapiere des Anlagevermogens (langfristig)    |
| 1510      | Sonstige Wertpapiere des Umlaufvermogens (Trading) |

### Erfolgskonten (GuV)

| Konto | Bezeichnung                                                    |
|-------|----------------------------------------------------------------|
| 4900  | Ertraege aus Abgang von Gegenstaenden des Anlagevermogens      |
| 4905  | Ertraege aus Abgang von Gegenstaenden des Umlaufvermogens      |
| 4906  | Ertraege aus Abgang UV - 8b Abs. 2 KStG (95% steuerfrei)      |
| 6905  | Verluste aus Abgang von Gegenstaenden des Umlaufvermogens      |

### Rueckstellungskonten

| Konto | Bezeichnung                  |
|-------|------------------------------|
| 3035  | Gewerbesteuerrueckstellung   |
| 3040  | Koerperschaftsteuerrueckstellung |

---

## Buchungsbeispiele

### Kauf von Aktien (Umlaufvermoegen)

```
Soll 1510 (Wertpapiere UV)     5.000 EUR
Haben 1800 (Bank)              5.000 EUR
```

### Verkauf mit Gewinn

Kauf: 5.000 EUR, Verkauf: 7.000 EUR, Gewinn: 2.000 EUR

```
Soll 1800 (Bank)               7.000 EUR
Haben 4906 (Ertraege Abgang UV) 7.000 EUR

Soll 6905 (Verluste Abgang UV) 5.000 EUR
Haben 1510 (Wertpapiere UV)    5.000 EUR
```

Netto-Effekt in der GuV: 7.000 - 5.000 = 2.000 EUR Gewinn.

### Verkauf mit Verlust

Kauf: 5.000 EUR, Verkauf: 3.000 EUR, Verlust: 2.000 EUR

```
Soll 1800 (Bank)               3.000 EUR
Haben 4906 (Ertraege Abgang UV) 3.000 EUR

Soll 6905 (Verluste Abgang UV) 5.000 EUR
Haben 1510 (Wertpapiere UV)    5.000 EUR
```

Netto-Effekt in der GuV: 3.000 - 5.000 = -2.000 EUR Verlust.

---

## Besteuerung: GmbH vs. Privatperson

### Privatperson

- 25% Kapitalertragsteuer + 5,5% Soli = ca. 26,375% Abgeltungsteuer
- Sparerpauschbetrag: 1.000 EUR (2.000 EUR bei Zusammenveranlagung)

### GmbH mit Einzelaktien (8b Abs. 2 KStG)

- Veraeusserungsgewinne sind zu **95% steuerfrei**
- Nur 5% gelten als nicht abzugsfaehige Betriebsausgaben
- Effektive Steuer: 5% x ca. 30% (KSt + GewSt) = **ca. 1,5%**
- Gilt fuer Aktien unabhaengig von Beteiligungshoehe und Haltedauer
- Konto 4906 verwenden (speziell fuer 8b-Ertraege)

### GmbH mit ETFs/Fonds (Investmentsteuergesetz - InvStG)

8b KStG greift bei Fonds **nicht**. Stattdessen Teilfreistellung:

| Fondstyp                       | Teilfreistellung | Steuerpflichtig | Effektive Steuer |
|--------------------------------|------------------|-----------------|------------------|
| Aktienfonds (>51% Aktien)     | 80%              | 20%             | ca. 6%           |
| Mischfonds (>25% Aktien)      | 40%              | 60%             | ca. 18%          |
| Sonstige Fonds                 | 0%               | 100%            | ca. 30%          |

**Fazit:** Einzelaktien in der GmbH (~1,5%) sind steuerlich deutlich guenstiger als ETFs (~6%) und viel guenstiger als privat (~26,4%).

---

## Steuerrueckstellungen bilden

Am Jahresende Rueckstellung fuer Steuern auf den steuerpflichtigen Anteil.

### Beispiel: Aktiengewinn 2.000 EUR (8b KStG)

Steuerpflichtiger Anteil: 5% x 2.000 = 100 EUR

```
KSt:   100 EUR x 15%              =  15,00 EUR
Soli:   15 EUR x 5,5%             =   0,83 EUR
GewSt: 100 EUR x 3,5% x Hebesatz  =  variabel
```

Bei Hebesatz 410%: GewSt = 100 x 3,5% x 410% = 14,35 EUR

Buchung:

```
Soll 7600 (KSt-Aufwand)           15,83 EUR
Haben 3040 (KSt-Rueckstellung)    15,83 EUR

Soll 7610 (GewSt-Aufwand)         14,35 EUR
Haben 3035 (GewSt-Rueckstellung)  14,35 EUR
```

### Beispiel: ETF-Gewinn 2.000 EUR (Aktienfonds, 80% Teilfreistellung)

Steuerpflichtiger Anteil: 20% x 2.000 = 400 EUR

```
KSt:   400 EUR x 15%              =  60,00 EUR
Soli:   60 EUR x 5,5%             =   3,30 EUR
GewSt: 400 EUR x 3,5% x Hebesatz  =  variabel
```

Bei Hebesatz 410%: GewSt = 400 x 3,5% x 410% = 57,40 EUR

---

## Anlage- vs. Umlaufvermoegen

| Kriterium            | Anlagevermoegen (AV)            | Umlaufvermoegen (UV)              |
|----------------------|---------------------------------|-----------------------------------|
| Haltedauer           | Langfristig (>1 Jahr)           | Kurzfristig (Trading)             |
| Konten               | 0900-0920                       | 1510                              |
| Bewertung            | Gemaesssigtes Niederstwertprinzip | Strenges Niederstwertprinzip     |
| Abschreibung         | Nur bei dauerhafter Wertminderung | Bei jeder Wertminderung am Stichtag |
| Steuerliche Behandlung | Identisch (8b KStG)           | Identisch (8b KStG)              |

Die Zuordnung hat keinen Einfluss auf die steuerliche Behandlung nach 8b KStG, aber auf die Bewertung in der Bilanz.

---

## Auswirkung auf das Gesamtergebnis der GmbH

### Handelsrecht (GuV/Bilanz)

Der **volle Wertpapiergewinn** erscheint in der GuV und fliesst in den Jahresueberschuss ein. Buchhalterisch gibt es keine Kuerzung. Das Gesamtergebnis der GmbH enthaelt den kompletten Gewinn.

### Steuerrecht (Steuererklaerung)

Die 95%-Freistellung nach 8b KStG ist eine **ausserbilanzielle Korrektur**. Sie passiert nicht in der Buchhaltung, sondern in der Koerperschaftsteuererklaerung:

```
Jahresueberschuss lt. GuV (inkl. vollem Wertpapiergewinn)
- 95% steuerfreier Anteil (8b Abs. 2 KStG)           <-- ausserbilanzielle Korrektur
= zu versteuerndes Einkommen
```

Konkret:

- **GuV** zeigt den vollen Gewinn -> erhoeht das Betriebsergebnis
- **KSt-Erklaerung** kuerzt 95% -> nur 5% steuerpflichtig
- **GewSt-Erklaerung** ebenfalls -> 8b wirkt ueber 7 GewStG durch

### Steuerrueckstellungen

Die Rueckstellungen (3035, 3040) muessen auf Basis des **steuerlichen** Ergebnisses gebildet werden, also nach der 8b-Kuerzung. Die Rueckstellung ist daher niedrig, obwohl der GuV-Gewinn hoch ist.

### Hinweis fuer buchhaltungR

Die Steuerberechnung in `R/buchhaltung.R` (Funktionen `berechne_koerperschaftssteuer`, `berechne_gewerbesteuer`) rechnet aktuell auf dem gesamten Betriebsergebnis. Bei Wertpapiergewinnen muss differenziert werden:

```
Betriebsergebnis (gesamt)
- davon 8b-beguenstigte Ertraege x 95%
= steuerliches Ergebnis -> darauf KSt/GewSt berechnen
```

Umsetzungsvorschlag: Die Steuerberechnungsfunktionen um einen Parameter `8b_ertraege` erweitern, der den Anteil der steuerfreien Wertpapierertraege enthaelt. Alternativ ein separates Konto (4906) in der GuV-Auswertung erkennen und automatisch kuerzen.

---

## Quellen

- [Kontenuebersicht Wertpapiere verbuchen](https://wertpapiere-verbuchen.de/kontenuebersicht/)
- [Haufe: Wertpapiere im Betriebsvermoegen](https://www.haufe.de/finance/haufe-finance-office-premium/wertpapiere-im-betriebsvermoegen_idesk_PI20354_HI10245061.html)
- [8b KStG - RIDE Capital](https://www.ride.capital/gmbh/8b)
- [Trading-GmbH 8b KStG - CPM Steuerberater](https://www.cpm-steuerberater.de/news/entry/2026/01/09/9503-trading-gmbh-8b-kstg-streubesitzdividenden-gewerbesteuer)
- [Wertpapiere GmbH Steuern - Immotax](https://immotax-steuerberatung.de/wertpapiere-gmbh-steuern)
- [SKR04 Konto 4906](https://www.buchungssatz.de/de/konto/skr04/klasse4901/4906.html)
- [Steuerrueckstellungen](https://www.rechnungswesen-info.de/rueckstellungen_steuerrueckstellungen.html)
