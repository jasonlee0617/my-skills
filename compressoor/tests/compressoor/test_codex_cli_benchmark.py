from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "benchmarks" / "benchmark_codex_cli.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class CodexCliBenchmarkTests(unittest.TestCase):
    def test_load_scenarios_supports_explicit_turn_lists(self) -> None:
        module = load_module(SCRIPT, "benchmark_codex_cli_scenarios")
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "scenarios.jsonl"
            path.write_text(
                json.dumps({"id": "case_a", "domain": "code", "turns": ["first", "second"]}) + "\n",
                encoding="utf-8",
            )
            scenarios = module.load_scenarios(path, limit=0)
        self.assertEqual(len(scenarios), 1)
        self.assertEqual(scenarios[0].case_id, "case_a")
        self.assertEqual(scenarios[0].turns, ["first", "second"])

    def test_extract_usage_from_json_event_payload(self) -> None:
        module = load_module(SCRIPT, "benchmark_codex_cli_json")
        out = "\n".join(
            [
                '{"type":"thread.started","thread_id":"abc"}',
                '{"type":"turn.completed","token_usage":{"input":120,"output":30,"total":150,"cached_input":40}}',
            ]
        )
        usage = module.extract_usage(out, "")
        self.assertIsNotNone(usage)
        assert usage is not None
        self.assertEqual(usage.total_tokens, 150)
        self.assertEqual(usage.input_tokens, 120)
        self.assertEqual(usage.output_tokens, 30)
        self.assertEqual(usage.cached_input_tokens, 40)

    def test_extract_usage_from_turn_completed_usage_without_total(self) -> None:
        module = load_module(SCRIPT, "benchmark_codex_cli_usage")
        out = "\n".join(
            [
                '{"type":"thread.started","thread_id":"abc"}',
                '{"type":"turn.completed","usage":{"input_tokens":11559,"cached_input_tokens":3456,"output_tokens":252}}',
            ]
        )
        usage = module.extract_usage(out, "")
        self.assertIsNotNone(usage)
        assert usage is not None
        self.assertEqual(usage.total_tokens, 11811)
        self.assertEqual(usage.input_tokens, 11559)
        self.assertEqual(usage.output_tokens, 252)
        self.assertEqual(usage.cached_input_tokens, 3456)

    def test_extract_usage_from_plaintext_fallback(self) -> None:
        module = load_module(SCRIPT, "benchmark_codex_cli_text")
        usage = module.extract_usage("", "Token usage: total=210 input=150 output=60 cached_input=10")
        self.assertIsNotNone(usage)
        assert usage is not None
        self.assertEqual(usage.total_tokens, 210)
        self.assertEqual(usage.input_tokens, 150)
        self.assertEqual(usage.output_tokens, 60)
        self.assertEqual(usage.cached_input_tokens, 10)

    def test_extract_thread_id_from_json_event_payload(self) -> None:
        module = load_module(SCRIPT, "benchmark_codex_cli_thread")
        out = "\n".join(
            [
                '{"type":"thread.started","thread_id":"abc-123"}',
                '{"type":"turn.started"}',
            ]
        )
        self.assertEqual(module.extract_thread_id(out), "abc-123")

    def test_build_codex_command_for_fresh_exec(self) -> None:
        module = load_module(SCRIPT, "benchmark_codex_cli_cmd_exec")
        command = module.build_codex_command(
            codex_bin="codex",
            workspace=Path("/tmp/ws"),
            prompt="hello",
            model="",
            enabled=True,
            session_id=None,
        )
        self.assertEqual(
            command,
            [
                "codex",
                "exec",
                "--json",
                "--skip-git-repo-check",
                "--enable",
                "codex_hooks",
                "--cd",
                "/tmp/ws",
                "hello",
            ],
        )

    def test_workspace_has_hooks_requires_nonempty_hook_config(self) -> None:
        module = load_module(SCRIPT, "benchmark_codex_cli_hooks_present")
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            hooks = workspace / ".codex" / "hooks.json"
            hooks.parent.mkdir(parents=True, exist_ok=True)
            hooks.write_text('{"hooks":{}}', encoding="utf-8")
            self.assertFalse(module.workspace_has_hooks(workspace))
            hooks.write_text('{"hooks":{"UserPromptSubmit":[{"hooks":[{"type":"command","command":"x"}]}]}}', encoding="utf-8")
            self.assertTrue(module.workspace_has_hooks(workspace))

    def test_build_codex_command_for_resume_puts_flags_before_session_id(self) -> None:
        module = load_module(SCRIPT, "benchmark_codex_cli_cmd_resume")
        command = module.build_codex_command(
            codex_bin="codex",
            workspace=Path("/tmp/ws"),
            prompt="next",
            model="gpt-test",
            enabled=False,
            session_id="thread-123",
        )
        self.assertEqual(
            command,
            [
                "codex",
                "exec",
                "resume",
                "--json",
                "--skip-git-repo-check",
                "--model",
                "gpt-test",
                "thread-123",
                "next",
            ],
        )

    def test_build_codex_command_for_resume_does_not_reenable_hooks(self) -> None:
        module = load_module(SCRIPT, "benchmark_codex_cli_cmd_resume_hooks")
        command = module.build_codex_command(
            codex_bin="codex",
            workspace=Path("/tmp/ws"),
            prompt="next",
            model="",
            enabled=True,
            session_id="thread-123",
        )
        self.assertNotIn("codex_hooks", command)

    def test_prepare_workspace_disables_repo_policy_files(self) -> None:
        module = load_module(SCRIPT, "benchmark_codex_cli_workspace")
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td) / "disabled"
            module.prepare_workspace(workspace, enabled=False)
            self.assertFalse((workspace / "AGENTS.md").exists())
            self.assertFalse((workspace / ".codex" / "hooks.json").exists())
            self.assertTrue((workspace / "README.md").exists())

    def test_prepare_workspace_preserves_dangling_symlinks(self) -> None:
        module = load_module(SCRIPT, "benchmark_codex_cli_workspace_symlink")
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td) / "enabled"
            module.prepare_workspace(workspace, enabled=True)
            copied = workspace / "plugins" / "compressoor" / "1.0.0"
            self.assertTrue(copied.is_symlink())
            self.assertEqual(os.readlink(copied), "/Users/max/.codex/cache/local/compressoor/1.0.0/")

    def test_repo_policy_overhead_stays_compact(self) -> None:
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8").strip()
        self.assertIn("The tool loop comes first", agents)
        self.assertIn("short professional language", agents)
        self.assertLess(len(agents), 460)

    def test_prepare_codex_home_copies_auth_only(self) -> None:
        module = load_module(SCRIPT, "benchmark_codex_cli_home")
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source_home"
            dest = Path(td) / "dest_home"
            source.mkdir()
            (source / "auth.json").write_text('{"token":"x"}', encoding="utf-8")
            (source / "config.toml").write_text("ignored = true\n", encoding="utf-8")
            module.prepare_codex_home(dest, source)
            self.assertTrue((dest / "auth.json").exists())
            self.assertFalse((dest / "config.toml").exists())


if __name__ == "__main__":
    unittest.main()
