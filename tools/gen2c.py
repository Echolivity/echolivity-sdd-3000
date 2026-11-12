#!/usr/bin/env python3
"""
gen2c.py -- compile the ECHOLIVITY GenExpr codebox to C for offline testing.

The point: the test-suite must exercise the *actual* gen~ source, not a
re-implementation. This tool takes the exact text that is embedded in the
.amxd and translates it 1:1 into C (GenExpr is C-like). Before translating it
enforces a conservative GenExpr subset so that gen~ and C semantics cannot
diverge:

  * only whitelisted gen operators are called (all exist in gen~ with the
    same semantics as their C counterparts)
  * every local is first assigned at block depth 0 (gen block scoping)
  * a History is never read after being written in the same frame, and
    never written inside a loop (so 'immediate' vs 'deferred' History
    semantics cannot matter)
  * no ternary, no '%', no scientific notation, no user functions
  * locals must not shadow gen operator names
  * every identifier read is defined earlier in the text

Usage:  gen2c.py in.genexpr out.c
"""
import re, sys

ALLOWED_FUNCS = {"pow", "abs", "exp", "tan", "sin", "cos", "sqrt", "floor", "min", "max",
                 "clamp", "log10", "noise", "fixdenorm", "fixnan", "peek", "poke"}
KEYWORDS = {"if", "else", "while"}
GEN_RESERVED = set("""
abs absdiff accum acos acosh add and asin asinh atan atan2 atanh atodb bool buffer cartopol
ceil change channels clamp clip cos cosh counter cycle data dbtoa dcblock degrees delay delta
dim div e elapsed eq equals exp exp2 fixdenorm fixnan floor fold fract ftom gate gen gt gte
history hypot in int interp isdenorm isnan latch ln log log10 log2 lookup lt lte max min mix
mod mstosamps mtof mul neg neq noise not notequals or out param pass peek phasor pi poke pow
radians rate rdiv round rsub sah samplerate sampstoms scale sel selector sign sin sinh slide
smoothstep splat sqrt step sub switch t60 t60time tan tanh train trunc twopi halfpi invpi
vectorsize wrap xor cell elapsed delay history
""".split())


def die(msg):
    sys.stderr.write("gen2c ERROR: " + msg + "\n")
    sys.exit(1)


def strip_comment(line):
    i = line.find("//")
    return line if i < 0 else line[:i]


