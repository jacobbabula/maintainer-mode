---
name: follow-up-contribution
description: Inspect and advance an existing GitHub pull request after submission. Use when the user asks to check a PR, find maintainer responses, understand CI failures, address review comments, resolve conflicts, mark a draft ready, or decide whether and how to follow up without noisy or unauthorized public activity.
---

# Follow Up Contribution

Find the smallest next action from current PR evidence. Keep inspection read-only until the user authorizes a change or public response.

## Workflow

1. Verify the repository, PR number, current authenticated identity, and head commit. Read the PR body, timeline, reviews, inline threads, checks, and merge state.
2. Classify each signal:
   - `ACTION REQUIRED`: requested changes, merge conflict, failing required check, or maintainer question.
   - `WAIT`: checks running or review pending within the repository's normal cadence.
   - `READY FOR USER`: a prepared fix, reply, or readiness change needs authorization.
   - `DONE`: merged or closed with no requested follow-up.
3. For CI failure, inspect the failing job and reproduce the narrowest relevant command locally. Do not infer cause from the red icon alone.
4. For review feedback, map each unresolved comment to code and decide whether it needs a code change, explanation, or maintainer clarification. Implement only within the user's requested scope.
5. After edits, use `$prove-contribution` on the final tree and recheck the live PR before proposing a response.
6. Report new activity since the last check, current blockers, and exactly one recommended next action. Avoid “any updates?” comments unless the user explicitly requests one and the wait is reasonable under project norms.

## Authorization boundary

Reading PR state does not authorize replies, commits, pushes, review-thread resolution, re-requesting review, or changing draft/readiness state. Obtain explicit authorization for the exact external action and verify the resulting GitHub state after performing it.
