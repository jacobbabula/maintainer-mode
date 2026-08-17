from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import Decision, GateResult


@dataclass(frozen=True)
class ContributionPolicy:
    blocked_labels: tuple[str, ...] = ("blocked", "deferred", "duplicate", "invalid", "wontfix")
    accepted_labels: tuple[str, ...] = ()
    require_acceptance: bool = False
    self_filed_requires_acceptance: bool = True
    max_actor_open_prs: int | None = None
    snapshot_freshness_hours: int = 24
    required_checks: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "ContributionPolicy":
        known = {
            "blocked_labels",
            "accepted_labels",
            "require_acceptance",
            "self_filed_requires_acceptance",
            "max_actor_open_prs",
            "snapshot_freshness_hours",
            "required_checks",
        }
        unknown = sorted(set(raw) - known - {"version"})
        if unknown:
            raise ValueError(f"Unknown policy keys: {', '.join(unknown)}")
        if raw.get("version", 1) != 1:
            raise ValueError("Only policy version 1 is supported")
        values = {key: raw[key] for key in known if key in raw}
        for key in ("blocked_labels", "accepted_labels", "required_checks"):
            if key in values:
                values[key] = tuple(str(item) for item in values[key])
        return cls(**values)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return data


def normalize_labels(items: list[Any]) -> set[str]:
    labels: set[str] = set()
    for item in items:
        if isinstance(item, str):
            labels.add(item.casefold())
        elif isinstance(item, dict) and item.get("name"):
            labels.add(str(item["name"]).casefold())
    return labels


def parse_time(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def evaluate_gate(
    snapshot: dict[str, Any],
    policy: ContributionPolicy,
    *,
    now: datetime | None = None,
) -> GateResult:
    now = now or datetime.now(timezone.utc)
    result = GateResult()
    issue = snapshot.get("issue")
    actor = snapshot.get("actor")

    schema = snapshot.get("schema")
    if schema != "maintainer-mode.snapshot/v1":
        decision = Decision.ASK if schema is None else Decision.STOP
        result.add(
            decision,
            "snapshot.schema-unsupported",
            f"Expected maintainer-mode.snapshot/v1, received {schema or 'no schema'}.",
        )

    if not isinstance(issue, dict):
        result.add(Decision.STOP, "snapshot.issue.missing", "The snapshot has no issue record.")
        return result
    if not isinstance(actor, dict) or not actor.get("login"):
        result.add(Decision.ASK, "snapshot.actor.missing", "Record the contributor login before proceeding.")

    state = str(issue.get("state", "")).upper()
    if state != "OPEN":
        result.add(Decision.STOP, "issue.not-open", f"Issue state is {state or 'unknown'}, not OPEN.")

    labels = normalize_labels(issue.get("labels") or [])
    blocked = labels.intersection(label.casefold() for label in policy.blocked_labels)
    if blocked:
        result.add(
            Decision.STOP,
            "issue.blocked-label",
            f"Issue has blocking label(s): {', '.join(sorted(blocked))}.",
        )

    accepted = labels.intersection(label.casefold() for label in policy.accepted_labels)
    actor_login = str((actor or {}).get("login", "")).casefold()
    author = issue.get("author") or {}
    author_login = str(author.get("login", "") if isinstance(author, dict) else author).casefold()
    self_filed = bool(actor_login and author_login and actor_login == author_login)
    needs_acceptance = policy.require_acceptance or (
        self_filed and policy.self_filed_requires_acceptance
    )
    if needs_acceptance and not policy.accepted_labels:
        result.add(
            Decision.ASK,
            "policy.acceptance-labels-undefined",
            "Acceptance is required, but the policy does not define accepted labels.",
        )
    elif needs_acceptance and not accepted:
        reason = "Self-filed issues" if self_filed else "This repository"
        result.add(
            Decision.STOP,
            "issue.acceptance-required",
            f"{reason} require maintainer acceptance before implementation.",
            f"Expected one of: {', '.join(policy.accepted_labels)}",
        )

    candidates = snapshot.get("candidate_pull_requests") or []
    open_candidates = [
        item
        for item in candidates
        if isinstance(item, dict) and str(item.get("state", "OPEN")).upper() == "OPEN"
    ]
    if open_candidates:
        numbers = ", ".join(f"#{item.get('number', '?')}" for item in open_candidates)
        result.add(
            Decision.ASK,
            "duplicate.candidate-pr",
            f"Open pull request candidate(s) mention this issue: {numbers}.",
            "Inspect the diffs before deciding whether the work overlaps.",
        )

    assignees = issue.get("assignees") or []
    assignee_names = {
        str(item.get("login", "") if isinstance(item, dict) else item).casefold()
        for item in assignees
    }
    other_assignees = sorted(name for name in assignee_names if name and name != actor_login)
    if other_assignees:
        result.add(
            Decision.ASK,
            "issue.assigned-to-other",
            f"Issue is assigned to: {', '.join(other_assignees)}.",
        )

    actor_open_prs = snapshot.get("actor_open_prs")
    if policy.max_actor_open_prs is not None:
        if actor_open_prs is None:
            result.add(
                Decision.ASK,
                "actor.open-pr-count-missing",
                "Policy limits concurrent PRs, but the actor's open PR count is missing.",
            )
        else:
            try:
                open_pr_count = int(actor_open_prs)
            except (TypeError, ValueError):
                result.add(Decision.ASK, "actor.open-pr-count-invalid", "Actor open PR count is invalid.")
            else:
                if open_pr_count >= policy.max_actor_open_prs:
                    result.add(
                        Decision.STOP,
                        "actor.open-pr-limit",
                        f"Actor has {open_pr_count} open PR(s); policy limit is {policy.max_actor_open_prs}.",
                    )

    captured_at = snapshot.get("captured_at")
    if not captured_at:
        result.add(Decision.ASK, "snapshot.timestamp-missing", "Snapshot freshness cannot be verified.")
    else:
        try:
            age_hours = (now - parse_time(str(captured_at))).total_seconds() / 3600
            if age_hours < -0.05:
                result.add(Decision.ASK, "snapshot.from-future", "Snapshot timestamp is in the future.")
            elif age_hours > policy.snapshot_freshness_hours:
                result.add(
                    Decision.ASK,
                    "snapshot.stale",
                    f"Snapshot is {age_hours:.1f} hours old; refresh it before acting.",
                )
        except ValueError:
            result.add(Decision.ASK, "snapshot.timestamp-invalid", "Snapshot timestamp is invalid.")

    if not result.findings:
        result.add(
            Decision.READY,
            "gate.ready",
            "No configured policy gate blocks implementation.",
            "This is a readiness check, not maintainer approval.",
        )
    return result


def render_gate_markdown(result: GateResult, snapshot: dict[str, Any]) -> str:
    issue = snapshot.get("issue") or {}
    title = issue.get("title") or "Untitled issue"
    number = issue.get("number", "?")
    lines = [
        f"# Contribution gate: {result.decision.label}",
        "",
        f"**Issue:** #{number} - {title}",
        "",
    ]
    for finding in result.findings:
        marker = {Decision.READY: "PASS", Decision.ASK: "ASK", Decision.STOP: "STOP"}[finding.decision]
        lines.append(f"- **{marker} / `{finding.code}`** - {finding.message}")
        if finding.evidence:
            lines.append(f"  - {finding.evidence}")
    lines.extend(
        [
            "",
            "> Maintainer Mode never treats this report as assignment, acceptance, or permission to publish.",
        ]
    )
    return "\n".join(lines) + "\n"
