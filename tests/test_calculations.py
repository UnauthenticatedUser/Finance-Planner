"""Take-home pay, taxes, budget, net worth and the yearly summary.

Hundreds of random users are run through the tool and through an independent Python model of Estonia's 2026 rules
(income tax, basic exemption, unemployment insurance, 2nd pillar including on the bonus, 3rd pillar tax refund, and for
working pensioners no unemployment insurance and only what the state pension leaves of the EUR 776 tax-free amount). The
two must agree to the cent, and every headline figure on screen must show the computed value.
Run: python tests/test_calculations.py [number of users]"""
from playwright.sync_api import sync_playwright
import json, random, sys, math, datetime
from helpers import PAGE, finish, launch
from model import pension_age, state_pension
PY={'week':52,'month':12,'quarter':4,'year':1}
def R(a,b,z=0.25): return 0 if random.random()<z else round(random.uniform(a,b))
def user():
    s={'gross':R(0,9000,0.1),'autoNet':random.random()<.8,'manualNet':R(500,6000),'bonus':R(0,10000,.5),'expenses':R(0,5000,.1),'thirdPillar':R(0,800,.4),
       'etfMonthly':R(0,2500,.3),'p2rate':random.choice([2,4,6]),'enableP2':random.random()<.85,'p2state':4,'taxRate':random.choice([22,22,22,20,24]),'unemployment':1.6,'basicExemption':700,
       'cashOnHand':R(0,3000,.5),'creditLimit':R(0,5000,.5),'enableEtfPlan':random.random()<.6,'enableExpenseCats':random.random()<.3,'projReturn':random.choice([0,4,7,8,10]),'projYears':random.choice([5,10,20,40])}
    s['accounts']=[{'name':'A%d'%i,'amount':R(0,40000),'yield':round(random.uniform(0,4),2)} for i in range(random.randint(0,3))]
    s['etfs']=[{'name':'E%d'%i,'weight':R(0,100),'value':R(0,50000),'monthly':R(0,800),'fee':round(random.uniform(0,.6),2)} for i in range(random.randint(0,4))]
    s['investments']=[{'name':'I%d'%i,'monthly':R(0,300),'value':R(0,20000),'fee':0} for i in range(random.randint(0,3))]
    s['incomes']=[{'name':'X%d'%i,'amount':R(50,3000,0),'freq':random.choice(list(PY)),'tax':random.choice(['salary','free','custom']),'rate':R(0,40)} for i in range(random.randint(0,3))]
    s['expenseItems']=[{'name':'C%d'%i,'amount':R(10,2000,0),'freq':random.choice(list(PY))} for i in range(random.randint(0,4))]
    s['debts']=[{'name':'D%d'%i,'balance':R(0,200000),'rtype':random.choice(['fixed','euribor']),'rate':round(random.uniform(0,20),1),'margin':round(random.uniform(0,3),2),'payment':R(0,2000),'asset':R(0,250000,.5)} for i in range(random.randint(0,3))]
    s['physAssets']=[{'name':'P%d'%i,'value':R(0,30000)} for i in range(random.randint(0,3))]
    s['p2funds']=[{'name':'F%d'%i,'value':R(0,80000),'share':R(0,100),'fee':round(random.uniform(0,1),2)} for i in range(random.randint(0,2))]
    s['p3funds']=[{'name':'G%d'%i,'value':R(0,30000),'share':R(0,100),'fee':round(random.uniform(0,1),2)} for i in range(random.randint(0,2))]
    s['euribor']=round(random.uniform(-0.5,4),2)
    s['birthYear']=random.choice([0]*6+[1950,1958,1961,1964,1990]); s['statePension']=random.choice([0,500,700,900])   # some are of pension age
    return s
