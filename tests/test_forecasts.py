"""Projection, after-tax value, fund fee blend, loan payoff dates and how amounts are shortened on screen.

Random users are checked against independent month-by-month calculations in Python: how money grows with deposits
(the 2nd pillar on the bonus included) and fees, what's left after tax, and how loans amortize. Target dates and
retirement have their own tests.
Run: python tests/test_forecasts.py [number of users]"""
from playwright.sync_api import sync_playwright
import json, random, math, sys
from helpers import PAGE, finish, launch
from model import grow, payout_tax
from test_calculations import user, model
def amort(B,rate,P):
    if B<=0: return 0
    if P<=0: return None
    r=rate/1200; n=0
    while B>1e-9:
        if r>0 and P<=B*r: return math.inf
        B=B*(1+r)-P; n+=1
        if n>100000: return math.inf
    return n
fails=0
def bad(i,msg):
    global fails; fails+=1
    if fails<=8: print(f"user {i}:", msg)
def main():
    random.seed(11); N=int(sys.argv[1]) if len(sys.argv)>1 else 150
    with sync_playwright() as p:
        b=launch(p); pg=b.new_page(viewport={'width':1300,'height':900}, reduced_motion='reduce'); errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)[:150]))
        pg.goto(PAGE); pg.wait_for_timeout(500)
        # short amounts: thousands with one decimal (eurS) or none (eurC) and millions, rounding up to the next unit
        for n,want in [(999499,'€999k'),(999500,'€1M'),(999999,'€1M'),(1234567,'€1.23M'),(-999600,'−€1M')]:
            if pg.evaluate("n=>eurC(n)", n)!=want: bad('eurC',f"{n} shows {pg.evaluate('n=>eurC(n)', n)}, expected {want}")
        for n,want in [(9999,'€9,999'),(23340,'€23.3k'),(999949,'€999.9k'),(999950,'€1M')]:
            if pg.evaluate("n=>eurS(n)", n)!=want: bad('eurS',f"{n} shows {pg.evaluate('n=>eurS(n)', n)}, expected {want}")
        for i in range(N):
            s=user(); s.update(projGrowth=random.choice([0,0,2,3]), enableProjReal=random.random()<.3, projInflation=2.5, enableProjNet=random.random()<.3, invDeposits=random.choice([0,0,5000,20000]),
                enableProjSurplus=random.random()<.3, enableProjFee=random.random()<.2, projFee=round(random.uniform(0,2),2), birthYear=random.choice([0,1950,1970,1985,1995,2005]), statePension=random.choice([0,900]), retireAge=random.choice([65,58,62]), payoutYears=random.choice([20,15]))
            r=pg.evaluate("""s=>{ state=normalize(JSON.parse(s)); save(); refreshAll(); const c=compute(), pi=projInputs(c);
                return {c:{pension:c.pension, etfVal:c.etfVal, invValue:c.invValue, etfM:c.etfMonthly, invM:c.invMonthly, surplus:c.surplus, fee:c.fundFee, exp:c.expenses, dM:c.debtMonthly, etfVals:c.etfVals},
                  start:pi.start, monthly:pi.monthly, rate:projRate(c).net, big:document.getElementById('proj-big').textContent,
                  pay:(state.debts||[]).map(d=>{const q=payoff(d.balance, debtRate(d), d.payment); return q?q.months:null}), debtRates:(state.debts||[]).map(d=>debtRate(d)),
                  note:document.getElementById('proj-note').textContent, now:new Date().getFullYear()} }""", json.dumps(s))
            c=r['c']; yrs=max(1,round(s['projYears'])); penM=model(s)['penMonthly']
            # fee blend
            def pil(f, mo):
                sh=sum(x['share'] for x in f); return [(x['value']+12*mo*(x['share']/sh if sh>0 else 0), x['fee']) for x in f]
            etfSumW=sum(e['weight'] for e in s['etfs']); plan=s['enableEtfPlan']; perfund=not plan and sum(e['monthly'] for e in s['etfs'])>0
            W=pil(s['p2funds'],penM-s['thirdPillar'])+pil(s['p3funds'],s['thirdPillar'])+[(c['etfVals'][k]+12*((c['etfM']*e['weight']/etfSumW if etfSumW>0 else 0) if plan else (e['monthly'] if perfund else 0)), e['fee']) for k,e in enumerate(s['etfs'])]+[(x['value']+12*x['monthly'],x['fee']) for x in s['investments']]
            tw=sum(w for w,_ in W); fee=sum(w*f for w,f in W)/tw if tw>0 else 0
            if abs(fee-c['fee'])>1e-9: bad(i,f"fee {c['fee']} vs {fee}")
            net_r=s['projReturn']-(s['projFee'] if s['enableProjFee'] else fee)
            if abs(net_r-r['rate'])>1e-9: bad(i,f"rate {r['rate']} vs {net_r}")
            # projection (gross or after tax), today's money
            start=c['pension']+c['etfVal']+c['invValue']; monthly=penM+c['etfM']+c['invM']+(max(0,c['surplus'])/12 if s['enableProjSurplus'] else 0)
            if abs(start-r['start'])>1e-6 or abs(monthly-r['monthly'])>1e-6: bad(i,f"inputs {r['start']},{r['monthly']} vs {start},{monthly}")
            if s['enableProjNet']:
                pv,_=grow(c['pension'],penM,net_r,yrs*12,s['projGrowth']); i0=c['etfVal']+c['invValue']
                iv,iput=grow(i0,c['etfM']+c['invM']+(max(0,c['surplus'])/12 if s['enableProjSurplus'] else 0),net_r,yrs*12,s['projGrowth'])
                age=max(s['retireAge'], r['now']-s['birthYear'] if s['birthYear'] else 0)   # pension funds are taxed as Retirement pays them out
                dep=(s['invDeposits'] if s['invDeposits']>0 else i0)+(iput-i0); final=pv*(1-payout_tax(age, s['payoutYears'], s['taxRate'])/100)+iv-s['taxRate']/100*max(0,iv-dep)
                pt=payout_tax(age, s['payoutYears'], s['taxRate']); said=f"{pt}% on pension payouts" if pt else "pension payouts are tax-free"
                if said not in r['note']: bad(i,f"after-tax note should say '{said}'")
            else: final,_=grow(start,monthly,net_r,yrs*12,s['projGrowth'])
            if s['enableProjReal']: final/=1.025**yrs
            exp_big=pg.evaluate("n=>eurC(n)", final)
            if r['big']!=exp_big: bad(i,f"projection shows {r['big']} expected {exp_big}")
            # payoff
            for k,d in enumerate(s['debts']):
                rt=(max(0,s['euribor'])+d['margin']) if d['rtype']=='euribor' else d['rate']
                if abs(rt-r['debtRates'][k])>1e-9: bad(i,f"debt rate {r['debtRates'][k]} vs {rt}")
                n=amort(d['balance'],rt,d['payment']); got=r['pay'][k]
                if n is not None and n>1200: n=math.inf   # over 100 years counts as never
                ok=(n is None and got is None) or (n is not None and got is not None and (abs(n-got)<=1 or (n==math.inf and got>1e300)))   # never paid off: the tool says "never" (a huge number)
                if not ok: bad(i,f"payoff {got} vs {n} (bal {d['balance']} rate {rt} pay {d['payment']})")
        print("page errors:", errs[:3] or "none")
        b.close()
    finish('forecasts', fails or errs, f"{N} random users: {'all forecasts match' if not fails else str(fails)+' differences'}")

if __name__=='__main__':
    main()
