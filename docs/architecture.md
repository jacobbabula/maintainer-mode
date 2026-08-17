# Architecture

Maintainer Mode separates agent judgment from deterministic claims.

```text
GitHub + repository docs
          |
          v
   read-only snapshot  --->  policy gate  --->  READY / ASK / STOP
                                                    |
                                                    v
                                             focused change
                                                    |
                                                    v
command execution  --->  privacy-preserving receipt  --->  exact-tree report
```

## Boundaries

The Codex skills own the adaptive work: reading instructions, judging semantic overlap, designing a patch, and interpreting maintainer feedback. The Python engine owns repeatable mechanics: snapshot shape, configured gate evaluation, receipt integrity, Git state fingerprints, and report completeness.

The engine is offline by default. Only `snapshot` calls the GitHub CLI, and it performs read-only queries. It never comments, creates a branch, pushes, opens a PR, submits a review, or changes readiness.

## Fail-closed behavior

`STOP` is reserved for explicit contradictions such as a closed issue, configured blocking label, missing required acceptance, or configured PR-count limit. `ASK` captures uncertainty: a stale snapshot, another assignee, a candidate duplicate, or incomplete policy data. `READY` means only that no configured gate blocked implementation.

## Exact-tree verification

A receipt records Git HEAD plus a worktree SHA-256 derived from porcelain status, the binary diff, untracked paths, and untracked file bytes. A report refuses `PROVEN` if required checks were recorded against different fingerprints.

Receipts default to Git's private metadata path (`git rev-parse --git-path maintainer-mode/receipts`) so evidence does not modify the contribution being measured. Linked worktrees therefore receive the correct Git-managed path automatically.

## Trust model

Receipt hashes detect accidental or post-hoc content changes. They are not signatures: someone who controls a file can construct and rehash a new receipt. The system proves internal consistency, not runner identity. Hosted CI remains the authoritative shared execution surface when a project provides it.
