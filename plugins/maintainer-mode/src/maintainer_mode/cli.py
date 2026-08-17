from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from . import __version__
from .doctor import inspect_repository, render_doctor_markdown
from .evidence import build_report, collect_receipts, load_receipt, run_and_record, verify_receipt
from .git import GitError
from .github import capture_snapshot
from .policy import ContributionPolicy, evaluate_gate, load_json, render_gate_markdown


def json_text(value: object) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def write_text(value: str, output: Path | None) -> None:
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(value, encoding="utf-8")
        print(output)
    else:
        sys.stdout.write(value)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="maintainer-mode",
        description="Evidence-first guardrails for open-source contributions.",
    )
    root.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = root.add_subparsers(dest="command", required=True)

    doctor = commands.add_parser("doctor", help="Inspect a local repository without changing it")
    doctor.add_argument("repo", type=Path, nargs="?", default=Path.cwd())
    doctor.add_argument("--format", choices=("markdown", "json"), default="markdown")
    doctor.add_argument("--output", type=Path)

    snapshot = commands.add_parser("snapshot", help="Capture read-only live GitHub issue state")
    snapshot.add_argument("--repo", required=True, help="GitHub OWNER/REPO")
    snapshot.add_argument("--issue", required=True, type=int)
    snapshot.add_argument("--actor", help="Contributor login; defaults to authenticated gh user")
    snapshot.add_argument("--output", type=Path)

    gate = commands.add_parser("gate", help="Evaluate a snapshot against explicit policy")
    gate.add_argument("--snapshot", type=Path, required=True)
    gate.add_argument("--policy", type=Path)
    gate.add_argument("--format", choices=("markdown", "json"), default="markdown")
    gate.add_argument("--output", type=Path)

    record = commands.add_parser("run", help="Run a check and write a privacy-preserving receipt")
    record.add_argument("--repo", type=Path, default=Path.cwd())
    record.add_argument("--label", required=True, help="Stable claim label, such as unit-tests")
    record.add_argument("--receipt-dir", type=Path)
    record.add_argument("argv", nargs=argparse.REMAINDER, help="Command after --")

    verify = commands.add_parser("verify", help="Verify a receipt's content digest")
    verify.add_argument("receipt", type=Path)
    verify.add_argument("--format", choices=("text", "json"), default="text")

    report = commands.add_parser("report", help="Build an honest PR evidence report")
    report.add_argument("--receipts", type=Path, required=True)
    report.add_argument("--policy", type=Path, help="Use required_checks from policy")
    report.add_argument("--require", action="append", default=[], help="Required label; repeat as needed")
    report.add_argument("--output", type=Path)
    return root


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "doctor":
            report = inspect_repository(args.repo)
            value = json_text(report) if args.format == "json" else render_doctor_markdown(report)
            write_text(value, args.output)
            return 0

        if args.command == "snapshot":
            data = capture_snapshot(args.repo, args.issue, args.actor)
            write_text(json_text(data), args.output)
            return 0

        if args.command == "gate":
            snapshot = load_json(args.snapshot)
            policy = ContributionPolicy.from_dict(load_json(args.policy)) if args.policy else ContributionPolicy()
            result = evaluate_gate(snapshot, policy)
            value = json_text(result.to_dict()) if args.format == "json" else render_gate_markdown(result, snapshot)
            write_text(value, args.output)
            return int(result.decision)

        if args.command == "run":
            command = list(args.argv)
            if command and command[0] == "--":
                command = command[1:]
            code, receipt, stdout, stderr = run_and_record(
                args.repo,
                args.label,
                command,
                receipt_dir=args.receipt_dir,
            )
            sys.stdout.buffer.write(stdout)
            sys.stdout.buffer.flush()
            sys.stderr.buffer.write(stderr)
            sys.stderr.buffer.flush()
            print(f"maintainer-mode receipt: {receipt}", file=sys.stderr)
            return code

        if args.command == "verify":
            valid, message = verify_receipt(load_receipt(args.receipt))
            if args.format == "json":
                sys.stdout.write(json_text({"valid": valid, "message": message, "receipt": str(args.receipt)}))
            else:
                print(f"{'VALID' if valid else 'INVALID'}: {message}")
            return 0 if valid else 2

        if args.command == "report":
            receipts = collect_receipts(args.receipts)
            required = list(args.require)
            if args.policy:
                policy = ContributionPolicy.from_dict(load_json(args.policy))
                required.extend(policy.required_checks)
            content, proven = build_report(receipts, required)
            write_text(content, args.output)
            return 0 if proven else 2
    except (GitError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"maintainer-mode: {exc}", file=sys.stderr)
        return 2
    return 2
