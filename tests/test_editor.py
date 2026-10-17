"""The editor: every "+ Add" button adds a row that saves, in English and Estonian, and picking "Car tax" as a spending
category sets it to once a year. Decimals work with a comma or a dot, in a setting and a list row, and stop at the field's
number of decimals (euros 2, rates 3, the surplus share 1, years and ages none); a minus sign (also the tool's own "−") only at
the start of fields that can go below 0, one decimal point, and a field left with only signs shows empty. A pasted number
with thousands separators ("12,345.67", "1.234,56", "1,500" in a euro field) keeps its value. A tiny value from a file
shows as a plain number. Notes at their limit refuse more instead of emptying. With browser storage blocked the layout
button still switches. A weekly income says so in Estonian. A loan's rate can be high, an own tax rate or a
withdrawal rate can't. Undo doesn't bring a row back into a list that's full again, moving a row with the keyboard keeps
focus on it, and a tip that doesn't fit below its field goes above it. The yearly surplus slider
splits it between cash (left) and investments (right); each end's share can be typed (the other side and the slider follow),
and moving the slider shows new numbers at once (with the glow) instead of rolling them. On a phone, a card's pencil shows "Back to dashboard", which goes away once you are
back at the card, whether you tap it or scroll up yourself, and moves up above an Undo note instead of sitting under it.
Scrolling into the editor yourself shows the same pill as "Back to top", which takes you up; desktops (editor beside) get none.
A cash account's rate and interest stay together: beside a short name, or as one piece under a long one.
The example's names follow the language you switch to, and your own names stay as typed ("Gold 2y", "My {YEAR} fund").
A decimal typed into a year or age field is ignored, and a refused character leaves the cursor in place. The keyboard stays
where it was after ✎ (the part's first control), a new type, a picked suggestion or a removed row, and no suggestion list
opens by itself; a dropdown stays open when its own box is pressed and closes on a press outside, also unfocused (Safari);
the compact ☰ menu closes when Tab leaves it. An Estonian default title stays the default, a pillar block shown again while
it closes stays, a full list's "+ Add" can still be reached, switching language keeps an Undo note, and a field's help shows
with Tab (moving with the page) but not after a tap.
Run: python tests/test_editor.py"""
from playwright.sync_api import sync_playwright
from helpers import BROWSER, PAGE, finish, launch, watch_errors, fixture

# button id -> the list in the saved data it adds to
ADD = {'addIncome': 'incomes', 'addExp': 'expenseItems', 'addAcct': 'accounts', 'addP2Fund': 'p2funds', 'addP3Fund': 'p3funds',
       'addEtf': 'etfs', 'addInv': 'investments', 'addPhys': 'physAssets', 'addDebt': 'debts', 'addTarget': 'targets', 'addHist': 'history'}

