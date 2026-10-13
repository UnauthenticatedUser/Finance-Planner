"""Target dates and the extra money a deadline needs, against an independent month-by-month model.

Net worth goals (with loans paid down and freed payments), FIRE goals that rise with inflation, invested-total and
cash goals, "put in" in today's money, and that the suggested extra EUR/month really reaches a deadline while
noticeably less does not. Random mixes of debts, fees, inflation, deposit growth and big numbers.
Run: python tests/test_targets.py [number of users]"""
from playwright.sync_api import sync_playwright
import json, random, math, sys, datetime
from helpers import PAGE, fixture, finish
def months_to(start, monthly, rate, g, reached, cap=720):
    rm=max(0,1+rate/100)**(1/12)-1; v=start; m=monthly
    if reached(0,v): return 0
    for i in range(1,cap+1):
        v=v*(1+rm)+m
        if reached(i,v): return i
        if i%12==0: m*=1+g/100
    return math.inf
def debt_path(debts, months):
    # month by month: balance after interest and payment; once paid, the payment is freed as cash
    out=[0.0]*(months+1); state=[dict(b=d['B'], paid=False) for d in debts]
    freed=0.0
    for i in range(1,months+1):
        for d,s in zip(debts,state):
            if s['paid']: freed+=d['P']; continue
            s['b']=s['b']*(1+d['r'])-d['P']
            if s['b']<=1e-9 and d['P']>0: s['paid']=True; s['b']=0.0
        out[i]=sum(d['B']-max(0,s['b']) for d,s in zip(debts,state))+freed
    return out
