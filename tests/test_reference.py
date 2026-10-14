"""Reference examples: the tool against worked examples published by Estonian authorities.

The other tests compare the tool with a Python model written from the same reading of the rules, so a misread rule
would pass them. Here every expected number comes from an official page, quoted next to it, never from our own
formulas. Each example starts from the tool's defaults (a blank tool), so it also checks that those are the current
rules: 22% income tax, the EUR 700 basic exemption, 1.6% unemployment insurance and a 2% 2nd pillar.
Update these in January, together with the yearly rule check.
Run: python tests/test_reference.py"""
from playwright.sync_api import sync_playwright
from helpers import PAGE, finish, launch

TSD = 'https://www.emta.ee/node/330/main_chapter/13293/pdf'   # Tax and Customs Board, "Deklaratsiooni TSD esitamine", updated 19.01.2026
P3 = 'https://www.pensionikeskus.ee/en/iii-pillar/contributions/questions-and-answers-about-the-iii-pillar-tax-refund/'
PENSIONER = 'https://sotsiaalkindlustusamet.ee/uudised/kuidas-mojutab-aprilli-pensionitous-tootava-pensionari-maksuvaba-tulu'   # 09.04.2026
PENSION_AGE = 'https://www.emta.ee/en/private-client/taxes-and-payment/tax-incentives/basic-exemption-pensionable-age'   # updated 25.11.2025
RATES = 'https://www.emta.ee/en/private-client/taxes-and-payment/declaration-income/tax-rates'

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

    # Pension fund payout tax (%), by the age payouts start and how long they last. Pension age is 65 in 2026.
    ('payout tax: lump sum at 66', {'payoutYears': 1}, 'payout@66', 10, PENSION_AGE,
     '"one-off and partial one-off payments made at pensionable age or up to five years before reaching pensionable age" (10%)'),
    ('payout tax: lump sum at 60, five years early', {'payoutYears': 1}, 'payout@60', 10, PENSION_AGE,
     'the same 10%: "up to five years before reaching pensionable age"'),
    ('payout tax: lump sum at 59, more than five years early', {'payoutYears': 1}, 'payout@59', 22, PENSION_AGE,
     '"lump sum payments made before pensionable age and partial lump sum payments, on which 22% income tax is withheld."'),
    ('payout tax: over 10 years from 65', {'payoutYears': 10}, 'payout@65', 10, PENSION_AGE,
     '"payments of a fixed-term pension divided by a shorter than the average life expectancy" (10%)'),
    ('payout tax: over 30 years from 65', {'payoutYears': 30}, 'payout@65', 0, PENSION_AGE,
     '"regular funded pension and pension agreement payments divided by life expectancy are exempt of tax"'),
]

READ = """s=>{ state=normalize(s); refreshAll(); const c=compute(), r=retirement(c);
  const out={net:c.net, taxRefund:c.taxRefund, p3Limit:c.p3Limit};
  if(r){ out.stateTaxable=r.stateGross-r.exemption; out.stateTax=r.stateTax; }
  [59,60,65,66].forEach(a=>out['payout@'+a]=payoutTaxPct(a));
  return out; }"""


def main():
    fails = []
    with sync_playwright() as p:
        b = launch(p); pg = b.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)[:150]))
        pg.goto(PAGE); pg.wait_for_timeout(300)
        for what, changes, key, expected, source, words in CASES:
            got = pg.evaluate(READ, changes).get(key)
            ok = got is not None and abs(got - expected) < 0.005 + 1e-9
            print(f"  {'ok  ' if ok else 'FAIL'} {what}: {got if got is None else round(got, 4)} (expected {expected})")
            if not ok: fails.append(f'{what}\n      source: {source}\n      {words}')
        b.close()
    for f in fails: print('  ' + f)
    print('page errors:', errs[:3] or 'none')
    finish('reference', fails or errs, f'{len(CASES)} official examples, {len(CASES) - len(fails)} matched')


if __name__ == '__main__':
    main()
