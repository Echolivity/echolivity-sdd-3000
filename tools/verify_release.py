#!/usr/bin/env python3
"""
verify_release.py -- reproducibility check for an ECHOLIVITY release tree.

  python3 tools/verify_release.py [--baseline FILE.sha256] [--write-checksums] [--skip-audio]
  python3 tools/verify_release.py --checksums-only

1. copies the shipped files only (no build/, caches, compiled objects) into an empty
   temporary directory = a clean checkout
2. regenerates the GenExpr, the .maxpat, the .amxd and the UI preview there and
   compares them byte-for-byte with the release tree
3. builds the device a second time and checks the two builds are identical
4. runs tests/run_tests.py and tools/inspect_amxd.py in the clean copy
5. re-renders the audio examples and compares them with the shipped WAVs
6. scans the release tree for temporary/build files
7. optionally compares selected files with a baseline checksum file (e.g. v1.0)
Writes docs/REPRODUCIBILITY.json. With --write-checksums, writes SHA256SUMS.txt last.
"""
import hashlib, json, os, shutil, subprocess, sys, tempfile, fnmatch

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EXCLUDE_DIRS = {"build", "__pycache__", ".git"}
TEMP_PATTERNS = ["*.pyc", "*.pyo", "*.so", "*.o", "*.dll", "*.dylib", "*.c", ".DS_Store", "Thumbs.db",
                 "*.tmp", "*~", "*.bak", "*.swp"]
SOURCE_ALLOW = {"tests/bench_engine.c"}      # hand-written C source (generated C only lives in build/)
GENERATED = ["src/gen/echolivity_core.genexpr", "src/max/ECHOLIVITY_SDD-3000.maxpat",
             "dist/ECHOLIVITY SDD-3000.amxd", "docs/ui_preview.png"]
R = []


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def rec(name, ok, detail):
    R.append({"check": name, "pass": bool(ok), "detail": detail})
    print(("PASS " if ok else "FAIL ") + name + " :: " + detail)


def release_files(root):
    out = []
    for d, dirs, files in os.walk(root):
        dirs[:] = sorted(x for x in dirs if x not in EXCLUDE_DIRS)
        for f in sorted(files):
            rel = os.path.relpath(os.path.join(d, f), root).replace(os.sep, "/")
            if rel == "SHA256SUMS.txt":
                continue
            out.append(rel)
    return out


def run(cmd, cwd):
    return subprocess.run([sys.executable] + cmd, cwd=cwd, capture_output=True, text=True)


def write_checksums():
    files = release_files(ROOT)
    with open(os.path.join(ROOT, "SHA256SUMS.txt"), "w", newline="\n") as f:
        for p in files:
            f.write(f"{sha(os.path.join(ROOT, p))}  {p}\n")
    print(f"SHA256SUMS.txt written ({len(files)} files)")


