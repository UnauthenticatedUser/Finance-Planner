"""Backups: Export, Import, Reset and Undo, in English and Estonian.

Export then Reset then Import gives back exactly the same data and the same numbers on screen; Undo after an import
restores what was there; a broken or oversized file is refused without touching your data; and every backup format from v1.0.0
on (tests/fixtures/backup-*.json) still loads with every value kept.
Run: python tests/test_backups.py"""
from playwright.sync_api import sync_playwright
import json, os, tempfile
from helpers import PAGE, FIXTURES, fixture, finish, launch
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
        pg.on('pageerror', lambda e: errs.append(str(e)[:200])); pg.on('dialog', lambda d: d.accept())
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
        pg.set_input_files('#importFile', path); pg.wait_for_timeout(400)
        after_state=pg.evaluate("JSON.stringify(state)"); after=screen(pg)
        if after_state!=before_state: fails.append((lang,'data after import differs'))
        if after!=before: fails.append((lang,'screen after import differs', [k for k in before if before[k]!=after[k]]))
        if pg.evaluate("localStorage.getItem(KEY)")!=after_state: fails.append((lang,'import not saved'))
        # Undo after import brings back what was there before it (one step)
        menu('#revertBtn'); pg.wait_for_timeout(300)
        if pg.evaluate("state.targets.length")!=0: fails.append((lang,'undo after import did not go back'))
        if pg.evaluate("getComputedStyle(document.getElementById('revertBtn')).display")!='none': fails.append((lang,'Undo still offered after undoing (it is one step)'))
        pg.set_input_files('#importFile', path); pg.wait_for_timeout(300)
        if pg.evaluate("JSON.stringify(state)")!=before_state: fails.append((lang,'import after undo failed'))
        # broken file: refused, nothing changes
        bad=os.path.join(tempfile.mkdtemp(),'bad.json'); open(bad,'w').write('{not json')
        cur=pg.evaluate("JSON.stringify(state)"); pg.set_input_files('#importFile', bad); pg.wait_for_timeout(300)
        if pg.evaluate("JSON.stringify(state)")!=cur: fails.append((lang,'broken file changed data'))
        # a file far bigger than any backup is refused before it's read, and says why
        big=os.path.join(tempfile.mkdtemp(),'big.json'); json.dump({**exported, 'pad':'x'*(6*1024*1024)}, open(big,'w'))
        said=[]; pg.once('dialog', lambda d: said.append(d.message))
        pg.set_input_files('#importFile', big); pg.wait_for_timeout(300)
        if pg.evaluate("JSON.stringify(state)")!=cur or not said or '5 MB' not in said[0]: fails.append((lang,'oversized file not refused clearly', said[:1]))
        # importing the same file twice in a row still works (file input resets)
        pg.set_input_files('#importFile', path); pg.wait_for_timeout(300); pg.set_input_files('#importFile', path); pg.wait_for_timeout(300)
        if pg.evaluate("JSON.stringify(state)")!=before_state: fails.append((lang,'re-import of same file failed'))
        # backups saved by earlier versions (from v1.0.0 on) load without errors and without any change to their data
        for f in sorted(FIXTURES.glob('backup-*.json')):
            n0=len(errs); pg.set_input_files('#importFile', str(f)); pg.wait_for_timeout(250)
            if len(errs)>n0: fails.append((lang,'old file '+f.name+' error: '+errs[-1]))
            # (this month's net worth snapshot is kept up to date automatically, so it is left out of the comparison)
            # every value in the file is kept exactly; newer versions may only add settings it didn't have yet
            same=pg.evaluate("""file=>{ const m=thisMonth(), kept=(a,b)=> Array.isArray(a) ? Array.isArray(b) && a.length===b.length && a.every((x,i)=>kept(x,b[i]))
                : a && typeof a==='object' ? !!b && typeof b==='object' && Object.keys(a).every(k=>kept(a[k],b[k])) : a===b;
              const drop=s=>({...s, history:(s.history||[]).filter(e=>e.m!==m)});
              return kept(drop(file), drop(state)) && kept(file, normalize(file)); }""", json.loads(f.read_text(encoding='utf-8')))
            if not same: fails.append((lang,'old file '+f.name+' changed when loaded'))
        if errs: fails.append((lang,'page errors', errs[:2]))
        print(lang, 'export file name:', fname, '| page errors:', errs or 'none')
        ctx.close()
    finish('backups', fails, 'problems: '+(str(fails) if fails else 'none'))
