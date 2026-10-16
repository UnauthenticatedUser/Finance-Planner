"""Reference examples: the tool against worked examples published by Estonian authorities.

The other tests compare the tool with a Python model written from the same reading of the rules, so a misread rule
would pass them. Here every expected number comes from an official page, quoted next to it, never from our own
formulas; a few are plain arithmetic on the quoted figures (44 × 22%, 399.24 + 45 × 10.477), shown with the quote. Each example starts from the tool's defaults (a blank tool), so it also checks that those are the current
rules: 22% income tax, the EUR 700 basic exemption, 1.6% unemployment insurance and a 2% 2nd pillar.
Update these in January, together with the yearly rule check.
Run: python tests/test_reference.py"""
from playwright.sync_api import sync_playwright
from helpers import PAGE, finish, launch, shown

TSD = 'https://www.emta.ee/node/330/main_chapter/13293/pdf'   # Tax and Customs Board, "Deklaratsiooni TSD esitamine", updated 19.01.2026
P3 = 'https://www.pensionikeskus.ee/en/iii-pillar/contributions/questions-and-answers-about-the-iii-pillar-tax-refund/'
PENSIONER = 'https://sotsiaalkindlustusamet.ee/uudised/kuidas-mojutab-aprilli-pensionitous-tootava-pensionari-maksuvaba-tulu'   # 09.04.2026
PENSION_AGE = 'https://www.emta.ee/en/private-client/taxes-and-payment/tax-incentives/basic-exemption-pensionable-age'   # updated 25.11.2025
RATES = 'https://www.emta.ee/en/private-client/taxes-and-payment/declaration-income/tax-rates'
WORKING = 'https://emta.ee/eraklient/maksud-ja-tasumine/maksusoodustused/maksuvaba-tulu-vanaduspensionieas'   # updated 01.09.2026
AGE = 'https://sotsiaalkindlustusamet.ee/en/pension-and-benefits/applying-pension/retirement-age'   # updated 05.10.2026
CALC = 'https://sotsiaalkindlustusamet.ee/en/pension-and-benefits/pension-amount/pension-calculation'   # updated 06.04.2026
AVERAGE = "Social Ministry, explanatory memo to the regulation on the 2026 provisional average, 07.10.2025"
FICHE = 'https://economy-finance.ec.europa.eu/document/download/67de7ae2-37bd-482a-a691-1cbc525b0733_en?filename=2024-ageing-report-country-fiche-Estonia.pdf'

