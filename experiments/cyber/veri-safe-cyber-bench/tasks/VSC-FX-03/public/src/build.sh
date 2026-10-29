#!/bin/sh
# Compile-check every module (Python has no separate build step).
set -e
cd "$(dirname "$0")"
python3 -B -c "
import glob, sys
for path in sorted(glob.glob('*.py')):
    compile(open(path).read(), path, 'exec')
print('build ok')
"
