"""Run every skill integration test in this directory. Exit 1 if any fails.

Usage: python tests/skills/run_all.py  (from anywhere; paths are self-contained)
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
tests = sorted(f for f in os.listdir(HERE) if f.startswith("test_") and f.endswith(".py"))
fails = []
for name in tests:
    proc = subprocess.run([sys.executable, os.path.join(HERE, name)],
                          capture_output=True, text=True)
    ok = proc.returncode == 0
    checks = proc.stdout.count("ok  ")
    print(f"{'PASS' if ok else 'FAIL'}  {name}  ({checks} checks)")
    if not ok:
        fails.append(name)
        tail = (proc.stdout + proc.stderr).strip().splitlines()[-15:]
        print("\n".join(f"      {ln}" for ln in tail))
print(f"\n{len(tests) - len(fails)}/{len(tests)} test files passed")
sys.exit(1 if fails else 0)
