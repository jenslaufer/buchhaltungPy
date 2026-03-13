"""Chi-squared survival function without scipy dependency."""

import math


def _gamma_inc_lower_series(a: float, x: float) -> float:
    """Lower regularized incomplete gamma P(a,x) via series expansion.

    Works well when x < a + 1.
    """
    if x <= 0:
        return 0.0

    s = 1.0 / a
    term = 1.0 / a
    for n in range(1, 500):
        term *= x / (a + n)
        s += term
        if abs(term) < 1e-14 * abs(s):
            break

    log_val = -x + a * math.log(x) - math.lgamma(a)
    if log_val < -700:
        return 0.0
    return math.exp(log_val) * s


def _gamma_inc_upper_cf(a: float, x: float) -> float:
    """Upper regularized incomplete gamma Q(a,x) via continued fraction.

    Works well when x >= a + 1.
    Uses the Legendre continued fraction representation.
    """
    # Q(a,x) = exp(-x) * x^a / Gamma(a) * CF
    # CF = 1/(x+1-a+ K(n*(a-n), x+2n+1-a))
    # Using modified Lentz method

    b0 = x + 1.0 - a
    if abs(b0) < 1e-30:
        b0 = 1e-30

    f = 1.0 / b0
    c = 1.0 / 1e-30
    d = 1.0 / b0

    for n in range(1, 500):
        an = -n * (n - a)
        bn = x + 2.0 * n + 1.0 - a
        d = bn + an * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = bn + an / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        delta = c * d
        f *= delta
        if abs(delta - 1.0) < 1e-14:
            break

    log_val = -x + a * math.log(x) - math.lgamma(a)
    if log_val < -700:
        return 0.0
    return math.exp(log_val) * f


def chi2_sf(x: float, df: int) -> float:
    """Survival function (1 - CDF) for chi-squared distribution.

    Q(df/2, x/2) where Q is the upper regularized incomplete gamma.
    """
    if x <= 0:
        return 1.0
    a = df / 2.0
    z = x / 2.0
    if z >= a + 1:
        return _gamma_inc_upper_cf(a, z)
    return 1.0 - _gamma_inc_lower_series(a, z)
