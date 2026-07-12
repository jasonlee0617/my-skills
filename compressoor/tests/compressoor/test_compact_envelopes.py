from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / "skills" / "compressoor" / "scripts" / "pack_ccm.py"


CASES = {
    "handoff": ("Current status: parser change is implemented in src/parser.ts, but integration tests are not run yet. Unit tests pass. The main unresolved issue is whether the new delimiter handling breaks legacy CSV imports. Next steps are to run integration tests and verify one old fixture before merging.", "H1["),
    "memory": ("This repository uses Bun for scripts, not npm. Prefer ripgrep for search. Avoid destructive git commands unless explicitly requested. If editing frontend code, preserve the existing design system and do not introduce a new font stack.", "M1["),
    "constraint": ("Auth fix is in src/auth.ts. Keep API stable. Keep the exact error text. Tests for the boundary case still need to be added. No DB migration.", "K1["),
    "review": ("Findings: src/cache.ts may leak stale entries after partial invalidation. Keep the external API unchanged. Add a regression test for concurrent invalidation. Risk: metrics dashboards currently rely on the old miss counter shape.", "V1["),
    "progress": ("Status: benchmarking in progress. Next step: verify token deltas.", "P1["),
}


class EnvelopeTests(unittest.TestCase):
    def test_compact_envelopes_selected(self) -> None:
        for name, (text, prefix) in CASES.items():
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory() as td:
                    src = Path(td) / "src.txt"
                    src.write_text(text + "\n", encoding="utf-8")
                    proc = subprocess.run(
                        ["python3", str(PACK), "--level", "auto", "--domain", "code", "--source-id", name, str(src)],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    self.assertTrue(proc.stdout.startswith(prefix), proc.stdout)

    def test_instruction_like_text_does_not_use_compact_template(self) -> None:
        text = (
            "Use $compressoor by default across projects. Prefer compact envelopes for durable state. "
            "Tool calls first; no human-readable pre-tool status text. Use H1 M1 K1 V1 E1 when shorter."
        )
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "src.txt"
            src.write_text(text + "\n", encoding="utf-8")
            proc = subprocess.run(
                ["python3", str(PACK), "--level", "auto", "--domain", "repo", "--source-id", "policy", str(src)],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertTrue(proc.stdout.startswith("CCM1|"), proc.stdout)

    def test_skill_defaults_require_terse_execution_mode(self) -> None:
        skill = (ROOT / "skills" / "compressoor" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("do not narrate every repo exploration, search, or implementation step", skill)
        self.assertIn("prefer the next relevant tool action before any outward text", skill)
        self.assertIn("do not send acknowledgements, commentary, or status text before, between, or during tool calls", skill)
        self.assertIn("never give progress updates or commentary before tools, when calling tools, or during tool loops", skill)
        self.assertIn("after internal thinking, move directly into the tool-calling loop", skill)
        self.assertIn("finish the current tool loop before replying unless blocked", skill)
        self.assertIn("stop only to ask a necessary question or to summarize what was done", skill)
        self.assertIn("store it in `CCM1` or a compact envelope", skill)
        self.assertIn("stop carrying the verbose version forward", skill)
        self.assertIn("Never send a progress update before the current tool loop is complete.", skill)
        self.assertIn("Never pause after internal thinking to narrate intent when you can enter the tool loop instead.", skill)
        self.assertIn("Never hand-write fake packed status for live progress.", skill)
        self.assertIn("Keep final close-out concise but complete.", skill)
        self.assertIn("Keep summaries of steps taken as short as possible.", skill)
        self.assertIn("Never turn concision into caveman speech.", skill)
