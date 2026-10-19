"""Your path (Progress): net worth by part, month by month, against an independent model, and the card around it.

Each month: pensions and investments grow like the Projection, cash earns its interest and adds the part of the yearly
surplus that isn't invested, loans shrink by their payments (one without a payment stays as it is) and a paid-off loan's
payment is split like the surplus between cash and investments; saving stops when you retire; property bought with a loan keeps up with prices, other property its euro value; pensions and investments grow at their own fees;
and everything is in today's money when inflation is on, also beyond 30 years on the Retire zoom, for pensioners too.
Milestone dots sit exactly at the dates the Targets card gives (or, with "Try other numbers" on, where the path itself
reaches the goal). Also: the zoom buttons, Retire only with a year of birth and rounded up to whole years (also on a day
where that differs from rounding off), a loan that never gets paid off, Estonian, hover values, the wide layout and phone
widths.
Run: python tests/test_path.py [number of users]"""
from playwright.sync_api import sync_playwright
import json, random, math, sys, datetime
from helpers import PAGE, finish, fixture, launch, pick, watch_errors
from model import surplus_invested, savings, save_months, payout_tax, pension_age, payout_age




def model_path(c, st, net_p, net_i, months):
    """Net worth and its parts for months 0..months, in today's money when inflation is on; saving stops when you retire.
    Pensions and investments grow at their own fees (net_p, net_i); what was bought with a loan keeps up with prices, other
    property keeps its euro value. After tax on: pensions minus the payout tax, investments minus income tax on gains above
    what was put in."""
    rp, rm = (max(0, 1 + n / 100) ** (1 / 12) - 1 for n in (net_p, net_i)); g = st['projGrowth'] / 100; stop = save_months(st, datetime.date.today().year)
    infl = (st['projInflation'] if st['enableProjReal'] else 0) / 100
    pen, inv = c['pension'], c['etfVal'] + c['invValue']; mp, mi = c['penMonthly'], c['investedNoPen'] + surplus_invested(st, c['surplus'])
    cash, owed, inv_f, inv_put = savings(c['debts'], months, st, c['surplus'], net_i, c['buffer'], stop); out = []
    i0 = inv; put = inv; tax = st['enableProjNet']; inc = st['taxRate'] / 100 if tax else 0
    pt = payout_tax(payout_age(st), st['payoutYears'], st['taxRate'], pension_age(st)) / 100 if tax else 0
    for i in range(months + 1):
        if i:
            pen = pen * (1 + rp) + (mp if i <= stop else 0); inv = inv * (1 + rm) + (mi if i <= stop else 0); put += mi if i <= stop else 0
            if i % 12 == 0: mp *= 1 + g; mi *= 1 + g
        defl = (1 + infl) ** (i / 12); val = inv + inv_f[i]; dep = (st['invDeposits'] if st['invDeposits'] > 0 else i0) + (put - i0) + inv_put[i]
        inv_all = val - inc * max(0, val - dep); pen_k = pen * (1 - pt)
        phys = c['physVal'] + c['debtAssets'] * defl
        out.append(dict(pen=pen_k / defl, inv=inv_all / defl, cash=cash[i] / defl, debt=owed[i] / defl, nw=(phys + pen_k + inv_all + cash[i] - owed[i]) / defl))
    return out


def close(a, b): return abs(a - b) <= max(0.02, abs(b) * 1e-9)