def model(s):
    g=s['gross']; T=s['taxRate']/100; U=s['unemployment']/100; E=s['basicExemption']
    if s['birthYear'] and s['birthYear']+math.floor(pension_age(s))<=datetime.date.today().year:   # a working pensioner
        U=0; E=max(0, 776-state_pension(s, (g+sum(x['amount']*PY[x['freq']]/12 for x in s['incomes'] if x['freq']!='year' and x['tax']=='salary'))*12+s['bonus']+sum(x['amount'] for x in s['incomes'] if x['freq']=='year' and x['tax']=='salary')))
    p2r=s['p2rate'] if s['enableP2'] else 0; p2sr=s['p2state'] if s['enableP2'] else 0
    inc=s['incomes']; per_month=lambda x: x['amount']*PY[x['freq']]/12
    mon=[x for x in inc if x['freq']!='year']; yr=[x for x in inc if x['freq']=='year']
    mSal=sum(per_month(x) for x in mon if x['tax']=='salary'); ySal=sum(x['amount'] for x in yr if x['tax']=='salary')
    mFree=sum(per_month(x) for x in mon if x['tax']=='free'); yFree=sum(x['amount'] for x in yr if x['tax']=='free')
    mC=sum(per_month(x) for x in mon if x['tax']=='custom'); yC=sum(x['amount'] for x in yr if x['tax']=='custom')
    mCT=sum(per_month(x)*min(100,x['rate'])/100 for x in mon if x['tax']=='custom'); yCT=sum(x['amount']*min(100,x['rate'])/100 for x in yr if x['tax']=='custom')
    def net_of(x): a=x*p2r/100; b=x*U; return x-a-b-max(0,x-a-b-E)*T
    gS=g+mSal
    net=(net_of(g) if s['autoNet'] else s['manualNet']) + (net_of(gS)-net_of(g)) + mFree + (mC-mCT)
    exp= sum(x['amount']*PY[x['freq']]/12 for x in s['expenseItems']) if (s['enableExpenseCats'] and s['expenseItems']) else s['expenses']
    p2=gS*p2r/100; p2s=gS*p2sr/100; t3=s['thirdPillar']
    perfund=not s['enableEtfPlan'] and sum(e['monthly'] for e in s['etfs'])>0
    etfM=sum(e['monthly'] for e in s['etfs']) if perfund else s['etfMonthly']
    invM=sum(x['monthly'] for x in s['investments'])
    invested=t3+p2+etfM+invM
    rate=lambda d: (max(0,s['euribor'])+d['margin']) if d['rtype']=='euribor' else d['rate']
    debt=sum(d['balance'] for d in s['debts']); dM=sum(d['payment'] for d in s['debts'])
    pension=sum(f['value'] for f in s['p2funds']+s['p3funds'])
    buffer=sum(a['amount'] for a in s['accounts'])+s['cashOnHand']
    assets=pension+sum(e['value'] for e in s['etfs'])+sum(x['value'] for x in s['investments'])+buffer+sum(d['asset'] for d in s['debts'])+sum(p['value'] for p in s['physAssets'])
    aSal=gS*12+s['bonus']+ySal; aP2=aSal*p2r/100; aU=aSal*U
    aTax=max(0,aSal-aP2-aU-E*12)*T; aCT=mCT*12+yCT
    taxedCust=sum(x['amount']*PY[x['freq']] for x in inc if x['tax']=='custom' and x['rate']>0)
    p3Limit=min(6000,(aSal+taxedCust)*0.15); ded=min(t3*12, p3Limit); refund=min(ded*T, aTax+aCT)
    aGross=g*12+s['bonus']+(mSal+mFree+mC)*12+ySal+yFree+yC
    # bonus + yearly salary-like income: the year's take-home on all salary-like pay minus 12 monthly salaries (the exemption is yearly)
    year_extra=(aSal-aP2-aU-aTax)-12*net_of(gS)
    surplus=(net-exp-dM-(invested-p2))*12 + year_extra + yFree + (yC-yCT) + refund
    return {'net':net,'expenses':exp,'p2':p2,'p2s':p2s,'penMonthly':t3+aSal*(p2r+p2sr)/100/12,'invested':invested,'networth':assets-debt,'assets':assets,'debt':debt,'taxRefund':refund,'aGross':aGross,
            'aNet':aGross-aP2-aU-aTax-aCT+refund,'surplus':surplus,'buffer':buffer,'pension':pension,'savings':invested/(net+p2)*100 if net+p2>0 else 0,'p3Limit':p3Limit,
            'debtInterestYr':sum(d['balance']*rate(d)/100 for d in s['debts'])}
