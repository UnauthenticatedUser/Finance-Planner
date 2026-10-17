"""Shared setup for the tests: where the planner and the example data are, and how a test reports its result.

Every test opens index.html from this repository in a headless browser through Playwright (Chromium, unless the
BROWSER environment variable says firefox or webkit) and checks the tool's own results against calculations written
separately in Python. Nothing is fetched from the internet. With the TODAY environment variable (for example
TODAY=2027-01-01) the tests run as if it were that day: the page's clock and the Python models' date.today() both say so
(only date.today(): tests use that, not datetime.now())."""
import json, os, random, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = (ROOT / 'index.html').as_uri()
FIXTURES = Path(__file__).resolve().parent / 'fixtures'
BROWSER = os.environ.get('BROWSER', 'chromium')   # chromium, firefox or webkit (Safari's engine)
TODAY = os.environ.get('TODAY')   # a day to run the tests on, YYYY-MM-DD; the real date when not set

if TODAY:   # the Python models' today
    import datetime as _dt
    _day = _dt.date.fromisoformat(TODAY)
    class _Date(_dt.date):
        @classmethod
        def today(cls): return cls(_day.year, _day.month, _day.day)
    _dt.date = _Date


# Shifts the page's Date to TODAY at noon (local time) and lets it run on from there; timers and animations are untouched.
# A function, not a class, so Date() without "new" still gives the (shifted) time as text, as the real one does.
_SHIFT = """(target=>{ const D=Date, off=new D(target).getTime()-D.now();
  function Shifted(...a){ return new.target ? new D(...(a.length ? a : [D.now()+off])) : new D(D.now()+off).toString(); }
  Shifted.prototype=D.prototype; Object.setPrototypeOf(Shifted, D); Shifted.now=()=>D.now()+off;
  globalThis.Date=Shifted; })(%s)"""


def on_day(pg, day):
    """A page (or a browser context) whose date starts at noon on `day` (YYYY-MM-DD) and runs on, from its next load."""
    pg.add_init_script(_SHIFT % json.dumps(day + 'T12:00:00')); return pg


class _OnDay:
    """The browser, with every new page's date starting at noon on TODAY and running on."""
    def __init__(self, b): self._b = b
    def __getattr__(self, name): return getattr(self._b, name)
    def new_page(self, **kw): return on_day(self._b.new_page(**kw), TODAY)
    def new_context(self, **kw): return on_day(self._b.new_context(**kw), TODAY)


def launch(p):
    """Start the browser chosen with the BROWSER environment variable (on TODAY's date, when that's set)."""
    b = getattr(p, BROWSER).launch()
    return _OnDay(b) if TODAY else b


def shown(pg):
    """The page is on screen: its guard against being shown inside another site has let it show (a hidden page would pass
    every check for bad text, as nothing is visible)."""
    return pg.evaluate("()=>!document.getElementById('framed') && getComputedStyle(document.documentElement).display!=='none'")


def pick(*a): return random.choice(a)


def watch_errors(pg, errs=None, n=200):
    """The page's script errors, as they happen, in a list (a new one, or added to errs)."""
    errs = [] if errs is None else errs
    pg.on('pageerror', lambda e: errs.append(str(e)[:n])); return errs


def import_file(pg, path, timeout=20000):
    """Import a file through the Import button and wait until the tool has dealt with it: your data replaced, or a note saying
    why not. Waiting for that, not a fixed time, so a slow machine can't check too early."""
    pg.evaluate("()=>{ window.__was=state; document.querySelector('.toast').hidden=true; }")
    pg.set_input_files('#importFile', str(path))
    pg.wait_for_function("()=>state!==window.__was || !document.querySelector('.toast').hidden", timeout=timeout)   # an arrow function: the page's security rule refuses a bare string


def fixture(name):
    """Made-up example data (never anyone's real numbers)."""
    return json.loads((FIXTURES / name).read_text(encoding='utf-8'))


def finish(name, problems, summary):
    """Print the result and exit with an error code when anything failed, so CI marks the run red."""
    print(f'{name}: {summary}')
    sys.exit(1 if problems else 0)
