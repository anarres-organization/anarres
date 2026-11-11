#!/usr/bin/env python3
"""Audit a pinned Business Bench checkout without reading outcome directories."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from anarres.finance.business_bench_source import qualify_checkout


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("checkout", type=Path)
    args = parser.parse_args()
    result = qualify_checkout(args.checkout.resolve())
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
