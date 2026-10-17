"""Target dates and the extra money a deadline needs, against an independent month-by-month model.

Net worth goals (with loans paid down and freed payments), FIRE goals that rise with inflation (with your own health
insurance only until pension age), invested-total and cash goals (cash grows by the part of the yearly surplus that isn't
invested, shrinks when the surplus is negative, and pays the loans after you retire), each followed month by month with
pensions and investments at their own fees and property bought with a loan keeping up with prices; paid-off loans'
payments split like the surplus between cash and investments; "put in" in today's money; deadlines worked out here, not
read from the page; and that the suggested extra EUR/month (a flat amount) really reaches a deadline while noticeably less
does not. The deadline line the card shows: early, just in time, the extra a month ("until you retire" when saving stops
first, never for one you track yourself), out of reach, passed, this month; FIRE without spending asks for it. Random
mixes of debts, fees, inflation, deposit growth, invested surplus shares and big numbers. On the cards: the surplus link
on a cash goal, the Annual surplus tile's split and its Change link, and old data where the surplus switch was on
becoming 100%.
Run: python tests/test_targets.py [number of users]"""
from playwright.sync_api import sync_playwright
import json, random, math, sys, datetime, calendar
from helpers import FIXTURES, PAGE, finish, fixture, launch, pick, watch_errors, import_file
from model import surplus_invested, savings, save_months, by_month, payout_tax, pension_age, payout_age
def eur(v):   # whole euros, a half away from zero
    n=int(math.floor(abs(v)+0.5)); return ('−' if v<0 and n else '')+'€{:,}'.format(n)
