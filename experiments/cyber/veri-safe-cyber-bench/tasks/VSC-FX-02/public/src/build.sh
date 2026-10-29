#!/bin/sh
# Builds ./tilekit next to this script (AddressSanitizer + UBSan, debug info).
set -e
cd "$(dirname "$0")"
gcc -fsanitize=address,undefined -g -O1 -Wall -Wextra -o tilekit main.c util.c store.c rle.c image.c ops.c
