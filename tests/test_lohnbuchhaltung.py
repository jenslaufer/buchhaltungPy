"""Tests for payroll accounting (Lohnbuchhaltung)."""

from datetime import date

import polars as pl
import pytest

from src.lohnbuchhaltung import (
    Firma,
    Lohnabrechnung,
    Mitarbeiter,
    SVSaetze,
    berechne_lohnabrechnung,
    berechne_lohnsteuer,
    berechne_minijob_ag,
    berechne_sv_ag,
    berechne_sv_an,
    erzeuge_buchungssaetze,
    lohnzettel,
)


# ---------------------------------------------------------------------------
# Lohnsteuer via BMF calculator
# ---------------------------------------------------------------------------

class TestLohnsteuer:
    def test_steuerklasse_1_basic(self):
        result = berechne_lohnsteuer(3500, steuerklasse=1, krv=2, pkv=1, jahr=2024)
        assert result["lohnsteuer"] > 0
        assert result["soli"] >= 0
        assert result["gesamt"] == round(result["lohnsteuer"] + result["soli"] + result["kirchensteuer"], 2)

    def test_steuerklasse_1_high_income(self):
        low = berechne_lohnsteuer(3500, steuerklasse=1, krv=2, pkv=1, jahr=2024)
        high = berechne_lohnsteuer(10000, steuerklasse=1, krv=2, pkv=1, jahr=2024)
        assert high["lohnsteuer"] > low["lohnsteuer"]

    def test_kirchensteuer(self):
        result = berechne_lohnsteuer(5000, steuerklasse=1, kirchensteuer_satz=0.09, krv=2, pkv=1, jahr=2024)
        assert result["kirchensteuer"] == round(result["lohnsteuer"] * 0.09, 2)

    def test_zero_income(self):
        result = berechne_lohnsteuer(0, steuerklasse=1, krv=2, pkv=1, jahr=2024)
        assert result["lohnsteuer"] == 0
        assert result["soli"] == 0

    def test_invalid_year_raises(self):
        with pytest.raises(ValueError, match="2020"):
            berechne_lohnsteuer(3500, jahr=2020)

    @pytest.mark.parametrize("jahr", [2023, 2024, 2025, 2026])
    def test_all_years_produce_tax(self, jahr):
        result = berechne_lohnsteuer(3500, steuerklasse=1, krv=2, pkv=1, jahr=jahr)
        assert result["lohnsteuer"] > 0
        assert result["gesamt"] == round(result["lohnsteuer"] + result["soli"] + result["kirchensteuer"], 2)

    @pytest.mark.parametrize("jahr", [2023, 2024, 2025, 2026])
    def test_all_years_higher_income_more_tax(self, jahr):
        low = berechne_lohnsteuer(2000, steuerklasse=1, krv=2, pkv=1, jahr=jahr)
        high = berechne_lohnsteuer(8000, steuerklasse=1, krv=2, pkv=1, jahr=jahr)
        assert high["lohnsteuer"] > low["lohnsteuer"]

    @pytest.mark.parametrize("jahr", [2025, 2026])
    def test_new_pap_zero_income(self, jahr):
        result = berechne_lohnsteuer(0, steuerklasse=1, krv=2, pkv=1, jahr=jahr)
        assert result["lohnsteuer"] == 0
        assert result["soli"] == 0

    @pytest.mark.parametrize("jahr", [2025, 2026])
    def test_new_pap_kirchensteuer(self, jahr):
        result = berechne_lohnsteuer(5000, steuerklasse=1, kirchensteuer_satz=0.09, krv=2, pkv=1, jahr=jahr)
        assert result["kirchensteuer"] == round(result["lohnsteuer"] * 0.09, 2)

    @pytest.mark.parametrize("jahr", [2025, 2026])
    def test_new_pap_gesetzlich_versichert(self, jahr):
        result = berechne_lohnsteuer(4000, steuerklasse=1, krv=0, pkv=0, jahr=jahr)
        assert result["lohnsteuer"] > 0

    @pytest.mark.parametrize("jahr", [2025, 2026])
    def test_new_pap_lohnabrechnung_gf(self, jahr):
        gf = Mitarbeiter(name="Test GF", brutto_monat=8000, krankenversicherung="privat", krv=2)
        abr = berechne_lohnabrechnung(gf, date(jahr, 6, 1))
        assert abr.netto < abr.brutto
        assert abr.lohnsteuer > 0
        assert abr.sv_an == 0.0

    @pytest.mark.parametrize("jahr", [2025, 2026])
    def test_new_pap_lohnabrechnung_angestellter(self, jahr):
        ma = Mitarbeiter(name="Test AN", brutto_monat=4000, krankenversicherung="gesetzlich", krv=0)
        abr = berechne_lohnabrechnung(ma, date(jahr, 1, 1))
        assert abr.sv_an > 0
        assert abr.sv_ag > 0
        assert abr.netto < abr.brutto