def pick(*a): return random.choice(a)
def main():
    random.seed(int(sys.argv[2]) if len(sys.argv)>2 else 7); N=int(sys.argv[1]) if len(sys.argv)>1 else 120
    with sync_playwright() as p:
        b=p.chromium.launch(); pg=b.new_page(); errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)[:200]))
        pg.goto(PAGE); pg.wait_for_timeout(300)
        base=fixture('example.json'); fails=0
        for k in range(N):
            s=json.loads(json.dumps(base)); big=k%5==0
            s.update(projReturn=pick(10,7,0,-5,15,random.uniform(-20,30)), projInflation=pick(2.5,0,5,-1,random.uniform(0,10)), projGrowth=pick(0,3,-5,random.uniform(0,10)),
                     enableProjSurplus=pick(True,False), enableProjFee=pick(True,False), projFee=pick(0,0.2,1.5), enableProjReal=pick(True,False), projYears=pick(10,20,40),
                     expenses=pick(1600,500,4000,9000), euribor=pick(2.6,0,4))
            s['debts']=[{'name':'d'+str(j), 'balance':pick(5000,150000,1e6 if big else 300000), 'rtype':pick('fixed','euribor'), 'rate':pick(0,3,8,25), 'margin':pick(0.5,2), 'payment':pick(0,100,950,3000), 'asset':pick(0,200000)} for j in range(random.randint(0,3))]
            if big: s['gross']=pick(1e5,1e7); s['etfMonthly']=pick(1e5,1e7)
            due=random.randint(6,400); dy=datetime.date.today().year+due//12+1
            s['targets']=[{'name':'nw','kind':'networth','amount':pick(1e5,5e5,2e6,1e8 if big else 3e6)}, {'name':'fire','kind':'fire','amount':0,'rate':pick(4,3.5),'spend':pick(0,30000,60000)},
                          {'name':'inv','kind':'invested','amount':pick(1e5,1e6)}, {'name':'cash','kind':'cash','amount':pick(5000,30000,200000)}]
            for t in s['targets']: t['dueMon']='06'; t['dueYear']=str(dy)
            r=pg.evaluate("""s=>{ state=normalize(s); refreshAll(); const c=compute(), R=projRate(c), pi=projInputs(c);
                const st=state.targets.map(t=>{ const x=targetStatus(t,c), due=dueMonths(t); return {kind:t.kind, eta:x.eta, goal:x.goal, due, need: due>0 ? x.need(due) : null}; });
                const sim=simulate(pi.start, pi.monthly, R.net, Math.max(1,Math.round(state.projYears||20)), state.projGrowth, state.enableProjReal?state.projInflation:0);
                return {st, net:R.net, start:pi.start, monthly:pi.monthly, c:{buffer:c.buffer, leftover:c.net-c.expenses-c.debtMonthly-c.cashInvested, networth:c.networth, surplus:c.surplus, etfVal:c.etfVal, invValue:c.invValue, etfMonthly:c.etfMonthly, invMonthly:c.invMonthly, expenses:c.expenses},
                        debts:c.debtList.filter(d=>(+d.balance||0)>0).map(d=>({B:+d.balance, r:(+d.rate||0)/1200, P:Math.max(0,+d.payment||0)})), st8:{...state},
                        putR:sim.putR, put:sim.put, propsub:document.getElementById('proj-sub').textContent}; }""", s)
            st=r['st8']; net=r['net']; g=st['projGrowth']; c=r['c']
            infl=1+(st['projInflation'] if st['enableProjReal'] else 0)/100
            # net worth
            path=debt_path(r['debts'], 720)
            cashM=(min(0,c['surplus']) if st['enableProjSurplus'] else c['surplus'])/12
            base_nw=c['networth']-r['start']
            nwT=s['targets'][0]['amount']
            def reach_nw():
                return lambda i,v: v+base_nw+cashM*i+path[i]>=nwT*infl**(i/12)
            want=months_to(r['start'], r['monthly'], net, g, reach_nw())
            got=r['st'][0]['eta']; got=math.inf if got is None or got>1e300 else got
            if not (want==got or (abs(want-got)<=1 and want<math.inf)): fails+=1; print(k,'networth eta', got,'want',want)
            # FIRE
            t=s['targets'][1]; yearly=t['spend'] if t['spend']>0 else c['expenses']*12; goal=yearly/(t['rate']/100); acc=c['etfVal']+c['invValue']
            mo=c['etfMonthly']+c['invMonthly']+(max(0,c['surplus'])/12 if st['enableProjSurplus'] else 0); infl=1+(st['projInflation'] if st['enableProjReal'] else 0)/100
            want=months_to(acc, mo, net, g, lambda i,v: v>=goal*infl**(i/12)) if goal>0 else None
            got=r['st'][1]['eta']; got=math.inf if got is not None and got>1e300 else got
            if want!=got: fails+=1; print(k,'fire eta', got,'want',want)
            # cash buffer: grows by the monthly leftover; the goal rises with inflation when that's on
            A=s['targets'][3]['amount']; want=math.inf
            for i in range(0,721):
                if c['buffer']+(min(0,c['leftover']) if st['enableProjSurplus'] else c['leftover'])*i>=A*infl**(i/12): want=i; break   # surplus invested: a positive leftover isn't cash
            got=r['st'][3]['eta']; got=math.inf if got is None or got>1e300 else got
            if want!=got: fails+=1; print(k,'cash eta',got,'want',want)
            # deadline: extra €/month really makes it, and noticeably less doesn't
            for x,(reach,start,monthly) in zip(r['st'], [(reach_nw(), r['start'], r['monthly']), (lambda i,v: v>=goal*infl**(i/12), acc, mo), (lambda i,v: v>=s['targets'][2]['amount']*infl**(i/12), r['start'], r['monthly'])]):
                if x['need'] is None or x['due'] is None or x['due']<=0: continue
                n=x['need']
                if n>0:
                    if months_to(start, monthly+n, net, g, reach)>x['due']: fails+=1; print(k,x['kind'],'need',n,'does not make it')
                    if n>1 and months_to(start, monthly+n*0.97, net, g, reach)<=x['due']: fails+=1; print(k,x['kind'],'need',n,'is too high')
                elif months_to(start, monthly, net, g, reach)>x['due']: fails+=1; print(k,x['kind'],'says no extra needed but misses')
            # put in, today's money when shown so
            yrs=max(1,round(st['projYears'])); inf=st['projInflation'] if st['enableProjReal'] else 0
            m=r['monthly']; tot=r['start']; d=1.0
            for i in range(1,yrs*12+1):
                d*=(1+inf/100)**(1/12); tot+=m/d
                if i%12==0: m*=1+g/100
            if abs(tot-r['putR'])>max(0.01,abs(tot)*1e-9): fails+=1; print(k,'put in',r['putR'],'want',tot)
        print('page errors:', errs[:3] or 'none')
        finish('targets', fails or errs, f"{N} random users: {'all match' if not fails else str(fails)+' differences'}")

if __name__=='__main__':
    main()