def main(src, dst):
    raw = open(src).read().splitlines()
    params, hists, datas = {}, {}, {}
    body = []          # (lineno, text)
    for n, line in enumerate(raw, 1):
        t = strip_comment(line).rstrip()
        if not t.strip():
            continue
        m = re.match(r"\s*Param\s+(\w+)\(([^,]+),\s*min=([^,]+),\s*max=([^)]+)\);\s*$", t)
        if m:
            params[m.group(1)] = (float(m.group(2)), float(m.group(3)), float(m.group(4)))
            continue
        m = re.match(r"\s*History\s+(\w+)\(([^)]*)\);\s*$", t)
        if m:
            hists[m.group(1)] = float(m.group(2) or 0)
            continue
        m = re.match(r"\s*Data\s+(\w+)\((\d+),\s*(\d+)\);\s*$", t)
        if m:
            datas[m.group(1)] = (int(m.group(2)), int(m.group(3)))
            continue
        if re.match(r"\s*(Param|History|Data|Buffer)\b", t):
            die(f"line {n}: unparsed declaration: {t}")
        body.append((n, t))

    text = "\n".join(t for _, t in body)
    # --- banned constructs
    if "?" in text:
        die("ternary operator found")
    if "%" in text:
        die("'%' found")
    if re.search(r"\b\d+\.?\d*[eE][-+]?\d+", text):
        die("scientific notation found")

    # --- per-statement analysis
    depth = 0
    loop_depths = []
    last_closed = {}      # depth -> kind of the block that just closed at this depth
    open_kind = []
    locals_first = {}     # name -> depth at first assignment
    defined = set(params) | set(hists) | set(datas) | {"in1", "in2", "in3", "in4", "samplerate", "pi"}
    hist_written = set()
    outs = set()
    order = []
    for n, t in body:
        # split into statements while tracking braces
        tokens = re.split(r"([{};])", t)
        stmt = ""
        for tok in tokens:
            if tok == "{":
                if re.match(r"\s*while\b", stmt):
                    loop_depths.append(depth + 1)
                if re.match(r"\s*else\b", stmt) and last_closed.get(depth) not in ("if",):
                    die(f"line {n}: 'else' without a preceding if-block")
                kind = "if" if re.match(r"\s*(else\s+)?if\b", stmt) else "other"
                last_closed[depth] = None
                open_kind.append(kind)
                analyse(n, stmt, depth, loop_depths, locals_first, defined, hists, hist_written,
                        outs, params, datas)
                depth += 1
                stmt = ""
            elif tok == "}":
                if stmt.strip():
                    die(f"line {n}: statement without ';' before '}}'")
                if loop_depths and loop_depths[-1] == depth:
                    loop_depths.pop()
                depth -= 1
                last_closed[depth] = open_kind.pop()
                if depth < 0:
                    die(f"line {n}: unbalanced braces")
            elif tok == ";":
                last_closed[depth] = None
                analyse(n, stmt, depth, loop_depths, locals_first, defined, hists, hist_written,
                        outs, params, datas)
                stmt = ""
            else:
                stmt += tok
        if stmt.strip() and not re.match(r"\s*(else)\s*$", stmt):
            die(f"line {n}: dangling text '{stmt.strip()}'")
    if depth != 0:
        die("unbalanced braces at EOF")

    for name, d in locals_first.items():
        if d != 0:
            die(f"local '{name}' first assigned at depth {d} (must be 0)")
        if name in GEN_RESERVED:
            die(f"local '{name}' shadows a gen operator")

    # --- emit C
    c = []
    a = c.append
    a("/* AUTO-GENERATED by gen2c.py from the gen~ codebox -- do not edit */")
    a("#include <math.h>\n#include <string.h>\n#include <stdint.h>")
    a("static double g_sr = 48000.0;")
    a("static long g_bounds_err = 0;")
    a("static uint64_t g_rng = 0x9E3779B97F4A7C15ULL;")
    a("static inline double g_noise(void){ g_rng ^= g_rng << 13; g_rng ^= g_rng >> 7; g_rng ^= g_rng << 17;"
      " return ((double)(g_rng >> 11) / 9007199254740992.0) * 2.0 - 1.0; }")
    a("static inline double g_clamp(double x,double lo,double hi){ return x<lo?lo:(x>hi?hi:x); }")
    a("static inline double g_fixdenorm(double x){ return fabs(x) < 1e-30 ? 0.0 : x; }")
    a("static inline double g_fixnan(double x){ return isnan(x) ? 0.0 : x; }")
    for p, (d, lo, hi) in params.items():
        a(f"static double {p} = {d!r};")
    for h, v in hists.items():
        a(f"static double {h} = {v!r};")
    for d, (size, ch) in datas.items():
        a(f"static double D_{d}[{size * ch}];")
        a(f"static inline double peek_{d}(double i, double c){{ long ii=(long)floor(i), cc=(long)floor(c);"
          f" if(ii<0||ii>={size}||cc<0||cc>={ch}){{g_bounds_err++;return 0.0;}} return D_{d}[cc*{size}+ii]; }}")
        a(f"static inline void poke_{d}(double v,double i,double c){{ long ii=(long)floor(i), cc=(long)floor(c);"
          f" if(ii<0||ii>={size}||cc<0||cc>={ch}){{g_bounds_err++;return;}} D_{d}[cc*{size}+ii]=v; }}")
    # param table
    a("typedef struct { const char* n; double* p; double lo, hi; } ptab_t;")
    a("static ptab_t PT[] = {")
    for p, (d, lo, hi) in params.items():
        a(f'  {{"{p}", &{p}, {lo!r}, {hi!r}}},')
    a("  {0,0,0,0}};")
    a("int set_param(const char* n, double v){ for(int i=0;PT[i].n;i++) if(!strcmp(PT[i].n,n)){"
      " if(v<PT[i].lo)v=PT[i].lo; if(v>PT[i].hi)v=PT[i].hi; *PT[i].p=v; return 1;} return 0; }")
    a("int set_param_raw(const char* n, double v){ for(int i=0;PT[i].n;i++) if(!strcmp(PT[i].n,n)){"
      " *PT[i].p=v; return 1;} return 0; }")
    a("void set_samplerate(double sr){ g_sr = sr; }   /* test harness: rate change without reset */")
    a("double get_param(const char* n){ for(int i=0;PT[i].n;i++) if(!strcmp(PT[i].n,n)) return *PT[i].p; return -1e99; }")
    a("long bounds_errors(void){ return g_bounds_err; }")
    a("void reset(double sr){ g_sr = sr; g_bounds_err = 0; g_rng = 0x9E3779B97F4A7C15ULL;")
    for p, (d, lo, hi) in params.items():
        a(f"  {p} = {d!r};")
    for h, v in hists.items():
        a(f"  {h} = {v!r};")
    for d, (size, ch) in datas.items():
        a(f"  memset(D_{d}, 0, sizeof(D_{d}));")
    a("}")
    nouts = max([int(o[3:]) for o in outs] + [1])
    a(f"int num_outs(void){{ return {nouts}; }}")
    a("static inline void frame(double in1, double in2, double in3, double in4, double* o){")
    for v in sorted(locals_first):
        a(f"  double {v} = 0.0;")
    btxt = "\n".join("  " + t for _, t in body)
    btxt = re.sub(r"\bsamplerate\b", "g_sr", btxt)
    btxt = re.sub(r"\bpi\b", "M_PI", btxt)
    btxt = re.sub(r"\bnoise\(\)", "g_noise()", btxt)
    btxt = re.sub(r"\babs\(", "fabs(", btxt)
    btxt = re.sub(r"\bmin\(", "fmin(", btxt)
    btxt = re.sub(r"\bmax\(", "fmax(", btxt)
    btxt = re.sub(r"\bclamp\(", "g_clamp(", btxt)
    btxt = re.sub(r"\bfixdenorm\(", "g_fixdenorm(", btxt)
    btxt = re.sub(r"\bfixnan\(", "g_fixnan(", btxt)
    for d in datas:
        btxt = re.sub(r"\bpeek\(\s*" + d + r"\s*,", f"peek_{d}(", btxt)
        btxt = re.sub(r"\bpoke\(\s*" + d + r"\s*,", f"poke_{d}(", btxt)
    btxt = re.sub(r"\bout(\d+)\s*=", lambda m: f"o[{int(m.group(1)) - 1}] =", btxt)
    a(btxt)
    a("}")
    a("void process(const double* inL, const double* inR, double* outs, int n){")
    a(f"  double o[{nouts}];")
    a("  for(int i=0;i<n;i++){ frame(inL[i], inR[i], 0.0, 0.0, o);")
    a(f"    for(int k=0;k<{nouts};k++) outs[k*n+i]=o[k]; }}")
    a("}")
    a("/* v1.0.2-rc4: 4-input version (inputs 3/4 = EXT loop return) */")
    a("void process4(const double* inL, const double* inR, const double* in3, const double* in4, double* outs, int n){")
    a(f"  double o[{nouts}];")
    a("  for(int i=0;i<n;i++){ frame(inL[i], inR[i], in3[i], in4[i], o);")
    a(f"    for(int k=0;k<{nouts};k++) outs[k*n+i]=o[k]; }}")
    a("}")
    open(dst, "w").write("\n".join(c) + "\n")
    print(f"gen2c: {len(params)} params, {len(hists)} histories, {len(locals_first)} locals, "
          f"{nouts} outs -> {dst}")


