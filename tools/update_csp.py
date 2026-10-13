"""Updates the script fingerprints in index.html's security rule (Content-Security-Policy).

The rule only lets the browser run scripts whose SHA-256 fingerprint it lists, so any script that isn't the page's own
(for example one injected through a bug) is blocked. Every change to a <script> block changes its fingerprint, so run
this after editing a script, from the repository folder:

    python tools/update_csp.py

It rewrites the script-src part of the rule. With --check it changes nothing and fails if the rule is out of date
(the tests do the same check)."""
import base64, hashlib, re, sys
from pathlib import Path

PAGE = Path(__file__).resolve().parent.parent / 'index.html'


def fingerprints(html):
    """The CSP fingerprint of every inline <script> block, in page order."""
    return ["'sha256-" + base64.b64encode(hashlib.sha256(body.encode('utf-8')).digest()).decode() + "'"
            for body in re.findall(r'<script>(.*?)</script>', html, re.S)]


def script_src(html):
    m = re.search(r'(<meta http-equiv="Content-Security-Policy" content="[^"]*?script-src )([^;"]*)', html)
    if not m: sys.exit('No Content-Security-Policy with script-src found in index.html')
    return m


if __name__ == '__main__':
    html = PAGE.read_text(encoding='utf-8')
    want = ' '.join(fingerprints(html)); m = script_src(html)
    if m.group(2) == want: print('Script fingerprints are up to date.'); sys.exit(0)
    if '--check' in sys.argv: sys.exit('Script fingerprints are out of date: run python tools/update_csp.py')
    PAGE.write_text(html[:m.start(2)] + want + html[m.end(2):], encoding='utf-8')
    print('Updated script-src to:', want)