RECON="""()=>{ const c=compute(), out=[], txt=id=>{const e=document.getElementById(id); return e?e.textContent:null};
  const chk=(lbl,shown,expect)=>{ if(shown!=null && shown!==expect) out.push(lbl+': shows '+shown+' expected '+expect); };
  chk('hero net worth', txt('out-networth'), eur(c.networth));
  // every headline figure on screen is the computed one (the model check above covers the computing)
  chk('cash buffer tile', txt('out-buffer'), eur(c.buffer)); chk('invested tile', txt('out-invested'), eur(c.invested));
  chk('annual surplus tile', txt('out-surplus'), (c.surplus<0?'−':'')+eur(Math.abs(c.surplus)));
  chk('gross / year', txt('out-y-grosshead'), eur(c.aGross)); chk('net / year', txt('out-y-nethead'), eur(c.aNet));
  chk('take-home donut', txt('donut-center'), eur(c.net)); chk('pension total', txt('out-pension'), eurS(c.pension));
  // the yearly breakdown lists the 2nd pillar whenever the year has some (a bonus alone counts)
  [['row-y-p2',c.aP2],['row-y-statep2',c.aStateP2]].forEach(([id,v])=>{ if((v>0)!==(document.getElementById(id).style.display!=='none')) out.push(id+' shown wrongly for '+v); });
  if(c.aP2>0 && !(txt('out-p2')||'').includes(eur(c.p2Avg)+'/mo')) out.push('pensions card 2nd pillar: '+txt('out-p2')+' expected '+eur(c.p2Avg)+'/mo');
  // over the 3rd pillar refund limit: the editor note and the pensions card both say so, with the limit
  const over=c.t3*12>c.p3Limit;
  ['w-p3limit','p3-limit'].forEach(id=>{ const e=document.getElementById(id); if(e.hidden===over || (over && !e.textContent.includes(eur(c.p3Limit)))) out.push(id+' wrong: '+(e.hidden?'hidden':e.textContent)+' for '+c.t3*12+' over '+c.p3Limit); });
  // card rows: amounts follow one rule (exact below EUR 10,000, then short), each on the right; a Euribor loan shows its range line
  const rows=(sel,want)=>[...document.querySelectorAll(sel)].forEach((e,i)=>{ const w=want(i); if(e.textContent!==w) out.push(sel+' '+i+': shows '+e.textContent+' expected '+w); });
  rows('#etf-legend .evalue', i=>c.etfVal>0 ? eurS(c.etfVals[i]||0) : '');
  rows('#inv-legend .evalue', i=>+state.investments[i].value ? eurS(state.investments[i].value) : '');
  rows('#cash-accounts .a-amt', i=>eurS(+state.accounts[i].amount||0));
  rows('#debt-list .dbal', i=>eurS(+c.debtList[i].balance||0));
  rows('#debt-list .dterms', i=>{ const d=c.debtList[i]; return num(d.rate)+'%'+(+d.payment ? ' · '+eur(+d.payment)+'/mo' : ''); });
  rows('#cash-accounts .a-gain', i=>{ const a=state.accounts[i], y=+a.yield||0, amt=+a.amount||0; return y>0 && amt>0 ? '+'+eurS(amt*y/100)+'/yr' : ''; });
  { const p=[...document.querySelectorAll('#etf-legend .ecalc')].map(e=>(e.textContent.match(/(\\d+)%$/)||[])[1]).filter(Boolean).map(Number);
    if(p.length>1 && p.reduce((a,b)=>a+b,0)!==100) out.push('fund shares add up to '+p.reduce((a,b)=>a+b,0)); }
  c.debtList.forEach((d,i)=>{ const b=+d.balance||0, P=+d.payment||0, po=payoff(b, d.rate, P), shown=!!document.querySelectorAll('#debt-list .drange')[i].textContent;
    const when=e=>{ const q=payoff(b, debtRate(d, e), P); return q && q.months!==Infinity ? q.months : -1; }, e0=state.euribor||0;   // a range only when ±1% gives two different dates
    const want=d.rtype==='euribor' && b>0 && !!po && po.months!==Infinity && monthYear(when(e0-1))!==monthYear(when(e0+1)) ;
    if(shown!==want) out.push('debt '+i+' Euribor range shown='+shown); });
  const sum=sel=>[...document.querySelectorAll(sel)].filter(e=>e.getClientRects().length).map(e=>parseFloat(e.textContent)).filter(x=>!isNaN(x)).reduce((a,b)=>a+b,0);
  const bud=sum('#bd-expp, #bd-invp, #bd-leftp, #bd-debtp'); if(c.net>0 && bud!==100) out.push('budget % add up to '+bud);
  const bad=[...document.querySelectorAll('.main *')].filter(e=>e.children.length===0 && e.getClientRects().length && /NaN|undefined|Infinity|null\\b|\\[object/.test(e.textContent)).map(e=>e.textContent.slice(0,40));
  if(bad.length) out.push('bad text: '+bad.slice(0,3).join(' | '));
  const tips=[...document.querySelectorAll('[data-tip]')].map(e=>e.getAttribute('data-tip')).filter(x=>/NaN|undefined|Infinity|\\[object/.test(x));
  if(tips.length) out.push('bad tooltip: '+tips[0].slice(0,60));
  const pcts=[...document.querySelectorAll('#alloc-legend > span i')].map(e=>parseFloat(e.textContent)).filter(x=>!isNaN(x));
  if(pcts.length>1 && pcts.reduce((a,b)=>a+b,0)!==100) out.push('allocation % sum '+pcts.reduce((a,b)=>a+b,0));
  return out; }"""
