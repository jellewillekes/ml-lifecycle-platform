#!/usr/bin/env python3
"""Strip volatile fields from a Grafana dashboard export so the committed JSON
stays stable across UI edits.

Usage:

    python scripts/normalize_grafana_dashboard.py < export.json > serving.json
"""

from __future__ import annotations

import json
import sys

VOLATILE_TOP_LEVEL = ("id", "version", "iteration", "gnetId")


def normalize(payload: dict) -> dict:
    cleaned = {
        key: value for key, value in payload.items() if key not in VOLATILE_TOP_LEVEL
    }
    cleaned.setdefault("uid", payload.get("uid", ""))
    return cleaned


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"invalid dashboard JSON on stdin: {exc}", file=sys.stderr)
        return 2

    json.dump(normalize(payload), sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
