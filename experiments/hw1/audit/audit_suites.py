#!/usr/bin/env python3
"""Run the existing engine suite (tests/run_tests.py, unmodified, 'only' mode: docs/ not written) against
each engine and store EVERY result with its spec string -> results/audit_engine_suite.json
Usage: audit_suites.py name=engine.so [...]"""
import json, os, sys, importlib
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tests"))
import engine
engs = dict(a.split("=", 1) for a in sys.argv[1:])
out = {}
for name, so in engs.items():
    engine.SO = os.path.abspath(so)
    import run_tests
    importlib.reload(run_tests)
    run_tests.build = lambda: None
    names = [n for n in dir(run_tests) if n.startswith("t_")]
    sys.argv = ["run_tests.py"] + names
    try:
        run_tests.main()
    except SystemExit:
        pass
    out[name] = [dict(test=r["test"], passed=bool(r["pass"]), detail=r["detail"], spec=r.get("spec", ""), known=r.get("known", ""))
                 for r in run_tests.RESULTS]
    print(name, sum(r["passed"] for r in out[name]), "/", len(out[name]), flush=True)
json.dump(out, open(os.path.join(os.environ.get("AUDIT_RESULTS", os.path.join(HERE, "results")), "audit_engine_suite.json"), "w"), indent=1)
