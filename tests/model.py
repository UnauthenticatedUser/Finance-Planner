"""Independent month-by-month models shared by the forecast, target and retirement tests.

Money grows at the yearly return compounded monthly (a return below −100% counts as −100%), deposits are added at the
end of each month and rise by the deposit growth once a year."""
import math


def grow(start, monthly, rate, months, g=0):
    """Value and everything put in (today's value included) after `months`."""
    rm = max(0, 1 + rate / 100) ** (1 / 12) - 1; v = start; m = monthly; put = start
    for i in range(1, months + 1):
        v = v * (1 + rm) + m; put += m
        if i % 12 == 0: m *= 1 + g / 100
    return v, put


def months_to(start, monthly, rate, g, reached, cap=720):
    """First month in which reached(month, value) holds, or infinity within `cap` months."""
    rm = max(0, 1 + rate / 100) ** (1 / 12) - 1; v = start; m = monthly
    if reached(0, v): return 0
    for i in range(1, cap + 1):
        v = v * (1 + rm) + m
        if reached(i, v): return i
        if i % 12 == 0: m *= 1 + g / 100
    return math.inf


def life_left(age):
    """Remaining life expectancy: 19.3 years at 65 (Statistics Estonia, 2025), 0.8 less per year older, at least 1."""
    return max(1, 19.3 - 0.8 * (age - 65))


def payout_tax(age, payout_years, tax_rate):
    """Tax % on pension fund payouts starting at `age`: income tax more than 5 years before pension age (65), else none
    when spread over at least the remaining life expectancy and 10% when shorter."""
    if age < 60: return tax_rate
    return 10 if payout_years < life_left(age) - 1e-9 else 0
