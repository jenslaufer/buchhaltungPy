# coding: utf-8

import decimal

class BigDecimal(decimal.Decimal):
    """ Compatibility class for decimal.Decimal """

    ROUND_DOWN = decimal.ROUND_DOWN
    ROUND_UP = decimal.ROUND_UP

    @classmethod
    def _mk_exp(cls, prec):
        return cls('0.' + '0' * prec)

    def divide(self, other, scale=None, rounding=None):
        if not scale and not rounding:
            return BigDecimal(self / other)
        if type(scale) is not int:
            raise ValueError("Expected integer value for scale")
        exp = BigDecimal._mk_exp(scale)
        return BigDecimal((self / other).quantize(exp, rounding=rounding))

    @classmethod
    def valueOf(cls, value):
        return cls(value)

    def multiply(self, other):
        return BigDecimal(self * other)

    def setScale(self, scale, rounding):
        exp = BigDecimal._mk_exp(scale)
        return BigDecimal(self.quantize(exp, rounding=rounding))

    def add(self, other):
        return BigDecimal(self + other)

    def subtract(self, other):
        return BigDecimal(self - other)

    def longValue(self):
        return int(self)

    def compareTo(self, other):
        return BigDecimal(self.compare(other))

BigDecimal.ZERO = BigDecimal(0)
BigDecimal.ONE = BigDecimal(1)
BigDecimal.TEN = BigDecimal(10)