def analyse(n, stmt, depth, loop_depths, locals_first, defined, hists, hist_written, outs,
            params, datas):
    s = stmt.strip()
    if not s or s == "else":
        return
    m = re.match(r"(else\s+)?(if|while)\s*\((.*)\)\s*$", s)
    if m:
        check_expr(n, m.group(3), defined, hists, hist_written)
        return
    if s.startswith("else"):
        die(f"line {n}: odd else: {s}")
    m = re.match(r"(\w+)\s*=(?!=)\s*(.*)$", s, re.S)
    if m:
        lhs, rhs = m.group(1), m.group(2)
        check_expr(n, rhs, defined, hists, hist_written)
        if lhs in params:
            die(f"line {n}: assignment to Param {lhs}")
        if re.match(r"out\d+$", lhs):
            outs.add(lhs)
            return
        if lhs in hists:
            if loop_depths:
                die(f"line {n}: History {lhs} written inside a loop")
            hist_written.add(lhs)
            return
        if lhs not in locals_first:
            locals_first[lhs] = depth
        defined.add(lhs)
        return
    m = re.match(r"(poke)\s*\((.*)\)$", s, re.S)
    if m:
        check_expr(n, m.group(2), defined, hists, hist_written)
        return
    die(f"line {n}: cannot parse statement: {s}")


def check_expr(n, e, defined, hists, hist_written):
    for fm in re.finditer(r"\b([A-Za-z_]\w*)\s*\(", e):
        f = fm.group(1)
        if f not in ALLOWED_FUNCS and f not in KEYWORDS:
            die(f"line {n}: function '{f}' not in the allowed gen subset")
    for im in re.finditer(r"\b([A-Za-z_]\w*)\b(?!\s*\()", e):
        name = im.group(1)
        if name in hists and name in hist_written:
            die(f"line {n}: History '{name}' read after it was written")
        if name not in defined:
            die(f"line {n}: '{name}' used before definition")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