def main():
    args = sys.argv[1:]
    if "--checksums-only" in args:
        write_checksums()
        return
    baseline = args[args.index("--baseline") + 1] if "--baseline" in args else None
    files = release_files(ROOT)

    # 6. temporary/build files in the tree
    stray = [f for f in files if f not in SOURCE_ALLOW and
             any(fnmatch.fnmatch(os.path.basename(f), p) for p in TEMP_PATTERNS)]
    present_dirs = [d for d in EXCLUDE_DIRS if os.path.isdir(os.path.join(ROOT, d))]
    rec("no temporary or build files in the release tree", not stray,
        f"{len(files)} files scanned; stray: {stray or 'none'}"
        + (f"; local-only dirs excluded from the release: {sorted(present_dirs)}" if present_dirs else ""))

    tmp = tempfile.mkdtemp(prefix="echolivity_clean_")
    try:
        for f in files:
            dst = os.path.join(tmp, f)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(os.path.join(ROOT, f), dst)
        rec("clean checkout prepared", not os.path.exists(os.path.join(tmp, "build")),
            f"{len(files)} files copied to an empty directory, no build/ directory")
        # remove generated artefacts so they must be regenerated from source
        shipped = {g: sha(os.path.join(ROOT, g)) for g in GENERATED}
        for g in GENERATED:
            os.remove(os.path.join(tmp, g))
        r1 = run(["tools/make_gen.py"], tmp)
        r2 = run(["tools/build_amxd.py"], tmp)
        ok = r1.returncode == 0 and r2.returncode == 0
        diffs = [g for g in GENERATED if not os.path.exists(os.path.join(tmp, g)) or
                 sha(os.path.join(tmp, g)) != shipped[g]]
        rec("clean rebuild reproduces the shipped artefacts", ok and not diffs,
            "; ".join(f"{g}: {shipped[g][:16]}..." for g in GENERATED) + (f"; DIFFER: {diffs}" if diffs else ""))
        first = {g: sha(os.path.join(tmp, g)) for g in GENERATED}
        run(["tools/make_gen.py"], tmp)
        run(["tools/build_amxd.py"], tmp)
        second = {g: sha(os.path.join(tmp, g)) for g in GENERATED}
        rec("deterministic build (two consecutive builds identical)", first == second,
            f"{len(GENERATED)} artefacts compared")
        t = run(["tests/run_tests.py"], tmp)
        res = json.load(open(os.path.join(tmp, "docs", "TEST_RESULTS.json")))
        mine = json.load(open(os.path.join(ROOT, "docs", "TEST_RESULTS.json")))
        same = [(a["test"], a["pass"]) for a in res] == [(b["test"], b["pass"]) for b in mine]
        n = sum(x["pass"] for x in res)
        rec("engine tests pass from the clean checkout", t.returncode == 0 and same,
            f"exit {t.returncode}; {n}/{len(res)} PASS, "
            f"{sum(1 for x in res if not x['pass'] and x.get('known_limitation'))} known-limitation FAIL; "
            f"results identical to the release tree: {same}")
        s = run(["tools/inspect_amxd.py"], tmp)
        sc = json.load(open(os.path.join(tmp, "docs", "STATIC_CHECKS.json")))
        rec("static device checks pass from the clean checkout", s.returncode == 0,
            f"{sum(x['pass'] for x in sc)}/{len(sc)}")
        if "--skip-audio" not in args:
            wavs = sorted(f for f in files if f.startswith("audio_examples/") and f.endswith(".wav"))
            for w in wavs:
                os.remove(os.path.join(tmp, w))
            shutil.rmtree(os.path.join(tmp, "build"), ignore_errors=True)   # renderer must build on its own
            a = run(["tests/render_examples.py"], tmp)
            bad = [w for w in wavs if not os.path.exists(os.path.join(tmp, w)) or
                   sha(os.path.join(tmp, w)) != sha(os.path.join(ROOT, w))]
            rec("audio examples re-render identically from the current DSP", a.returncode == 0 and not bad,
                f"{len(wavs)} WAV files (1 dry source + {len(wavs) - 1} renders)"
                + (f"; DIFFER: {bad}" if bad else ""))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if baseline:
        base = {}
        for line in open(baseline):
            h, p = line.rstrip("\n").split("  ", 1)
            base[p] = h
        cmp = {p: (sha(os.path.join(ROOT, p)) == h) for p, h in base.items() if os.path.exists(os.path.join(ROOT, p))}
        rec("unchanged versus baseline " + os.path.basename(baseline), all(cmp.values()) and len(cmp) == len(base),
            "; ".join(f"{p}: {'identical' if v else 'CHANGED'}" for p, v in cmp.items()))

    json.dump(R, open(os.path.join(ROOT, "docs", "REPRODUCIBILITY.json"), "w"), indent=1)
    if "--write-checksums" in args:
        write_checksums()
    n = sum(r["pass"] for r in R)
    print(f"\n{n}/{len(R)} reproducibility checks passed")
    sys.exit(0 if n == len(R) else 1)


if __name__ == "__main__":
    main()
