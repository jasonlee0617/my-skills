from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PLUGIN_JSON = ROOT / "plugins" / "compressoor" / ".codex-plugin" / "plugin.json"
CLAUDE_PLUGIN_JSON = ROOT / ".claude-plugin" / "plugin.json"
CLAUDE_MARKETPLACE_JSON = ROOT / ".claude-plugin" / "marketplace.json"
CLAUDE_AGENT = ROOT / ".claude" / "agents" / "compressoor.md"
CLAUDE_COMMAND = ROOT / ".claude" / "commands" / "compressoor.md"
AGENT_YAML_PATHS = [
    ROOT / "skills" / "compressoor" / "agents" / "openai.yaml",
    ROOT / "plugins" / "compressoor" / "skills" / "compressoor" / "agents" / "openai.yaml",
]
LAUNCHER_PATHS = [
    ROOT / "skills" / "compressoor" / "scripts" / "launch_codex_compressoor.py",
    ROOT / "plugins" / "compressoor" / "skills" / "compressoor" / "scripts" / "launch_codex_compressoor.py",
]
INSTALLER_PATHS = [
    ROOT / "skills" / "compressoor" / "scripts" / "install_codex_compressoor.py",
    ROOT / "plugins" / "compressoor" / "skills" / "compressoor" / "scripts" / "install_codex_compressoor.py",
]


