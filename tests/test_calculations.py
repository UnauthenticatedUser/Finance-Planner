"""Take-home pay, taxes, budget, net worth and the yearly summary.

Hundreds of random users are run through the tool and through an independent Python model of Estonia's 2026 rules
(income tax, basic exemption, unemployment insurance and the state top-up, each varied, 2nd pillar including on the bonus
and a business account's 2nd pillar part (into your fund, not tax), 3rd pillar tax refund (none on business account
income), one-time income left out, funds split from a total by their target shares, and for
working pensioners unemployment insurance only until the month they reach pension age and only what the state pension
leaves of the EUR 776 tax-free amount; a loan with nothing left to pay takes no payment; a net pay typed in is kept and
gives the gross it comes from, with the settings of the moment). The
two must agree to the cent, and every headline figure on screen must show the computed value: also the pay summary, the
donut's tooltips (the legend's percentages), the 3rd pillar refund at
your tax rate, and no red "−€0", "10.0 months" or "0.0 months", including the edge cases that cause them; a figure whose
place on the page is missing fails too.
Run: python tests/test_calculations.py [number of users]"""
from playwright.sync_api import sync_playwright
import json, random, sys, datetime
from helpers import PAGE, finish, launch, on_day, watch_errors
from model import state_pension, pensioner as of_pension_age, unemp_months, birth_month, months, pension_age
PY={'week':52,'month':12,'quarter':4,'year':1}
def R(a,b,z=0.25): return 0 if random.random()<z else round(random.uniform(a,b))
def user():
    s={'gross':R(0,9000,0.1),'autoNet':random.random()>=.2,'manualNet':R(500,6000),'bonus':R(0,10000,.5),'expenses':R(0,5000,.1),'thirdPillar':R(0,800,.4),
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
    s['birthYear']=random.choice([0]*6+[1950,1958,1961,1962,1964,1990]); s['statePension']=random.choice([0,500,700,900])   # some are of pension age
    s['birthMonth']=random.choice([0]*4+list(range(1,13)))   # often not given (July)
    s['pensionAgeYears']=random.choice([0,0,0,62,66,67]); s['pensionAgeMonths']=random.choice([0,0,8])   # an own pension age: an earlier one doesn't bring the pensioner tax rules
    return s
def model(s):
    g=s['gross']; T=s['taxRate']/100; U=s['unemployment']/100; E=s['basicExemption']
    pensioner=of_pension_age(s, datetime.date.today().year)
    um=unemp_months(s, datetime.date.today().year); U*=um/12   # the year you reach pension age: until that month, spread over the year
    by=s['birthYear']; ps=by*12+birth_month(s)+months(pension_age(s)) if 1000<=by<=datetime.date.today().year else None   # the pension starts at your own pension age
    pen_months=12 if ps is None else max(0, min(12, (datetime.date.today().year+1)*12-ps))   # it takes its part of the €776 only for this year's months it's paid
    pen_E=lambda p: (776*12-min(p, 776)*pen_months)/12   # a pensioner's pay: what the pension leaves of €776 a month, over the year
    joined=s['enableP2'] and s['p2rate']>0
    p2r=s['p2rate'] if joined else 0
    if pensioner:   # a working pensioner: the exemption is what the state pension leaves of €776
        E=pen_E(state_pension(s, 0))   # your own state pension, else the average (today's pay doesn't show what was earned)
    if not s['autoNet']:   # a net pay typed in is kept: the gross is the one that leaves it with these settings
        k=1-p2r/100-U; n=s['manualNet']; g=n/k if n<=E else (n-E*T)/(k*(1-T))
    p2sr=s['p2state'] if joined else 0
    inc=[x for x in s['incomes'] if x['freq']!='once']; per_month=lambda x: x['amount']*PY[x['freq']]/12   # a one-time payment is money you already have
    own=lambda x: x['tax'] in ('custom','biz'); rate_of=lambda x: (20+p2r if x['tax']=='biz' else min(100,x['rate']))/100   # a business account: 20% + your 2nd pillar rate
    mon=[x for x in inc if x['freq']!='year']; yr=[x for x in inc if x['freq']=='year']
    mSal=sum(per_month(x) for x in mon if x['tax']=='salary'); ySal=sum(x['amount'] for x in yr if x['tax']=='salary')
    mFree=sum(per_month(x) for x in mon if x['tax']=='free'); yFree=sum(x['amount'] for x in yr if x['tax']=='free')
    mC=sum(per_month(x) for x in mon if own(x)); yC=sum(x['amount'] for x in yr if own(x))
    mCT=sum(per_month(x)*rate_of(x) for x in mon if own(x)); yCT=sum(x['amount']*rate_of(x) for x in yr if own(x))
    def net_of(x): a=x*p2r/100; b=x*U; return x-a-b-max(0,x-a-b-E)*T
    gS=g+mSal
    net=net_of(g) + (net_of(gS)-net_of(g)) + mFree + (mC-mCT)
    exp= sum(x['amount']*PY[x['freq']]/12 for x in s['expenseItems']) if (s['enableExpenseCats'] and s['expenseItems']) else s['expenses']
    biz=lambda x: x['tax']=='biz'; mB=sum(per_month(x)*p2r/100 for x in mon if biz(x)); yB=sum(x['amount']*p2r/100 for x in yr if biz(x))   # a business account's 2nd pillar part: into your fund
    p2=gS*p2r/100+mB; p2s=gS*p2sr/100; t3=s['thirdPillar']
    perfund=not s['enableEtfPlan'] and sum(e['monthly'] for e in s['etfs'])>0
    etfM=sum(e['monthly'] for e in s['etfs']) if perfund else s['etfMonthly']
    invM=sum(x['monthly'] for x in s['investments'])
    invested=t3+p2+etfM+invM
    rate=lambda d: (max(0,s['euribor'])+d['margin']) if d['rtype']=='euribor' else d['rate']
    debt=sum(d['balance'] for d in s['debts']); dM=sum(d['payment'] for d in s['debts'] if d['balance']>0)   # a paid-off loan takes nothing
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
            'aNet':aGross-aP2-aU-aTax-aCT+refund,'surplus':surplus,'buffer':buffer,'pension':pension,'savings':invested/(net+p2)*100 if net+p2>0 else 0,'p3Limit':p3Limit,
            'debtInterestYr':sum(d['balance']*rate(d)/100 for d in s['debts']), 'etfVals':etf_vals, 'gross':g, 'salaryNet':net_of(g)}
