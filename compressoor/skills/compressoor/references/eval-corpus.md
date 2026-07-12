# Eval Corpus

Use these examples to tune compression quality and spot failure modes.

## Example 1: Bug Fix

Source:

```text
We need to fix the authentication middleware without changing the API contract. Keep the current error message exactly the same. The likely bug is that token expiry uses < instead of <=. Update tests around the boundary case and do not introduce a database migration.
```

Target properties:

- preserve API stability constraint
- preserve exact error-message requirement
- preserve boundary comparison decision
- preserve test follow-up

Critical facts:

- `authentication middleware`
- `do not change the API contract`
- `keep the current error message exactly the same`
- `token expiry uses < instead of <=`
- `do not introduce a database migration`

## Example 2: Refactor

Source:

```text
Refactor the payments client to isolate retry logic into a single helper. Do not change request payload shapes or public method names. Add unit coverage for timeout and 429 retry behavior. Risk: webhook reconciliation may depend on existing error wrapping.
```

Target properties:

- preserve no-API-change constraints
- preserve extracted helper decision
- preserve timeout and 429 coverage
- preserve webhook reconciliation risk

Critical facts:

- `payments client`
- `isolate retry logic into a single helper`
- `do not change request payload shapes`
- `do not change public method names`
- `timeout`
- `429`
- `webhook reconciliation`

## Example 3: Review Handoff

Source:

```text
Current status: parser change is implemented in src/parser.ts, but integration tests are not run yet. Unit tests pass. The main unresolved issue is whether the new delimiter handling breaks legacy CSV imports. Next steps are to run integration tests and verify one old fixture before merging.
```

Target properties:

- preserve implemented file
- preserve unit-pass and integration-not-run status
- preserve delimiter compatibility risk
- preserve next actions

Critical facts:

- `src/parser.ts`
- `implemented`
- `integration tests are not run yet`
- `unit tests pass`
- `legacy CSV imports`
- `run integration tests`
- `verify one old fixture`

## Example 4: Project Memory

Source:

```text
This repository uses Bun for scripts, not npm. Prefer ripgrep for search. Avoid destructive git commands unless explicitly requested. If editing frontend code, preserve the existing design system and do not introduce a new font stack.
```

Target properties:

- preserve tool preferences
- preserve safety rule on git
- preserve frontend design constraint

Critical facts:

- `Bun for scripts`
- `prefer ripgrep for search`
- `avoid destructive git commands`
- `preserve the existing design system`
- `do not introduce a new font stack`

## Example 5: Dense Handoff

Source:

```text
Auth fix is in src/auth.ts. Keep API stable. Keep the exact error text. Tests for the boundary case still need to be added. No DB migration.
```

Target properties:

- preserve implementation file
- preserve API stability
- preserve exact error text
- preserve boundary test requirement
- preserve migration ban

Critical facts:

- `src/auth.ts`
- `keep API stable`
- `keep the exact error text`
- `boundary case`
- `no DB migration`
