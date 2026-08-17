<p align="center">
  <img src="assets/maintainer-mode-mark.svg" width="120" alt="Maintainer Mode mark">
</p>

<h1 align="center">Maintainer Mode</h1>

<p align="center"><strong>Turn GitHub issues into defensible pull requests—without duplicating work or claiming tests that never ran.</strong></p>

<p align="center">
  <a href="https://github.com/jacobbabula/maintainer-mode/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/jacobbabula/maintainer-mode/ci.yml?branch=main&style=flat-square" alt="CI status"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-101828?style=flat-square" alt="MIT license"></a>
  <a href="https://github.com/jacobbabula/maintainer-mode/stargazers"><img src="https://img.shields.io/github/stars/jacobbabula/maintainer-mode?style=flat-square" alt="GitHub stars"></a>
</p>

Maintainer Mode is a Codex plugin and zero-dependency CLI for evidence-first open-source contribution. It gives an agent four precise workflows—triage, execute, prove, and follow up—and puts deterministic gates beneath the judgment calls.

```text
Contribution gate: ASK

ASK / duplicate.candidate-pr - Open pull request candidate #99 mentions this issue.
ASK / issue.assigned-to-other - Issue is assigned to someone-else.

Next action: inspect the existing diff before writing code.
```

## Why it exists

Coding is often the easy part. The expensive failures happen around it: a deferred issue, an overlapping PR, a contribution rule hidden in `AGENTS.md`, a test result from the wrong commit, or a public comment the user never approved.

Maintainer Mode treats those as first-class engineering constraints.

| Stage | Codex skill | Deterministic support |
|---|---|---|
| Decide whether to work | `$triage-contribution` | Live snapshot + READY / ASK / STOP gate |
| Build the smallest correct change | `$execute-contribution` | Repository doctor + authorization boundaries |
| Make only provable claims | `$prove-contribution` | Integrity-checked receipts + exact-tree report |
| Respond without noise | `$follow-up-contribution` | CI/review classification + scoped next action |

## One-minute local demo

Requirements: Python 3.10+, Git, and optionally the authenticated GitHub CLI for live read-only snapshots.

```bash
# Run the bundled disposable demo first
python scripts/demo.py

# Inspect a checkout without changing it
python scripts/maintainer_mode.py doctor ../some-project

# Run the deterministic gate against bundled fixtures
python scripts/maintainer_mode.py gate \
  --snapshot tests/fixtures/issue-ready.json \
  --policy tests/fixtures/policy.json

# Record checks. Raw stdout/stderr are displayed but not stored.
python scripts/maintainer_mode.py run --repo ../some-project --label unit-tests -- python -m unittest
python scripts/maintainer_mode.py run --repo ../some-project --label lint -- ruff check .

# Use the receipt directory printed by the commands above
python scripts/maintainer_mode.py report \
  --receipts ../some-project/.git/maintainer-mode/receipts \
  --policy ../some-project/.maintainer-mode.json \
  --output evidence.md
```

The report says `PROVEN` only when every required label has a latest passing receipt, each receipt's integrity digest is valid, and all receipts describe the same commit and worktree contents.

## Live GitHub triage

Snapshot is read-only. It captures current issue metadata, assignees, the contributor's open PR count, and PRs whose bodies explicitly mention the issue number.

```bash
python scripts/maintainer_mode.py snapshot \
  --repo owner/project --issue 123 \
  --output issue-123.snapshot.json

python scripts/maintainer_mode.py gate \
  --snapshot issue-123.snapshot.json \
  --policy .maintainer-mode.json
```

Candidate duplicates remain `ASK`, never an automatic accusation: issue-number search is a lead, and a human or agent must inspect the actual diff.

Gate exit codes are automation-friendly: `0` for `READY`, `1` for `ASK`, and `2` for `STOP` or invalid input.

## Explicit repository policy

Maintainer Mode does not pretend it can infer every maintainer rule. Repositories can encode the small subset that should be deterministic:

```json
{
  "version": 1,
  "blocked_labels": ["deferred", "duplicate", "wontfix"],
  "accepted_labels": ["accepted"],
  "require_acceptance": true,
  "self_filed_requires_acceptance": true,
  "max_actor_open_prs": 4,
  "snapshot_freshness_hours": 24,
  "required_checks": ["unit-tests", "lint"]
}
```

Unknown rules stay unknown. Missing acceptance labels, stale snapshots, assignments, and candidate duplicates become explicit `ASK` findings. Closed issues and configured blocking labels become `STOP` findings.

## Evidence without log hoarding

Each receipt records the redacted command, exit code, output hashes and byte counts, runtime, Git commit, and a worktree fingerprint that includes tracked changes and untracked file contents. Raw output and environment variables are not persisted.

The SHA-256 integrity field detects receipt edits; it is not a signature, identity proof, CI result, or maintainer approval. That boundary is printed in every report because honest limitations are part of the feature.

See [the architecture](docs/architecture.md) and [receipt schema](docs/receipt-schema.md) for the exact contract.

## Codex plugin

The package follows the official Codex plugin layout:

```text
.codex-plugin/plugin.json
skills/
  triage-contribution/
  execute-contribution/
  prove-contribution/
  follow-up-contribution/
scripts/
src/
```

Point Codex's local plugin workflow at this checkout during development. Each skill resolves the bundled runner from its installed plugin path; the CLI never needs to be copied into the repository under review.

## Safety contract

- Read-only inspection is allowed when relevant; comments, commits, pushes, PR creation, review submission, and readiness changes require explicit user authorization.
- `READY` means no configured gate blocked the work. It does not mean accepted, assigned, mergeable, or guaranteed to be reviewed.
- Local execution, hosted CI, review approval, merge, and contributor rewards are reported as separate facts.
- Existing worktree changes are preserved. A public contribution never receives invented authorship or verification claims.
- No analytics, credential collection, network service, or hidden prompt telemetry exists.

## Development

```bash
python -m unittest discover -s tests -v
python scripts/maintainer_mode.py --version
```

The runtime uses only the Python standard library. See [CONTRIBUTING.md](CONTRIBUTING.md) for change requirements.

If Maintainer Mode saves you from one duplicated PR or one unsupported test claim, consider starring the repository. It helps other contributors find it.

## License

MIT
