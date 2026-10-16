"""Privacy: the page never makes a network request, and its security rule (Content-Security-Policy) is in place: it
blocks all network access and only lets the page's own two scripts run, identified by their SHA-256 fingerprints. The
whole rule is compared, so a loosened part (an image allowed from the web, say) fails too.

The tool is used the way a person would: the example is shown, numbers are typed in, both views and both languages
are opened, a backup is exported and imported. Every request the browser tries to make, from the page or anything it
opens, is recorded; the only one allowed is loading index.html itself. No window or tab may open and the page may not
navigate anywhere (the security rule can't stop those, so they're the way data could still leave). A fetch the page tries
must be stopped by the security rule itself, not just fail because there's no network.
Run: python tests/test_privacy.py"""
from playwright.sync_api import sync_playwright
import sys
from helpers import PAGE, ROOT, finish, launch
sys.path.insert(0, str(ROOT / 'tools'))
from update_csp import fingerprints

# the whole rule, word for word; {scripts} is the fingerprints of the page's two scripts
RULE = "default-src 'none'; script-src {scripts}; style-src 'unsafe-inline'; font-src data:; img-src data: blob:; connect-src 'none'; form-action 'none'; base-uri 'none'"

problems = []
with sync_playwright() as p:
    b = launch(p)
    ctx = b.new_context(accept_downloads=True, viewport={'width': 1360, 'height': 900})
    requests = []; errs = []; opened = []; away = []
    ctx.on('request', lambda r: requests.append(r.url) if r.url != PAGE else None)   # popups and frames too
    ctx.on('page', lambda q: opened.append(q))
    pg = ctx.new_page(); opened.clear(); pg.add_init_script("document.addEventListener('securitypolicyviolation', e=>(window.__csp=window.__csp||[]).push(e.violatedDirective))")
    pg.on('framenavigated', lambda f: away.append(f.url) if f == pg.main_frame and f.url not in (PAGE, 'about:blank') else None)
    pg.on('pageerror', lambda e: errs.append(str(e)[:150]))
    pg.goto(PAGE); pg.wait_for_timeout(300)

    csp = pg.evaluate("document.querySelector('meta[http-equiv=Content-Security-Policy]')?.content || ''")
    fps = fingerprints((ROOT / 'index.html').read_text(encoding='utf-8'))
    if len(fps) != 2: problems.append(f'the page has {len(fps)} inline scripts, not 2')
    if csp != RULE.format(scripts=' '.join(fps)): problems.append('security rule differs from the expected one: ' + csp.replace(' '.join(fps), '{scripts}'))
    if pg.evaluate("document.querySelector('meta[name=referrer]')?.content") != 'no-referrer': problems.append('referrer rule missing')
    script_src = csp.split('script-src', 1)[1].split(';', 1)[0].split() if 'script-src' in csp else []
    if "'unsafe-inline'" in script_src: problems.append("script-src still allows any inline script")
    if script_src != fingerprints((ROOT / 'index.html').read_text(encoding='utf-8')):
        problems.append('script fingerprints are out of date: run python tools/update_csp.py')
    # a script that isn't one of the page's own must not run, even when something manages to put it into the page
    pg.evaluate("()=>{ const s=document.createElement('script'); s.textContent='window.__injected=1'; document.body.appendChild(s); }"); pg.wait_for_timeout(100)
    if pg.evaluate("!!window.__injected"): problems.append('an injected script ran')

    pg.click('#exampleBtn'); pg.wait_for_timeout(600)
    pg.click('#exampleBtn'); pg.wait_for_timeout(300)   # back to your own (empty) tool
    pg.evaluate("document.querySelector('[data-sec=income]').open=true")
    pg.fill('[data-key=gross]', '3500'); pg.wait_for_timeout(200)
    for lang in ('et', 'en'):
        pg.click(f'.langtabs [data-lang={lang}]'); pg.wait_for_timeout(200)
        for view in ('progress', 'overview'):
            pg.click(f'.viewtabs [data-view={view}]'); pg.wait_for_timeout(300)
    pg.evaluate("document.querySelectorAll('details').forEach(d=>d.open=true)"); pg.wait_for_timeout(300)
    with pg.expect_download() as d: pg.click('#exportBtn')
    pg.set_input_files('#importFile', d.value.path()); pg.wait_for_timeout(400)

    # the page's own code is blocked from reaching the network even when it tries
    blocked = pg.evaluate("""async()=>{ try{ await fetch('https://example.com/'); return false; }catch(e){ await new Promise(ok=>setTimeout(ok, 300)); return (window.__csp||[]).includes('connect-src'); } }""")   # the rule reports it just after
    if not blocked: problems.append('fetch was not stopped by the security rule')
    requests = [u for u in requests if u != 'https://example.com/']   # the attempt above is refused before it leaves
    if requests: problems.append('network requests: ' + ', '.join(requests[:5]))
    if opened: problems.append('a window or tab opened: ' + ', '.join(q.url for q in opened[:3]))
    if away: problems.append('the page navigated to ' + ', '.join(away[:3]))
    if errs: problems.append('page errors: ' + '; '.join(errs[:2]))
    b.close()

finish('privacy', problems, 'no network requests, security rule in place' if not problems else 'problems: ' + str(problems))
