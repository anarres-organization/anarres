#!/bin/sh
# Synthetic benchmark code for defensive evaluation. Authored by cc opus 5.5 xhigh, 2026-10-29.
# Byte-compiles every module (syntax check). Run from anywhere.
set -eu
cd "$(dirname "$0")"
python3 -m py_compile *.py
echo "build ok"