def months_label(m):   # "1y 2m"
    return ' '.join(x for x in (f'{m//12}y' if m//12 else '', f'{m%12}m' if m%12 else '') if x) or '0m'
def deadline_text(eta, need, due, by, stop, tracked=False):
    # what the card says about a deadline (`by`: "By Jun 2031") `due` months away: reached (nothing), early or just in time, or
    # the extra a month ("until you retire" when saving stops first, but not for a target you track yourself)
    if eta==0: return ''
    if due<0: return by+': passed'
    if due==0: return by+': this month'
    if eta<=due: return by+' · '+('~'+months_label(due-eta)+' early' if due-eta>=1 else 'just in time')
    if need==math.inf: return by+' · out of reach'
    return by+' · +'+eur(need)+('/mo until you retire would make it' if stop<due and not tracked else '/mo would make it')
def need_problem(n, makes):
    # the extra €/month for a deadline: enough, and noticeably less isn't; "out of reach" (infinity) only when nothing would do
    if n==math.inf: return 'says out of reach, but €1T a month makes it' if makes(1e12) else None
    if not makes(n): return 'does not make it'
    if n>1 and makes(n-max(1, n*0.001)): return 'is too high'   # within 0.1% (or €1) of the least that makes it
def main():
    random.seed(int(sys.argv[2]) if len(sys.argv)>2 else 7); N=int(sys.argv[1]) if len(sys.argv)>1 else 120
    with sync_playwright() as p:
        b=launch(p); pg=b.new_page(reduced_motion='reduce'); errs=watch_errors(pg, n=200)
        pg.goto(PAGE); pg.wait_for_timeout(300)
        base=fixture('example.json'); fails=0
        for k in range(N):
            s=json.loads(json.dumps(base)); big=k%5==0
            s.update(projReturn=pick(10,7,0,-5,15,random.uniform(-20,30)), projInflation=pick(2.5,0,5,-1,random.uniform(0,10)), projGrowth=pick(0,3,-5,random.uniform(0,10)),
                     enableProjSurplus=pick(True,False), projSurplusPct=pick(100,60,0,random.uniform(0,100)), enableProjFee=pick(True,False), projFee=pick(0,0.2,1.5), enableProjReal=pick(True,False), projYears=pick(10,20,40),
                     expenses=pick(1600,500,4000,9000), euribor=pick(2.6,0,4), birthYear=pick(0,1958,1965,1980,1990,2000), retireAge=pick(65,60,70),   # 1958: already a pensioner
                     enableProjNet=pick(True,False), invDeposits=pick(0,0,20000), payoutYears=pick(20,10,30))
            for a in s['accounts']: a['yield']=pick(a['yield'],0,4.5,-0.5)   # cash earns its interest after tax
            s['debts']=[{'name':'d'+str(j), 'balance':pick(5000,150000,1e6 if big else 300000), 'rtype':pick('fixed','euribor'), 'rate':pick(0,3,8,25), 'margin':pick(0.5,2), 'payment':pick(0,100,950,3000), 'asset':pick(0,200000)} for j in range(random.randint(0,3))]
            if big: s['gross']=pick(1e5,1e7); s['etfMonthly']=pick(1e5,1e7)
            due=random.randint(6,400); dy=datetime.date.today().year+due//12+1; mon=random.randint(1,12)   # any month of the deadline year
            s['targets']=[{'name':'nw','kind':'networth','amount':pick(1e5,5e5,2e6,1e8 if big else 3e6)}, {'name':'fire','kind':'fire','amount':0,'rate':pick(4,3.5),'spend':pick(0,30000,60000),'health':pick('yes','no')},
                          {'name':'inv','kind':'invested','amount':pick(1e5,1e6)}, {'name':'cash','kind':'cash','amount':pick(5000,30000,200000)},
                          {'name':'own','kind':'custom','amount':pick(5000,50000),'current':pick(0,2000,60000)}]   # tracked by you
            for t in s['targets']: t['dueMon']=f'{mon:02d}'; t['dueYear']=str(dy)
            r=pg.evaluate("""s=>{ state=normalize(s); refreshAll(); const c=compute(), R=projRate(c), pi=projInputs(c);
                const st=state.targets.map(t=>{ const x=targetStatus(t,c), due=dueMonths(t); return {kind:t.kind, eta:x.eta, goal:x.goal, due, need: due>0 ? x.need(due) : null}; });
                const rows=[...document.querySelectorAll('#tgt-list .tgtitem:not(.debtt)')], shown=rows.map(e=>e.querySelector('.teta').textContent), dl=rows.map(e=>e.querySelector('.tdr').textContent);
                const sim=simulate(pi.start, pi.monthly, R.net, Math.max(1,Math.round(state.projYears||20)), state.projGrowth, state.enableProjReal?state.projInflation:0);
                return {st, net:R.net, netPen:projRate(c,null,'pen').net, netInv:projRate(c,null,'inv').net, start:pi.start, monthly:pi.monthly, c:{debtAssets:c.debtAssets, pension:c.pension, penMonthly:c.penMonthly, buffer:c.buffer, networth:c.networth, surplus:c.surplus, etfVal:c.etfVal, invValue:c.invValue, etfMonthly:c.etfMonthly, invMonthly:c.invMonthly, expenses:c.expenses},
                        debts:c.debtList.filter(d=>(+d.balance||0)>0).map(d=>({B:+d.balance, r:(+d.rate||0)/1200, P:Math.max(0,+d.payment||0)})), st8:{...state},
                        putR:sim.putR, shown, dl}; }""", s)
            st=r['st8']; g=st['projGrowth']; c=r['c']; net_p, net_i = r['netPen'], r['netInv']   # pensions and investments, each after its own fees
            infl=1+(st['projInflation'] if st['enableProjReal'] else 0)/100
            # the deadline, worked out here: from this month to that month of the deadline year
            today=datetime.date.today(); due0=(dy-today.year)*12+mon-today.month; lbl=f'By {calendar.month_abbr[mon]} {dy}'
            if any(x['due']!=due0 for x in r['st']): fails+=1; print(k,'deadline months',[x['due'] for x in r['st']],'want',due0)
            # saving stops when you retire; cash, loans and paid-off loans' payments month by month (after retiring, payments come out of cash)
            stop=save_months(st, today.year)
            cash, owed, inv_f, inv_put = savings(r['debts'], 800, st, c['surplus'], net_i, c['buffer'], stop)
            i0=c['etfVal']+c['invValue']; mo=c['etfMonthly']+c['invMonthly']+surplus_invested(st, c['surplus'])
            pen_v,_=by_month(c['pension'], c['penMonthly'], net_p, 720, g, stop); inv_v, inv_p = by_month(i0, mo, net_i, 720, g, stop)
            one_v, one_p = by_month(0, 1, net_i, 720, 0, stop)   # €1 more a month into investments, a flat amount
            other=c['networth']-r['start']-c['buffer']+owed[0]   # property; what was bought with a loan keeps up with prices
            prop=lambda i: other+c['debtAssets']*(infl**(i/12)-1)
            # health insurance (FIRE): your own, €272/mo in 2026, only while you'd be below pension age (birthday taken as mid-year)
            t=s['targets'][1]; by=st['birthYear']; spa=pension_age(st)
            health=lambda i: 272*12 if t['health']=='yes' and (not by or today.year-by+(today.month-1-6+i)/12<spa) else 0
            goal=lambda i: ((t['spend'] if t['spend']>0 else c['expenses']*12)+health(i))/(t['rate']/100)
            nwT=s['targets'][0]['amount']; A2=s['targets'][2]['amount']; A3=s['targets'][3]['amount']
            first=lambda v, G: next((i for i in range(721) if v[i]>=G(i)*infl**(i/12)), math.inf)
            const=lambda a: (lambda i: a)
            # what each target follows, with `e` more a month (into investments; for the cash buffer, into cash)
            if not st['enableProjNet']:
                series={'networth':(lambda e=0: [pen_v[i]+inv_v[i]+e*one_v[i]+inv_f[i]+prop(i)+cash[i]-owed[i] for i in range(721)], const(nwT)),
                        'fire':(lambda e=0: [inv_v[i]+e*one_v[i]+inv_f[i] for i in range(721)], goal),
                        'invested':(lambda e=0: [pen_v[i]+inv_v[i]+e*one_v[i]+inv_f[i] for i in range(721)], const(A2))}
            else:   # After tax: what you'd keep if you cashed out each month; pensions lose the payout tax (as Retirement pays them out), investments income tax on gains above what went in
                pt=payout_tax(payout_age(st), st['payoutYears'], st['taxRate'], pension_age(st))/100; inc=st['taxRate']/100
                def kept(e, inv_only=False):
                    out=[]
                    for i in range(721):
                        val=inv_v[i]+e*one_v[i]+inv_f[i]; dep=(st['invDeposits'] if st['invDeposits']>0 else i0)+(inv_p[i]-i0)+e*one_p[i]+inv_put[i]
                        out.append(val-inc*max(0,val-dep)+(0 if inv_only else pen_v[i]*(1-pt)))
                    return out
                series={'networth':(lambda e=0: [v+prop(i)+cash[i]-owed[i] for i,v in enumerate(kept(e))], const(nwT)), 'fire':(lambda e=0: kept(e,True), goal), 'invested':(kept, const(A2))}
            for x,dl in zip(r['st'][:3], r['dl']):
                vals,G=series[x['kind']]
                if x['kind']=='fire' and goal(0)<=0: continue
                want=first(vals(0), G); got=x['eta']; got=math.inf if got is None or got>1e300 else got
                if want!=got: fails+=1; print(k,x['kind'],'eta',got,'want',want,'after tax' if st['enableProjNet'] else '')
                if dl!=deadline_text(want, x['need'], due0, lbl, stop): fails+=1; print(k,x['kind'],'deadline line',repr(dl),'want',repr(deadline_text(want, x['need'], due0, lbl, stop)))
                if x['kind']=='fire' and want<720 and abs(x['goal']-goal(want if want>0 else 0))>0.01: fails+=1; print(k,'FIRE goal on the card',x['goal'],'want',goal(want))   # as it is when you'd reach it
                if x['need'] is not None and due0>0 and want>due0:   # the extra €/month for the deadline really makes it, and noticeably less doesn't
                    d=min(due0,720); makes=lambda e, vals=vals, G=G, d=d: (lambda a: any(a[i]>=G(i)*infl**(i/12)-0.01 for i in range(0,d+1)))(vals(e))
                    bad=need_problem(x['need'], makes)
                    if bad: fails+=1; print(k,x['kind'],'need',x['need'],bad)
            # what the card says: each date as "≈ Mon YYYY", from this month plus the months to go
            for x,txt in zip(r['st'], r['shown']):
                e=x['eta']
                if e is not None and 0<e<720:
                    mm=today.month-1+e; label='≈ '+calendar.month_abbr[mm%12+1]+' '+str(today.year+mm//12)
                    if not txt.startswith(label): fails+=1; print(k,x['kind'],'card shows',repr(txt[:24]),'want',label)
            # cash buffer: earns interest, grows by the part of the yearly surplus that isn't invested (a negative one always counts)
            # and by the same part of paid-off loans' payments, until you retire; the goal rises with inflation when that's on
            want=first(cash, const(A3)); got=r['st'][3]['eta']; got=math.inf if got is None or got>1e300 else got
            if want!=got: fails+=1; print(k,'cash eta',got,'want',want)
            if r['dl'][3]!=deadline_text(want, r['st'][3]['need'], due0, lbl, stop): fails+=1; print(k,'cash deadline line',repr(r['dl'][3]),'want',repr(deadline_text(want, r['st'][3]['need'], due0, lbl, stop)))
            # a target you track yourself: what's left, spread over the months to the deadline (the goal rising with prices)
            o=s['targets'][4]; left=o['amount']*infl**(due0/12)-o['current']
            want_own='' if o['current']>=o['amount'] else deadline_text(math.inf, max(0, left/due0), due0, lbl, stop, True)   # no date of its own
            if r['dl'][4]!=want_own: fails+=1; print(k,'own target deadline line',repr(r['dl'][4]),'want',repr(want_own))
            x=r['st'][3]
            if x['need'] is not None and due0>0:
                n=x['need']; d=min(due0,720)   # reached in any month up to the deadline, with the extra put in month by month (cash below zero earns nothing)
                makes=lambda e: (lambda cs: any(cs[i]>=A3*infl**(i/12)-0.01 for i in range(0,d+1)))(savings(r['debts'], d, st, c['surplus'], net_i, c['buffer'], stop, e)[0])
                bad=need_problem(n, makes)
                if bad: fails+=1; print(k,'cash need',n,bad)
            # put in, today's money when shown so
            yrs=max(1,round(st['projYears'])); inf=st['projInflation'] if st['enableProjReal'] else 0
            m=r['monthly']; tot=r['start']; d=1.0
            for i in range(1,yrs*12+1):
                d*=(1+inf/100)**(1/12); tot+=(m if i<=stop else 0)/d
                if i%12==0: m*=1+g/100
            if abs(tot-r['putR'])>max(0.01,abs(tot)*1e-9): fails+=1; print(k,'put in',r['putR'],'want',tot)
        # the card: an emergency fund that can't grow because all of the surplus is invested says so, with a link to that setting
        pg.set_viewport_size({'width':1300,'height':900})
        for share, lang in ((100,'en'), (100,'et'), (60,'en'), (0,'en')):
            pg.evaluate("l=>document.querySelector('.langtabs [data-lang='+l+']').click()", lang); invest=share>=100
            s=json.loads(json.dumps(base)); s.update(enableProjSurplus=share>0, projSurplusPct=share or 100, targets=[{'name':'Rainy day','kind':'cash','amount':10**7,'dueMon':'','dueYear':'','rate':4,'current':0,'spend':0}])
            pg.evaluate("s=>{ document.querySelector('.viewtabs [data-view=progress]').click(); state=normalize(s); save(); refreshAll(); }", s); pg.wait_for_timeout(900)   # numbers finish animating
            row=pg.evaluate("""()=>{ const r=document.querySelector('#tgt-list .tgtitem'), a=r.querySelector('.tlink'), c=compute(), t=targetStatus(state.targets[0], c);
              return {link:!a.hidden && !!a.getClientRects().length, text:r.querySelector('.teta').textContent, val:r.querySelector('.tval').textContent, want:eurS(t.cur)+' of '+eurS(t.goal), pct:r.querySelector('.tpct').textContent, sur:c.surplus}; }""")
            if row['val']!=row['want'].replace(' of ', ' of ' if lang=='en' else ' / ') or row['pct']!='0%': fails+=1; print('target row shows', row['val'], row['pct'], 'want', row['want'])
            if invest and row['sur']>=0:
                if not row['link'] or ('your surplus is invested' if lang=='en' else 'ülejääk läheb investeerimisse') not in row['text']: fails+=1; print('invested surplus: no link', lang, row)
                pg.click('#tgt-list .tlink'); pg.wait_for_timeout(600)
                if pg.evaluate("[document.querySelector('.esec[data-sec=savings]').open, document.activeElement.id]")!=[True,'surplusRange']: fails+=1; print('the link did not open the surplus setting')
            if not invest and row['link']: fails+=1; print('link shown although not all of the surplus is invested', share)
            # the Annual surplus tile: what share is invested, and the same split as under the setting
            tile=pg.evaluate("()=>[document.getElementById('surplus-sub').textContent, document.querySelector('#sur-split > span').textContent, document.getElementById('surplus-hint').textContent, compute().surplus]")
            sub={100:{'en':'invested / year','et':'investeeritud / aastas'}, 60:{'en':'60% invested / year'}, 0:{'en':'unassigned / year'}}[share][lang]
            y=round(tile[3]); inv=math.floor(y*share/100+0.5); eu=lambda v: '€{:,}'.format(v)   # whole euros that add up to the tile
            words={100:eu(y), 60:eu(inv)+(' a year goes to your investments and ')+eu(y-inv), 0:eu(y)}[share]
            if y<=0 or tile[0]!=sub or tile[1]!=tile[2] or words not in tile[1]: fails+=1; print('surplus tile', share, lang, tile, 'want', sub, words)
        # spending more than you earn: nothing is invested, whatever the share, and the shortfall comes out of cash
        s=json.loads(json.dumps(base)); s.update(enableProjSurplus=True, projSurplusPct=60, expenses=20000)
        neg=pg.evaluate("s=>{ state=normalize(s); refreshAll(); return [compute().surplus, document.getElementById('surplus-sub').textContent, document.getElementById('surplus-hint').textContent, surplusInvested(compute())]; }", s)
        if not (neg[0]<0 and neg[1]=='short / year' and neg[2].startswith('A shortfall comes out of your cash') and neg[3]==0): fails+=1; print('negative surplus tile', neg)
        # the tile's Change link opens the setting with the cursor in it
        pg.evaluate("()=>{ document.querySelector('.viewtabs [data-view=overview]').click(); document.querySelector('.esec[data-sec=savings]').open=false; document.getElementById('surplus-det').open=true; }")
        pg.click('#sur-change'); pg.wait_for_timeout(600)
        if pg.evaluate("[document.querySelector('.esec[data-sec=savings]').open, document.activeElement.id, document.getElementById('surplus-det').open]")!=[True,'surplusRange',True]: fails+=1; print('Change did not open the surplus setting with the tile still open')
        pg.click('#surplusRange'); pg.wait_for_timeout(200)   # using the setting keeps the tile open, so its split can be watched
        if not pg.evaluate("document.getElementById('surplus-det').open"): fails+=1; print('the tile closed when the setting was used')
        pg.mouse.click(5, 5); pg.wait_for_timeout(700)   # a click elsewhere on the page closes it (after its closing animation)
        if pg.evaluate("document.getElementById('surplus-det').open"): fails+=1; print('the tile stayed open after a click elsewhere')
        # older backups, imported: the surplus switch on means all of it (v1.1.6 file), off means none (v1.1.0 file); the slider's value is the cash share
        for name, want in (('backup-v1.1.6.json', [100,'0']), ('backup-v1.1.0.json', [0,'100'])):
            import_file(pg, FIXTURES/name)
            got=pg.evaluate("()=>[surplusPct(), document.getElementById('surplusRange').value]")
            if got!=want: fails+=1; print('old backup', name, 'gave', got, 'want', want)
        # a payment that fits the balance exactly takes exactly that many months (not one more from rounding)
        po=pg.evaluate("[payoff(1199.88,0,99.99).months, payoff(64723.26,0,10787.21).months, payoff(1200,0,100).months, payoff(1200.01,0,100).months]")
        if po!=[12,6,12,13]: fails+=1; print('payoff months', po, 'want [12, 6, 12, 13]')
        # loans as "paid off" targets: details on the left, the date on the right; a row reused for a goal loses the debt's red
        s=json.loads(json.dumps(base)); s.update(enableDebtTargets=True, targets=[], debts=[{'name':'Car','balance':5000,'rtype':'fixed','rate':6,'margin':0,'payment':0,'asset':0}])
        pg.evaluate("s=>{ state=normalize(s); save(); refreshAll(); }", s); pg.wait_for_timeout(900)
        d=pg.evaluate("()=>{ const r=document.querySelector('#tgt-list .tgtitem'); return {left:r.querySelector('.teta').textContent, warn:r.querySelector('.tdr').classList.contains('warn')}; }")
        if not d['left'].startswith('€5,000') or not d['warn']: fails+=1; print('debt target row', d)
        s['targets']=[{'name':'Rainy day','kind':'cash','amount':10**7,'dueMon':'','dueYear':'','rate':4,'current':0,'spend':0}]; s['debts']=[]
        pg.evaluate("s=>{ state=normalize(s); save(); refreshAll(); }", s); pg.wait_for_timeout(900)
        g=pg.evaluate("()=>{ const r=document.querySelector('#tgt-list .tgtitem'); return {warn:r.querySelector('.tdr').classList.contains('warn'), tip:r.querySelector('.dname').getAttribute('data-tip')}; }")
        if g['warn'] or not g['tip']: fails+=1; print('goal row kept debt state', g)
        s['targets']=[]; s['debts']=[{'name':'Car','balance':5000,'rtype':'fixed','rate':6,'margin':0,'payment':200,'asset':0}]   # and back: the debt row drops the goal's details
        pg.evaluate("s=>{ state=normalize(s); save(); refreshAll(); }", s); pg.wait_for_timeout(900)
        n=pg.evaluate("()=>{ const e=document.querySelector('#tgt-list .tgtitem .dname'); return ['data-tip','aria-description','tabindex'].filter(a=>e.hasAttribute(a)); }")
        if n: fails+=1; print('debt row kept the goal details', n)
        # "Try other numbers": an invested target follows only the tried numbers, without your real loans' freed payments on top
        tr={**s, 'enableProjCustom':True, 'projStart':20000, 'projMonthly':500, 'enableProjSurplus':True, 'projSurplusPct':100, 'enableProjReal':False, 'projGrowth':0, 'birthYear':0,
            'debts':[{'name':'car','balance':5000,'rtype':'fixed','rate':5,'margin':0,'payment':900,'asset':0}],
            'targets':[{'name':'inv','kind':'invested','amount':300000,'rate':4,'current':0,'spend':0,'dueMon':'','dueYear':'','health':'no'}]}
        q=pg.evaluate("""s=>{ state=normalize(s); refreshAll(); const c=compute(); return {eta:targetStatus(state.targets[0], c).eta, net:projRate(c).net}; }""", tr)
        v,_=by_month(20000, 500, q['net'], 720); want=next((i for i in range(721) if v[i]>=300000), math.inf)
        if q['eta']!=want: fails+=1; print('Try other numbers: invested target', q['eta'], 'want', want)
        # FIRE: your own health insurance only until pension age, so none for someone already past it
        g=pg.evaluate("""s=>{ state=normalize(s); refreshAll(); return targetStatus(state.targets[0], compute()).goal; }""",
                      {**s, 'birthYear':1955, 'targets':[{'name':'','kind':'fire','amount':0,'rate':4,'current':0,'spend':30000,'health':'yes','dueMon':'','dueYear':''}]})
        if abs(g-750000)>0.01: fails+=1; print('FIRE past pension age still counts health insurance', g)
        # the deadline line in set cases (English): passed, this month, just in time, a month early; one you track yourself has no
        # deposits that stop when you retire; FIRE with no spending asks for it
        today=datetime.date.today()
        def at(m): mm=today.month-1+m; return {'dueMon':f'{mm%12+1:02d}', 'dueYear':str(today.year+mm//12)}
        cash=lambda **d: {'name':'c','kind':'cash','amount':30000,'rate':4,'current':0,'spend':0,'health':'no','dueMon':'','dueYear':'', **d}
        b2={**base, 'targets':[], 'debts':[], 'enableProjReal':False, 'enableProjSurplus':False, 'birthYear':1990, 'retireAge':65}
        pg.evaluate("l=>document.querySelector('.langtabs [data-lang='+l+']').click()", 'en')
        eta=pg.evaluate("s=>{ state=normalize(s); refreshAll(); return targetStatus(state.targets[0], compute()).eta; }", {**b2, 'targets':[cash()]})
        retired={**b2, 'birthYear':1950, 'retireAge':60}   # retired already: nothing new goes in
        for name, st8, want in (('passed', {**b2, 'targets':[cash(**at(-2))]}, 'By '+calendar.month_abbr[(today.month-3)%12+1]+' '+str(today.year-(1 if today.month<3 else 0))+': passed'),
                                ('this month', {**b2, 'targets':[cash(**at(0))]}, 'By '+calendar.month_abbr[today.month]+' '+str(today.year)+': this month'),
                                ('just in time', {**b2, 'targets':[cash(**at(eta))]}, 'just in time'), ('a month early', {**b2, 'targets':[cash(**at(eta+1))]}, '~1m early'),
                                ('tracked by you', {**retired, 'targets':[{**cash(**at(12)), 'kind':'custom', 'amount':13000, 'current':1000}]}, '+€1,000/mo would make it'),
                                ('cash, retiring first', {**b2, 'birthYear':today.year-64, 'targets':[cash(**at(24), amount=10**6)]}, '/mo until you retire would make it')):   # 65 within 6-17 months
            got=pg.evaluate("s=>{ state=normalize(s); refreshAll(); return document.querySelector('#tgt-list .tgtitem .tdr').textContent; }", st8)
            if not (0<eta<400) or not got.endswith(want): fails+=1; print('deadline line,', name, repr(got), 'want it to end with', repr(want))
        got=pg.evaluate("s=>{ state=normalize(s); refreshAll(); return document.querySelector('#tgt-list .tgtitem .teta').textContent; }",
                        {**b2, 'expenses':0, 'expenseItems':[], 'targets':[{**cash(), 'kind':'fire', 'health':'yes'}]})   # not health insurance alone as the goal
        if got!='Enter your yearly spending': fails+=1; print('FIRE without spending says', repr(got))
        # FIRE between its two goals: €620k is past the goal once your own health insurance stops (in 2 years), not today's
        fire=lambda **d: {**cash(), 'kind':'fire', 'amount':0, 'spend':24000, 'health':'yes', **d}
        st8={**b2, 'birthYear':today.year-63, 'projReturn':0, 'enableProjReal':False, 'etfs':[{'name':'E','weight':100,'value':620000,'monthly':0,'fee':0}], 'investments':[],
             'etfMonthly':0, 'enableEtfPlan':False, 'enableProjSurplus':False, 'targets':[fire()]}
        q=pg.evaluate("s=>{ state=normalize(s); refreshAll(); const r=document.querySelector('#tgt-list .tgtitem'); return [r.classList.contains('done'), r.querySelector('.tpct').textContent, targetStatus(state.targets[0], compute()).eta]; }", st8)
        if q[0] or q[1]=='100%' or not 0<q[2]<40: fails+=1; print('FIRE between its goals shows', q)
        # "Try other numbers" doesn't move FIRE: it follows your own investments
        e=[pg.evaluate("s=>{ state=normalize(s); refreshAll(); return targetStatus(state.targets[0], compute()).eta; }", {**st8, 'birthYear':1990, 'enableProjCustom':on, 'projStart':2e6, 'projMonthly':5000}) for on in (False, True)]
        if e[0]!=e[1]: fails+=1; print('FIRE with Try other numbers on:', e)
        # 50 FIRE targets: health insurance mustn't make a change slower. Its pension-age month is worked out once per target, not
        # for every month of every target; counted by how often the targets read the clock (a count, so a slow machine can't matter)
        reads=pg.evaluate("""()=>{ const run=h=>{ state=normalize({birthYear:1980, gross:3000, etfMonthly:500, etfs:[{name:'A', value:20000, weight:100}],
            targets:Array.from({length:50}, (_,i)=>({name:'f'+i, kind:'fire', spend:20000+i*100, rate:4, health:h}))}); const c=compute(); moneyByMonth(c, 720, {real:true});
            const D=Date; let n=0; window.Date=new Proxy(D, {construct:(T,a)=>{ n++; return new T(...a); }, apply:(T,th,a)=>{ n++; return T(...a); }});
            try{ state.targets.forEach(t=>targetStatus(t,c)); } finally{ window.Date=D; } return n; };
          return [run('yes'), run('no')]; }""")
        if reads[0]-reads[1]>200: fails+=1; print('50 FIRE targets with health insurance read the clock', reads[0], 'times, without it', reads[1])
        print('page errors:', errs[:3] or 'none')
        finish('targets', fails or errs, f"{N} random users: {'all match' if not fails else str(fails)+' differences'}")

if __name__=='__main__':
    main()
