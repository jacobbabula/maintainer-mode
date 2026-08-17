from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path
from typing import Sequence


class GitError(RuntimeError):
    pass


def run_command(
    argv: Sequence[str],
    *,
    cwd: Path | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            list(argv),
            cwd=cwd,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise GitError(f"Executable not found: {argv[0]}") from exc
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown error"
        raise GitError(f"Command failed ({result.returncode}): {' '.join(argv)}\n{detail}")
    return result


def repo_root(path: Path) -> Path:
    result = run_command(["git", "rev-parse", "--show-toplevel"], cwd=path)
    return Path(result.stdout.strip()).resolve()


def git_text(root: Path, *args: str, check: bool = True) -> str:
    return run_command(["git", *args], cwd=root, check=check).stdout.strip()


def git_state(root: Path) -> dict[str, object]:
    status = git_text(root, "status", "--porcelain=v1", "--untracked-files=all")
    paths = sorted(line[3:] for line in status.splitlines() if len(line) > 3)
    diff = subprocess.run(
        ["git", "diff", "--binary", "HEAD", "--", "."],
        cwd=root,
        capture_output=True,
        check=False,
    ).stdout
    untracked_raw = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
        cwd=root,
        capture_output=True,
        check=False,
    ).stdout
    tree_hasher = hashlib.sha256()
    tree_hasher.update(status.encode("utf-8"))
    tree_hasher.update(b"\0DIFF\0")
    tree_hasher.update(diff)
    for raw_path in sorted(item for item in untracked_raw.split(b"\0") if item):
        tree_hasher.update(b"\0UNTRACKED\0")
        tree_hasher.update(raw_path)
        candidate = root / raw_path.decode("utf-8", errors="surrogateescape")
        if candidate.is_file():
            try:
                tree_hasher.update(candidate.read_bytes())
            except OSError:
                tree_hasher.update(b"[UNREADABLE]")
    remote = git_text(root, "remote", "get-url", "origin", check=False)
    return {
        "head": git_text(root, "rev-parse", "HEAD", check=False) or None,
        "branch": git_text(root, "branch", "--show-current", check=False) or None,
        "dirty": bool(paths),
        "dirty_paths": paths,
        "diff_sha256": hashlib.sha256(diff).hexdigest(),
        "worktree_sha256": tree_hasher.hexdigest(),
        "origin": sanitize_remote(remote) if remote else None,
    }


def sanitize_remote(remote: str) -> str:
    # Remove URL userinfo, which can contain credentials. Keep repository identity.
    if "://" in remote:
        scheme, rest = remote.split("://", 1)
        if "@" in rest:
            rest = rest.split("@", 1)[1]
        return f"{scheme}://{rest}"
    return remote


def executable_available(name: str) -> bool:
    return shutil.which(name) is not None
