#!/usr/bin/env python3
"""Install compressoor's concise runtime policy into AGENTS and hooks files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
GLOBAL_TEMPLATE = ROOT / "skills" / "compressoor" / "policy" / "global_agents.md"
GLOBAL_MARKETPLACE_ENTRY = {
    "name": "compressoor",
    "source": {"source": "local", "path": "./plugins/compressoor"},
    "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
    "category": "Productivity",
}


def render_global_agents() -> str:
    return GLOBAL_TEMPLATE.read_text(encoding="utf-8").rstrip() + "\n"


def render_global_marketplace(existing: str | None = None) -> str:
    if existing:
        payload = json.loads(existing)
    else:
        payload = {
            "name": "local-plugins",
            "interface": {"displayName": "Local Plugins"},
            "plugins": [],
        }

    plugins = payload.setdefault("plugins", [])
    for index, plugin in enumerate(plugins):
        if plugin.get("name") == GLOBAL_MARKETPLACE_ENTRY["name"]:
            plugins[index] = GLOBAL_MARKETPLACE_ENTRY
            break
    else:
        plugins.append(GLOBAL_MARKETPLACE_ENTRY)

    return json.dumps(payload, indent=2) + "\n"


def hook_command(script_name: str) -> str:
    return f"python3 {ROOT / 'skills' / 'compressoor' / 'scripts' / script_name}"


def render_hooks_config() -> str:
    payload = {
        "hooks": {
            "SessionStart": [
                {
                    "hooks": [
                        {"type": "command", "command": hook_command("session_start_hook.py")},
                    ]
                }
            ],
            "SessionResume": [
                {
                    "hooks": [
                        {"type": "command", "command": hook_command("session_resume_hook.py")},
                    ]
                }
            ],
        }
    }
    return json.dumps(payload, indent=2) + "\n"


def merge_agents(existing: str, content: str) -> str:
    stripped_content = content.strip()
    if stripped_content in existing:
        return existing
    if not existing.strip():
        return content
    return existing.rstrip() + "\n\n" + content


def write_text(path: Path, content: str, force: bool = False) -> bool:
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if existing == content:
            return False
        if not force:
            raise FileExistsError(f"{path} already exists; rerun with --force to replace it")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def write_agents_text(path: Path, content: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    merged = merge_agents(existing, content)
    if existing == merged:
        return False
    path.write_text(merged, encoding="utf-8")
    return True


def write_marketplace(path: Path, force: bool = False) -> bool:
    existing = path.read_text(encoding="utf-8") if path.exists() else None
    rendered = render_global_marketplace(existing)
    return write_text(path, rendered, force=force)


def ensure_plugin_link(path: Path, target: Path, force: bool = False) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink() and path.resolve() == target.resolve():
        return False
    if path.exists() or path.is_symlink():
        if not force:
            raise FileExistsError(f"{path} already exists; rerun with --force to replace it")
        if path.is_dir() and not path.is_symlink():
            raise FileExistsError(f"{path} exists as a directory; remove it manually or choose another path")
        path.unlink()
    path.symlink_to(target, target_is_directory=True)
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install compressoor's concise runtime policy notes.")
    parser.add_argument("--global-agents", type=Path, default=Path.home() / ".codex" / "AGENTS.md")
    parser.add_argument("--global-hooks", type=Path, default=Path.home() / ".codex" / "hooks.json")
    parser.add_argument("--global-marketplace", type=Path, default=Path.home() / ".agents" / "plugins" / "marketplace.json")
    parser.add_argument("--global-plugin-dir", type=Path, default=Path.home() / "plugins" / "compressoor")
    parser.add_argument("--plugin-source", type=Path, default=ROOT / "plugins" / "compressoor")
    parser.add_argument("--project-agents", type=Path, action="append", default=[])
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    content = render_global_agents()
    hooks = render_hooks_config()

    for path in [args.global_agents, *args.project_agents]:
        changed = write_agents_text(path, content)
        print(f"{'wrote' if changed else 'unchanged'} {path}")

    changed = write_text(args.global_hooks, hooks, force=args.force)
    print(f"{'wrote' if changed else 'unchanged'} {args.global_hooks}")
    changed = write_marketplace(args.global_marketplace, force=args.force)
    print(f"{'wrote' if changed else 'unchanged'} {args.global_marketplace}")
    changed = ensure_plugin_link(args.global_plugin_dir, args.plugin_source, force=args.force)
    print(f"{'linked' if changed else 'unchanged'} {args.global_plugin_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
