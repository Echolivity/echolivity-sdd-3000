#!/bin/sh
# Diagnostic only: copy of a genexpr with out4 (LFO LED) replaced by a probe expression. Not a candidate.
# usage: probe_build.sh <src.genexpr> <name> "<expr>"
set -e
cd "$(dirname "$0")/../../.."
OUT=experiments/hw1/d2/build/probe_$2
sed "s|^out4 = fixnan(m_s);.*|out4 = fixnan($3);   // PROBE|" "$1" > $OUT.genexpr
grep -q "// PROBE" $OUT.genexpr
python3 tools/gen2c.py $OUT.genexpr $OUT.c > /dev/null
gcc -O2 -shared -fPIC -o $OUT.so $OUT.c -lm
