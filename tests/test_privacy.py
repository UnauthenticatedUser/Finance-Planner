"""Privacy: the page never makes a network request, and its security rule (Content-Security-Policy) is in place.

The tool is used the way a person would: the example is shown, numbers are typed in, both views and both languages
are opened, a backup is exported and imported. Every request the browser tries to make is recorded; the only one
allowed is loading index.html itself.
Run: python tests/test_privacy.py"""
from playwright.sync_api import sync_playwright
from helpers import PAGE, finish

REQUIRED = ["default-src 'none'", "connect-src 'none'", "form-action 'none'", "base-uri 'none'"]

problems = []
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(accept_downloads=True, viewport={'width': 1360, 'height': 900})
    pg = ctx.new_page(); requests = []; errs = []
    pg.on('request', lambda r: requests.append(r.url) if r.url != PAGE else None)
    pg.on('pageerror', lambda e: errs.append(str(e)[:150]))
    pg.goto(PAGE); pg.wait_for_timeout(300)

    csp = pg.evaluate("document.querySelector('meta[http-equiv=Content-Security-Policy]')?.content || ''")
    for rule in REQUIRED:
        if rule not in csp: problems.append('security rule missing: ' + rule)
    if pg.evaluate("document.querySelector('meta[name=referrer]')?.content") != 'no-referrer': problems.append('referrer rule missing')

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
    blocked = pg.evaluate("""async()=>{ try{ await fetch('https://example.com/'); return false; }catch(e){ return true; } }""")
    if not blocked: problems.append('fetch was not blocked')
    requests = [u for u in requests if u != 'https://example.com/']   # the attempt above is refused before it leaves
    if requests: problems.append('network requests: ' + ', '.join(requests[:5]))
    if errs: problems.append('page errors: ' + '; '.join(errs[:2]))
    b.close()

finish('privacy', problems, 'no network requests, security rule in place' if not problems else 'problems: ' + str(problems))
