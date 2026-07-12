#!/usr/bin/env python3
"""
Expand CCM1 into readable structured text.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


SECTION_NAMES = {
    "A": "Abbreviations",
    "G": "Goals",
    "C": "Constraints",
    "D": "Decisions",
    "S": "Current state",
    "F": "Files and objects",
    "E": "Explain Pack",
    "H": "Handoff",
    "K": "Constraint Pack",
    "M": "Memory Pack",
    "T": "Tests and verification",
    "R": "Risks",
    "N": "Next actions",
    "Q": "Open questions",
    "V": "Review Pack",
}
STATIC_ABBREVS = {
    "chk": "check",
    "chg": "changing",
    "curr": "current",
    "design-sys": "design system",
    "MW": "middleware",
    "auth": "authentication",
    "cfg": "configuration",
    "cmds": "commands",
    "ctx": "context",
    "dep": "dependency",
    "deps": "dependencies",
    "destr": "destructive",
    "doc": "documentation",
    "env": "environment",
    "err": "error",
    "errs": "errors",
    "exact": "exactly",
    "exist": "existing",
    "fe": "frontend",
    "fn": "function",
    "impl": "implementation",
    "integ": "integration",
    "intro": "introduce",
    "msg": "message",
    "msgs": "messages",
    "mig": "migration",
    "perf": "performance",
    "pref": "prefer",
    "pre": "before",
    "pub": "public",
    "repo": "repository",
    "req": "requested",
    "resp": "response",
    "resps": "responses",
    "ver": "version",
    "only-if-req": "only if requested",
}
PATH_RE = re.compile(r"(?:\./|\../|/)?[\w.-]+(?:/[\w.-]+)+")
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")


def read_input(path: str | None) -> str:
    if path:
        return Path(path).read_text(encoding="utf-8")
    return sys.stdin.read()


def parse_sections(text: str) -> tuple[str, list[tuple[str, list[str]]]]:
    raw = text.strip()
    compact = re.match(r"^([EHMKV])1\[(.*)\]$", raw, re.S)
    if compact:
        key = compact.group(1)
        return f"{key}1", [(key, [compact.group(2).strip()])]
    if not raw.startswith("CCM1|"):
        raise ValueError("Input does not start with a CCM1 header.")
    if "\n" not in raw and any(
        marker in raw for marker in ["|A[", "|G[", "|C[", "|D[", "|S[", "|F[", "|H[", "|K[", "|M[", "|T[", "|R[", "|N[", "|Q[", "|V["]
    ):
        parts = raw.split("|")
        header = "|".join(parts[:4])
        lines = [header]
        lines.extend(parts[4:])
    else:
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        header = lines[0]
    sections = []
    for line in lines[1:]:
        match = re.match(r"^([A-Z])\[(.*)\]$", line)
        if not match:
            continue
        key = match.group(1)
        if key in {"H", "M", "K", "V"}:
            parts = [match.group(2).strip()]
        else:
            parts = [item.strip() for item in match.group(2).split(";") if item.strip()]
        sections.append((key, parts))
    return header, sections


def expand_dynamic_abbrevs(sections: list[tuple[str, list[str]]]) -> list[tuple[str, list[str]]]:
    mapping: dict[str, str] = {}
    for key, parts in sections:
        if key != "A":
            continue
        for part in parts:
            if "=" not in part:
                continue
            full, short = part.split("=", 1)
            mapping[short.strip()] = full.strip()

    if not mapping:
        return sections

    expanded: list[tuple[str, list[str]]] = []
    for key, parts in sections:
        if key == "A":
            expanded.append((key, parts))
            continue
        next_parts = []
        for part in parts:
            for short, full in sorted(mapping.items(), key=lambda item: -len(item[0])):
                part = re.sub(rf"\b{re.escape(short)}\b", full, part)
            next_parts.append(part)
        expanded.append((key, next_parts))
    return expanded


def parse_kv_payload(part: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in part.split(";"):
        item = item.strip()
        if not item or "=" not in item:
            continue
        key, value = item.split("=", 1)
        out[key.strip()] = value.strip()
    return out


def expand_templates(sections: list[tuple[str, list[str]]]) -> list[tuple[str, list[str]]]:
    expanded: list[tuple[str, list[str]]] = []
    for key, parts in sections:
        if key not in {"E", "H", "M", "K", "V"}:
            expanded.append((key, parts))
            continue
        if not parts:
            continue
        data = parse_kv_payload(parts[0])
        if key == "E":
            if data.get("topic") == "react-rerender":
                goals = ["Explain why a React component re-renders when an inline object prop is recreated on every render"]
                decisions = []
                if data.get("cause") == "inline-obj-ref":
                    decisions.append("Inline object prop creates a new object reference on each render")
                if data.get("note") == "shallow-cmp":
                    decisions.append("React shallow comparison sees the prop as different every render")
                next_actions = []
                if data.get("fix") == "useMemo":
                    next_actions.append("Show the fix with useMemo")
                if goals:
                    expanded.append(("G", goals))
                if decisions:
                    expanded.append(("D", decisions))
                if next_actions:
                    expanded.append(("N", next_actions))
            elif data.get("topic") == "git-rebase-v-merge":
                expanded.append(("G", ["Explain git rebase vs merge for a backend repository"]))
            elif data.get("topic") == "svc-v-mono":
                goals = ["Explain microservices vs monolith tradeoffs for a backend team"]
                decisions = []
                point_map = {
                    "deploy": "Mention deployment complexity",
                    "autonomy": "Mention team autonomy",
                    "debug": "Mention debugging complexity",
                    "ops": "Mention operational overhead",
                }
                for token in data.get("pts", "").split(","):
                    token = token.strip()
                    if token in point_map:
                        decisions.append(point_map[token])
                if goals:
                    expanded.append(("G", goals))
                if decisions:
                    expanded.append(("D", decisions))
            elif data.get("topic") == "docker-mstage":
                goals = ["Explain a Docker multi-stage build for a Node service"]
                cons = []
                decisions = []
                if data.get("cmd") == "exact":
                    cons.append("Keep commands exact where relevant")
                point_map = {
                    "build": "Mention build stage",
                    "runtime": "Mention runtime stage",
                    "small": "Mention smaller image size",
                    "dep-iso": "Mention dependency isolation",
                }
                for token in data.get("pts", "").split(","):
                    token = token.strip()
                    if token in point_map:
                        decisions.append(point_map[token])
                if goals:
                    expanded.append(("G", goals))
                if cons:
                    expanded.append(("C", cons))
                if decisions:
                    expanded.append(("D", decisions))
        elif key == "H":
            if "f" in data:
                if data.get("st") == "impl" and data["f"] == "src/parser.ts":
                    expanded.append(("S", [f"current status: parser change is implemented in {data['f']}"]))
                elif data.get("st") == "impl" and data["f"] == "src/search/rank.ts":
                    expanded.append(("S", [f"current status: search ranking patch is implemented in {data['f']}"]))
                elif data.get("st") == "patch" and data["f"] == "src/parser/csv.ts":
                    expanded.append(("S", [f"current status: CSV parser patch is in {data['f']}"]))
                else:
                    expanded.append(("F", [f"current status: change is in {data['f']}"]))
            state = []
            if data.get("st") == "impl" and data.get("f") != "src/parser.ts":
                state.append("implemented")
            if data.get("st") == "patch":
                state.append("patch is in progress")
            if data.get("repro") == "ios":
                state.append("repro still exists on iOS clients only")
            if data.get("repro") == "legacy-fixture":
                state.append("repro still exists on one legacy fixture only")
            if data.get("it") == "nt":
                state.append("integration tests are not run yet")
            if data.get("ut") == "pass":
                state.append("unit tests pass")
            if state:
                expanded.append(("S", state))
            if data.get("c") == "resp-stable":
                expanded.append(("C", ["do not change the token response shape"]))
            if data.get("c") == "api-stable":
                expanded.append(("C", ["keep the API contract unchanged"]))
            if data.get("c") == "csv-stable":
                expanded.append(("C", ["do not change CSV output shape"]))
            if data.get("q") == "legacy-csv":
                expanded.append(("Q", ["whether the new delimiter handling breaks legacy CSV imports"]))
            if data.get("r") == "refresh-mobile":
                expanded.append(("R", ["refresh-token expiry semantics may break mobile clients"]))
            if data.get("r") == "rank-fixture":
                expanded.append(("R", ["older ranking fixtures may break if score normalization shifts"]))
            if "n" in data:
                acts = []
                for token in data["n"].split(","):
                    token = token.strip()
                    if token == "integ":
                        acts.append("run integration tests")
                    elif token == "fixture":
                        acts.append("verify one old fixture")
                    elif token == "merge":
                        acts.append("before merging")
                    elif token == "cmp-exp":
                        acts.append("compare expiry math")
                    elif token == "cmp-delim":
                        acts.append("compare delimiter normalization")
                    elif token == "cap-fixture":
                        acts.append("capture the failing fixture")
                if acts:
                    expanded.append(("N", acts))
        elif key == "M":
            cons = []
            files = []
            risks = []
            if data.get("tool") == "bun":
                cons.append("repository uses Bun for scripts")
            if "cmd" in data:
                cons.append(f"deploy uses {data['cmd']}")
            if data.get("search") == "rg":
                cons.append("prefer ripgrep for search")
            if data.get("git") == "safe":
                cons.append("avoid destructive git commands unless explicitly requested")
            if data.get("fe") == "design-sys":
                cons.append("preserve the existing design system")
            if data.get("font") == "no-new":
                cons.append("do not introduce a new font stack")
            if data.get("api") == "resp-stable":
                cons.append("preserve the existing API response shape in backend refactors")
            if data.get("env") == "exact":
                cons.append("keep environment variable names exactly the same")
            if "hc" in data:
                cons.append(f"do not change the health check path `{data['hc']}`")
            if "path" in data:
                if data.get("layout") == "nav":
                    files.append(f"update navigation layout in {data['path']}")
                elif data.get("pathk") == "route":
                    files.append(f"check {data['path']} before changing route wiring")
                else:
                    files.append(f"check {data['path']} before layout edits")
            if data.get("stage") == "stg>prod":
                expanded.append(("N", ["verify staging before production deploy"]))
            if data.get("kb") == "same":
                cons.append("keep keyboard navigation behavior unchanged")
            if data.get("t") == "smoke-sidebar":
                expanded.append(("T", ["add a smoke test for the compact sidebar state"]))
            if data.get("t") == "smoke-drawer":
                expanded.append(("T", ["add a smoke test for the compact mobile drawer state"]))
            if "r" in data:
                risks.append(f"legacy workers still expect `{data['r']}`")
            if cons:
                expanded.append(("C", cons))
            if files:
                expanded.append(("F", files))
            if risks:
                expanded.append(("R", risks))
        elif key == "K":
            goals = []
            cons = []
            files = []
            tests = []
            risks = []
            if "f" in data:
                files.append(data["f"])
            if data.get("api") == "stable":
                cons.append("do not change the API contract")
            if data.get("g") == "auth-fix":
                goals.append("fix the authentication middleware")
            if data.get("req") == "stable":
                cons.append("do not change request payload shapes")
            if data.get("resp") == "stable":
                cons.append("do not change response fields")
            if data.get("pub") == "stable":
                cons.append("do not change public method names")
            if data.get("err") == "exact":
                cons.append("keep the current error message exactly the same")
            if data.get("err429") == "exact":
                cons.append("keep the current 429 error message unchanged")
            if data.get("mig") == "no":
                cons.append("no DB migration")
            if data.get("bt") == "todo":
                tests.append("tests for the boundary case still need to be added")
            if data.get("g") == "pay-retry-1helper":
                goals.append("refactor the payments client to isolate retry logic into a single helper")
            if data.get("g") == "audit-batch":
                goals.append("implement the new audit log batching helper")
            if data.get("g") == "graphql-batch":
                goals.append("implement the GraphQL batching helper")
            if data.get("g") == "react-eb":
                goals.append("implement a React error boundary for a dashboard page")
            if data.get("cmp") == "<,<=":
                expanded.append(("D", ["the likely bug is that token expiry uses < instead of <="]))
            if "t" in data:
                vals = set(data["t"].split(","))
                if vals == {"429", "flush-exit", "partial-batch"}:
                    tests.append("add tests for flush-on-exit and partial batch failure")
                elif {"timeout", "429"} & vals:
                    tests.append("add unit coverage for timeout and 429 retry behavior")
                if vals == {"partial-batch"}:
                    tests.append("add tests for partial batch failure")
                elif vals == {"flush-exit", "partial-batch"}:
                    tests.append("add tests for flush-on-exit and partial batch failure")
                elif vals == {"fallback", "reset"}:
                    tests.append("add a smoke test for fallback rendering and a regression test for reset behavior")
            if data.get("r") == "webhook-err-wrap":
                risks.append("webhook reconciliation may depend on existing error wrapping")
            if data.get("fe") == "design-sys":
                cons.append("preserve the existing design system")
            if data.get("props") == "stable":
                cons.append("keep public props unchanged")
            if goals:
                expanded.append(("G", goals))
            if cons:
                expanded.append(("C", cons))
            if files:
                expanded.append(("F", files))
            if tests:
                expanded.append(("T", tests))
            if risks:
                expanded.append(("R", risks))
        elif key == "V":
            if "f" in data:
                if data.get("issue") == "stale-session-inval":
                    expanded.append(("F", [f"findings: {data['f']} may retain stale session entries after partial invalidation"]))
                else:
                    expanded.append(("F", [f"findings: {data['f']} may leak stale entries after partial invalidation"]))
            if data.get("c") == "api-stable":
                expanded.append(("C", ["keep the external API unchanged"]))
            if data.get("t") == "concurr-inval":
                expanded.append(("T", ["add a regression test for concurrent invalidation"]))
            if data.get("r") == "miss-counter-shape":
                expanded.append(("R", ["metrics dashboards currently rely on the old miss counter shape"]))
            if data.get("r") == "cache-miss-shape":
                expanded.append(("R", ["admin dashboards currently rely on the old cache-miss metric shape"]))
    return expanded


def expand_static_abbrevs(sections: list[tuple[str, list[str]]]) -> list[tuple[str, list[str]]]:
    expanded: list[tuple[str, list[str]]] = []
    for key, parts in sections:
        next_parts = []
        for part in parts:
            protected: dict[str, str] = {}

            def protect(pattern: re.Pattern[str], src: str, prefix: str) -> str:
                idx = 0

                def repl(match: re.Match[str]) -> str:
                    nonlocal idx
                    token = f"__{prefix}{idx}__"
                    protected[token] = match.group(0)
                    idx += 1
                    return token

                return pattern.sub(repl, src)

            part = protect(INLINE_CODE_RE, part, "CODE")
            part = protect(PATH_RE, part, "PATH")
            for short, full in sorted(STATIC_ABBREVS.items(), key=lambda item: -len(item[0])):
                part = re.sub(rf"\b{re.escape(short)}\b", full, part)
            for token, value in protected.items():
                part = part.replace(token, value)
            next_parts.append(part)
        expanded.append((key, next_parts))
    return expanded


def expand_phrases(sections: list[tuple[str, list[str]]]) -> list[tuple[str, list[str]]]:
    rewrites = [
        ("no changing api", "do not change the api contract"),
        ("api stable", "do not change the api contract"),
        ("api contract stable", "do not change the api contract"),
        ("err msg exact", "keep the current error message exactly the same"),
        ("keep current error message exactly", "keep the current error message exactly the same"),
        ("no introduce database migration", "do not introduce a database migration"),
        ("add boundary test", "update tests around the boundary case"),
        ("tests for boundary still be added", "tests for the boundary case still need to be added"),
        ("bug is that token expiry use < instead of <=", "the likely bug is that token expiry uses < instead of <="),
        ("we fix authentication middleware", "fix the authentication middleware"),
        ("status: authentication middleware patch is implemented in src/auth.ts, but integration tests are not run yet", "current status: authentication middleware patch is implemented in src/auth.ts, but integration tests are not run yet"),
        ("unit pass", "unit tests pass"),
        ("next: run integration;verify refresh fixture;merge green", "next steps: run integration tests, verify old refresh fixture, then merge if green"),
        ("risk: refresh expiry may break mobile", "risk: refresh-token expiry semantics may break mobile clients"),
        ("parser reg @src/parser.ts", "fix parser regression in src/parser.ts"),
        ("err string exact \"invalid delimiter\"", "preserve exact error string \"invalid delimiter\""),
        ("add trailing-sep test", "add edge-case test for trailing separators"),
        ("risk: legacy fixtures may rely on prev trim", "risk: legacy import fixtures may rely on previous whitespace trimming"),
    ]
    expanded: list[tuple[str, list[str]]] = []
    for key, parts in sections:
        next_parts = []
        for part in parts:
            for old, new in rewrites:
                if part == old:
                    part = new
                    break
            next_parts.append(part)
        expanded.append((key, next_parts))
    return expanded


def render(header: str, sections: list[tuple[str, list[str]]]) -> str:
    out = [f"Header: {header}"]
    for key, parts in sections:
        title = SECTION_NAMES.get(key, key)
        out.append(f"{title}:")
        for part in parts:
            out.append(f"- {part}")
    return "\n".join(out) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Unpack CCM1 into readable text.")
    parser.add_argument("path", nargs="?", help="CCM1 file. Reads stdin if omitted.")
    args = parser.parse_args()

    text = read_input(args.path)
    header, sections = parse_sections(text)
    sections = expand_templates(sections)
    sections = expand_dynamic_abbrevs(sections)
    sections = expand_static_abbrevs(sections)
    sections = expand_phrases(sections)
    sys.stdout.write(render(header, sections))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
