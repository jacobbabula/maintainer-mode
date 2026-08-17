---
name: prove-contribution
description: Verify an open-source patch and create an honest, exact-tree evidence packet for a pull request. Use when the user asks whether a change is ready, what tests ran, for a PR description or verification section, to validate local checks, or to prevent unsupported claims about CI, reviews, mergeability, acceptance, or rewards.
---

# Prove Contribution

Convert observed verification into bounded claims. Absence of evidence stays visible.

## Workflow

1. Derive required checks from repository instructions, CI workflows, project configuration, and the changed surface. Distinguish mandatory checks from useful targeted checks.
2. Resolve `../../scripts/maintainer_mode.py` relative to this file. Run every local check with `run --repo <path> --label <stable-name> -- <command>`.
3. If a check changes files, inspect the change and rerun all required checks against the final tree.
4. Run `report --receipts <printed-directory> --policy <repo-policy> --output <report.md>`, or repeat `--require <label>` when no explicit policy exists.
5. Accept `PROVEN` only when all required labels pass with valid receipts on one commit and worktree fingerprint. Treat `NOT PROVEN` as a blocker to the corresponding claim, not necessarily to all development.
6. Inspect hosted CI separately. Never translate a local receipt into “CI passed,” or a green CI run into maintainer approval.

## Claim language

Use concrete sentences such as “Locally ran `unit-tests` and `lint` against commit `abc123`; both passed.” State skipped, unavailable, or unrelated checks explicitly. Keep source review, local execution, hosted execution, review status, merge status, and reward eligibility separate.

Receipts store command provenance and output hashes, not raw logs or environment variables. Their SHA-256 detects edits but is not a signature or proof of runner identity. Preserve this limitation in durable reports.

Do not post a PR body, review, or follow-up comment without explicit authorization for that public action.
