"""The editor: every "+ Add" button adds a row that saves, in English and Estonian, and picking "Car tax" as a spending
category sets it to once a year. Decimals work with a comma or a dot, in a setting and a list row, and stop at the field's
number of decimals (euros 2, rates 3, the surplus share 1, the year of birth none); a minus sign only at the start of fields
that can go below 0, one decimal point, and a field left with only signs shows empty. The yearly surplus slider
splits it between cash (left) and investments (right); each end's share can be typed (the other side and the slider follow),
and moving the slider shows new numbers at once (with the glow) instead of rolling them. On a phone, a card's pencil shows "Back to dashboard", which goes away once you are
back at the card, whether you tap it or scroll up yourself, and moves up above an Undo note instead of sitting under it.
Scrolling into the editor yourself shows the same pill as "Back to top", which takes you up; desktops (editor beside) get none.
A cash account's rate and interest stay together: beside a short name, or as one piece under a long one.
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
        # other income suggestions: each type starts with its usual tax (rent 17.6% after the 20% deduction, dividends tax-free,
        # a business account 20% plus the 2nd pillar rate)
        p2 = pg.evaluate("()=>state.enableP2 ? state.p2rate : 0")
        for typ, want in (('Rental income', ['custom', 17.6]), ('Dividends', ['free', 0]), ('Freelance work', ['custom', 20 + p2])):
            pg.evaluate("()=>document.getElementById('addIncome').click()"); pg.wait_for_timeout(150)
            pg.locator('#income-rows .invname').last.click(); pg.wait_for_timeout(150)
            shown = pg.evaluate("n=>t(n)", typ)
            opt = pg.locator('body > .suggest:not([hidden]) .sopt', has_text=shown)
            if not opt.count(): problems.append(f'{lang}: "{shown}" not suggested'); continue
            opt.first.dispatch_event('mousedown'); pg.wait_for_timeout(150)
            got = pg.evaluate("()=>{ const e=state.incomes.at(-1); return [e.name, e.tax, e.rate]; }")
            if got != [shown] + want: problems.append(f'{lang}: picking {typ} gave {got}')
        # decimals: a comma or a dot, in a setting and a list row
        for sel, typed, key, want in (('[data-key=projInflation]', ('2,5', '2.5'), "state.projInflation", 2.5),
                                      ('#acct-rows .acctyield', ('1,75', '1.75'), "state.accounts[0].yield", 1.75)):
            for t in typed:
                pg.fill(sel, ''); pg.locator(sel).first.fill(t); pg.wait_for_timeout(100)
                got = pg.evaluate(f"()=>[{key}, JSON.parse(localStorage.getItem(KEY))]")
                if got[0] != want: problems.append(f'{lang}: typing {t} in {sel} gave {got[0]}')
        # decimals stop where the field's do; a second point is ignored
        for sel, typed, want in (('[data-key=gross]', '3,826189648712', '3,82'), ('[data-key=projInflation]', '49.2394791862', '49.239'),
                                 ('[data-key=birthYear]', '1990.75', '1990'), ('#sr-inv-pct', '33.3333', '33.3'), ('[data-key=gross]', '1.2.3', '1.23'),
                                 ('#acct-rows .acctyield', '1,23456', '1,234'), ('[data-key=gross]', 'abc12x.3y4z5', '12.34'),
                                 ('[data-key=projInflation]', '-2,5', '-2,5'), ('[data-key=projInflation]', '2-5', '25'), ('[data-key=gross]', '-5', '5'),
                                 ('[data-key=projInflation]', '-.,-,-.,,-.,,-,,,,-', '-.'), ('#sr-inv-pct', '-.,-,-.,,-.,,-,,,,-', '.')):
            pg.locator(sel).first.fill(typed); pg.wait_for_timeout(80); got = pg.locator(sel).first.input_value()
            if got != want: problems.append(f'{lang}: typing {typed} in {sel} shows {got!r}, want {want!r}')
        pg.locator('[data-key=projInflation]').fill('-.'); pg.locator('[data-key=projInflation]').blur(); pg.wait_for_timeout(80)   # nothing but signs: empty once you leave
        if pg.locator('[data-key=projInflation]').input_value() != '': problems.append(f'{lang}: a field with only "-." keeps it after leaving')
        # the surplus slider: its value is the cash share; all the way to Cash is 0% invested (switched off), to Investments 100%
        ends = "()=>[surplusPct(), state.enableProjSurplus, document.getElementById('sr-cash-pct').value, document.getElementById('sr-inv-pct').value]"
        pg.evaluate("()=>{ const r=document.getElementById('surplusRange'); r.value=30; r.dispatchEvent(new Event('input')); }"); pg.wait_for_timeout(100)
        a = pg.evaluate(ends)
        pg.focus('#surplusRange'); pg.keyboard.press('End'); pg.wait_for_timeout(100); z = pg.evaluate(ends)
        pg.keyboard.press('Home'); pg.wait_for_timeout(100); h = pg.evaluate(ends)
        if a != [70, True, '30', '70'] or z != [0, False, '100', '0'] or h != [100, True, '0', '100']: problems.append(f'{lang}: surplus slider {a} {z} {h}')
        # typing a share: the other side and the slider follow; a comma or a dot; too much is held at 100; an emptied field counts as 0
        shares = "()=>[surplusPct(), document.getElementById('sr-cash-pct').value, document.getElementById('sr-inv-pct').value, document.getElementById('surplusRange').value]"
        for box, typed, want in (('#sr-cash-pct', '25', [75, '25', '75', '25']), ('#sr-inv-pct', '33,3', [33.3, '66.7', '33,3', '67']),
                                 ('#sr-inv-pct', '33.3', [33.3, '66.7', '33.3', '67']), ('#sr-cash-pct', '150', [0, '100', '0', '100']), ('#sr-cash-pct', '', [100, '', '100', '0'])):
            pg.fill(box, typed); pg.wait_for_timeout(120); got = pg.evaluate(shares)
            if got != want: problems.append(f'{lang}: typing {typed!r} in {box} gave {got}, want {want}')
        pg.locator('#sr-cash-pct').blur(); pg.wait_for_timeout(120)
        if pg.evaluate("document.getElementById('sr-cash-pct').value") != '0': problems.append(f'{lang}: an emptied share does not show 0 after leaving it')
        if errs: problems.append(f'{lang}: page errors {errs[:2]}')
        pg.close()
    # phone: the back pill after a card's pencil
    pg = b.new_page(viewport={'width': 390, 'height': 844}, reduced_motion='reduce'); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)[:150]))
    pg.goto(PAGE); pg.evaluate("localStorage.clear()"); pg.reload(); pg.wait_for_timeout(300)
    pg.evaluate("showExample(true)"); pg.wait_for_timeout(300)
    PILL = "()=>!document.getElementById('backpill').hidden"
    ONSCREEN = "()=>{ const r=document.querySelector('.cardedit[data-edit^=\"savings\"]').closest('.card').getBoundingClientRect(); return r.bottom>0 && r.top<innerHeight; }"
    for how in ('tap', 'scroll', 'top'):
        pg.evaluate("document.querySelector('.cardedit[data-edit^=\"savings\"]').click()"); pg.wait_for_timeout(500)
        if not pg.evaluate(PILL): problems.append(f'phone ({how}): no back pill after the pencil')
        if how == 'tap': pg.click('#backpill')
        elif how == 'top': pg.evaluate("window.scrollTo(0,0)")   # a jump straight past the card counts too
        else: pg.evaluate("()=>{ const c=document.querySelector('.cardedit[data-edit^=\"savings\"]').closest('.card'); window.scrollTo(0, window.scrollY + c.getBoundingClientRect().top - 40); }")   # scroll up to the card
        pg.wait_for_timeout(400)
        if pg.evaluate(PILL): problems.append(f'phone ({how}): back pill still showing at the card')
        if how != 'top' and not pg.evaluate(ONSCREEN): problems.append(f'phone ({how}): card not on screen')
    # scrolled into the editor yourself: "Back to top" takes you up and goes away; the pencil's pill says "Back to dashboard"
    LABEL = "()=>{ const p=document.getElementById('backpill'); return p.hidden ? null : [...p.children].find(c=>!c.hidden).textContent; }"
    pg.evaluate("window.scrollTo(0,0)"); pg.wait_for_timeout(200)
    if pg.evaluate(LABEL) is not None: problems.append('phone: a back pill shows at the top of the page')
    pg.evaluate("window.scrollTo(0, document.querySelector('.editor').getBoundingClientRect().top + scrollY + 600)"); pg.wait_for_timeout(200)
    if pg.evaluate(LABEL) != '↑ Back to top': problems.append(f'phone: in the editor the pill says {pg.evaluate(LABEL)!r}')
    pg.click('#backpill'); pg.wait_for_timeout(600)
    if pg.evaluate("[Math.round(scrollY), document.getElementById('backpill').hidden]") != [0, True]: problems.append('phone: Back to top did not take you up')
    pg.evaluate("document.querySelector('.cardedit[data-edit^=\"savings\"]').click()"); pg.wait_for_timeout(500)
    if pg.evaluate(LABEL) != '↑ Back to dashboard': problems.append(f'phone: after the pencil the pill says {pg.evaluate(LABEL)!r}')
    pg.click('#backpill'); pg.wait_for_timeout(600)
    # an Undo note while the pill shows: the pill sits above it, not under it
    pg.evaluate("document.querySelector('.cardedit[data-edit^=\"savings\"]').click()"); pg.wait_for_timeout(500)
    pg.evaluate("undoToast('Holiday', ()=>{})"); pg.wait_for_timeout(400)
    gap = pg.evaluate("()=>document.querySelector('.toast').getBoundingClientRect().top - document.getElementById('backpill').getBoundingClientRect().bottom")
    if not gap >= 4: problems.append(f'phone: back pill overlaps the Undo note ({gap}px)')
    # cash rows: the rate and interest never split across lines
    pg.evaluate("()=>{ state.accounts=[{name:'Rainy day money in a money market fund', amount:2016, yield:2.44},{name:'Short', amount:900, yield:3}]; refreshAll(); }"); pg.wait_for_timeout(300)
    rows = pg.evaluate("()=>[...document.querySelectorAll('#cash-accounts .acctrow')].map(r=>{ const t=s=>Math.round(r.querySelector(s).getBoundingClientRect().top); return [t('.a-name'), t('.a-yld'), t('.a-gain')]; })")
    if rows[0][1] != rows[0][2] or rows[0][1] - rows[0][0] < 10: problems.append(f'phone: long cash row split its rate and interest {rows[0]}')
    if max(rows[1]) - min(rows[1]) > 8: problems.append(f'phone: short cash row not on one line {rows[1]}')
    # numbers: the slider shows the new value at once with the glow; typing elsewhere still rolls them
    pg2 = b.new_page(viewport={'width': 1360, 'height': 900}); pg2.goto(PAGE); pg2.evaluate("localStorage.clear()"); pg2.reload(); pg2.wait_for_timeout(300)
    pg2.evaluate("()=>{ showExample(true); openSection('savings:surplus'); }"); pg2.wait_for_timeout(1200)
    frame = "new Promise(ok=>requestAnimationFrame(()=>ok()))"   # the slider redraws on the next frame (once per frame while dragging)
    first = pg2.evaluate("async ()=>{ const r=document.getElementById('surplusRange'), e=document.getElementById('proj-big'); r.value=0; r.dispatchEvent(new Event('input')); await "+frame+"; return [e.textContent, e.classList.contains('mtx')]; }")
    pg2.wait_for_timeout(600); settled = pg2.evaluate("document.getElementById('proj-big').textContent")
    if first[0] != settled or not first[1]: problems.append(f'slider: projection rolled or had no glow {first} -> {settled}')
    if pg2.evaluate("async ()=>{ const r=document.getElementById('surplusRange'); r.value=50; r.dispatchEvent(new Event('input')); await "+frame+"; return !!projState.raf; }"): problems.append('slider: the projection chart still animates')
    # a fast drag (many input events within one frame) redraws once, with the last value
    n = pg2.evaluate("async ()=>{ let k=0; const orig=renderCalc; renderCalc=()=>{ k++; orig(); }; const r=document.getElementById('surplusRange'); for(let v=0; v<=40; v+=2){ r.value=v; r.dispatchEvent(new Event('input')); } await "+frame+"; renderCalc=orig; return [k, surplusPct()]; }")
    if n != [1, 60]: problems.append(f'slider: a fast drag redrew {n[0]} times or kept {n[1]}% (want once, 60%)')
    pg2.evaluate("()=>{ const f=document.querySelector('[data-key=projReturn]'); f.value='3'; f.dispatchEvent(new Event('input')); }")
    rolling = pg2.evaluate("document.getElementById('proj-big').textContent"); pg2.wait_for_timeout(600); settled2 = pg2.evaluate("document.getElementById('proj-big').textContent")
    if rolling == settled2: problems.append('typing: the projection did not roll to its new value')
    pg2.evaluate("window.scrollTo(0, document.body.scrollHeight)"); pg2.wait_for_timeout(200)   # desktop: the editor is beside the cards, no pill
    if not pg2.evaluate("document.getElementById('backpill').hidden"): problems.append('desktop: a back pill showed')
    pg2.close()
    if errs: problems.append(f'phone: page errors {errs[:2]}')
    b.close()

finish('editor', problems, f'{len(ADD)} add buttons, the car tax default, decimals with a comma or a dot and the surplus slider, in 2 languages, and the back pill: ' + ('all fine' if not problems else str(problems)))