# (what is checked, changes from a blank tool, the tool's value, expected, source, the source's words)
CASES = [
    # Take-home pay: the TSD guide's payslips. Gross pay a month in, net pay out, to the cent.
    ('net pay, €2,100 gross', {'gross': 2100}, 'net', 1733.03, TSD,
     'Näide 1: "Kinnipeetud tulumaks (2100 – 42 – 33,60 – 700) x 22% = 291,37 eurot" … "töötasu netosummas, mis on 1733,03 eurot"'),
    ('net pay, €2,200 gross', {'gross': 2200}, 'net', 1808.22, TSD,
     'Näide 6: "Kinnipeetud tulumaks (2200 – 44 – 35,20 – 700) x 22% = 312,58 eurot" … "netosummas, mis on 1808,22 eurot"'),
    ('net pay below the basic exemption, €600 gross', {'gross': 600}, 'net', 578.40, TSD,
     'Näide 3: "Kinnipeetud tulumaks (600 – 12 – 9,60 – 578,40) x 22% = 0 eurot" … "netosummas, mis on 578,40 eurot (600 – 12 – 9,60)"'),
    ('net pay without a 2nd pillar, €1,600 gross', {'gross': 1600, 'enableP2': False}, 'net', 1382.03, TSD,
     'Näide 12: "Tulumaks töötasult (1600 – 25,60 – 700) x 22% = 192,37 eurot" … "töötasu netosummas 1382,03 eurot"'),

    # 3rd pillar refund: the Pension Centre's example (€1,700 gross a month).
    ('3rd pillar refund limit, €1,700 gross', {'gross': 1700, 'thirdPillar': 100}, 'p3Limit', 3060, P3,
     '"15% of your annual income is 1,700 euros x 12 months x 15% = 3,060 euros."'),
    ('3rd pillar refund on €1,200 a year', {'gross': 1700, 'thirdPillar': 100}, 'taxRefund', 264, P3,
     '"On the 1,200 euros paid into the III pillar during the year, you will gain 22% x 1200 = 264 euros."'),
    ('3rd pillar refund at the full limit', {'gross': 1700, 'thirdPillar': 255}, 'taxRefund', 673.20, P3,
     '"you can gain up to 22% x 3,060 = €673.20 in total."'),
    ('3rd pillar refund limit capped at €6,000', {'gross': 5000, 'thirdPillar': 600}, 'p3Limit', 6000, P3,
     '"If 15% of gross income is more than 6,000 euros, then 6,000 euros is tax-free."'),

    # The pensioners' tax-free amount: the state pension is taxed only above €776 a month.
    ('state pension €820: taxed part', {'birthYear': 1990, 'statePension': 820}, 'stateTaxable', 44, PENSIONER,
     'Example 2: "Selles näites on tulumaksuga maksustatud 44 eurot kuus (820 – 776 = 44)."'),
    ('state pension €820: tax', {'birthYear': 1990, 'statePension': 820}, 'stateTax', 9.68, PENSIONER + ' and ' + RATES,
     'the 44 euros above, at "The rate of withheld income tax is 22%." (44 x 22% = 9.68)'),
    ('state pension €700: no tax', {'birthYear': 1990, 'statePension': 700}, 'stateTax', 0, PENSION_AGE,
     '"The Social Insurance Board will pay you the entire old-age pension of 700 euros."'),

    # A working pensioner: the €776 tax-free amount goes to the pension first, the rest (76) to the pay, and no
    # unemployment insurance is withheld. The example has no 2nd pillar.
    ('working pensioner: net pay, €1,000 gross and a €700 pension', {'birthYear': 1955, 'statePension': 700, 'gross': 1000, 'enableP2': False}, 'net', 796.72, WORKING,
     '"Tööandja arvestab teie avalduse alusel töötasule maksuvaba tulu 76 eurot (1000 – 76 = 924)" … "netotöötasu väljamakse 796,72 eurot (1000 – 203,28 = 796,72)"'),

    # State pension age by year of birth: the year someone turns 65 sets it.
    ('pension age, born 1961', {'birthYear': 1961}, 'spa', 65, AGE, '"In 2026, people born in 1961 reach retirement age — their retirement age is 65 years."'),
    ('pension age, born 1962', {'birthYear': 1962}, 'spa', 65 + 1/12, AGE, '"In 2027, the retirement age will be 65 years and 1 month."'),
    ('pension age, born 1963', {'birthYear': 1963}, 'spa', 65 + 3/12, AGE, '"In 2028, the retirement age will be 65 years and 3 month."'),
    ('pension age, born 1964', {'birthYear': 1964}, 'spa', 65 + 4/12, AGE, '"In 2029, the retirement age will be 65 years and 4 month."'),

    # The state pension estimated from pay: a year's unit, and the monthly pension it gives. €2,121.96 a month is the 2026
    # average (20% of it a year is the €5,092.70 average pension part of social tax); €886 is the 2026 minimum base.
    ('I pillar: a year at the average pay', {'gross': 2121.96, 'enableP2': False}, 'unit', 1, CALC + ' and ' + AVERAGE,
     '"The solidary component is 1.0 if social tax was paid … at least 12 times the minimum wage"; the memo: the average "5092,70 eurot", social tax on it gives an insurance component of 1.0; "(solidary component + insurance component) ÷ 2 = joint part"'),
    ('I pillar: a year at half the minimum base', {'gross': 443, 'enableP2': False}, 'unit', (0.5 + 443/2121.96)/2, CALC,
     '"If less was paid, it is reduced proportionally" (443 / 886 = 0.5), and the insurance component is 443 / 2,121.96'),
    ('I pillar: a year at the average pay in the II pillar', {'gross': 2121.96, 'enableP2': True}, 'unit', 0.8, FICHE,
     '"effective rate of the state pension insurance part of the social tax is 16%" for those who joined the second pillar, against 20% (16 / 20 = 0.8)'),
    ('I pillar: 45 years at the average pay', {'gross': 2121.96, 'enableP2': False, 'birthYear': 1990, 'retireAge': 65}, 'stateToday', 399.24 + 45 * 10.477, CALC,
     '"Starting from April 1st, 2026, the base part is 399,2400 euros." … "the yearly rate is 10,477 euros." (45 years from age 20 to 65)'),

    # Pension fund payout tax (%), by the age payouts start and how long they last, for someone whose pension age is 65.
    ('payout tax: lump sum at 66', {'birthYear': 1961, 'payoutYears': 1}, 'payout@66', 10, PENSION_AGE,
     '"one-off and partial one-off payments made at pensionable age or up to five years before reaching pensionable age" (10%)'),
    ('payout tax: lump sum at 60, five years early', {'birthYear': 1961, 'payoutYears': 1}, 'payout@60', 10, PENSION_AGE,
     'the same 10%: "up to five years before reaching pensionable age"'),
    ('payout tax: lump sum at 59, more than five years early', {'birthYear': 1961, 'payoutYears': 1}, 'payout@59', 22, PENSION_AGE,
     '"lump sum payments made before pensionable age and partial lump sum payments, on which 22% income tax is withheld."'),
    ('payout tax: over 10 years from 65', {'birthYear': 1961, 'payoutYears': 10}, 'payout@65', 10, PENSION_AGE,
     '"payments of a fixed-term pension divided by a shorter than the average life expectancy" (10%)'),
    ('payout tax: over 30 years from 65', {'birthYear': 1961, 'payoutYears': 30}, 'payout@65', 0, PENSION_AGE,
     '"regular funded pension and pension agreement payments divided by life expectancy are exempt of tax"'),
]

