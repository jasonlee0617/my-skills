from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HOOKS_JSON = ROOT / ".codex" / "hooks.json"
INSTALLER = ROOT / "skills" / "compressoor" / "scripts" / "install_codex_compressoor.py"
SESSION_START = ROOT / "skills" / "compressoor" / "scripts" / "session_start_hook.py"
SESSION_RESUME = ROOT / "skills" / "compressoor" / "scripts" / "session_resume_hook.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class HookTests(unittest.TestCase):
    def test_repo_hooks_config_installs_session_bootstrap_hooks(self) -> None:
        payload = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
        hooks = payload["hooks"]
        self.assertIn("SessionStart", hooks)
        self.assertIn("SessionResume", hooks)
        start_command = hooks["SessionStart"][0]["hooks"][0]["command"]
        resume_command = hooks["SessionResume"][0]["hooks"][0]["command"]
        self.assertIn("session_start_hook.py", start_command)
        self.assertIn("session_resume_hook.py", resume_command)

    def test_installer_renders_session_hooks(self) -> None:
        module = load_module(INSTALLER, "compressoor_installer")
        hooks = json.loads(module.render_hooks_config())
        self.assertIn("SessionStart", hooks["hooks"])
        self.assertIn("SessionResume", hooks["hooks"])

    def test_installer_renders_mandatory_agents_directive(self) -> None:
        module = load_module(INSTALLER, "compressoor_installer_agents")
        agents = module.render_global_agents()
        self.assertIn("Compressoor mandatory session directive", agents)
        self.assertIn("override normal conversational defaults", agents)
        self.assertIn("send nothing before the first tool call", agents)
        self.assertIn("Never send an initial plan, thinking summary, reasoning preamble, intent statement", agents)
        self.assertIn("Do not narrate what you are about to do.", agents)
        self.assertIn("Session start and resume hooks must reinforce this same rule set.", agents)

    def test_installer_main_writes_agents_and_hooks_only(self) -> None:
        module = load_module(INSTALLER, "compressoor_installer_main")
        with tempfile.TemporaryDirectory() as td:
            agents = Path(td) / "AGENTS.md"
            hooks = Path(td) / "hooks.json"
            marketplace = Path(td) / ".agents" / "plugins" / "marketplace.json"
            plugin_dir = Path(td) / "plugins" / "compressoor"
            old_argv = __import__("sys").argv
            __import__("sys").argv = [
                "install_codex_compressoor.py",
                "--force",
                "--global-agents",
                str(agents),
                "--global-hooks",
                str(hooks),
                "--global-marketplace",
                str(marketplace),
                "--global-plugin-dir",
                str(plugin_dir),
                "--plugin-source",
                str(ROOT / "plugins" / "compressoor"),
            ]
            try:
                self.assertEqual(module.main(), 0)
            finally:
                __import__("sys").argv = old_argv
            self.assertTrue(agents.exists())
            self.assertTrue(hooks.exists())
            self.assertTrue(marketplace.exists())
            self.assertTrue(plugin_dir.is_symlink())

    def test_installer_appends_existing_agents_instead_of_replacing(self) -> None:
        module = load_module(INSTALLER, "compressoor_installer_merge")
        with tempfile.TemporaryDirectory() as td:
            agents = Path(td) / "AGENTS.md"
            agents.write_text("Existing repo note.\n", encoding="utf-8")
            changed = module.write_agents_text(agents, module.render_global_agents())
            text = agents.read_text(encoding="utf-8")
            self.assertTrue(changed)
            self.assertIn("Existing repo note.", text)
            self.assertIn("Compressoor mandatory session directive", text)

    def test_installer_renders_global_marketplace_entry(self) -> None:
        module = load_module(INSTALLER, "compressoor_installer_marketplace")
        text = module.render_global_marketplace()
        payload = json.loads(text)
        self.assertEqual(payload["name"], "local-plugins")
        self.assertEqual(payload["plugins"][0]["name"], "compressoor")
        self.assertEqual(payload["plugins"][0]["source"]["path"], "./plugins/compressoor")

    def test_session_hook_scripts_emit_policy_context(self) -> None:
        for event_name, script in (("SessionStart", SESSION_START), ("SessionResume", SESSION_RESUME)):
            with self.subTest(event_name=event_name):
                proc = subprocess.run(
                    ["python3", str(script)],
                    input="{}",
                    capture_output=True,
                    text=True,
                    check=True,
                )
                payload = json.loads(proc.stdout)
                hook = payload["hookSpecificOutput"]
                self.assertEqual(hook["hookEventName"], event_name)
                self.assertIn("Compressoor mandatory session directive", hook["additionalContext"])
                self.assertIn("The tool loop comes first", hook["additionalContext"])
                self.assertIn("send nothing before the first tool call", hook["additionalContext"])
                self.assertIn("initial plan, thinking summary, reasoning preamble, intent statement", hook["additionalContext"])
                self.assertIn("Do not narrate what you are about to do.", hook["additionalContext"])
                self.assertIn("Session start and resume hooks are active to reinforce this same rule set.", hook["additionalContext"])
