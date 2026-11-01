#!/usr/bin/env python3
"""DISABLED: historical NQ Sept/Oct data is protected read-only.

This legacy Yahoo exporter could replace existing NQ October CSV and coverage
files. It is intentionally disabled to preserve verified historical data.
See Git history before reintroducing any collector. New download experiments
must use a unique test filename and must never overwrite existing datasets.
"""

def main() -> int:
    print("BLOCKED: NQ October dataset is READ ONLY; no download or write performed.")
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
