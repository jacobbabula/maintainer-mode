#!/usr/bin/env python3
"""Run a disposable, network-free Maintainer Mode demonstration."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "plugins" / "maintainer-mode"
sys.path.insert(0, str(PLUGIN_ROOT / "src"))

from maintainer_mode.evidence import build_report, collect_receipts, run_and_record  # noqa: E402
from maintainer_mode.policy import ContributionPolicy, evaluate_gate, render_gate_markdown  # noqa: E402


def run(*argv: str, cwd: Path) -> None:
    subprocess.run(list(argv), cwd=cwd, check=True, capture_output=True)


def main() -> int:
    fixtures = ROOT / "tests" / "fixtures"
    snapshot = json.loads((fixtures / "issue-ready.json").read_text(encoding="utf-8"))
    policy = ContributionPolicy.from_dict(
        json.loads((fixtures / "policy.json").read_text(encoding="utf-8"))
    )
    now = datetime.now(timezone.utc)
    print("MAINTAINER MODE / 30-SECOND PROOF")
    print("=================================")

    print("\n[1/3] Stale issue state")
    snapshot["captured_at"] = (now - timedelta(hours=49)).isoformat()
    print(render_gate_markdown(evaluate_gate(snapshot, policy, now=now), snapshot))

    print("[2/3] Fresh, accepted task")
    snapshot["captured_at"] = now.isoformat()
    print(render_gate_markdown(evaluate_gate(snapshot, policy, now=now), snapshot))

    print("[3/3] Checks bound to one exact tree")

    with tempfile.TemporaryDirectory(prefix="maintainer-mode-demo-") as directory:
        repo = Path(directory) / "sample-project"
        receipts = Path(directory) / "receipts"
        repo.mkdir()
        run("git", "init", "-q", cwd=repo)
        run("git", "config", "user.email", "demo@example.invalid", cwd=repo)
        run("git", "config", "user.name", "Maintainer Mode Demo", cwd=repo)
        (repo / "answer.py").write_text("def answer():\n    return 42\n", encoding="utf-8")
        run("git", "add", "answer.py", cwd=repo)
        run("git", "commit", "-qm", "demo fixture", cwd=repo)

        checks = {
            "unit-tests": [sys.executable, "-c", "from answer import answer; assert answer() == 42"],
            "lint": [
                sys.executable,
                "-c",
                "import ast,pathlib; ast.parse(pathlib.Path('answer.py').read_text())",
            ],
        }
        for label, command in checks.items():
            code, path, _, _ = run_and_record(repo, label, command, receipt_dir=receipts)
            status = "PASS" if code == 0 else "FAIL"
            print(f"  {status}  {label:<12} receipt={path.name}")

        report, proven = build_report(collect_receipts(receipts), list(checks))
        print("\n" + report)
        return 0 if proven else 2


if __name__ == "__main__":
    raise SystemExit(main())