# ---------------------------------------------------------------------------
# Sozialversicherung
# ---------------------------------------------------------------------------

class TestSV:
    def test_sv_ag_positive(self):
        result = berechne_sv_ag(4000)
        assert result["gesamt"] > 0
        assert result["kv"] > 0
        assert result["rv"] > 0
        assert result["av"] > 0
        assert result["pv"] > 0
        assert result["insolvenz"] > 0

    def test_sv_an_positive(self):
        result = berechne_sv_an(4000)
        assert result["gesamt"] > 0

    def test_sv_an_kinderlos_higher(self):
        normal = berechne_sv_an(4000, kinderlos=False)
        kinderlos = berechne_sv_an(4000, kinderlos=True)
        assert kinderlos["pv"] > normal["pv"]
        assert kinderlos["gesamt"] > normal["gesamt"]

    def test_sv_ag_components_sum(self):
        result = berechne_sv_ag(4000)
        expected = round(result["kv"] + result["rv"] + result["av"] + result["pv"] + result["insolvenz"], 2)
        assert result["gesamt"] == expected

    def test_sv_an_components_sum(self):
        result = berechne_sv_an(4000)
        expected = round(result["kv"] + result["rv"] + result["av"] + result["pv"], 2)
        assert result["gesamt"] == expected


# ---------------------------------------------------------------------------
# Minijob
# ---------------------------------------------------------------------------

class TestMinijob:
    def test_minijob_ag_costs(self):
        result = berechne_minijob_ag(520)
        assert result["pauschale_kv"] == round(520 * 0.13, 2)
        assert result["pauschale_rv"] == round(520 * 0.15, 2)
        assert result["pauschale_steuer"] == round(520 * 0.02, 2)
        assert result["gesamt"] > 0

    def test_minijob_ag_components_sum(self):
        result = berechne_minijob_ag(520)
        expected = round(
            result["pauschale_kv"] + result["pauschale_rv"] + result["pauschale_steuer"]
            + result["umlage_u1"] + result["umlage_u2"] + result["insolvenz"],
            2,
        )
        assert result["gesamt"] == expected


# ---------------------------------------------------------------------------
# Lohnabrechnung (full payslip)
# ---------------------------------------------------------------------------

class TestLohnabrechnung:
    @pytest.fixture
    def gf(self):
        """GmbH-Geschaeftsfuehrer with private health insurance."""
        return Mitarbeiter(
            name="Max Mustermann",
            brutto_monat=8000,
            steuerklasse=1,
            krankenversicherung="privat",
            krv=2,
            konto_gehalt="6024",
        )

    @pytest.fixture
    def minijobber(self):
        return Mitarbeiter(
            name="Mini Jobber",
            brutto_monat=520,
            minijob=True,
            konto_gehalt="6035",
        )

    @pytest.fixture
    def angestellter(self):
        """Regular employee with statutory insurance."""
        return Mitarbeiter(
            name="Anna Angestellt",
            brutto_monat=4000,
            steuerklasse=1,
            krankenversicherung="gesetzlich",
            krv=0,
            konto_gehalt="6024",
        )

    def test_gf_no_sv(self, gf):
        result = berechne_lohnabrechnung(gf, date(2024, 1, 1))
        assert result.sv_an == 0.0
        assert result.sv_ag == 0.0
        assert result.netto == round(result.brutto - result.lohnsteuer - result.soli - result.kirchensteuer, 2)

    def test_gf_netto_less_than_brutto(self, gf):
        result = berechne_lohnabrechnung(gf, date(2024, 1, 1))
        assert result.netto < result.brutto

    def test_gf_ag_kosten_equals_brutto(self, gf):
        result = berechne_lohnabrechnung(gf, date(2024, 1, 1))
        assert result.ag_kosten == result.brutto  # no AG SV for private GF

    def test_minijob_netto_equals_brutto(self, minijobber):
        result = berechne_lohnabrechnung(minijobber, date(2024, 1, 1))
        assert result.netto == result.brutto
        assert result.lohnsteuer == 0.0
        assert result.sv_an == 0.0
        assert result.sv_ag > 0

    def test_minijob_ag_kosten(self, minijobber):
        result = berechne_lohnabrechnung(minijobber, date(2024, 1, 1))
        assert result.ag_kosten > result.brutto

    def test_angestellter_has_sv(self, angestellter):
        result = berechne_lohnabrechnung(angestellter, date(2024, 1, 1))
        assert result.sv_an > 0
        assert result.sv_ag > 0
        assert result.netto < result.brutto

    def test_angestellter_netto_correct(self, angestellter):
        result = berechne_lohnabrechnung(angestellter, date(2024, 1, 1))
        expected_netto = round(result.brutto - result.lohnsteuer - result.soli - result.kirchensteuer - result.sv_an, 2)
        assert result.netto == expected_netto

    def test_monat_format(self, gf):
        result = berechne_lohnabrechnung(gf, date(2024, 3, 1))
        assert result.monat == "03.2024"

    def test_to_dict(self, gf):
        result = berechne_lohnabrechnung(gf, date(2024, 1, 1))
        d = result.to_dict()
        assert d["Mitarbeiter"] == "Max Mustermann"
        assert d["Brutto"] == 8000
        assert "Netto" in d