def main():
    random.seed(int(sys.argv[2]) if len(sys.argv) > 2 else 11); N = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    fails = 0
    with sync_playwright() as p:
        b = launch(p); pg = b.new_page(viewport={'width': 1300, 'height': 900}); errs=watch_errors(pg, n=200)
        pg.goto(PAGE); pg.wait_for_timeout(300)
        pg.evaluate("document.querySelector('.viewtabs [data-view=progress]').click()")
        base = fixture('example.json')
        # 1. the numbers, for random mixes of returns, inflation, deposit growth, surplus shares, loans and targets
        for k in range(N):
            s = json.loads(json.dumps(base))
            s.update(projReturn=pick(7, 0, -5, 15, random.uniform(-20, 30)), projInflation=pick(2.5, 0, 6), projGrowth=pick(0, 3, -5),
                     enableProjSurplus=pick(True, False), projSurplusPct=pick(100, 60, 0, random.uniform(0, 100)), enableProjFee=pick(True, False), projFee=pick(0, 0.5),
                     enableProjReal=pick(True, False), expenses=pick(1600, 500, 4000, 9000), euribor=pick(2.6, 0), enableDebtTargets=pick(True, False),
                     enableProjCustom=pick(False, False, True), projStart=pick(0, 50000), projMonthly=pick(0, 800), birthYear=pick(None, 1958, 1975, 1990, 2005), birthMonth=pick(0, 0, 3, 11), gross=pick(3800, 8000, 15000),   # 1958: already a pensioner
                     enableProjNet=pick(True, False), invDeposits=pick(0, 0, 30000), payoutYears=pick(20, 10))   # higher pay: a surplus left, so paid-off loans get invested too
            for a in s['accounts']: a['yield'] = pick(a['yield'], 0, 4.5, -0.5)   # cash earns its interest after tax
            s['debts'] = [{'name': 'd' + str(j), 'balance': pick(5000, 150000, 300000), 'rtype': pick('fixed', 'euribor'), 'rate': pick(0, 3, 8, 25), 'margin': pick(0.5, 2),
                           'payment': pick(0, 100, 950, 3000), 'asset': pick(0, 200000)} for j in range(random.randint(0, 3))]
            s['targets'] = [{'name': 'nw', 'kind': 'networth', 'amount': pick(1e5, 5e5, 2e6)}, {'name': 'inv', 'kind': 'invested', 'amount': pick(1e5, 1e6)},
                            {'name': 'cash', 'kind': 'cash', 'amount': pick(5000, 30000, 200000)}, {'name': 'fire', 'kind': 'fire', 'amount': 0, 'rate': 4, 'spend': 0, 'health': 'no'}]
            sm = save_months(s, datetime.date.today().year); far = 360 < sm < math.inf   # retiring more than 30 years ahead: the Retire zoom shows beyond 30 years
            r = pg.evaluate("""a=>{ const s=a[0]; state=normalize(s); pathSpan=a[1]; refreshAll(); const c=compute(), R=projRate(c), H=pathHover;
                return {net:R.net, netPen:projRate(c,null,'pen').net, netInv:projRate(c,null,'inv').net, st:{...state}, c:{pension:c.pension, penMonthly:c.penMonthly, etfVal:c.etfVal, invValue:c.invValue, investedNoPen:c.investedNoPen, surplus:c.surplus,
                          buffer:c.buffer, networth:c.networth, physVal:c.physVal, debtAssets:c.debtAssets, debts:c.debtList.filter(d=>(+d.balance||0)>0).map(d=>({B:+d.balance, r:(+d.rate||0)/1200, P:Math.max(0,+d.payment||0)}))},
                        pts:H.pts.map(p=>({pen:p.pen, inv:p.inv, cash:p.cash+p.short, debt:p.debt, nw:p.nw})), ms:H.ms.map(m=>({name:m.name, m:m.m})),
                        eta:state.targets.map(t=>targetStatus(t,c).eta), dots:document.querySelectorAll('#path-svg .pdot-ms').length, rows:document.querySelectorAll('#path-list .row').length,
                        later:document.querySelectorAll('#path-list .row.later').length, note:document.getElementById('path-note').textContent}; }""", [s, 'ret' if far else '30'])
            st, c = r['st'], r['c']
            full = model_path(c, st, r['netPen'], r['netInv'], 720); n = math.ceil(sm / 12) * 12 if far else 360; want = full[:n + 1]
            if len(r['pts']) != n + 1: fails += 1; print(k, 'path has', len(r['pts']), 'months, want', n + 1)
            if not st['enableProjNet'] and not close(r['pts'][0]['nw'], c['networth']):   # after tax, today's gains count as cashed out
                fails += 1; print(k, 'path starts at', r['pts'][0]['nw'], 'but net worth is', c['networth'])
            for i in (0, 1, 11, 12, 13, 59, 120, 240, 360, 361, 480, n):
                if i > n or i >= len(r['pts']): continue
                got, w = r['pts'][i], want[i]
                bad = [x for x in w if not close(got[x], w[x])]
                if bad: fails += 1; print(k, 'month', i, ', '.join(f'{x} {got[x]:.2f} want {w[x]:.2f}' for x in bad)); break
            # milestones: the Targets card's dates, or with "Try other numbers" on, the first month the path reaches the goal
            ms = {m['name']: m['m'] for m in r['ms']}
            for t, eta in zip(st['targets'], r['eta']):
                if st['enableProjCustom'] and t['kind'] in ('networth', 'invested'):
                    val = (lambda q: q['nw']) if t['kind'] == 'networth' else (lambda q: q['pen'] + q['inv'])
                    eta = next((i for i, q in enumerate(full) if val(q) >= t['amount'] - 1e-6), math.inf)
                eta = math.inf if eta is None or eta > 1e300 else eta
                name = t['name']
                if 0 < eta < math.inf:
                    if name not in ms: fails += 1; print(k, 'no milestone for', name, 'due in', eta); continue
                    if ms[name] != eta: fails += 1; print(k, name, 'at month', ms[name], 'want', eta)
                elif name in ms: fails += 1; print(k, 'milestone for', name, 'which is', 'reached' if eta == 0 else 'never reached')
            # a cash goal is reached when the path's cash gets there (spare cash plus the payments of loans paid off)
            ca = s['targets'][2]['amount']; want_c = next((i for i, q in enumerate(full) if q['cash'] >= ca - 1e-6), math.inf)
            got_c = math.inf if r['eta'][2] is None or r['eta'][2] > 1e300 else r['eta'][2]
            if got_c != want_c: fails += 1; print(k, 'cash goal at month', got_c, 'want', want_c)
            loans = [m for m in r['ms'] if m['name'].endswith('paid off')]
            if not st['enableDebtTargets'] and loans: fails += 1; print(k, 'loan payoffs shown with the switch off')
            if r['dots'] != r['rows'] - r['later']: fails += 1; print(k, r['dots'], 'dots but', r['rows'] - r['later'], 'rows inside the chart')
            if ('Try other numbers' in r['note']) != bool(st['enableProjCustom']): fails += 1; print(k, 'note about Try other numbers', st['enableProjCustom'], r['note'][-120:])

        # 2. the card: nothing entered yet shows a hint; a target without an amount gets no dot; a cash shortfall isn't called a loan
        e = pg.evaluate("""()=>{ state=normalize({}); refreshAll(); const c=document.getElementById('path-card'); return [c.classList.contains('isempty'), !!document.getElementById('path-empty').getClientRects().length, !!document.getElementById('pathbtns').getClientRects().length,
                 document.querySelectorAll('#path-list .row').length, document.getElementById('path-legend').textContent, document.getElementById('ret-tag').textContent]; }""")
        if e != [True, True, False, 0, '', '']: fails += 1; print('emptied: path card (isempty, hint, buttons, old rows, legend) and the Retirement header', e)   # nothing left from the data before
        s = json.loads(json.dumps(base)); s.update(expenses=6000, debts=[], targets=[{'name': 'Zero', 'kind': 'networth', 'amount': 0}])
        z = pg.evaluate("s=>{ state=normalize(s); refreshAll(); return [pathHover.ms.map(m=>m.name), document.getElementById('path-legend').textContent, document.getElementById('path-card').classList.contains('isempty')]; }", s)
        if 'Zero' in z[0] or 'Shortfall' not in z[1] or 'Loans' in z[1] or z[2]: fails += 1; print('no amount / shortfall', z)
        # the zoom buttons, Retire only with a year of birth, a loan that never gets paid off, Estonian, hover
        s = json.loads(json.dumps(base)); s.update(birthYear=None, enableDebtTargets=True)
        s['debts'] = [{'name': 'Forever', 'balance': 100000, 'rtype': 'fixed', 'rate': 10, 'margin': 0, 'payment': 100, 'asset': 0}]   # pays less than the interest
        z = pg.evaluate("""s=>{ state=normalize(s); pathSpan='ret'; save(); refreshAll(); return {ret:document.getElementById('path-ret').hidden, active:document.querySelector('#pathbtns .active').dataset.span,
                 forever:pathHover.ms.some(m=>m.name.startsWith('Forever')), n:pathHover.pts.length}; }""", s)
        if z != {'ret': True, 'active': '10', 'forever': False, 'n': 121}: fails += 1; print('without a year of birth', z)
        s['birthYear'] = 1990
        y = pg.evaluate("""s=>{ state=normalize(s); save(); refreshAll(); const out={};
                 for(const b of document.querySelectorAll('#pathbtns button')){ b.click(); out[b.dataset.span]=[pathHover.pts.length-1, Math.round((pathHover.t1-pathHover.t0)*12), b.classList.contains('active')]; }
                 const r=retirement(compute()); out.year=r.year; out.label=document.getElementById('path-ret').textContent; return out; }""", s)
        now = datetime.date.today().year
        for span in ('5', '10', '20', '30'):
            m = int(span) * 12
            if y[span] != [m, m, True]: fails += 1; print('zoom', span, y[span])
        ry = math.ceil(save_months(s, now) / 12) * 12   # the Retire zoom: the months to retirement, rounded up to whole years
        if y['ret'][:3] != [ry, ry, True] or y['label'] != 'Retire': fails += 1; print('zoom to retirement', y['ret'], y['year'], y['label'])
        # and on 15 March, when the months to retirement aren't whole years plus 6 or more (rounding up and rounding off differ)
        q = getattr(b, '_b', b).new_page(); q.clock.set_fixed_time('2027-03-15T12:00:00'); q.goto(PAGE); q.wait_for_timeout(300)
        got = q.evaluate("s=>{ state=normalize(s); pathSpan='ret'; refreshAll(); return Math.round((pathHover.t1-pathHover.t0)*12); }", s); q.close()
        if got != math.ceil(save_months(s, 2027, 2) / 12) * 12: fails += 1; print('zoom to retirement on 15 March', got, 'want', math.ceil(save_months(s, 2027, 2) / 12) * 12)
        # zoomed in so retirement is past the end: the note doesn't promise its dot, and says why its row is dimmed
        pg.click('#pathbtns [data-span="5"]'); pg.wait_for_timeout(100)
        note = pg.evaluate("document.getElementById('path-note').textContent")
        if 'retirement.' in note or 'Dimmed rows' not in note: fails += 1; print('note at 5 years', note[-200:])
        # hover: the box shows that month's net worth
        pg.click('#pathbtns [data-span="10"]'); pg.wait_for_timeout(900)   # the heading's year finishes rolling
        if pg.evaluate("document.getElementById('path-tag').textContent").split(' ')[1] != str(now + 10): fails += 1; print('path heading', pg.evaluate("document.getElementById('path-tag').textContent"))
        box = pg.locator('#path-svg svg').bounding_box(); pg.mouse.move(box['x'] + box['width'] * 0.5, box['y'] + box['height'] * 0.5); pg.wait_for_timeout(100)
        h = pg.evaluate("""()=>{ const b=document.querySelector('#path-chart .ph-box'), ov=document.querySelector('#path-chart .phov'), H=pathHover, svg=document.querySelector('#path-svg svg').getBoundingClientRect();
                 const x=parseFloat(document.querySelector('#path-chart .ph-line').style.left), k=svg.width/H.W, p=H.pts.reduce((a,q)=>Math.abs(H.X(q.t)*k-x)<Math.abs(H.X(a.t)*k-x)?q:a);
                 return {shown:!ov.hidden, text:b.textContent, want:eurS(p.nw), parts:b.querySelectorAll('.row2').length}; }""")
        if not h['shown'] or h['want'] not in h['text'] or h['parts'] < 5: fails += 1; print('path hover', h)
        pg.mouse.move(5, 5); pg.wait_for_timeout(100)
        if not pg.evaluate("document.querySelector('#path-chart .phov').hidden"): fails += 1; print('path hover stayed after the mouse left')
        # the projection's hover still works through the same helper
        pg.evaluate("document.querySelector('.viewtabs [data-view=overview]').click()"); pg.wait_for_timeout(1200)   # after the chart's morph
        box = pg.locator('#proj-svg svg').bounding_box(); pg.mouse.move(box['x'] + box['width'] * 0.6, box['y'] + box['height'] * 0.5); pg.wait_for_timeout(100)
        ph = pg.evaluate("()=>{ const ov=document.querySelector('#proj-chart .phov'); return [!ov.hidden, ov.querySelector('.ph-box').textContent, getComputedStyle(ov.querySelector('.ph-dot.g')).left]; }")
        if not ph[0] or 'Total' not in ph[1] or ph[2] in ('auto', '0px'): fails += 1; print('projection hover', ph)
        pg.mouse.move(5, 5)
        # Estonian
        pg.evaluate("()=>{ document.querySelector('.langtabs [data-lang=et]').click(); document.querySelector('.viewtabs [data-view=progress]').click(); }"); pg.wait_for_timeout(300)
        et = pg.evaluate("()=>[document.querySelector('#path-card .lbl').textContent, document.getElementById('path-ret').textContent, document.querySelector('#pathbtns [data-span=\"5\"]').textContent, document.getElementById('path-svg').getAttribute('aria-label'), document.getElementById('path-tag').textContent]")
        if et[:3] != ['Sinu teekond', 'Pension', '5a'] or not et[3].startswith('Sinu teekond') or not et[4].startswith('kuni'): fails += 1; print('Estonian', et)
        pg.set_viewport_size({'width': 320, 'height': 900}); pg.wait_for_timeout(300)   # "Pension 65-aastaselt" keeps the age and the word together on a narrow phone
        one = pg.evaluate("""()=>{ const s=[...document.querySelectorAll('#path-list .k span')].find(x=>x.textContent.endsWith('-aastaselt')); if(!s) return null;
                 const r=document.createRange(); r.selectNodeContents(s); return new Set([...r.getClientRects()].map(x=>Math.round(x.top))).size; }""")
        if one != 1: fails += 1; print('the retirement age broke across lines', one)
        pg.set_viewport_size({'width': 1300, 'height': 900})
        # a renamed title is kept, in both languages; the default one follows the language
        ren = pg.evaluate("()=>{ state.text.titlePath='Where I\\'m heading'; refreshAll(); const a=document.querySelector('#path-card .lbl').textContent; state.text.titlePath=DEFAULTS.text.titlePath; refreshAll(); return [a, document.querySelector('#path-card .lbl').textContent]; }")
        if ren != ["Where I'm heading", 'Sinu teekond']: fails += 1; print('renaming Your path', ren)
        pg.evaluate("document.querySelector('.langtabs [data-lang=en]').click()")
        # the chips above the cards: inflation and loan payoffs, for the whole page
        pg.evaluate("()=>document.querySelector('.pctrl [data-for*=debtTargets]').click()"); pg.wait_for_timeout(100)
        if pg.evaluate("state.enableDebtTargets"): fails += 1; print('the Loan payoffs chip did not switch them off')
        pg.evaluate("()=>document.querySelector('.pctrl [data-for*=debtTargets]').click()")
        # After tax sits right after After inflation, as on the Projection, and is the same switch
        order = pg.evaluate("[...document.querySelectorAll('.pctrl .chip')].map(b=>b.textContent.replace(/[0-9.,%]+ /,''))")
        before = pg.evaluate("state.enableProjNet"); pg.evaluate("()=>document.querySelector('.pctrl [data-for*=projNet]').click()"); pg.wait_for_timeout(900)
        on = pg.evaluate("[state.enableProjNet, document.querySelector('#yrbtns') && document.querySelector('.projctrl [data-for*=projNet], .card [data-for*=projNet]').getAttribute('aria-pressed'), document.getElementById('path-tag').textContent, document.getElementById('path-note').textContent]")
        pg.evaluate("()=>document.querySelector('.pctrl [data-for*=projNet]').click()")
        if order[:2] != ['After inflation', 'After tax'] or on[0] == before or on[1] != 'true' or 'after tax' not in on[2] or 'only what you take out' not in on[3]: fails += 1; print('After tax on Progress', order, on)
        # the hover box closes when the chart redraws (here: inflation switched off), instead of showing the old numbers
        box = pg.locator('#path-svg svg').bounding_box(); pg.mouse.move(box['x'] + box['width'] * 0.4, box['y'] + box['height'] * 0.5); pg.wait_for_timeout(100)
        pg.focus('.pctrl .inflchip'); pg.keyboard.press('Enter'); pg.wait_for_timeout(200)
        if not pg.evaluate("document.querySelector('#path-chart .phov').hidden"): fails += 1; print('the hover box stayed open after the chart redrew')
        pg.keyboard.press('Enter'); pg.mouse.move(5, 5)
        # a target's dot and row light up while the pointer is at its month anywhere on the chart, not only on the dot, and go out when it leaves
        span = pg.evaluate("()=>{ const was=pathSpan; state=normalize({gross:4000, birthYear:1990, expenses:1500, accounts:[{name:'A', amount:20000, yield:0}], targets:[{name:'', kind:'networth', amount:100000}]}); pathSpan='30'; refreshAll(); return was; }")
        dot = pg.locator('#path-svg .pdot-ms').first.bounding_box(); box = pg.locator('#path-svg svg').bounding_box()
        lit = lambda: sorted(pg.evaluate("[...document.querySelectorAll('#path-card .on')].map(e=>e.tagName.toLowerCase())"))
        pg.mouse.move(dot['x'] + dot['width'] / 2, box['y'] + 10); pg.wait_for_timeout(100); above = lit()
        pg.mouse.move(box['x'] + box['width'] - 20, box['y'] + 10); pg.wait_for_timeout(100); away = lit()
        pg.mouse.move(dot['x'] + dot['width'] / 2, box['y'] + 10); pg.wait_for_timeout(100); pg.mouse.move(5, 5); pg.wait_for_timeout(100); left = lit()
        pg.locator('#path-list .row').first.hover(); pg.mouse.down(); pg.mouse.up(); pg.wait_for_timeout(100); pressed = lit(); pg.mouse.move(5, 5)   # pressing its row keeps it lit
        if above != ['circle', 'div'] or away or left or pressed != ['circle', 'div']: fails += 1; print('a target lit up (above its dot, far from it, after leaving the chart, its row pressed):', above, away, left, pressed)
        pg.evaluate("a=>{ state=normalize(a[0]); pathSpan=a[1]; refreshAll(); }", [s, span])
        # a long name wraps, its date stays on one line; the note only names the kinds of dots there are
        s2 = json.loads(json.dumps(s)); s2['targets'] = [{'name': 'Net worth goal before we move to the countryside house, someday soon', 'kind': 'networth', 'amount': 150000}]
        s2.update(enableDebtTargets=False, birthYear=None)
        d = pg.evaluate("""s=>{ state=normalize(s); refreshAll(); const v=document.querySelector('#path-list .row .v'), r=document.createRange(); r.selectNodeContents(v);
                 return [new Set([...r.getClientRects()].map(x=>Math.round(x.top))).size===1, document.getElementById('path-note').textContent]; }""", s2)
        if not d[0] or 'dots on the white line are your targets.' not in d[1] or 'loan' in d[1].split('dots on the white line')[1] or 'Dimmed' in d[1]: fails += 1; print('long name or note', d)
        # only loans: nothing drawn above €0
        o = pg.evaluate("""()=>{ state=normalize({debts:[{name:'Study',balance:20000,rtype:'fixed',rate:4,margin:0,payment:200,asset:0}]}); refreshAll();
                 return [...document.querySelectorAll('#path-svg text.axl')].map(e=>e.textContent).filter(x=>x.startsWith('€') && x!=='€0'); }""")
        if o: fails += 1; print('only loans, but labels above €0:', o)
        # a loan without a payment stays at today's balance, and the card says so
        o = pg.evaluate("""()=>{ state=normalize({debts:[{name:'Mortgage',balance:200000,rtype:'fixed',rate:4,margin:0,payment:0,asset:0}], accounts:[{name:'A',amount:5000,yield:0}]}); pathSpan='30'; refreshAll();
                 const h=document.getElementById('path-hint'); return [Math.round(pathHover.pts[360].debt*inflAfter(360)), h.style.display!=='none' && h.textContent]; }""")
        if o[0] != 200000 or not o[1] or 'Mortgage has no monthly payment' not in o[1]: fails += 1; print('loan without a payment', o)
        pg.evaluate("s=>{ state=normalize(s); refreshAll(); }", s)
        # 3. widths: no sideways scrolling on phones; every zoom label has the same room around it, the first and last too
        GAPS = """id=>{ const bar=document.getElementById(id), br=bar.getBoundingClientRect(), tx=b=>{ const r=document.createRange(); r.selectNodeContents(b); return r.getBoundingClientRect(); };
                 const bs=[...bar.querySelectorAll('button')].filter(b=>!b.hidden); return [tx(bs[0]).left-br.left, br.right-tx(bs[bs.length-1]).right,
                 ...bs.map(b=>{ const r=b.getBoundingClientRect(), x=tx(b); return Math.abs((x.left-r.left)-(r.right-x.right)); })]; }"""
        for w, lang in ((320, 'en'), (320, 'et'), (390, 'en'), (700, 'en'), (1300, 'en'), (1300, 'et')):
            pg.evaluate("l=>document.querySelector('.langtabs [data-lang='+l+']').click()", lang)
            pg.set_viewport_size({'width': w, 'height': 900}); pg.wait_for_timeout(300)
            g = pg.evaluate(GAPS, 'pathbtns')
            if abs(g[0] - g[1]) > 1.5 or max(g[2:]) > 1.5: fails += 1; print('zoom labels unevenly spaced', w, lang, [round(x, 1) for x in g])
            o = pg.evaluate("""()=>{ const c=document.getElementById('path-card').getBoundingClientRect(), btns=[...document.querySelectorAll('#pathbtns button')].filter(b=>!b.hidden);
                     return {page:document.documentElement.scrollWidth>innerWidth, svg:document.querySelector('#path-svg svg').getBoundingClientRect().right>c.right+0.5, clipped:btns.filter(b=>b.scrollWidth>b.clientWidth+1).map(b=>b.textContent)}; }""")
            if o['page'] or o['svg'] or o['clipped']: fails += 1; print('width', w, o)
        pg.evaluate("document.querySelector('.langtabs [data-lang=en]').click()")
        pg.evaluate("document.querySelector('.viewtabs [data-view=overview]').click()"); pg.wait_for_timeout(300)   # the Projection's buttons share the style
        g = pg.evaluate(GAPS, 'yrbtns')
        if abs(g[0] - g[1]) > 1.5 or max(g[2:]) > 1.5: fails += 1; print('projection labels unevenly spaced', [round(x, 1) for x in g])
        pg.evaluate("document.querySelector('.viewtabs [data-view=progress]').click()")
        pg.set_viewport_size({'width': 1900, 'height': 900}); pg.click('#wideBtn'); pg.wait_for_timeout(400)
        # wide layout: the chips and Your path full width; Targets on the left, Retirement with History under it on the right
        wd = pg.evaluate("""()=>{ const v=document.getElementById('view-progress').getBoundingClientRect(), r=s=>document.querySelector(s).getBoundingClientRect(), wid=s=>Math.round(r(s).width/v.width*100);
                 return [wid('#view-progress > .pctrl'), wid('#path-card'), wid('#targets-card'), wid('#retire-card'), wid('#history-card'),
                         r('#retire-card').left>r('#targets-card').right, Math.abs(r('#history-card').left-r('#retire-card').left)<1, r('#history-card').top>r('#retire-card').bottom, Math.abs(r('#targets-card').top-r('#retire-card').top)<1]; }""")
        if wd != [100, 100, 50, 50, 50, True, True, True, True]: fails += 1; print('wide layout (widths in % of the page, then placement)', wd)
        b.close()
    if errs: fails += 1; print('page errors:', errs[:3])
    finish('Your path', fails, f'{N} random users, the card and the widths' + (' all fine' if not fails else f': {fails} problems'))


if __name__ == '__main__':
    main()
