"""Backups: Export, Import, Reset and Undo, in English and Estonian.

Export then Reset then Import gives back exactly the same data and the same numbers on screen; Undo after Reset then
Import restores your data from before the Reset; a broken or oversized file is refused without touching your data; an
imported history month after this one is dropped (this month and duplicates kept once), but opening the tool once with a
wrong clock costs no history; a file of exactly 5 MB is read and one byte more refused; unknown keys are dropped; a file
with only some of a backup's parts is refused; Reset, a display click, Import, Undo brings your data back; on load,
deadline years the editor can't show are cleared, years and ages are whole, an emptied card title gets its name back and
history keeps its newest 1,200 good months; this month's snapshot follows you down to €0 and a full history drops its
oldest month; an old FIRE target gets no health insurance; someone
who entered only their net pay gets the backup reminder too; and every backup format from v1.0.0 on
(tests/fixtures/backup-*.json) still loads with every value kept.
Run: python tests/test_backups.py"""
from playwright.sync_api import sync_playwright
import json, os, tempfile, datetime
from helpers import FIXTURES, PAGE, finish, fixture, launch, on_day, watch_errors, import_file
VIEW_IDS=['proj-big','proj-sub','tgt-note','ret-total','y-tag']
def screen(pg):
    pg.evaluate("()=>{ for(const v of ['progress','overview']) document.querySelector('.viewtabs [data-view='+v+']').click(); }"); pg.wait_for_timeout(150)
    return pg.evaluate("""ids=>{ const c=compute(); return {nums:Object.fromEntries(Object.entries(c).filter(([k,v])=>typeof v==='number')), txt:ids.map(i=>{const e=document.getElementById(i); return e?e.textContent:''}),
       infl:[...document.querySelectorAll('.inflchip')].map(c=>c.textContent+c.getAttribute('aria-pressed')), field:document.querySelector('[data-key=projInflation]').value} }""", VIEW_IDS)
