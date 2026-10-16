"""Independent month-by-month models shared by the forecast, target and retirement tests.

Money grows at the yearly return compounded monthly (a return below −100% counts as −100%), deposits are added at the
end of each month and rise by the deposit growth once a year."""
import math, datetime


def grow(start, monthly, rate, months, g=0, stop=math.inf):
    """Value and everything put in (today's value included) after `months`; no deposits after month `stop` (retiring)."""
    rm = max(0, 1 + rate / 100) ** (1 / 12) - 1; v = start; m = monthly; put = start
    for i in range(1, months + 1):
        dep = m if i <= stop else 0
        v = v * (1 + rm) + dep; put += dep
        if i % 12 == 0: m *= 1 + g / 100
    return v, put


def retire_age(s):
    """The retirement age as a whole number (65 when not set), rounded like the page (a half rounds up)."""
    return math.floor((s.get('retireAge') or 0) + 0.5) or 65


def save_months(s, now, month=None):
    """Months of saving left: you retire in the middle (July) of the year you reach your retirement age, counted from this
    month (0-11); none once you're past it; without a year of birth deposits go on."""
    by = s.get('birthYear') or 0
    if not (1000 <= by <= now): return math.inf
    if month is None: month = datetime.date.today().month - 1
    return max(0, (by + retire_age(s) - now) * 12 + 6 - month)


def cash_rate(s):
    """What all your cash earns a year after tax, in %: each account's interest (taxed when positive, a negative rate isn't
    a refund) over all cash, cash on hand included."""
    buf = sum(a.get('amount', 0) or 0 for a in s.get('accounts', [])) + (s.get('cashOnHand') or 0)
    ints = [(a.get('amount', 0) or 0) * (a.get('yield', 0) or 0) / 100 for a in s.get('accounts', [])]
    if buf <= 0: return 0
    return sum(i * (1 - (s.get('taxRate') or 0) / 100) if i > 0 else i for i in ints) / buf * 100


def surplus_share(s):
    """The share of the yearly surplus that's invested, in %: the share set (all of it in data from before v1.1.7, where
    it was a switch), to one decimal as the tool shows it."""
    share = s.get('projSurplusPct', 100) if s.get('enableProjSurplus') else 0
    return math.floor(share * 10 + 0.5) / 10


def surplus_invested(s, surplus):
    """The part of the yearly surplus invested each month; a negative surplus is never invested."""
    return surplus_share(s) / 100 * max(0, surplus) / 12


def savings(debts, months, s, surplus, rate, buffer, stop=math.inf, extra=0):
    """Month by month (0..months): cash, what's still owed and the invested share of paid-off loans' payments (growing at
    `rate`) with what went into it; `extra` more a month into cash while saving, a flat amount. Loans (dicts B, r monthly, P) shrink by their payments;
    one without a payment stays as it is; a paid-off loan's payment is split like the surplus (a shortfall is covered
    first) and its last payment is only what's left. Cash earns cash_rate() on what's there (nothing on a shortfall) and
    gets the part of the surplus that isn't invested, rising with deposit growth when positive. Nothing new after `stop`,
    when loan payments come out of cash."""
    rm = max(0, 1 + rate / 100) ** (1 / 12) - 1; rc = max(0, 1 + cash_rate(s) / 100) ** (1 / 12) - 1; g = (s.get('projGrowth') or 0) / 100
    S = surplus / 12; share = surplus_share(s) / 100; dep = S - surplus_invested(s, surplus)
    st = [dict(b=d['B'], paid=False) for d in debts]
    cash, owed, inv, inv_put = [buffer], [sum(d['B'] for d in debts)], [0.0], [0.0]
    for i in range(1, months + 1):
        F = paid = 0.0
        for d, x in zip(debts, st):
            if x['paid']: F += d['P']; continue
            if d['P'] <= 0: continue   # no payment entered: stays as it is
            x['b'] = x['b'] * (1 + d['r']) - d['P']; paid += d['P']
            if x['b'] <= 1e-9: x['paid'] = True; F += -x['b']; paid -= -x['b']; x['b'] = 0.0
        saving = i <= stop
        to_inv = share * (max(0, S + F) - max(0, S)) if saving else 0
        prev = cash[-1]; cash.append((prev * (1 + rc) if prev > 0 else prev) + ((dep + extra + F - to_inv) if saving else -paid))
        inv.append(inv[-1] * (1 + rm) + to_inv); inv_put.append(inv_put[-1] + to_inv)
        owed.append(sum(max(0, x['b']) for x in st))
        if i % 12 == 0 and dep > 0: dep *= 1 + g
    return cash, owed, inv, inv_put


