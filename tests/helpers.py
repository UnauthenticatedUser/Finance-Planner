"""Shared setup for the tests: where the planner and the example data are, and how a test reports its result.

Every test opens index.html from this repository in a headless browser through Playwright (Chromium, unless the
BROWSER environment variable says firefox or webkit) and checks the tool's own results against calculations written
separately in Python. Nothing is fetched from the internet."""
import json, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = (ROOT / 'index.html').as_uri()
FIXTURES = Path(__file__).resolve().parent / 'fixtures'
BROWSER = os.environ.get('BROWSER', 'chromium')   # chromium, firefox or webkit (Safari's engine)


def launch(p):
    """Start the browser chosen with the BROWSER environment variable."""
    return getattr(p, BROWSER).launch()


def fixture(name):
    """Made-up example data (never anyone's real numbers)."""
    return json.loads((FIXTURES / name).read_text(encoding='utf-8'))


def finish(name, problems, summary):
    """Print the result and exit with an error code when anything failed, so CI marks the run red."""
    print(f'{name}: {summary}')
    sys.exit(1 if problems else 0)