with sync_playwright() as p:
    b=launch(p); fails=[]
    rich=fixture('example.json')
    rich.update(enableProjReal=True, projInflation=3.7, birthYear=1990, enableIncome=True, enableProjNet=True, enableProjRange=True, projGrowth=2)
    rich['incomes']=[{'name':'Travel allowance','amount':1000,'freq':'once','tax':'free','rate':0},{'name':'Rent','amount':300,'freq':'month','tax':'custom','rate':14}]
    rich['targets']=[{'name':'1M','kind':'networth','amount':1000000,'dueMon':'06','dueYear':'2040','rate':4,'current':0,'spend':0},{'name':'FIRE','kind':'fire','amount':0,'rate':3.5,'spend':40000,'current':0,'dueMon':'','dueYear':''}]
    rich['debts']=[{'name':'Mortgage','balance':150000,'rtype':'euribor','rate':0,'margin':1.7,'payment':950,'asset':200000}]
    rich['text']={**rich.get('text',{}), 'pageTitle':'My plan', 'goalsHTML':'<li>Buy <b>flat</b></li>'}
    for lang in ['en','et']:
        ctx=b.new_context(accept_downloads=True, viewport={'width':1300,'height':900}, reduced_motion='reduce'); pg=ctx.new_page(); errs=[]
        watch_errors(pg, errs, n=200)
        def menu(sel):   # top bar buttons sit in the ☰ menu when the bar is compact
            if not pg.is_visible(sel) and pg.is_visible('#moreBtn'): pg.click('#moreBtn')
            pg.click(sel)
        pg.goto(PAGE); pg.wait_for_timeout(200)
        pg.evaluate("s=>localStorage.setItem(KEY, JSON.stringify(s))", rich); pg.reload(); pg.wait_for_timeout(300)
        pg.evaluate("l=>document.querySelector('.langtabs [data-lang='+l+']').click()", lang); pg.wait_for_timeout(150)
        before_state=pg.evaluate("JSON.stringify(state)"); before=screen(pg)
        with pg.expect_download() as d: menu('#exportBtn')
        path=d.value.path(); exported=json.load(open(path)); fname=d.value.suggested_filename
        if json.dumps(exported, sort_keys=True)!=json.dumps(json.loads(before_state), sort_keys=True): fails.append((lang,'export file differs from your data'))
        if exported.get('incomes',[{}])[0].get('freq')!='once' or exported.get('projInflation')!=3.7 or exported.get('enableProjReal') is not True: fails.append((lang,'new settings missing from export'))
        menu('#resetBtn'); pg.wait_for_timeout(300)
        if pg.evaluate("state.targets.length")!=0: fails.append((lang,'reset did not clear'))
        import_file(pg, path)
        after_state=pg.evaluate("JSON.stringify(state)"); after=screen(pg)
        if after_state!=before_state: fails.append((lang,'data after import differs'))
        if after!=before: fails.append((lang,'screen after import differs', [k for k in before if before[k]!=after[k]]))
        if pg.evaluate("localStorage.getItem(KEY)")!=after_state: fails.append((lang,'import not saved'))
        # Undo after Reset then Import brings back your data from before the Reset, not the blank tool (one step); shown with a
        # second, different file
        other=os.path.join(tempfile.mkdtemp(),'other.json'); json.dump({**exported, 'gross':1234}, open(other,'w'))
        menu('#resetBtn'); pg.wait_for_timeout(300); import_file(pg, other)
        if pg.evaluate("state.gross")!=1234: fails.append((lang,'second file not imported'))
        menu('#revertBtn'); pg.wait_for_timeout(300)
        if pg.evaluate("JSON.stringify(state)")!=before_state: fails.append((lang,'undo after reset and import did not bring back your data'))
        if pg.evaluate("getComputedStyle(document.getElementById('revertBtn')).display")!='none': fails.append((lang,'Undo still offered after undoing (it is one step)'))
        import_file(pg, path)
        if pg.evaluate("JSON.stringify(state)")!=before_state: fails.append((lang,'import after undo failed'))
        # broken file: refused, nothing changes
        bad=os.path.join(tempfile.mkdtemp(),'bad.json'); open(bad,'w').write('{not json')
        cur=pg.evaluate("JSON.stringify(state)"); import_file(pg, bad)
        if pg.evaluate("JSON.stringify(state)")!=cur: fails.append((lang,'broken file changed data'))
        note=pg.evaluate("()=>{ const t=document.querySelector('.toast'); return t.hidden ? '' : t.getAttribute('role')+': '+t.textContent; }")
        if not note.startswith('alert: ') or ('backup' not in note and 'varukoopia' not in note): fails.append((lang,'broken file refused without saying why', note))
        # a file far bigger than any backup is refused before it's read, and says why
        big=os.path.join(tempfile.mkdtemp(),'big.json'); json.dump({**exported, 'pad':'x'*(6*1024*1024)}, open(big,'w'))
        import_file(pg, big)
        said=pg.evaluate("()=>{ const t=document.querySelector('.toast'); return t.hidden ? '' : t.textContent; }")
        if pg.evaluate("JSON.stringify(state)")!=cur or '5 MB' not in said: fails.append((lang,'oversized file not refused clearly', said))
        # importing the same file twice in a row still works (file input resets)
        import_file(pg, path); import_file(pg, path)
        if pg.evaluate("JSON.stringify(state)")!=before_state: fails.append((lang,'re-import of same file failed'))
        # an imported history month after this one (an odd file) is dropped
        fut=os.path.join(tempfile.mkdtemp(),'future.json'); json.dump({**exported, 'history':exported.get('history',[])+[{'m':'2999-01','nw':1,'assets':1,'debt':0,'auto':1}]}, open(fut,'w'))
        import_file(pg, fut)
        if pg.evaluate("state.history.some(e=>e.m>thisMonth())"): fails.append((lang,'a future history month was kept'))
        # ...but this month is kept, and a month given twice is kept once
        now_m=pg.evaluate("thisMonth()"); f2=os.path.join(tempfile.mkdtemp(),'months.json')
        json.dump({**exported, 'history':[{'m':'2025-01','nw':1,'assets':1,'debt':0,'auto':0}, {'m':'2025-01','nw':2,'assets':2,'debt':0,'auto':0}, {'m':now_m,'nw':3,'assets':3,'debt':0,'auto':0}]}, open(f2,'w'))
        import_file(pg, f2)
        got=pg.evaluate("state.history.map(e=>[e.m, e.nw])")   # this month as the file has it (not a fresh snapshot made after dropping it)
        if got!=[['2025-01', 1], [now_m, 3]]: fails.append((lang,'history months after import', got))
        refused=lambda: pg.evaluate("()=>{ const t=document.querySelector('.toast'); return !t.hidden && t.classList.contains('problem'); }")
        # the size limit exactly: a 5 MB file is read (its unknown keys, also in the card titles, dropped and so not exported again),
        # one byte more is refused
        for extra in (0, 1):
            body={**exported, 'evil':1, 'text':{**exported['text'], 'evilT':'x'}, 'pad':''}; n=5*1024*1024-len(json.dumps(body).encode())+extra
            fb=os.path.join(tempfile.mkdtemp(),'edge.json'); open(fb,'w').write(json.dumps({**body, 'pad':'x'*n})); assert os.path.getsize(fb)==5*1024*1024+extra
            pg.evaluate("()=>document.querySelector('.toast').hidden=true"); import_file(pg, fb)
            kept=pg.evaluate("()=>['evil','pad'].filter(k=>k in state).concat('evilT' in state.text ? ['evilT'] : [])")
            if extra==0 and (refused() or kept): fails.append((lang,'a file of exactly 5 MB', 'refused' if refused() else 'kept '+str(kept)))
            if extra==1 and not refused(): fails.append((lang,'a file one byte over 5 MB was read'))
        # valid JSON with only some of a backup's parts isn't a backup
        fs=os.path.join(tempfile.mkdtemp(),'some.json'); json.dump({'gross':5, 'accounts':[]}, open(fs,'w')); cur=pg.evaluate("JSON.stringify(state)")
        pg.evaluate("()=>document.querySelector('.toast').hidden=true"); import_file(pg, fs)
        if not refused() or pg.evaluate("JSON.stringify(state)")!=cur: fails.append((lang,'a file with only some of a backup\'s parts was taken'))
        # Reset, then a display choice (30y), then Import, then Undo: your data from before the Reset
        import_file(pg, path)
        menu('#resetBtn'); pg.wait_for_timeout(300); pg.evaluate("[...document.querySelectorAll('#yrbtns button')].find(b=>b.dataset.yr==='30').click()"); pg.wait_for_timeout(200)
        import_file(pg, other); menu('#revertBtn'); pg.wait_for_timeout(300)
        if pg.evaluate("JSON.stringify(state)")!=before_state: fails.append((lang,'Reset, a display click, Import, Undo did not bring back your data'))
        import_file(pg, path)
        # backups saved by earlier versions (from v1.0.0 on) load without errors and without any change to their data
        for f in sorted(FIXTURES.glob('backup-*.json')):
            n0=len(errs); import_file(pg, f)
            if len(errs)>n0: fails.append((lang,'old file '+f.name+' error: '+errs[-1]))
            # (this month's net worth snapshot is kept up to date automatically, so it is left out of the comparison)
            # every value in the file is kept exactly; newer versions may only add settings it didn't have yet
            same=pg.evaluate("""file=>{ const m=thisMonth(), kept=(a,b)=> Array.isArray(a) ? Array.isArray(b) && a.length===b.length && a.every((x,i)=>kept(x,b[i]))
                : a && typeof a==='object' ? !!b && typeof b==='object' && Object.keys(a).every(k=>kept(a[k],b[k])) : a===b;
              const drop=s=>({...s, history:(s.history||[]).filter(e=>e.m!==m)});
              return kept(drop(file), drop(state)) && kept(file, normalize(file)); }""", json.loads(f.read_text(encoding='utf-8')))
            if not same: fails.append((lang,'old file '+f.name+' changed when loaded'))
            # what a file doesn't have gets its default: FIRE targets from before v1.1.0 have no health insurance setting, so "no"
            if f.name=='backup-v1.0.0.json' and pg.evaluate("state.targets.filter(t=>t.kind==='fire').map(t=>t.health)")!=['no']: fails.append((lang,'an old FIRE target got health insurance'))
        if errs: fails.append((lang,'page errors', errs[:2]))
        print(lang, 'export file name:', fname, '| page errors:', errs or 'none')
        ctx.close()
    # a clock that's wrong once (a year behind) costs no history: your own data keeps every month, only an imported file drops later ones
    ctx=b.new_context(); pg=ctx.new_page(); pg.goto(PAGE); pg.wait_for_timeout(300)
    months=pg.evaluate("""()=>{ const h=[]; for(let i=11;i>=0;i--){ const d=new Date(); d.setDate(1); d.setMonth(d.getMonth()-i); h.push({m:ym(d), nw:1000*i, assets:1000*i, debt:0, auto:0}); }
        state.accounts=[{name:'a', amount:5000, yield:0}]; state.enableHistory=true; state.history=h; save(); return h.map(e=>e.m); }""")
    pg.close(); year_ago=(datetime.date.today()-datetime.timedelta(days=365)).isoformat()
    pg=on_day(ctx.new_page(), year_ago); pg.goto(PAGE); pg.wait_for_timeout(400); pg.close()
    pg=ctx.new_page(); pg.goto(PAGE); pg.wait_for_timeout(400)
    kept=pg.evaluate("state.history.map(e=>e.m)")
    if not set(months)<=set(kept): fails.append(('a wrong clock dropped history months', sorted(set(months)-set(kept))))
    # what a file holds is made something the editor can show: a deadline year it can't (9999, 0000) is cleared, years and ages
    # are whole, a card title left empty gets its name back; history keeps its newest 1,200 good months (junk rows don't count)
    junk=[{'m':'junk','nw':1}]*50; months_=[f'{1900+i//12}-{i%12+1:02d}' for i in range(1300)]
    q=pg.evaluate("""s=>{ const m=normalize(s); return {due:m.targets.map(t=>t.dueYear), by:m.birthYear, ret:m.retireAge, title:m.text.titleCash, h:[m.history.length, m.history[0].m, m.history.at(-1).m]}; }""",
                  {'birthYear':1990.5, 'retireAge':64.6, 'text':{'titleCash':'  '}, 'history':junk+[{'m':m,'nw':1,'assets':1,'debt':0,'auto':0} for m in months_],
                   'targets':[{'kind':'cash','amount':1,'dueMon':'06','dueYear':'9999'}, {'kind':'cash','amount':1,'dueMon':'06','dueYear':'0000'}, {'kind':'cash','amount':1,'dueMon':'06','dueYear':'2030'}]})
    if q!={'due':['','','2030'], 'by':1991, 'ret':65, 'title':'Cash & savings', 'h':[1200, months_[100], months_[-1]]}: fails.append(('a file cleaned on load', q))
    # this month's snapshot follows you down to €0; a full history drops its oldest month for a new one
    h=pg.evaluate("""()=>{ localStorage.clear(); state=normalize({accounts:[{name:'A', amount:1000, yield:0}], etfs:[], text:{}, gross:0, enableHistory:true}); refreshAll();
        const a=state.history.at(-1).nw; state.accounts[0].amount=0; refreshAll(); const z=state.history.at(-1).nw;
        state.history=Array.from({length:1200}, (_,i)=>({m:(1800+Math.floor(i/12))+'-'+String(i%12+1).padStart(2,'0'), nw:1, assets:1, debt:0, auto:0})); state.accounts[0].amount=5; refreshAll();
        return [a, z, state.history.length, state.history[0].m, state.history.at(-1).m===thisMonth()]; }""")
    if h!=[1000, 0, 1200, '1800-02', True]: fails.append(('history snapshot and limit', h))
    # the backup reminder: someone who entered only their net pay is reminded too (7 days after starting, never exported)
    pg.evaluate("""()=>{ localStorage.clear(); state=normalize({gross:0, autoNet:false, manualNet:2000, accounts:[], etfs:[], text:{}}); save();
        writeJSON(KEY_META, {firstData:Date.now()-8*DAY}); }"""); pg.reload(); pg.wait_for_timeout(400)
    if pg.evaluate("document.getElementById('exportNotice').hidden"): fails.append(('no backup reminder for someone with only their net pay',))
    # what a file holds that isn't a number gets the default, not 0 (no income tax); a deadline month picked before its year stays;
    # history months need a real year; a 2nd pillar at 0% is "Not joined", so the state adds nothing either
    q=pg.evaluate("""()=>{ const m=normalize({taxRate:null, retireAge:'abc', expenses:'1200', targets:[{kind:'cash', amount:1, dueMon:'03', dueYear:''}],
        history:[{m:'0001-01', nw:1}, {m:'2025-06', nw:2}]}); state=normalize({gross:3000, enableP2:true, p2rate:0}); refreshAll();
      return [m.taxRate, m.retireAge, m.expenses, m.targets[0].dueMon, m.history.map(e=>e.m), compute().aStateP2]; }""")
    if q!=[22, 65, 1200, '03', ['2025-06'], 0]: fails.append(('defaults, a lone deadline month, history years or a 2nd pillar at 0%', q))
    # the clock set back to a month you already saved: that month stays as it was, and a full history isn't saved over and over
    pg.close(); pg=on_day(ctx.new_page(), '2026-03-15'); pg.goto(PAGE); pg.wait_for_timeout(300)
    q=pg.evaluate("""()=>{ state=normalize({accounts:[{name:'a', amount:5000, yield:0}], enableHistory:true, history:[{m:'2026-03', nw:111, assets:111, debt:0, auto:1}, {m:'2026-08', nw:222, assets:222, debt:0, auto:1}]});
        refreshAll(); const kept=state.history[0].nw; state.history=Array.from({length:1200}, (_,i)=>({m:(1950+Math.floor(i/12))+'-'+String(i%12+1).padStart(2,'0'), nw:1, assets:1, debt:0, auto:0}));
        const again=[recordHistory(compute()), recordHistory(compute())];
        state=normalize({enableHistory:true, history:[{m:'2026-03', nw:0, assets:0, debt:0, auto:1}]}); refreshAll();
        const dot=document.querySelector('#hist-chart .hdot'); return [kept, again, dot ? dot.getAttribute('data-tip') : '']; }""")
    if q[0]!=111 or q[1]!=[False, False] or 'entered by you' in q[2]: fails.append(('a past month kept, no saving loop, an automatic €0 month', q))
    # Reset, then only monthly saving entered, then Reset again: Undo brings back that saving; Reset on an empty tool offers no Undo
    pg.close(); pg=ctx.new_page(); pg.goto(PAGE); pg.wait_for_timeout(300)
    q=pg.evaluate("""()=>{ localStorage.clear(); backup=null; state=normalize({gross:3000}); refreshAll(); document.getElementById('resetBtn').click();
        state.etfMonthly=300; state.thirdPillar=100; save(); refreshAll(); document.getElementById('resetBtn').click(); document.getElementById('revertBtn').click();
        const kept=[state.etfMonthly, state.thirdPillar]; localStorage.clear(); backup=null; state=blankState(state); refreshAll(); document.getElementById('resetBtn').click();
        return [kept, !!backup, getComputedStyle(document.getElementById('revertBtn')).display]; }""")
    if q!=[[300, 100], False, 'none']: fails.append(('Undo after Reset: saving lost, or an empty Undo offered', q))
    # notes cut to the limit when loaded stay editable (closing tags added by the cleaning used to push them over it)
    q=pg.evaluate("""()=>{ state=normalize({text:{goalsHTML:'<b>'+'x'.repeat(NOTES_MAX-2)+'</b>'}}); refreshAll(); const n=document.getElementById('goalsList');
        n.focus(); getSelection().selectAllChildren(n); getSelection().collapseToEnd(); document.execCommand('delete'); return [state.text.goalsHTML.length<=NOTES_MAX, n.innerHTML===state.text.goalsHTML]; }""")
    if q!=[True, True]: fails.append(('notes over the limit after loading', q))
    ctx.close()
    finish('backups', fails, 'problems: '+(str(fails) if fails else 'none'))