class PluginDefaultsTests(unittest.TestCase):
    def test_default_prompt_enforces_silent_tool_loops_and_short_professional_results(self) -> None:
        payload = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))
        prompts = payload["interface"]["defaultPrompt"]
        self.assertEqual(len(prompts), 1)
        prompt = prompts[0]
        self.assertIn("Compressoor mandatory session directive", prompt)
        self.assertIn("The tool loop comes first", prompt)
        self.assertIn("send nothing before the first tool call", prompt)
        self.assertIn("Never send an initial plan, thinking summary, reasoning preamble, intent statement", prompt)
        self.assertIn("before, between, or during tool calls", prompt)
        self.assertIn("After internal thinking, move directly into the tool-calling loop", prompt)
        self.assertIn("minimal completion summary", prompt)
        self.assertIn("Do not narrate what you are about to do", prompt)
        self.assertIn("Finish the current tool loop first", prompt)
        self.assertIn("Session start and resume hooks reinforce this same rule set", prompt)
        self.assertIn("concise professional language", prompt)
        self.assertIn("shortest useful result", prompt)
        self.assertIn("summary of steps taken to the bare minimum", prompt)
        self.assertIn("changed files only when they matter", prompt)
        self.assertLess(len(prompt), 1100)

    def test_skill_docs_require_tool_first_and_encoded_context_storage(self) -> None:
        skill_paths = [
            ROOT / "skills" / "compressoor" / "SKILL.md",
            ROOT / "plugins" / "compressoor" / "skills" / "compressoor" / "SKILL.md",
        ]
        for path in skill_paths:
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                self.assertIn("runtime policy first and a packing toolset second", text)
                self.assertIn("prefer the next relevant tool action before any outward text", text)
                self.assertIn("if tools can materially advance the task, send nothing before the first tool call", text)
                self.assertIn("do not send acknowledgements, commentary, or status text before, between, or during tool calls", text)
                self.assertIn("never give progress updates or commentary before tools, when calling tools, or during tool loops", text)
                self.assertIn("never send an initial plan, thinking summary, reasoning preamble, or intent statement before the first tool call", text)
                self.assertIn("after internal thinking, move directly into the tool-calling loop", text)
                self.assertIn("finish the current tool loop before replying unless blocked", text)
                self.assertIn("stop only to ask a necessary question or to summarize what was done", text)
                self.assertIn("Never send a progress update before the current tool loop is complete.", text)
                self.assertIn("Never send an initial plan or thinking summary before the first tool call when tools can help.", text)
                self.assertIn("Never pause after internal thinking to narrate intent when you can enter the tool loop instead.", text)
                self.assertIn("Session start and resume hooks must restate and reinforce these defaults.", text)
                self.assertIn("Never turn concision into caveman speech.", text)
                self.assertIn("Keep summaries of steps taken as short as possible.", text)
                self.assertIn("store it in `CCM1` or a compact envelope", text)

    def test_agent_yaml_prompts_define_runtime_policy(self) -> None:
        for path in AGENT_YAML_PATHS:
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                self.assertIn("Compressoor mandatory session directive", text)
                self.assertIn("The tool loop comes first", text)
                self.assertIn("send nothing before the first tool call", text)
                self.assertIn("Never send an initial plan, thinking summary, reasoning preamble, intent statement", text)
                self.assertIn("before, between, or during tool calls", text)
                self.assertIn("After internal thinking, move directly into the tool-calling loop", text)
                self.assertIn("minimal completion summary", text)
                self.assertIn("Do not narrate what you are about to do", text)
                self.assertIn("Finish the current tool loop first", text)
                self.assertIn("Session start and resume hooks reinforce this same rule set", text)
                self.assertIn("concise professional language", text)
                self.assertIn("shortest useful result", text)
                self.assertIn("summary of steps taken to the bare minimum", text)
                self.assertIn("allow_implicit_invocation: false", text)

    def test_claude_plugin_manifest_is_present_and_runtime_focused(self) -> None:
        payload = json.loads(CLAUDE_PLUGIN_JSON.read_text(encoding="utf-8"))
        self.assertEqual(payload["name"], "compressoor")
        self.assertIn("Concise runtime policy", payload["description"])
        self.assertEqual(payload["author"]["name"], "Max")

    def test_claude_marketplace_points_at_repo_root(self) -> None:
        payload = json.loads(CLAUDE_MARKETPLACE_JSON.read_text(encoding="utf-8"))
        self.assertEqual(payload["name"], "compressoor")
        self.assertEqual(len(payload["plugins"]), 1)
        plugin = payload["plugins"][0]
        self.assertEqual(plugin["name"], "compressoor")
        self.assertEqual(plugin["source"], "./")
        self.assertEqual(plugin["category"], "productivity")
        self.assertIn("concise and professional by default", plugin["description"])

    def test_claude_subagent_keeps_tool_loops_silent_and_post_loop_output_brief(self) -> None:
        text = CLAUDE_AGENT.read_text(encoding="utf-8")
        self.assertIn("Concise runtime policy specialist", text)
        self.assertIn("The tool loop comes first", text)
        self.assertIn("send nothing before the first tool call", text)
        self.assertIn("never send acknowledgements or routine status messages before or during tool loops", text)
        self.assertIn("never give progress updates or commentary before tools, when calling tools, or during tool loops", text)
        self.assertIn("never send an initial plan, thinking summary, reasoning preamble, or intent statement before the first tool call", text)
        self.assertIn("after internal thinking, go straight to the next tool call unless blocked or a necessary question must be asked", text)
        self.assertIn("finish the current tool loop before replying unless blocked", text)
        self.assertIn("packed `CCM1` block", text)
        self.assertIn("say what changed, plus failures, blockers, or risks when needed, with the bare minimum summary", text)
        self.assertIn("Do not turn concision into caveman speech", text)

    def test_claude_command_routes_into_concise_runtime_and_explicit_compaction(self) -> None:
        text = CLAUDE_COMMAND.read_text(encoding="utf-8")
        self.assertIn("Use the `compressoor` subagent", text)
        self.assertIn("concise, professional, and tool-first", text)
        self.assertIn("pack, unpack, benchmark, or rewrite durable reusable context", text)
        self.assertIn("if tools can materially advance the task, send nothing before the first tool call", text)
        self.assertIn("do not send acknowledgements, commentary, or status text before, between, or during tool calls", text)
        self.assertIn("never give progress updates or commentary before tools, when calling tools, or during tool loops", text)
        self.assertIn("never send an initial plan, thinking summary, reasoning preamble, or intent statement before the first tool call", text)
        self.assertIn("after internal thinking, move directly into the tool-calling loop unless blocked or a necessary question must be asked", text)
        self.assertIn("finish the current tool loop before replying unless blocked", text)
        self.assertIn("return a brief direct result", text)
        self.assertIn("keep any summary of steps taken to the bare minimum", text)
        self.assertIn("changed files, or risks when needed", text)
        self.assertIn("User arguments: $ARGUMENTS", text)

    def test_launchers_exist_for_session_prompt_bootstrap(self) -> None:
        for path in LAUNCHER_PATHS:
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                self.assertIn("Launch interactive Codex with the compressoor runtime policy prompt.", text)
                self.assertIn("build_bootstrap", text)
                self.assertIn("has_compressoor_policy", text)
                self.assertIn("os.execvp", text)

    def test_installers_exist_for_agents_and_session_hooks(self) -> None:
        for path in INSTALLER_PATHS:
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                self.assertIn("Install compressoor's concise runtime policy into AGENTS and hooks files.", text)
                self.assertIn("render_hooks_config", text)
                self.assertIn("render_global_marketplace", text)
                self.assertIn("write_agents_text", text)
                self.assertIn("ensure_plugin_link", text)
                self.assertIn("--global-marketplace", text)
                self.assertIn("--global-plugin-dir", text)
                self.assertIn("SessionStart", text)
                self.assertIn("SessionResume", text)
