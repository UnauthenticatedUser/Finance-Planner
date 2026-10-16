"""Broken and hostile backup files: the page must never crash, never show NaN/undefined/Infinity (in text, tooltips or
charts), never scroll sideways, never refuse a file that has a backup's parts (a crash while loading one would look like
that), and never run code or render HTML that came from a name in the file. Also: a switch saved as the text "false" is
off and "true" on, an unknown target type becomes a known one, and a file with huge lists is cut to each list's limit and
stays quick (a crafted file can't freeze the page); "+ Add" stops at the limit.
Run: python tests/test_broken_files.py [number of files] [seed]"""
from playwright.sync_api import sync_playwright
import json, random, os, tempfile, sys
from helpers import PAGE, fixture, finish, launch, shown
random.seed(int(sys.argv[2]) if len(sys.argv)>2 else 3)
XSS='<img src=x onerror="window.__xss=1"><script>window.__xss=1</script>"><b>x</b>'
JUNK=[None, '', 'abc', '12abc', -5, -1e9, 1e300, float('nan') if False else 'NaN', 'Infinity', [], {}, True, '1e999', '0x10', ' 42 ', 3.14159]
def junk(): return random.choice(JUNK)
def name(): return random.choice(['', XSS, 'x'*10000, 'Ä õ ü 😀', '${alert(1)}', None, 123])
def hostile():
    base=fixture('example.json')
    s=dict(base)
    for k in list(s):
        if k!='text' and random.random()<.35: s[k]=junk()
    for lk in ['accounts','etfs','investments','incomes','expenseItems','debts','physAssets','p2funds','p3funds','targets','history']:
        r=random.random()
        if r<.15: s[lk]=junk()
        elif r<.6: s[lk]=[{**{f:junk() for f in ['amount','value','weight','monthly','balance','rate','payment','asset','share','fee','yield','margin','current','spend']}, 'name':name(),
                         'freq':random.choice(['month','year','bogus',None]),'tax':random.choice(['salary','custom','x',None]),'rtype':random.choice(['fixed','euribor','x']),'kind':random.choice(['cash','fire','x',None]),
                         'm':random.choice(['2025-01','2025-13','garbage',None]),'nw':junk(),'dueMon':random.choice(['01','13','',None]),'dueYear':random.choice(['2030','abc',None])} for _ in range(random.randint(0,4))]
    s['text']=random.choice([junk(), {'titleCash':name(),'pageTitle':name(),'goalsHTML':XSS}, base.get('text',{})])
    return s
BAD="""()=>{ const vis=[...document.querySelectorAll('body *')].filter(e=>e.children.length===0 && e.getClientRects().length && !e.closest('#goalsList,input,textarea') && /NaN|undefined|Infinity|\\[object|null\\b/.test(e.textContent)).map(e=>e.textContent.slice(0,50));
  const tips=[...document.querySelectorAll('[data-tip]')].map(e=>e.getAttribute('data-tip')).filter(x=>/NaN|undefined|Infinity|\\[object/.test(x)).map(x=>x.slice(0,60));
  const injected=document.querySelectorAll('.main img, .editor img, .main script, .editor script').length;
  const charts=[...document.querySelectorAll('svg')].filter(e=>/NaN|Infinity|undefined/.test(e.innerHTML)).map(e=>(e.closest('[id]')||{}).id);   // a chart drawn with a bad number is blank
  const toast=document.querySelector('.toast'), refused=!!toast && !toast.hidden && toast.classList.contains('problem');
  return {vis:vis.slice(0,3), tips:tips.slice(0,2), charts, refused, xss:!!window.__xss, injected, sideways:document.documentElement.scrollWidth>innerWidth+1}; }"""
