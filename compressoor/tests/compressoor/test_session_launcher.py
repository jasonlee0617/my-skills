from __future__ import annotations

import importlib.util
import os
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = ROOT / "skills" / "compressoor" / "scripts" / "launch_codex_compressoor.py"
PLUGIN_LAUNCHER = ROOT / "plugins" / "compressoor" / "skills" / "compressoor" / "scripts" / "launch_codex_compressoor.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SessionLauncherTests(unittest.TestCase):
    def test_launchers_exist_in_skill_and_plugin(self) -> None:
        self.assertTrue(LAUNCHER.exists())
        self.assertTrue(PLUGIN_LAUNCHER.exists())

    def test_bootstrap_is_runtime_policy_prompt(self) -> None:
        module = load_module(LAUNCHER, "compressoor_launcher")
        prompt = module.build_bootstrap()
        self.assertIn("Compressoor mandatory session directive", prompt)
        self.assertIn("The tool loop comes first", prompt)
        self.assertIn("send nothing before the first tool call", prompt)
        self.assertIn("Never send an initial plan, thinking summary, reasoning preamble, intent statement", prompt)
        self.assertIn("Do not narrate what you are about to do", prompt)
        self.assertIn("Session start and resume hooks are active to reinforce this same rule set", prompt)
        self.assertIn("concise professional language", prompt)
        self.assertLess(len(prompt), 1100)

    def test_compose_prompt_skips_session_prompt_when_policy_exists(self) -> None:
        module = load_module(LAUNCHER, "compressoor_launcher_prompt")
        prompt = module.compose_prompt("Fix the failing test.")
        self.assertEqual(prompt, "Fix the failing test.")

    def test_compose_prompt_uses_bootstrap_without_agents_policy(self) -> None:
        module = load_module(LAUNCHER, "compressoor_launcher_bootstrap")
        old = os.environ.get("COMPRESSOOR_FORCE_BOOTSTRAP")
        os.environ["COMPRESSOOR_FORCE_BOOTSTRAP"] = "1"
        try:
            prompt = module.compose_prompt("Fix the failing test.")
        finally:
            if old is None:
                os.environ.pop("COMPRESSOOR_FORCE_BOOTSTRAP", None)
            else:
                os.environ["COMPRESSOOR_FORCE_BOOTSTRAP"] = old
        self.assertTrue(prompt.startswith("Compressoor mandatory session directive"), prompt)
        self.assertTrue(prompt.endswith("\nFix the failing test."), prompt)

    def test_noninteractive_subcommands_are_rejected(self) -> None:
        module = load_module(LAUNCHER, "compressoor_launcher_reject")
        with self.assertRaises(SystemExit):
            module.reject_noninteractive_subcommands(["exec", "fix bug"])
