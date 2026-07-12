#!/usr/bin/env python3
"""Claude Code SessionStart hook that injects compressoor session policy.

Claude Code pipes JSON to stdin with a `source` field (startup|resume|clear|compact).
To inject context, print text to stdout and exit 0.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
POLICY = ROOT / "skills" / "compressoor" / "policy" / "session_injection.txt"


def main() -> int:
    event = json.load(sys.stdin)
    source = event.get("source", "startup")
    policy = POLICY.read_text(encoding="utf-8").strip()

    # Inject policy as plain text to stdout for all session sources
    if source in ("startup", "resume", "clear", "compact"):
        print(policy)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
