#!/bin/sh
# Smoke expected outputs are stored as smoke/NAME.expected (the repo hygiene check rejects
# *.out). Task packages ship them as smoke/NAME.out, as INSTRUCTION.md says: run this before packaging.
cd "$(dirname "$0")/.." || exit 1
for f in tasks/*/public/smoke/*.expected; do
  cp "$f" "${f%.expected}.out"
done