RECON="""()=>{ const c=compute(), out=[], txt=id=>{const e=document.getElementById(id); return e?e.textContent:null};
  const chk=(lbl,shown,expect)=>{ if(shown===null) out.push(lbl+': not on the page'); else if(shown!==expect) out.push(lbl+': shows '+shown+' expected '+expect); };   // a renamed id fails too
  chk('hero net worth', txt('out-networth'), eur(c.networth));
  // every headline figure on screen is the computed one (the model check above covers the computing)
  chk('cash buffer tile', txt('out-buffer'), eur(c.buffer)); chk('invested tile', txt('out-invested'), eur(c.invested));
  chk('annual surplus tile', txt('out-surplus'), (rnd(c.surplus)<0?'−':'')+eur(Math.abs(c.surplus)));   // −€0.40 is €0
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
  rows('#cash-accounts .a-gain', i=>{ const a=state.accounts[i], y=+a.yield||0, amt=+a.amount||0; return y>0 && amt>0 && Math.round(amt*y/100) ? '+'+eurS(amt*y/100)+'/yr' : ''; });   // under 50 cents a year: nothing
  { const p=[...document.querySelectorAll('#etf-legend .ecalc')].map(e=>(e.textContent.match(/(\\d+)%$/)||[])[1]).filter(Boolean).map(Number);
    const sum=p.reduce((a,b)=>a+b,0); if(p.length>1 && sum && sum!==100) out.push('fund shares add up to '+sum); }   // all 0% (every target at 0, nothing to split) is what they are
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
  // the 3rd pillar refund at your tax rate
  if(!(document.getElementById('out-p3').dataset.tip||'').startsWith(num(state.taxRate)+'% income tax back')) out.push('3rd pillar tip: '+document.getElementById('out-p3').dataset.tip);
  if(/≈ 0\\.0/.test(document.getElementById('buffer-months').textContent)) out.push('cash buffer ≈ 0.0 months');
  const bm=document.getElementById('buffer-months').textContent.match(/≈ (\\d+)\\.\\d/); if(bm && +bm[1]>=10) out.push('cash buffer '+bm[0]);
  // the yearly breakdown and the budget legend add up to the totals they show, to the euro (each total is rounded once and its
  // rows to match), and no row in the breakdown says "−€0"
  const eu=s=>s===null || /[BTMk]/.test(s) ? NaN : (/^[−-]/.test(s.trim())?-1:1)*+s.replace(/[^\\d]/g,''), v=id=>eu(txt(id));
  // each deduction row: never below €0, within a euro of its exact value
  [['out-y-p2',c.aP2],['out-y-unemp',c.aUnemp],['out-y-tax',c.aTax],['out-y-custtax',c.aCustTax]].forEach(([id,x])=>{ const d=-v(id); if(/[−-]\\s*[−-]/.test(txt(id)||'') || !isNaN(d) && (d<0 || Math.abs(d-x)>=1)) out.push('breakdown: '+id+' shows '+txt(id)+' for '+x.toFixed(2)); });   // "−−€1" is a row below €0
  const g=v('out-y-base')+v('out-y-bonus')+[...document.querySelectorAll('#y-other-rows .v')].reduce((a,e)=>a+eu(e.textContent),0);
  if(!isNaN(g) && g!==v('out-y-gross')) out.push('breakdown: the gross rows add up to '+g+', the total shows '+txt('out-y-gross'));
  const th=v('out-y-gross')+v('out-y-p2')+v('out-y-unemp')+v('out-y-tax')+(document.getElementById('row-y-custtax').style.display==='none' ? 0 : v('out-y-custtax'));
  if(!isNaN(th) && th!==v('out-y-takehome')) out.push('breakdown: gross less deductions is '+th+', take-home shows '+txt('out-y-takehome'));
  if(c.onP3 && !isNaN(th) && v('out-y-takehome')+v('out-y-refund')!==v('out-y-netbenefit')) out.push('breakdown: take-home plus the refund is not the net shown');
  const bl=['bd-exp','bd-debt','bd-inv','bd-left'].map(v).reduce((a,b)=>a+b,0); if(!isNaN(bl) && c.net>0 && bl!==v('donut-center')) out.push('budget: the amounts add up to '+bl+', take-home shows '+txt('donut-center'));
  const m0=[...document.querySelectorAll('.dropbody .row')].filter(r=>r.style.display!=='none' && /^[−-]€0$/.test(r.querySelector('.v').textContent)).map(r=>r.textContent.slice(0,30)); if(m0.length) out.push('−€0 in the breakdown: '+m0);
  return out; }"""
