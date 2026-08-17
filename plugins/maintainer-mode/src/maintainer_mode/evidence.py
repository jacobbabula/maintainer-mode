from __future__ import annotations

import hashlib
import json
import platform
import re
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from .git import git_state, git_text, repo_root


SCHEMA = "maintainer-mode.receipt/v1"
SECRET_FLAGS = {
    "--api-key",
    "--password",
    "--secret",
    "--token",
    "-p",
}
SECRET_KEYWORDS = ("token", "password", "secret", "api_key", "apikey", "private_key")
TOKEN_PATTERNS = (
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{16,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def timestamp(value: datetime | None = None) -> str:
    return (value or utc_now()).isoformat(timespec="microseconds").replace("+00:00", "Z")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def receipt_digest(receipt_without_integrity: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json(receipt_without_integrity))


def slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return normalized[:48] or "check"


def redact_text(value: str) -> str:
    redacted = value
    for pattern in TOKEN_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    if "=" in redacted:
        key, candidate = redacted.split("=", 1)
        if any(keyword in key.casefold() for keyword in SECRET_KEYWORDS) and candidate:
            return f"{key}=[REDACTED]"
    return redacted


def redact_argv(argv: Sequence[str]) -> list[str]:
    result: list[str] = []
    hide_next = False
    for raw in argv:
        value = str(raw)
        if hide_next:
            result.append("[REDACTED]")
            hide_next = False
            continue
        result.append(redact_text(value))
        if value.casefold() in SECRET_FLAGS:
            hide_next = True
    return result


def write_receipt(directory: Path, receipt: dict[str, Any]) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    stamp = receipt["recorded_at"].replace("-", "").replace(":", "")
    stamp = stamp.replace("Z", "Z").replace("+00:00", "Z")
    filename = f"{stamp}_{slug(receipt['check']['label'])}_{receipt['id'][:8]}.json"
    target = directory / filename
    target.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target


def run_and_record(
    repo: Path,
    label: str,
    argv: Sequence[str],
    *,
    receipt_dir: Path | None = None,
) -> tuple[int, Path, bytes, bytes]:
    if not argv:
        raise ValueError("A command is required after --")
    root = repo_root(repo)
    before = git_state(root)
    started = utc_now()
    start_clock = time.monotonic()
    try:
        completed = subprocess.run(
            list(argv),
            cwd=root,
            capture_output=True,
            check=False,
        )
        return_code = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
        launch_error = None
    except FileNotFoundError as exc:
        return_code = 127
        stdout = b""
        stderr = str(exc).encode("utf-8", errors="replace")
        launch_error = "executable-not-found"
    finished = utc_now()
    after = git_state(root)
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "id": str(uuid.uuid4()),
        "recorded_at": timestamp(finished),
        "repository": {
            "name": root.name,
            "origin": after.get("origin"),
        },
        "check": {
            "label": label,
            "command": redact_argv(argv),
            "started_at": timestamp(started),
            "duration_ms": round((time.monotonic() - start_clock) * 1000),
            "exit_code": return_code,
            "passed": return_code == 0,
            "launch_error": launch_error,
        },
        "output": {
            "stdout_sha256": sha256_bytes(stdout),
            "stdout_bytes": len(stdout),
            "stderr_sha256": sha256_bytes(stderr),
            "stderr_bytes": len(stderr),
            "stored": False,
        },
        "git": {
            "before": before,
            "after": after,
            "head_unchanged": before.get("head") == after.get("head"),
        },
        "runtime": {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "python": platform.python_version(),
        },
        "privacy": {
            "raw_output_stored": False,
            "command_redaction": "best-effort",
            "environment_stored": False,
        },
    }
    payload["integrity"] = {
        "algorithm": "sha256",
        "digest": receipt_digest(payload),
        "scope": "all fields except integrity",
    }
    if receipt_dir is None:
        git_path = Path(git_text(root, "rev-parse", "--git-path", "maintainer-mode/receipts"))
        directory = git_path if git_path.is_absolute() else root / git_path
    else:
        directory = receipt_dir
    target = write_receipt(directory, payload)
    return return_code, target, stdout, stderr


def load_receipt(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        receipt = json.load(handle)
    if not isinstance(receipt, dict):
        raise ValueError(f"Receipt is not a JSON object: {path}")
    return receipt


def verify_receipt(receipt: dict[str, Any]) -> tuple[bool, str]:
    if receipt.get("schema") != SCHEMA:
        return False, f"Unsupported schema: {receipt.get('schema')!r}"
    integrity = receipt.get("integrity")
    if not isinstance(integrity, dict) or integrity.get("algorithm") != "sha256":
        return False, "Missing SHA-256 integrity record"
    unsigned = dict(receipt)
    unsigned.pop("integrity", None)
    expected = receipt_digest(unsigned)
    actual = integrity.get("digest")
    if not isinstance(actual, str) or not __import__("hmac").compare_digest(expected, actual):
        return False, "Integrity digest does not match receipt contents"
    return True, "Receipt integrity is valid"


def collect_receipts(directory: Path) -> list[tuple[Path, dict[str, Any]]]:
    return [(path, load_receipt(path)) for path in sorted(directory.glob("*.json"))]


def build_report(
    receipts: list[tuple[Path, dict[str, Any]]],
    required: Sequence[str],
) -> tuple[str, bool]:
    by_label: dict[str, list[tuple[Path, dict[str, Any], bool, str]]] = {}
    for path, receipt in receipts:
        valid, message = verify_receipt(receipt)
        label = str((receipt.get("check") or {}).get("label", "unlabelled"))
        by_label.setdefault(label, []).append((path, receipt, valid, message))

    required = list(dict.fromkeys(required))
    missing = [label for label in required if label not in by_label]
    failed: list[str] = []
    invalid: list[str] = []
    selected: list[tuple[str, Path, dict[str, Any], bool, str]] = []
    for label in required:
        entries = by_label.get(label)
        if not entries:
            continue
        path, receipt, valid, message = entries[-1]
        selected.append((label, path, receipt, valid, message))
        if not valid:
            invalid.append(label)
        elif not bool((receipt.get("check") or {}).get("passed")):
            failed.append(label)

    fingerprints = {
        (
            str((((receipt.get("git") or {}).get("after") or {}).get("head") or "")),
            str((((receipt.get("git") or {}).get("after") or {}).get("worktree_sha256") or "")),
        )
        for _, _, receipt, valid, _ in selected
        if valid
    }
    inconsistent_tree = len(fingerprints) > 1
    proven = not missing and not failed and not invalid and not inconsistent_tree and bool(required)
    verdict = "PROVEN" if proven else "NOT PROVEN"
    lines = [
        f"# PR evidence: {verdict}",
        "",
        "This report is derived from local command receipts. It is not CI or maintainer approval.",
        "",
        "| Check | Result | Exit | Receipt integrity | Git head |",
        "|---|---:|---:|---:|---|",
    ]
    for label, path, receipt, valid, _ in selected:
        check = receipt.get("check") or {}
        git = receipt.get("git") or {}
        after = git.get("after") or {}
        result = "PASS" if check.get("passed") else "FAIL"
        lines.append(
            f"| `{label}` | {result} | {check.get('exit_code', '?')} | "
            f"{'valid' if valid else 'INVALID'} | `{str(after.get('head') or 'unknown')[:12]}` |"
        )
    lines.extend(["", "## Claim boundary", ""])
    if missing:
        lines.append(f"- Missing required receipt(s): {', '.join(f'`{item}`' for item in missing)}")
    if failed:
        lines.append(f"- Latest failed receipt(s): {', '.join(f'`{item}`' for item in failed)}")
    if invalid:
        lines.append(f"- Invalid receipt integrity: {', '.join(f'`{item}`' for item in invalid)}")
    if inconsistent_tree:
        lines.append("- Required receipts describe different commits or worktree contents; rerun them on one exact tree.")
    if proven:
        lines.append("- Every required label has a latest passing, integrity-valid receipt.")
    if not required:
        lines.append("- No required checks were declared, so readiness cannot be proven.")
    lines.extend(
        [
            "- Raw stdout and stderr are not stored; receipts contain only hashes and byte counts.",
            "- SHA-256 detects edits but is not a signature and does not establish who ran a command.",
            "",
        ]
    )
    return "\n".join(lines), proven