class Lohnsteuer:
    TAB1 = [BigDecimal.ZERO, BigDecimal.valueOf(0.4), BigDecimal.valueOf(0.384), BigDecimal.valueOf(0.368), BigDecimal.valueOf(0.352), BigDecimal.valueOf(0.336), BigDecimal.valueOf(0.32), BigDecimal.valueOf(0.304), BigDecimal.valueOf(0.288), BigDecimal.valueOf(0.272), BigDecimal.valueOf(0.256), BigDecimal.valueOf(0.24), BigDecimal.valueOf(0.224), BigDecimal.valueOf(0.208), BigDecimal.valueOf(0.192), BigDecimal.valueOf(0.176), BigDecimal.valueOf(0.16), BigDecimal.valueOf(0.152), BigDecimal.valueOf(0.144), BigDecimal.valueOf(0.14), BigDecimal.valueOf(0.136), BigDecimal.valueOf(0.132), BigDecimal.valueOf(0.128), BigDecimal.valueOf(0.124), BigDecimal.valueOf(0.12), BigDecimal.valueOf(0.116), BigDecimal.valueOf(0.112), BigDecimal.valueOf(0.108), BigDecimal.valueOf(0.104), BigDecimal.valueOf(0.1), BigDecimal.valueOf(0.096), BigDecimal.valueOf(0.092), BigDecimal.valueOf(0.088), BigDecimal.valueOf(0.084), BigDecimal.valueOf(0.08), BigDecimal.valueOf(0.076), BigDecimal.valueOf(0.072), BigDecimal.valueOf(0.068), BigDecimal.valueOf(0.064), BigDecimal.valueOf(0.06), BigDecimal.valueOf(0.056), BigDecimal.valueOf(0.052), BigDecimal.valueOf(0.048), BigDecimal.valueOf(0.044), BigDecimal.valueOf(0.04), BigDecimal.valueOf(0.036), BigDecimal.valueOf(0.032), BigDecimal.valueOf(0.028), BigDecimal.valueOf(0.024), BigDecimal.valueOf(0.02), BigDecimal.valueOf(0.016), BigDecimal.valueOf(0.012), BigDecimal.valueOf(0.008), BigDecimal.valueOf(0.004), BigDecimal.valueOf(0)]
    """
    Tabelle für die Prozentsätze des Versorgungsfreibetrags
    """

    TAB2 = [BigDecimal.ZERO, BigDecimal.valueOf(3000), BigDecimal.valueOf(2880), BigDecimal.valueOf(2760), BigDecimal.valueOf(2640), BigDecimal.valueOf(2520), BigDecimal.valueOf(2400), BigDecimal.valueOf(2280), BigDecimal.valueOf(2160), BigDecimal.valueOf(2040), BigDecimal.valueOf(1920), BigDecimal.valueOf(1800), BigDecimal.valueOf(1680), BigDecimal.valueOf(1560), BigDecimal.valueOf(1440), BigDecimal.valueOf(1320), BigDecimal.valueOf(1200), BigDecimal.valueOf(1140), BigDecimal.valueOf(1080), BigDecimal.valueOf(1050), BigDecimal.valueOf(1020), BigDecimal.valueOf(990), BigDecimal.valueOf(960), BigDecimal.valueOf(930), BigDecimal.valueOf(900), BigDecimal.valueOf(870), BigDecimal.valueOf(840), BigDecimal.valueOf(810), BigDecimal.valueOf(780), BigDecimal.valueOf(750), BigDecimal.valueOf(720), BigDecimal.valueOf(690), BigDecimal.valueOf(660), BigDecimal.valueOf(630), BigDecimal.valueOf(600), BigDecimal.valueOf(570), BigDecimal.valueOf(540), BigDecimal.valueOf(510), BigDecimal.valueOf(480), BigDecimal.valueOf(450), BigDecimal.valueOf(420), BigDecimal.valueOf(390), BigDecimal.valueOf(360), BigDecimal.valueOf(330), BigDecimal.valueOf(300), BigDecimal.valueOf(270), BigDecimal.valueOf(240), BigDecimal.valueOf(210), BigDecimal.valueOf(180), BigDecimal.valueOf(150), BigDecimal.valueOf(120), BigDecimal.valueOf(90), BigDecimal.valueOf(60), BigDecimal.valueOf(30), BigDecimal.valueOf(0)]
    """
    Tabelle für die Höchstbeträge des Versorgungsfreibetrags
    """

    TAB3 = [BigDecimal.ZERO, BigDecimal.valueOf(900), BigDecimal.valueOf(864), BigDecimal.valueOf(828), BigDecimal.valueOf(792), BigDecimal.valueOf(756), BigDecimal.valueOf(720), BigDecimal.valueOf(684), BigDecimal.valueOf(648), BigDecimal.valueOf(612), BigDecimal.valueOf(576), BigDecimal.valueOf(540), BigDecimal.valueOf(504), BigDecimal.valueOf(468), BigDecimal.valueOf(432), BigDecimal.valueOf(396), BigDecimal.valueOf(360), BigDecimal.valueOf(342), BigDecimal.valueOf(324), BigDecimal.valueOf(315), BigDecimal.valueOf(306), BigDecimal.valueOf(297), BigDecimal.valueOf(288), BigDecimal.valueOf(279), BigDecimal.valueOf(270), BigDecimal.valueOf(261), BigDecimal.valueOf(252), BigDecimal.valueOf(243), BigDecimal.valueOf(234), BigDecimal.valueOf(225), BigDecimal.valueOf(216), BigDecimal.valueOf(207), BigDecimal.valueOf(198), BigDecimal.valueOf(189), BigDecimal.valueOf(180), BigDecimal.valueOf(171), BigDecimal.valueOf(162), BigDecimal.valueOf(153), BigDecimal.valueOf(144), BigDecimal.valueOf(135), BigDecimal.valueOf(126), BigDecimal.valueOf(117), BigDecimal.valueOf(108), BigDecimal.valueOf(99), BigDecimal.valueOf(90), BigDecimal.valueOf(81), BigDecimal.valueOf(72), BigDecimal.valueOf(63), BigDecimal.valueOf(54), BigDecimal.valueOf(45), BigDecimal.valueOf(36), BigDecimal.valueOf(27), BigDecimal.valueOf(18), BigDecimal.valueOf(9), BigDecimal.valueOf(0)]
    """
    Tabelle für die Zuschläge zum Versorgungsfreibetrag
    """

    TAB4 = [BigDecimal.ZERO, BigDecimal.valueOf(0.4), BigDecimal.valueOf(0.384), BigDecimal.valueOf(0.368), BigDecimal.valueOf(0.352), BigDecimal.valueOf(0.336), BigDecimal.valueOf(0.32), BigDecimal.valueOf(0.304), BigDecimal.valueOf(0.288), BigDecimal.valueOf(0.272), BigDecimal.valueOf(0.256), BigDecimal.valueOf(0.24), BigDecimal.valueOf(0.224), BigDecimal.valueOf(0.208), BigDecimal.valueOf(0.192), BigDecimal.valueOf(0.176), BigDecimal.valueOf(0.16), BigDecimal.valueOf(0.152), BigDecimal.valueOf(0.144), BigDecimal.valueOf(0.14), BigDecimal.valueOf(0.136), BigDecimal.valueOf(0.132), BigDecimal.valueOf(0.128), BigDecimal.valueOf(0.124), BigDecimal.valueOf(0.12), BigDecimal.valueOf(0.116), BigDecimal.valueOf(0.112), BigDecimal.valueOf(0.108), BigDecimal.valueOf(0.104), BigDecimal.valueOf(0.1), BigDecimal.valueOf(0.096), BigDecimal.valueOf(0.092), BigDecimal.valueOf(0.088), BigDecimal.valueOf(0.084), BigDecimal.valueOf(0.08), BigDecimal.valueOf(0.076), BigDecimal.valueOf(0.072), BigDecimal.valueOf(0.068), BigDecimal.valueOf(0.064), BigDecimal.valueOf(0.06), BigDecimal.valueOf(0.056), BigDecimal.valueOf(0.052), BigDecimal.valueOf(0.048), BigDecimal.valueOf(0.044), BigDecimal.valueOf(0.04), BigDecimal.valueOf(0.036), BigDecimal.valueOf(0.032), BigDecimal.valueOf(0.028), BigDecimal.valueOf(0.024), BigDecimal.valueOf(0.02), BigDecimal.valueOf(0.016), BigDecimal.valueOf(0.012), BigDecimal.valueOf(0.008), BigDecimal.valueOf(0.004), BigDecimal.valueOf(0)]
    """
    Tabelle für die Höchstbeträge des Altersentlastungsbetrags
    """

    TAB5 = [BigDecimal.ZERO, BigDecimal.valueOf(1900), BigDecimal.valueOf(1824), BigDecimal.valueOf(1748), BigDecimal.valueOf(1672), BigDecimal.valueOf(1596), BigDecimal.valueOf(1520), BigDecimal.valueOf(1444), BigDecimal.valueOf(1368), BigDecimal.valueOf(1292), BigDecimal.valueOf(1216), BigDecimal.valueOf(1140), BigDecimal.valueOf(1064), BigDecimal.valueOf(988), BigDecimal.valueOf(912), BigDecimal.valueOf(836), BigDecimal.valueOf(760), BigDecimal.valueOf(722), BigDecimal.valueOf(684), BigDecimal.valueOf(665), BigDecimal.valueOf(646), BigDecimal.valueOf(627), BigDecimal.valueOf(608), BigDecimal.valueOf(589), BigDecimal.valueOf(570), BigDecimal.valueOf(551), BigDecimal.valueOf(532), BigDecimal.valueOf(513), BigDecimal.valueOf(494), BigDecimal.valueOf(475), BigDecimal.valueOf(456), BigDecimal.valueOf(437), BigDecimal.valueOf(418), BigDecimal.valueOf(399), BigDecimal.valueOf(380), BigDecimal.valueOf(361), BigDecimal.valueOf(342), BigDecimal.valueOf(323), BigDecimal.valueOf(304), BigDecimal.valueOf(285), BigDecimal.valueOf(266), BigDecimal.valueOf(247), BigDecimal.valueOf(228), BigDecimal.valueOf(209), BigDecimal.valueOf(190), BigDecimal.valueOf(171), BigDecimal.valueOf(152), BigDecimal.valueOf(133), BigDecimal.valueOf(114), BigDecimal.valueOf(95), BigDecimal.valueOf(76), BigDecimal.valueOf(57), BigDecimal.valueOf(38), BigDecimal.valueOf(19), BigDecimal.valueOf(0)]
    """
    Tabelle fuer die Hächstbeträge des Altersentlastungsbetrags
    """

    ZAHL1 = BigDecimal.ONE
    """
    Zahlenkonstanten fuer im Plan oft genutzte BigDecimal Werte
    """

    ZAHL2 = BigDecimal.valueOf(2)
    ZAHL5 = BigDecimal.valueOf(5)
    ZAHL7 = BigDecimal.valueOf(7)
    ZAHL12 = BigDecimal.valueOf(12)
    ZAHL100 = BigDecimal.valueOf(100)
    ZAHL360 = BigDecimal.valueOf(360)
    ZAHL500 = BigDecimal.valueOf(500)
    ZAHL700 = BigDecimal.valueOf(700)
    ZAHL1000 = BigDecimal.valueOf(1000)
    ZAHL10000 = BigDecimal.valueOf(10000)

    def __init__(self, **kwargs):
        # input variables

        # 1, wenn die Anwendung des Faktorverfahrens gewählt wurden (nur in Steuerklasse IV)
        self.af = 1
        if "af" in kwargs:
            self.setAf(kwargs["af"])

        # Auf die Vollendung des 64. Lebensjahres folgende
        # Kalenderjahr (erforderlich, wenn ALTER1=1)
        self.AJAHR = 0
        if "AJAHR" in kwargs:
            self.setAjahr(kwargs["AJAHR"])

        # 1, wenn das 64. Lebensjahr zu Beginn des Kalenderjahres vollendet wurde, in dem
        # der Lohnzahlungszeitraum endet (§ 24 a EStG), sonst = 0
        self.ALTER1 = 0
        if "ALTER1" in kwargs:
            self.setAlter1(kwargs["ALTER1"])

        # Merker für die Vorsorgepauschale
        # 0 = der Arbeitnehmer ist in der Arbeitslosenversicherung pflichtversichert; es gilt die allgemeine Beitragsbemessungsgrenze
        # 1 = wenn nicht 0
        self.ALV = 0
        if "ALV" in kwargs:
            self.setAlv(kwargs["ALV"])

        # eingetragener Faktor mit drei Nachkommastellen
        self.f = 1.0
        if "f" in kwargs:
            self.setF(kwargs["f"])

        # Jahresfreibetrag für die Ermittlung der Lohnsteuer für die sonstigen Bezüge
        # sowie für Vermögensbeteiligungen nach § 19a Absatz 1 und 4 EStG nach Maßgabe der
        # elektronischen Lohnsteuerabzugsmerkmale nach § 39e EStG oder der Eintragung
        # auf der Bescheinigung für den Lohnsteuerabzug 2026 in Cent (ggf. 0)
        self.JFREIB = BigDecimal.ZERO
        if "JFREIB" in kwargs:
            self.setJfreib(kwargs["JFREIB"])

        # Jahreshinzurechnungsbetrag für die Ermittlung der Lohnsteuer für die sonstigen Bezüge
        # sowie für Vermögensbeteiligungen nach § 19a Absatz 1 und 4 EStG nach Maßgabe der
        # elektronischen Lohnsteuerabzugsmerkmale nach § 39e EStG oder der Eintragung auf der
        # Bescheinigung für den Lohnsteuerabzug 2026 in Cent (ggf. 0)
        self.JHINZU = BigDecimal.ZERO
        if "JHINZU" in kwargs:
            self.setJhinzu(kwargs["JHINZU"])

        # Voraussichtlicher Jahresarbeitslohn ohne sonstige Bezüge (d.h. auch ohne
        # die zu besteuernden Vorteile bei Vermögensbeteiligungen,
        # § 19a Absatz 4 EStG) in Cent.
        # Anmerkung: Die Eingabe dieses Feldes (ggf. 0) ist erforderlich bei Eingaben zu sonstigen
        # Bezügen (Feld SONSTB).
        # Sind in einem vorangegangenen Abrechnungszeitraum bereits sonstige Bezüge gezahlt worden,
        # so sind sie dem voraussichtlichen Jahresarbeitslohn hinzuzurechnen. Gleiches gilt für zu
        # besteuernde Vorteile bei Vermögensbeteiligungen (§ 19a Absatz 4 EStG).
        self.JRE4 = BigDecimal.ZERO
        if "JRE4" in kwargs:
            self.setJre4(kwargs["JRE4"])

        # In JRE4 enthaltene Entschädigungen nach § 24 Nummer 1 EStG und zu besteuernde
        # Vorteile bei Vermögensbeteiligungen (§ 19a Absatz 4 EStG) in Cent
        self.JRE4ENT = BigDecimal.ZERO
        if "JRE4ENT" in kwargs:
            self.setJre4ent(kwargs["JRE4ENT"])

        # In JRE4 enthaltene Versorgungsbezüge in Cent (ggf. 0)
        self.JVBEZ = BigDecimal.ZERO
        if "JVBEZ" in kwargs:
            self.setJvbez(kwargs["JVBEZ"])

        # Merker für die Vorsorgepauschale
        # 0 = der Arbeitnehmer ist in der gesetzlichen Rentenversicherung oder einer
        # berufsständischen Versorgungseinrichtung pflichtversichert oder bei Befreiung von der
        # Versicherungspflicht freiwillig versichert; es gilt die allgemeine Beitragsbemessungsgrenze
        # 
        # 1 = wenn nicht 0
        # 
        self.KRV = 0
        if "KRV" in kwargs:
            self.setKrv(kwargs["KRV"])

        # Kassenindividueller Zusatzbeitragssatz bei einem gesetzlich krankenversicherten Arbeitnehmer
        # in Prozent (bspw. 2,50 für 2,50 %) mit 2 Dezimalstellen.
        # Es ist der volle Zusatzbeitragssatz anzugeben. Die Aufteilung in Arbeitnehmer- und Arbeitgeber-
        # anteil erfolgt im Programmablauf.
        self.KVZ = BigDecimal.ZERO
        if "KVZ" in kwargs:
            self.setKvz(kwargs["KVZ"])

        # Lohnzahlungszeitraum:
        # 1 = Jahr
        # 2 = Monat
        # 3 = Woche
        # 4 = Tag
        self.LZZ = 1
        if "LZZ" in kwargs:
            self.setLzz(kwargs["LZZ"])

        # Der als elektronisches Lohnsteuerabzugsmerkmal für den Arbeitgeber nach § 39e EStG festgestellte
        # oder in der Bescheinigung für den Lohnsteuerabzug 2026 eingetragene Freibetrag für den
        # Lohnzahlungszeitraum in Cent
        self.LZZFREIB = BigDecimal.ZERO
        if "LZZFREIB" in kwargs:
            self.setLzzfreib(kwargs["LZZFREIB"])

        # Der als elektronisches Lohnsteuerabzugsmerkmal für den Arbeitgeber nach § 39e EStG festgestellte
        # oder in der Bescheinigung für den Lohnsteuerabzug 2026 eingetragene Hinzurechnungsbetrag für den
        # Lohnzahlungszeitraum in Cent
        self.LZZHINZU = BigDecimal.ZERO
        if "LZZHINZU" in kwargs:
            self.setLzzhinzu(kwargs["LZZHINZU"])

        # Nicht zu besteuernde Vorteile bei Vermögensbeteiligungen
        # (§ 19a Absatz 1 Satz 4 EStG) in Cent
        self.MBV = BigDecimal.ZERO
        if "MBV" in kwargs:
            self.setMbv(kwargs["MBV"])

        # Dem Arbeitgeber mitgeteilte Beiträge des Arbeitnehmers für eine private
        # Basiskranken- bzw. Pflege-Pflichtversicherung im Sinne des
        # § 10 Absatz 1 Nummer 3 EStG in Cent; der Wert ist unabhängig vom Lohnzahlungszeitraum
        # immer als Monatsbetrag anzugeben
        self.PKPV = BigDecimal.ZERO
        if "PKPV" in kwargs:
            self.setPkpv(kwargs["PKPV"])

        # Arbeitgeberzuschuss für eine private Basiskranken- bzw. Pflege-Pflichtversicherung im
        # Sinne des § 10 Absatz 1 Nummer 3 EStG in Cent; der Wert ist unabhängig vom
        # Lohnzahlungszeitraum immer als Monatsbetrag anzugeben
        self.PKPVAGZ = BigDecimal.ZERO
        if "PKPVAGZ" in kwargs:
            self.setPkpvagz(kwargs["PKPVAGZ"])

        # Krankenversicherung:
        # 0 = gesetzlich krankenversicherte Arbeitnehmer
        # 1 = ausschließlich privat krankenversicherte Arbeitnehmer
        self.PKV = 0
        if "PKV" in kwargs:
            self.setPkv(kwargs["PKV"])

        # Zahl der beim Arbeitnehmer zu berücksichtigenden Beitragsabschläge in der sozialen Pflegeversicherung
        # bei mehr als einem Kind
        # 0 = kein Abschlag
        # 1 = Beitragsabschlag für das 2. Kind
        # 2 = Beitragsabschläge für das 2. und 3. Kind
        # 3 = Beitragsabschläge für 2. bis 4. Kinder
        # 4 = Beitragsabschläge für 2. bis 5. oder mehr Kinder
        self.PVA = BigDecimal.ZERO
        if "PVA" in kwargs:
            self.setPva(kwargs["PVA"])

        # 1, wenn bei der sozialen Pflegeversicherung die Besonderheiten in Sachsen zu berücksichtigen sind bzw.
        # zu berücksichtigen wären
        self.PVS = 0
        if "PVS" in kwargs:
            self.setPvs(kwargs["PVS"])

        # 1, wenn er der Arbeitnehmer den Zuschlag zur sozialen Pflegeversicherung
        # zu zahlen hat
        self.PVZ = 0
        if "PVZ" in kwargs:
            self.setPvz(kwargs["PVZ"])

        # Religionsgemeinschaft des Arbeitnehmers lt. elektronischer Lohnsteuerabzugsmerkmale oder der
        # Bescheinigung für den Lohnsteuerabzug 2026 (bei keiner Religionszugehörigkeit = 0)
        self.R = 0
        if "R" in kwargs:
            self.setR(kwargs["R"])

        # Steuerpflichtiger Arbeitslohn für den Lohnzahlungszeitraum vor Berücksichtigung des
        # Versorgungsfreibetrags und des Zuschlags zum Versorgungsfreibetrag, des Altersentlastungsbetrags
        # und des als elektronisches Lohnsteuerabzugsmerkmal festgestellten oder in der Bescheinigung für
        # den Lohnsteuerabzug 2026 für den Lohnzahlungszeitraum eingetragenen Freibetrags bzw.
        # Hinzurechnungsbetrags in Cent
        self.RE4 = BigDecimal.ZERO
        if "RE4" in kwargs:
            self.setRe4(kwargs["RE4"])

        # Sonstige Bezüge einschließlich zu besteuernde Vorteile bei Vermögensbeteiligungen und Sterbegeld bei Versorgungsbezügen sowie
        # Kapitalauszahlungen/Abfindungen, in Cent (ggf. 0)
        self.SONSTB = BigDecimal.ZERO
        if "SONSTB" in kwargs:
            self.setSonstb(kwargs["SONSTB"])

        # In SONSTB enthaltene Entschädigungen nach § 24 Nummer 1 EStG sowie zu besteuernde Vorteile bei Vermögensbeteiligungen (§ 19a
        # Absatz 4 EStG), in Cent
        self.SONSTENT = BigDecimal.ZERO
        if "SONSTENT" in kwargs:
            self.setSonstent(kwargs["SONSTENT"])

        # Sterbegeld bei Versorgungsbezügen sowie Kapitalauszahlungen/Abfindungen
        # (in SONSTB enthalten), in Cent
        self.STERBE = BigDecimal.ZERO
        if "STERBE" in kwargs:
            self.setSterbe(kwargs["STERBE"])

        # Steuerklasse:
        # 1 = I
        # 2 = II
        # 3 = III
        # 4 = IV
        # 5 = V
        # 6 = VI
        self.STKL = 1
        if "STKL" in kwargs:
            self.setStkl(kwargs["STKL"])

        # In RE4 enthaltene Versorgungsbezüge in Cent (ggf. 0) ggf. unter Berücksichtigung
        # einer geänderten Bemessungsgrundlage nach  § 19 Absatz 2 Satz 10 und 11 EStG
        self.VBEZ = BigDecimal.ZERO
        if "VBEZ" in kwargs:
            self.setVbez(kwargs["VBEZ"])

        # Versorgungsbezug im Januar 2005 bzw. für den ersten vollen Monat, wenn der
        # Versorgungsbezug erstmalig nach Januar 2005 gewährt  wurde, in Cent
        self.VBEZM = BigDecimal.ZERO
        if "VBEZM" in kwargs:
            self.setVbezm(kwargs["VBEZM"])

        # Voraussichtliche Sonderzahlungen von Versorgungsbezügen im
        # Kalenderjahr des Versorgungsbeginns bei Versorgungsempfängern
        # ohne Sterbegeld, Kapitalauszahlungen/Abfindungen in Cent
        # 
        self.VBEZS = BigDecimal.ZERO
        if "VBEZS" in kwargs:
            self.setVbezs(kwargs["VBEZS"])

        # In SONSTB enthaltene Versorgungsbezüge einschließlich Sterbegeld in Cent (ggf. 0)
        self.VBS = BigDecimal.ZERO
        if "VBS" in kwargs:
            self.setVbs(kwargs["VBS"])

        # Jahr, in dem der Versorgungsbezug erstmalig gewährt wurde;
        # werden mehrere Versorgungsbezüge gezahlt, wird aus
        # Vereinfachungsgründen für die Berechnung das Jahr des ältesten
        # erstmaligen Bezugs herangezogen; auf die Möglichkeit der
        # getrennten Abrechnung verschiedenartiger Bezüge (§ 39e Absatz 5a
        # EStG) wird im Übrigen verwiesen
        self.VJAHR = 0
        if "VJAHR" in kwargs:
            self.setVjahr(kwargs["VJAHR"])

        # Zahl der Freibeträge für Kinder (eine Dezimalstelle, nur bei Steuerklassen
        # I, II, III und IV)
        self.ZKF = BigDecimal.ZERO
        if "ZKF" in kwargs:
            self.setZkf(kwargs["ZKF"])

        # Zahl der Monate, für die Versorgungsbezüge gezahlt werden [nur
        # erforderlich bei Jahresberechnung (LZZ = 1)]
        self.ZMVB = 0
        if "ZMVB" in kwargs:
            self.setZmvb(kwargs["ZMVB"])

        # output variables

        # Bemessungsgrundlage für die Kirchenlohnsteuer in Cent
        self.BK = BigDecimal.ZERO

        # Bemessungsgrundlage der sonstigen Bezüge  für die Kirchenlohnsteuer in Cent.
        # Hinweis: Negativbeträge, die aus nicht zu besteuernden Vorteilen bei
        # Vermögensbeteiligungen (§ 19a Absatz 1 Satz 4 EStG) resultieren, mindern BK
        # (maximal bis 0). Der Sonderausgabenabzug für tatsächlich erbrachte Vorsorgeaufwendungen
        # im Rahmen der Veranlagung zur Einkommensteuer bleibt unberührt.
        self.BKS = BigDecimal.ZERO

        # Für den Lohnzahlungszeitraum einzubehaltende Lohnsteuer in Cent
        self.LSTLZZ = BigDecimal.ZERO

        # Für den Lohnzahlungszeitraum einzubehaltender Solidaritätszuschlag
        # in Cent
        self.SOLZLZZ = BigDecimal.ZERO

        # Solidaritätszuschlag für sonstige Bezüge in Cent.
        # Hinweis: Negativbeträge, die aus nicht zu besteuernden Vorteilen bei
        # Vermögensbeteiligungen (§ 19a Absatz 1 Satz 4 EStG) resultieren,
        # mindern SOLZLZZ (maximal bis 0). Der Sonderausgabenabzug für
        # tatsächlich erbrachte Vorsorgeaufwendungen im Rahmen der
        # Veranlagung zur Einkommensteuer bleibt unberührt.
        self.SOLZS = BigDecimal.ZERO

        # Lohnsteuer für sonstige Bezüge in Cent
        # Hinweis: Negativbeträge, die aus nicht zu besteuernden Vorteilen bei Vermögensbeteiligungen
        # (§ 19a Absatz 1 Satz 4 EStG) resultieren, mindern LSTLZZ (maximal bis 0). Der
        # Sonderausgabenabzug für tatsächlich erbrachte Vorsorgeaufwendungen im Rahmen der
        # Veranlagung zur Einkommensteuer bleibt unberührt.
        self.STS = BigDecimal.ZERO

        # Verbrauchter Freibetrag bei Berechnung des laufenden Arbeitslohns, in Cent
        self.VFRB = BigDecimal.ZERO

        # Verbrauchter Freibetrag bei Berechnung des voraussichtlichen Jahresarbeitslohns, in Cent
        self.VFRBS1 = BigDecimal.ZERO

        # Verbrauchter Freibetrag bei Berechnung der sonstigen Bezüge, in Cent
        self.VFRBS2 = BigDecimal.ZERO

        # Für die weitergehende Berücksichtigung des Steuerfreibetrags nach dem DBA Türkei verfügbares ZVE über
        # dem Grundfreibetrag bei der Berechnung des laufenden Arbeitslohns, in Cent
        self.WVFRB = BigDecimal.ZERO

        # Für die weitergehende Berücksichtigung des Steuerfreibetrags nach dem DBA Türkei verfügbares ZVE über dem Grundfreibetrag
        # bei der Berechnung des voraussichtlichen Jahresarbeitslohns, in Cent
        self.WVFRBO = BigDecimal.ZERO

        # Für die weitergehende Berücksichtigung des Steuerfreibetrags nach dem DBA Türkei verfügbares ZVE
        # über dem Grundfreibetrag bei der Berechnung der sonstigen Bezüge, in Cent
        self.WVFRBM = BigDecimal.ZERO

        # internal variables

        # Altersentlastungsbetrag in Euro, Cent (2 Dezimalstellen)
        self.ALTE = BigDecimal.ZERO

        # Arbeitnehmer-Pauschbetrag/Werbungskosten-Pauschbetrag in Euro
        self.ANP = BigDecimal.ZERO

        # Auf den Lohnzahlungszeitraum entfallender Anteil von Jahreswerten
        # auf ganze Cent abgerundet
        self.ANTEIL1 = BigDecimal.ZERO

        # Beitragssatz des Arbeitnehmers zur Arbeitslosenversicherung (4 Dezimalstellen)
        self.AVSATZAN = BigDecimal.ZERO

        # Beitragsbemessungsgrenze in der gesetzlichen Krankenversicherung
        # und der sozialen Pflegeversicherung in Euro
        self.BBGKVPV = BigDecimal.ZERO

        # Allgemeine Beitragsbemessungsgrenze in der allgemeinen Rentenversicherung und Arbeitslosenversicherung in Euro
        self.BBGRVALV = BigDecimal.ZERO

        # Bemessungsgrundlage für Altersentlastungsbetrag in Euro, Cent
        # (2 Dezimalstellen)
        self.BMG = BigDecimal.ZERO

        # Differenz zwischen ST1 und ST2 in Euro
        self.DIFF = BigDecimal.ZERO

        # Entlastungsbetrag für Alleinerziehende in Euro
        self.EFA = BigDecimal.ZERO

        # Versorgungsfreibetrag in Euro, Cent (2 Dezimalstellen)
        self.FVB = BigDecimal.ZERO

        # Versorgungsfreibetrag in Euro, Cent (2 Dezimalstellen) für die Berechnung
        # der Lohnsteuer beim sonstigen Bezug
        self.FVBSO = BigDecimal.ZERO

        # Zuschlag zum Versorgungsfreibetrag in Euro
        self.FVBZ = BigDecimal.ZERO

        # Zuschlag zum Versorgungsfreibetrag in Euro für die Berechnung
        # der Lohnsteuer beim sonstigen Bezug
        self.FVBZSO = BigDecimal.ZERO

        # Grundfreibetrag in Euro
        self.GFB = BigDecimal.ZERO

        # Maximaler Altersentlastungsbetrag in Euro
        self.HBALTE = BigDecimal.ZERO

        # Maßgeblicher maximaler Versorgungsfreibetrag in Euro, Cent (2 Dezimalstellen)
        self.HFVB = BigDecimal.ZERO

        # Maßgeblicher maximaler Zuschlag zum Versorgungsfreibetrag in Euro, Cent
        # (2 Dezimalstellen)
        self.HFVBZ = BigDecimal.ZERO

        # Maßgeblicher maximaler Zuschlag zum Versorgungsfreibetrag in Euro, Cent (2 Dezimalstellen)
        # für die Berechnung der Lohnsteuer für den sonstigen Bezug
        self.HFVBZSO = BigDecimal.ZERO

        # Zwischenfeld zu X für die Berechnung der Steuer nach § 39b
        # Absatz 2 Satz 7 EStG in Euro
        self.HOCH = BigDecimal.ZERO

        # Nummer der Tabellenwerte für Versorgungsparameter
        self.J = 0

        # Jahressteuer nach § 51a EStG, aus der Solidaritätszuschlag und
        # Bemessungsgrundlage für die Kirchenlohnsteuer ermittelt werden in Euro
        self.JBMG = BigDecimal.ZERO

        # Auf einen Jahreslohn hochgerechneter LZZFREIB in Euro, Cent
        # (2 Dezimalstellen)
        self.JLFREIB = BigDecimal.ZERO

        # Auf einen Jahreslohn hochgerechnete LZZHINZU in Euro, Cent
        # (2 Dezimalstellen)
        self.JLHINZU = BigDecimal.ZERO

        # Jahreswert, dessen Anteil für einen Lohnzahlungszeitraum in
        # UPANTEIL errechnet werden soll in Cent
        self.JW = BigDecimal.ZERO

        # Nummer der Tabellenwerte für Parameter bei Altersentlastungsbetrag
        self.K = 0

        # Summe der Freibeträge für Kinder in Euro
        self.KFB = BigDecimal.ZERO

        # Beitragssatz des Arbeitnehmers zur Krankenversicherung
        # (5 Dezimalstellen)
        self.KVSATZAN = BigDecimal.ZERO

        # Kennzahl für die Einkommensteuer-Tabellenart:
        # 1 = Grundtarif
        # 2 = Splittingverfahren
        self.KZTAB = 0

        # Jahreslohnsteuer in Euro
        self.LSTJAHR = BigDecimal.ZERO

        # Zwischenfelder der Jahreslohnsteuer in Cent
        self.LSTOSO = BigDecimal.ZERO
        self.LSTSO = BigDecimal.ZERO

        # Mindeststeuer für die Steuerklassen V und VI in Euro
        self.MIST = BigDecimal.ZERO

        # Auf einen Jahreswert hochgerechneter Arbeitgeberzuschuss für eine private Basiskranken-
        # bzw. Pflege-Pflichtversicherung im Sinne des § 10 Absatz 1 Nummer 3 EStG in Euro, Cent (2 Dezimalstellen)
        self.PKPVAGZJ = BigDecimal.ZERO

        # Beitragssatz des Arbeitnehmers zur Pflegeversicherung (6 Dezimalstellen)
        self.PVSATZAN = BigDecimal.ZERO

        # Beitragssatz des Arbeitnehmers in der allgemeinen gesetzlichen Rentenversicherung (4 Dezimalstellen)
        self.RVSATZAN = BigDecimal.ZERO

        # Rechenwert in Gleitkommadarstellung
        self.RW = BigDecimal.ZERO

        # Sonderausgaben-Pauschbetrag in Euro
        self.SAP = BigDecimal.ZERO

        # Freigrenze für den Solidaritätszuschlag in Euro
        self.SOLZFREI = BigDecimal.ZERO

        # Solidaritätszuschlag auf die Jahreslohnsteuer in Euro, Cent (2 Dezimalstellen)
        self.SOLZJ = BigDecimal.ZERO

        # Zwischenwert für den Solidaritätszuschlag auf die Jahreslohnsteuer
        # in Euro, Cent (2 Dezimalstellen)
        self.SOLZMIN = BigDecimal.ZERO

        # Bemessungsgrundlage des Solidaritätszuschlags zur Prüfung der Freigrenze beim Solidaritätszuschlag für sonstige Bezüge in Euro
        self.SOLZSBMG = BigDecimal.ZERO

        # Zu versteuerndes Einkommen für die Ermittlung der
        # Bemessungsgrundlage des Solidaritätszuschlags zur Prüfung der
        # Freigrenze beim Solidaritätszuschlag für sonstige Bezüge in Euro,
        # Cent (2 Dezimalstellen)
        self.SOLZSZVE = BigDecimal.ZERO

        # Tarifliche Einkommensteuer in Euro
        self.ST = BigDecimal.ZERO

        # Tarifliche Einkommensteuer auf das 1,25-fache ZX in Euro
        self.ST1 = BigDecimal.ZERO

        # Tarifliche Einkommensteuer auf das 0,75-fache ZX in Euro
        self.ST2 = BigDecimal.ZERO

        # Bemessungsgrundlage für den Versorgungsfreibetrag in Cent
        self.VBEZB = BigDecimal.ZERO

        # Bemessungsgrundlage für den Versorgungsfreibetrag in Cent für
        # den sonstigen Bezug
        self.VBEZBSO = BigDecimal.ZERO

        # Zwischenfeld zu X für die Berechnung der Steuer nach § 39b
        # Absatz 2 Satz 7 EStG in Euro
        self.VERGL = BigDecimal.ZERO

        # Auf den Höchstbetrag begrenzte Beiträge zur Arbeitslosenversicherung
        # einschließlich Kranken- und Pflegeversicherung in Euro, Cent (2 Dezimalstellen)
        self.VSPHB = BigDecimal.ZERO

        # Vorsorgepauschale mit Teilbeträgen für die Rentenversicherung
        # sowie die gesetzliche Kranken- und soziale Pflegeversicherung nach
        # fiktiven Beträgen oder ggf. für die private Basiskrankenversicherung
        # und private Pflege-Pflichtversicherung in Euro, Cent (2 Dezimalstellen)
        self.VSP = BigDecimal.ZERO

        # Vorsorgepauschale mit Teilbeträgen für die Rentenversicherung sowie auf den Höchstbetrag
        # begrenzten Teilbeträgen für die Arbeitslosen-, Kranken- und Pflegeversicherung in
        # Euro, Cent (2 Dezimalstellen)
        self.VSPN = BigDecimal.ZERO

        # Teilbetrag für die Arbeitslosenversicherung bei der Berechnung der
        # Vorsorgepauschale in Euro, Cent (2 Dezimalstellen)
        self.VSPALV = BigDecimal.ZERO

        # Vorsorgepauschale mit Teilbeträgen für die gesetzliche Kranken- und soziale Pflegeversicherung
        # nach fiktiven Beträgen oder ggf. für die private Basiskrankenversicherung und private
        # Pflege-Pflichtversicherung in Euro, Cent (2 Dezimalstellen)
        self.VSPKVPV = BigDecimal.ZERO

        # Teilbetrag für die Rentenversicherung bei der Berechnung der Vorsorgepauschale
        # in Euro, Cent (2 Dezimalstellen)
        self.VSPR = BigDecimal.ZERO

        # Erster Grenzwert in Steuerklasse V/VI in Euro
        self.W1STKL5 = BigDecimal.ZERO

        # Zweiter Grenzwert in Steuerklasse V/VI in Euro
        self.W2STKL5 = BigDecimal.ZERO

        # Dritter Grenzwert in Steuerklasse V/VI in Euro
        self.W3STKL5 = BigDecimal.ZERO

        # Zu versteuerndes Einkommen gem. § 32a Absatz 1 und 5 EStG in Euro, Cent
        # (2 Dezimalstellen)
        self.X = BigDecimal.ZERO

        # Gem. § 32a Absatz 1 EStG (6 Dezimalstellen)
        self.Y = BigDecimal.ZERO

        # Auf einen Jahreslohn hochgerechnetes RE4 in Euro, Cent (2 Dezimalstellen)
        # nach Abzug der Freibeträge nach § 39 b Absatz 2 Satz 3 und 4 EStG
        self.ZRE4 = BigDecimal.ZERO

        # Auf einen Jahreslohn hochgerechnetes RE4 in Euro, Cent (2 Dezimalstellen)
        self.ZRE4J = BigDecimal.ZERO

        # Auf einen Jahreslohn hochgerechnetes RE4, ggf. nach Abzug der
        # Entschädigungen i.S.d. § 24 Nummer 1 EStG in Euro, Cent
        # (2 Dezimalstellen)
        self.ZRE4VP = BigDecimal.ZERO

        # Zwischenfeld zu ZRE4VP für die Begrenzung auf die jeweilige
        # Beitragsbemessungsgrenze in Euro, Cent (2 Dezimalstellen)"
        self.ZRE4VPR = BigDecimal.ZERO

        # Feste Tabellenfreibeträge (ohne Vorsorgepauschale) in Euro, Cent
        # (2 Dezimalstellen)
        self.ZTABFB = BigDecimal.ZERO

        # Auf einen Jahreslohn hochgerechnetes VBEZ abzüglich FVB in
        # Euro, Cent (2 Dezimalstellen)
        self.ZVBEZ = BigDecimal.ZERO

        # Auf einen Jahreslohn hochgerechnetes VBEZ in Euro, Cent (2 Dezimalstellen)
        self.ZVBEZJ = BigDecimal.ZERO

        # Zu versteuerndes Einkommen in Euro, Cent (2 Dezimalstellen)
        self.ZVE = BigDecimal.ZERO

        # Zwischenfeld zu X für die Berechnung der Steuer nach § 39b
        # Absatz 2 Satz 7 EStG in Euro
        self.ZX = BigDecimal.ZERO

        # Zwischenfeld zu X für die Berechnung der Steuer nach § 39b
        # Absatz 2 Satz 7 EStG in Euro
        self.ZZX = BigDecimal.ZERO


    def setAf(self, value):
        self.af = value

    def setAjahr(self, value):
        self.AJAHR = value

    def setAlter1(self, value):
        self.ALTER1 = value

    def setAlv(self, value):
        self.ALV = value

    def setF(self, value):
        self.f = value

    def setJfreib(self, value):
        self.JFREIB = BigDecimal(value)

    def setJhinzu(self, value):
        self.JHINZU = BigDecimal(value)

    def setJre4(self, value):
        self.JRE4 = BigDecimal(value)

    def setJre4ent(self, value):
        self.JRE4ENT = BigDecimal(value)

    def setJvbez(self, value):
        self.JVBEZ = BigDecimal(value)

    def setKrv(self, value):
        self.KRV = value

    def setKvz(self, value):
        self.KVZ = BigDecimal(value)

    def setLzz(self, value):
        self.LZZ = value

    def setLzzfreib(self, value):
        self.LZZFREIB = BigDecimal(value)

    def setLzzhinzu(self, value):
        self.LZZHINZU = BigDecimal(value)

    def setMbv(self, value):
        self.MBV = BigDecimal(value)

    def setPkpv(self, value):
        self.PKPV = BigDecimal(value)

    def setPkpvagz(self, value):
        self.PKPVAGZ = BigDecimal(value)

    def setPkv(self, value):
        self.PKV = value

    def setPva(self, value):
        self.PVA = BigDecimal(value)

    def setPvs(self, value):
        self.PVS = value

    def setPvz(self, value):
        self.PVZ = value

    def setR(self, value):
        self.R = value

    def setRe4(self, value):
        self.RE4 = BigDecimal(value)

    def setSonstb(self, value):
        self.SONSTB = BigDecimal(value)

    def setSonstent(self, value):
        self.SONSTENT = BigDecimal(value)

    def setSterbe(self, value):
        self.STERBE = BigDecimal(value)

    def setStkl(self, value):
        self.STKL = value

    def setVbez(self, value):
        self.VBEZ = BigDecimal(value)

    def setVbezm(self, value):
        self.VBEZM = BigDecimal(value)

    def setVbezs(self, value):
        self.VBEZS = BigDecimal(value)

    def setVbs(self, value):
        self.VBS = BigDecimal(value)

    def setVjahr(self, value):
        self.VJAHR = value

    def setZkf(self, value):
        self.ZKF = BigDecimal(value)

    def setZmvb(self, value):
        self.ZMVB = value

    def getBk(self):
        return self.BK

    def getBks(self):
        return self.BKS

    def getLstlzz(self):
        return self.LSTLZZ

    def getSolzlzz(self):
        return self.SOLZLZZ

    def getSolzs(self):
        return self.SOLZS

    def getSts(self):
        return self.STS

    def getVfrb(self):
        return self.VFRB

    def getVfrbs1(self):
        return self.VFRBS1

    def getVfrbs2(self):
        return self.VFRBS2

    def getWvfrb(self):
        return self.WVFRB

    def getWvfrbo(self):
        return self.WVFRBO

    def getWvfrbm(self):
        return self.WVFRBM

    def MAIN(self):
        """
        PROGRAMMABLAUFPLAN 2026
        Steueruung, PAP Seite 13
        """
        self.MPARA()
        self.MRE4JL()
        self.VBEZBSO = BigDecimal.ZERO
        self.MRE4()
        self.MRE4ABZ()
        self.MBERECH()
        self.MSONST()

    def MPARA(self):
        """
        Zuweisung von Werten für bestimmte Steuer- und Sozialversicherungsparameter  PAP Seite 14
        """
        self.BBGRVALV = BigDecimal.valueOf(101400)
        self.AVSATZAN = BigDecimal.valueOf(0.013)
        self.RVSATZAN = BigDecimal.valueOf(0.093)
        self.BBGKVPV = BigDecimal.valueOf(69750)
        self.KVSATZAN = self.KVZ.divide(Lohnsteuer.ZAHL2).divide(Lohnsteuer.ZAHL100).add(BigDecimal.valueOf(0.07))
        if self.PVS == 1:
            self.PVSATZAN = BigDecimal.valueOf(0.023)
        else:
            self.PVSATZAN = BigDecimal.valueOf(0.018)
        if self.PVZ == 1:
            self.PVSATZAN = self.PVSATZAN.add(BigDecimal.valueOf(0.006))
        else:
            self.PVSATZAN = self.PVSATZAN.subtract(self.PVA.multiply(BigDecimal.valueOf(0.0025)))
        self.W1STKL5 = BigDecimal.valueOf(14071)
        self.W2STKL5 = BigDecimal.valueOf(34939)
        self.W3STKL5 = BigDecimal.valueOf(222260)
        self.GFB = BigDecimal.valueOf(12348)
        self.SOLZFREI = BigDecimal.valueOf(20350)

    def MRE4JL(self):
        """
        Ermittlung des Jahresarbeitslohns nach § 39 b Absatz 2 Satz 2 EStG, PAP Seite 15
        """
        if self.LZZ == 1:
            self.ZRE4J = self.RE4.divide(Lohnsteuer.ZAHL100, 2, BigDecimal.ROUND_DOWN)
            self.ZVBEZJ = self.VBEZ.divide(Lohnsteuer.ZAHL100, 2, BigDecimal.ROUND_DOWN)
            self.JLFREIB = self.LZZFREIB.divide(Lohnsteuer.ZAHL100, 2, BigDecimal.ROUND_DOWN)
            self.JLHINZU = self.LZZHINZU.divide(Lohnsteuer.ZAHL100, 2, BigDecimal.ROUND_DOWN)
        else:
            if self.LZZ == 2:
                self.ZRE4J = self.RE4.multiply(Lohnsteuer.ZAHL12).divide(Lohnsteuer.ZAHL100, 2, BigDecimal.ROUND_DOWN)
                self.ZVBEZJ = self.VBEZ.multiply(Lohnsteuer.ZAHL12).divide(Lohnsteuer.ZAHL100, 2, BigDecimal.ROUND_DOWN)
                self.JLFREIB = self.LZZFREIB.multiply(Lohnsteuer.ZAHL12).divide(Lohnsteuer.ZAHL100, 2, BigDecimal.ROUND_DOWN)
                self.JLHINZU = self.LZZHINZU.multiply(Lohnsteuer.ZAHL12).divide(Lohnsteuer.ZAHL100, 2, BigDecimal.ROUND_DOWN)
            else:
                if self.LZZ == 3:
                    self.ZRE4J = self.RE4.multiply(Lohnsteuer.ZAHL360).divide(Lohnsteuer.ZAHL700, 2, BigDecimal.ROUND_DOWN)
                    self.ZVBEZJ = self.VBEZ.multiply(Lohnsteuer.ZAHL360).divide(Lohnsteuer.ZAHL700, 2, BigDecimal.ROUND_DOWN)
                    self.JLFREIB = self.LZZFREIB.multiply(Lohnsteuer.ZAHL360).divide(Lohnsteuer.ZAHL700, 2, BigDecimal.ROUND_DOWN)
                    self.JLHINZU = self.LZZHINZU.multiply(Lohnsteuer.ZAHL360).divide(Lohnsteuer.ZAHL700, 2, BigDecimal.ROUND_DOWN)
                else:
                    self.ZRE4J = self.RE4.multiply(Lohnsteuer.ZAHL360).divide(Lohnsteuer.ZAHL100, 2, BigDecimal.ROUND_DOWN)
                    self.ZVBEZJ = self.VBEZ.multiply(Lohnsteuer.ZAHL360).divide(Lohnsteuer.ZAHL100, 2, BigDecimal.ROUND_DOWN)
                    self.JLFREIB = self.LZZFREIB.multiply(Lohnsteuer.ZAHL360).divide(Lohnsteuer.ZAHL100, 2, BigDecimal.ROUND_DOWN)
                    self.JLHINZU = self.LZZHINZU.multiply(Lohnsteuer.ZAHL360).divide(Lohnsteuer.ZAHL100, 2, BigDecimal.ROUND_DOWN)
        if self.af == 0:
            self.f = 1

    def MRE4(self):
        """
        Freibeträge für Versorgungsbezüge, Altersentlastungsbetrag (§ 39b Absatz 2 Satz 3 EStG), PAP Seite 16
        """
        if self.ZVBEZJ.compareTo(BigDecimal.ZERO) == 0:
            self.FVBZ = BigDecimal.ZERO
            self.FVB = BigDecimal.ZERO
            self.FVBZSO = BigDecimal.ZERO
            self.FVBSO = BigDecimal.ZERO
        else:
            if self.VJAHR < 2006:
                self.J = 1
            else:
                if self.VJAHR < 2058:
                    self.J = self.VJAHR - 2004
                else:
                    self.J = 54
            if self.LZZ == 1:
                self.VBEZB = self.VBEZM.multiply(BigDecimal.valueOf(self.ZMVB)).add(self.VBEZS)
                self.HFVB = Lohnsteuer.TAB2[self.J].divide(Lohnsteuer.ZAHL12).multiply(BigDecimal.valueOf(self.ZMVB)).setScale(0, BigDecimal.ROUND_UP)
                self.FVBZ = Lohnsteuer.TAB3[self.J].divide(Lohnsteuer.ZAHL12).multiply(BigDecimal.valueOf(self.ZMVB)).setScale(0, BigDecimal.ROUND_UP)
            else:
                self.VBEZB = self.VBEZM.multiply(Lohnsteuer.ZAHL12).add(self.VBEZS).setScale(2, BigDecimal.ROUND_DOWN)
                self.HFVB = Lohnsteuer.TAB2[self.J]
                self.FVBZ = Lohnsteuer.TAB3[self.J]
            self.FVB = self.VBEZB.multiply(Lohnsteuer.TAB1[self.J]).divide(Lohnsteuer.ZAHL100).setScale(2, BigDecimal.ROUND_UP)
            if self.FVB.compareTo(self.HFVB) == 1:
                self.FVB = self.HFVB
            if self.FVB.compareTo(self.ZVBEZJ) == 1:
                self.FVB = self.ZVBEZJ
            self.FVBSO = self.FVB.add(self.VBEZBSO.multiply(Lohnsteuer.TAB1[self.J]).divide(Lohnsteuer.ZAHL100)).setScale(2, BigDecimal.ROUND_UP)
            if self.FVBSO.compareTo(Lohnsteuer.TAB2[self.J]) == 1:
                self.FVBSO = Lohnsteuer.TAB2[self.J]
            self.HFVBZSO = self.VBEZB.add(self.VBEZBSO).divide(Lohnsteuer.ZAHL100).subtract(self.FVBSO).setScale(2, BigDecimal.ROUND_DOWN)
            self.FVBZSO = self.FVBZ.add(self.VBEZBSO.divide(Lohnsteuer.ZAHL100)).setScale(0, BigDecimal.ROUND_UP)
            if self.FVBZSO.compareTo(self.HFVBZSO) == 1:
                self.FVBZSO = self.HFVBZSO.setScale(0, BigDecimal.ROUND_UP)
            if self.FVBZSO.compareTo(Lohnsteuer.TAB3[self.J]) == 1:
                self.FVBZSO = Lohnsteuer.TAB3[self.J]
            self.HFVBZ = self.VBEZB.divide(Lohnsteuer.ZAHL100).subtract(self.FVB).setScale(2, BigDecimal.ROUND_DOWN)
            if self.FVBZ.compareTo(self.HFVBZ) == 1:
                self.FVBZ = self.HFVBZ.setScale(0, BigDecimal.ROUND_UP)
        self.MRE4ALTE()

    def MRE4ALTE(self):
        """
        Altersentlastungsbetrag (§ 39b Absatz 2 Satz 3 EStG), PAP Seite 17
        """
        if self.ALTER1 == 0:
            self.ALTE = BigDecimal.ZERO
        else:
            if self.AJAHR < 2006:
                self.K = 1
            else:
                if self.AJAHR < 2058:
                    self.K = self.AJAHR - 2004
                else:
                    self.K = 54
            self.BMG = self.ZRE4J.subtract(self.ZVBEZJ)
            self.ALTE = self.BMG.multiply(Lohnsteuer.TAB4[self.K]).setScale(0, BigDecimal.ROUND_UP)
            self.HBALTE = Lohnsteuer.TAB5[self.K]
            if self.ALTE.compareTo(self.HBALTE) == 1:
                self.ALTE = self.HBALTE

    def MRE4ABZ(self):
        """
        Ermittlung des Jahresarbeitslohns nach Abzug der Freibeträge nach § 39 b Absatz 2 Satz 3 und 4 EStG, PAP Seite 20
        """
        self.ZRE4 = self.ZRE4J.subtract(self.FVB).subtract(self.ALTE).subtract(self.JLFREIB).add(self.JLHINZU).setScale(2, BigDecimal.ROUND_DOWN)
        if self.ZRE4.compareTo(BigDecimal.ZERO) == -1:
            self.ZRE4 = BigDecimal.ZERO
        self.ZRE4VP = self.ZRE4J
        self.ZVBEZ = self.ZVBEZJ.subtract(self.FVB).setScale(2, BigDecimal.ROUND_DOWN)
        if self.ZVBEZ.compareTo(BigDecimal.ZERO) == -1:
            self.ZVBEZ = BigDecimal.ZERO

    def MBERECH(self):
        """
        Berechnung fuer laufende Lohnzahlungszeitraueme Seite 21
        """
        self.MZTABFB()
        self.VFRB = self.ANP.add(self.FVB.add(self.FVBZ)).multiply(Lohnsteuer.ZAHL100).setScale(0, BigDecimal.ROUND_DOWN)
        self.MLSTJAHR()
        self.WVFRB = self.ZVE.subtract(self.GFB).multiply(Lohnsteuer.ZAHL100).setScale(0, BigDecimal.ROUND_DOWN)
        if self.WVFRB.compareTo(BigDecimal.ZERO) == -1:
            self.WVFRB = BigDecimal.ZERO
        self.LSTJAHR = self.ST.multiply(BigDecimal.valueOf(self.f)).setScale(0, BigDecimal.ROUND_DOWN)
        self.UPLSTLZZ()
        if self.ZKF.compareTo(BigDecimal.ZERO) == 1:
            self.ZTABFB = self.ZTABFB.add(self.KFB)
            self.MRE4ABZ()
            self.MLSTJAHR()
            self.JBMG = self.ST.multiply(BigDecimal.valueOf(self.f)).setScale(0, BigDecimal.ROUND_DOWN)
        else:
            self.JBMG = self.LSTJAHR
        self.MSOLZ()

    def MZTABFB(self):
        """
        Ermittlung der festen Tabellenfreibeträge (ohne Vorsorgepauschale), PAP Seite 22
        """
        self.ANP = BigDecimal.ZERO
        if self.ZVBEZ.compareTo(BigDecimal.ZERO) >= 0 and self.ZVBEZ.compareTo(self.FVBZ) == -1:
            self.FVBZ = BigDecimal.valueOf(self.ZVBEZ.longValue())
        if self.STKL < 6:
            if self.ZVBEZ.compareTo(BigDecimal.ZERO) == 1:
                if self.ZVBEZ.subtract(self.FVBZ).compareTo(BigDecimal.valueOf(102)) == -1:
                    self.ANP = self.ZVBEZ.subtract(self.FVBZ).setScale(0, BigDecimal.ROUND_UP)
                else:
                    self.ANP = BigDecimal.valueOf(102)
        else:
            self.FVBZ = BigDecimal.ZERO
            self.FVBZSO = BigDecimal.ZERO
        if self.STKL < 6:
            if self.ZRE4.compareTo(self.ZVBEZ) == 1:
                if self.ZRE4.subtract(self.ZVBEZ).compareTo(BigDecimal.valueOf(1230)) == -1:
                    self.ANP = self.ANP.add(self.ZRE4).subtract(self.ZVBEZ).setScale(0, BigDecimal.ROUND_UP)
                else:
                    self.ANP = self.ANP.add(BigDecimal.valueOf(1230))
        self.KZTAB = 1
        if self.STKL == 1:
            self.SAP = BigDecimal.valueOf(36)
            self.KFB = self.ZKF.multiply(BigDecimal.valueOf(9756)).setScale(0, BigDecimal.ROUND_DOWN)
        else:
            if self.STKL == 2:
                self.EFA = BigDecimal.valueOf(4260)
                self.SAP = BigDecimal.valueOf(36)
                self.KFB = self.ZKF.multiply(BigDecimal.valueOf(9756)).setScale(0, BigDecimal.ROUND_DOWN)
            else:
                if self.STKL == 3:
                    self.KZTAB = 2
                    self.SAP = BigDecimal.valueOf(36)
                    self.KFB = self.ZKF.multiply(BigDecimal.valueOf(9756)).setScale(0, BigDecimal.ROUND_DOWN)
                else:
                    if self.STKL == 4:
                        self.SAP = BigDecimal.valueOf(36)
                        self.KFB = self.ZKF.multiply(BigDecimal.valueOf(4878)).setScale(0, BigDecimal.ROUND_DOWN)
                    else:
                        if self.STKL == 5:
                            self.SAP = BigDecimal.valueOf(36)
                            self.KFB = BigDecimal.ZERO
                        else:
                            self.KFB = BigDecimal.ZERO
        self.ZTABFB = self.EFA.add(self.ANP).add(self.SAP).add(self.FVBZ).setScale(2, BigDecimal.ROUND_DOWN)

    def MLSTJAHR(self):
        """
        Ermittlung Jahreslohnsteuer, PAP Seite 23
        """
        self.UPEVP()
        self.ZVE = self.ZRE4.subtract(self.ZTABFB).subtract(self.VSP)
        self.UPMLST()

    def UPLSTLZZ(self):
        """
        PAP Seite 24
        """
        self.JW = self.LSTJAHR.multiply(Lohnsteuer.ZAHL100)
        self.UPANTEIL()
        self.LSTLZZ = self.ANTEIL1

    def UPMLST(self):
        """
        PAP Seite 25
        """
        if self.ZVE.compareTo(Lohnsteuer.ZAHL1) == -1:
            self.ZVE = BigDecimal.ZERO
            self.X = BigDecimal.ZERO
        else:
            self.X = self.ZVE.divide(BigDecimal.valueOf(self.KZTAB)).setScale(0, BigDecimal.ROUND_DOWN)
        if self.STKL < 5:
            self.UPTAB26()
        else:
            self.MST5_6()

    def UPEVP(self):
        """
        Vorsorgepauschale (§ 39b Absatz 2 Satz 5 Nummer 3 EStG) PAP Seite 26
        """
        if self.KRV == 1:
            self.VSPR = BigDecimal.ZERO
        else:
            if self.ZRE4VP.compareTo(self.BBGRVALV) == 1:
                self.ZRE4VPR = self.BBGRVALV
            else:
                self.ZRE4VPR = self.ZRE4VP
            self.VSPR = self.ZRE4VPR.multiply(self.RVSATZAN).setScale(2, BigDecimal.ROUND_DOWN)
        self.MVSPKVPV()
        if self.ALV == 1:
            pass
        else:
            if self.STKL == 6:
                pass
            else:
                self.MVSPHB()

    def MVSPKVPV(self):
        """
        Vorsorgepauschale (§ 39b Absatz 2 Satz 5 Nummer 3 Buchstaben b bis d EStG), PAP Seite 27
        """
        if self.ZRE4VP.compareTo(self.BBGKVPV) == 1:
            self.ZRE4VPR = self.BBGKVPV
        else:
            self.ZRE4VPR = self.ZRE4VP
        if self.PKV > 0:
            if self.STKL == 6:
                self.VSPKVPV = BigDecimal.ZERO
            else:
                self.PKPVAGZJ = self.PKPVAGZ.multiply(Lohnsteuer.ZAHL12).divide(Lohnsteuer.ZAHL100).setScale(2, BigDecimal.ROUND_DOWN)
                self.VSPKVPV = self.PKPV.multiply(Lohnsteuer.ZAHL12).divide(Lohnsteuer.ZAHL100).setScale(2, BigDecimal.ROUND_DOWN)
                self.VSPKVPV = self.VSPKVPV.subtract(self.PKPVAGZJ)
                if self.VSPKVPV.compareTo(BigDecimal.ZERO) == -1:
                    self.VSPKVPV = BigDecimal.ZERO
        else:
            self.VSPKVPV = self.ZRE4VPR.multiply(self.KVSATZAN.add(self.PVSATZAN)).setScale(2, BigDecimal.ROUND_DOWN)
        self.VSP = self.VSPKVPV.add(self.VSPR).setScale(0, BigDecimal.ROUND_UP)

    def MVSPHB(self):
        """
        Höchstbetragsberechnung zur Arbeitslosenversicherung (§ 39b Absatz 2 Satz 5 Nummer 3 Buchstabe e EStG), PAP Seite 28
        """
        if self.ZRE4VP.compareTo(self.BBGRVALV) == 1:
            self.ZRE4VPR = self.BBGRVALV
        else:
            self.ZRE4VPR = self.ZRE4VP
        self.VSPALV = self.AVSATZAN.multiply(self.ZRE4VPR).setScale(2, BigDecimal.ROUND_DOWN)
        self.VSPHB = self.VSPALV.add(self.VSPKVPV).setScale(2, BigDecimal.ROUND_DOWN)
        if self.VSPHB.compareTo(BigDecimal.valueOf(1900)) == 1:
            self.VSPHB = BigDecimal.valueOf(1900)
        self.VSPN = self.VSPR.add(self.VSPHB).setScale(0, BigDecimal.ROUND_UP)
        if self.VSPN.compareTo(self.VSP) == 1:
            self.VSP = self.VSPN

    def MST5_6(self):
        """
        Lohnsteuer fuer die Steuerklassen V und VI (§ 39b Absatz 2 Satz 7 EStG), PAP Seite 29
        """
        self.ZZX = self.X
        if self.ZZX.compareTo(self.W2STKL5) == 1:
            self.ZX = self.W2STKL5
            self.UP5_6()
            if self.ZZX.compareTo(self.W3STKL5) == 1:
                self.ST = self.ST.add(self.W3STKL5.subtract(self.W2STKL5).multiply(BigDecimal.valueOf(0.42))).setScale(0, BigDecimal.ROUND_DOWN)
                self.ST = self.ST.add(self.ZZX.subtract(self.W3STKL5).multiply(BigDecimal.valueOf(0.45))).setScale(0, BigDecimal.ROUND_DOWN)
            else:
                self.ST = self.ST.add(self.ZZX.subtract(self.W2STKL5).multiply(BigDecimal.valueOf(0.42))).setScale(0, BigDecimal.ROUND_DOWN)
        else:
            self.ZX = self.ZZX
            self.UP5_6()
            if self.ZZX.compareTo(self.W1STKL5) == 1:
                self.VERGL = self.ST
                self.ZX = self.W1STKL5
                self.UP5_6()
                self.HOCH = self.ST.add(self.ZZX.subtract(self.W1STKL5).multiply(BigDecimal.valueOf(0.42))).setScale(0, BigDecimal.ROUND_DOWN)
                if self.HOCH.compareTo(self.VERGL) == -1:
                    self.ST = self.HOCH
                else:
                    self.ST = self.VERGL

    def UP5_6(self):
        """
        Unterprogramm zur Lohnsteuer fuer die Steuerklassen V und VI (§ 39b Absatz 2 Satz 7 EStG), PAP Seite 30
        """
        self.X = self.ZX.multiply(BigDecimal.valueOf(1.25)).setScale(0, BigDecimal.ROUND_DOWN)
        self.UPTAB26()
        self.ST1 = self.ST
        self.X = self.ZX.multiply(BigDecimal.valueOf(0.75)).setScale(0, BigDecimal.ROUND_DOWN)
        self.UPTAB26()
        self.ST2 = self.ST
        self.DIFF = self.ST1.subtract(self.ST2).multiply(Lohnsteuer.ZAHL2)
        self.MIST = self.ZX.multiply(BigDecimal.valueOf(0.14)).setScale(0, BigDecimal.ROUND_DOWN)
        if self.MIST.compareTo(self.DIFF) == 1:
            self.ST = self.MIST
        else:
            self.ST = self.DIFF

    def MSOLZ(self):
        """
        Solidaritätszuschlag, PAP Seite 31
        """
        self.SOLZFREI = self.SOLZFREI.multiply(BigDecimal.valueOf(self.KZTAB))
        if self.JBMG.compareTo(self.SOLZFREI) == 1:
            self.SOLZJ = self.JBMG.multiply(BigDecimal.valueOf(5.5)).divide(Lohnsteuer.ZAHL100).setScale(2, BigDecimal.ROUND_DOWN)
            self.SOLZMIN = self.JBMG.subtract(self.SOLZFREI).multiply(BigDecimal.valueOf(11.9)).divide(Lohnsteuer.ZAHL100).setScale(2, BigDecimal.ROUND_DOWN)
            if self.SOLZMIN.compareTo(self.SOLZJ) == -1:
                self.SOLZJ = self.SOLZMIN
            self.JW = self.SOLZJ.multiply(Lohnsteuer.ZAHL100).setScale(0, BigDecimal.ROUND_DOWN)
            self.UPANTEIL()
            self.SOLZLZZ = self.ANTEIL1
        else:
            self.SOLZLZZ = BigDecimal.ZERO
        if self.R > 0:
            self.JW = self.JBMG.multiply(Lohnsteuer.ZAHL100)
            self.UPANTEIL()
            self.BK = self.ANTEIL1
        else:
            self.BK = BigDecimal.ZERO

    def UPANTEIL(self):
        """
        Anteil von Jahresbeträgen fuer einen LZZ (§ 39b Absatz 2 Satz 9 EStG), PAP Seite 32
        """
        if self.LZZ == 1:
            self.ANTEIL1 = self.JW
        else:
            if self.LZZ == 2:
                self.ANTEIL1 = self.JW.divide(Lohnsteuer.ZAHL12, 0, BigDecimal.ROUND_DOWN)
            else:
                if self.LZZ == 3:
                    self.ANTEIL1 = self.JW.multiply(Lohnsteuer.ZAHL7).divide(Lohnsteuer.ZAHL360, 0, BigDecimal.ROUND_DOWN)
                else:
                    self.ANTEIL1 = self.JW.divide(Lohnsteuer.ZAHL360, 0, BigDecimal.ROUND_DOWN)

    def MSONST(self):
        """
        Berechnung sonstiger Bezüge nach § 39b Absatz 3 Sätze 1 bis 8 EStG, PAP Seite 33
        """
        self.LZZ = 1
        if self.ZMVB == 0:
            self.ZMVB = 12
        if self.SONSTB.compareTo(BigDecimal.ZERO) == 0 and self.MBV.compareTo(BigDecimal.ZERO) == 0:
            self.LSTSO = BigDecimal.ZERO
            self.STS = BigDecimal.ZERO
            self.SOLZS = BigDecimal.ZERO
            self.BKS = BigDecimal.ZERO
        else:
            self.MOSONST()
            self.ZRE4J = self.JRE4.add(self.SONSTB).divide(Lohnsteuer.ZAHL100).setScale(2, BigDecimal.ROUND_DOWN)
            self.ZVBEZJ = self.JVBEZ.add(self.VBS).divide(Lohnsteuer.ZAHL100).setScale(2, BigDecimal.ROUND_DOWN)
            self.VBEZBSO = self.STERBE
            self.MRE4SONST()
            self.MLSTJAHR()
            self.WVFRBM = self.ZVE.subtract(self.GFB).multiply(Lohnsteuer.ZAHL100).setScale(2, BigDecimal.ROUND_DOWN)
            if self.WVFRBM.compareTo(BigDecimal.ZERO) == -1:
                self.WVFRBM = BigDecimal.ZERO
            self.LSTSO = self.ST.multiply(Lohnsteuer.ZAHL100)
            self.STS = self.LSTSO.subtract(self.LSTOSO).multiply(BigDecimal.valueOf(self.f)).divide(Lohnsteuer.ZAHL100, 0, BigDecimal.ROUND_DOWN).multiply(Lohnsteuer.ZAHL100)
            self.STSMIN()

    def STSMIN(self):
        """
        PAP Seite 34
        """
        if self.STS.compareTo(BigDecimal.ZERO) == -1:
            if self.MBV.compareTo(BigDecimal.ZERO) == 0:
                pass
            else:
                self.LSTLZZ = self.LSTLZZ.add(self.STS)
                if self.LSTLZZ.compareTo(BigDecimal.ZERO) == -1:
                    self.LSTLZZ = BigDecimal.ZERO
                self.SOLZLZZ = self.SOLZLZZ.add(self.STS.multiply(BigDecimal.valueOf(5.5).divide(Lohnsteuer.ZAHL100))).setScale(0, BigDecimal.ROUND_DOWN)
                if self.SOLZLZZ.compareTo(BigDecimal.ZERO) == -1:
                    self.SOLZLZZ = BigDecimal.ZERO
                self.BK = self.BK.add(self.STS)
                if self.BK.compareTo(BigDecimal.ZERO) == -1:
                    self.BK = BigDecimal.ZERO
            self.STS = BigDecimal.ZERO
            self.SOLZS = BigDecimal.ZERO
        else:
            self.MSOLZSTS()
        if self.R > 0:
            self.BKS = self.STS
        else:
            self.BKS = BigDecimal.ZERO

    def MSOLZSTS(self):
        """
        Berechnung des SolZ auf sonstige Bezüge, PAP Seite 35
        """
        if self.ZKF.compareTo(BigDecimal.ZERO) == 1:
            self.SOLZSZVE = self.ZVE.subtract(self.KFB)
        else:
            self.SOLZSZVE = self.ZVE
        if self.SOLZSZVE.compareTo(BigDecimal.ONE) == -1:
            self.SOLZSZVE = BigDecimal.ZERO
            self.X = BigDecimal.ZERO
        else:
            self.X = self.SOLZSZVE.divide(BigDecimal.valueOf(self.KZTAB), 0, BigDecimal.ROUND_DOWN)
        if self.STKL < 5:
            self.UPTAB26()
        else:
            self.MST5_6()
        self.SOLZSBMG = self.ST.multiply(BigDecimal.valueOf(self.f)).setScale(0, BigDecimal.ROUND_DOWN)
        if self.SOLZSBMG.compareTo(self.SOLZFREI) == 1:
            self.SOLZS = self.STS.multiply(BigDecimal.valueOf(5.5)).divide(Lohnsteuer.ZAHL100, 0, BigDecimal.ROUND_DOWN)
        else:
            self.SOLZS = BigDecimal.ZERO

    def MOSONST(self):
        """
        Sonderberechnung ohne sonstige Bezüge für Berechnung bei sonstigen Bezügen, PAP Seite 36
        """
        self.ZRE4J = self.JRE4.divide(Lohnsteuer.ZAHL100).setScale(2, BigDecimal.ROUND_DOWN)
        self.ZVBEZJ = self.JVBEZ.divide(Lohnsteuer.ZAHL100).setScale(2, BigDecimal.ROUND_DOWN)
        self.JLFREIB = self.JFREIB.divide(Lohnsteuer.ZAHL100, 2, BigDecimal.ROUND_DOWN)
        self.JLHINZU = self.JHINZU.divide(Lohnsteuer.ZAHL100, 2, BigDecimal.ROUND_DOWN)
        self.MRE4()
        self.MRE4ABZ()
        self.ZRE4VP = self.ZRE4VP.subtract(self.JRE4ENT.divide(Lohnsteuer.ZAHL100))
        self.MZTABFB()
        self.VFRBS1 = self.ANP.add(self.FVB.add(self.FVBZ)).multiply(Lohnsteuer.ZAHL100).setScale(2, BigDecimal.ROUND_DOWN)
        self.MLSTJAHR()
        self.WVFRBO = self.ZVE.subtract(self.GFB).multiply(Lohnsteuer.ZAHL100).setScale(2, BigDecimal.ROUND_DOWN)
        if self.WVFRBO.compareTo(BigDecimal.ZERO) == -1:
            self.WVFRBO = BigDecimal.ZERO
        self.LSTOSO = self.ST.multiply(Lohnsteuer.ZAHL100)

    def MRE4SONST(self):
        """
        Sonderberechnung mit sonstigen Bezüge für Berechnung bei sonstigen Bezügen, PAP Seite 37
        """
        self.MRE4()
        self.FVB = self.FVBSO
        self.MRE4ABZ()
        self.ZRE4VP = self.ZRE4VP.add(self.MBV.divide(Lohnsteuer.ZAHL100)).subtract(self.JRE4ENT.divide(Lohnsteuer.ZAHL100)).subtract(self.SONSTENT.divide(Lohnsteuer.ZAHL100))
        self.FVBZ = self.FVBZSO
        self.MZTABFB()
        self.VFRBS2 = self.ANP.add(self.FVB).add(self.FVBZ).multiply(Lohnsteuer.ZAHL100).subtract(self.VFRBS1)

    def UPTAB26(self):
        """
        Tarifliche Einkommensteuer §32a EStG, PAP Seite 38
        """
        if self.X.compareTo(self.GFB.add(Lohnsteuer.ZAHL1)) == -1:
            self.ST = BigDecimal.ZERO
        else:
            if self.X.compareTo(BigDecimal.valueOf(17800)) == -1:
                self.Y = self.X.subtract(self.GFB).divide(Lohnsteuer.ZAHL10000, 6, BigDecimal.ROUND_DOWN)
                self.RW = self.Y.multiply(BigDecimal.valueOf(914.51))
                self.RW = self.RW.add(BigDecimal.valueOf(1400))
                self.ST = self.RW.multiply(self.Y).setScale(0, BigDecimal.ROUND_DOWN)
            else:
                if self.X.compareTo(BigDecimal.valueOf(69879)) == -1:
                    self.Y = self.X.subtract(BigDecimal.valueOf(17799)).divide(Lohnsteuer.ZAHL10000, 6, BigDecimal.ROUND_DOWN)
                    self.RW = self.Y.multiply(BigDecimal.valueOf(173.1))
                    self.RW = self.RW.add(BigDecimal.valueOf(2397))
                    self.RW = self.RW.multiply(self.Y)
                    self.ST = self.RW.add(BigDecimal.valueOf(1034.87)).setScale(0, BigDecimal.ROUND_DOWN)
                else:
                    if self.X.compareTo(BigDecimal.valueOf(277826)) == -1:
                        self.ST = self.X.multiply(BigDecimal.valueOf(0.42)).subtract(BigDecimal.valueOf(11135.63)).setScale(0, BigDecimal.ROUND_DOWN)
                    else:
                        self.ST = self.X.multiply(BigDecimal.valueOf(0.45)).subtract(BigDecimal.valueOf(19470.38)).setScale(0, BigDecimal.ROUND_DOWN)
        self.ST = self.ST.multiply(BigDecimal.valueOf(self.KZTAB))
