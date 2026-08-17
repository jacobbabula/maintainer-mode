from __future__ import annotations

from pathlib import Path
from typing import Any

from .git import executable_available, git_state, repo_root, run_command


def inspect_repository(path: Path) -> dict[str, Any]:
    root = repo_root(path)
    instructions: list[str] = []
    patterns = (
        "AGENTS.md",
        "CONTRIBUTING*",
        "SECURITY.md",
        ".github/PULL_REQUEST_TEMPLATE*",
        ".github/pull_request_template*",
        ".github/PULL_REQUEST_TEMPLATE/**/*",
        ".github/pull_request_template/**/*",
    )
    for pattern in patterns:
        instructions.extend(str(item.relative_to(root)).replace("\\", "/") for item in root.glob(pattern) if item.is_file())
    gh_available = executable_available("gh")
    gh_authenticated = False
    if gh_available:
        gh_authenticated = run_command(["gh", "auth", "status"], cwd=root, check=False).returncode == 0
    return {
        "repository": root.name,
        "git": git_state(root),
        "instruction_files": sorted(set(instructions)),
        "policy_file": ".maintainer-mode.json" if (root / ".maintainer-mode.json").is_file() else None,
        "tools": {
            "git": executable_available("git"),
            "gh": gh_available,
            "gh_authenticated": gh_authenticated,
        },
        "warnings": _warnings(root, instructions, gh_available, gh_authenticated),
    }


def _warnings(root: Path, instructions: list[str], gh_available: bool, gh_authenticated: bool) -> list[str]:
    warnings: list[str] = []
    if not instructions:
        warnings.append("No root contribution or agent instruction files were discovered.")
    if not (root / ".maintainer-mode.json").is_file():
        warnings.append("No explicit .maintainer-mode.json policy exists; unknown gates must remain ASK.")
    if not gh_available:
        warnings.append("GitHub CLI is unavailable; live issue and PR snapshots cannot be captured.")
    elif not gh_authenticated:
        warnings.append("GitHub CLI is not authenticated; live snapshots may fail.")
    return warnings


def render_doctor_markdown(report: dict[str, Any]) -> str:
    git = report["git"]
    tools = report["tools"]
    lines = [
        "# Maintainer Mode doctor",
        "",
        f"**Repository:** `{report['repository']}`",
        f"**Branch:** `{git.get('branch') or 'detached'}`",
        f"**HEAD:** `{str(git.get('head') or 'unknown')[:12]}`",
        f"**Worktree:** {'dirty' if git.get('dirty') else 'clean'}",
        f"**GitHub CLI:** {'authenticated' if tools['gh_authenticated'] else 'not ready'}",
        "",
        "## Instruction surface",
        "",
    ]
    files = report["instruction_files"]
    lines.extend(f"- `{item}`" for item in files)
    if not files:
        lines.append("- None discovered")
    if report["warnings"]:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {item}" for item in report["warnings"])
    lines.append("")
    return "\n".join(lines)
