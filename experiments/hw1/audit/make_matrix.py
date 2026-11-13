#!/usr/bin/env python3
"""Build the regression matrix (markdown) from results/audit_engine_suite.json and the hardware-reference
JSONs: every test, its ORIGINAL criterion (spec string as recorded by the test), production and candidate
results verbatim (truncated for the table; full text in the JSON)."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HERE, "results", "audit_engine_suite.json")))
P = {x["test"]: x for x in R["production"]}; C = {x["test"]: x for x in R["candidate_D"]}; H = {x["test"]: x for x in R["counterfactual_holdfix"]}
import re
SRC = open(os.path.join(HERE, "..", "..", "..", "tests", "run_tests.py")).read()
# map each recorded test name to the acceptance expressions of the function that records it (verbatim code)
CRIT = {}
for m in re.finditer(r"\ndef (t_\w+)\(\):(.*?)(?=\ndef |\Z)", SRC, re.S):
    body = m.group(2)
    conds = [l.strip() for l in body.splitlines() if re.match(r"\s*(ok\s*&?=|good\s*=|lat_ok\s*=|big_ok\s*=|clamp_ok\s*&?=|same\s*=)", l)]
    for rn in re.findall(r'record\(\s*f?"([^"{]+)', body):
        CRIT.setdefault(rn.strip(), (m.group(1), conds))
def crit(t):
    for k, v in CRIT.items():
        if t.startswith(k.strip()):
            return f"`{v[0]}`: " + "; ".join(f"`{c}`" for c in v[1])[:400]
    return "(see tests/run_tests.py)"
cut = lambda s, n=230: (s[:n] + " …") if len(s) > n else s
lines = ["| # | Test | Original criterion | Production | Candidate D | D + HOLD counterfactual |", "|---|---|---|---|---|---|"]
for i, t in enumerate(P, 1):
    st = lambda x: ("PASS" if x["passed"] else "**FAIL**")
    lines.append(f"| E{i:02d} | {t} | {crit(t).replace('|', '/')} — spec: {cut(P[t]['spec'], 80)} | {st(P[t])} | {st(C[t])}: {cut(C[t]['detail']).replace('|', '/')} | {st(H[t])} |")
hp = json.load(open(os.path.join(HERE, "..", "results", "hwref_prod.json")))
hd = json.load(open(os.path.join(HERE, "..", "results", "hwref_d.json")))
rows = lambda j: j["results"] if isinstance(j, dict) and "results" in j else j
hp = {r["area"] + ": " + r["name"]: r for r in rows(hp)}; hd = {r["area"] + ": " + r["name"]: r for r in rows(hd)}
lines += ["", "| # | Hardware-reference measurement | Reference / tolerance | Production | Candidate D |", "|---|---|---|---|---|"]
for i, k in enumerate(hp, 1):
    a, b = hp[k], hd.get(k, {})
    lines.append(f"| H{i:02d} | {k} | {cut(str(a.get('reference', '')) + ' / ' + str(a.get('tolerance', '')), 90)} | {a['verdict']}: {cut(str(a['measured']), 90)} | {b.get('verdict')}: {cut(str(b.get('measured')), 90)} |")
open(os.path.join(HERE, "results", "regression_matrix.md"), "w").write("\n".join(lines) + "\n")
print(len(P), "engine tests;", len(hp), "hw-reference rows")
