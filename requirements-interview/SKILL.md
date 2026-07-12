---
name: requirements-interview
description: Conduct one-question-at-a-time requirements interviews before producing a decision-complete plan. Use when the user explicitly requests iterative clarification, requirements discovery, constraint gathering, or a final solution only after high confidence.
---

# Requirements Interview

Clarify the user's goal, constraints, and acceptance criteria through a focused interview, then produce one implementation-ready plan.

## Interview Workflow

1. Inspect available files, logs, configuration, and environment before asking about facts that can be discovered directly.
2. Identify the single highest-impact uncertainty that prevents a correct plan.
3. Ask exactly one material question in the current turn.
4. Use the user's latest answer to choose the next single question; do not repeat answered questions or ask filler questions.
5. Continue until no material ambiguity remains. Treat 95% confidence as a decision threshold, not a numeric calculation.
6. State any residual assumptions and produce one complete, decision-ready plan.

## Readiness Checklist

Before producing the plan, confirm or mark as not applicable:

- goal and desired outcome
- current state and relevant context
- in-scope and out-of-scope work
- users, operators, or downstream consumers
- functional and safety constraints
- interfaces, dependencies, and compatibility requirements
- important tradeoffs and user preferences
- failure handling and rollback expectations
- verification steps and acceptance criteria

Do not keep interviewing after the remaining uncertainty would not materially change the solution.

## Boundaries

- Follow higher-priority system, developer, mode, safety, and user instructions.
- Do not implement changes while the user has asked only for a plan.
- Do not claim 95% confidence merely because many questions were asked.
- If the user requests immediate implementation or explicitly waives clarification, proceed with stated assumptions unless a blocking or safety-critical uncertainty remains.
