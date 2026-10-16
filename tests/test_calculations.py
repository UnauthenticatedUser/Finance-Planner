"""Take-home pay, taxes, budget, net worth and the yearly summary.

Hundreds of random users are run through the tool and through an independent Python model of Estonia's 2026 rules
(income tax, basic exemption, unemployment insurance and the state top-up, each varied, 2nd pillar including on the bonus
and a business account's 2nd pillar part (into your fund, not tax), 3rd pillar tax refund (none on business account
income), one-time income left out, funds split from a total by their target shares, and for
working pensioners no unemployment insurance and only what the state pension leaves of the EUR 776 tax-free amount; your own
net pay with no gross gives the gross it comes from, and your own net pay is what the yearly figures use). The
two must agree to the cent, and every headline figure on screen must show the computed value: also the pay summary, the
donut's tooltips (the legend's percentages), the net pay difference row only when there is one, the 3rd pillar refund at
your tax rate, and no red "−€0", "10.0 months" or "0.0 months", including the edge cases that cause them; a figure whose
place on the page is missing fails too.
Run: python tests/test_calculations.py [number of users]"""
from playwright.sync_api import sync_playwright
import json, random, sys, datetime
from helpers import PAGE, finish, launch
from model import state_pension, pensioner as of_pension_age
PY={'week':52,'month':12,'quarter':4,'year':1}
def R(a,b,z=0.25): return 0 if random.random()<z else round(random.uniform(a,b))
def user():
    s={'gross':R(0,9000,0.1),'autoNet':random.random()<.8,'manualNet':R(500,6000),'bonus':R(0,10000,.5),'expenses':R(0,5000,.1),'thirdPillar':R(0,800,.4),
       'etfMonthly':R(0,2500,.3),'p2rate':random.choice([2,4,6]),'enableP2':random.random()<.85,'p2state':random.choice([4,4,0,5]),'taxRate':random.choice([22,22,22,20,24]),'unemployment':random.choice([1.6,1.6,0,2]),'basicExemption':random.choice([700,700,0,654]),
       'cashOnHand':R(0,3000,.5),'creditLimit':R(0,5000,.5),'enableEtfPlan':random.random()<.6,'enableEtfAutoSplit':random.random()<.3,'etfTotal':R(0,80000),'enableExpenseCats':random.random()<.3,'projReturn':random.choice([0,4,7,8,10]),'projYears':random.choice([5,10,20,40])}
    s['accounts']=[{'name':'A%d'%i,'amount':R(0,40000),'yield':round(random.uniform(0,4),2)} for i in range(random.randint(0,3))]
    s['etfs']=[{'name':'E%d'%i,'weight':R(0,100),'value':R(0,50000),'monthly':R(0,800),'fee':round(random.uniform(0,.6),2)} for i in range(random.randint(0,4))]
    s['investments']=[{'name':'I%d'%i,'monthly':R(0,300),'value':R(0,20000),'fee':0} for i in range(random.randint(0,3))]
    s['incomes']=[{'name':'X%d'%i,'amount':R(50,3000,0),'freq':random.choice(list(PY)+['once']),'tax':random.choice(['salary','free','custom','biz']),'rate':R(0,40)} for i in range(random.randint(0,3))]
    s['expenseItems']=[{'name':'C%d'%i,'amount':R(10,2000,0),'freq':random.choice(list(PY))} for i in range(random.randint(0,4))]
    s['debts']=[{'name':'D%d'%i,'balance':R(0,200000),'rtype':random.choice(['fixed','euribor']),'rate':round(random.uniform(0,20),1),'margin':round(random.uniform(0,3),2),'payment':R(0,2000),'asset':R(0,250000,.5)} for i in range(random.randint(0,3))]
    s['physAssets']=[{'name':'P%d'%i,'value':R(0,30000)} for i in range(random.randint(0,3))]
    s['p2funds']=[{'name':'F%d'%i,'value':R(0,80000),'share':R(0,100),'fee':round(random.uniform(0,1),2)} for i in range(random.randint(0,2))]
    s['p3funds']=[{'name':'G%d'%i,'value':R(0,30000),'share':R(0,100),'fee':round(random.uniform(0,1),2)} for i in range(random.randint(0,2))]
    s['euribor']=round(random.uniform(-0.5,4),2)
    s['birthYear']=random.choice([0]*6+[1950,1958,1961,1964,1990]); s['statePension']=random.choice([0,500,700,900])   # some are of pension age
    s['pensionAgeYears']=random.choice([0,0,0,62,67]); s['pensionAgeMonths']=0   # an own pension age: an earlier one doesn't bring the pensioner tax rules
    return s
