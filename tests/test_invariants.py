"""Cross-module invariants: parts of the tool checked against each other, with no Python model in between.

The other tests compare the tool with models written from the same reading of the rules, so a choice made in both
passes them. These checks need no model: the yearly summary and the surplus must tell the same story; Your path must
start at today's net worth; the Projection, Your path and Retirement must agree month by month; a net worth or cash
target's date must be where Your path crosses it; the extra a month a cash deadline asks for must make it while 0.5%
less doesn't; nothing on screen shows NaN, Infinity or "1e+21". Random users from test_calculations, with ages,
retirement ages, inflation, After tax, Try other numbers and deadlines varied.
Run: python tests/test_invariants.py [number of users]"""
import random, sys, datetime
from playwright.sync_api import sync_playwright
from helpers import PAGE, finish, launch, watch_errors
from test_calculations import user
JS = r"""s=>{ state=normalize(s); refreshAll(); const c=compute(), out=[], near=(a,b,t=0.02)=>Math.abs(a-b)<=Math.max(t, Math.abs(b)*1e-9);
  // 1. the yearly summary and the surplus tell the same story
  const y=c.aNet-12*(c.expenses+c.debtMonthly+c.cashInvested); if(!near(y, c.surplus)) out.push('aNet vs surplus '+y+' / '+c.surplus);
  // 2. Your path starts at today's net worth (before tax)
  const H=pathHover; if(H && !state.enableProjNet && !near(H.pts[0].nw, c.networth)) out.push('path start '+H.pts[0].nw+' vs nw '+c.networth);
  // 3. Projection == path's pensions+investments (own numbers)
  if(!state.enableProjCustom){ const yrs=projYears(), gp=growParts(c, projRate(c).gross, yrs*12), mm=moneyByMonth(c,720,{}), iv=mm.inv();
    for(let k=0;k<=Math.min(yrs,60);k++){ const a=gp.pen.pts[k].val+gp.inv.pts[k].val, b=mm.pen[12*k]+iv[12*k]; if(!near(a,b,0.05)){ out.push('proj vs path y'+k+' '+a+' / '+b); break; } } }
  // 4. targets vs the path (own numbers): net worth and cash dates
  if(!state.enableProjCustom && H){ const all=moneyByMonth(c,720,{real:true, tax:!!state.enableProjNet}), parts=netWorthParts(c), inv=all.inv();
    state.targets.forEach(t=>{ const s=targetStatus(t,c); let k=-1;
      if(t.kind==='networth'){ k=inv.findIndex((v,i)=>{ const p=parts(i), d=inflAfter(i); return (c.physVal+c.debtAssets*d+all.pen[i]+v+p.cash-p.debt) >= t.amount*d; }); }
      else if(t.kind==='cash'){ k=[...Array(721).keys()].findIndex(i=>parts(i).cash>=t.amount*inflAfter(i)); }
      else return;
      const want=k<0?Infinity:k; if(s.eta!==want) out.push(t.kind+' eta '+s.eta+' vs path '+want); }); }
  // 5. the extra a month a deadline asks for really makes it, a little less doesn't
  state.targets.forEach(t=>{ const due=dueMonths(t), s=targetStatus(t,c); if(!(due>0) || s.eta==null || s.eta<=due || t.kind==='custom') return; const n=s.need(due); if(!isFinite(n) || n<=1) return;
    const lo=n*0.995; const test=x=>{ if(t.kind==='cash'){ const p=netWorthParts(c,x); for(let i=0;i<=Math.min(due,720);i++) if(p(i).cash>=t.amount*inflAfter(i)) return true; return false; } return null; };
    if(t.kind==='cash' && (!test(n) || test(lo))) out.push('cash need '+n+' wrong'); });
  // 6. retirement agrees with the path
  const r=retirement(c); if(r && !state.enableProjCustom){ const mm=moneyByMonth(c, Math.max(720, r.pm, r.m), {}), iv=mm.inv();
    if(r.pm<=720 && !near(r.penAt, mm.pen[r.pm]/inflAfter(r.pm))) out.push('ret pen '+r.penAt+' vs '+mm.pen[r.pm]/inflAfter(r.pm));
    if(r.m<=720 && !near(r.invAt, iv[r.m]/inflAfter(r.m))) out.push('ret inv '+r.invAt+' vs '+iv[r.m]/inflAfter(r.m));
    if(!isFinite(r.total)) out.push('ret total '+r.total); }
  // 7. nothing broken on screen
  const bad=[...document.querySelectorAll('.main *, .editor *')].filter(e=>e.children.length===0 && e.getClientRects().length && /NaN|undefined|Infinity|null\b|\[object|\de\+\d/.test(e.textContent)).map(e=>(e.id||e.className)+': '+e.textContent.slice(0,60));
  if(bad.length) out.push('bad text '+bad.slice(0,2).join(' | '));
  return out; }"""
def main(N=300, seed=3):
    random.seed(seed); fails=0
    with sync_playwright() as p:
        b=launch(p); pg=b.new_page(viewport={'width':1300,'height':900}, reduced_motion='reduce'); errs=watch_errors(pg)
        pg.goto(PAGE); pg.wait_for_timeout(300); pg.evaluate("document.querySelector('.viewtabs [data-view=progress]').click()")
        for i in range(N):
            s=user()
            s.update(birthYear=random.choice([0,1950,1960,1963,1966,1975,1990,2005]), retireAge=random.choice([55,60,63,65,67,70]), enableProjReal=random.random()<.7, projInflation=random.choice([2.5,0,5,-1]),
                     enableProjNet=random.random()<.4, enableProjSurplus=random.random()<.5, projSurplusPct=random.choice([100,50,0,33.3]), projGrowth=random.choice([0,0,3,-2]), invDeposits=random.choice([0,0,10000]),
                     enableProjCustom=random.random()<.15, projStart=random.choice([0,30000]), projMonthly=random.choice([0,700]), payoutYears=random.choice([20,10,0]))
            today=datetime.date.today()
            s['targets']=[{'name':'nw','kind':'networth','amount':random.choice([1e5,5e5,2e6])},{'name':'c','kind':'cash','amount':random.choice([5000,30000,2e5]),'dueMon':'%02d'%random.randint(1,12),'dueYear':str(today.year+random.randint(1,12))},
                          {'name':'i','kind':'invested','amount':3e5},{'name':'f','kind':'fire','spend':random.choice([0,24000]),'rate':4,'health':random.choice(['yes','no'])}]
            r=pg.evaluate(JS, s)
            if r:
                fails+=1
                if fails<=15: print(i, r[:3], {k:s[k] for k in ('birthYear','retireAge','enableProjNet','enableProjCustom','gross','autoNet')})
        print('page errors:', errs[:3] or 'none'); b.close()
    finish('invariants', fails or errs, f'{N} random users: {"all consistent" if not fails else str(fails)+" with problems"}')

if __name__=='__main__':
    main(int(sys.argv[1]) if len(sys.argv)>1 else 300)
