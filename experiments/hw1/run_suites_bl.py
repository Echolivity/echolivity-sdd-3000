#!/usr/bin/env python3
"""
Run the EXISTING suites, unmodified, against the experimental candidate-B engine, so every
behavioural difference from production is listed. Results go to experiments/hw1/results/;
docs/TEST_RESULTS.json and docs/validation/* are not touched.
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "tests", "hwref"))
import engine
engine.build()
BL = os.path.join(HERE, "build", "engine_bl.so")
PROD = engine.SO
OUT = os.path.join(HERE, "results")


def engine_suite(so):
    engine.SO = so
    import importlib, run_tests
    importlib.reload(run_tests)
    run_tests.build = lambda: None                  # keep the chosen engine
    names = [n for n in dir(run_tests) if n.startswith("t_")]
    sys.argv = ["run_tests.py"] + names            # 'only' mode: results are not written to docs/
    try:
        run_tests.main()
    except SystemExit:
        pass
    return {r["test"]: r for r in run_tests.RESULTS}


def hw_suite(so):
    engine.SO = so
    import importlib, hw_validation
    importlib.reload(hw_validation)
    hw_validation.build = lambda: None
    hw_validation.OUT_JSON = os.path.join(OUT, "hwref_" + ("bl" if so == BL else "prod") + ".json")
    hw_validation.OUT_MD = os.path.join(OUT, "hwref_" + ("bl" if so == BL else "prod") + ".md")
    hw_validation.RES.clear()
    hw_validation.main()
    return {r["area"] + ": " + r["name"]: r for r in hw_validation.RES}


def main():
    prod = engine_suite(PROD)
    bl = engine_suite(BL)
    diff = []
    for k in prod:
        a, b = prod[k], bl.get(k)
        if b is None:
            continue
        if a["pass"] != b["pass"] or a.get("detail") != b.get("detail"):
            diff.append(dict(test=k, production_pass=a["pass"], candidate_pass=b["pass"],
                             production=str(a.get("detail"))[:400], candidate=str(b.get("detail"))[:400]))
    hp = hw_suite(PROD)
    hb = hw_suite(BL)
    hdiff = [dict(measurement=k, production=hp[k]["verdict"], candidate=hb[k]["verdict"],
                  production_value=str(hp[k]["measured"])[:300], candidate_value=str(hb[k]["measured"])[:300])
             for k in hp if k in hb and (hp[k]["verdict"] != hb[k]["verdict"] or hp[k]["measured"] != hb[k]["measured"])]
    res = dict(engine_suite=dict(production_pass=sum(r["pass"] for r in prod.values()), candidate_pass=sum(r["pass"] for r in bl.values()),
                                 total=len(prod), differences=diff),
               hw_suite=dict(production={v: sum(r["verdict"] == v for r in hp.values()) for v in ("CONSISTENT", "INCONSISTENT", "REPORTED", "NOT COMPARABLE")},
                             candidate={v: sum(r["verdict"] == v for r in hb.values()) for v in ("CONSISTENT", "INCONSISTENT", "REPORTED", "NOT COMPARABLE")},
                             differences=hdiff))
    json.dump(res, open(os.path.join(OUT, "suites_production_vs_candidate.json"), "w"), indent=1)
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "differences"} for k, v in res.items()}, indent=1))
    for d in diff:
        print("ENGINE", d["test"], d["production_pass"], "->", d["candidate_pass"], "|", d["candidate"][:200])
    for d in hdiff:
        print("HWREF", d["measurement"], d["production"], "->", d["candidate"], "|", d["candidate_value"][:160])


if __name__ == "__main__":
    main()