def model(s):
    g=s['gross']; T=s['taxRate']/100; U=s['unemployment']/100; E=s['basicExemption']
    pensioner=of_pension_age(s, datetime.date.today().year)
    if pensioner: U=0
    p2r=s['p2rate'] if s['enableP2'] else 0
    if not g and not s['autoNet'] and s['manualNet']>0:   # your own net pay and no gross: the gross that leaves that net
        k=1-p2r/100-U; n=s['manualNet']; E0=max(0, 776-(s['statePension'] or 860)) if pensioner else E
        g=n/k if n<=E0 else (n-E0*T)/(k*(1-T))
    if pensioner:   # a working pensioner: the exemption is what the state pension leaves of €776
        E=max(0, 776-state_pension(s, 0))   # your own state pension, else the average (today's pay doesn't show what was earned)
    p2sr=s['p2state'] if s['enableP2'] else 0
    inc=[x for x in s['incomes'] if x['freq']!='once']; per_month=lambda x: x['amount']*PY[x['freq']]/12   # a one-time payment is money you already have
    own=lambda x: x['tax'] in ('custom','biz'); rate_of=lambda x: (20+p2r if x['tax']=='biz' else min(100,x['rate']))/100   # a business account: 20% + your 2nd pillar rate
    mon=[x for x in inc if x['freq']!='year']; yr=[x for x in inc if x['freq']=='year']
    mSal=sum(per_month(x) for x in mon if x['tax']=='salary'); ySal=sum(x['amount'] for x in yr if x['tax']=='salary')
    mFree=sum(per_month(x) for x in mon if x['tax']=='free'); yFree=sum(x['amount'] for x in yr if x['tax']=='free')
    mC=sum(per_month(x) for x in mon if own(x)); yC=sum(x['amount'] for x in yr if own(x))
    mCT=sum(per_month(x)*rate_of(x) for x in mon if own(x)); yCT=sum(x['amount']*rate_of(x) for x in yr if own(x))
    def net_of(x): a=x*p2r/100; b=x*U; return x-a-b-max(0,x-a-b-E)*T
    gS=g+mSal
    net=(net_of(g) if s['autoNet'] else s['manualNet']) + (net_of(gS)-net_of(g)) + mFree + (mC-mCT)
    exp= sum(x['amount']*PY[x['freq']]/12 for x in s['expenseItems']) if (s['enableExpenseCats'] and s['expenseItems']) else s['expenses']
    biz=lambda x: x['tax']=='biz'; mB=sum(per_month(x)*p2r/100 for x in mon if biz(x)); yB=sum(x['amount']*p2r/100 for x in yr if biz(x))   # a business account's 2nd pillar part: into your fund
    p2=gS*p2r/100+mB; p2s=gS*p2sr/100; t3=s['thirdPillar']
    perfund=not s['enableEtfPlan'] and sum(e['monthly'] for e in s['etfs'])>0
    etfM=sum(e['monthly'] for e in s['etfs']) if perfund else s['etfMonthly']
    invM=sum(x['monthly'] for x in s['investments'])
    invested=t3+p2+etfM+invM
    rate=lambda d: (max(0,s['euribor'])+d['margin']) if d['rtype']=='euribor' else d['rate']
    debt=sum(d['balance'] for d in s['debts']); dM=sum(d['payment'] for d in s['debts'])
    pension=sum(f['value'] for f in s['p2funds']+s['p3funds'])
    buffer=sum(a['amount'] for a in s['accounts'])+s['cashOnHand']
    auto=s['enableEtfPlan'] and s['enableEtfAutoSplit']; sw=sum(e['weight'] for e in s['etfs'])   # a target split with "spread my total": each fund its weight's share
    etf_vals=[s['etfTotal']*e['weight']/sw if sw>0 else 0 for e in s['etfs']] if auto else [e['value'] for e in s['etfs']]
    assets=pension+(s['etfTotal'] if auto else sum(etf_vals))+sum(x['value'] for x in s['investments'])+buffer+sum(d['asset'] for d in s['debts'])+sum(p['value'] for p in s['physAssets'])
    aSal=gS*12+s['bonus']+ySal; aP2s=aSal*p2r/100; aP2=aP2s+mB*12+yB; aU=aSal*U   # the 2nd pillar from pay (before tax) and from a business account
    aTax=max(0,aSal-aP2s-aU-E*12)*T; aCT=mCT*12+yCT-(mB*12+yB)   # withheld at your own rates, less that 2nd pillar part
    # the 3rd pillar refund: income at your own rate counts (its 15% and its tax); a business account's doesn't (no deductions there)
    taxedCust=sum(x['amount']*PY[x['freq']] for x in inc if x['tax']=='custom' and x['rate']>0); ownTax=sum(x['amount']*PY[x['freq']]*rate_of(x) for x in inc if x['tax']=='custom' and x['rate']>0)
    p3Limit=min(6000,(aSal+taxedCust)*0.15); ded=min(t3*12, p3Limit); refund=min(ded*T, aTax+ownTax)
    aGross=g*12+s['bonus']+(mSal+mFree+mC)*12+ySal+yFree+yC
    # bonus + yearly salary-like income: the year's take-home on all salary-like pay minus 12 monthly salaries (the exemption is yearly)
    year_extra=(aSal-aP2s-aU-aTax)-12*net_of(gS)
    surplus=(net-exp-dM-(invested-p2))*12 + year_extra + yFree + (yC-yCT) + refund
    return {'net':net,'expenses':exp,'p2':p2,'p2s':p2s,'penMonthly':t3+(aSal*(p2r+p2sr)/100+mB*12+yB)/12,'invested':invested,'networth':assets-debt,'assets':assets,'debt':debt,'taxRefund':refund,'aGross':aGross,
            'aNet':aGross-aP2-aU-aTax-aCT+refund+(0 if s['autoNet'] else 12*(s['manualNet']-net_of(g))),'surplus':surplus,'buffer':buffer,'pension':pension,'savings':invested/(net+p2)*100 if net+p2>0 else 0,'p3Limit':p3Limit,
            'debtInterestYr':sum(d['balance']*rate(d)/100 for d in s['debts']), 'etfVals':etf_vals}
