"""Retirement income per month, against an independent model.

Covers birth year and retirement age (including already past it, and before pension age: the state pension isn't in
the total when it starts a year or more after retiring, pension fund payouts are taxed as income more than 5 years
early, compared in whole months: an own pension age of 67 years 2 months less 5 years isn't "too early"), the pension
funds growing until payouts start when you retire before they can, the state pension age by year of birth or set by hand
(the state pension a year or more after retiring left out, 11 months counted), payout periods shorter and longer than life
expectancy (19.3 years at 65, 0.8 fewer per later year), inflation on and off, the state pension estimated from pay (or the
average without pay, or for someone already a pensioner, and the hint saying so), the pensioners' EUR 776 tax-free
amount, investment account withdrawals tax-free until they add up to more than was put in and taxed in full after that
(with net deposits entered or not; the years it takes, counted year by year, and what's left once it's taxed), no jump overnight on 1 January
(also for someone already retired), loan payments still running at retirement in today's money (one paid off in that very
month isn't; one with no payment, or one that never pays off), a half-year retirement age from an old file, ages written
"65y 1m", never "1 years", and huge numbers that must never show NaN or Infinity.
Run: python tests/test_retirement.py [number of users]"""
from playwright.sync_api import sync_playwright
import json, random, math, sys, re
from helpers import PAGE, finish, fixture, launch, on_day, pick, watch_errors
from model import grow, life_left, payout_tax, surplus_invested, pension_age, state_pension, save_months, retire_age, payout_age, savings, months, age_now
def main():
    random.seed(int(sys.argv[2]) if len(sys.argv)>2 else 5); N=int(sys.argv[1]) if len(sys.argv)>1 else 200
    with sync_playwright() as p:
        b=launch(p); pg=b.new_page(viewport={'width':1300,'height':900}, reduced_motion='reduce'); errs=watch_errors(pg, n=200)
        pg.goto(PAGE); pg.wait_for_timeout(300); pg.click('.viewtabs [data-view=progress]')
        base=fixture('example.json'); fails=0; shown_bad=0
        for i in range(N):
            big=i%3==0
            s=json.loads(json.dumps(base))
            s.update(birthMonth=pick(0,0,1,6,7,12), birthYear=pick(0,1940,1960,1975,1990,2000,2010,2026,2050), retireAge=pick(0,55,60,64.5,65,67,70,120,random.randint(1,120)),   # a half year from an old file rounds up
                     payoutYears=pick(0,1,10,20,30,100,random.randint(0,100)), projInflation=pick(0,2.5,-2,10,random.uniform(-50,100)) ,
                     statePension=pick(0,0,500,1200,1e12 if big else 2000), enableProjReal=pick(True,False), projReturn=pick(7,0,-5,12,random.uniform(-100,100)),
                     projGrowth=pick(0,3,-10,random.uniform(-100,100)), enableProjSurplus=pick(True,False), projSurplusPct=pick(100,25,0,random.uniform(0,100)),
                     enableProjFee=pick(True,False), projFee=pick(0,0.2,1.5,100),
                     pensionAgeYears=pick(0,0,0,63,67,70), pensionAgeMonths=pick(0,0,1,6,11), enableP2=pick(True,False), invDeposits=pick(0,0,30000,1e6))   # net deposits: less or more than the value
            if random.random()<.3: s['gross']=pick(0,400,886,6000)   # the state pension estimate below and above the minimum, and none
            for d in s['debts']: d['payment']=pick(d['payment'], d['payment'], 0, 50)   # loans with no payment, or one that never pays them off
            if big:
                s['gross']=pick(1e6,1e9,1e12); s['etfMonthly']=pick(1e6,1e12); s['thirdPillar']=pick(1e5,1e12)
                for k in ['accounts','etfs','investments','p2funds','p3funds']:
                    for x in s.get(k,[]):
                        for f in ['amount','value','monthly']:
                            if f in x: x[f]=pick(1e9,1e12,x[f])
            r=pg.evaluate("""s=>{ state=normalize(s); save(); refreshAll(); const c=compute(), r=retirement(c), R=projRate(c);
                const txt=['ret-tag','ret-total','ret-sub','ret-state','ret-pen','ret-inv','ret-note'].map(id=>{const e=document.getElementById(id); return e?e.textContent:''}).join(' | ');
                const runs=c.debtList.map(d=>{ const q=payoff(d.balance, d.rate, d.payment); return {P:+d.payment||0, n:q?q.months:0}; });
                return {r, runs, st:{...state}, c:{aSal:c.aSal,pension:c.pension,penM:c.t3+(c.aP2+c.aStateP2)/12,etfVal:c.etfVal,invValue:c.invValue,etfMonthly:c.etfMonthly,invMonthly:c.invMonthly,surplus:c.surplus,expenses:c.expenses,debtMonthly:c.debtMonthly, buffer:c.buffer}, netPen:projRate(c,null,'pen').net, netInv:projRate(c,null,'inv').net,
                  debts:c.debtList.filter(d=>(+d.balance||0)>0).map(d=>({B:+d.balance, r:(+d.rate||0)/1200, P:Math.max(0,+d.payment||0)})), total:document.getElementById('ret-total').textContent, now:new Date().getFullYear(), txt,
                  visible:!document.getElementById('ret-body').hidden && !!document.getElementById('ret-body').getClientRects().length}; }   // Progress is open""", s)
            st, c, got = r['st'], r['c'], r['r']
            by=st['birthYear']
            if not by or by>r['now']:
                if got is not None: fails+=1; print(i,'expected no retirement for birthYear',by, 'got', got and got['year'])
                continue
            age=retire_age(st); m=save_months(st, r['now'])   # until the middle of the year you retire, from this month
            pay_age=payout_age(st)                                 # payouts start at retirement, not before 5 years before pension age, nor before now
            pm=max(m, months(pay_age-age_now(st)))                 # the pension funds stay invested until then, with nothing new after you retire
            pen=grow(c['pension'],c['penM'],r['netPen'],pm,st['projGrowth'],m)[0] if pm else c['pension']   # 2nd pillar on the bonus too; pensions at their own fees
            start=c['etfVal']+c['invValue']
            inv,put=grow(start,c['etfMonthly']+c['invMonthly']+surplus_invested(st, c['surplus']),r['netInv'],m,st['projGrowth']) if m else (start,start)
            _,_,fi,fput=savings(r['debts'], m, st, c['surplus'], r['netInv'], c['buffer'], m); inv+=fi[m]; put+=fput[m]   # paid-off loans' invested share
            defl=(1+(st['projInflation'] if st['enableProjReal'] else 0)/100)**(m/12)
            penAt=pen/(1+(st['projInflation'] if st['enableProjReal'] else 0)/100)**(pm/12); invAt=inv/defl
            tx=(st['taxRate'] or 0)/100
            spa=pension_age(st)
            s1=state_pension(st, c['aSal'], r['now'])              # inflation off counts as 0%, so it's today's amount either way
            s1-=tx*max(0,s1-776)                                   # state pension: taxed above the pensioner's €776 a month
            dep=(st['invDeposits'] if st['invDeposits']>0 else start)+(put-start)
            ig=1+(st['projInflation'] if st['enableProjReal'] else 0)/100; w=inv*0.04; took=0; free_years=0   # 4% a year, rising with prices
            while inv>0 and dep>0 and free_years<200 and took+w*ig**free_years<=dep: took+=w*ig**free_years; free_years+=1   # whole years before what's taken out passes what was put in
            # under a year tax-free: the first year is taxed from the month what's taken out (rising smoothly with prices) passes what was put in
            first=1 if free_years>=1 else 0 if not (inv>0 and dep>0) else dep/w if ig==1 else math.log(1+dep*(ig-1)/w)/math.log(ig)
            inv_kept=invAt*0.04/12*(1-tx*(1-first))   # tax-free while it lasts (what the total counts)
            py=st['payoutYears'] or 20
            penPart=penAt/(py*12)*(1-payout_tax(pay_age, py, st['taxRate'] or 0, spa)/100)
            tot=(s1 if months(pay_age)>months(spa)-12 else 0)+penPart+inv_kept   # not counted when it starts a year or more after retiring
            spend=c['expenses']+sum(d['P'] for d in r['runs'] if d['n']>m)/defl   # loans still being paid at retirement: a fixed payment, less in today's money
            if got is None: fails+=1; print(i,'no result'); continue
            if not r['visible']: shown_bad+=1; print(i,'the Retirement card is hidden although there is a result')
            if math.isfinite(tot) and abs(tot)<1e12 and r['total']!=pg.evaluate("n=>'≈ '+eur(n)+' a month'", tot): fails+=1; print(i,'card shows',r['total'],'want',tot)   # what the card says, not only what it works out
            if got['m']==0 and not r['txt'].startswith(('now','praegu')): shown_bad+=1; print(i,'past retirement age should say now:', r['txt'][:60])
            if not math.isfinite(tot):
                ok= not math.isfinite(got['total']) or got['total']>1e300
            else:
                ok= abs(got['total']-tot)<=max(0.01,abs(tot)*1e-9)
            if not ok: fails+=1; print(i,'total',got['total'],'want',tot, {k:st[k] for k in ['birthYear','retireAge','payoutYears','projInflation','projReturn','projGrowth']})
            if abs(got['spend']-spend)>0.01: fails+=1; print(i,'spending',got['spend'],'want',spend)
            if math.isfinite(tot) and abs(tot)<1e12:
                fy=got['invFreeYears'] if got['invFreeYears'] is not None else math.inf   # JSON turns Infinity into null
                if free_years<100 and not (free_years<=fy<free_years+1+1e-9) or free_years>=100 and fy<100: fails+=1; print(i,'tax-free years',fy,'want',free_years)   # over 100 years counts as never
                if abs(got['fromInvLater']-invAt*0.04/12*(1-tx))>max(0.01,abs(invAt)*1e-9): fails+=1; print(i,'after the tax-free years',got['fromInvLater'],'want',invAt*0.04/12*(1-tx))
            if abs(got['lifeYears']-life_left(pay_age))>1e-9: fails+=1; print(i,'life expectancy',got['lifeYears'],'want',life_left(pay_age))
            if any(w in r['txt'] for w in ['NaN','undefined','Infinity','e+','null']) : shown_bad+=1; print(i,'shows:',r['txt'][:300])
            if re.search(r'\dy \d+ months?\b', r['txt']): shown_bad+=1; print(i,'mixed short and long age:', re.search(r'.{0,20}\dy \d+ months?', r['txt']).group(0))
            if re.search(r'(?<![\d.])1 (years|months)\b', r['txt']): shown_bad+=1; print(i,'plural for one:', re.search(r'.{0,40}(?<![\d.])1 (years|months)\b', r['txt']).group(0))
        # already retired with payouts starting now, exactly 12 months before an own pension age: the state pension isn't in the
        # total. Tried in every month of the year, as only some month counts (64y1m, 64y4m…) went wrong when compared in decimals.
        for mo in range(1, 13):
            q=on_day(getattr(b, '_b', b).new_page(), '2027-%02d-15' % mo); q.goto(PAGE); q.wait_for_timeout(200)
            late=q.evaluate("""()=>{ const by=1963, k=Math.round(((new Date().getFullYear()-by)+(new Date().getMonth()-6)/12)*12)+12;   // your age now in months, plus a year
              state=normalize({birthYear:by, retireAge:60, pensionAgeYears:Math.floor(k/12), pensionAgeMonths:k%12, gross:2000}); refreshAll(); const r=retirement(compute());
              return [r.stateLater, Math.round((r.payAge)*12), k]; }""")
            if not late[0]: fails+=1; print('payouts now, 12 months before pension age', late[2], 'in month', mo, ': the state pension is counted')
            q.close()
        # the wording: past your retirement age, payouts start now (not "at your retirement age"); one year of payouts is
        # "1 aasta" in Estonian; investment withdrawals say how long they're tax-free and what's left after that
        words=pg.evaluate("""()=>{ const y=new Date().getFullYear(), note=()=>document.getElementById('ret-note').textContent;
          state=normalize({birthYear:y-66, retireAge:58, gross:2000, etfs:[{name:'A', value:100000, weight:100}], enableEtfPlan:false, invDeposits:60000}); refreshAll(); const en=note();
          state.payoutYears=1; LANG='et'; refreshAll(); const et=note(); LANG='en'; refreshAll(); return [en, et]; }""")
        if 'start now' not in words[0] or 'at your retirement age' in words[0] or 'tax-free until' not in words[0] or '1 aastat' in words[1] or '1 aasta ' not in words[1]:
            fails+=1; print('retirement wording:', words[0][:120], '|', words[1][:120])
        # a loan paid off in the very month you retire isn't spending in retirement; one a month longer is
        for extra, want in ((0, 0), (1, 100)):
            sp=pg.evaluate("""a=>{ state=normalize(a[0]); refreshAll(); const m=saveMonths();
              state.debts=[{name:'car', balance:(m+a[1])*100, rtype:'fixed', rate:0, margin:0, payment:100, asset:0}]; refreshAll(); const c=compute(); return retirement(c).spend-c.expenses; }""",
              [{**base, 'birthYear':1990, 'retireAge':65, 'enableProjReal':False}, extra])   # inflation off: the payment as it is
            if abs(sp-want)>1e-9: fails+=1; print('a loan ending', extra, 'months after retiring adds', sp, 'to spending, want', want)
        # New Year: nothing changes overnight except one month less to go (saving used to be counted in whole calendar years,
        # so the forecasts jumped every 1 January)
        # someone already past retirement age (born 1960) too: their payouts start now, and their age moves on by a month, not a year
        seen=[]
        for when in ('2026-12-31T20:00:00', '2027-01-01T08:00:00'):
            q=getattr(b, '_b', b).new_page(); q.clock.set_fixed_time(when); q.goto(PAGE); q.wait_for_timeout(300)   # its own clock, also when the tests run on another day
            seen.append(q.evaluate("""a=>{ const out={}; for(const [k,s] of Object.entries(a)){ state=normalize(s); refreshAll(); const c=compute(), r=retirement(c);
              out[k]={m:saveMonths(), total:r.total, payAge:r.payAge, tax:r.penTaxPct, fire:k==='young' ? targetStatus(state.targets[0], c).eta : 0}; } return out; }""",
              {'young':{**base, 'birthYear':1990, 'retireAge':65, 'targets':[{'kind':'fire','spend':30000,'health':'yes','rate':4}]},
               'retired':{**base, 'birthYear':1960, 'retireAge':65, 'payoutYears':18, 'targets':[]}})); q.close()
        a,z=seen
        if a['young']['m']-z['young']['m']!=1 or abs(a['young']['total']-z['young']['total'])>a['young']['total']*0.01 or abs(a['young']['fire']-z['young']['fire'])>1: fails+=1; print('New Year jump:', a['young'], z['young'])
        if round((z['retired']['payAge']-a['retired']['payAge'])*12)!=1 or a['retired']['tax']!=z['retired']['tax']: fails+=1; print('New Year jump when retired:', a['retired'], z['retired'])
        # a pensioner's state pension isn't estimated from their pay (it doesn't show what they earned): the average, and the hint says so
        h=pg.evaluate("s=>{ state=normalize(s); refreshAll(); return [retirement(compute()).stateFrom, document.getElementById('sp-hint').textContent]; }", {**base, 'birthYear':1958, 'gross':2500, 'statePension':0})
        if h[0]!='avg' or 'average' not in h[1]: fails+=1; print('pensioner state pension hint', h)
        # whole months at the boundaries: payouts from exactly 5 years before an own pension age with 2 or 5 extra months aren't
        # "too early" (no 22%); the state pension starting exactly a year after you retire is out of the total, 11 months after is in
        for spa_y, spa_m, ret, want_tax22, want_later in ((67,2,55,False,True), (65,5,60,False,True), (67,0,66,False,True), (66,11,66,False,False), (67,2,61,False,True)):
            q=pg.evaluate("""s=>{ state=normalize(s); refreshAll(); const r=retirement(compute()); return {tax:r.penTaxPct, later:r.stateLater, payAge:r.payAge}; }""",
                          {**base, 'birthYear':1990, 'retireAge':ret, 'pensionAgeYears':spa_y, 'pensionAgeMonths':spa_m, 'taxRate':22, 'payoutYears':30})
            if (q['tax']==22)!=want_tax22 or q['later']!=want_later: fails+=1; print(f'pension age {spa_y}y{spa_m}m, retiring at {ret}:', q)
        # the investment account: no tax sentence at 0% income tax; no jump between 0.99 and 1.01 tax-free years (retired, inflation
        # off, €100,000: 4% is €4,000 a year); what you put in is shown as you paid it in (€50,000), not in today's money
        etf=lambda v: [{'name':'World', 'weight':100, 'value':v, 'monthly':0, 'fee':0}]
        inv_base={**base, 'birthYear':1975, 'retireAge':65, 'enableEtfPlan':False, 'etfMonthly':0, 'investments':[], 'etfs':etf(50000), 'projReturn':8}
        rd="s=>{ state=normalize(s); refreshAll(); const r=retirement(compute()); return [r.fromInv, document.getElementById('ret-note').textContent]; }"
        zero=pg.evaluate(rd, {**inv_base, 'taxRate':0, 'invDeposits':1})[1]
        lo, hi=[pg.evaluate(rd, {**inv_base, 'birthYear':1955, 'enableProjReal':False, 'etfs':etf(100000), 'invDeposits':d})[0] for d in (3960, 4040)]
        put=pg.evaluate(rd, {**inv_base, 'invDeposits':50000})[1]
        near=pg.evaluate(rd, {**inv_base, 'birthYear':1955, 'enableProjReal':False, 'etfs':etf(100000), 'invDeposits':3920})[1]   # 0.98 years: "about 1 year", not "after about 12 months"
        if 'about 12 months' in near or not re.search(r'about 1 year here, and the total counts the tax due at the end of the first year: €[1-9]', near):   # the total deducts it
            fails+=1; print('investment account at 0.98 tax-free years:', near[near.find('investment account'):][:220])
        if 'which is what the total counts' not in put: fails+=1; print('investment account with whole tax-free years:', put[put.find('investment account'):][:220])
        if 'investment account' in zero or abs(hi-lo)>2 or 'more than you put in (€50,000)' not in put:
            fails+=1; print('investment account: at 0% tax', 'investment account' in zero, '| 0.99 vs 1.01 years', lo, hi, '|', put[put.find('investment account'):][:110])
        print('page errors:', errs[:3] or 'none')
        finish('retirement', fails or shown_bad or errs, f"{N} users: {fails} calculation differences, {shown_bad} display problems")

if __name__=='__main__':
    main()
