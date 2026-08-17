# Receipt schema v1

`maintainer-mode.receipt/v1` is a local JSON record with these sections:

| Field | Meaning |
|---|---|
| `id`, `recorded_at` | Unique run identity and UTC completion time |
| `repository` | Repository name and credential-sanitized origin |
| `check` | Stable label, redacted argv, timing, exit code, pass/fail |
| `output` | SHA-256 and byte count for stdout/stderr; never raw logs |
| `git.before`, `git.after` | Commit, branch, dirty paths, diff and worktree hashes |
| `runtime` | OS and Python versions |
| `privacy` | Explicit storage and redaction behavior |
| `integrity` | SHA-256 over canonical JSON excluding `integrity` itself |

## Claim rules

The report selects the latest receipt for each required label. `PROVEN` requires:

1. Every required label exists.
2. Every selected command exited zero.
3. Every selected integrity digest verifies.
4. Every selected receipt has the same Git HEAD and worktree fingerprint.

Raw command output is intentionally not recoverable from a receipt. The command line is retained for provenance and redacted on a best-effort basis; do not put secrets directly in command arguments.