# ---------------------------------------------------------------------------
# Journal entries (Buchungssaetze)
# ---------------------------------------------------------------------------

class TestBuchungssaetze:
    @pytest.fixture
    def gf_abrechnung(self):
        gf = Mitarbeiter(
            name="Max Mustermann",
            brutto_monat=8000,
            steuerklasse=1,
            krankenversicherung="privat",
            krv=2,
        )
        return berechne_lohnabrechnung(gf, date(2024, 1, 1))

    @pytest.fixture
    def angestellter_abrechnung(self):
        ma = Mitarbeiter(
            name="Anna Angestellt",
            brutto_monat=4000,
            steuerklasse=1,
            krankenversicherung="gesetzlich",
            krv=0,
        )
        return berechne_lohnabrechnung(ma, date(2024, 1, 1))

    @pytest.fixture
    def minijob_abrechnung(self):
        mj = Mitarbeiter(
            name="Mini Jobber",
            brutto_monat=520,
            minijob=True,
        )
        return berechne_lohnabrechnung(mj, date(2024, 1, 1))

    def test_gf_entries_balanced(self, gf_abrechnung):
        df = erzeuge_buchungssaetze(gf_abrechnung, date(2024, 1, 1))
        soll = df.filter(pl.col("Typ") == "Soll")["Betrag"].sum()
        haben = df.filter(pl.col("Typ") == "Haben")["Betrag"].sum()
        assert abs(soll - haben) < 0.01

    def test_gf_no_sv_entries(self, gf_abrechnung):
        df = erzeuge_buchungssaetze(gf_abrechnung, date(2024, 1, 1))
        assert df.filter(pl.col("Konto") == "6110").height == 0

    def test_gf_has_gehalt_and_steuer(self, gf_abrechnung):
        df = erzeuge_buchungssaetze(gf_abrechnung, date(2024, 1, 1))
        assert df.filter(pl.col("Konto") == "6024").height > 0
        assert df.filter(pl.col("Konto") == "3730").height > 0

    def test_angestellter_entries_balanced(self, angestellter_abrechnung):
        df = erzeuge_buchungssaetze(angestellter_abrechnung, date(2024, 1, 1))
        soll = df.filter(pl.col("Typ") == "Soll")["Betrag"].sum()
        haben = df.filter(pl.col("Typ") == "Haben")["Betrag"].sum()
        assert abs(soll - haben) < 0.01

    def test_angestellter_has_sv_entries(self, angestellter_abrechnung):
        df = erzeuge_buchungssaetze(angestellter_abrechnung, date(2024, 1, 1))
        assert df.filter(pl.col("Konto") == "6110").height > 0

    def test_minijob_entries_balanced(self, minijob_abrechnung):
        df = erzeuge_buchungssaetze(minijob_abrechnung, date(2024, 1, 1))
        soll = df.filter(pl.col("Typ") == "Soll")["Betrag"].sum()
        haben = df.filter(pl.col("Typ") == "Haben")["Betrag"].sum()
        assert abs(soll - haben) < 0.01

    def test_datum_last_day_of_month(self, gf_abrechnung):
        df = erzeuge_buchungssaetze(gf_abrechnung, date(2024, 1, 1))
        assert df["Belegdatum"][0] == "31.01.2024"

    def test_february_last_day(self):
        gf = Mitarbeiter(name="Test", brutto_monat=5000, krankenversicherung="privat", krv=2)
        abr = berechne_lohnabrechnung(gf, date(2024, 2, 1))
        df = erzeuge_buchungssaetze(abr, date(2024, 2, 1))
        assert df["Belegdatum"][0] == "29.02.2024"

    def test_columns_present(self, gf_abrechnung):
        df = erzeuge_buchungssaetze(gf_abrechnung, date(2024, 1, 1))
        expected_cols = {"Belegnummer", "Belegdatum", "Buchungsdatum", "Buchungstext", "Konto", "Typ", "Betrag"}
        assert set(df.columns) == expected_cols

    def test_belegnummer_format(self, gf_abrechnung):
        df = erzeuge_buchungssaetze(gf_abrechnung, date(2024, 3, 1))
        assert df["Belegnummer"][0] == "GH0324"


