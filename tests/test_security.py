"""Attack tests: hostile backups and tampered browser storage try to run code or inject HTML; every text field gets
every payload (script tags, event handlers, javascript: links, prototype pollution, template tricks), in both
languages, both views, with every section and tooltip opened.
Pass = no payload ever runs, no foreign element or attribute appears, and the page keeps working.
Run: python tests/test_security.py"""
import json, copy, os, tempfile
from playwright.sync_api import sync_playwright
from helpers import PAGE, fixture, finish
base=fixture('example.json')
P=['<img src=x onerror="window.__pwned=1">','<svg onload=window.__pwned=1>','"><script>window.__pwned=1</script>',"'><iframe srcdoc='<script>parent.__pwned=1</script>'>",
   'javascript:window.__pwned=1','<a href="javascript:window.__pwned=1">x</a>','{{constructor.constructor("window.__pwned=1")()}}','${window.__pwned=1}',
   '<math><mtext><table><mglyph><style><img src=x onerror=window.__pwned=1>','<noscript><p title="</noscript><img src=x onerror=window.__pwned=1>">','<SCRIPT>window.__pwned=1</SCRIPT>',
   '<svg><script>window.__pwned=1</script></svg>','<details open ontoggle=window.__pwned=1>','toString','valueOf','__proto__','constructor','hasOwnProperty',' · '.join(['<b onmouseover=window.__pwned=1>x</b>','valueOf'])]
def strings(o, f):
    if isinstance(o, dict): return {k:(f(v) if isinstance(v,str) else strings(v,f)) for k,v in o.items()}
    if isinstance(o, list): return [f(v) if isinstance(v,str) else strings(v,f) for v in o]
    return o
CHECK="""()=>{ const bad=[]; document.querySelectorAll('body *').forEach(e=>{ for(const a of e.attributes){ if(/^on/i.test(a.name)) bad.push(e.tagName+' '+a.name); if(/^(href|src|action|formaction|xlink:href|srcdoc)$/i.test(a.name) && /^\\s*javascript:/i.test(a.value)) bad.push(e.tagName+' '+a.name+'=js');   /* only attributes a browser follows as a link */ } if(/^(SCRIPT|IFRAME|OBJECT|EMBED|IMG|svg|math|STYLE)$/.test(e.tagName) && e.closest('#goalsList')) bad.push('foreign '+e.tagName); });
   return {pwned:!!window.__pwned, bad:[...new Set(bad)].slice(0,5), proto:({}).polluted!==undefined || ({}).__pwned!==undefined} }"""
fails=0; runs=0
with sync_playwright() as p:
    b=p.chromium.launch()
    for pl in P:
        for how in ('import','storage'):
            data=strings(copy.deepcopy(base), lambda v: pl)                     # every string field gets the payload
            data['text']={k:pl for k in ['pageTitle','goalsHTML','titleIncome','titleProj']}; data['text']['goalsHTML']='<p>'+pl+'</p>'
            data['__proto__']={'polluted':1}; data['constructor']={'x':1}; data['history']=[{'m':pl,'nw':1},{'m':'2025-01','nw':5}]
            raw=json.dumps(data)
            pg=b.new_page(viewport={'width':1360,'height':900}); errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)[:120]))
            pg.on('dialog', lambda d: d.dismiss())
            pg.goto(PAGE); pg.wait_for_timeout(200)
            if how=='storage':
                pg.evaluate("(raw)=>{ localStorage.clear(); localStorage.setItem(KEY, raw); }", raw); pg.reload(); pg.wait_for_timeout(900)
            else:
                path=os.path.join(tempfile.mkdtemp(),'evil.json'); open(path,'w').write(raw)
                pg.set_input_files('input[type=file]', path); pg.wait_for_timeout(900)
            for lang in ('et','en'):                                            # translation lookups, both views, every tooltip, open everything
                pg.evaluate("(l)=>{ const b=document.querySelector('.langtabs [data-lang='+l+']'); if(b) b.click(); }", lang); pg.wait_for_timeout(250)
                for view in ('progress','overview'):
                    pg.evaluate("(v)=>document.querySelector('.viewtabs [data-view='+v+']').click()", view); pg.wait_for_timeout(250)
                    pg.evaluate("()=>{ document.querySelectorAll('details').forEach(d=>d.open=true); document.querySelectorAll('[data-tip]').forEach((e,i)=>{ if(i<400){ e.dispatchEvent(new MouseEvent('mouseover',{bubbles:true})); e.dispatchEvent(new MouseEvent('mouseenter',{bubbles:true})); } }); }"); pg.wait_for_timeout(150)
            r=pg.evaluate(CHECK); alive=pg.evaluate("()=>typeof compute==='function' && !!document.querySelector('#out-networth').textContent")
            saved=pg.evaluate("()=>{ try{ JSON.stringify(JSON.parse(localStorage.getItem(KEY))); return true }catch(e){ return false } }")
            runs+=1
            if r['pwned'] or r['bad'] or r['proto'] or errs or not alive or not saved:
                fails+=1; print('FAIL', how, repr(pl)[:50], r, 'errors:', errs[:2], 'alive:', alive, 'saved:', saved)
            pg.close()
finish('security', fails, f'{runs} attack runs, {fails} failed')
