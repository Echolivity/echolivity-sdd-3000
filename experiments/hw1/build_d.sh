#!/bin/sh
# Build a candidate-D engine: build_d.sh <name> [make_d.py args...]
set -e
cd "$(dirname "$0")/../.."
N=$1; shift
python3 experiments/hw1/make_d.py --out experiments/hw1/build/echolivity_core_$N.genexpr "$@"
python3 tools/gen2c.py experiments/hw1/build/echolivity_core_$N.genexpr experiments/hw1/build/engine_$N.c
gcc -O2 -shared -fPIC -o experiments/hw1/build/engine_$N.so experiments/hw1/build/engine_$N.c -lm
