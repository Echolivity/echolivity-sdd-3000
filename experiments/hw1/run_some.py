#!/usr/bin/env python3
"""Run selected tests from tests/run_tests.py (unmodified) against a given engine and print full
details. Nothing is written to docs/. Usage: run_some.py <engine.so> t_name [t_name ...]"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tests"))
import engine
engine.SO = os.path.abspath(sys.argv[1])
import run_tests
run_tests.build = lambda: None
names = sys.argv[2:]
sys.argv = ["run_tests.py"] + names
try:
    run_tests.main()
except SystemExit:
    pass
for r in run_tests.RESULTS:
    print("PASS" if r["pass"] else "FAIL", r["test"], "::", r["detail"])
