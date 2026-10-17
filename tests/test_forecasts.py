"""Projection, after-tax value, fund fee blend, loan payoff dates and how amounts are shortened on screen.

Random users are checked against independent month-by-month calculations in Python: how money grows with deposits
(the 2nd pillar on the bonus included) and fees (pensions at their funds' average fee, investments at theirs), with
paid-off loans' payments invested like the surplus, what's left after tax, the range band's lower and higher returns, and
how loans amortize; what was put in and the growth (a loss shown as one); the chart itself (drawn, and its box at the end
saying what the headline says), "Try other numbers" with and without tax, and how percentages round (0.145% is 0.15%). Target dates and retirement have their own tests.
Run: python tests/test_forecasts.py [number of users]"""
from playwright.sync_api import sync_playwright
import json, random, math, sys, datetime
from helpers import PAGE, finish, launch, watch_errors
from model import grow, payout_tax, surplus_invested, save_months, pension_age, payout_age, savings
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
        b=launch(p); pg=b.new_page(viewport={'width':1300,'height':900}, reduced_motion='reduce'); errs=watch_errors(pg, n=150)
        pg.goto(PAGE); pg.wait_for_timeout(500)
        # short amounts: thousands with one decimal (eurS) or none (eurC) and millions, rounding up to the next unit
        for n,want in [(999499,'€999k'),(999500,'€1M'),(999999,'€1M'),(1234567,'€1.23M'),(-999600,'−€1M')]:
            if pg.evaluate("n=>eurC(n)", n)!=want: bad('eurC',f"{n} shows {pg.evaluate('n=>eurC(n)', n)}, expected {want}")
        for n,want in [(9999,'€9,999'),(23340,'€23.3k'),(999949,'€999.9k'),(999950,'€1M')]:
            if pg.evaluate("n=>eurS(n)", n)!=want: bad('eurS',f"{n} shows {pg.evaluate('n=>eurS(n)', n)}, expected {want}")
        for n,want in [(2.5,'€3'),(-2.5,'−€3'),(-70282.5,'−€70,283'),(-0.4,'€0')]:   # a half rounds away from zero on both sides
            if pg.evaluate("n=>eur(n)", n)!=want: bad('eur',f"{n} shows {pg.evaluate('n=>eur(n)', n)}, expected {want}")
        for f,n,want in [('num',2.25,'2.3'),('num',-2.25,'−2.3'),('num',-0.04,'0'),('num2',-0.004,'0.00'),('num2',-0.125,'−0.13'),('num2',0.2,'0.20'),('num2',0.145,'0.15'),('num2',1.005,'1.01'),('num',1.05,'1.1')]:   # 0.145 is stored as 0.14499…   # percentages likewise
            if pg.evaluate(f"n=>{f}(n)", n)!=want: bad(f,f"{n} shows {pg.evaluate(f'n=>{f}(n)', n)}, expected {want}")
        for i in range(N):
            s=user(); s.update(projGrowth=random.choice([0,0,2,3]), enableProjReal=random.random()<.3, projInflation=2.5, enableProjNet=random.random()<.3, invDeposits=random.choice([0,0,5000,20000]),
                enableProjSurplus=random.random()<.3, projSurplusPct=random.choice([100,100,50,random.uniform(0,100)]), enableProjFee=random.random()<.2, projFee=round(random.uniform(0,2),2), enableProjRange=random.random()<.3, projRangeSpread=random.choice([1,2,3.5]), birthYear=random.choice([0,1950,1970,1985,1995,2005]), statePension=random.choice([0,900]), retireAge=random.choice([65,58,62]), payoutYears=random.choice([20,15]))
            r=pg.evaluate("""s=>{ state=normalize(JSON.parse(s)); save(); refreshAll(); const c=compute(), pi=projInputs(c);
                return {c:{pension:c.pension, etfVal:c.etfVal, invValue:c.invValue, etfM:c.etfMonthly, invM:c.invMonthly, surplus:c.surplus, fee:c.fundFee, exp:c.expenses, dM:c.debtMonthly, etfVals:c.etfVals},
                  start:pi.start, monthly:pi.monthly, rate:projRate(c).net, ratePen:projRate(c,null,'pen').net, rateInv:projRate(c,null,'inv').net, big:document.getElementById('proj-big').textContent,
                  pay:(state.debts||[]).map(d=>{const q=payoff(d.balance, debtRate(d), d.payment); return q?q.months:null}), debtRates:(state.debts||[]).map(d=>debtRate(d)),
                  debts:c.debtList.filter(d=>(+d.balance||0)>0).map(d=>({B:+d.balance, r:(+d.rate||0)/1200, P:Math.max(0,+d.payment||0)})), buffer:c.buffer,
                  note:document.getElementById('proj-note').textContent, now:new Date().getFullYear(), sub:document.getElementById('proj-sub').textContent,
                  svgBad:/NaN|Infinity/.test(document.getElementById('proj-svg').innerHTML), hover:(()=>{   // the chart's box at the end of the timeframe
                    const svg=document.querySelector('#proj-svg svg'), rc=svg.getBoundingClientRect(), k=rc.width/PROJ.W;
                    document.getElementById('proj-chart').dispatchEvent(new PointerEvent('pointermove', {clientX:rc.left+(PROJ.W-PROJ.padR)*k, clientY:rc.top+rc.height/2, bubbles:true}));
                    return document.querySelector('#proj-chart .ph-box').textContent; })()} }""", json.dumps(s))
            c=r['c']; yrs=max(1,round(s['projYears'])); penM=model(s)['penMonthly']
            # fee blend
            def pil(f, mo):
                sh=sum(x['share'] for x in f); return [(x['value']+12*mo*(x['share']/sh if sh>0 else 0), x['fee']) for x in f]
            etfSumW=sum(e['weight'] for e in s['etfs']); plan=s['enableEtfPlan']; perfund=not plan and sum(e['monthly'] for e in s['etfs'])>0
            Wp=pil(s['p2funds'],penM-s['thirdPillar'])+pil(s['p3funds'],s['thirdPillar']); Wi=[(c['etfVals'][k]+12*((c['etfM']*e['weight']/etfSumW if etfSumW>0 else 0) if plan else (e['monthly'] if perfund else 0)), e['fee']) for k,e in enumerate(s['etfs'])]+[(x['value']+12*x['monthly'],x['fee']) for x in s['investments']]
            avg=lambda W: (lambda tw: sum(w*f for w,f in W)/tw if tw>0 else 0)(sum(w for w,_ in W)); fee=avg(Wp+Wi)
            if abs(fee-c['fee'])>1e-9: bad(i,f"fee {c['fee']} vs {fee}")
            own=lambda f, ret=s['projReturn']: ret-(s['projFee'] if s['enableProjFee'] else f)
            net_r, net_p, net_i = own(fee), own(avg(Wp)), own(avg(Wi))   # the average (the card's summary), pensions, investments
            for got,want,what in ((r['rate'],net_r,'rate'),(r['ratePen'],net_p,'pension rate'),(r['rateInv'],net_i,'investment rate')):
                if abs(got-want)>1e-9: bad(i,f"{what} {got} vs {want}")
            # projection (gross or after tax), today's money
            start=c['pension']+c['etfVal']+c['invValue']; monthly=penM+c['etfM']+c['invM']+surplus_invested(s, c['surplus'])
            if abs(start-r['start'])>1e-6 or abs(monthly-r['monthly'])>1e-6: bad(i,f"inputs {r['start']},{r['monthly']} vs {start},{monthly}")
            stop=save_months(s, r['now']); i0=c['etfVal']+c['invValue']   # deposits stop when you retire
            pt=payout_tax(payout_age(s), s['payoutYears'], s['taxRate'], pension_age(s))   # pension funds are taxed as Retirement pays them out
            def final_at(ret):   # the Projection's end value with this return (the range band: lower and higher), paid-off loans' share included
                np, ni = own(avg(Wp), ret), own(avg(Wi), ret)
                pv,_=grow(c['pension'],penM,np,yrs*12,s['projGrowth'],stop)
                iv,iput=grow(i0,c['etfM']+c['invM']+surplus_invested(s, c['surplus']),ni,yrs*12,s['projGrowth'],stop)
                _,_,fi,fput=savings(r['debts'], yrs*12, s, c['surplus'], ni, r['buffer'], stop)   # paid-off loans' payments, the invested share
                iv+=fi[yrs*12]; iput+=fput[yrs*12]
                dep=(s['invDeposits'] if s['invDeposits']>0 else i0)+(iput-i0)
                v=pv*(1-pt/100)+iv-s['taxRate']/100*max(0,iv-dep) if s['enableProjNet'] else pv+iv
                return v/1.025**yrs if s['enableProjReal'] else v
            if s['enableProjNet']:
                said=f"{pt}% on pension payouts" if pt else "pension payouts are tax-free"
                if said not in r['note']: bad(i,f"after-tax note should say '{said}'")
            exp_big=pg.evaluate("n=>eurC(n)", final_at(s['projReturn']))
            if r['big']!=exp_big: bad(i,f"projection shows {r['big']} expected {exp_big}")
            if s['enableProjRange']:
                sp=s['projRangeSpread']; band=pg.evaluate("a=>eurC(a[0])+'–'+eurC(a[1])", [final_at(s['projReturn']-sp), final_at(s['projReturn']+sp)])
                if 'range '+band not in r['sub']: bad(i,f"range band in {r['sub']!r}, expected {band}")
            # put in: each deposit (and paid-off loans' invested share) in today's money when inflation is taken off
            _,_,_,fput=savings(r['debts'], yrs*12, s, c['surplus'], net_i, r['buffer'], stop); df=(1.025 if s['enableProjReal'] else 1)**(1/12)
            mo=penM+c['etfM']+c['invM']+surplus_invested(s, c['surplus']); want_put=start; d=1
            for k in range(1, yrs*12+1):
                d*=df; want_put+=((mo if k<=stop else 0)+fput[k]-fput[k-1])/d
                if k%12==0: mo*=1+s['projGrowth']/100
            put=r['sub'].split(' put in')[0].split(' · ')[-1]
            if put!=pg.evaluate("n=>eurC(n)", want_put): bad(i,f"put in {put}, expected {pg.evaluate('n=>eurC(n)', want_put)}")
            gr=final_at(s['projReturn'])-want_put; gtxt=pg.evaluate("n=>(Math.sign(Math.round(n))<0?'−':'+')+eurC(Math.abs(n))", gr)   # a loss shows as one
            if gtxt+' growth' not in r['sub']: bad(i,f"growth in {r['sub']!r}, expected {gtxt}")
            # the chart: drawn (no NaN in it), and its box at the end says what the headline says
            if r['svgBad'] or 'Total '+r['big'] not in r['hover'] or 'Put in '+put not in r['hover']: bad(i,f"chart {'has NaN' if r['svgBad'] else ''} hover {r['hover']!r} vs {r['big']}, {put} put in")
            # payoff
            for k,d in enumerate(s['debts']):
                rt=(max(0,s['euribor'])+d['margin']) if d['rtype']=='euribor' else d['rate']
                if abs(rt-r['debtRates'][k])>1e-9: bad(i,f"debt rate {r['debtRates'][k]} vs {rt}")
                n=amort(d['balance'],rt,d['payment']); got=r['pay'][k]
                if n is not None and n>1200: n=math.inf   # over 100 years counts as never
                ok=(n is None and got is None) or (n is not None and got is not None and (n==got or (n==math.inf and got>1e300)))   # never paid off: the tool says "never" (a huge number)
                if not ok: bad(i,f"payoff {got} vs {n} (bal {d['balance']} rate {rt} pay {d['payment']})")
        # "Try other numbers" with After tax: income tax on the growth above what you put in
        for tax in (False, True):
            s=user(); s.update(enableProjCustom=True, projStart=20000, projMonthly=500, projReturn=7, enableProjFee=True, projFee=0.5, projGrowth=0, enableProjReal=False, enableProjNet=tax, enableProjRange=False, projYears=20, birthYear=0, taxRate=22)
            got=pg.evaluate("s=>{ state=normalize(s); refreshAll(); return document.getElementById('proj-big').textContent; }", s)
            v,put=grow(20000,500,6.5,240,0,save_months(s, datetime.date.today().year)); want=pg.evaluate("n=>eurC(n)", v-0.22*max(0,v-put) if tax else v)
            if got!=want: bad('custom',f"Try other numbers{' after tax' if tax else ''} shows {got}, expected {want}")
        print("page errors:", errs[:3] or "none")
        b.close()
    finish('forecasts', fails or errs, f"{N} random users: {'all forecasts match' if not fails else str(fails)+' differences'}")

if __name__=='__main__':
    main()