READ = """s=>{ state=normalize(s); refreshAll(); const c=compute(), r=retirement(c);
  const out={net:c.net, taxRefund:c.taxRefund, p3Limit:c.p3Limit, spa:statePensionAge()};
  if(r){ out.stateTaxable=r.stateGross-r.exemption; out.stateTax=r.stateTax; out.stateToday=r.stateToday; }
  out.unit=iPillarUnit(c.aSal);
  [59,60,65,66].forEach(a=>out['payout@'+a]=payoutTaxPct(a));
  return out; }"""


def main():
    fails = []
    with sync_playwright() as p:
        b = launch(p); pg = b.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)[:150]))
        pg.goto(PAGE); pg.wait_for_timeout(300)
        if not shown(pg): fails.append('the page is hidden')
        for what, changes, key, expected, source, words in CASES:
            got = pg.evaluate(READ, changes).get(key)
            ok = got is not None and abs(got - expected) < (1e-5 if key == 'unit' else 0.005 + 1e-9)   # euros to the half cent; a year's unit to 0.001% (the quoted average pay is rounded to the cent)
            print(f"  {'ok  ' if ok else 'FAIL'} {what}: {got if got is None else round(got, 4)} (expected {expected})")
            if not ok: fails.append(f'{what}\n      source: {source}\n      {words}')
        b.close()
    for f in fails: print('  ' + f)
    print('page errors:', errs[:3] or 'none')
    finish('reference', fails or errs, f'{len(CASES)} official examples, {len(CASES) - len(fails)} matched')


if __name__ == '__main__':
    main()
