"""Tests for tax calculations: KSt, Soli, GewSt, total steuern."""

import math

import pytest
from tests.conftest import fixture_path, DEFAULT_START, DEFAULT_ENDE, DEFAULT_HEBESATZ


# --- KSt = 15% of floor(BE) when BE > 0, else 0 ---

KST_CASES = [
    ("01_simple_profit.csv", 10000.0, round(math.floor(10000) * 0.15, 2)),
    ("02_simple_loss.csv", -15000.0, 0.0),
    ("03_multi_bookings.csv", 7000.0, round(math.floor(7000) * 0.15, 2)),
    ("04_rounding.csv", 1234.56, round(math.floor(1234.56) * 0.15, 2)),
    ("07_breakeven.csv", 0.0, 0.0),
    ("08_one_cent.csv", 0.01, 0.0),  # floor(0.01) * 0.15 = 0
    ("09_large_amount.csv", 999999.99, round(math.floor(999999.99) * 0.15, 2)),
    ("19_boundary_rounding_99.csv", 99.99, round(math.floor(99.99) * 0.15, 2)),
]


@pytest.mark.parametrize("fixture,be,expected_kst", KST_CASES, ids=[
    c[0].split(".")[0] for c in KST_CASES
])
def test_koerperschaftssteuer(api, konten, fixture, be, expected_kst):
    result = api.berechne_koerperschaftssteuer(
        fixture_path(fixture), konten, DEFAULT_START, DEFAULT_ENDE
    )
    assert abs(result - expected_kst) < 0.01, f"Expected {expected_kst}, got {result}"


# --- Soli = 5.5% of KSt ---

SOLI_CASES = [
    ("01_simple_profit.csv", round(round(math.floor(10000) * 0.15, 2) * 0.055, 2)),
    ("02_simple_loss.csv", 0.0),
    ("07_breakeven.csv", 0.0),
]


@pytest.mark.parametrize("fixture,expected_soli", SOLI_CASES, ids=[
    c[0].split(".")[0] for c in SOLI_CASES
])
def test_soli(api, konten, fixture, expected_soli):
    result = api.berechne_soli(
        fixture_path(fixture), konten, DEFAULT_START, DEFAULT_ENDE
    )
    assert abs(result - expected_soli) < 0.01, f"Expected {expected_soli}, got {result}"


# --- GewSt = floor(BE/100)*100 * hebesatz * 3.5 / 10000 ---

def calc_gewst(be: float, hebesatz: int) -> float:
    if be <= 0:
        return 0.0
    return round(math.floor(be / 100) * 100 * hebesatz * 3.5 / 10000, 2)


GEWST_CASES = [
    ("01_simple_profit.csv", DEFAULT_HEBESATZ, calc_gewst(10000, DEFAULT_HEBESATZ)),
    ("02_simple_loss.csv", DEFAULT_HEBESATZ, 0.0),
    ("03_multi_bookings.csv", DEFAULT_HEBESATZ, calc_gewst(7000, DEFAULT_HEBESATZ)),
    ("07_breakeven.csv", DEFAULT_HEBESATZ, 0.0),
    ("09_large_amount.csv", DEFAULT_HEBESATZ, calc_gewst(999999.99, DEFAULT_HEBESATZ)),
    # Hebesatz sensitivity
    ("01_simple_profit.csv", 200, calc_gewst(10000, 200)),
    ("01_simple_profit.csv", 500, calc_gewst(10000, 500)),
    ("01_simple_profit.csv", 900, calc_gewst(10000, 900)),
]


@pytest.mark.parametrize("fixture,hebesatz,expected_gwst", GEWST_CASES, ids=[
    f"{c[0].split('.')[0]}_h{c[1]}" for c in GEWST_CASES
])
def test_gewerbesteuer(api, konten, fixture, hebesatz, expected_gwst):
    result = api.berechne_gewerbesteuer(
        hebesatz, fixture_path(fixture), konten, DEFAULT_START, DEFAULT_ENDE
    )
    assert abs(result - expected_gwst) < 0.01, f"Expected {expected_gwst}, got {result}"


# --- Hebesatz linearity ---

def test_gewerbesteuer_scales_linearly(api, konten):
    gwst_200 = api.berechne_gewerbesteuer(
        200, fixture_path("01_simple_profit.csv"), konten, DEFAULT_START, DEFAULT_ENDE
    )
    gwst_500 = api.berechne_gewerbesteuer(
        500, fixture_path("01_simple_profit.csv"), konten, DEFAULT_START, DEFAULT_ENDE
    )
    assert gwst_500 > gwst_200
    assert abs(gwst_500 / gwst_200 - 500 / 200) < 0.01


# --- Total tax = KSt + Soli + GewSt ---

def test_steuern_equals_sum(api, konten):
    f = fixture_path("01_simple_profit.csv")
    kst = api.berechne_koerperschaftssteuer(f, konten, DEFAULT_START, DEFAULT_ENDE)
    soli = api.berechne_soli(f, konten, DEFAULT_START, DEFAULT_ENDE)
    gwst = api.berechne_gewerbesteuer(
        DEFAULT_HEBESATZ, f, konten, DEFAULT_START, DEFAULT_ENDE
    )
    total = api.steuern(f, konten, DEFAULT_START, DEFAULT_ENDE, DEFAULT_HEBESATZ)
    assert abs(total - (kst + soli + gwst)) < 0.01


# --- Effective tax rate plausibility ---

def test_effective_tax_rate_plausible(api, konten):
    f = fixture_path("01_simple_profit.csv")
    total = api.steuern(f, konten, DEFAULT_START, DEFAULT_ENDE, DEFAULT_HEBESATZ)
    rate = total / 10000
    assert 0.25 < rate < 0.35, f"Effective rate {rate:.1%} outside plausible range"
