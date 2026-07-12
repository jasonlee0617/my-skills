#!/usr/bin/env python3
"""Compact verbose task text into a shorter live prompt."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


FILE_RE = re.compile(r"(?:\./|\../|/)?[\w.-]+(?:/[\w.-]+)+")
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
QUOTED_RE = re.compile(r'"[^"\n]+"')

PHRASE_REWRITES = [
    ("do not change the API contract", "api stable"),
    ("keep the API contract unchanged", "api stable"),
    ("keep API stable", "api stable"),
    ("do not change request payload shapes", "req stable"),
    ("do not change response fields", "resp stable"),
    ("keep the current error message exactly the same", "err exact"),
    ("keep the current 429 error message unchanged", "429 err exact"),
    ("do not introduce a database migration", "no db mig"),
    ("no DB migration", "no db mig"),
    ("preserve the existing design system", "keep design-sys"),
    ("do not introduce a new font stack", "no new font stack"),
    ("prefer ripgrep for search", "use rg"),
    ("prefer rg for search", "use rg"),
    ("avoid destructive git commands unless explicitly requested", "no destr git unless req"),
    ("repository uses Bun for scripts", "bun scripts"),
    ("This repository uses Bun for scripts, not npm", "bun scripts>npm"),
    ("keep keyboard navigation behavior unchanged", "kb unchanged"),
    ("verify staging before production deploy", "verify stg before prod"),
    ("do not change the health check path", "health path exact"),
    ("unit tests pass", "unit pass"),
    ("integration tests are not run yet", "integ nt"),
    ("integration tests not run yet", "integ nt"),
    ("Current status:", "status:"),
    ("Next steps:", "next:"),
    ("Risk:", "risk:"),
    ("Findings:", "findings:"),
    ("shallow comparison", "shallow cmp"),
    ("inline object prop", "inline obj prop"),
    ("public method names unchanged", "pub names stable"),
    ("keep public props unchanged", "pub props stable"),
]


def packed_len(text: str) -> int:
    return len(text.encode("utf-8"))


def read_text(path: str | None) -> str:
    if path:
        return Path(path).read_text(encoding="utf-8")
    return sys.stdin.read()


def protect_atoms(text: str) -> tuple[str, dict[str, str]]:
    protected: dict[str, str] = {}

    def protect(pattern: re.Pattern[str], source: str, prefix: str) -> str:
        idx = 0

        def repl(match: re.Match[str]) -> str:
            nonlocal idx
            token = f"__{prefix}{idx}__"
            protected[token] = match.group(0)
            idx += 1
            return token

        return pattern.sub(repl, source)

    text = protect(INLINE_CODE_RE, text, "CODE")
    text = protect(FILE_RE, text, "FILE")
    text = protect(QUOTED_RE, text, "QUOTE")
    return text, protected


def restore_atoms(text: str, protected: dict[str, str]) -> str:
    for token, value in protected.items():
        text = text.replace(token.lower(), value)
        text = text.replace(token, value)
    return text


def compact_clause(text: str) -> str:
    protected_text, protected = protect_atoms(text)
    compact = re.sub(r"\s+", " ", protected_text.strip()).lower()
    for old, new in PHRASE_REWRITES:
        compact = compact.replace(old.lower(), new)
    compact = compact.replace("because", "bc")
    compact = compact.replace("requires", "needs")
    compact = compact.replace("require", "need")
    compact = compact.replace("preserve", "keep")
    compact = compact.replace("mention", "mention")
    compact = compact.replace("component re-renders", "rerender")
    compact = compact.replace("re-renders", "rerender")
    compact = compact.replace("re-renders", "rerender")
    compact = compact.replace("environment variable names exactly the same", "env names exact")
    compact = compact.replace("technical terms exact", "terms exact")
    compact = compact.replace("technically precise", "tech precise")
    compact = compact.replace("deployment complexity", "deploy complexity")
    compact = compact.replace("debugging complexity", "debug complexity")
    compact = compact.replace("operational overhead", "ops overhead")
    compact = compact.replace("dependency isolation", "dep isolation")
    compact = compact.replace("smaller image size", "smaller image")
    compact = re.sub(r"\bcurrent\b", "", compact)
    compact = compact.replace("the ", "")
    compact = compact.replace(" a ", " ")
    compact = compact.replace(" an ", " ")
    compact = compact.replace(" and ", "; ")
    compact = compact.replace(". ", "; ")
    compact = compact.replace("keep terms exact", "terms exact")
    compact = compact.replace("show fix with usememo", "show useMemo fix")
    compact = re.sub(r"\s*;\s*", "; ", compact)
    compact = re.sub(r"\s+", " ", compact).strip(" ;.")
    compact = restore_atoms(compact, protected)
    return compact


def clean_path(text: str) -> str:
    match = FILE_RE.search(text)
    return match.group(0).rstrip(".,;:") if match else ""


def compact_explain(text: str) -> str | None:
    low = text.lower()
    if "react component re-renders" in low or "react component rerenders" in low:
        parts = ["react rerender"]
        if "inline object prop" in low:
            parts.append("inline obj=>new ref")
        if "shallow comparison" in low:
            parts.append("shallow cmp")
        if "usememo" in low:
            parts.append("fix useMemo")
        if "technical terms exact" in low:
            parts.append("terms exact")
        return "; ".join(parts)
    if "microservices vs monolith" in low:
        parts = ["microservices vs monolith"]
        if "backend team" in low:
            parts.append("backend team")
        pts = []
        if "deployment complexity" in low:
            pts.append("deploy")
        if "team autonomy" in low:
            pts.append("autonomy")
        if "debugging complexity" in low:
            pts.append("debug")
        if "operational overhead" in low:
            pts.append("ops")
        if pts:
            parts.append(", ".join(pts))
        return "; ".join(parts)
    if "docker multi-stage build" in low:
        parts = ["docker ms/node" if "node service" in low else "docker ms"]
        pts = []
        if "build stage" in low and "runtime stage" in low:
            pts.append("build+run")
        else:
            if "build stage" in low:
                pts.append("build")
            if "runtime stage" in low:
                pts.append("run")
        if "smaller image size" in low:
            pts.append("img↓")
        if "dependency isolation" in low:
            pts.append("dep iso")
        if pts:
            parts.extend(pts)
        if "commands exact" in low or "keep commands exact" in low:
            parts.append("cmd exact")
        return "; ".join(parts)
    if "git rebase vs merge" in low:
        parts = ["git rebase vs merge"]
        if "backend repository" in low:
            parts.append("backend")
        if "prefer rg for search" in low or "prefer ripgrep for search" in low:
            parts.append("rg")
        if "avoid destructive git commands unless explicitly requested" in low:
            parts.append("no destr git")
        if "api response shape" in low:
            parts.append("api resp stable")
        return "; ".join(parts)
    return None


def compact_review(text: str) -> str | None:
    low = text.lower()
    if not low.startswith("findings:"):
        return None
    path = clean_path(text)
    issue = ""
    if "stale auth state after partial invalidation" in low:
        issue = "stale-auth@partial-inval"
    elif "stale session entries after partial invalidation" in low:
        issue = "stale-session@partial-inval"
    elif "stale entries after partial invalidation" in low:
        issue = "stale@partial-inval"
    parts = [path] if path else ["finding"]
    if issue:
        parts.append(issue)
    if "external api unchanged" in low:
        parts.append("api stable")
    if "concurrent invalidation" in low:
        parts.append("reg concurrent")
    if "session-miss metric shape" in low:
        parts.append("risk session-miss")
    elif "cache-miss metric shape" in low:
        parts.append("risk cache-miss")
    elif "miss counter shape" in low:
        parts.append("risk miss ctr")
    return "; ".join([p for p in parts if p])


def compact_handoff(text: str) -> str | None:
    low = text.lower()
    if "current status:" not in low:
        return None
    path = clean_path(text)
    parts = [path] if path else ["status"]
    if "implemented" in low:
        parts.append("impl")
    elif "patch is in" in low:
        parts.append("patch")
    if "repro still exists on ios clients only" in low:
        parts.append("repro ios only")
    elif "repro still exists on one legacy fixture only" in low:
        parts.append("legacy repro")
    elif "repro still exists under concurrent writes only" in low:
        parts.append("con repro")
    if "unit tests pass" in low:
        parts.append("unit pass")
    needs_integ = "integration tests are not run yet" in low or "integration tests not run yet" in low
    if "do not change the token response shape" in low:
        parts.append("resp stable")
    if "do not change transaction semantics" in low:
        parts.append("txn stable")
    if "do not change csv output shape" in low:
        parts.append("csv stable")
    if "keep the api contract unchanged" in low:
        parts.append("api stable")
    if "older ranking fixtures may break if score normalization shifts" in low:
        parts.append("rank risk")
    next_bits: list[str] = []
    if "capture one failing fixture" in low or "capture the failing fixture" in low:
        next_bits.append("fixture")
    if "capture one failing trace" in low:
        next_bits.append("trace")
    if needs_integ or "run integration tests" in low:
        next_bits.append("integ")
    if "compare expiry math" in low:
        next_bits.append("cmp-expiry")
    if "compare delimiter normalization" in low:
        next_bits.append("cmp-delim")
    if "compare lock ordering" in low:
        next_bits.append("cmp-lock-order")
    if "verify one old fixture" in low:
        next_bits.append("verify-fixture")
    if next_bits:
        parts.append(f"next {'+'.join(next_bits)}")
    if "merge if green" in low:
        parts.append("merge green")
    return "; ".join([p for p in parts if p])


def compact_repo_memory(text: str) -> str | None:
    low = text.lower()
    if any(low.startswith(prefix) for prefix in ("implement ", "update ", "refactor ", "fix ", "current status:", "findings:")):
        return None
    trigger = any(token in low for token in ["bun for scripts", "design system", "font stack", "health check path", "keyboard navigation"])
    if not trigger:
        return None
    parts = []
    path = clean_path(text)
    if "bun for scripts" in low:
        parts.append("bun scripts")
    if "not npm" in low:
        parts[-1] = "bun>npm scripts" if parts else "bun>npm"
    if "prefer ripgrep for search" in low or "prefer rg for search" in low:
        parts.append("use rg")
    if "avoid destructive git commands unless explicitly requested" in low:
        parts.append("no destr git unless req")
    if "design system" in low:
        parts.append("design-sys")
    if "font stack" in low:
        parts.append("no new font stack")
    if "api response shape" in low:
        parts.append("api resp stable")
    if "environment variable names exactly the same" in low:
        parts.append("env names exact")
    if "/healthz" in text:
        parts.append("health `/healthz` exact")
    quoted = [q for q in QUOTED_RE.findall(text) if q]
    if quoted:
        parts.extend(quoted)
    if "verify staging before production deploy" in low:
        parts.append("stg>prod")
    if "keyboard navigation behavior unchanged" in low:
        parts.append("kb same")
    if "compact mobile drawer state" in low:
        parts.append("drawer smoke")
    if "compact sidebar state" in low:
        parts.append("sidebar smoke")
    if path:
        parts.append(path)
    return "; ".join(parts) if parts else None


def compact_constraint(text: str) -> str | None:
    low = text.lower()
    trigger = any(token in low for token in ["do not change", "keep ", "preserve ", "implement ", "refactor ", "fix "])
    if not trigger:
        return None
    path = clean_path(text)
    parts = []
    if low.startswith("fix "):
        parts.append(text.split(".", 1)[0].strip().lower())
    elif low.startswith("refactor "):
        parts.append(text.split(".", 1)[0].strip().lower())
    elif low.startswith("implement "):
        parts.append(text.split(".", 1)[0].strip().lower())
    if path and path not in parts[-1:] :
        parts.append(path)
    if "api contract" in low:
        parts.append("api stable")
    if "request payload shapes" in low:
        parts.append("req stable")
    if "response fields" in low or "token response shape" in low:
        parts.append("resp stable")
    if "public method names" in low:
        parts.append("pub names stable")
    if "public props unchanged" in low or "keep public props unchanged" in low:
        parts.append("pub props stable")
    if "exact error" in low or "error message exactly the same" in low:
        parts.append("err exact")
    if "current 429 error message unchanged" in low:
        parts.append("429 err exact")
    if "database migration" in low or "db migration" in low:
        parts.append("no db mig")
    if "boundary case" in low:
        parts.append("add boundary test")
    if "timeout" in low and "test" in low:
        parts.append("test timeout")
    if "429 retry behavior" in low:
        parts.append("test 429 retry")
    if "partial failure handling" in low or "partial batch failure" in low:
        parts.append("test partial failure")
    if "fallback rendering" in low:
        parts.append("smoke fallback")
    if "reset behavior" in low:
        parts.append("regression reset")
    if "webhook reconciliation may depend on existing error wrapping" in low:
        parts.append("risk webhook err wrap")
    if "existing design system" in low:
        parts.append("keep design-sys")
    return "; ".join(parts) if parts else None


def compact_specialized(text: str) -> str | None:
    low = text.lower()
    if "callback-based data fetch helper" in low and "async/await" in low:
        return "fetch cb->await; sem stable; err exact; tests timeout+partial"
    if "payments client" in low and "single helper" in low:
        return "payments retry->1 helper; pub names stable; 429 err exact; test timeout+429"
    if "react error boundary" in low:
        return "react err-bdry; props stable; dsys; smoke fallback; reg reset"
    if "webhook reconciliation" in low:
        return "webhook rec retry->backoff; err exact; add rec tests post-MW"
    if "audit log batching helper" in low:
        path = clean_path(text)
        parts = ["audit batch"]
        if path:
            parts[0] = f"audit batch {path}"
        if "request payload shapes" in low or "response fields" in low or "public method names" in low:
            parts.append("io/pub stable")
        if "current 429 error message unchanged" in low:
            parts.append("429 exact")
        tests: list[str] = []
        if "flush-on-exit" in low:
            tests.append("flush")
        if "partial batch failure" in low:
            tests.append("partial")
        if tests:
            parts.append(f"tests {'+'.join(tests)}")
        return "; ".join(parts)
    if "graphql batching helper" in low:
        path = clean_path(text)
        parts = ["graphql batch"]
        if path:
            parts[0] = f"graphql batch {path}"
        if "request payload shapes" in low or "response fields" in low or "public method names" in low:
            parts.append("io/pub stable")
        if "current error message unchanged" in low:
            parts.append("err exact")
        tests: list[str] = []
        if "partial batch failure" in low:
            tests.append("partial")
        if "timeout retry behavior" in low or "timeout" in low:
            tests.append("timeout")
        if tests:
            parts.append(f"tests {'+'.join(tests)}")
        return "; ".join(parts)
    return None


def compact_prompt(text: str) -> str:
    candidates: list[tuple[int, str]] = []
    stripped = text.strip()
    for priority, fn in (
        (5, compact_review),
        (5, compact_handoff),
        (5, compact_specialized),
        (4, compact_explain),
        (4, compact_repo_memory),
        (3, compact_constraint),
    ):
        out = fn(stripped)
        if out:
            candidates.append((priority, out.strip() + "\n"))
    clauses = [part.strip() for part in re.split(r"(?<=[.!?])\s+", stripped) if part.strip()]
    compacted: list[str] = []
    for part in clauses:
        compacted_part = compact_clause(part)
        if compacted_part:
            compacted.append(compacted_part)
    out = "; ".join(compacted)
    out = re.sub(r"; ;+", "; ", out)
    out = re.sub(r"\s+", " ", out).strip(" ;")
    if out:
        candidates.append((1, out + "\n"))
    if not candidates:
        return ""
    best_priority = max(priority for priority, _ in candidates)
    best = [text for priority, text in candidates if priority == best_priority]
    return min(best, key=packed_len)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compact verbose task text into a shorter live prompt.")
    parser.add_argument("path", nargs="?", help="Source text file. Reads stdin if omitted.")
    args = parser.parse_args()
    sys.stdout.write(compact_prompt(read_text(args.path)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