def by_month(start, monthly, rate, months, g=0, stop=math.inf):
    """Value and everything put in (today's value included), month by month (0..months)."""
    rm = max(0, 1 + rate / 100) ** (1 / 12) - 1; v = start; m = monthly; put = start; vs, ps = [v], [put]
    for i in range(1, months + 1):
        dep = m if i <= stop else 0
        v = v * (1 + rm) + dep; put += dep; vs.append(v); ps.append(put)
        if i % 12 == 0: m *= 1 + g / 100
    return vs, ps


def life_left(age):
    """Remaining life expectancy: 19.3 years at 65 (Statistics Estonia, 2025), 0.8 less per year older, at least 1."""
    return max(1, 19.3 - 0.8 * (age - 65))


PENSION_AGE_KNOWN = [(1961, 65), (1962, 65 + 1/12), (1963, 65 + 3/12), (1964, 65 + 4/12)]   # Social Insurance Board, by year of birth


def auto_pension_age(s):
    """The general state pension age by year of birth (the latest known one, 65y4m, for later years or none)."""
    by = s.get('birthYear') or 0
    return next((a for y, a in PENSION_AGE_KNOWN if by and by <= y), PENSION_AGE_KNOWN[-1][1])


def pension_age(s):
    """State pension age: your own setting, else the general one by year of birth."""
    if (s.get('pensionAgeYears') or 0) > 0: return s['pensionAgeYears'] + (s.get('pensionAgeMonths') or 0) / 12
    return auto_pension_age(s)


def pensioner(s, now):
    """Of pension age this year, for the tax rules: from the general age (an earlier pension of your own doesn't count)."""
    by = s.get('birthYear') or 0
    return bool(by) and by <= now and by + math.floor(max(pension_age(s), auto_pension_age(s))) <= now


def months(age):
    """An age in whole months (ages here are years plus whole months, so this is exact; 65y5m isn't as a decimal)."""
    return round(age * 12)


def age_now(s, today=None):
    """Your age today, your birthday taken as mid-year (1 July): born 1990, on 16 October 2026 that's 36 years 3 months."""
    by = s.get('birthYear') or 0; today = today or datetime.date.today()
    return today.year - by + (today.month - 1 - 6) / 12 if by else 0


def payout_age(s, today=None):
    """When pension fund payouts start, in whole months: at retirement, but not before 5 years before pension age, nor before now."""
    return max(retire_age(s) * 12, months(pension_age(s)) - 60, months(age_now(s, today))) / 12


I_BASE, I_YEAR, I_AVG_PAY, I_MIN_PAY = 399.24, 10.477, 5092.70 / 0.2, 886 * 12   # 2026: base part, a year's value, average and minimum pay a year


def state_pension(s, a_sal, now=None):
    """State pension a month in today's money: your own forecast, else estimated from a year's salary-like pay (`a_sal`): the
    base part plus a year's value for each year from 20 until retirement, each year worth half your pay against the average and
    half a solidarity share (1 from 12 minimum months of pay up), times 0.8 in the II pillar; else (no pay, or already of
    pension age, when today's pay doesn't show what was earned) the average."""
    if (s.get('statePension') or 0) > 0: return s['statePension']
    if a_sal <= 0 or pensioner(s, now or datetime.date.today().year): return 860
    unit = (0.8 if s.get('enableP2') else 1) * (min(1, a_sal / I_MIN_PAY) + a_sal / I_AVG_PAY) / 2
    return I_BASE + I_YEAR * unit * max(0, retire_age(s) - 20)


def payout_tax(age, payout_years, tax_rate, spa=65):
    """Tax % on pension fund payouts starting at `age`: income tax more than 5 years before pension age `spa`, else
    none when spread over at least the remaining life expectancy and 10% when shorter."""
    if months(age) < months(spa) - 60: return tax_rate
    return 10 if payout_years < life_left(age) - 1e-9 else 0
