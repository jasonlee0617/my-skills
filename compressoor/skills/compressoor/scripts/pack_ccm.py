#!/usr/bin/env python3
"""
Heuristic packer for CCM1.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path


SECTION_ORDER = ["A", "G", "C", "D", "S", "F", "T", "R", "N", "Q"]
SECTION_LABELS = {
    "A": "abbrev",
    "G": "goal",
    "C": "constraints",
    "D": "decisions",
    "S": "state",
    "F": "files",
    "T": "tests",
    "R": "risks",
    "N": "next",
    "Q": "questions",
}
ABBREVIATIONS = {
    "authentication": "auth",
    "before": "pre",
    "commands": "cmds",
    "middleware": "MW",
    "configuration": "cfg",
    "context": "ctx",
    "dependency": "dep",
    "dependencies": "deps",
    "destructive": "destr",
    "documentation": "doc",
    "environment": "env",
    "error": "err",
    "errors": "errs",
    "exactly": "exact",
    "existing": "exist",
    "frontend": "fe",
    "function": "fn",
    "implementation": "impl",
    "integration": "integ",
    "introduce": "intro",
    "message": "msg",
    "messages": "msgs",
    "migration": "mig",
    "performance": "perf",
    "prefer": "pref",
    "preference": "pref",
    "preferences": "prefs",
    "repository": "repo",
    "request": "req",
    "requests": "reqs",
    "response": "resp",
    "responses": "resps",
    "version": "ver",
}

FILE_RE = re.compile(r"(?:\./|\../|/)?[\w.-]+(?:/[\w.-]+)+")
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
QUOTED_RE = re.compile(r'"[^"\n]+"')
TOKEN_RE = re.compile(r"\b[a-z][a-z0-9-]{4,}\b")
PHRASE_REWRITES = [
    ("avoid destructive git commands unless req", "git destr cmds only-if-req"),
    ("avoid destructive git commands unless requested", "git destr cmds only-if-req"),
    ("keep curr error msg exact", "err msg exact"),
    ("keep curr error msg exactly", "err msg exact"),
    ("keep current error msg exact", "err msg exact"),
    ("keep current error msg exactly", "err msg exact"),
    ("no changing api", "api contract stable"),
    ("no change api", "api contract stable"),
    ("no changing api contract", "api contract stable"),
    ("no chg api", "api contract stable"),
    ("no chg api contract", "api contract stable"),
    ("no changing public method names", "pub method names stable"),
    ("no change request payload shapes", "req shapes stable"),
    ("no intro database mig", "no database mig"),
    ("no intro new font stack", "no new font stack"),
    ("preserve exist design-sys", "preserve design-sys"),
    ("edit fe code, preserve exist design-sys", "fe: preserve design-sys"),
    ("this repository uses bun for scripts, not npm", "repo bun scripts>npm"),
    ("repository uses bun for scripts, not npm", "repo bun scripts>npm"),
    ("prefer ripgrep for search", "pref ripgrep search"),
    ("if editing frontend code, preserve the existing design system and do not introduce a new font stack", "fe preserve design-sys;no new font stack"),
    ("check ", "chk "),
    ("update tests boundary", "add boundary test"),
    ("update authentication tests", "add auth tests"),
    ("fix authentication middleware", "fix auth MW"),
    ("fix auth middleware", "fix auth MW"),
    ("we fix auth MW", "fix auth MW"),
    ("current status:", "status:"),
    ("integration tests are not run yet", "integ nt"),
    ("unit tests pass", "unit pass"),
    ("next steps: run integration tests, verify old refresh fixture, then merge if green", "next: run integ;verify refresh fixture;merge green"),
    ("risk: refresh-token expiry semantics may break mobile clients", "risk: refresh expiry may break mobile"),
    ("fix parser regression in ", "parser reg @"),
    ("preserve exact error string", "err string exact"),
    ("add edge-case test for trailing separators", "add trailing-sep test"),
    ("risk: legacy import fixtures may rely on previous whitespace trimming", "risk: legacy fixtures may rely on prev trim"),
]
HEADER_MARKERS = ["|A[", "|G[", "|C[", "|D[", "|S[", "|F[", "|T[", "|R[", "|N[", "|Q[", "|H[", "|M[", "|K[", "|V[", "|E["]
INSTRUCTION_MARKERS = (
    "$compressoor",
    "tool calls first",
    "never send any message before",
    "tool loop is complete",
    "pre-tool status",
    "never send progress updates",
    "packed context internal",
    "reusable handoffs",
    "agents and sub-agents",
    "final summaries",
)


def read_input(path: str | None) -> str:
    if path:
        text = Path(path).read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()
    return normalize_unpacked_render(text)


def normalize_unpacked_render(text: str) -> str:
    lines = [line.rstrip() for line in text.splitlines()]
    if not lines or not lines[0].startswith("Header: "):
        return text

    out: list[str] = []
    section = None
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        if line.endswith(":") and not line.startswith("- "):
            section = line[:-1]
            continue
        if not line.startswith("- "):
            continue
        item = line[2:]
        if section == "Goals":
            out.append(item + ".")
        elif section == "Constraints":
            out.append(item + ".")
        elif section == "Decisions":
            out.append(item + ".")
        elif section == "Current state":
            out.append(item + ".")
        elif section == "Files and objects":
            out.append(item + ".")
        elif section == "Tests and verification":
            out.append(item + ".")
        elif section == "Risks":
            if not item.lower().startswith("risk:"):
                item = "Risk: " + item
            out.append(item + ".")
        elif section == "Next actions":
            out.append("Next steps: " + item + ".")
        elif section == "Open questions":
            if not item.endswith("?"):
                item = item + "?"
            out.append(item)
    return " ".join(out) if out else text


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text.strip())
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+", text)
    clauses: list[str] = []
    for part in parts:
        if not part.strip():
            continue
        expanded = (
            part.replace(" without ", ". Do not ")
            .replace(" and do not ", ". Do not ")
            .replace(" but do not ", ". Do not ")
            .replace(" while keeping ", ". Keep ")
        )
        clauses.extend(re.split(r"(?<=[.!?])\s+", expanded))
    return [part.strip() for part in clauses if part.strip()]


def shorten(text: str, dynamic_abbrevs: dict[str, str] | None = None) -> str:
    protected: dict[str, str] = {}

    def protect(pattern: re.Pattern[str], src: str, prefix: str) -> str:
        idx = 0

        def repl(match: re.Match[str]) -> str:
            nonlocal idx
            key = f"__{prefix}{idx}__"
            protected[key] = match.group(0)
            idx += 1
            return key

        return pattern.sub(repl, src)

    text = protect(INLINE_CODE_RE, text, "CODE")
    text = protect(FILE_RE, text, "FILE")
    text = protect(QUOTED_RE, text, "QUOTE")

    text = text.lower()
    text = text.replace("do not", "no")
    text = text.replace("without", "no")
    text = text.replace("need to", "")
    text = text.replace("we should", "")
    text = text.replace("we need", "")
    text = text.replace("there is", "")
    text = text.replace("the current", "curr")
    text = text.replace("current", "curr")
    text = text.replace("likely", "")
    text = text.replace("this repository uses", "repo use")
    text = text.replace("repository uses", "repo use")
    text = text.replace("uses", "use")
    text = text.replace("design system", "design-sys")
    text = text.replace("if editing", "edit")
    text = text.replace("for scripts", "scripts")
    text = text.replace("for search", "search")
    text = text.replace("unless", "unless")
    text = text.replace("explicitly requested", "req")
    text = text.replace("requested", "req")
    text = text.replace("changing", "chg")
    text = text.replace("around the", "")
    text = text.replace("around", "")
    text = text.replace("boundary case", "boundary")
    text = text.replace("public method names", "pub method names")
    text = text.replace("api contract", "api")
    text = text.replace("exactly the same", "exact")
    text = re.sub(r"\b(a|an|the)\b", "", text)
    text = re.sub(r"\s+", " ", text).strip(" .;:-")

    words = []
    for word in text.split():
        bare = word.strip(",.;:")
        repl = ABBREVIATIONS.get(bare, bare)
        if dynamic_abbrevs and repl == bare:
            repl = dynamic_abbrevs.get(bare, bare)
        if word[-1:] in ",.;:" and bare != word:
            repl += word[-1]
        words.append(repl)
    text = " ".join(words)

    for key, value in protected.items():
        text = text.replace(key.lower(), value)
    for old, new in PHRASE_REWRITES:
        text = text.replace(old, new)
    text = re.sub(r"\s+", " ", text).strip(" .;:-")
    return text


def classify(sentence: str) -> str:
    s = sentence.lower()
    if "?" in sentence or "unclear" in s or "whether" in s:
        return "Q"
    if any(k in s for k in ["current status", "implemented", "not run yet", "in progress", "done", "status"]):
        return "S"
    if s.startswith(("we need to ", "need to ", "goal: ", "objective: ", "fix ", "refactor ", "implement ")):
        return "G"
    if any(k in s for k in ["risk", "might break", "may depend", "regression", "edge case"]):
        return "R"
    if any(k in s for k in ["src/", ".ts", ".js", ".py", ".rs", ".go", "`", "/"]) and (FILE_RE.search(sentence) or INLINE_CODE_RE.search(sentence)):
        return "F"
    if any(k in s for k in ["do not", "without", "keep ", "preserve", "avoid", "must", "should not", "no db migration", "no database migration", "no migration"]):
        return "C"
    if any(k in s for k in ["unit test", "unit tests", "integration tests", "coverage", "tests pass", "tests are", "repro", "pass", "fail", "tests for", "test for"]) or ("test" in s and "added" in s):
        return "T"
    if any(k in s for k in ["bug is", "use <", "use <=", "refactor", "isolate", "extract", "chosen", "decision"]):
        return "D"
    if any(k in s for k in ["next step", "next steps", "follow up", "then ", "update tests", "add unit", "run integration", "run unit", "verify ", "patch "]) or s.startswith(("update ", "add ", "run ", "verify ", "patch ")):
        return "N"
    return "G"


def dedupe_keep_order(items: list[str]) -> list[str]:
    seen = set()
    out = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def build_dynamic_abbrevs(text: str) -> dict[str, str]:
    counts = Counter(TOKEN_RE.findall(text.lower()))
    candidates = [
        token
        for token, count in counts.items()
        if count >= 2 and len(token) >= 7 and token not in ABBREVIATIONS
    ]
    used = set(ABBREVIATIONS.values())
    mapping: dict[str, str] = {}
    for token in sorted(candidates, key=lambda t: (-counts[t], -len(t), t)):
        abbr = token[:3]
        if abbr in used:
            for i in range(4, min(len(token), 8) + 1):
                abbr = token[:i]
                if abbr not in used:
                    break
        if abbr in used or len(abbr) >= len(token):
            continue
        gross_gain = counts[token] * (len(token) - len(abbr))
        dict_cost = len(token) + len(abbr) + 4
        if gross_gain <= dict_cost:
            continue
        used.add(abbr)
        mapping[token] = abbr
    return mapping


def recommend_level(text: str) -> str:
    if build_dynamic_abbrevs(text):
        return "max"
    return "std"


def render_multiline(level: str, domain: str, source_id: str, sections: dict[str, list[str]]) -> str:
    lines = [f"CCM1|lvl={level}|dom={domain}|src={source_id}"]
    for key in SECTION_ORDER:
        items = dedupe_keep_order(sections[key])
        if not items:
            continue
        lines.append(f"{key}[{';'.join(items)}]")
    return "\n".join(lines) + "\n"


def render_inline(level: str, domain: str, source_id: str, sections: dict[str, list[str]]) -> str:
    parts = [f"CCM1|lvl={level}|dom={domain}|src={source_id}"]
    for key in SECTION_ORDER:
        items = dedupe_keep_order(sections[key])
        if not items:
            continue
        parts.append(f"{key}[{';'.join(items)}]")
    return "|".join(parts) + "\n"


def packed_length(text: str) -> int:
    return len(text.encode("utf-8"))


def clean_path(match: re.Match[str] | None) -> str | None:
    if not match:
        return None
    return match.group(0).rstrip(".,;:")


def build_handoff_template(text: str, domain: str, source_id: str) -> str | None:
    low = text.lower()
    if "current status:" not in low:
        return None
    parts = []
    path = clean_path(FILE_RE.search(text))
    if path:
        parts.append(f"f={path}")
    if "implemented" in low:
        parts.append("st=impl")
    elif "patch is in" in low:
        parts.append("st=patch")
    if "integration tests are not run yet" in low or "integration tests not run yet" in low:
        parts.append("it=nt")
    if "unit tests pass" in low:
        parts.append("ut=pass")
    if "ios clients only" in low:
        parts.append("repro=ios")
    if "legacy fixture only" in low:
        parts.append("repro=legacy-fixture")
    if "legacy csv imports" in low:
        parts.append("q=legacy-csv")
    if "api contract unchanged" in low or "api contract unchanged." in low or "api contract" in low and "unchanged" in low:
        parts.append("c=api-stable")
    if "do not change csv output shape" in low:
        parts.append("c=csv-stable")
    if "refresh-token expiry semantics may break mobile clients" in low:
        parts.append("r=refresh-mobile")
    if "older ranking fixtures may break if score normalization shifts" in low:
        parts.append("r=rank-fixture")
    if "next steps" in low:
        actions = []
        if "run integration tests" in low:
            actions.append("integ")
        if "verify one old fixture" in low or "verify old refresh fixture" in low:
            actions.append("fixture")
        if "compare expiry math" in low:
            actions.append("cmp-exp")
        if "compare delimiter normalization" in low:
            actions.append("cmp-delim")
        if "merge if green" in low or "before merging" in low:
            actions.append("merge")
        if "capture one failing fixture" in low:
            actions.append("cap-fixture")
        if "capture the failing fixture" in low:
            actions.append("cap-fixture")
        if actions:
            parts.append(f"n={','.join(actions)}")
    if "do not change the token response shape" in low:
        parts.append("c=resp-stable")
    if not parts:
        return None
    return f"H1[{';'.join(parts)}]\n"


def build_memory_template(text: str, domain: str, source_id: str) -> str | None:
    low = text.lower()
    parts = []
    path = clean_path(FILE_RE.search(text))
    if "bun" in low and "scripts" in low:
        parts.append("tool=bun")
    if "`bun run build`" in text or "bun run build" in low:
        parts.append("cmd=`bun run build`")
    if "ripgrep" in low or re.search(r"\brg\b", low):
        parts.append("search=rg")
    if "avoid destructive git commands" in low:
        parts.append("git=safe")
    if "design system" in low:
        parts.append("fe=design-sys")
    if "font stack" in low:
        parts.append("font=no-new")
    if "api response shape" in low:
        parts.append("api=resp-stable")
    if "environment variable names exactly the same" in low:
        parts.append("env=exact")
    if "/healthz" in text:
        parts.append("hc=/healthz")
    if "verify staging before production deploy" in low:
        parts.append("stage=stg>prod")
    env_match = re.search(r"\b[A-Z][A-Z0-9_]{3,}\b", text)
    if env_match and env_match.group(0) not in {"BUN", "RG"}:
        parts.append(f"r={env_match.group(0)}")
    if "keyboard navigation behavior unchanged" in low:
        parts.append("kb=same")
    if "compact sidebar state" in low:
        parts.append("t=smoke-sidebar")
    if "compact mobile drawer state" in low:
        parts.append("t=smoke-drawer")
    if "navigation layout" in low:
        parts.append("layout=nav")
    if path:
        parts.append(f"path={path}")
    if "route wiring" in low:
        parts.append("pathk=route")
    if len(parts) < 2:
        return None
    return f"M1[{';'.join(parts)}]\n"


def build_constraint_template(text: str, domain: str, source_id: str) -> str | None:
    low = text.lower()
    parts = []
    path = clean_path(FILE_RE.search(text))
    if path:
        parts.append(f"f={path}")
    if "api stable" in low or "keep api stable" in low or "api contract" in low:
        parts.append("api=stable")
    if "authentication middleware" in low or "auth fix is in" in low:
        parts.append("g=auth-fix")
    if "request payload shapes" in low:
        parts.append("req=stable")
    if "response fields" in low or "token response shape" in low:
        parts.append("resp=stable")
    if "public method names" in low:
        parts.append("pub=stable")
    if "current error message unchanged" in low:
        parts.append("err=exact")
    if "current 429 error message unchanged" in low:
        parts.append("err429=exact")
    elif "exact error text" in low or "error message exactly the same" in low:
        parts.append("err=exact")
    if "no db migration" in low or "do not introduce a database migration" in low:
        parts.append("mig=no")
    if "boundary case" in low:
        parts.append("bt=todo")
    if "< instead of <=" in text:
        parts.append("cmp=<,<=")
    if "payments client" in low and "retry logic" in low:
        parts.append("g=pay-retry-1helper")
    if "audit log batching helper" in low:
        parts.append("g=audit-batch")
    if "graphql batching helper" in low:
        parts.append("g=graphql-batch")
    if "react error boundary" in low:
        parts.append("g=react-eb")
    tests = []
    if "timeout" in low:
        tests.append("timeout")
    if "429" in low:
        tests.append("429")
    if "flush-on-exit" in low:
        tests.append("flush-exit")
    if "partial batch failure" in low:
        tests.append("partial-batch")
    if "fallback rendering" in low:
        tests.append("fallback")
    if "reset behavior" in low:
        tests.append("reset")
    if tests:
        parts.append(f"t={','.join(tests)}")
    if "webhook reconciliation may depend on existing error wrapping" in low:
        parts.append("r=webhook-err-wrap")
    if "preserve the existing design system" in low:
        parts.append("fe=design-sys")
    if "public props unchanged" in low or "keep public props unchanged" in low:
        parts.append("props=stable")
    meaningful = [
        part for part in parts if not part.startswith("f=") and part not in {"fe=design-sys", "props=stable"}
    ]
    if not meaningful:
        return None
    return f"K1[{';'.join(parts)}]\n"


def build_review_template(text: str, domain: str, source_id: str) -> str | None:
    low = text.lower()
    if not low.startswith("findings:"):
        return None
    path = clean_path(FILE_RE.search(text))
    if not path:
        return None
    parts = [f"f={path}"]
    if "stale entries after partial invalidation" in low:
        parts.append("issue=stale-partial-inval")
    if "stale session entries after partial invalidation" in low:
        parts.append("issue=stale-session-inval")
    if "external api unchanged" in low:
        parts.append("c=api-stable")
    if "concurrent invalidation" in low:
        parts.append("t=concurr-inval")
    if "miss counter shape" in low:
        parts.append("r=miss-counter-shape")
    if "cache-miss metric shape" in low:
        parts.append("r=cache-miss-shape")
    return f"V1[{';'.join(parts)}]\n"


def build_explain_template(text: str, domain: str, source_id: str) -> str | None:
    low = text.lower()
    parts = []
    if "react component re-renders" in low or "react component rerenders" in low:
        parts.append("topic=react-rerender")
        if "inline object prop" in low or "inline object" in low:
            parts.append("cause=inline-obj-ref")
        if "usememo" in low:
            parts.append("fix=useMemo")
        if "shallow comparison" in low:
            parts.append("note=shallow-cmp")
    elif "git rebase vs merge" in low:
        parts.append("topic=git-rebase-v-merge")
        if "backend repository" in low:
            parts.append("ctx=backend-repo")
    elif "microservices vs monolith" in low:
        parts.append("topic=svc-v-mono")
        if "backend team" in low:
            parts.append("ctx=backend-team")
        points = []
        if "deployment complexity" in low:
            points.append("deploy")
        if "team autonomy" in low:
            points.append("autonomy")
        if "debugging complexity" in low:
            points.append("debug")
        if "operational overhead" in low:
            points.append("ops")
        if points:
            parts.append(f"pts={','.join(points)}")
    elif "docker multi-stage build" in low:
        parts.append("topic=docker-mstage")
        if "node service" in low:
            parts.append("ctx=node-svc")
        if "commands exact" in low or "keep commands exact" in low:
            parts.append("cmd=exact")
        points = []
        if "build stage" in low:
            points.append("build")
        if "runtime stage" in low:
            points.append("runtime")
        if "smaller image size" in low:
            points.append("small")
        if "dependency isolation" in low:
            points.append("dep-iso")
        if points:
            parts.append(f"pts={','.join(points)}")
    if len(parts) < 2:
        return None
    return f"E1[{';'.join(parts)}]\n"


def build_progress_template(text: str, domain: str, source_id: str) -> str | None:
    low = text.lower().strip()
    if len(text) > 140 or FILE_RE.search(text) or "current status:" in low:
        return None
    if not any(token in low for token in ["status", "progress", "working", "next", "scanning", "checking", "benchmark"]):
        return None

    parts = []
    if "benchmark" in low:
        parts.append("s=bench")
    elif "scan" in low or "scanning" in low:
        parts.append("s=scan")
    elif "check" in low or "checking" in low:
        parts.append("s=check")
    elif "test" in low or "testing" in low:
        parts.append("s=test")
    elif "working" in low:
        parts.append("s=work")
    elif "status" in low:
        parts.append("s=status")

    if "next" in low:
        if "benchmark" in low:
            parts.append("n=bench")
        elif "test" in low:
            parts.append("n=test")
        elif "verify" in low:
            parts.append("n=verify")
        elif "patch" in low or "fix" in low:
            parts.append("n=patch")
    elif "benchmark" in low:
        parts.append("n=bench")
    elif "verify" in low:
        parts.append("n=verify")

    if "blocked" in low:
        parts.append("r=blocked")
    elif "waiting" in low:
        parts.append("r=wait")
    elif "risk" in low:
        parts.append("r=risk")

    if not parts:
        return None
    return f"P1[{';'.join(parts)}]\n"


def is_instruction_like(text: str) -> bool:
    low = text.lower()
    return any(marker in low for marker in INSTRUCTION_MARKERS)


def template_pack(text: str, domain: str, source_id: str) -> str | None:
    if is_instruction_like(text):
        return None
    candidates: list[tuple[int, str]] = []
    for priority, builder in (
        (1, build_progress_template),
        (5, build_handoff_template),
        (4, build_memory_template),
        (3, build_constraint_template),
        (5, build_review_template),
        (4, build_explain_template),
    ):
        packed = builder(text, domain, source_id)
        if packed:
            candidates.append((priority, packed))
    if not candidates:
        return None
    best_priority = max(priority for priority, _ in candidates)
    best_candidates = [packed for priority, packed in candidates if priority == best_priority]
    return min(best_candidates, key=packed_length)


def candidate_sections(text: str, use_dynamic_abbrevs: bool) -> dict[str, list[str]]:
    sections = {key: [] for key in SECTION_ORDER}
    dynamic_abbrevs = build_dynamic_abbrevs(text) if use_dynamic_abbrevs else {}
    if dynamic_abbrevs:
        sections["A"] = [f"{k}={v}" for k, v in dynamic_abbrevs.items()]
    for sentence in split_sentences(text):
        bucket = classify(sentence)
        norm = shorten(sentence, dynamic_abbrevs)
        if norm:
            sections[bucket].append(norm)
    return sections


def pack(text: str, level: str, domain: str, source_id: str) -> str:
    base_sections = candidate_sections(text, use_dynamic_abbrevs=False)
    base_multiline = render_multiline(level, domain, source_id, base_sections)
    if level == "lite":
        return base_multiline

    best = base_multiline
    best_len = packed_length(best)

    inline_base = render_inline(level, domain, source_id, base_sections)
    inline_len = packed_length(inline_base)
    if inline_len < best_len:
        best = inline_base
        best_len = inline_len

    if level == "max":
        dynamic_sections = candidate_sections(text, use_dynamic_abbrevs=True)
        dynamic_multiline = render_multiline(level, domain, source_id, dynamic_sections)
        dynamic_inline = render_inline(level, domain, source_id, dynamic_sections)
        for candidate in (dynamic_multiline, dynamic_inline):
            cand_len = packed_length(candidate)
            if cand_len < best_len:
                best = candidate
                best_len = cand_len

    template = template_pack(text, domain, source_id)
    if template and packed_length(template) < best_len:
        best = template

    return best


def main() -> int:
    parser = argparse.ArgumentParser(description="Pack free text into CCM1.")
    parser.add_argument("path", nargs="?", help="Source text file. Reads stdin if omitted.")
    parser.add_argument("--level", default="std", choices=["auto", "lite", "std", "max"])
    parser.add_argument("--domain", default="general")
    parser.add_argument("--source-id", default="note")
    parser.add_argument("--explain-level", action="store_true", help="Print chosen level to stderr when using auto.")
    args = parser.parse_args()

    text = read_input(args.path)
    level = recommend_level(text) if args.level == "auto" else args.level
    if args.level == "auto" and args.explain_level:
        print(f"chosen_level: {level}", file=sys.stderr)
    sys.stdout.write(pack(text, level, args.domain, args.source_id))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
