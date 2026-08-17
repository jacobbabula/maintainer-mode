---
name: triage-contribution
description: Evaluate whether a GitHub issue is a safe, non-duplicative, policy-compliant open-source contribution before coding or posting. Use for contribution scouting, issue selection, acceptance-label checks, assignment checks, duplicate PR screening, contributor-limit checks, and deciding whether work is READY, needs maintainer clarification, or must STOP.
---

# Triage Contribution

Produce a source-backed `READY`, `ASK`, or `STOP` decision before implementation. Treat repository policy and current GitHub state as volatile.

## Workflow

1. Resolve the target repository and issue. Read every applicable `AGENTS.md`, contribution guide, security policy, and pull-request template before recommending action.
2. Resolve `../../scripts/maintainer_mode.py` relative to this file and run `doctor <repo-path>`. Preserve the worktree; this phase is read-only.
3. When current GitHub state is needed, run `snapshot --repo OWNER/REPO --issue N --output <temporary-json>`. This command is read-only. If live access is unavailable, label the result stale or unverified.
4. Use a repository `.maintainer-mode.json` only when its rules are sourced from maintainer documentation. Never invent labels or limits to force a verdict.
5. Run `gate` against the snapshot and policy. If no explicit policy exists, use the engine's conservative defaults and keep unknown repository-specific rules as `ASK`.
6. Inspect every candidate duplicate semantically: compare changed files, intended behavior, and issue linkage. An issue-number match is a lead, not proof of duplication.
7. Report the verdict, each finding with its source, and exactly one next action.

## Decision contract

- `READY`: no discovered or configured gate blocks implementation. Do not call this acceptance, assignment, or likely merge.
- `ASK`: a maintainer or user decision is needed, or evidence is stale/incomplete. Draft a concise question if useful, but do not post it.
- `STOP`: current evidence contradicts starting work. Do not implement unless new authoritative evidence changes the gate.

## Authorization boundary

Do not comment, claim an issue, create a branch remotely, commit, push, or open a PR during triage unless the user explicitly authorizes the named action. A general request to “look” or “find” authorizes read-only inspection only.
