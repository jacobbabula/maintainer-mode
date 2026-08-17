from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from .git import GitError, run_command


def gh_json(args: list[str]) -> Any:
    result = run_command(["gh", *args])
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise GitError(f"GitHub CLI returned invalid JSON for: gh {' '.join(args)}") from exc


def current_actor() -> str:
    data = gh_json(["api", "user"])
    login = data.get("login") if isinstance(data, dict) else None
    if not login:
        raise GitError("Could not determine the authenticated GitHub login")
    return str(login)


def capture_snapshot(repository: str, issue_number: int, actor: str | None = None) -> dict[str, Any]:
    actor = actor or current_actor()
    issue = gh_json(
        [
            "issue",
            "view",
            str(issue_number),
            "--repo",
            repository,
            "--json",
            "number,title,url,state,author,assignees,labels,createdAt,updatedAt",
        ]
    )
    candidates = gh_json(
        [
            "pr",
            "list",
            "--repo",
            repository,
            "--state",
            "open",
            "--search",
            f"#{issue_number}",
            "--limit",
            "100",
            "--json",
            "number,title,url,state,author,body",
        ]
    )
    # Search results can be fuzzy. Keep only bodies with an explicit issue-number mention.
    mention = re.compile(rf"(?<!\d)#{issue_number}(?!\d)")
    candidates = [item for item in candidates if mention.search(str(item.get("body", "")))]
    open_prs = gh_json(
        [
            "pr",
            "list",
            "--repo",
            repository,
            "--state",
            "open",
            "--author",
            actor,
            "--limit",
            "100",
            "--json",
            "number",
        ]
    )
    return {
        "schema": "maintainer-mode.snapshot/v1",
        "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "repository": repository,
        "actor": {"login": actor},
        "actor_open_prs": len(open_prs),
        "issue": issue,
        "candidate_pull_requests": candidates,
        "disclaimer": "Candidate pull requests mention the issue number; inspect diffs to confirm overlap.",
    }
