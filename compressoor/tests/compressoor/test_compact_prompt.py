from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skills" / "compressoor" / "scripts" / "compact_prompt.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class CompactPromptTests(unittest.TestCase):
    def test_compacts_auth_fix_prompt(self) -> None:
        module = load_module(SCRIPT, "compact_prompt_auth")
        out = module.compact_prompt(
            "Fix auth middleware token expiry bug. Do not change the API contract. "
            "Keep the current error message exactly the same. Update tests around the boundary case and do not introduce a database migration."
        )
        self.assertIn("fix auth middleware token expiry bug", out)
        self.assertIn("api stable", out)
        self.assertIn("err exact", out)
        self.assertIn("no db mig", out)

    def test_preserves_protected_atoms(self) -> None:
        module = load_module(SCRIPT, "compact_prompt_atoms")
        out = module.compact_prompt(
            'Do not change the health check path `/healthz`. Risk: older workers still expect "DATABASE_URL".'
        )
        self.assertIn("`/healthz`", out)
        self.assertIn('"DATABASE_URL"', out)

    def test_compacts_review_and_handoff_patterns_more_aggressively(self) -> None:
        module = load_module(SCRIPT, "compact_prompt_patterns")
        review = module.compact_prompt(
            "Findings: src/auth/session.ts may leak stale auth state after partial invalidation. "
            "Keep the external API unchanged. Add a regression test for concurrent invalidation. "
            "Risk: admin dashboards currently rely on the old session-miss metric shape."
        )
        handoff = module.compact_prompt(
            "Current status: CSV parser patch is in src/parser/csv.ts. "
            "Repro still exists on one legacy fixture only. Unit tests pass; integration tests not run yet. "
            "Do not change CSV output shape. Next steps: capture the failing fixture, run integration tests, then compare delimiter normalization."
        )
        self.assertIn("stale-auth@partial-inval", review)
        self.assertIn("reg concurrent", review)
        self.assertIn("next fixture+integ+cmp-delim", handoff)
        self.assertNotIn("integ nt", handoff)


if __name__ == "__main__":
    unittest.main()