def main():
    N=int(sys.argv[1]) if len(sys.argv)>1 else 300
    random.seed(7)
    fails=0; checked=0
    with sync_playwright() as p:
        b=launch(p); pg=b.new_page(viewport={'width':1300,'height':900}, reduced_motion='reduce'); errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)[:150]))
        pg.goto(PAGE); pg.wait_for_timeout(500)
        for i in range(N):
            s=user(); m=model(s)
            r=pg.evaluate("s=>{ state=normalize(JSON.parse(s)); save(); refreshAll(); const c=compute(); return {net:c.net,expenses:c.expenses,p2:c.p2,p2s:c.p2s,penMonthly:c.penMonthly,invested:c.invested,networth:c.networth,assets:c.assets,debt:c.debt,taxRefund:c.taxRefund,aGross:c.aGross,aNet:c.aNet,surplus:c.surplus,buffer:c.buffer,pension:c.pension,savings:c.savings,p3Limit:c.p3Limit,debtInterestYr:c.debtInterestYr}}", json.dumps(s))
            diffs=[f"{k}: tool {r[k]:.4f} vs model {m[k]:.4f}" for k in m if abs(r[k]-m[k])>max(0.01, abs(m[k])*1e-9)]
            rec=pg.evaluate(RECON)
            checked+=1
            if diffs or rec:
                fails+=1
                if fails<=6: print(f"user {i}:", diffs[:3], rec[:3])
        print("page errors:", errs[:3] or "none")
        b.close()
    finish('calculations', fails or errs, f"{checked} random users: {checked-fails} matched, {fails} with differences")

if __name__=='__main__':
    main()
