#!/usr/bin/env python3
"""Codex SessionStart hook that injects compressoor session policy."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
POLICY = ROOT / "skills" / "compressoor" / "policy" / "session_injection.txt"


def main() -> int:
    json.load(sys.stdin)
    payload = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": POLICY.read_text(encoding="utf-8").strip(),
        }
    }
    json.dump(payload, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
