#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
gcc -shared -fPIC -O2 proximity_score.c proximity_math.S -o libproxmath.so
echo "Built native/libproxmath.so"