def main():
    N=int(sys.argv[1]) if len(sys.argv)>1 else 300
    random.seed(7)
    fails=0; checked=0
    with sync_playwright() as p:
        b=launch(p); pg=b.new_page(viewport={'width':1300,'height':900}, reduced_motion='reduce'); errs=watch_errors(pg, n=150)
        pg.goto(PAGE); pg.wait_for_timeout(500)
        for i in range(N):
            s=user()
            r=pg.evaluate("s=>{ state=normalize(JSON.parse(s)); save(); refreshAll(); const c=compute(); return {gross:c.gross, salaryNet:c.estNet, net:c.net,expenses:c.expenses,p2:c.p2,p2s:c.p2s,penMonthly:c.penMonthly,invested:c.invested,networth:c.networth,assets:c.assets,debt:c.debt,taxRefund:c.taxRefund,aGross:c.aGross,aNet:c.aNet,surplus:c.surplus,buffer:c.buffer,pension:c.pension,savings:c.savings,p3Limit:c.p3Limit,debtInterestYr:c.debtInterestYr,etfVals:c.etfVals}}", json.dumps(s))
            m=model(s)
            diffs=[f"{k}: tool {r[k]:.4f} vs model {m[k]:.4f}" for k in m if k!='etfVals' and abs(r[k]-m[k])>max(0.01, abs(m[k])*1e-9)]
            if not s['autoNet'] and abs(r['salaryNet']-s['manualNet'])>0.005: diffs.append(f"net {s['manualNet']} typed, but the tool's salary net is {r['salaryNet']:.4f}")
            if len(r['etfVals'])!=len(m['etfVals']) or any(abs(a-b)>0.005 for a,b in zip(r['etfVals'],m['etfVals'])): diffs.append(f"fund values {r['etfVals']} vs {m['etfVals']}")
            rec=pg.evaluate(RECON)
            checked+=1
            if diffs or rec:
                fails+=1
                if fails<=6: print(f"user {i}:", diffs[:3], rec[:3])
        # edges the random users rarely reach: 9.97 months of cash, a leftover of −€0.40, a loan with nothing owned, a small history near €0
        none={'accounts':[],'cashOnHand':0,'etfs':[],'investments':[],'physAssets':[],'p2funds':[],'p3funds':[],'debts':[],'enableExpenseCats':False,'enableEtfAutoSplit':False}
        loan=[{'name':'d','balance':5000,'rtype':'fixed','rate':5,'margin':0,'payment':100,'asset':0}]
        for name, extra, js, want in (('breakdown with cents', {**none, 'gross':5356.53, 'autoNet':True, 'bonus':1823.30, 'incomes':[]}, '', None),   # the gross typed, not a net
                                      ('cash buffer', {**none, 'accounts':[{'name':'a','amount':9970,'yield':0}], 'expenses':1000}, '', ('buffer-months', '≈ 10 months of expenses')),
                                      ('tiny cash buffer', {**none, 'accounts':[{'name':'a','amount':10,'yield':0}], 'expenses':1000}, '', ('buffer-months', '')),
                                      ('leftover', {'enableExpenseCats':False}, 'state.expenses+=(compute().surplusLeft+0.4)/12;', ('sur-left', '+€0')),   # one spending total, which the line changes
                                      ('loan, nothing owned', {**none, 'debts':loan}, '', None)):
            s=user(); s.update(extra)
            r=pg.evaluate("a=>{ state=normalize(JSON.parse(a[0])); "+js+" refreshAll(); return a[1] ? document.getElementById(a[1]).textContent : ''; }", [json.dumps(s), want and want[0]])
            rec=pg.evaluate(RECON)
            if rec or (want and r!=want[1]): fails+=1; print(name, rec[:3], r, want)
        if 'with no assets entered' not in pg.evaluate("document.querySelector('#alloc-svg .dring').getAttribute('data-tip')"): fails+=1; print('debt ring tooltip without assets')
        # a row worth nothing (here the hidden tax on other income) never takes the euro of rounding the shown rows need
        r=pg.evaluate("s=>{ state=normalize(s); refreshAll(); }", {'gross':2787.72, 'enableP2':False, 'bonus':1438.34, 'birthYear':1960, 'expenses':1000,
                      'incomes':[{'name':'y', 'amount':190.51, 'freq':'year', 'tax':'free', 'rate':0}]}); rec=pg.evaluate(RECON)
        if rec: fails+=1; print('breakdown with an empty hidden row:', rec[:3])
        # an early pension (own pension age 63) is paid all year when you reach the general age (65, July 2026), so it takes the
        # €776 every month and the pay keeps none: (30,000 − 7 × 40 unemployment insurance) × 22%
        q=on_day(b.new_page(), '2026-10-17'); q.goto(PAGE); q.wait_for_timeout(200)
        got=q.evaluate("()=>{ state=normalize({birthYear:1961, pensionAgeYears:63, gross:2500, enableP2:false, statePension:800}); return Math.round(compute().aTax*100)/100; }"); q.close()
        if got!=6538.40: fails+=1; print('pay tax with an early pension, the year of the general age:', got, 'want 6538.40')
        # the pensioner tax year with an own pension age of years and 6+ months, in whole months: born 1960 (July) with 66y8m reaches it
        # in March 2027, so the pensioner rules start on 1 January 2027, not in 2026 (66.67 years as a decimal used to land in 2026)
        for day, want in (('2026-12-31', False), ('2027-01-01', True)):
            q=on_day(b.new_page(), day); q.goto(PAGE); q.wait_for_timeout(200)
            got=q.evaluate("()=>{ state=normalize({birthYear:1960, pensionAgeYears:66, pensionAgeMonths:8, gross:2000}); return pensionerNow(); }"); q.close()
            if got!=want: fails+=1; print('pensioner on', day, 'with 66y8m, born 1960:', got)
        # small salaries whose deductions round awkwardly, and a tiny one with the default unemployment insurance ("−−€1" once)
        for g, u in ((1533.30, 0), (510.53, 0), (0.51, 1.6)):
            pg.evaluate("s=>{ state=normalize(s); refreshAll(); }", {'gross':g, 'enableP2':False, 'unemployment':u}); rec=pg.evaluate(RECON)
            if rec: fails+=1; print(f'breakdown of a {g} salary:', rec[:3])
        rtt=pg.evaluate("[roundToTotal([0, 0, 13165.912, 0], 13167), roundToTotal([291.912, 220.8], 514), roundToTotal([5.4, 0], 2), roundToTotal([0, 0], 1)]")
        if rtt!=[[0, 0, 13167, 0], [293, 221], [2, 0], [0, 0]]: fails+=1; print('rounding to a total with a gap bigger than its rows:', rtt)
        # the wording of edge cases: unemployment insurance the year you reach pension age (until then) and after it (no row); the
        # debt ring's share with a thousands separator, and under 1% not "0%"; no interest line under 50 cents; the cash buffer
        # without spending; the largest amounts in order; funds "on target" only when they are; no split warning for an old pillar
        edge=pg.evaluate("""()=>{ const out=[], y=new Date().getFullYear(), go=s=>{ state=normalize(s); refreshAll(); return compute(); }, tip=sel=>document.querySelector(sel).getAttribute('data-tip')||'';
          let c=go({gross:2000, birthYear:y-66, pensionAgeYears:66, enableP2:false});   // 66 is later than any general age, so July of this year
          if(c.uMonths!==7 || Math.abs(c.aUnemp-2000*12*0.016*7/12)>0.005 || !/until pension age/.test(document.getElementById('row-y-unemp').textContent)) out.push('unemployment insurance until July: '+c.uMonths+' months, '+c.aUnemp+' '+document.getElementById('row-y-unemp').textContent);
          c=go({gross:2000, birthYear:y-66, birthMonth:2, pensionAgeYears:66, enableP2:false}); if(c.uMonths!==2 || !/until your state pension starts/.test(tip('#tile-net'))) out.push('unemployment insurance with a February birthday: '+c.uMonths+' months, '+tip('#tile-net'));   // the month of birth, when given, replaces July
          const p08=r=>{ go({gross:3000, enableP2:true, p2rate:r, birthYear:1990}); return /0\\.8 of it in the II pillar/.test(document.getElementById('ret-note').textContent); };
          if(p08(0) || !p08(2)) out.push('the I pillar note says "0.8 of it in the II pillar" only when in it: rate 0 '+p08(0)+', rate 2 '+p08(2));
          c=go({gross:2000, birthYear:y-66, birthMonth:12, pensionAgeYears:66, enableP2:false}); if(c.uMonths!==12 || !/all year, as you reach it in December/.test(tip('#tile-net'))) out.push('a December pension age: '+c.uMonths+', '+tip('#tile-net'));
          LANG='et'; refreshAll(); if(!/jõuad pensioniikka detsembris, ja /.test(tip('#tile-net'))) out.push('a December pension age in Estonian: '+tip('#tile-net')); LANG='en';
          c=go({gross:2000, birthYear:y-67}); if(c.uMonths!==0 || document.getElementById('row-y-unemp').style.display!=='none') out.push('no unemployment insurance after pension age: '+c.uMonths);
          go({debts:[{name:'d', balance:96000, payment:100, rate:1}], accounts:[{name:'a', amount:100, yield:0}]}); if(!tip('#alloc-svg .dring').includes('96,000%')) out.push('debt ring: '+tip('#alloc-svg .dring'));
          go({debts:[{name:'d', balance:1, payment:1, rate:1}], accounts:[{name:'a', amount:140000, yield:0}]}); if(!tip('#alloc-svg .dring').includes('<1%')) out.push('debt ring: '+tip('#alloc-svg .dring'));
          go({accounts:[{name:'Tiny', amount:10, yield:1}]}); if(document.querySelector('#cash-accounts .a-gain').textContent || /·/.test(document.querySelector('#cash-accounts .a-yld').textContent)) out.push('interest line for 10 cents: '+document.querySelector('#cash-accounts .ecalc').textContent);
          go({accounts:[{name:'Low', amount:10000, yield:-2}]}); if(!document.querySelector('#cash-accounts .a-gain').classList.contains('neg')) out.push('a negative rate is not shown as a loss');
          if(/covers/.test(tip('#tile-buffer'))) out.push('buffer without spending: '+tip('#tile-buffer'));
          if(eur(999.996e12)!=='€999T+') out.push('largest amounts: '+eur(999.996e12));
          go({etfMonthly:1, enableEtfPlan:true, etfs:[{name:'A', weight:50, value:1000}, {name:'B', weight:50, value:100}]}); if(/on target/.test(document.getElementById('rebal').textContent)) out.push('funds called on target: '+document.getElementById('rebal').textContent);
          go({gross:2000, enableP2:false, p2funds:[{name:'Old', value:5000, share:0}]}); const w=document.getElementById('p2share'); if(w && w.offsetParent && /100%/.test(w.textContent)) out.push('split warning for a pillar nothing goes into: '+w.textContent);
          return out; }""")
        if edge: fails+=1; print('edge cases:', edge)
        labels=pg.evaluate("()=>{ state.history=[{m:'2026-01',nw:40,assets:40,debt:0,auto:0},{m:'2026-02',nw:-3000,assets:0,debt:3000,auto:0}]; state.enableHistory=false; refreshAll(); return [...document.querySelectorAll('#hist-chart text')].map(e=>e.textContent); }")
        if '€0' not in labels: fails+=1; print('history chart: no €0 label', labels)
        print("page errors:", errs[:3] or "none")
        b.close()
    finish('calculations', fails or errs, f"{checked} random users: {checked-fails} matched, {fails} with differences")

if __name__=='__main__':
    main()
