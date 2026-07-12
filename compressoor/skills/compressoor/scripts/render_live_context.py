#!/usr/bin/env python3
"""Render packed context into a short model-readable handoff."""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PACK = ROOT / "skills" / "compressoor" / "scripts" / "pack_ccm.py"
UNPACK = ROOT / "skills" / "compressoor" / "scripts" / "unpack_ccm.py"
KEEP_KEYS = {"G", "C", "D", "F", "T", "R", "N", "Q"}
LABELS = {
    "G": "Goal",
    "C": "Constraint",
    "D": "Decision",
    "F": "Fact",
    "T": "Test",
    "R": "Risk",
    "N": "Next",
    "Q": "Question",
}
SHORT_LABELS = {
    "G": "G",
    "C": "C",
    "D": "D",
    "F": "F",
    "T": "T",
    "R": "R",
    "N": "N",
    "Q": "Q",
}
MIN_LABEL_LIMITS = {
    "Goal": 1,
    "Constraint": 2,
    "Decision": 2,
    "Fact": 2,
    "Test": 2,
    "Risk": 2,
    "Next": 1,
    "Question": 1,
}


def load_unpack_module():
    spec = importlib.util.spec_from_file_location("compressoor_unpack", UNPACK)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pack_text(text: str, domain: str, source_id: str) -> str:
    import subprocess

    proc = subprocess.run(
        ["python3", str(PACK), "--level", "auto", "--domain", domain, "--source-id", source_id],
        input=text,
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def normalize_sections(packed: str):
    unpack = load_unpack_module()
    header, sections = unpack.parse_sections(packed)
    sections = unpack.expand_templates(sections)
    sections = unpack.expand_dynamic_abbrevs(sections)
    sections = unpack.expand_static_abbrevs(sections)
    sections = unpack.expand_phrases(sections)
    return header, sections


def line_from_part(label: str, part: str) -> str | None:
    text = part.strip().rstrip(".")
    if not text:
        return None
    return f"{label}: {text}"


def score_label(label: str, followup_text: str) -> int:
    low = followup_text.lower()
    score = 0
    if label == "Constraint" and any(token in low for token in ["plan", "checklist", "constraint", "preserve", "without", "unchanged"]):
        score += 5
    if label == "Decision" and any(token in low for token in ["explain", "why", "cause", "shorter", "plan"]):
        score += 5
    if label == "Fact" and any(token in low for token in ["review", "finding", "file", "implementation", "status"]):
        score += 5
    if label == "Test" and any(token in low for token in ["test", "coverage", "checklist", "regression", "smoke"]):
        score += 6
    if label == "Risk" and any(token in low for token in ["risk", "callout", "rollout", "review"]):
        score += 6
    if label == "Next" and any(token in low for token in ["next", "plan", "rollout"]):
        score += 4
    if label == "Goal" and any(token in low for token in ["explain", "plan", "implement"]):
        score += 2
    return score


def render_live_context_min(packed: str, followup_text: str = "", bullet_limit: int = 4) -> str:
    _, sections = normalize_sections(packed)
    candidates: list[tuple[int, str, str]] = []
    counts: dict[str, int] = {}
    order = 0
    for key, parts in sections:
        if key not in KEEP_KEYS:
            continue
        label = LABELS[key]
        short_label = SHORT_LABELS[key]
        for part in parts:
            line = line_from_part(short_label, part)
            if line is None:
                continue
            score = score_label(label, followup_text)
            # Prefer durable operational details over generic goals in min mode.
            if label in {"Constraint", "Decision", "Fact", "Test", "Risk"}:
                score += 2
            candidates.append((score, str(order), line))
            order += 1
    candidates.sort(key=lambda item: (-item[0], item[1]))

    lines: list[str] = []
    for _, _, line in candidates:
        label = line.split(": ", 1)[0]
        if counts.get(label, 0) >= MIN_LABEL_LIMITS.get(label, 1):
            continue
        if line in lines:
            continue
        counts[label] = counts.get(label, 0) + 1
        lines.append(line)
        if len(lines) >= bullet_limit:
            break
    if not lines:
        return "CTX: none\n"
    return "CTX:\n" + "\n".join(lines) + "\n"


def render_live_context(packed: str, bullet_limit: int = 6) -> str:
    _, sections = normalize_sections(packed)
    lines: list[str] = []
    for key, parts in sections:
        if key not in KEEP_KEYS:
            continue
        label = SHORT_LABELS[key]
        for part in parts:
            line = line_from_part(label, part)
            if line is None:
                continue
            lines.append(line)
            if len(lines) >= bullet_limit:
                break
        if len(lines) >= bullet_limit:
            break
    if not lines:
        return "CTX: none\n"
    return "CTX:\n" + "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Render packed context into a short readable handoff.")
    parser.add_argument("path", nargs="?", help="Packed context file. Reads stdin if omitted.")
    parser.add_argument("--domain", default="general")
    parser.add_argument("--source-id", default="note")
    parser.add_argument("--from-source", action="store_true", help="Pack the input first before rendering.")
    parser.add_argument("--bullet-limit", type=int, default=6)
    parser.add_argument("--mode", choices=["full", "min"], default="full")
    parser.add_argument("--followup-text", default="")
    args = parser.parse_args()

    if args.path:
        text = Path(args.path).read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()
    packed = pack_text(text, args.domain, args.source_id) if args.from_source else text.strip()
    if args.mode == "min":
        sys.stdout.write(render_live_context_min(packed, followup_text=args.followup_text, bullet_limit=args.bullet_limit))
    else:
        sys.stdout.write(render_live_context(packed, bullet_limit=args.bullet_limit))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
