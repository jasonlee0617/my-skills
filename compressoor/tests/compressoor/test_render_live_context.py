from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skills" / "compressoor" / "scripts" / "render_live_context.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class RenderLiveContextTests(unittest.TestCase):
    def test_render_live_context_expands_compact_constraint_pack(self) -> None:
        module = load_module(SCRIPT, "render_live_context")
        out = module.render_live_context("K1[api=stable;err=exact;mig=no;bt=todo;cmp=<,<=]")
        self.assertIn("C: do not change the API contract", out)
        self.assertIn("D: the likely bug is that token expiry uses < instead of <=", out)
        self.assertIn("T: tests for the boundary case still need to be added", out)
        self.assertNotIn("Durable context:", out)

    def test_render_live_context_min_prioritizes_followup_relevant_points(self) -> None:
        module = load_module(SCRIPT, "render_live_context_min")
        packed = "K1[api=stable;err=exact;mig=no;bt=todo;cmp=<,<=]"
        out = module.render_live_context_min(packed, followup_text="Give the final plan and test checklist.", bullet_limit=3)
        self.assertIn("C: do not change the API contract", out)
        self.assertIn("T: tests for the boundary case still need to be added", out)
        self.assertLessEqual(len([line for line in out.splitlines() if ": " in line and not line.startswith("CTX")]), 3)

    def test_render_live_context_empty_state_uses_short_none_marker(self) -> None:
        module = load_module(SCRIPT, "render_live_context_empty")
        out = module.render_live_context("CCM1|lvl=std|dom=repo|src=empty\n")
        self.assertEqual(out, "CTX: none\n")


if __name__ == "__main__":
    unittest.main()
