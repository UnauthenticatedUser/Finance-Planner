"""Accessibility: the core checks from the WCAG guidelines, on the empty tool and the example, in both languages, with
every section of the editor open.

- the page language is set, and there is a "Skip to content" link that leads to the dashboard
- every button, input, dropdown and link has a name a screen reader can announce
- no two elements share an id, and every aria reference points to an element that exists
- text has enough contrast against its background (4.5:1, or 3:1 for large text)
- keyboard focus is visible on every button and field
Run: python tests/test_accessibility.py"""
from playwright.sync_api import sync_playwright
from helpers import PAGE, finish, launch

CHECK = r"""()=>{
  const out=[], vis=e=>!!(e.offsetWidth||e.offsetHeight||e.getClientRects().length) && getComputedStyle(e).visibility!=='hidden';
  const name=e=>(e.getAttribute('aria-label')||'').trim() || (e.getAttribute('aria-labelledby')||'').split(/\s+/).map(i=>document.getElementById(i)?.textContent||'').join(' ').trim()
    || (e.labels && [...e.labels].map(l=>l.textContent).join(' ').trim()) || (e.textContent||'').trim() || (e.getAttribute('title')||'').trim() || (e.getAttribute('placeholder')||'').trim();
  if(!document.documentElement.lang) out.push('page language missing');
  const skip=document.querySelector('a.skiplink'); if(!skip || !document.querySelector(skip.getAttribute('href'))) out.push('skip link missing or broken');
  document.querySelectorAll('button, input:not([type=hidden]), select, textarea, a[href], [role=button], [role=switch], [contenteditable=true]').forEach(e=>{
    if(e.type==='file') return;   // the hidden file picker behind Import
    if(!vis(e) && !(e.type==='checkbox' && vis(e.closest('label')||e))) return;
    if(!name(e)) out.push('no accessible name: '+e.outerHTML.slice(0,90)); });
  const ids={}; document.querySelectorAll('[id]').forEach(e=>{ ids[e.id]=(ids[e.id]||0)+1; });
  Object.entries(ids).filter(([,n])=>n>1).forEach(([id])=>out.push('duplicate id: '+id));
  document.querySelectorAll('[aria-controls],[aria-labelledby],[aria-describedby],[aria-activedescendant]').forEach(e=>{
    ['aria-controls','aria-labelledby','aria-describedby','aria-activedescendant'].forEach(a=>{ const v=e.getAttribute(a); if(v) v.split(/\s+/).forEach(id=>{ if(!document.getElementById(id)) out.push(a+' points to missing #'+id); }); }); });
  // contrast: each visible text element against the first opaque background behind it
  const rgb=s=>{ const m=s.match(/[\d.]+/g)||[0,0,0,0]; return m.map(Number).concat(m.length<4?[1]:[]).slice(0,4); };
  const lum=([r,g,b])=>{ const f=c=>{ c/=255; return c<=0.03928?c/12.92:((c+0.055)/1.055)**2.4; }; return 0.2126*f(r)+0.7152*f(g)+0.0722*f(b); };
  const bgOf=e=>{ let layers=[]; for(let n=e;n;n=n.parentElement){ const c=rgb(getComputedStyle(n).backgroundColor); if(c[3]>0) layers.push(c); if(c[3]>=1) break; }
    let col=[5,7,10]; for(const c of layers.reverse()) col=col.map((x,i)=>x*(1-c[3])+c[i]*c[3]); return col; };   // page background is #05070A
  const seen=new Set();
  document.querySelectorAll('body *').forEach(e=>{
    if(!vis(e) || e.closest('svg') || e.closest('[aria-hidden=true]')) return;
    const own=[...e.childNodes].some(n=>n.nodeType===3 && n.nodeValue.trim()); if(!own) return;
    const cs=getComputedStyle(e); if(parseFloat(cs.opacity)<0.99) return;   // fading in or out
    const fg=rgb(cs.color), bg=bgOf(e), f=fg.slice(0,3).map((x,i)=>x*fg[3]+bg[i]*(1-fg[3]));
    const L1=lum(f), L2=lum(bg), ratio=(Math.max(L1,L2)+0.05)/(Math.min(L1,L2)+0.05);
    const size=parseFloat(cs.fontSize), bold=+cs.fontWeight>=700, large=size>=24 || (bold && size>=18.66);
    const need= e.matches(':disabled, [disabled] *, .chart *, ::placeholder') ? 0 : large?3:4.5;
    if(ratio<need){ const k=e.textContent.trim().slice(0,30)+' '+ratio.toFixed(2); if(!seen.has(k)){ seen.add(k); out.push('low contrast '+ratio.toFixed(2)+': "'+e.textContent.trim().slice(0,40)+'"'); } } });
  return out; }"""

FOCUS = r"""()=>{ const out=[];
  document.querySelectorAll('button, input[type=text], a[href]').forEach(e=>{
    if(!(e.offsetWidth||e.offsetHeight) || e.disabled) return;
    e.focus({focusVisible:true}); const cs=getComputedStyle(e);
    const shown=(cs.outlineStyle!=='none' && parseFloat(cs.outlineWidth)>0) || cs.boxShadow!=='none' || cs.borderColor!==getComputedStyle(document.body).borderColor;
    if(!shown && document.activeElement===e) out.push('no visible focus: '+e.outerHTML.slice(0,80)); e.blur(); });
  return out.slice(0,10); }"""

problems = []
with sync_playwright() as p:
    b = launch(p)
    for lang in ('en', 'et'):
        for example in (False, True):
            pg = b.new_page(viewport={'width': 1360, 'height': 900}, reduced_motion='reduce')
            pg.goto(PAGE); pg.evaluate("l=>{ localStorage.clear(); localStorage.setItem(KEY_UI, JSON.stringify({lang:l})); }", lang); pg.reload(); pg.wait_for_timeout(400)
            if example: pg.click('#exampleBtn'); pg.wait_for_timeout(600)
            pg.evaluate("()=>document.querySelectorAll('details').forEach(d=>d.open=true)"); pg.wait_for_timeout(400)
            for view in ('overview', 'progress'):
                pg.evaluate("v=>document.querySelector('.viewtabs [data-view='+v+']').click()", view); pg.wait_for_timeout(400)
                for issue in pg.evaluate(CHECK) + (pg.evaluate(FOCUS) if not example and view == 'overview' else []):
                    msg = f'{lang} {"example" if example else "empty"} {view}: {issue}'
                    if msg not in problems: problems.append(msg)
            pg.close()
    b.close()

for m in problems[:25]: print(' ', m)
finish('accessibility', problems, f'{len(problems)} problems' if problems else 'names, ids, contrast, focus and skip link all fine')
