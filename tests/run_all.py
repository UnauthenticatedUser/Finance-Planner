"""Runs every test in this folder and exits with an error if any of them failed (or if none ran).
Run from the repository folder: python tests/run_all.py
To leave tests out, name them after --skip, for example the slow security test: python tests/run_all.py --skip security
To run them as if it were another day: python tests/run_all.py --date 2027-01-01 (the options can come in any order)
Dates worth trying: 31 December, 1 January, a day in March (before mid-year) and in August."""
import argparse, datetime, os, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TESTS = ['test_reference.py', 'test_calculations.py', 'test_forecasts.py', 'test_retirement.py', 'test_targets.py', 'test_path.py',
         'test_editor.py', 'test_accessibility.py', 'test_backups.py', 'test_broken_files.py', 'test_security.py', 'test_privacy.py']

short = lambda name: name.removeprefix('test_').removesuffix('.py')
ap = argparse.ArgumentParser(description='Run the tests.')
ap.add_argument('--date', type=datetime.date.fromisoformat, help='run as if it were this day, YYYY-MM-DD')
ap.add_argument('--skip', nargs='+', default=[], choices=[short(t) for t in TESTS], metavar='TEST', help='tests to leave out: ' + ', '.join(map(short, TESTS)))
args = ap.parse_args()
env = dict(os.environ)
if args.date: env['TODAY'] = args.date.isoformat(); print('Running as if it were', env['TODAY'])
skip = set(args.skip)

failed, ran = [], 0
for name in TESTS:
    if short(name) in skip: continue
    start = time.time(); ran += 1
    print(f'--- {name}', flush=True)
    result = subprocess.run([sys.executable, str(HERE / name)], cwd=HERE, env=env)
    print(f'    {"passed" if result.returncode == 0 else "FAILED"} in {time.time() - start:.0f}s', flush=True)
    if result.returncode != 0: failed.append(name)

if not ran: sys.exit('No tests ran: everything was skipped.')
print(('\nAll tests passed.' if not failed else '\nFailed: ' + ', '.join(failed)) + (f' Skipped: {", ".join(sorted(skip))}.' if skip else ''))
sys.exit(1 if failed else 0)
