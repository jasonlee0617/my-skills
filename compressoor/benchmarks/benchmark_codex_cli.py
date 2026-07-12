#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCENARIOS = ROOT / "benchmarks" / "codex_cli_scenarios.jsonl"
REPO_HOOKS = ROOT / ".codex" / "hooks.json"
REPO_AGENTS = ROOT / "AGENTS.md"
DEFAULT_CODEX_HOME = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
CONFIG_WARNING = (
    "Codex CLI benchmarking needs network access and a working Codex auth setup. "
    "If your local run fails before producing usage events, verify `codex exec` works first."
)
TOKEN_KEYS = {
    "input": "input_tokens",
    "input_tokens": "input_tokens",
    "output": "output_tokens",
    "output_tokens": "output_tokens",
    "total": "total_tokens",
    "total_tokens": "total_tokens",
    "cached_input": "cached_input_tokens",
    "cached_input_tokens": "cached_input_tokens",
    "reasoning": "reasoning_tokens",
    "reasoning_tokens": "reasoning_tokens",
}
TOKEN_USAGE_LINE_RE = re.compile(
    r"Token usage:\s+total=(?P<total>\d+)"
    r"(?:\s+input=(?P<input>\d+))?"
    r"(?:\s+output=(?P<output>\d+))?"
    r"(?:\s+cached_input=(?P<cached_input>\d+))?"
    r"(?:\s+reasoning=(?P<reasoning>\d+))?"
)


@dataclass
class Scenario:
    case_id: str
    domain: str
    turns: list[str]


@dataclass
class Usage:
    total_tokens: int
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    reasoning_tokens: int = 0


@dataclass
class TurnResult:
    usage: Usage
    stdout: str
    stderr: str
    session_id: str
    last_message: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark multi-turn Codex CLI sessions with compressoor enabled and disabled."
    )
    parser.add_argument("--scenarios", type=Path, default=DEFAULT_SCENARIOS)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--codex-bin", default=os.environ.get("CODEX_BIN", "codex"))
    parser.add_argument("--model", default="")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--keep-workspaces", action="store_true")
    parser.add_argument(
        "--codex-home",
        type=Path,
        default=DEFAULT_CODEX_HOME,
        help="Source CODEX_HOME used only to seed auth into isolated benchmark homes.",
    )
    return parser.parse_args()


def load_scenarios(path: Path, limit: int) -> list[Scenario]:
    scenarios: list[Scenario] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        payload = json.loads(line)
        turns = payload.get("turns")
        if turns is None:
            turns = [payload["source"].strip()]
        scenarios.append(
            Scenario(
                case_id=payload["id"],
                domain=payload.get("domain", "general"),
                turns=[str(turn).strip() for turn in turns if str(turn).strip()],
            )
        )
    if limit > 0:
        return scenarios[:limit]
    return scenarios


def prepare_workspace(dest: Path, enabled: bool) -> None:
    shutil.copytree(ROOT, dest, dirs_exist_ok=True, symlinks=True)
    if enabled:
        return
    agents_path = dest / REPO_AGENTS.relative_to(ROOT)
    hooks_path = dest / REPO_HOOKS.relative_to(ROOT)
    if agents_path.exists():
        agents_path.unlink()
    if hooks_path.exists():
        hooks_path.unlink()


def prepare_codex_home(dest: Path, source_home: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for name in ("auth.json",):
        source = source_home / name
        if source.exists():
            shutil.copy2(source, dest / name)


def run_codex_turn(
    codex_bin: str,
    codex_home: Path,
    workspace: Path,
    prompt: str,
    timeout: int,
    model: str,
    enabled: bool,
    session_id: str | None,
) -> TurnResult:
    use_hooks = enabled and session_id is None and workspace_has_hooks(workspace)
    cmd = build_codex_command(
        codex_bin=codex_bin,
        workspace=workspace,
        prompt=prompt,
        model=model,
        enabled=use_hooks,
        session_id=session_id,
    )

    env = os.environ.copy()
    env["CODEX_HOME"] = str(codex_home)

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"codex exec failed in {workspace} with exit code {proc.returncode}\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}\n"
            f"{CONFIG_WARNING}"
        )
    usage = extract_usage(proc.stdout, proc.stderr)
    if usage is None:
        raise RuntimeError(
            f"could not find token-usage data in codex output for {workspace}\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}\n"
            f"{CONFIG_WARNING}"
        )
    thread_id = extract_thread_id(proc.stdout) or session_id
    if not thread_id:
        raise RuntimeError(
            f"could not find a Codex session id in output for {workspace}\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}\n"
        )
    return TurnResult(
        usage=usage,
        stdout=proc.stdout,
        stderr=proc.stderr,
        session_id=thread_id,
        last_message=extract_last_message(proc.stdout),
    )


