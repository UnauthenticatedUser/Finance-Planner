"""Updates the script fingerprints in index.html's security rule (Content-Security-Policy).

The rule only lets the browser run scripts whose SHA-256 fingerprint it lists, so any script that isn't the page's own
(for example one injected through a bug) is blocked. Every change to a <script> block changes its fingerprint, so run
this after editing a script, from the repository folder:

    python tools/update_csp.py

It rewrites the script-src part of the rule. With --check it changes nothing and fails if the rule is out of date
(the tests do the same check). The page has exactly two inline scripts (the frame guard and the tool itself); a third
one is refused rather than approved, since it could be something that got in by mistake. Adding one on purpose means
changing SCRIPTS below."""
import base64, hashlib, re, sys
from html.parser import HTMLParser
from pathlib import Path

PAGE = Path(__file__).resolve().parent.parent / 'index.html'
SCRIPTS = 2   # inline scripts the page is meant to have


class _Scripts(HTMLParser):
    """Collects the text of every inline <script> the way a browser reads the page: any letter case, with or without
    attributes, and never from inside an HTML comment."""
    def __init__(self):
        super().__init__(convert_charrefs=False); self.bodies = []; self._in = None
    def handle_starttag(self, tag, attrs):
        if tag == 'script' and not dict(attrs).get('src'): self._in = []
    def handle_data(self, data):
        if self._in is not None: self._in.append(data)
    def handle_endtag(self, tag):
        if tag == 'script' and self._in is not None: self.bodies.append(''.join(self._in)); self._in = None


def fingerprints(html):
    """The CSP fingerprint of every inline script, in page order."""
    parser = _Scripts(); parser.feed(html); parser.close()
    return ["'sha256-" + base64.b64encode(hashlib.sha256(body.encode('utf-8')).digest()).decode() + "'" for body in parser.bodies]


def script_src(html):
    m = re.search(r'(<meta http-equiv="Content-Security-Policy" content="[^"]*?script-src )([^;"]*)', html)
    if not m: sys.exit('No Content-Security-Policy with script-src found in index.html')
    return m


if __name__ == '__main__':
    html = PAGE.read_text(encoding='utf-8'); fps = fingerprints(html)
    if len(fps) != SCRIPTS: sys.exit(f'index.html has {len(fps)} inline scripts, not {SCRIPTS}, so nothing was approved. Check the page by hand.')
    want = ' '.join(fps); m = script_src(html)
    if m.group(2) == want: print('Script fingerprints are up to date.'); sys.exit(0)
    if '--check' in sys.argv: sys.exit('Script fingerprints are out of date: run python tools/update_csp.py')
    PAGE.write_text(html[:m.start(2)] + want + html[m.end(2):], encoding='utf-8')
    print('Updated script-src to:', want)
