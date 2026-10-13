"""Retirement income per month, against an independent model.

Covers birth year and retirement age (including already past it, and before pension age: no state pension until 65,
pension fund payouts taxed as income more than 5 years early), payout periods shorter and longer than life
expectancy (19.3 years at 65, 0.8 fewer per later year), inflation on and off, the pensioners' EUR 776 tax-free
amount, the growth share of investment withdrawals, loan payments still running at retirement, and huge numbers that
must never show NaN or Infinity.
Run: python tests/test_retirement.py [number of users]"""
from playwright.sync_api import sync_playwright
import json, random, math, sys
from helpers import PAGE, fixture, finish, launch
from model import grow, life_left, payout_tax
def pick(*a): return random.choice(a)
def main():
    random.seed(int(sys.argv[2]) if len(sys.argv)>2 else 5); N=int(sys.argv[1]) if len(sys.argv)>1 else 200
    with sync_playwright() as p:
        b=launch(p); pg=b.new_page(viewport={'width':1300,'height':900}, reduced_motion='reduce'); errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)[:200]))
        pg.goto(PAGE); pg.wait_for_timeout(300); pg.click('.viewtabs [data-view=progress]')
        base=fixture('example.json'); fails=0; shown_bad=0
        for i in range(N):
            big=i%3==0
            s=json.loads(json.dumps(base))
            s.update(birthYear=pick(0,1940,1960,1975,1990,2000,2010,2026,2050), retireAge=pick(0,55,60,65,67,70,120,random.randint(1,120)),
                     payoutYears=pick(0,1,10,20,30,100,random.randint(0,100)), projInflation=pick(0,2.5,-2,10,random.uniform(-50,100)) ,
                     statePension=pick(0,0,500,1200,1e12 if big else 2000), enableProjReal=pick(True,False), projReturn=pick(7,0,-5,12,random.uniform(-100,100)),
                     projGrowth=pick(0,3,-10,random.uniform(-100,100)), enableProjSurplus=pick(True,False),
                     enableProjFee=pick(True,False), projFee=pick(0,0.2,1.5,100))
            if big:
                s['gross']=pick(1e6,1e9,1e12); s['etfMonthly']=pick(1e6,1e12); s['thirdPillar']=pick(1e5,1e12)
                for k in ['accounts','etfs','investments','p2funds','p3funds']:
                    for x in s.get(k,[]):
                        for f in ['amount','value','monthly']:
                            if f in x: x[f]=pick(1e9,1e12,x[f])
            r=pg.evaluate("""s=>{ state=normalize(s); save(); refreshAll(); const c=compute(), r=retirement(c), R=projRate(c);
                const txt=['ret-tag','ret-total','ret-sub','ret-state','ret-pen','ret-inv','ret-note'].map(id=>{const e=document.getElementById(id); return e?e.textContent:''}).join(' | ');
                const runs=c.debtList.map(d=>{ const q=payoff(d.balance, d.rate, d.payment); return {P:+d.payment||0, n:q?q.months:0}; });
                return {r, runs, st:{...state}, c:{pension:c.pension,penM:c.t3+(c.aP2+c.aStateP2)/12,etfVal:c.etfVal,invValue:c.invValue,etfMonthly:c.etfMonthly,invMonthly:c.invMonthly,surplus:c.surplus,expenses:c.expenses,debtMonthly:c.debtMonthly}, net:R.net, now:new Date().getFullYear(), txt,
                  visible:!document.getElementById('ret-body').hidden && !!document.getElementById('ret-body').getClientRects().length || document.getElementById('view-progress').hidden}; }""", s)
            st, c, got = r['st'], r['c'], r['r']
            by=st['birthYear']
            if not by or by>r['now']:
                if got is not None: fails+=1; print(i,'expected no retirement for birthYear',by, 'got', got and got['year'])
                continue
            age=st['retireAge'] or 65; yrs=max(0,by+age-r['now']); m=yrs*12
            pen=grow(c['pension'],c['penM'],r['net'],m,st['projGrowth'])[0] if m else c['pension']   # 2nd pillar on the bonus too
            start=c['etfVal']+c['invValue']
            inv,put=grow(start,c['etfMonthly']+c['invMonthly']+(max(0,c['surplus'])/12 if st['enableProjSurplus'] else 0),r['net'],m,st['projGrowth']) if m else (start,start)
            defl=(1+(st['projInflation'] if st['enableProjReal'] else 0)/100)**yrs
            penAt=pen/defl; invAt=inv/defl
            tx=(st['taxRate'] or 0)/100
            pay_age=max(age, r['now']-by)                          # payouts start at retirement age, or now if that's later
            nom=1 if st['enableProjReal'] else (1+(st['projInflation'] or 0)/100)**max(yrs, by+65-r['now'])   # inflation off: the pension figures in the euros of the year it starts
            s1=(st['statePension'] if st['statePension']>0 else 860)*nom
            s1-=tx*max(0,s1-776*nom)                               # state pension: taxed above the pensioner's €776 a month
            dep=(st['invDeposits'] if st['invDeposits']>0 else start)+(put-start)
            gs=max(0,inv-dep)/inv if inv>0 else 0                  # share of a withdrawal that is growth (taxed)
            py=st['payoutYears'] or 20
            penPart=penAt/(py*12)*(1-payout_tax(pay_age, py, st['taxRate'] or 0)/100)
            tot=(s1 if pay_age>=65 else 0)+penPart+invAt*0.04/12*(1-tx*gs)   # no state pension before 65
            spend=c['expenses']+sum(d['P'] for d in r['runs'] if d['n']>m)  # loans still being paid at retirement
            if got is None: fails+=1; print(i,'no result'); continue
            if got['yrs']==0 and not r['txt'].startswith(('now','praegu')): shown_bad+=1; print(i,'past retirement age should say now:', r['txt'][:60])
            if not math.isfinite(tot):
                ok= not math.isfinite(got['total']) or got['total']>1e300
            else:
                ok= abs(got['total']-tot)<=max(0.01,abs(tot)*1e-9)
            if not ok: fails+=1; print(i,'total',got['total'],'want',tot, {k:st[k] for k in ['birthYear','retireAge','payoutYears','projInflation','projReturn','projGrowth']})
            if abs(got['spend']-spend)>0.01: fails+=1; print(i,'spending',got['spend'],'want',spend)
            if abs(got['lifeYears']-life_left(pay_age))>1e-9: fails+=1; print(i,'life expectancy',got['lifeYears'],'want',life_left(pay_age))
            if any(w in r['txt'] for w in ['NaN','undefined','Infinity','e+','null']) : shown_bad+=1; print(i,'shows:',r['txt'][:300])
        print('page errors:', errs[:3] or 'none')
        finish('retirement', fails or shown_bad or errs, f"{N} users: {fails} calculation differences, {shown_bad} display problems")

if __name__=='__main__':
    main()
