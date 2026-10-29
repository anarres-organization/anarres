#!/bin/sh
# Synthetic benchmark code for defensive evaluation. Authored by cc opus 5.5 xhigh, 2026-10-29.
# Builds ./sesscache next to this script, with AddressSanitizer and UBSan enabled.
set -e
cd "$(dirname "$0")"
${CC:-gcc} -std=c11 -Wall -Wextra -g -O1 \
    -fsanitize=address,undefined -fno-sanitize-recover=undefined \
    -fno-omit-frame-pointer -o sesscache main.c cmd.c cache.c
