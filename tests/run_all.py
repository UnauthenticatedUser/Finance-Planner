"""Runs every test in this folder and exits with an error if any of them failed.
Run from the repository folder: python tests/run_all.py"""
import subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TESTS = ['test_calculations.py', 'test_forecasts.py', 'test_retirement.py', 'test_targets.py',
         'test_editor.py', 'test_accessibility.py', 'test_backups.py', 'test_broken_files.py', 'test_security.py', 'test_privacy.py']

failed = []
for name in TESTS:
    start = time.time()
    print(f'--- {name}', flush=True)
    result = subprocess.run([sys.executable, str(HERE / name)], cwd=HERE)
    print(f'    {"passed" if result.returncode == 0 else "FAILED"} in {time.time() - start:.0f}s', flush=True)
    if result.returncode != 0: failed.append(name)

print('\nAll tests passed.' if not failed else '\nFailed: ' + ', '.join(failed))
sys.exit(1 if failed else 0)
