from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "benchmarks" / "benchmark_explicit_packed_context.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class ExplicitContextBenchmarkTests(unittest.TestCase):
    def test_build_packed_followup_is_shorter_than_verbose_for_sample_case(self) -> None:
        module = load_module(SCRIPT, "benchmark_explicit_context")
        prior = (
            "Fix auth middleware token expiry bug. Do not change the API contract. "
            "Keep the current error message exactly the same. The likely bug is that token expiry uses < instead of <=. "
            "Update tests around the boundary case and do not introduce a database migration."
        )
        followup = "Continue from the earlier context. Give the final plan and test checklist."
        verbose = module.build_verbose_followup(prior, followup)
        packed = module.build_packed_followup(prior, followup, "code", "sample")
        verbose_tokens, encoding_used = module.token_count(verbose, "o200k_base")
        packed_tokens, _ = module.token_count(packed, "o200k_base")
        self.assertIn("o200k_base", encoding_used)
        self.assertLess(packed_tokens, verbose_tokens)

    def test_build_codex_command_stays_neutral(self) -> None:
        module = load_module(SCRIPT, "benchmark_explicit_context_cmd")
        command = module.build_codex_command("codex", Path("/tmp/ws"), "hello", "")
        self.assertEqual(
            command,
            [
                "codex",
                "exec",
                "--json",
                "--skip-git-repo-check",
                "--cd",
                "/tmp/ws",
                "hello",
            ],
        )

    def test_add_benchmark_nonce_appends_shared_suffix(self) -> None:
        module = load_module(SCRIPT, "benchmark_explicit_context_nonce")
        prompt = module.add_benchmark_nonce("base", "case-1")
        self.assertIn("Benchmark nonce: case-1", prompt)
        self.assertTrue(prompt.startswith("base"))

    def test_compact_min_is_supported_variant(self) -> None:
        module = load_module(SCRIPT, "benchmark_explicit_context_min")
        prompt = module.build_variant_prompt(
            module.VARIANT_COMPACT_MIN,
            "Fix auth middleware token expiry bug. Do not change the API contract.",
            "Give the final plan and test checklist.",
            "code",
            "sample",
        )
        self.assertIn("CTX:", prompt)
        self.assertIn("REQ:", prompt)
        self.assertNotIn("Current request:", prompt)
        compact = module.build_variant_prompt(
            module.VARIANT_COMPACT,
            "Fix auth middleware token expiry bug. Do not change the API contract. Keep the current error message exactly the same. Update tests around the boundary case and do not introduce a database migration.",
            "Give the final plan and test checklist.",
            "code",
            "sample",
        )
        self.assertLessEqual(len(prompt), len(compact))

    def test_build_verbose_followup_uses_compact_scaffold(self) -> None:
        module = load_module(SCRIPT, "benchmark_explicit_context_scaffold")
        prompt = module.build_verbose_followup("earlier", "followup")
        self.assertEqual(prompt, "CTX:\nearlier\nREQ:\nfollowup\n")

    def test_load_scenarios_supports_single_source_cases(self) -> None:
        module = load_module(SCRIPT, "benchmark_explicit_context_cases")
        scenarios = module.load_scenarios(ROOT / "benchmarks" / "prompts.json", 1)
        self.assertEqual(len(scenarios), 1)
        self.assertEqual(scenarios[0].case_id, "react_rerender_bug")
        self.assertEqual(scenarios[0].label, "Explain React re-render bug")
        self.assertEqual(len(scenarios[0].turns), 2)

    def test_load_scenarios_keeps_jsonl_back_compat(self) -> None:
        module = load_module(SCRIPT, "benchmark_explicit_context_jsonl")
        scenarios = module.load_scenarios(ROOT / "benchmarks" / "caveman_style_cases.jsonl", 1)
        self.assertEqual(len(scenarios), 1)
        self.assertEqual(scenarios[0].case_id, "react_rerender_bug")
        self.assertEqual(scenarios[0].label, "react_rerender_bug")

    def test_current_status_prefers_handoff_over_shorter_constraint_template(self) -> None:
        pack_module = load_module(ROOT / "skills" / "compressoor" / "scripts" / "pack_ccm.py", "pack_ccm_template_pick")
        text = (
            "Current status: search ranking patch is implemented in src/search/rank.ts, but integration tests are not run yet. "
            "Unit tests pass. Keep the API contract unchanged. "
            "Risk: older ranking fixtures may break if score normalization shifts. "
            "Next steps: run integration tests, verify one old fixture, then merge if green."
        )
        packed = pack_module.pack(text, "auto", "code", "release_handoff_search")
        self.assertTrue(packed.startswith("H1["), packed)

    def test_single_field_constraint_can_use_compact_template(self) -> None:
        pack_module = load_module(ROOT / "skills" / "compressoor" / "scripts" / "pack_ccm.py", "pack_ccm_single_constraint")
        packed = pack_module.pack("Keep API stable.", "auto", "code", "sample")
        self.assertEqual(packed, "K1[api=stable]\n")

    def test_compact_text_is_cached(self) -> None:
        module = load_module(SCRIPT, "benchmark_explicit_context_cache")
        module.compact_text.cache_clear()
        prior = "Fix auth middleware token expiry bug. Do not change the API contract."
        first = module.compact_text(prior)
        second = module.compact_text(prior)
        self.assertEqual(first, second)
        self.assertEqual(module.compact_text.cache_info().hits, 1)

    def test_prepare_clean_workspace_preserves_dangling_symlinks(self) -> None:
        module = load_module(SCRIPT, "benchmark_explicit_context_workspace")
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "workspace"
            module.prepare_clean_workspace(dest)
            copied = dest / "plugins" / "compressoor" / "1.0.0"
            self.assertTrue(copied.is_symlink())
            self.assertEqual(os.readlink(copied), "/Users/max/.codex/cache/local/compressoor/1.0.0/")

    def test_format_markdown_table_matches_caveman_style(self) -> None:
        module = load_module(SCRIPT, "benchmark_explicit_context_table")
        rows = [
            {
                "label": "Explain React re-render bug",
                "verbose_tokens": 55,
                "compact_tokens": 40,
                "compact_saved_pct": 27.3,
                "compact_min_tokens": 33,
                "compact_min_saved_pct": 40.0,
            }
        ]
        summary = {
            "avg_verbose_tokens": 55.0,
            "avg_compact_tokens": 40.0,
            "avg_saved_percent_compact": 27.3,
            "avg_compact_min_tokens": 33.0,
            "avg_saved_percent_compact_min": 40.0,
            "min_saved_percent_compact": 27.3,
            "max_saved_percent_compact": 27.3,
            "min_saved_percent_compact_min": 40.0,
            "max_saved_percent_compact_min": 40.0,
        }
        table = module.format_markdown_table(rows, summary)
        self.assertIn("| Task | Verbose | `compact` | Saved | `compact_min` | Saved |", table)
        self.assertIn("| Explain React re-render bug | 55 | 40 | 27.3% | 33 | 40.0% |", table)
        self.assertIn("*Range: `compact` 27.3% to 27.3%; `compact_min` 40.0% to 40.0%.*", table)


if __name__ == "__main__":
    unittest.main()