def build_codex_command(
    codex_bin: str,
    workspace: Path,
    prompt: str,
    model: str,
    enabled: bool,
    session_id: str | None,
) -> list[str]:
    flags = [
        "--json",
        "--skip-git-repo-check",
    ]
    if enabled and session_id is None:
        flags.extend(["--enable", "codex_hooks"])
    if model:
        flags.extend(["--model", model])
    if session_id is None:
        return [
            codex_bin,
            "exec",
            *flags,
            "--cd",
            str(workspace),
            prompt,
        ]
    return [
        codex_bin,
        "exec",
        "resume",
        *flags,
        session_id,
        prompt,
    ]


def workspace_has_hooks(workspace: Path) -> bool:
    hooks_path = workspace / REPO_HOOKS.relative_to(ROOT)
    if not hooks_path.exists():
        return False
    try:
        payload = json.loads(hooks_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    hooks = payload.get("hooks")
    return isinstance(hooks, dict) and any(hooks.values())


def extract_thread_id(output: str) -> str | None:
    for line in output.splitlines():
        text = line.strip()
        if not text.startswith("{"):
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        if payload.get("type") == "thread.started" and isinstance(payload.get("thread_id"), str):
            return payload["thread_id"]
    return None


def extract_last_message(output: str) -> str:
    last_text = ""
    for line in output.splitlines():
        text = line.strip()
        if not text.startswith("{"):
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        if payload.get("type") != "item.completed":
            continue
        item = payload.get("item")
        if isinstance(item, dict) and item.get("type") == "agent_message" and isinstance(item.get("text"), str):
            last_text = item["text"]
    return last_text


def extract_usage(stdout: str, stderr: str) -> Usage | None:
    from_json = extract_usage_from_jsonl(stdout)
    if from_json is not None:
        return from_json
    return extract_usage_from_text(stdout + "\n" + stderr)


def extract_usage_from_jsonl(output: str) -> Usage | None:
    candidates: list[Usage] = []
    for line in output.splitlines():
        text = line.strip()
        if not text.startswith("{"):
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        candidates.extend(find_usage_candidates(payload))
    if not candidates:
        return None
    return max(candidates, key=lambda usage: usage.total_tokens)


def find_usage_candidates(payload: Any) -> list[Usage]:
    candidates: list[Usage] = []
    if isinstance(payload, dict):
        normalized = normalize_usage_dict(payload)
        if normalized is not None:
            candidates.append(normalized)
        for value in payload.values():
            candidates.extend(find_usage_candidates(value))
    elif isinstance(payload, list):
        for item in payload:
            candidates.extend(find_usage_candidates(item))
    return candidates


def normalize_usage_dict(payload: dict[str, Any]) -> Usage | None:
    mapped: dict[str, int] = {}
    for key, value in payload.items():
        if key not in TOKEN_KEYS or not isinstance(value, int):
            continue
        mapped[TOKEN_KEYS[key]] = value
    total = mapped.get("total_tokens")
    if total is None and ("input_tokens" in mapped or "output_tokens" in mapped or "reasoning_tokens" in mapped):
        total = mapped.get("input_tokens", 0) + mapped.get("output_tokens", 0) + mapped.get("reasoning_tokens", 0)
    if total is None or total == 0:
        return None
    return Usage(
        total_tokens=total,
        input_tokens=mapped.get("input_tokens", 0),
        output_tokens=mapped.get("output_tokens", 0),
        cached_input_tokens=mapped.get("cached_input_tokens", 0),
        reasoning_tokens=mapped.get("reasoning_tokens", 0),
    )


def extract_usage_from_text(output: str) -> Usage | None:
    matches = list(TOKEN_USAGE_LINE_RE.finditer(output))
    if not matches:
        return None
    match = matches[-1]
    values = {name: int(value) for name, value in match.groupdict(default="0").items()}
    return Usage(
        total_tokens=values["total"],
        input_tokens=values["input"],
        output_tokens=values["output"],
        cached_input_tokens=values["cached_input"],
        reasoning_tokens=values["reasoning"],
    )


def avg(values: list[int]) -> float:
    if not values:
        return 0.0
    return statistics.mean(values)


def sum_usage(turns: list[Usage]) -> Usage:
    return Usage(
        total_tokens=sum(turn.total_tokens for turn in turns),
        input_tokens=sum(turn.input_tokens for turn in turns),
        output_tokens=sum(turn.output_tokens for turn in turns),
        cached_input_tokens=sum(turn.cached_input_tokens for turn in turns),
        reasoning_tokens=sum(turn.reasoning_tokens for turn in turns),
    )


def print_summary(enabled_totals: list[Usage], disabled_totals: list[Usage], followup_start: int) -> None:
    enabled_total = [result.total_tokens for result in enabled_totals]
    disabled_total = [result.total_tokens for result in disabled_totals]
    avg_enabled_total = avg(enabled_total)
    avg_disabled_total = avg(disabled_total)
    total_saved = avg_disabled_total - avg_enabled_total
    total_saved_pct = 0.0 if avg_disabled_total == 0 else (total_saved / avg_disabled_total) * 100

    print(f"cases: {len(enabled_totals)}")
    print(f"disabled_avg_session_total_tokens: {avg_disabled_total:.1f}")
    print(f"enabled_avg_session_total_tokens: {avg_enabled_total:.1f}")
    print(f"avg_session_tokens_saved: {total_saved:.1f}")
    print(f"avg_session_tokens_saved_percent: {total_saved_pct:.1f}")
    print(f"disabled_avg_session_input_tokens: {avg([result.input_tokens for result in disabled_totals]):.1f}")
    print(f"enabled_avg_session_input_tokens: {avg([result.input_tokens for result in enabled_totals]):.1f}")
    print(f"disabled_avg_session_output_tokens: {avg([result.output_tokens for result in disabled_totals]):.1f}")
    print(f"enabled_avg_session_output_tokens: {avg([result.output_tokens for result in enabled_totals]):.1f}")
    print(f"disabled_avg_session_cached_input_tokens: {avg([result.cached_input_tokens for result in disabled_totals]):.1f}")
    print(f"enabled_avg_session_cached_input_tokens: {avg([result.cached_input_tokens for result in enabled_totals]):.1f}")
    if followup_start > 1:
        print(f"followup_turns_start_at: {followup_start}")


def write_turn_artifacts(base_dir: Path, scenario_id: str, turn_index: int, variant: str, result: TurnResult) -> None:
    turn_dir = base_dir / scenario_id / f"turn{turn_index}" / variant
    turn_dir.mkdir(parents=True, exist_ok=True)
    (turn_dir / "last_message.txt").write_text(result.last_message, encoding="utf-8")
    (turn_dir / "stdout.jsonl").write_text(result.stdout, encoding="utf-8")
    (turn_dir / "stderr.txt").write_text(result.stderr, encoding="utf-8")
    (turn_dir / "usage.json").write_text(
        json.dumps(
            {
                "total_tokens": result.usage.total_tokens,
                "input_tokens": result.usage.input_tokens,
                "output_tokens": result.usage.output_tokens,
                "cached_input_tokens": result.usage.cached_input_tokens,
                "reasoning_tokens": result.usage.reasoning_tokens,
                "session_id": result.session_id,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    scenarios = load_scenarios(args.scenarios, args.limit)
    enabled_session_totals: list[Usage] = []
    disabled_session_totals: list[Usage] = []
    enabled_followup_totals: list[Usage] = []
    disabled_followup_totals: list[Usage] = []

    with tempfile.TemporaryDirectory(prefix="compressoor_codex_bench_") as td:
        tmp_root = Path(td)
        enabled_workspace = tmp_root / "enabled_workspace"
        disabled_workspace = tmp_root / "disabled_workspace"
        enabled_home = tmp_root / "enabled_home"
        disabled_home = tmp_root / "disabled_home"
        artifact_root = tmp_root / "artifacts"

        prepare_workspace(enabled_workspace, enabled=True)
        prepare_workspace(disabled_workspace, enabled=False)
        prepare_codex_home(enabled_home, args.codex_home)
        prepare_codex_home(disabled_home, args.codex_home)

        if args.keep_workspaces:
            print(f"enabled_workspace: {enabled_workspace}")
            print(f"disabled_workspace: {disabled_workspace}")
            print(f"enabled_codex_home: {enabled_home}")
            print(f"disabled_codex_home: {disabled_home}")
            print(f"artifacts: {artifact_root}")

        for scenario in scenarios:
            disabled_turns: list[Usage] = []
            enabled_turns: list[Usage] = []
            disabled_session_id: str | None = None
            enabled_session_id: str | None = None

            for index, prompt in enumerate(scenario.turns, start=1):
                disabled = run_codex_turn(
                    codex_bin=args.codex_bin,
                    codex_home=disabled_home,
                    workspace=disabled_workspace,
                    prompt=prompt,
                    timeout=args.timeout,
                    model=args.model,
                    enabled=False,
                    session_id=disabled_session_id,
                )
                enabled = run_codex_turn(
                    codex_bin=args.codex_bin,
                    codex_home=enabled_home,
                    workspace=enabled_workspace,
                    prompt=prompt,
                    timeout=args.timeout,
                    model=args.model,
                    enabled=True,
                    session_id=enabled_session_id,
                )
                disabled_session_id = disabled.session_id
                enabled_session_id = enabled.session_id
                disabled_turns.append(disabled.usage)
                enabled_turns.append(enabled.usage)
                write_turn_artifacts(artifact_root, scenario.case_id, index, "disabled", disabled)
                write_turn_artifacts(artifact_root, scenario.case_id, index, "enabled", enabled)
                delta_total = disabled.usage.total_tokens - enabled.usage.total_tokens
                delta_input = disabled.usage.input_tokens - enabled.usage.input_tokens
                delta_output = disabled.usage.output_tokens - enabled.usage.output_tokens
                delta_pct = (
                    0.0
                    if disabled.usage.total_tokens == 0
                    else (delta_total / disabled.usage.total_tokens) * 100
                )
                print(
                    f"{scenario.case_id}/turn{index}: "
                    f"disabled_total={disabled.usage.total_tokens} "
                    f"enabled_total={enabled.usage.total_tokens} "
                    f"disabled_input={disabled.usage.input_tokens} "
                    f"enabled_input={enabled.usage.input_tokens} "
                    f"disabled_output={disabled.usage.output_tokens} "
                    f"enabled_output={enabled.usage.output_tokens} "
                    f"delta_total={delta_total} "
                    f"delta_input={delta_input} "
                    f"delta_output={delta_output} "
                    f"delta_pct={delta_pct:.1f}"
                )

            disabled_total = sum_usage(disabled_turns)
            enabled_total = sum_usage(enabled_turns)
            disabled_followup = sum_usage(disabled_turns[1:]) if len(disabled_turns) > 1 else Usage(total_tokens=0)
            enabled_followup = sum_usage(enabled_turns[1:]) if len(enabled_turns) > 1 else Usage(total_tokens=0)

            disabled_session_totals.append(disabled_total)
            enabled_session_totals.append(enabled_total)
            disabled_followup_totals.append(disabled_followup)
            enabled_followup_totals.append(enabled_followup)

            session_delta = disabled_total.total_tokens - enabled_total.total_tokens
            session_delta_pct = (
                0.0
                if disabled_total.total_tokens == 0
                else (session_delta / disabled_total.total_tokens) * 100
            )
            print(
                f"{scenario.case_id}: "
                f"disabled_session_total={disabled_total.total_tokens} "
                f"enabled_session_total={enabled_total.total_tokens} "
                f"delta_total={session_delta} "
                f"delta_pct={session_delta_pct:.1f}"
            )
            if len(scenario.turns) > 1:
                followup_delta = disabled_followup.total_tokens - enabled_followup.total_tokens
                followup_delta_pct = (
                    0.0
                    if disabled_followup.total_tokens == 0
                    else (followup_delta / disabled_followup.total_tokens) * 100
                )
                print(
                    f"{scenario.case_id}/followups: "
                    f"disabled_total={disabled_followup.total_tokens} "
                    f"enabled_total={enabled_followup.total_tokens} "
                    f"delta_total={followup_delta} "
                    f"delta_pct={followup_delta_pct:.1f}"
                )

        print_summary(enabled_session_totals, disabled_session_totals, followup_start=2)
        if any(total.total_tokens > 0 for total in disabled_followup_totals):
            print("followup_summary:")
            print_summary(enabled_followup_totals, disabled_followup_totals, followup_start=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
