# compressoor

Compressoor is a concise runtime policy for Codex and Claude Code.

Its main job is to cut token overhead without making the agent sound unnatural. The style target is tool-first execution with no pre-tool chatter, no mid-loop chatter, no plan/thinking preambles before the first tool call, and short professional output after the loop. It also includes a small set of tools for compressing durable context such as handoffs, review notes, constraint summaries, and benchmark prompts.

[Install](#install) • [Benchmarks](#benchmarks) • [Runtime Behavior](#runtime-behavior) • [Context Tools](#context-tools) • [Main Files](#main-files)

## What it is

- A Codex skill and plugin plus a Claude Code plugin for concise runtime behavior
- A small set of scripts for prompt compaction, rendering short live context, and benchmarking token savings
- Session bootstrap hooks and an optional launcher for Codex

## Style target

- tool-first
- no pre-tool or mid-loop status text
- no initial plans or thinking summaries before the first tool call
- brief and professional
- no acknowledgements or filler
- no step-by-step narration unless it changes the plan
- short final answers with verification, blockers, and risks only when they matter

This is closer to "do the work first, then say less and keep it normal" than to character-role compression. The goal is lower token use without caveman speech.

## Install

### Fast Install From GitHub

If an agent or user only has the GitHub URL, this is the shortest Codex-friendly install path:

```bash
git clone https://github.com/M4cs/compressoor.git
cd compressoor
python3 skills/compressoor/scripts/install_codex_compressoor.py --force
```

If the repo is already cloned somewhere else, run the installer from that checkout.

Suggested prompt for an agent:

```text
Clone https://github.com/M4cs/compressoor if it is not already present, change into that checkout, then run python3 skills/compressoor/scripts/install_codex_compressoor.py --force. After that, confirm that ~/.codex/AGENTS.md, ~/.codex/hooks.json, ~/.agents/plugins/marketplace.json, and ~/plugins/compressoor exist.
```

### Codex Plugin

Install the plugin from [`plugins/compressoor/.codex-plugin/plugin.json`](plugins/compressoor/.codex-plugin/plugin.json).

### Claude Code Plugin

Add this repository as a Claude marketplace, then install `compressoor`:

```bash
claude plugin marketplace add M4cs/compressoor
claude plugin install compressoor@compressoor
```

The Claude plugin ships:

- [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json)
- [`.claude-plugin/plugin.json`](.claude-plugin/plugin.json)
- [`.claude/agents/compressoor.md`](.claude/agents/compressoor.md)
- [`.claude/commands/compressoor.md`](.claude/commands/compressoor.md)

### Standalone runtime policy

```bash
python3 skills/compressoor/scripts/install_codex_compressoor.py --force
```

This writes:

- `~/.codex/AGENTS.md` with compressoor runtime guidance
- `~/.codex/hooks.json` with `SessionStart` and `SessionResume` runtime-policy hooks
- `~/.agents/plugins/marketplace.json` with a home-local `compressoor` marketplace entry
- `~/plugins/compressoor` as a symlink to this repo's plugin directory

The installed hooks inject a mandatory compressoor session directive automatically on session start and resume. That directive is meant to reduce token use by:

- preferring tools before any outward text
- forbidding initial plans, thinking summaries, and intent statements before the first tool call
- suppressing acknowledgements and routine narration before and during tool loops
- suppressing explanations of intent before tool calls
- keeping outward answers short and professional
- using compaction tools only when reusable context actually needs shortening

If you update compressoor rules, rerun the installer so `~/.codex/hooks.json` still points at the current hook scripts:

```bash
python3 skills/compressoor/scripts/install_codex_compressoor.py --force
```

This also makes `compressoor` discoverable outside this repo, because Codex can resolve it from the home-local marketplace at `~/.agents/plugins/marketplace.json`.

If you also want the same note in a project `AGENTS.md`:

```bash
python3 skills/compressoor/scripts/install_codex_compressoor.py --force \
  --project-agents /path/to/repo/AGENTS.md
```

If a target `AGENTS.md` already exists, the installer appends the compressoor directive instead of replacing the file.

## Launch Codex With Compressoor

Use the launcher if you want a Codex session bootstrapped with the compressoor runtime policy:

```bash
python3 skills/compressoor/scripts/launch_codex_compressoor.py -- -C /path/to/repo
```

Useful variants:

```bash
python3 skills/compressoor/scripts/launch_codex_compressoor.py --print-bootstrap
python3 skills/compressoor/scripts/launch_codex_compressoor.py --prompt "Review this repo for regressions." -- -C /path/to/repo
```

If compressoor guidance is already present in repo or global `AGENTS.md`, or active compressoor hooks are already installed, the launcher does not prepend another bootstrap prompt.

## Runtime Behavior

When compressoor is active, the intended behavior is:

- tools first
- no acknowledgements, commentary, or progress updates before or during tool loops
- no initial plans, thinking summaries, or intent statements before the first tool call
- concise status only after the loop, unless blocked
- short final answers after the tool loop
- explain failures, blockers, verification, or changed files when needed

This mode is aimed at keeping token overhead small in long tool-driven sessions while still sounding like a normal competent assistant after the tool loop ends.

## Context Tools

Compressoor also includes explicit-use context tools when you want to:

- pack a handoff
- compress a memory note
- shorten review findings
- compact a constraint summary
- benchmark verbose vs compact prompt text

In practice, the simplest workflow is:

1. Take verbose reusable context.
2. Compact it once.
3. Reuse the shorter version in later prompts instead of resending the original prose.

In Claude Code, the explicit entry point is `/compressoor ...`. In Codex, use the installed plugin or scripts directly when you want packing behavior.

## Benchmarks

Compressoor and Caveman optimize different parts of the loop, so the headline numbers are not directly comparable:

| Tool | Primary target | Public benchmark signal |
|------|------|------:|
| [Caveman](https://github.com/JuliusBrussee/caveman) | Output token reduction by changing response style | 65% average output-token reduction in its README |
| Compressoor `compact` | Reusable prompt and handoff compaction | 35.8% average prompt-token reduction on 15 cases |
| Compressoor `compact_min` | More aggressive follow-up-oriented prompt compaction | 46.0% average prompt-token reduction on 15 cases |

> [!IMPORTANT]
> Caveman's published numbers are output-token benchmarks. Compressoor's strongest measured result so far is prompt compaction on reusable context. Those are different workloads and should not be treated as like-for-like savings.

### Direct Prompt Compaction

Run the direct prompt-compaction benchmark:

```bash
python3 benchmarks/benchmark_explicit_packed_context.py
python3 benchmarks/benchmark_explicit_packed_context.py --dry-run
python3 benchmarks/benchmark_explicit_packed_context.py --update-readme
```

This compares verbose prompt scaffolds against compacted prompt scaffolds and reports token savings for the compaction helpers. The benchmark corpus now lives in [`benchmarks/prompts.json`](benchmarks/prompts.json), using the same high-level layout as Caveman's benchmark fixture.

- `compact`: full compacted form
- `compact_min`: shorter follow-up-oriented form

<!-- benchmark:direct-prompt:start -->
| Task | Verbose | `compact` | Saved | `compact_min` | Saved |
|------|-------:|----------:|------:|--------------:|------:|
| Explain React re-render bug | 55 | 40 | 27.3% | 33 | 40.0% |
| Fix auth middleware token expiry | 70 | 41 | 41.4% | 33 | 52.9% |
| Set up PostgreSQL connection pool | 66 | 36 | 45.5% | 36 | 45.5% |
| Explain git rebase vs merge | 55 | 38 | 30.9% | 30 | 45.5% |
| Review PR for security issues | 67 | 43 | 35.8% | 35 | 47.8% |
| Refactor callback to async/await | 52 | 36 | 30.8% | 31 | 40.4% |
| Architecture: microservices vs monolith | 55 | 37 | 32.7% | 37 | 32.7% |
| Docker multi-stage build | 52 | 37 | 28.8% | 31 | 40.4% |
| Debug PostgreSQL race condition | 78 | 45 | 42.3% | 32 | 59.0% |
| Implement React error boundary | 56 | 37 | 33.9% | 31 | 44.6% |
| Refactor payments retry helper | 60 | 40 | 33.3% | 35 | 41.7% |
| Update navigation layout guardrails | 55 | 32 | 41.8% | 32 | 41.8% |
| CSV parser handoff | 78 | 47 | 39.7% | 31 | 60.3% |
| Cache invalidation review | 68 | 44 | 35.3% | 36 | 47.1% |
| Bun repo rules | 54 | 38 | 29.6% | 34 | 37.0% |
| **Average** | **61.4** | **39.4** | **35.8%** | **33.1** | **46.0%** |

*Range: `compact` 27.3% to 45.5%; `compact_min` 32.7% to 60.3%.*
<!-- benchmark:direct-prompt:end -->

### Live Codex Run

Live Codex usage is much noisier because fixed per-run overhead dominates short prompts. Current live result so far:

| Task | Verbose total | `compact` total | Saved | `compact_min` total | Saved |
|------|--------------:|----------------:|------:|--------------------:|------:|
| Explain React re-render bug | 29,900 | 29,870 | 0.1% | 29,875 | 0.1% |

The same live run showed no input-token savings on that single case because Codex session overhead was much larger than the prompt delta:

- verbose input: 29,598
- `compact` input: 29,600
- `compact_min` input: 29,606

That makes the live result directionally useful, but not strong enough yet for a broader claim.

To measure live Codex token usage for the same A/B prompts:

```bash
python3 benchmarks/benchmark_explicit_packed_context.py --limit 5 --live-codex
python3 benchmarks/benchmark_explicit_packed_context.py --limit 5 --live-codex --repeats 3 --order alternate
```

There is also a Codex CLI integration benchmark:

```bash
python3 benchmarks/benchmark_codex_cli.py --limit 5
```

Use that one as a runtime and integration check, not as the primary savings benchmark. A longer live Codex CLI session benchmark was started, then stopped to avoid burning more benchmark budget, so there is no aggregate session benchmark published here yet.

## Main Files

- [`skills/compressoor/SKILL.md`](skills/compressoor/SKILL.md): runtime policy and compaction behavior
- [`skills/compressoor/scripts/compact_prompt.py`](skills/compressoor/scripts/compact_prompt.py): direct prompt compactor
- [`skills/compressoor/scripts/render_live_context.py`](skills/compressoor/scripts/render_live_context.py): short live-context renderer
- [`skills/compressoor/scripts/install_codex_compressoor.py`](skills/compressoor/scripts/install_codex_compressoor.py): installer for runtime-policy notes
- [`skills/compressoor/scripts/launch_codex_compressoor.py`](skills/compressoor/scripts/launch_codex_compressoor.py): session launcher
- [`benchmarks/benchmark_explicit_packed_context.py`](benchmarks/benchmark_explicit_packed_context.py): main benchmark runner

## Tests

```bash
python3 -m unittest discover -s tests/compressoor -p 'test_*.py'
```

## Repo Layout

```text
compressoor/
├── plugins/compressoor/
├── skills/compressoor/
├── benchmarks/
└── tests/compressoor/
```
