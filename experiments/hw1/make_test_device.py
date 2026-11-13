#!/usr/bin/env python3
"""
Build a SEPARATE native test device for candidate D, for Max 9 / Live 12 validation:
experiments/hw1/build/ECHOLIVITY SDD-3000 HW1-D TEST.amxd

Uses the unmodified production generator (tools/build_amxd.py: same panel, parameters, presets)
with only the gen~ code swapped for experiments/hw1/build/echolivity_core_d.genexpr, and the panel
legend marked "HW1-D TEST" so it cannot be mistaken for the release. Nothing in dist/, src/ or docs/
is written (the production main() is not called).
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import build_amxd as B

# usage: make_test_device.py [genexpr] [label]   (defaults: candidate D, "HW1-D")
B.GEN = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(HERE, "build", "echolivity_core_d.genexpr")
LABEL = sys.argv[2] if len(sys.argv) > 2 else "HW1-D"
OUT = os.path.join(HERE, "build", f"ECHOLIVITY SDD-3000 {LABEL} TEST.amxd")


def mark(obj):
    n = 0
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "text" and v == "ECHOLIVITY":
                obj[k] = f"ECHOLIVITY {LABEL} TEST"; n += 1
            elif k == "description" and isinstance(v, str) and v.startswith("ECHOLIVITY SDD-3000"):
                obj[k] = v + f" - {LABEL} TEST BUILD (not a release)"; n += 1
            else:
                n += mark(v)
    elif isinstance(obj, list):
        for v in obj:
            n += mark(v)
    return n


def main():
    patcher, _ = B.build()
    nb, nl, npar = B.validate(patcher)
    n = mark(patcher)
    code = None
    def find_code(o):
        nonlocal code
        if isinstance(o, dict):
            if o.get("maxclass") == "codebox" or ("code" in o and isinstance(o.get("code"), str)):
                code = o.get("code", code)
            for v in o.values():
                find_code(v)
        elif isinstance(o, list):
            for v in o:
                find_code(v)
    find_code(patcher)
    assert code and "HW-1 D" in code, "candidate code not embedded"
    size = B.write_amxd(patcher, OUT)
    json.dump(patcher, open(OUT.replace(".amxd", ".maxpat"), "w"), indent=1, ensure_ascii=False)
    print(f"test device: {size} bytes, {nb} boxes, {nl} lines, {npar} parameters, {n} labels marked -> {OUT}")


if __name__ == "__main__":
    main()
