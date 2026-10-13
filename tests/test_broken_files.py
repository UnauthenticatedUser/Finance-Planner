"""Broken and hostile backup files: the page must never crash, never show NaN/undefined/Infinity, never scroll
sideways, and never run code or render HTML that came from a name in the file.
Run: python tests/test_broken_files.py [number of files] [seed]"""
from playwright.sync_api import sync_playwright
import json, random, os, tempfile, sys
from helpers import PAGE, fixture, finish
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
  return {vis:vis.slice(0,3), tips:tips.slice(0,2), xss:!!window.__xss, injected, sideways:document.documentElement.scrollWidth>innerWidth+1}; }"""
N=int(sys.argv[1]) if len(sys.argv)>1 else 40; fails=0
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':1300,'height':900}, reduced_motion='reduce'); errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)[:160])); pg.on('dialog', lambda d: d.dismiss())
    pg.goto(PAGE); pg.wait_for_timeout(500)
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
        if r['xss'] or r['injected']: problems.append('HTML from a name was rendered/executed')
        if also: problems.append('non-finite results: '+str(also[:5]))
        if r['sideways']: problems.append('sideways scroll')
        print(i, end=' ', flush=True)
        if problems:
            fails+=1
            if fails<=8: print(f"case {i} ({lang}):", problems[:3])
    b.close()
print()
finish('broken files', fails, f"{N} hostile files: {'all handled cleanly' if not fails else str(fails)+' with problems'}")
