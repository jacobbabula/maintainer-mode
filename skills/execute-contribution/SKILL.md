---
name: execute-contribution
description: Implement a focused, attribution-safe open-source code contribution from an accepted or otherwise ready GitHub issue. Use when the user asks to fix an issue, write the patch, add tests, prepare a commit, push a contribution branch, or open a pull request after policy and duplicate gates have been checked.
---

# Execute Contribution

Turn a `READY` issue into the smallest defensible patch while preserving repository state and user authorship.

## Entry gate

Run `$triage-contribution` first or verify equivalent current evidence. Do not start from a `STOP` verdict. For `ASK`, resolve the uncertainty before broad implementation; a user may accept an ordinary engineering tradeoff but cannot waive a maintainer's explicit contribution rule.

## Workflow

1. Inspect the exact code path, tests, blame, and nearby conventions. Record the causal behavior and narrow acceptance criteria.
2. Check the worktree before editing. Preserve unrelated and pre-existing changes. Follow all scoped instruction files.
3. Implement one coherent fix with a regression test that fails for the original reason. Avoid opportunistic refactors and generated churn.
4. Resolve `../../scripts/maintainer_mode.py` relative to this file. Run each required local check through `run --label <stable-name> -- <command>` so the result is attached to the exact tree.
5. Review the diff for scope, platform behavior, public API compatibility, error surfaces, and accidental files. Rerun checks after any code change.
6. Invoke `$prove-contribution` before drafting verification claims.

## Attribution and public actions

Keep authored work attributable to the user. Never claim maintainer agreement, independent review, hosted execution, or tests that were not observed.

Treat these as separate authorization gates: public comment, commit, push, PR creation, review submission, and changing draft/readiness state. Authorization for one does not imply the next. Prepare content locally when authorization is absent, then stop at the boundary.

Before a push or PR, recheck the live issue, duplicate candidates, branch diff, remote target, and authenticated GitHub identity. Never push to a protected or upstream branch by assumption.