# ---------------------------------------------------------------------------
# Lohnzettel (payslip)
# ---------------------------------------------------------------------------

class TestLohnzettel:
    @pytest.fixture
    def gf(self):
        return Mitarbeiter(
            name="Max Mustermann",
            brutto_monat=8000,
            steuerklasse=1,
            krankenversicherung="privat",
            krv=2,
            personal_nr="1",
            steuer_id="12 345 678 901",
            geburtsdatum="18.01.1970",
            eintritt="01.01.2024",
            strasse="Teststr. 1",
            plz="12345",
            ort="Teststadt",
        )

    @pytest.fixture
    def firma(self):
        return Firma(name="Test GmbH", strasse="Firmenstr. 5", plz="54321", ort="Firmenstadt")

    def test_contains_header(self, gf, firma):
        abr = berechne_lohnabrechnung(gf, date(2024, 1, 1))
        result = lohnzettel(gf, abr, firma)
        assert "Lohnabrechnung" in result
        assert "Januar 2024" in result

    def test_is_valid_html(self, gf, firma):
        abr = berechne_lohnabrechnung(gf, date(2024, 1, 1))
        result = lohnzettel(gf, abr, firma)
        assert result.startswith("<!DOCTYPE html>")
        assert "</html>" in result
        assert "<style>" in result

    def test_contains_firma(self, gf, firma):
        abr = berechne_lohnabrechnung(gf, date(2024, 1, 1))
        result = lohnzettel(gf, abr, firma)
        assert "Test GmbH" in result
        assert "Arbeitgeber" in result

    def test_contains_mitarbeiter(self, gf, firma):
        abr = berechne_lohnabrechnung(gf, date(2024, 1, 1))
        result = lohnzettel(gf, abr, firma)
        assert "Max Mustermann" in result
        assert "12 345 678 901" in result
        assert "Personal-Nr" in result
        assert "Arbeitnehmer" in result

    def test_contains_brutto_netto(self, gf, firma):
        abr = berechne_lohnabrechnung(gf, date(2024, 1, 1))
        result = lohnzettel(gf, abr, firma)
        assert "Gehalt" in result
        assert "Nettolohn" in result
        assert "8.000,00" in result

    def test_contains_lohnsteuer(self, gf, firma):
        abr = berechne_lohnabrechnung(gf, date(2024, 1, 1))
        result = lohnzettel(gf, abr, firma)
        assert "Lohnsteuer" in result

    def test_has_print_styles(self, gf, firma):
        abr = berechne_lohnabrechnung(gf, date(2024, 1, 1))
        result = lohnzettel(gf, abr, firma)
        assert "@page" in result
        assert "@media print" in result

    def test_no_kirchensteuer_when_zero(self, gf, firma):
        abr = berechne_lohnabrechnung(gf, date(2024, 1, 1))
        result = lohnzettel(gf, abr, firma)
        assert "Kirchensteuer" not in result

    def test_kirchensteuer_shown_when_nonzero(self, firma):
        ma = Mitarbeiter(
            name="Kirchlich",
            brutto_monat=5000,
            kirchensteuer_satz=0.09,
            krankenversicherung="privat",
            krv=2,
        )
        abr = berechne_lohnabrechnung(ma, date(2024, 1, 1))
        result = lohnzettel(ma, abr, firma)
        assert "Kirchensteuer" in result

    def test_no_firma_still_works(self, gf):
        abr = berechne_lohnabrechnung(gf, date(2024, 1, 1))
        result = lohnzettel(gf, abr)
        assert "Lohnabrechnung" in result
        assert "Max Mustermann" in result

    def test_different_months(self, gf, firma):
        for m, name in [(3, "Maerz"), (6, "Juni"), (12, "Dezember")]:
            abr = berechne_lohnabrechnung(gf, date(2024, m, 1))
            result = lohnzettel(gf, abr, firma)
            assert name in result

    def test_netto_highlighted(self, gf, firma):
        abr = berechne_lohnabrechnung(gf, date(2024, 1, 1))
        result = lohnzettel(gf, abr, firma)
        assert "font-weight: bold" in result

    def test_amounts_in_eur(self, gf, firma):
        abr = berechne_lohnabrechnung(gf, date(2024, 1, 1))
        result = lohnzettel(gf, abr, firma)
        assert "EUR" in result
