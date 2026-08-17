from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins" / "maintainer-mode" / "src"))

from maintainer_mode.evidence import (  # noqa: E402
    build_report,
    collect_receipts,
    load_receipt,
    redact_argv,
    run_and_record,
    verify_receipt,
)


class EvidenceTests(unittest.TestCase):
    def make_repo(self, base: Path) -> Path:
        repo = base / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
        (repo / "README.md").write_text("fixture\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=repo, check=True)
        return repo

    def test_run_records_hashes_without_raw_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            repo = self.make_repo(base)
            receipts = base / "receipts"
            code, path, stdout, _ = run_and_record(
                repo,
                "unit-tests",
                [
                    sys.executable,
                    "-c",
                    "print(bytes([115,101,110,115,105,116,105,118,101,45,105,115,104]).decode())",
                ],
                receipt_dir=receipts,
            )
            self.assertEqual(code, 0)
            self.assertIn(b"sensitive-ish", stdout)
            receipt = load_receipt(path)
            self.assertFalse(receipt["output"]["stored"])
            self.assertNotIn("sensitive-ish", path.read_text(encoding="utf-8"))
            self.assertEqual(verify_receipt(receipt), (True, "Receipt integrity is valid"))

    def test_editing_receipt_invalidates_integrity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            repo = self.make_repo(base)
            _, path, _, _ = run_and_record(
                repo,
                "lint",
                [sys.executable, "-c", "raise SystemExit(0)"],
                receipt_dir=base / "receipts",
            )
            receipt = load_receipt(path)
            receipt["check"]["exit_code"] = 9
            valid, message = verify_receipt(receipt)
            self.assertFalse(valid)
            self.assertIn("does not match", message)

    def test_report_requires_every_declared_check(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            repo = self.make_repo(base)
            receipts = base / "receipts"
            run_and_record(
                repo,
                "unit-tests",
                [sys.executable, "-c", "raise SystemExit(0)"],
                receipt_dir=receipts,
            )
            report, proven = build_report(collect_receipts(receipts), ["unit-tests", "lint"])
            self.assertFalse(proven)
            self.assertIn("Missing required receipt(s): `lint`", report)
            report, proven = build_report(collect_receipts(receipts), ["unit-tests"])
            self.assertTrue(proven)
            self.assertIn("PR evidence: PROVEN", report)

    def test_report_rejects_receipts_from_different_worktrees(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            repo = self.make_repo(base)
            receipts = base / "receipts"
            run_and_record(
                repo,
                "unit-tests",
                [sys.executable, "-c", "raise SystemExit(0)"],
                receipt_dir=receipts,
            )
            (repo / "README.md").write_text("changed\n", encoding="utf-8")
            run_and_record(
                repo,
                "lint",
                [sys.executable, "-c", "raise SystemExit(0)"],
                receipt_dir=receipts,
            )
            report, proven = build_report(collect_receipts(receipts), ["unit-tests", "lint"])
            self.assertFalse(proven)
            self.assertIn("different commits or worktree contents", report)

    def test_secret_shaped_arguments_are_redacted(self) -> None:
        redacted = redact_argv(["tool", "--token", "ghp_abcdefghijklmnopqrstuvwxyz", "API_KEY=sk-abcdefghijklmnop"])
        self.assertEqual(redacted[2], "[REDACTED]")
        self.assertEqual(redacted[3], "API_KEY=[REDACTED]")


if __name__ == "__main__":
    unittest.main()
