"""Attack tests: hostile backups and tampered browser storage try to run code or inject HTML; every text field gets
every payload (script tags, event handlers, javascript: links, prototype pollution, template tricks, attributes in notes),
in both languages, both views, with every section opened, every tooltip shown and Your path's hover box moved along.
Pass = no payload ever runs or trips the security rule, no foreign element appears anywhere (nor one that draws inside
your own text), no event handler or javascript: link, nothing in the notes keeps an attribute, and the page keeps working.
Run: python tests/test_security.py"""
import json, copy, os, tempfile
from playwright.sync_api import sync_playwright
from helpers import PAGE, fixture, finish, launch, shown
base=fixture('example.json')
P=['<img src=x onerror="window.__pwned=1">','<svg onload=window.__pwned=1>','"><script>window.__pwned=1</script>',"'><iframe srcdoc='<script>parent.__pwned=1</script>'>",
   'javascript:window.__pwned=1','<a href="javascript:window.__pwned=1">x</a>','{{constructor.constructor("window.__pwned=1")()}}','${window.__pwned=1}',
   '<math><mtext><table><mglyph><style><img src=x onerror=window.__pwned=1>','<noscript><p title="</noscript><img src=x onerror=window.__pwned=1>">','<SCRIPT>window.__pwned=1</SCRIPT>',
   '<svg><script>window.__pwned=1</script></svg>','<details open ontoggle=window.__pwned=1>','<p id=exportBtn style="position:fixed;inset:0" class=card>cover</p>','toString','valueOf','__proto__','constructor','hasOwnProperty',' · '.join(['<b onmouseover=window.__pwned=1>x</b>','valueOf'])]
def strings(o, f):
    if isinstance(o, dict): return {k:(f(v) if isinstance(v,str) else strings(v,f)) for k,v in o.items()}
    if isinstance(o, list): return [f(v) if isinstance(v,str) else strings(v,f) for v in o]
    return o
# foreign elements: anywhere (the page's one script aside); svg, which the page draws itself, inside your own text; in the
# notes, no attributes at all. window.__csp: what the security rule blocked (see VIOLATIONS).
CHECK="""()=>{ const bad=[]; document.querySelectorAll('body *').forEach(e=>{ for(const a of e.attributes){ if(/^on/i.test(a.name)) bad.push(e.tagName+' '+a.name); if(/^(href|src|action|formaction|xlink:href|srcdoc)$/i.test(a.name) && /^\\s*javascript:/i.test(a.value)) bad.push(e.tagName+' '+a.name+'=js');   /* only attributes a browser follows as a link */ }
     if(/^(IFRAME|OBJECT|EMBED|IMG|math|STYLE|LINK|META|BASE|FORM)$/i.test(e.tagName) || (e.tagName==='svg' && e.closest('#goalsList, #tip, .ph-box, #path-list, [data-text], .tname, .dname'))) bad.push('foreign '+e.tagName);
     if(e.closest('#goalsList') && e.id!=='goalsList' && e.attributes.length) bad.push('notes keep attributes: '+e.outerHTML.slice(0,40)); });
   if(document.querySelectorAll('body script').length!==1) bad.push('foreign SCRIPT');
   return {pwned:!!window.__pwned, bad:[...new Set(bad)].slice(0,5), csp:(window.__csp||[]).slice(0,3), proto:({}).polluted!==undefined || ({}).__pwned!==undefined} }"""
VIOLATIONS="document.addEventListener('securitypolicyviolation', e=>(window.__csp=window.__csp||[]).push(e.violatedDirective+' '+(e.sample||'').slice(0,40)))"
# every tooltip actually shown (as when hovered), and Your path's hover box moved across the chart: what each shows must be text
SHOW="""()=>{ const out=[], plain=el=>[...el.querySelectorAll('*')].filter(e=>!/^(B|SPAN|EM|I|BR)$/.test(e.tagName) || [...e.attributes].some(a=>!/^(class|style)$/.test(a.name))).map(e=>e.tagName);   // the box's own markup only
   document.querySelectorAll('[data-tip]').forEach((e,i)=>{ if(i<600 && e.getClientRects().length){ tipAt(e,e); const tp=document.getElementById('tip'); if(tp.children.length) out.push('tooltip '+tp.innerHTML.slice(0,40)); } }); hideTip();
   const box=document.getElementById('path-chart'), svg=box && box.querySelector('svg');
   if(svg && svg.getClientRects().length){ const r=svg.getBoundingClientRect();
     for(let x=r.left+2; x<r.right; x+=r.width/60){ box.dispatchEvent(new PointerEvent('pointermove',{clientX:x, clientY:r.top+r.height/2, bubbles:true})); const b=box.querySelector('.ph-box'); if(b) plain(b).forEach(t=>out.push('path hover '+t)); } }
   return [...new Set(out)].slice(0,4); }"""
fails=0; runs=0
with sync_playwright() as p:
    b=launch(p); pg=b.new_page(); pg.goto(PAGE); TEXT=pg.evaluate("Object.keys(DEFAULTS.text)"); pg.close()   # the page title, notes and every card title
    for pl in P:
        for how in ('import','storage'):
            data=strings(copy.deepcopy(base), lambda v: pl)                     # every string field gets the payload
            data['text']={k:pl for k in TEXT}; data['text']['goalsHTML']='<p>'+pl+'</p>'
            data['__proto__']={'polluted':1}; data['constructor']={'x':1}; data['history']=[{'m':pl,'nw':1},{'m':'2025-01','nw':5}]
            raw=json.dumps(data)
            pg=b.new_page(viewport={'width':1360,'height':900}); errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)[:120])); pg.add_init_script(VIOLATIONS)
            pg.on('dialog', lambda d: d.dismiss())
            pg.goto(PAGE); pg.wait_for_timeout(200)
            if how=='storage':
                pg.evaluate("(raw)=>{ localStorage.clear(); localStorage.setItem(KEY, raw); }", raw); pg.reload(); pg.wait_for_timeout(900)
            else:
                path=os.path.join(tempfile.mkdtemp(),'evil.json'); open(path,'w').write(raw)
                pg.set_input_files('input[type=file]', path); pg.wait_for_timeout(900)
            displayed=[]
            for lang in ('et','en'):                                            # translation lookups, both views, every tooltip, open everything
                pg.evaluate("(l)=>{ const b=document.querySelector('.langtabs [data-lang='+l+']'); if(b) b.click(); }", lang); pg.wait_for_timeout(250)
                for view in ('progress','overview'):
                    pg.evaluate("(v)=>document.querySelector('.viewtabs [data-view='+v+']').click()", view); pg.wait_for_timeout(250)
                    pg.evaluate("()=>document.querySelectorAll('details').forEach(d=>d.open=true)"); pg.wait_for_timeout(150)
                    displayed+=pg.evaluate(SHOW)
            r=pg.evaluate(CHECK); alive=pg.evaluate("()=>typeof compute==='function' && !!document.querySelector('#out-networth').textContent") and shown(pg)
            saved=pg.evaluate("()=>{ try{ JSON.stringify(JSON.parse(localStorage.getItem(KEY))); return true }catch(e){ return false } }")
            runs+=1
            if r['pwned'] or r['bad'] or r['csp'] or displayed or r['proto'] or errs or not alive or not saved:
                fails+=1; print('FAIL', how, repr(pl)[:50], r, displayed[:3], 'errors:', errs[:2], 'alive:', alive, 'saved:', saved)
            pg.close()
finish('security', fails, f'{runs} attack runs, {fails} failed')