N=int(sys.argv[1]) if len(sys.argv)>1 else 40; fails=0
with sync_playwright() as p:
    b=launch(p); pg=b.new_page(viewport={'width':1300,'height':900}, reduced_motion='reduce'); errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)[:160])); pg.on('dialog', lambda d: d.dismiss())
    pg.goto(PAGE); pg.wait_for_timeout(500)
    if not shown(pg): fails+=1; print('the page is hidden')
    d=tempfile.mkdtemp()
    for i in range(N):
        s=hostile(); f=os.path.join(d,'h.json'); open(f,'w').write(json.dumps(s, allow_nan=False, default=str))
        lang='et' if i%2 else 'en'
        pg.evaluate("l=>{ if(LANG!==l) document.querySelector('.langtabs [data-lang='+l+']').click(); }", lang)
        n0=len(errs); pg.set_input_files('#importFile', f); pg.wait_for_timeout(250)
        for v in ['progress','overview']: pg.evaluate("v=>document.querySelector('.viewtabs [data-view='+v+']').click()", v); pg.wait_for_timeout(80)
        pg.evaluate("()=>document.querySelectorAll('details').forEach(d=>d.open=true)"); pg.wait_for_timeout(120)
        r=pg.evaluate(BAD); also=pg.evaluate("()=>{ const c=compute(); return Object.entries(c).filter(([k,v])=>typeof v==='number' && !isFinite(v)).map(([k])=>k) }")
        problems=[]
        if len(errs)>n0: problems.append('page error: '+errs[-1])
        if r['vis']: problems.append('shows '+str(r['vis']))
        if r['tips']: problems.append('tooltip '+str(r['tips']))
        if r['charts']: problems.append('chart with a bad number in '+str(r['charts'][:3]))
        if r['refused']: problems.append('refused, though it has a backup\'s parts (or it broke while loading)')
        if r['xss'] or r['injected']: problems.append('HTML from a name was rendered/executed')
        if also: problems.append('non-finite results: '+str(also[:5]))
        if r['sideways']: problems.append('sideways scroll')
        print(i, end=' ', flush=True)
        if problems:
            fails+=1
            if fails<=8: print(f"case {i} ({lang}):", problems[:3])
    # clear cases: switches written as text, an unknown target type, and lists far over their limits
    base=fixture('example.json'); row=lambda k: (base[k] or [{}])[0]
    big={**base, 'enableP2':'false', 'enableProjNet':'true', 'enableHistory':'nope',   # After tax is off by default: "true" must turn it on
         'targets':[{**row('targets'), 'kind':'weird'}]*1000,
         'accounts':[row('accounts')]*1000, 'etfs':[row('etfs')]*1000, 'debts':[row('debts')]*1000, 'investments':[row('investments')]*1000}
    f=os.path.join(d,'big.json'); open(f,'w').write(json.dumps(big)); n0=len(errs)
    pg.evaluate("()=>{ window.__was=state; }")   # the import replaces state: wait for that, not for something already true
    import time; t=time.time(); pg.set_input_files('#importFile', f); pg.wait_for_function("state!==window.__was", timeout=20000); took=time.time()-t
    r=pg.evaluate("()=>{ const t0=performance.now(); state.gross+=1; refreshAll(); return {change:performance.now()-t0, p2:state.enableP2, net:state.enableProjNet, hist:state.enableHistory, kinds:[...new Set(state.targets.map(t=>t.kind))],"
                  " n:['targets','accounts','etfs','debts','investments'].map(k=>state[k].length), add:document.getElementById('addTarget').disabled}; }")
    want={'p2':False, 'net':True, 'hist':True, 'kinds':['cash'], 'n':[50,100,100,50,100], 'add':True}
    got={k:r[k] for k in want}
    if got!=want or took>10 or r['change']>3000 or len(errs)>n0: fails+=1; print('big file:', got, f'import {took:.1f}s, a change {r["change"]/1000:.1f}s', errs[n0:][:1])
    # a valid file whose loading breaks: a real error (seen, and kept for the report), never "not a backup, nothing was changed"
    f=os.path.join(d,'ok.json'); open(f,'w').write(json.dumps(base)); n0=len(errs)
    pg.evaluate("()=>{ window.__r=refreshAll; refreshAll=()=>{ refreshAll=window.__r; throw new Error('planted'); }; }")   # breaks once
    pg.set_input_files('#importFile', f); pg.wait_for_timeout(400); r=pg.evaluate(BAD)
    if r['refused'] or not any('planted' in e for e in errs[n0:]): fails+=1; print('a crash while importing was reported as', 'a refused file' if r['refused'] else 'nothing')
    errs[n0:]=[]
    b.close()
print()
finish('broken files', fails, f"{N} hostile files: {'all handled cleanly' if not fails else str(fails)+' with problems'}")
