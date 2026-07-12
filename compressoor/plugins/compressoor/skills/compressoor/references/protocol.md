# CCM1 Protocol

`CCM1` means `Codex Context Memory v1`.

Design target:

- extreme compression
- low decode ambiguity
- ASCII-safe
- tokenizer-friendly for GPT-5.4 style models

## Container

```text
CCM1|lvl=std|dom=code|src=auth-bug
A[authentication=aut]
G[fix auth expiry bug]
C[api stable;no db mig;keep err msg exact]
D[jwt stateless>sess;exp chk use<=]
S[bug repro yes;root=MW cmp]
F[src/auth.ts;test/auth.test.ts;fn=validateToken]
T[unit fail=2;integ nt]
R[refresh flow unclear]
N[patch MW;add edge test;run unit]
Q[refresh token same exp rule?]
```

## Semantics

- Each section is a compact fact bucket.
- Items inside brackets are separated by `;`.
- Use `>` for directional relation or chosen-over relation.
- Use `=` for compact key/value.
- Use `?` only for open uncertainty.
- Omit articles and filler words.
- `A[...]` is optional and only emitted when it yields net savings.
- The packer may emit inline output when it is shorter than multiline output.

## Section Guidance

`G[...]`
- Primary goal or goals.

`C[...]`
- Non-negotiable constraints, user requirements, safety boundaries.

`D[...]`
- Chosen decisions, tradeoffs, or exact fixes.

`S[...]`
- Current observed state, repro status, partial progress.

`F[...]`
- Files, functions, modules, endpoints, objects, entities.

`T[...]`
- Test results, verification status, missing coverage.

`R[...]`
- Known risks, edge cases, possible regressions.

`N[...]`
- Immediate next actions in execution order.

`Q[...]`
- Open questions that block or may change execution.

## Recommended Abbreviations

Keep abbreviations conservative and reusable.

```text
cfg=config
ctx=context
dep=dependency
doc=documentation
fn=function
impl=implementation
integ=integration
inv=invariant
msg=message
MW=middleware
perf=performance
pref=preference
reg=regression
req=requirement
resp=response
rt=round-trip
std=standard
tkn=token
unit=unit-test
ux=user-experience
val=validate
ver=version
```

Project-local abbreviations are allowed if they are:

- introduced once
- reused often
- unlikely to collide

Example:

```text
AB=auth-broker
RT=refresh-token
```

## Protected Atoms

These should pass through exactly:

- fenced code blocks
- inline code
- shell commands
- URLs
- file paths
- env vars
- dates
- version strings
- identifiers
- exact error text

If a source text contains a protected atom, copy it verbatim into the packed output or attach it with a short symbolic reference.

## Compression Tactics

Use these in order:

1. Delete filler and politeness.
2. Collapse long clauses into predicates.
3. Convert prose into state fields.
4. Replace repeated phrases with stable abbreviations.
5. Merge duplicate facts.
6. Keep only actionable uncertainty.

## Loss Budget

Use `lite` if any of these are true:

- a human will read and edit the packed text often
- wording nuance is operationally important
- the instruction is irreversible

Use `max` only if all of these are true:

- the payload is for agent handoff
- decode can be validated immediately
- protected atoms are preserved exactly

Use `auto` when you want the packer to prefer `std` by default and promote to `max` only for repetition-heavy notes.

## Compact Template Envelopes

For high-confidence note types, the packer may emit a compact template envelope instead of a full `CCM1` wrapper:

```text
E1[topic=react-rerender;cause=inline-obj-ref;fix=useMemo;note=shallow-cmp]
H1[f=src/parser.ts;st=impl;it=nt;ut=pass;q=legacy-csv;n=integ,fixture,merge]
M1[tool=bun;search=rg;git=safe;fe=design-sys;font=no-new]
K1[f=src/auth.ts;api=stable;err=exact;mig=no;bt=todo]
V1[f=src/cache.ts;issue=stale-partial-inval;c=api-stable;t=concurr-inval;r=miss-counter-shape]
P1[s=scan;n=bench]
```

These are preferred when they are shorter than the equivalent `CCM1` form.

Use `P1[...]` for unavoidable user-visible progress/status when the state is not meant to become reusable memory.

Recommended `P1` fields:

- `s=` short current phase or status
- `n=` immediate next action
- `r=` blocker or risk only if it changes the next action

Example `max` layout:

```text
CCM1|lvl=max|dom=repo|src=repo-mem|G[repo use bun 4 scripts]|C[git destr cmds only-if-req]|F[chk src/ui/app.tsx pre layout chg]
```

## Good Example

Source:

```text
We need to fix the authentication middleware without changing the API contract. Keep the current error message exactly the same. The likely bug is that token expiry uses < instead of <=. Update tests around the boundary case and do not introduce a database migration.
```

Packed:

```text
CCM1|lvl=std|dom=code|src=auth-fix
G[fix auth MW]
C[api stable;err msg exact;no db mig]
D[exp chk <=> <=]
F[MW=auth middleware]
N[patch exp cmp;add boundary test]
```

## Bad Example

```text
krg7::mw.exp<=|api~same|db0|msg!
```

Why bad:

- too opaque
- no stable schema
- weak cross-model decode
- high recovery cost if forgotten
