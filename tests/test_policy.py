from __future__ import annotations

import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins" / "maintainer-mode" / "src"))

from maintainer_mode.models import Decision  # noqa: E402
from maintainer_mode.policy import ContributionPolicy, evaluate_gate, render_gate_markdown  # noqa: E402


FIXTURES = ROOT / "tests" / "fixtures"
NOW = datetime(2026, 8, 16, 13, 0, tzinfo=timezone.utc)


def fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class PolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = ContributionPolicy.from_dict(fixture("policy.json"))

    def test_ready_issue_passes_all_configured_gates(self) -> None:
        result = evaluate_gate(fixture("issue-ready.json"), self.policy, now=NOW)
        self.assertEqual(result.decision, Decision.READY)
        self.assertEqual([item.code for item in result.findings], ["gate.ready"])

    def test_blocked_self_filed_assigned_issue_stops_and_explains_all_risks(self) -> None:
        result = evaluate_gate(fixture("issue-risky.json"), self.policy, now=NOW)
        codes = {item.code for item in result.findings}
        self.assertEqual(result.decision, Decision.STOP)
        self.assertIn("issue.blocked-label", codes)
        self.assertIn("issue.acceptance-required", codes)
        self.assertIn("duplicate.candidate-pr", codes)
        self.assertIn("issue.assigned-to-other", codes)

    def test_candidate_duplicate_requires_human_inspection_instead_of_false_stop(self) -> None:
        data = fixture("issue-ready.json")
        data["candidate_pull_requests"] = [{"number": 77, "state": "OPEN"}]
        result = evaluate_gate(data, self.policy, now=NOW)
        self.assertEqual(result.decision, Decision.ASK)
        self.assertIn("duplicate.candidate-pr", {item.code for item in result.findings})

    def test_stale_snapshot_is_ask(self) -> None:
        data = fixture("issue-ready.json")
        data["captured_at"] = (NOW - timedelta(hours=25)).isoformat()
        result = evaluate_gate(data, self.policy, now=NOW)
        self.assertEqual(result.decision, Decision.ASK)
        self.assertIn("snapshot.stale", {item.code for item in result.findings})

    def test_unknown_policy_key_fails_fast(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown policy keys"):
            ContributionPolicy.from_dict({"version": 1, "magic": True})

    def test_string_author_and_assignee_shapes_are_supported(self) -> None:
        data = fixture("issue-ready.json")
        data["issue"]["author"] = "maintainer"
        data["issue"]["assignees"] = ["contributor"]
        result = evaluate_gate(data, self.policy, now=NOW)
        self.assertEqual(result.decision, Decision.READY)

    def test_unknown_snapshot_schema_stops_evaluation_claim(self) -> None:
        data = fixture("issue-ready.json")
        data["schema"] = "maintainer-mode.snapshot/v9"
        result = evaluate_gate(data, self.policy, now=NOW)
        self.assertEqual(result.decision, Decision.STOP)
        self.assertIn("snapshot.schema-unsupported", {item.code for item in result.findings})

    def test_markdown_has_explicit_claim_boundary(self) -> None:
        data = fixture("issue-ready.json")
        rendered = render_gate_markdown(evaluate_gate(data, self.policy, now=NOW), data)
        self.assertIn("Contribution gate: READY", rendered)
        self.assertIn("not maintainer approval", rendered)


if __name__ == "__main__":
    unittest.main()