RECON="""()=>{ const c=compute(), out=[], txt=id=>{const e=document.getElementById(id); return e?e.textContent:null};
  const chk=(lbl,shown,expect)=>{ if(shown===null) out.push(lbl+': not on the page'); else if(shown!==expect) out.push(lbl+': shows '+shown+' expected '+expect); };   // a renamed id fails too
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
  // the donut's tooltips (on the slices shown) say the legend's whole percentages; the debt ring compares with assets only when there are some
  const tipP=[...document.querySelectorAll('#alloc-svg .dseg[data-tip]')].filter(e=>e.style.display!=='none').map(e=>(e.getAttribute('data-tip').match(/ · (\\d+)%$/)||[])[1]).filter(Boolean).map(Number), srt=a=>a.filter(x=>x>0).sort((x,y)=>x-y).join();   // a sliver too thin to draw can still be 0% in the legend
  if(pcts.length && srt(tipP)!==srt(pcts)) out.push('donut tips '+tipP+' vs legend '+pcts);
  const ring=document.querySelector('#alloc-svg .dring'); if(ring && c.debt>0 && !(c.assets>0) && /% of your assets/.test(ring.getAttribute('data-tip'))) out.push('debt ring: a share of no assets');
  // the summary's pay is the gross in use (worked out from net pay when that's all you entered); a red amount is one below €0 as shown
  if(!document.getElementById('sum-salary').textContent.startsWith(eur(c.aBase/12)+'/mo')) out.push('pay summary '+document.getElementById('sum-salary').textContent);
  [['out-surplus','.msurplus'],['sur-left','#sur-left']].forEach(([id,sel])=>{ const t=document.getElementById(id).textContent, red=document.querySelector(sel).classList.contains('neg');
    if(/^[−-]€0$/.test(t) || red!==t.startsWith('−')) out.push(id+' shows '+t+(red?' in red':'')); });
  // the "difference to the net pay you entered" row only when there is one; the 3rd pillar refund at your tax rate
  const adj=Math.round(c.ownNetAdj); if((document.getElementById('row-y-ownnet').style.display!=='none')!==(adj!==0)) out.push('net pay difference row shown wrongly for '+adj);
  if(!(document.getElementById('out-p3').dataset.tip||'').startsWith(num(state.taxRate)+'% income tax back')) out.push('3rd pillar tip: '+document.getElementById('out-p3').dataset.tip);
  if(/≈ 0\\.0/.test(document.getElementById('buffer-months').textContent)) out.push('cash buffer ≈ 0.0 months');
  const bm=document.getElementById('buffer-months').textContent.match(/≈ (\\d+)\\.\\d/); if(bm && +bm[1]>=10) out.push('cash buffer '+bm[0]);
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
            r=pg.evaluate("s=>{ state=normalize(JSON.parse(s)); save(); refreshAll(); const c=compute(); return {net:c.net,expenses:c.expenses,p2:c.p2,p2s:c.p2s,penMonthly:c.penMonthly,invested:c.invested,networth:c.networth,assets:c.assets,debt:c.debt,taxRefund:c.taxRefund,aGross:c.aGross,aNet:c.aNet,surplus:c.surplus,buffer:c.buffer,pension:c.pension,savings:c.savings,p3Limit:c.p3Limit,debtInterestYr:c.debtInterestYr,etfVals:c.etfVals}}", json.dumps(s))
            diffs=[f"{k}: tool {r[k]:.4f} vs model {m[k]:.4f}" for k in m if k!='etfVals' and abs(r[k]-m[k])>max(0.01, abs(m[k])*1e-9)]
            if len(r['etfVals'])!=len(m['etfVals']) or any(abs(a-b)>0.005 for a,b in zip(r['etfVals'],m['etfVals'])): diffs.append(f"fund values {r['etfVals']} vs {m['etfVals']}")
            rec=pg.evaluate(RECON)
            checked+=1
            if diffs or rec:
                fails+=1
                if fails<=6: print(f"user {i}:", diffs[:3], rec[:3])
        # edges the random users rarely reach: 9.97 months of cash, a leftover of −€0.40, a loan with nothing owned, a small history near €0
        none={'accounts':[],'cashOnHand':0,'etfs':[],'investments':[],'physAssets':[],'p2funds':[],'p3funds':[],'debts':[],'enableExpenseCats':False,'enableEtfAutoSplit':False}
        loan=[{'name':'d','balance':5000,'rtype':'fixed','rate':5,'margin':0,'payment':100,'asset':0}]
        for name, extra, js, want in (('cash buffer', {**none, 'accounts':[{'name':'a','amount':9970,'yield':0}], 'expenses':1000}, '', ('buffer-months', '≈ 10 months of expenses')),
                                      ('tiny cash buffer', {**none, 'accounts':[{'name':'a','amount':10,'yield':0}], 'expenses':1000}, '', ('buffer-months', '')),
                                      ('leftover', {}, 'state.expenses+=(compute().surplusLeft+0.4)/12;', ('sur-left', '+€0')),
                                      ('loan, nothing owned', {**none, 'debts':loan}, '', None)):
            s=user(); s.update(extra)
            r=pg.evaluate("a=>{ state=normalize(JSON.parse(a[0])); "+js+" refreshAll(); return a[1] ? document.getElementById(a[1]).textContent : ''; }", [json.dumps(s), want and want[0]])
            rec=pg.evaluate(RECON)
            if rec or (want and r!=want[1]): fails+=1; print(name, rec[:3], r, want)
        if 'with no assets entered' not in pg.evaluate("document.querySelector('#alloc-svg .dring').getAttribute('data-tip')"): fails+=1; print('debt ring tooltip without assets')
        labels=pg.evaluate("()=>{ state.history=[{m:'2026-01',nw:40,assets:40,debt:0,auto:0},{m:'2026-02',nw:-3000,assets:0,debt:3000,auto:0}]; state.enableHistory=false; refreshAll(); return [...document.querySelectorAll('#hist-chart text')].map(e=>e.textContent); }")
        if '€0' not in labels: fails+=1; print('history chart: no €0 label', labels)
        print("page errors:", errs[:3] or "none")
        b.close()
    finish('calculations', fails or errs, f"{checked} random users: {checked-fails} matched, {fails} with differences")

if __name__=='__main__':
    main()
