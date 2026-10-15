"""Runs every test in this folder and exits with an error if any of them failed.
Run from the repository folder: python tests/run_all.py
To leave tests out, name them after --skip, for example the slow security test: python tests/run_all.py --skip security"""
import subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TESTS = ['test_reference.py', 'test_calculations.py', 'test_forecasts.py', 'test_retirement.py', 'test_targets.py', 'test_path.py',
         'test_editor.py', 'test_accessibility.py', 'test_backups.py', 'test_broken_files.py', 'test_security.py', 'test_privacy.py']

short = lambda name: name.removeprefix('test_').removesuffix('.py')
skip = set(sys.argv[sys.argv.index('--skip') + 1:]) if '--skip' in sys.argv else set()
unknown = skip - {short(t) for t in TESTS}
if unknown: sys.exit('No such test: ' + ', '.join(sorted(unknown)) + '. The tests are: ' + ', '.join(map(short, TESTS)))

failed = []
for name in TESTS:
    if short(name) in skip: continue
    start = time.time()
    print(f'--- {name}', flush=True)
    result = subprocess.run([sys.executable, str(HERE / name)], cwd=HERE)
    print(f'    {"passed" if result.returncode == 0 else "FAILED"} in {time.time() - start:.0f}s', flush=True)
    if result.returncode != 0: failed.append(name)

print(('\nAll tests passed.' if not failed else '\nFailed: ' + ', '.join(failed)) + (f' Skipped: {", ".join(sorted(skip))}.' if skip else ''))
sys.exit(1 if failed else 0)
