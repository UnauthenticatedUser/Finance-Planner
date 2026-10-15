"""Target dates and the extra money a deadline needs, against an independent month-by-month model.

Net worth goals (with loans paid down and freed payments), FIRE goals that rise with inflation, invested-total and
cash goals (cash grows by the part of the yearly surplus that isn't invested, and shrinks when the surplus is negative), with paid-off loans'
payments split like the surplus between cash and investments, "put in" in today's money,
and that the suggested extra EUR/month really reaches a deadline while noticeably less does not. Random mixes of debts, fees, inflation,
deposit growth, invested surplus shares and big numbers. On the cards: the surplus link on a cash goal, the Annual surplus tile's split and
its Change link, and old data where the surplus switch was on becoming 100%.
Run: python tests/test_targets.py [number of users]"""
from playwright.sync_api import sync_playwright
import json, random, math, sys, datetime
from helpers import PAGE, FIXTURES, fixture, finish, launch
from model import months_to, surplus_invested, savings, save_months, by_month, payout_tax
def pick(*a): return random.choice(a)
def main():
    random.seed(int(sys.argv[2]) if len(sys.argv)>2 else 7); N=int(sys.argv[1]) if len(sys.argv)>1 else 120
    with sync_playwright() as p:
        b=launch(p); pg=b.new_page(); errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)[:200]))
        pg.goto(PAGE); pg.wait_for_timeout(300)
        base=fixture('example.json'); fails=0
        for k in range(N):
            s=json.loads(json.dumps(base)); big=k%5==0
            s.update(projReturn=pick(10,7,0,-5,15,random.uniform(-20,30)), projInflation=pick(2.5,0,5,-1,random.uniform(0,10)), projGrowth=pick(0,3,-5,random.uniform(0,10)),
                     enableProjSurplus=pick(True,False), projSurplusPct=pick(100,60,0,random.uniform(0,100)), enableProjFee=pick(True,False), projFee=pick(0,0.2,1.5), enableProjReal=pick(True,False), projYears=pick(10,20,40),
                     expenses=pick(1600,500,4000,9000), euribor=pick(2.6,0,4), birthYear=pick(0,1965,1980,1990,2000), retireAge=pick(65,60,70),
                     enableProjNet=pick(True,False), invDeposits=pick(0,0,20000), payoutYears=pick(20,10,30))
            for a in s['accounts']: a['yield']=pick(a['yield'],0,4.5,-0.5)   # cash earns its interest after tax
            s['debts']=[{'name':'d'+str(j), 'balance':pick(5000,150000,1e6 if big else 300000), 'rtype':pick('fixed','euribor'), 'rate':pick(0,3,8,25), 'margin':pick(0.5,2), 'payment':pick(0,100,950,3000), 'asset':pick(0,200000)} for j in range(random.randint(0,3))]
            if big: s['gross']=pick(1e5,1e7); s['etfMonthly']=pick(1e5,1e7)
            due=random.randint(6,400); dy=datetime.date.today().year+due//12+1
            s['targets']=[{'name':'nw','kind':'networth','amount':pick(1e5,5e5,2e6,1e8 if big else 3e6)}, {'name':'fire','kind':'fire','amount':0,'rate':pick(4,3.5),'spend':pick(0,30000,60000),'health':pick('yes','no')},
                          {'name':'inv','kind':'invested','amount':pick(1e5,1e6)}, {'name':'cash','kind':'cash','amount':pick(5000,30000,200000)}]
            for t in s['targets']: t['dueMon']='06'; t['dueYear']=str(dy)
            r=pg.evaluate("""s=>{ state=normalize(s); refreshAll(); const c=compute(), R=projRate(c), pi=projInputs(c);
                const st=state.targets.map(t=>{ const x=targetStatus(t,c), due=dueMonths(t); return {kind:t.kind, eta:x.eta, goal:x.goal, due, need: due>0 ? x.need(due) : null}; });
                const sim=simulate(pi.start, pi.monthly, R.net, Math.max(1,Math.round(state.projYears||20)), state.projGrowth, state.enableProjReal?state.projInflation:0);
                return {st, net:R.net, start:pi.start, monthly:pi.monthly, c:{pension:c.pension, penMonthly:c.penMonthly, buffer:c.buffer, networth:c.networth, surplus:c.surplus, etfVal:c.etfVal, invValue:c.invValue, etfMonthly:c.etfMonthly, invMonthly:c.invMonthly, expenses:c.expenses},
                        debts:c.debtList.filter(d=>(+d.balance||0)>0).map(d=>({B:+d.balance, r:(+d.rate||0)/1200, P:Math.max(0,+d.payment||0)})), st8:{...state},
                        putR:sim.putR, put:sim.put, propsub:document.getElementById('proj-sub').textContent}; }""", s)
            st=r['st8']; net=r['net']; g=st['projGrowth']; c=r['c']
            infl=1+(st['projInflation'] if st['enableProjReal'] else 0)/100
            # saving stops when you retire; cash, loans and paid-off loans' payments month by month
            stop=save_months(st, datetime.date.today().year)
            cash, owed, inv_f, inv_put = savings(r['debts'], 800, st, c['surplus'], net, c['buffer'], stop)
            mt=lambda start, monthly, reach: months_to(start, monthly, net, g, reach, stop=stop)
            # net worth
            other=c['networth']-r['start']-c['buffer']+owed[0]
            nwT=s['targets'][0]['amount']
            def reach_nw():
                return lambda i,v: v+other+cash[i]-owed[i]+inv_f[i]>=nwT*infl**(i/12)
            want=mt(r['start'], r['monthly'], reach_nw())
            got=r['st'][0]['eta']; got=math.inf if got is None or got>1e300 else got
            if not st['enableProjNet'] and not (want==got or (abs(want-got)<=1 and want<math.inf)): fails+=1; print(k,'networth eta', got,'want',want)
            # FIRE
            t=s['targets'][1]; yearly=(t['spend'] if t['spend']>0 else c['expenses']*12)+(272*12 if t['health']=='yes' else 0); goal=yearly/(t['rate']/100); acc=c['etfVal']+c['invValue']   # health: own insurance before pension age, €272/mo in 2026
            mo=c['etfMonthly']+c['invMonthly']+surplus_invested(st, c['surplus']); infl=1+(st['projInflation'] if st['enableProjReal'] else 0)/100
            want=mt(acc, mo, lambda i,v: v+inv_f[i]>=goal*infl**(i/12)) if goal>0 else None
            got=r['st'][1]['eta']; got=math.inf if got is not None and got>1e300 else got
            if not st['enableProjNet'] and want!=got: fails+=1; print(k,'fire eta', got,'want',want)
            # cash buffer: earns interest, grows by the part of the yearly surplus that isn't invested (a negative one always counts)
            # and by the same part of paid-off loans' payments, until you retire; the goal rises with inflation when that's on
            A=s['targets'][3]['amount']; want=math.inf; cash_at=lambda i: cash[i]
            for i in range(0,721):
                if cash_at(i)>=A*infl**(i/12): want=i; break
            got=r['st'][3]['eta']; got=math.inf if got is None or got>1e300 else got
            if want!=got: fails+=1; print(k,'cash eta',got,'want',want)
            x=r['st'][3]
            if x['need'] is not None and x['due']>0:
                n=x['need']; due=min(x['due'],720)   # reached in any month up to the deadline, with the extra put in month by month (cash below zero earns nothing)
                makes=lambda e: (lambda cs: any(cs[i]>=A*infl**(i/12)-0.01 for i in range(0,due+1)))(savings(r['debts'], due, st, c['surplus'], net, c['buffer'], stop, e)[0])
                if not makes(n): fails+=1; print(k,'cash need',n,'does not make it')
                if n>1 and makes(n*0.97): fails+=1; print(k,'cash need',n,'is too high')
            # deadline: extra €/month really makes it, and noticeably less doesn't
            for x,(reach,start,monthly) in ([] if st['enableProjNet'] else zip(r['st'], [(reach_nw(), r['start'], r['monthly']), (lambda i,v: v+inv_f[i]>=goal*infl**(i/12), acc, mo), (lambda i,v: v+inv_f[i]>=s['targets'][2]['amount']*infl**(i/12), r['start'], r['monthly'])])):
                if x['need'] is None or x['due'] is None or x['due']<=0: continue
                n=x['need']
                if n>0:
                    if mt(start, monthly+n, reach)>x['due']: fails+=1; print(k,x['kind'],'need',n,'does not make it')
                    if n>1 and mt(start, monthly+n*0.97, reach)<=x['due']: fails+=1; print(k,x['kind'],'need',n,'is too high')
                elif mt(start, monthly, reach)>x['due']: fails+=1; print(k,x['kind'],'says no extra needed but misses')
            # After tax on: what you'd keep if you cashed out each month; growth itself is never taxed. Pensions lose the payout tax
            # (as Retirement pays them out), investments income tax on gains above what was put in (entered net deposits replace
            # today's value), the invested share of paid-off loans' payments included
            if st['enableProjNet']:
                now=datetime.date.today().year; age=max(st['retireAge'] or 65, now-st['birthYear'] if st['birthYear'] else 0)
                pt=payout_tax(age, st['payoutYears'], st['taxRate'])/100; inc=st['taxRate']/100; i0=c['etfVal']+c['invValue']
                pen_v,_=by_month(c['pension'], c['penMonthly'], net, 720, g, stop)
                def kept(e, inv_only=False):
                    iv,ip=by_month(i0, mo+e, net, 720, g, stop); out=[]
                    for i in range(721):
                        val=iv[i]+inv_f[i]; dep=(st['invDeposits'] if st['invDeposits']>0 else i0)+(ip[i]-i0)+inv_put[i]
                        out.append(val-inc*max(0,val-dep)+(0 if inv_only else pen_v[i]*(1-pt)))
                    return out
                kinds=[(0, lambda e: [v+other+cash[i]-owed[i] for i,v in enumerate(kept(e))], nwT), (1, lambda e: kept(e,True), goal), (2, kept, s['targets'][2]['amount'])]
                for j,vals,amt in kinds:
                    x=r['st'][j]
                    if j==1 and goal<=0: continue
                    v=vals(0); want=next((i for i in range(721) if v[i]>=amt*infl**(i/12)), math.inf)
                    got=x['eta']; got=math.inf if got is None or got>1e300 else got
                    if want!=got: fails+=1; print(k,'after tax',x['kind'],'eta',got,'want',want)
                    if x['need'] is not None and x['due']>0 and want>x['due']:
                        n=x['need']; due=min(x['due'],720); makes=lambda e: (lambda a: any(a[i]>=amt*infl**(i/12)-0.01 for i in range(0,due+1)))(vals(e))
                        if not makes(n): fails+=1; print(k,'after tax',x['kind'],'need',n,'does not make it')
                        if n>1 and makes(n*0.97): fails+=1; print(k,'after tax',x['kind'],'need',n,'is too high')
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
        if not (neg[0]<0 and neg[1]=='unassigned / year' and neg[2].startswith('A shortfall comes out of your cash') and neg[3]==0): fails+=1; print('negative surplus tile', neg)
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
            pg.set_input_files('#importFile', str(FIXTURES/name)); pg.wait_for_timeout(300)
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
        print('page errors:', errs[:3] or 'none')
        finish('targets', fails or errs, f"{N} random users: {'all match' if not fails else str(fails)+' differences'}")

if __name__=='__main__':
    main()
