"""The editor: every "+ Add" button adds a row that saves, in English and Estonian, and picking "Car tax" as a spending
category sets it to once a year.
Run: python tests/test_editor.py"""
from playwright.sync_api import sync_playwright
from helpers import PAGE, finish, launch

# button id -> the list in the saved data it adds to
ADD = {'addIncome': 'incomes', 'addExp': 'expenseItems', 'addAcct': 'accounts', 'addP2Fund': 'p2funds', 'addP3Fund': 'p3funds',
       'addEtf': 'etfs', 'addInv': 'investments', 'addPhys': 'physAssets', 'addDebt': 'debts', 'addTarget': 'targets', 'addHist': 'history'}

problems = []
with sync_playwright() as p:
    b = launch(p)
    for lang, car_tax, yearly in (('en', 'Car tax', 'Once a year'), ('et', 'Automaks', 'Kord aastas')):
        pg = b.new_page(viewport={'width': 1360, 'height': 900}, reduced_motion='reduce'); errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)[:150]))
        pg.goto(PAGE); pg.evaluate("l=>{ localStorage.clear(); localStorage.setItem(KEY_UI, JSON.stringify({lang:l})); }", lang); pg.reload(); pg.wait_for_timeout(400)
        pg.evaluate("()=>{ document.querySelectorAll('.editor details').forEach(d=>d.open=true); document.querySelectorAll('.editor .seg button[data-v=\"1\"], .editor input[type=checkbox][data-toggle]').forEach(x=>{ if(x.tagName==='BUTTON') x.click(); else if(!x.checked) x.click(); }); }")
        pg.wait_for_timeout(400)
        for btn, key in ADD.items():
            before = pg.evaluate("k=>state[k].length", key)
            pg.evaluate("id=>document.getElementById(id).click()", btn); pg.wait_for_timeout(150)
            after = pg.evaluate("k=>[state[k].length, JSON.parse(localStorage.getItem(KEY))[k].length]", key)
            if after != [before + 1, before + 1]: problems.append(f'{lang}: {btn} added {after} rows to {key} (had {before})')
        # spending category suggestion: car tax defaults to once a year
        pg.locator('#exp-rows .invname').last.click(); pg.wait_for_timeout(150)
        opt = pg.locator('body > .suggest:not([hidden]) .sopt', has_text=car_tax)
        if not opt.count(): problems.append(f'{lang}: "{car_tax}" not suggested')
        else:
            opt.first.dispatch_event('mousedown'); pg.wait_for_timeout(150)
            got = pg.evaluate("()=>{ const e=state.expenseItems.at(-1); return [e.name, e.freq, [...document.querySelectorAll('#exp-rows .exfreq')].at(-1).textContent]; }")
            if got != [car_tax, 'year', yearly]: problems.append(f'{lang}: car tax pick gave {got}')
        if errs: problems.append(f'{lang}: page errors {errs[:2]}')
        pg.close()
    b.close()

finish('editor', problems, f'{len(ADD)} add buttons and the car tax default, in 2 languages: ' + ('all fine' if not problems else str(problems)))
