#!/bin/sh
# Synthetic benchmark code for defensive evaluation. Authored by cc opus 5.5 xhigh, 2026-10-29.
# Builds ./logpack with AddressSanitizer and UBSan enabled.
set -e
cd "$(dirname "$0")"
${CC:-gcc} -fsanitize=address,undefined -g -O1 -fno-omit-frame-pointer \
    -Wall -Wextra -o logpack main.c archive.c hexin.c report.c
