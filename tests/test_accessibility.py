"""Accessibility: the core checks from the WCAG guidelines, on the empty tool and the example, in both languages, with
every section of the editor open.

- the page language is set, and there is a "Skip to content" link that leads to the dashboard
- every button, input, dropdown and link has a name a screen reader can announce (a placeholder that's only a number isn't one)
- no two elements share an id, and every aria reference points to an element that exists
- text has enough contrast against its background (4.5:1, or 3:1 for large text)
- keyboard focus is visible on every button, field, link, section header, editable text, help you can Tab to and switch,
  on both views: it looks different focused than not; a name has letters or digits ("×" alone isn't one)
- the dashboard's explanations can be reached with Tab and are read by screen readers (chart parts and history dots repeat
  what their legend or rows say); a field's help is read with it; a row's buttons say which row ("Remove fund “Global
  equity”"), a type dropdown is named "Type", name suggestions are a combobox, the view tabs control their panels and the
  language buttons are pressed buttons
- with reduced motion nothing moves (the target bars too), and the invested share's box is at least 24px wide at 0%
Run: python tests/test_accessibility.py"""
from playwright.sync_api import sync_playwright
from helpers import PAGE, finish, launch

CHECK = r"""()=>{
  const out=[], vis=e=>!!(e.offsetWidth||e.offsetHeight||e.getClientRects().length) && getComputedStyle(e).visibility!=='hidden';
  const name=e=>[(e.getAttribute('aria-label')||'').trim() || (e.getAttribute('aria-labelledby')||'').split(/\s+/).map(i=>document.getElementById(i)?.textContent||'').join(' ').trim()
    || (e.labels && [...e.labels].map(l=>l.textContent).join(' ').trim()) || (e.textContent||'').trim() || (e.getAttribute('title')||'').trim() ].find(n=>/[\p{L}\p{N}]/u.test(n)) || [(e.getAttribute('placeholder')||'').trim()].find(n=>/\p{L}/u.test(n)) || '';   // a name has letters or digits ("×" or "↑" alone isn't one); a placeholder needs letters (a number there is an automatic value)
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
    const need= e.matches(':disabled, [disabled] *, .chart *') ? 0 : large?3:4.5;
    if(ratio<need){ const k=e.textContent.trim().slice(0,30)+' '+ratio.toFixed(2); if(!seen.has(k)){ seen.add(k); out.push('low contrast '+ratio.toFixed(2)+': "'+e.textContent.trim().slice(0,40)+'"'); } } });
  return out; }"""

SEMANTICS = r"""()=>{ const out=[], vis=e=>!!e.getClientRects().length;
  document.querySelectorAll('.main [data-tip]:not([data-tip=""])').forEach(e=>{ if(!vis(e) || e.matches('button, .dseg, .dring, .hdot, .fn, .bar *')) return;
    if(e.tabIndex<0 || !e.getAttribute('aria-description')) out.push('mouse-only explanation: '+(e.id||e.className||e.tagName)+' '+e.textContent.trim().slice(0,30)); });
  document.querySelectorAll('[data-tip][aria-description]').forEach(e=>{ if(e.getAttribute('data-tip')!==e.__fixedTip && e.getAttribute('aria-description')!==e.getAttribute('data-tip')) out.push('screen readers hear an old tip: '+(e.id||e.className)); });
  document.querySelectorAll('.editor label[data-tip] input, .editor .field > label[data-tip] + .inwrap input').forEach(i=>{ if(!i.getAttribute('aria-description')) out.push('field help not read: '+(i.id||i.className)); });
  document.querySelectorAll('.editor .invtop').forEach(r=>{ const n=(r.querySelector('.invname')||{}).value, d=r.querySelector('.iconbtn:not(.mv)');
    if(n && d && !d.getAttribute('aria-label').includes(n)) out.push('remove button without its row: '+d.getAttribute('aria-label'));
    const s=r.querySelector('.cselect'); if(s && s.getAttribute('aria-label')!==L('Type','Tüüp')) out.push('type dropdown named '+s.getAttribute('aria-label')); });
  document.querySelectorAll('.editor .hassuggest').forEach(i=>{ if(i.getAttribute('role')!=='combobox' || !i.hasAttribute('aria-expanded') || !document.getElementById(i.getAttribute('aria-controls'))) out.push('suggestions without combobox roles'); });
  document.querySelectorAll('[role=tab]').forEach(b=>{ const p=document.getElementById(b.getAttribute('aria-controls')); if(!p || p.getAttribute('role')!=='tabpanel') out.push('tab without its panel: '+b.textContent); });
  if([...document.querySelectorAll('.langtabs button')].some(b=>!b.hasAttribute('aria-pressed'))) out.push('language buttons are not pressed buttons');
  const bar=document.querySelector('.tfill'); if(bar && getComputedStyle(bar).transitionDuration!=='0s') out.push('target bar moves with reduced motion');
  const share=document.getElementById('sr-inv-pct'); if(share.offsetWidth && share.offsetWidth<24) out.push('invested share box '+share.offsetWidth+'px wide');
  return [...new Set(out)].slice(0,8); }"""

FOCUS = r"""()=>{ const out=[], still=document.createElement('style');   // no transitions, so a style is read as it ends up
  still.textContent='*,*::before,*::after{transition:none!important; animation:none!important}'; document.head.append(still);
  // the browser's own ring (outline "auto": thin and dark, lost on this dark page) doesn't count, only the tool's own focus style
  const look=e=>{ const cs=getComputedStyle(e); return [/^(none|auto)$/.test(cs.outlineStyle) || !parseFloat(cs.outlineWidth) ? 'none' : cs.outlineStyle+' '+cs.outlineWidth+' '+cs.outlineColor, cs.boxShadow, cs.borderColor, cs.backgroundColor, cs.color, cs.opacity, cs.top].join('|'); };   // top: the skip link comes onto the screen
  // buttons, fields, links, section headers, editable text, help you can Tab to, and switches (their track shows it)
  document.querySelectorAll('button, input[type=text], a[href], summary, [contenteditable=true], [tabindex="0"], .switch input').forEach(e=>{
    const shows=e.matches('.switch input') ? e.nextElementSibling : e;
    if(!(shows.offsetWidth||shows.offsetHeight) || e.disabled) return;
    e.blur(); const before=look(shows); e.focus({focusVisible:true});
    if(document.activeElement===e && e.matches(':focus-visible') && look(shows)===before) out.push('no visible focus: '+e.outerHTML.slice(0,80));   // a browser that doesn't show keyboard focus here isn't judged
    e.blur(); });
  still.remove(); return out.slice(0,10); }"""

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
                for issue in pg.evaluate(CHECK) + pg.evaluate(FOCUS) + pg.evaluate(SEMANTICS):   # both views: some controls are only on Progress
                    msg = f'{lang} {"example" if example else "empty"} {view}: {issue}'
                    if msg not in problems: problems.append(msg)
            # a tip that changes with your numbers is read as it is now (the 3rd pillar's, with a 20% tax rate and over its limit)
            p3 = pg.evaluate("()=>{ state=normalize({gross:1000, taxRate:20, thirdPillar:500}); refreshAll(); const e=document.getElementById('out-p3'); return [e.getAttribute('aria-description'), e.getAttribute('data-tip')]; }")
            if p3[0] != p3[1]: problems.append(f'{lang}: screen readers hear an old 3rd pillar tip: {p3[0][:50]!r}')
            pg.close()
    b.close()

for m in problems[:25]: print(' ', m)
finish('accessibility', problems, f'{len(problems)} problems' if problems else 'names, ids, contrast, focus, explanations and skip link all fine')
