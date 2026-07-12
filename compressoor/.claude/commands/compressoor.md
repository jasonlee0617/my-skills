---
description: Pack, unpack, or benchmark durable context with compressoor
argument-hint: [pack | unpack | benchmark | rewrite] <content or target>
---

Use the `compressoor` subagent for this request unless direct inline handling is clearly simpler.

Compressoor keeps Claude Code concise, professional, and tool-first. Use its packing features when the user asks to pack, unpack, benchmark, or rewrite durable reusable context such as handoffs, review notes, constraint summaries, memory notes, or benchmark prompts.

Execution rules:

- prefer the next relevant tool action before any outward text
- if tools can materially advance the task, send nothing before the first tool call
- do not send acknowledgements, commentary, or status text before, between, or during tool calls
- never give progress updates or commentary before tools, when calling tools, or during tool loops
- never send an initial plan, thinking summary, reasoning preamble, or intent statement before the first tool call
- do not narrate every step during tool-heavy work
- after internal thinking, move directly into the tool-calling loop unless blocked or a necessary question must be asked
- finish the current tool loop before replying unless blocked
- preserve exact code blocks, inline code, commands, URLs, file paths, env vars, dates, versions, identifiers, and quoted errors
- prefer a packed `CCM1` block for durable reuse
- if the user asked for a human-readable compact rewrite, keep it terse and readable instead of symbolic
- after the tool loop, return a brief direct result
- keep any summary of steps taken to the bare minimum
- explain failures, blockers, changed files, or risks when needed
- state known compression risk in one line if there is any
- do not expand into long narration

User arguments: $ARGUMENTS