problems = []
with sync_playwright() as p:
    b = launch(p)
    for lang, car_tax, yearly in (('en', 'Car tax', 'Once a year'), ('et', 'Automaks', 'Kord aastas')):
        pg = b.new_page(viewport={'width': 1360, 'height': 900}, reduced_motion='reduce'); errs = []
        watch_errors(pg, errs, n=150)
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
        # freelance work through a business account)
        for typ, want in (('Rental income', ['custom', 17.6]), ('Dividends', ['free', 0]), ('Freelance work', ['biz', 0])):
            pg.evaluate("()=>document.getElementById('addIncome').click()"); pg.wait_for_timeout(150)
            pg.locator('#income-rows .invname').last.click(); pg.wait_for_timeout(150)
            shown = pg.evaluate("n=>t(n)", typ)
            opt = pg.locator('body > .suggest:not([hidden]) .sopt', has_text=shown)
            if not opt.count(): problems.append(f'{lang}: "{shown}" not suggested'); continue
            opt.first.dispatch_event('mousedown'); pg.wait_for_timeout(150)
            got = pg.evaluate("()=>{ const e=state.incomes.at(-1); return [e.name, e.tax, e.rate]; }")
            if got != [shown] + want: problems.append(f'{lang}: picking {typ} gave {got}')
        # the example's names follow the language you switch to
        pg.evaluate("()=>document.getElementById('exampleBtn').click()"); pg.wait_for_timeout(300)
        other = 'et' if lang == 'en' else 'en'
        pg.evaluate("l=>document.querySelector('.langtabs [data-lang='+l+']').click()", other); pg.wait_for_timeout(300)
        want = {'en': 'Home loan', 'et': 'Kodulaen'}[other]
        if pg.evaluate("()=>state.debts[0].name") != want: problems.append(f'{lang}: the example kept its names after switching to {other}')
        pg.evaluate("l=>document.querySelector('.langtabs [data-lang='+l+']').click()", lang); pg.evaluate("()=>document.getElementById('exampleBtn').click()"); pg.wait_for_timeout(300)
        # decimals: a comma or a dot, in a setting and a list row
        for sel, typed, key, want in (('[data-key=projInflation]', ('2,5', '2.5'), "state.projInflation", 2.5),
                                      ('#acct-rows .acctyield', ('1,75', '1.75'), "state.accounts[0].yield", 1.75)):
            for t in typed:
                pg.fill(sel, ''); pg.locator(sel).first.fill(t); pg.wait_for_timeout(100)
                got = pg.evaluate(f"()=>{key}")
                if got != want: problems.append(f'{lang}: typing {t} in {sel} gave {got}')
        # decimals stop where the field's do; a second point is ignored; a whole-number field keeps the point and nothing after it
        for sel, typed, want in (('[data-key=gross]', '3,826189648712', '3,82'), ('[data-key=projInflation]', '49.2394791862', '49.239'),
                                 ('[data-key=birthYear]', '1990.75', '1990.'), ('[data-key=retireAge]', '65.5', '65.'), ('[data-key=payoutYears]', '20,5', '20,'), ('#sr-inv-pct', '33.3333', '33.3'), ('[data-key=gross]', '1.2.3', '1.23'),
                                 ('#acct-rows .acctyield', '1,23456', '1,234'), ('[data-key=gross]', 'abc12x.3y4z5', '12.34'),
                                 ('[data-key=projInflation]', '-2,5', '-2,5'), ('[data-key=projInflation]', '2-5', '25'), ('[data-key=gross]', '-5', '5'),
                                 ('[data-key=projInflation]', '-.,-,-.,,-.,,-,,,,-', '-.'), ('#sr-inv-pct', '-.,-,-.,,-.,,-,,,,-', '.'),
                                 ('[data-key=projInflation]', '−2,5', '-2,5'), ('[data-key=projYears]', '12.5', '12.')):   # the minus sign the tool shows; whole years
            pg.locator(sel).first.fill(typed); pg.wait_for_timeout(80); got = pg.locator(sel).first.input_value()
            if got != want: problems.append(f'{lang}: typing {typed} in {sel} shows {got!r}, want {want!r}')
        # typed key by key, a decimal in a year or age field is just ignored: 64.5 was 645, held at 120
        for sel, typed, key, want in (('[data-key=retireAge]', '64.5', 'retireAge', 64), ('[data-key=birthYear]', '1980.5', 'birthYear', 1980), ('[data-key=projYears]', '12.7', 'projYears', 12)):
            f=pg.locator(sel).first; f.fill(''); f.press_sequentially(typed); pg.wait_for_timeout(80); got=pg.evaluate(f"state.{key}"); f.blur(); pg.wait_for_timeout(80)
            if got != want or f.input_value() != str(want): problems.append(f'{lang}: typing {typed} key by key in {sel} gave {got} and shows {f.input_value()!r} after leaving, want {want}')
        # a character the field refuses leaves the cursor where it was, so the next digit lands there (1x000 then 5: 15000)
        f=pg.locator('[data-key=gross]'); f.fill('1000'); f.evaluate("e=>e.setSelectionRange(1,1)"); f.press('x'); f.press('5'); pg.wait_for_timeout(80)
        if f.input_value()!='15000': problems.append(f'{lang}: a refused character moved the cursor: {f.input_value()!r}, want 15000')
        pg.locator('[data-key=projInflation]').fill('-.'); pg.locator('[data-key=projInflation]').blur(); pg.wait_for_timeout(80)   # nothing but signs: empty once you leave
        if pg.locator('[data-key=projInflation]').input_value() != '': problems.append(f'{lang}: a field with only "-." keeps it after leaving')
        # the surplus slider: its value is the cash share; all the way to Cash is 0% invested (switched off), to Investments 100%
        ends = "()=>[surplusPct(), state.enableProjSurplus, document.getElementById('sr-cash-pct').value, document.getElementById('sr-inv-pct').value]"
        frame = lambda: pg.evaluate("new Promise(ok=>requestAnimationFrame(()=>requestAnimationFrame(()=>ok())))")   # the slider applies its value on the next frame
        pg.evaluate("()=>{ const r=document.getElementById('surplusRange'); r.value=30; r.dispatchEvent(new Event('input')); }"); frame()
        a = pg.evaluate(ends)
        pg.focus('#surplusRange'); pg.keyboard.press('End'); frame(); z = pg.evaluate(ends)
        pg.keyboard.press('Home'); frame(); h = pg.evaluate(ends)
        if a != [70, True, '30', '70'] or z != [0, False, '100', '0'] or h != [100, True, '0', '100']: problems.append(f'{lang}: surplus slider {a} {z} {h}')
        # typing a share: the other side and the slider follow; a comma or a dot; too much is held at 100; an emptied field counts as 0
        shares = "()=>[surplusPct(), document.getElementById('sr-cash-pct').value, document.getElementById('sr-inv-pct').value, document.getElementById('surplusRange').value]"
        for box, typed, want in (('#sr-cash-pct', '25', [75, '25', '75', '25']), ('#sr-inv-pct', '33,3', [33.3, '66.7', '33,3', '67']),
                                 ('#sr-inv-pct', '33.3', [33.3, '66.7', '33.3', '67']), ('#sr-cash-pct', '150', [0, '100', '0', '100']), ('#sr-cash-pct', '', [100, '', '100', '0'])):
            pg.fill(box, typed); pg.wait_for_timeout(120); got = pg.evaluate(shares)
            if got != want: problems.append(f'{lang}: typing {typed!r} in {box} gave {got}, want {want}')
        pg.locator('#sr-cash-pct').blur(); pg.wait_for_timeout(120)
        if pg.evaluate("document.getElementById('sr-cash-pct').value") != '0': problems.append(f'{lang}: an emptied share does not show 0 after leaving it')
        if pg.evaluate("[t('Gold 2y'), t('€5/mo')]") != ['Gold 2y', '€5/mo' if lang == 'en' else '€5/kuus']: problems.append(f'{lang}: a name like "Gold 2y" was changed, or a unit not translated')   # names stay as typed
        # how often an income comes, in the chosen language
        freq = pg.evaluate("()=>{ state.incomes=[{name:'Side job', amount:100, freq:'week', tax:'salary', rate:0}]; refreshAll(); return document.getElementById('y-other-rows').textContent; }")
        if (' · weekly' in freq) != (lang == 'en') or (lang == 'et' and ' · iga nädal' not in freq): problems.append(f'{lang}: a weekly income is labelled wrongly')
        if errs: problems.append(f'{lang}: page errors {errs[:2]}')
        pg.close()
    # phone: the back pill after a card's pencil
    pg = b.new_page(viewport={'width': 390, 'height': 844}, reduced_motion='reduce'); errs = []
    watch_errors(pg, errs, n=150)
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
    # "Back to dashboard" after the surplus "Change" link returns the keyboard to that link
    pg.evaluate("window.scrollTo(0,0)"); pg.click('#tile-surplus'); pg.wait_for_timeout(400); pg.focus('#sur-change'); pg.keyboard.press('Enter'); pg.wait_for_timeout(900)
    back = None
    if pg.evaluate(PILL): pg.focus('#backpill'); pg.keyboard.press('Enter'); pg.wait_for_timeout(900); back = pg.evaluate("document.activeElement.id")
    if back != 'sur-change': problems.append(f'phone: focus after Back to dashboard from the surplus Change link: {back}')
    pg.click('#tile-surplus'); pg.wait_for_timeout(300)   # closed again
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
    pg.evaluate("undoToast(()=>'Holiday', ()=>{})"); pg.wait_for_timeout(400)
    gap = pg.evaluate("()=>document.querySelector('.toast').getBoundingClientRect().top - document.getElementById('backpill').getBoundingClientRect().bottom")
    if not gap >= 4: problems.append(f'phone: back pill overlaps the Undo note ({gap}px)')
    # cash rows: the rate and interest never split across lines
    pg.evaluate("()=>{ state.accounts=[{name:'Rainy day money in a money market fund', amount:2016, yield:2.44},{name:'Short', amount:900, yield:3}]; refreshAll(); }"); pg.wait_for_timeout(300)
    rows = pg.evaluate("()=>[...document.querySelectorAll('#cash-accounts .acctrow')].map(r=>{ const t=s=>Math.round(r.querySelector(s).getBoundingClientRect().top); return [t('.a-name'), t('.a-yld'), t('.a-gain')]; })")
    if rows[0][1] != rows[0][2] or rows[0][1] - rows[0][0] < 10: problems.append(f'phone: long cash row split its rate and interest {rows[0]}')
    if max(rows[1]) - min(rows[1]) > 8: problems.append(f'phone: short cash row not on one line {rows[1]}')
    # numbers: the slider shows the new value at once with the glow; typing elsewhere still rolls them
    pg2 = b.new_page(viewport={'width': 1360, 'height': 900}); watch_errors(pg2, errs, n=150); pg2.goto(PAGE); pg2.evaluate("localStorage.clear()"); pg2.reload(); pg2.wait_for_timeout(300)
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
    # pasting a number with thousands separators: the last point is the decimal one when both kinds are there, else they group thousands
    pg2.evaluate("()=>document.querySelectorAll('.editor details').forEach(d=>d.open=true)"); pg2.wait_for_timeout(300)
    PASTE = """a=>{ const f=document.querySelector(a[0]), dt=new DataTransfer(); dt.setData('text/plain', a[1]); f.focus(); f.select();
      // Chromium and WebKit take clipboardData; Firefox ignores it and makes its own (writable) one from data and dataType
      const ev=new ClipboardEvent('paste', {clipboardData:dt, data:a[1], dataType:'text/plain', bubbles:true, cancelable:true});
      try { if(ev.clipboardData && ev.clipboardData.getData('text/plain')!==a[1]) ev.clipboardData.setData('text/plain', a[1]); } catch(e) {}
      if(ev.clipboardData?.getData('text/plain')!==a[1]) return null;   // the event doesn't carry the text: this browser can't fake a paste
      if(f.dispatchEvent(ev)) document.execCommand('insertText', false, a[1]);   // not taken over: the browser's own paste, done by hand
      return f.value; }"""
    for sel, typed, want in (('[data-key=gross]', '12,345.67', '12345.67'), ('[data-key=gross]', '1.234,56', '1234,56'), ('[data-key=gross]', '1,234,567', '1234567'),
                             ('[data-key=gross]', '12,5', '12,5'), ('[data-key=gross]', '−5', '5'), ('[data-key=gross]', '1,500', '1500'), ('[data-key=gross]', '€2,400', '2400'),
                             ('#acct-rows .acctamt', '3.200', '3200'), ('[data-key=projInflation]', '1,500', '1,500'),   # one point before 3 digits: thousands where cents can't be 3 digits
                             ('[data-key=gross]', '0,500', '0,50'), ('#sr-inv-pct', '12.500', '12.5')):   # but not after a 0, nor beyond what the field holds
        got = pg2.evaluate(PASTE, [sel, typed])
        if got is None and BROWSER != 'webkit': problems.append(f'pasting {typed!r}: {BROWSER} could not fake the paste, so it was not checked')
        elif got is not None and got != want: problems.append(f'pasting {typed!r} into {sel} gave {got!r}, want {want!r}')
    # own limits in a list: a loan's rate can be high, an own tax rate or a withdrawal rate can't; a FIRE target without one uses 4% (its field shows that)
    lim = pg2.evaluate("[clampNum(300,'rate','incomes'), clampNum(-5,'rate','incomes'), clampNum(-50,'rate','targets'), clampNum(300,'rate','debts'), normalize({targets:[{kind:'fire'}]}).targets[0].rate, document.querySelector('#tgt-rows .trate').placeholder]")
    if lim != [100, 0, 0, 300, 4, '4']: problems.append(f'list limits {lim}, want [100, 0, 0, 300, 4, "4"]')
    # Undo of a removed row once the list is full again: it doesn't come back (it would be cut on the next load), and says why
    pg2.evaluate("()=>{ state.accounts=Array.from({length:listMax('accounts')}, (_,i)=>({name:'a'+i, amount:1, yield:0})); buildList('accounts'); refreshAll(); }")
    pg2.locator('#acct-rows .iconbtn:not(.mv)').last.click(); pg2.wait_for_timeout(600); pg2.click('#addAcct'); pg2.wait_for_timeout(200); pg2.click('.toast .btn'); pg2.wait_for_timeout(200)
    full = pg2.evaluate("[state.accounts.length, listMax('accounts'), document.querySelector('.toast').classList.contains('problem')]")
    if full[0] != full[1] or not full[2]: problems.append(f'undo into a full list: {full[0]} rows of {full[1]}, said so: {full[2]}')
    # moving a row to the bottom with the keyboard keeps focus on it (on its other arrow)
    pg2.evaluate("()=>{ state.accounts=[{name:'a', amount:1, yield:0}, {name:'b', amount:2, yield:0}]; buildList('accounts'); }")
    pg2.focus('#acct-rows .mvdn'); pg2.keyboard.press('Enter'); pg2.wait_for_timeout(500)
    if pg2.evaluate("()=>{ const a=document.activeElement, rows=document.getElementById('acct-rows').children; return [state.accounts[1].name, a.classList.contains('mvup') && rows[1].contains(a)]; }") != ['a', True]: problems.append('moving a row to the bottom lost the keyboard focus')
    # a field's tip that doesn't fit below it goes above it, not over it
    tip = pg2.evaluate("()=>{ const src=document.querySelector('label[data-tip]'), top=innerHeight-40; tipAt(src, {getBoundingClientRect:()=>({left:20, top, bottom:innerHeight-8})}); const r=document.getElementById('tip').getBoundingClientRect(); hideTip(); return [r.bottom, top]; }")
    if not tip[0] <= tip[1]: problems.append(f'a tip near the bottom covers its field (ends at {tip[0]}, the field starts at {tip[1]})')
    # notes at their limit: a letter more is refused, and the notes stay (they used to be emptied, then saved empty)
    pg2.evaluate("()=>{ state.text.goalsHTML='<li>'+'x'.repeat(NOTES_MAX-9)+'</li>'; save(); applyText(); }")
    pg2.locator('#goalsList').click(); pg2.keyboard.press('End'); pg2.keyboard.type('zz'); pg2.evaluate("document.activeElement.blur()"); pg2.wait_for_timeout(200)
    if pg2.evaluate("state.text.goalsHTML.length") < 19000: problems.append('notes over the limit were emptied')
    # a tiny value from a file shows as a plain number, never "1e-7" (typing after it would read 175)
    if pg2.evaluate("[fieldNum(1e-7), fieldNum(0.0001), fieldNum(2.5), fieldNum(0)]") != ['', '0.0001', '2.5', '']: problems.append('tiny values shown with an exponent')
    # with browser storage blocked, the layout button still switches both ways
    pg2.set_viewport_size({'width': 1700, 'height': 900}); pg2.wait_for_timeout(200)   # wide enough for the wide layout
    pg2.evaluate("()=>{ Storage.prototype.setItem=()=>{ throw new Error('blocked'); }; }")
    w = [pg2.evaluate("()=>{ document.getElementById('wideBtn').click(); return document.documentElement.classList.contains('wide'); }") for _ in range(3)]
    if w not in ([True, False, True], [False, True, False]): problems.append(f'wide layout with storage blocked: {w}')
    if w[-1]: pg2.evaluate("document.getElementById('wideBtn').click()")
    pg2.set_viewport_size({'width': 1360, 'height': 900}); pg2.wait_for_timeout(200)
    pg2.evaluate("window.scrollTo(0, document.body.scrollHeight)"); pg2.wait_for_timeout(200)   # desktop: the editor is beside the cards, no pill
    if not pg2.evaluate("document.getElementById('backpill').hidden"): problems.append('desktop: a back pill showed')
    pg2.close()
    # keyboard and screen: a default title in Estonian stays the default; a pillar block shown again while it closes stays;
    # an unnamed fund's tooltip isn't an empty box; a dropdown stays open when its own box is pressed and closes on a press
    # outside (also when its button never got the focus, as in Safari); the keyboard stays where it was after ✎, a new type,
    # a picked suggestion or a removed row; the language switch keeps an Undo note; a full list's "+ Add" can still be reached
    pg3 = b.new_page(viewport={'width': 1360, 'height': 900}); watch_errors(pg3, errs, n=150); pg3.goto(PAGE); pg3.evaluate("localStorage.clear()"); pg3.reload(); pg3.wait_for_timeout(300)
    pg3.evaluate("s=>localStorage.setItem(KEY, JSON.stringify(s))", fixture('example.json')); pg3.reload(); pg3.wait_for_timeout(300)   # as your own data, not the example
    pg3.evaluate("()=>document.querySelectorAll('.editor details').forEach(d=>d.open=true)"); pg3.wait_for_timeout(300)
    pg3.click('.langtabs [data-lang=et]'); pg3.wait_for_timeout(150)
    ttl = pg3.locator('[data-text=titleDebt]'); ttl.click(); pg3.keyboard.press('End'); pg3.keyboard.type('x'); pg3.keyboard.press('Backspace'); pg3.keyboard.press('Enter')
    pg3.click('.langtabs [data-lang=en]'); pg3.wait_for_timeout(150)
    if pg3.evaluate("state.text.titleDebt") != pg3.evaluate("DEFAULTS.text.titleDebt") or ttl.text_content() != pg3.evaluate("DEFAULTS.text.titleDebt"): problems.append(f'an Estonian default title was saved as your own: {ttl.text_content()!r}')
    blk = pg3.evaluate("""async s=>{ state=normalize({gross:3000}); save(); refreshAll(); await new Promise(r=>setTimeout(r, 400));   // only pay: the block shows while there's pay
        const f=document.querySelector('[data-key=gross]'), set=v=>{ f.value=v; f.dispatchEvent(new Event('input', {bubbles:true})); };
        set('0'); await new Promise(r=>setTimeout(r, 60)); set('4000'); await new Promise(r=>setTimeout(r, 500)); const d=getComputedStyle(document.getElementById('p2-block')).display;
        state=normalize(s); save(); refreshAll(); return d; }""", fixture('example.json'))
    if blk == 'none': problems.append('the 2nd pillar block stayed hidden after a quick retype')
    pg3.evaluate("()=>{ state.p2funds[0].name=''; refreshAll(); }"); pg3.wait_for_timeout(200)
    pg3.hover('#p2-funds .fn'); pg3.wait_for_timeout(600)
    if pg3.evaluate("getComputedStyle(document.getElementById('tip')).display") != 'none': problems.append('an unnamed fund shows an empty tooltip box')
    pg3.mouse.move(5, 5); pg3.evaluate("()=>{ state.p2funds[0].name='My {YEAR} fund'; refreshAll(); }"); pg3.wait_for_timeout(200)   # the rules' figures never go into your own names
    pg3.hover('#p2-funds .fn'); pg3.wait_for_timeout(600)
    if pg3.evaluate("document.getElementById('tip').textContent") != 'My {YEAR} fund': problems.append(f'your fund name changed in its tooltip: {pg3.evaluate("document.getElementById(\'tip\').textContent")!r}')
    sel = pg3.locator('#tgt-rows .cselect.ttype').first; sel.click(); pg3.wait_for_timeout(100)
    box = pg3.evaluate("()=>{ const m=document.getElementById(document.querySelector('#tgt-rows .cselect.ttype').getAttribute('aria-controls')); m.style.paddingBottom='6px'; const r=m.getBoundingClientRect(); return [r.left+r.width/2, r.bottom-2]; }")
    pg3.mouse.move(*box); pg3.mouse.down(); pg3.mouse.up(); open1 = pg3.evaluate("document.querySelector('#tgt-rows .cselect.ttype').getAttribute('aria-expanded')")
    pg3.mouse.click(5, 5); open2 = pg3.evaluate("document.querySelector('#tgt-rows .cselect.ttype').getAttribute('aria-expanded')")
    pg3.evaluate("()=>{ document.activeElement.blur(); document.querySelector('#tgt-rows .cselect.ttype').click(); }"); pg3.mouse.click(5, 5)   # opened without the focus
    open3 = pg3.evaluate("document.querySelector('#tgt-rows .cselect.ttype').getAttribute('aria-expanded')")
    if [open1, open2, open3] != ['true', 'false', 'false']: problems.append(f'dropdown: open after pressing its box {open1}, after a press outside {open2}, unfocused {open3}')
    pg3.evaluate("()=>{ state.incomes=[{name:'', amount:500, freq:'month', tax:'salary', rate:0}]; save(); refreshAll(); }"); pg3.wait_for_timeout(200)
    where = lambda: pg3.evaluate("()=>{ const a=document.activeElement; return (a.parentElement.closest('[id]')||{}).id+' '+a.tagName+'.'+a.className; }")   # the list it's in (a dropdown has an id of its own)
    pg3.focus('[data-edit="property:debts"]'); pg3.keyboard.press('Enter'); pg3.wait_for_timeout(100)
    in_debts = lambda: pg3.evaluate("()=>{ const a=document.activeElement, h=document.querySelector('[data-part=debts]'); return a.closest('.editor') && a.tagName!=='SUMMARY' && a.getClientRects().length && h.compareDocumentPosition(a) & Node.DOCUMENT_POSITION_FOLLOWING ? 'debts part' : a.tagName+'.'+a.className; }")
    w1 = in_debts()   # the part's first control
    pg3.focus('#tgt-rows .cselect.ttype'); pg3.keyboard.press('Enter'); pg3.keyboard.press('ArrowDown'); pg3.keyboard.press('Enter'); pg3.wait_for_timeout(100); w2 = where()
    pg3.focus('#income-rows .invname'); pg3.keyboard.press('ArrowDown'); pg3.keyboard.press('ArrowDown'); pg3.keyboard.press('Enter'); pg3.wait_for_timeout(100); w3 = where()   # Freelance work: its tax rebuilds the row
    picked_open = pg3.evaluate("document.querySelectorAll('body > .suggest:not([hidden])').length")   # the rebuilt row's list stays shut
    pg3.focus('#debt-rows .iconbtn:not(.mv)'); pg3.keyboard.press('Enter'); pg3.wait_for_timeout(500)   # a loan removed: the next loan's name gets the focus, its list stays shut
    picked_open += pg3.evaluate("document.querySelectorAll('body > .suggest:not([hidden])').length")
    pg3.focus('#etf-rows .iconbtn:not(.mv)'); pg3.keyboard.press('Enter'); pg3.wait_for_timeout(500); w4 = where()
    menus = picked_open + pg3.evaluate("document.querySelectorAll('body > .suggest:not([hidden])').length")   # moving the focus in code opens no name suggestions
    if w1 != 'debts part' or 'tgt-rows' not in w2 or 'income-rows' not in w3 or 'etf-rows' not in w4 or menus:
        problems.append(f'focus after ✎ {w1}, a new type {w2}, a suggestion {w3}, a removed row {w4}; suggestion lists open: {menus}')
    pg3.click('.langtabs [data-lang=et]'); pg3.wait_for_timeout(150)
    if pg3.evaluate("document.querySelector('.toast').hidden") or 'Võta tagasi' not in pg3.evaluate("document.querySelector('.toast').textContent"): problems.append('switching language closed the Undo note, or left it in English')
    pg3.click('.langtabs [data-lang=en]'); pg3.wait_for_timeout(150)
    pg3.focus('.toast button'); pg3.keyboard.press('Enter'); pg3.wait_for_timeout(200); undone = where()   # Undo with the keyboard: on to the row that came back
    if 'etf-rows' not in undone: problems.append(f'focus after Undo in the note: {undone}')
    full = pg3.evaluate("()=>{ state.targets=Array.from({length:listMax('targets')}, (_,i)=>({name:'t'+i, kind:'cash', amount:1})); refreshAll(); const b=document.getElementById('addTarget'); b.focus(); return [b.getAttribute('aria-disabled'), document.activeElement===b, (b.getAttribute('aria-description')||'').length>0]; }")
    if full != ['true', True, True]: problems.append(f'"+ Add" at the limit: {full}')
    # a field tapped on a touch screen doesn't show its label's help over the field below; one reached with Tab sits next to its
    # field (above it here, wherever the last tip was) and moves with it when that scrolls (here the editor panel scrolls: a page
    # scroll can leave the sticky editor where it is, as in WebKit)
    tp = pg3.evaluate("""async ()=>{ const f=document.querySelector('[data-key=projInflation]'), tip=document.getElementById('tip'), ed=document.querySelector('.editor'); document.dispatchEvent(new PointerEvent('pointerdown', {pointerType:'touch', bubbles:true}));
        f.focus({focusVisible:true}); const tapped=getComputedStyle(tip).display; document.dispatchEvent(new KeyboardEvent('keydown', {key:'Tab', bubbles:true}));
        f.blur(); tip.style.left=(innerWidth-120)+'px'; f.scrollIntoView({block:'end'}); ed.scrollBy(0, 30); await new Promise(r=>setTimeout(r, 100));   // the last tip near the right edge, the field low: its tip goes above it
        f.focus({focusVisible:true}); const a0=f.getBoundingClientRect().top;
        // next to its field: just below it, or just above it when there's no room below (where it sits can flip as it moves)
        const gap=()=>{ const t=tip.getBoundingClientRect(), r=f.getBoundingClientRect(); return Math.round(Math.min(Math.abs(t.top-r.bottom), Math.abs(r.top-t.bottom))); }, g0=gap();
        const scrolled=new Promise(r=>addEventListener('scroll', ()=>requestAnimationFrame(()=>r()), {once:true, capture:true}));
        ed.scrollBy(0, 60); await Promise.race([scrolled, new Promise(r=>setTimeout(r, 1000))]);   // the field moves up, staying in sight (out of sight, its tip goes)
        return [tapped, getComputedStyle(tip).display, g0, gap(), Math.round(f.getBoundingClientRect().top-a0)]; }""")
    if tp[0] != 'none' or tp[1] == 'none' or not tp[4] or tp[2] > 14 or tp[3] > 14: problems.append(f'field help: tapped {tp[0]}, tabbed {tp[1]}, {tp[2]}px from its field, {tp[3]}px after the field moved {tp[4]}px')
    # every loan fixed-rate: ✎ skips the hidden Euribor field and goes to the first control shown
    pg3.evaluate("()=>{ state.debts=[{name:'Car', balance:5000, rtype:'fixed', rate:5, margin:0, payment:200, asset:0}]; save(); refreshAll(); }"); pg3.wait_for_timeout(100)
    pg3.focus('[data-edit="property:debts"]'); pg3.keyboard.press('Enter'); pg3.wait_for_timeout(100); w5 = in_debts()
    # a suggestion picked with the arrows is let go when you type on: the field never points at an option that isn't highlighted
    pg3.fill('#income-rows .invname', ''); pg3.keyboard.type('r'); pg3.keyboard.press('ArrowDown'); pg3.keyboard.press('ArrowDown'); pg3.keyboard.type('e')
    ad = pg3.evaluate("()=>{ const i=document.querySelector('#income-rows .invname'), id=i.getAttribute('aria-activedescendant'), m=document.getElementById(i.getAttribute('aria-controls')); return [m.hidden ? 'shut' : 'open', !id || document.getElementById(id).classList.contains('act')]; }")
    pg3.keyboard.press('Escape')
    # the month of birth, picked with the keyboard beside the year: Not given → January → February
    pg3.evaluate("()=>{ state.birthYear=1961; state.birthMonth=0; save(); refreshAll(); }"); pg3.focus('#bmonth'); pg3.keyboard.press('Enter'); pg3.keyboard.press('ArrowDown'); pg3.keyboard.press('ArrowDown'); pg3.keyboard.press('Enter'); pg3.wait_for_timeout(100)
    bm = pg3.evaluate("[state.birthMonth, document.getElementById('bmonth').textContent, document.activeElement.id]")
    if bm != [2, 'Feb', 'bmonth']: problems.append(f'month of birth picked with the keyboard (value, shown, focus): {bm}')
    if w5 != 'debts part' or ad != ['open', True]: problems.append(f'focus after ✎ with only fixed-rate loans {w5}; typing after an arrow pick (list, points at the highlighted one) {ad}')
    # a tooltip whose field goes out of sight goes too, instead of staying at the edge of the screen: the field is moved off the
    # screen directly (a transform) and a scroll event sent, so it doesn't depend on how far a page can scroll in each browser
    # (following the field on a real scroll is checked above)
    pg6 = b.new_page(viewport={'width': 390, 'height': 844}, reduced_motion='reduce'); watch_errors(pg6, errs, n=150); pg6.goto(PAGE); pg6.wait_for_timeout(300)
    gone = pg6.evaluate("""()=>{ document.querySelectorAll('.editor details').forEach(d=>d.open=true); const f=document.querySelector('[data-key=projInflation]'), tip=document.getElementById('tip');
        f.scrollIntoView({block:'center'}); document.dispatchEvent(new KeyboardEvent('keydown', {key:'Tab', bubbles:true})); f.focus({focusVisible:true}); const shown=getComputedStyle(tip).display;
        window.dispatchEvent(new Event('scroll')); const still=getComputedStyle(tip).display;   // in sight: it stays
        f.style.transform='translateY(-3000px)'; window.dispatchEvent(new Event('scroll')); const out=[shown, still, getComputedStyle(tip).display, Math.round(f.getBoundingClientRect().bottom)];
        f.style.transform=''; return out; }""")
    pg6.close()
    # the narrowest phones: "Not given (July)" and its Estonian fit beside the year
    pg7 = b.new_page(viewport={'width': 320, 'height': 700}); watch_errors(pg7, errs, n=150); pg7.goto(PAGE); pg7.wait_for_timeout(300)
    cut = []
    for lang in ('en', 'et'):
        pg7.evaluate("l=>document.querySelector('.langtabs [data-lang='+l+']').click()", lang); pg7.wait_for_timeout(150)   # in the ☰ menu at this width
        if pg7.evaluate("()=>{ const s=document.getElementById('bmonth'); return s.scrollWidth>s.clientWidth; }"): cut.append(lang)
    pg7.close()
    if cut: problems.append(f'"Not given (July)" cut off at 320px in: {cut}')
    if gone[:3] != ['block', 'block', 'none'] or gone[3] >= 0: problems.append(f'tooltip with its field in sight, then off the screen (before, in sight, off, field bottom): {gone}')
    # the target type dropdown is read with its value; a target's buttons follow its name, unnamed ones say which row
    acc = pg3.evaluate("""()=>{ state.targets=[{name:'', kind:'cash', amount:1}, {name:'', kind:'cash', amount:2}]; save(); refreshAll();
        const s=document.querySelector('#tgt-rows .cselect.ttype'), nm=(s.getAttribute('aria-labelledby')||'').split(' ').map(id=>(document.getElementById(id)||{}).textContent).join(' ');
        const dels=()=>[...document.querySelectorAll('#tgt-rows .iconbtn:not(.mv)')].map(b=>b.getAttribute('aria-label')), before=dels();
        const i=document.querySelector('#tgt-rows .invsub input[type=text]'); i.value='Gamma'; i.dispatchEvent(new Event('input', {bubbles:true}));
        return [nm==='Type '+s.textContent, before, dels()[0], [...document.querySelectorAll('#tgt-rows .mv')].slice(2).map(b=>b.getAttribute('aria-label'))]; }""")
    if acc != [True, ['Remove target 1', 'Remove target 2'], 'Remove target “Gamma”', ['Move up', 'Move down']]: problems.append(f'target type name with its value, unnamed and renamed buttons, an unnamed row\'s arrows: {acc}')
    # name suggestions closed with Escape open again with ArrowDown
    pg3.evaluate("()=>{ state.incomes=[{name:'', amount:500, freq:'month', tax:'salary', rate:0}]; save(); refreshAll(); }")
    pg3.focus('#income-rows .invname'); pg3.keyboard.press('Escape'); pg3.keyboard.press('ArrowDown')
    reopened = pg3.evaluate("document.querySelector('#income-rows .invname').getAttribute('aria-expanded')"); pg3.keyboard.press('Escape')
    if reopened != 'true': problems.append(f'name suggestions after Escape, then ArrowDown: aria-expanded {reopened}')
    # a history month changed with the keyboard moves in the list, and the keyboard with it
    pg3.evaluate("()=>{ state.enableHistory=false; state.history=[{m:'2026-05', nw:1000}, {m:'2026-07', nw:2000}, {m:'2026-08', nw:2500}]; save(); refreshAll(); }")
    pg3.focus('#hist-rows .hmon >> nth=0'); pg3.keyboard.press('Enter'); pg3.keyboard.press('ArrowUp'); pg3.keyboard.press('ArrowUp'); pg3.keyboard.press('Enter'); pg3.wait_for_timeout(200)
    hm = pg3.evaluate("[state.history.map(e=>e.m).join(','), document.activeElement.className, document.activeElement.textContent]")
    if hm != ['2026-05,2026-06,2026-07', 'cselect hmon', 'Jun']: problems.append(f'history month changed with the keyboard (months, focus): {hm}')
    # the budget's "Expenses" with categories: its breakdown is read too
    el_ = pg3.evaluate("()=>{ state.enableExpenseCats=true; state.expenseItems=[{name:'Rent', amount:600, freq:'month'}]; save(); refreshAll(); const l=document.getElementById('bd-exp-label'); return [(l.getAttribute('aria-description')||'').startsWith('Per month'), l.tabIndex]; }")
    if el_ != [True, 0]: problems.append(f'budget Expenses breakdown for screen readers and Tab: {el_}')
    # the top bar's Undo, used with the keyboard, hands the focus to Reset beside it (Undo itself goes)
    pg3.evaluate("()=>{ state.gross=3000; save(); refreshAll(); }"); pg3.focus('#resetBtn'); pg3.keyboard.press('Enter'); pg3.wait_for_timeout(200)
    pg3.focus('#revertBtn'); pg3.keyboard.press('Enter'); pg3.wait_for_timeout(200)
    if pg3.evaluate("document.activeElement.id") != 'resetBtn': problems.append('focus after the top bar\'s Undo: '+pg3.evaluate("document.activeElement.id||document.activeElement.tagName"))
    pg3.close()
    # the compact top bar: its ☰ menu closes when Tab leaves it, and an action in it leaves the focus on ☰
    pg4 = b.new_page(viewport={'width': 400, 'height': 800}); watch_errors(pg4, errs, n=150); pg4.goto(PAGE); pg4.wait_for_timeout(300)
    pg4.click('#moreBtn'); pg4.focus('#tbMenu .langtabs [data-lang=en]'); pg4.keyboard.press('Tab'); pg4.keyboard.press('Tab'); pg4.wait_for_timeout(50)
    left = pg4.evaluate("document.querySelector('.topbar').classList.contains('menu-open') && !document.getElementById('tbMenu').contains(document.activeElement)")
    pg4.click('#moreBtn'); pg4.focus('#tbMenu [data-lang=et]'); pg4.keyboard.press('Enter'); pg4.wait_for_timeout(200)
    after = pg4.evaluate("document.activeElement.id")
    pg4.click('#moreBtn'); pg4.focus('#tbMenu [data-lang=en]'); pg4.click('#moreBtn'); pg4.wait_for_timeout(100)   # with the keyboard in it, ☰ still closes it
    shut = not pg4.evaluate("document.querySelector('.topbar').classList.contains('menu-open')")
    if left or after != 'moreBtn' or not shut: problems.append(f'☰ menu: open after Tab left it {left}, focus after an action in it {after!r}, closed by ☰ with the keyboard in it {shut}')
    pg4.close()
    # a touch screen: tapping into a list-row field (its label with the help wraps it) shows no help over the next row, while
    # tapping the label's words still does
    ctx5 = b.new_context(viewport={'width': 400, 'height': 800}, has_touch=True, reduced_motion='reduce'); pg5 = ctx5.new_page(); watch_errors(pg5, errs, n=150); pg5.goto(PAGE); pg5.wait_for_timeout(300)
    pg5.evaluate("()=>{ state=normalize({debts:[{name:'Car', balance:5000, rtype:'fixed', rate:5, payment:200}]}); save(); refreshAll(); document.querySelectorAll('.editor details').forEach(d=>d.open=true); }"); pg5.wait_for_timeout(200)
    pay = pg5.locator('#debt-rows label[data-tip^="What you pay"]'); pay.scroll_into_view_if_needed()
    tip_shown = lambda: pg5.evaluate("getComputedStyle(document.getElementById('tip')).display") != 'none'
    pay.locator('input').tap(); pg5.wait_for_timeout(200); on_field = tip_shown()
    pg5.evaluate("document.activeElement.blur()"); pay.locator('.lt').tap(); pg5.wait_for_timeout(200); on_label = tip_shown()
    if on_field or not on_label: problems.append(f'phone help in a list row: shown after tapping into the field {on_field}, after tapping its label {on_label}')
    # "Advanced" opens by itself when something in it is changed, but not for the 0% deposit increase everyone upgrading has saved
    adv = pg5.evaluate("""()=>[{projGrowth:0}, {projGrowth:0, enableProjFee:true}].map(s=>{ state=normalize({gross:3000, ...s}); document.querySelectorAll('details.adv').forEach(d=>{ d.open=false; d._seen=false; }); refreshAll();
        const d=document.querySelector('details.adv[data-adv="projection"]'); return [d.open, d.querySelector('.advtag').textContent.trim()]; })""")
    if adv != [[False, '· 1 changed'], [True, '· 2 changed']]: problems.append(f'Advanced with an old 0% deposit increase (open, badge), then with a fee too: {adv}')
    ctx5.close()
    if errs: problems.append(f'phone and desktop: page errors {errs[:2]}')
    b.close()

finish('editor', problems, f'{len(ADD)} add buttons, the car tax default, decimals with a comma or a dot and the surplus slider, in 2 languages, the back pill, keyboard focus and menus: ' + ('all fine' if not problems else str(problems)))
