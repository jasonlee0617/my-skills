#!/usr/bin/env python3
"""Launch interactive Codex with the compressoor runtime policy prompt."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
INTERACTIVE_SUBCOMMANDS = {
    "exec",
    "review",
    "login",
    "logout",
    "mcp",
    "mcp-server",
    "app-server",
    "app",
    "completion",
    "sandbox",
    "debug",
    "apply",
    "resume",
    "fork",
    "cloud",
    "features",
    "help",
}
POLICY = ROOT / "skills" / "compressoor" / "policy" / "session_injection.txt"


def has_compressoor_hooks() -> bool:
    hooks_path = ROOT / ".codex" / "hooks.json"
    if not hooks_path.exists():
        return False
    try:
        payload = __import__("json").loads(hooks_path.read_text(encoding="utf-8"))
    except Exception:
        return False
    hooks = payload.get("hooks")
    return isinstance(hooks, dict) and any(hooks.values())


def build_bootstrap() -> str:
    return POLICY.read_text(encoding="utf-8").strip()


def has_compressoor_policy() -> bool:
    if os.environ.get("COMPRESSOOR_FORCE_BOOTSTRAP") == "1":
        return False
    if has_compressoor_hooks():
        return True
    markers = (
        "$compressoor",
        "Compressoor runtime policy is active",
        "concise runtime policy",
        "tool-first",
    )
    candidates = [
        ROOT / "AGENTS.md",
        Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "AGENTS.md",
    ]
    for path in candidates:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if any(marker in text for marker in markers):
            return True
    return False


def compose_prompt(user_prompt: str | None) -> str:
    if has_compressoor_policy():
        return user_prompt or ""
    packed = build_bootstrap()
    if user_prompt:
        return f"{packed}\n{user_prompt}"
    return packed


def normalize_forward_args(argv: list[str]) -> list[str]:
    if argv and argv[0] == "--":
        return argv[1:]
    return argv


def reject_noninteractive_subcommands(argv: list[str]) -> None:
    for token in argv:
        if token == "--":
            continue
        if token.startswith("-"):
            continue
        if token in INTERACTIVE_SUBCOMMANDS:
            raise SystemExit(
                f"launch_codex_compressoor.py only wraps interactive `codex` sessions; got subcommand `{token}`"
            )
        break


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch Codex with an explicit compressoor session system prompt.")
    parser.add_argument("--codex-bin", default=os.environ.get("CODEX_BIN", "codex"))
    parser.add_argument("--prompt", help="Optional user prompt appended after the explicit session prompt.")
    parser.add_argument(
        "--print-bootstrap",
        action="store_true",
        help="Print the explicit startup prompt and exit.",
    )
    parser.add_argument("codex_args", nargs=argparse.REMAINDER)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.print_bootstrap:
        print(build_bootstrap())
        return 0

    codex_args = normalize_forward_args(args.codex_args)
    reject_noninteractive_subcommands(codex_args)
    cmd = [args.codex_bin, *codex_args, compose_prompt(args.prompt)]
    os.execvp(args.codex_bin, cmd)


if __name__ == "__main__":
    raise SystemExit(main())
