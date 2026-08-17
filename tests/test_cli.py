from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins" / "maintainer-mode" / "src"))

from maintainer_mode.cli import main  # noqa: E402


class CliTests(unittest.TestCase):
    def test_gate_json_returns_ready_exit_code(self) -> None:
        snapshot = json.loads(
            (ROOT / "tests" / "fixtures" / "issue-ready.json").read_text(encoding="utf-8")
        )
        snapshot["captured_at"] = datetime.now(timezone.utc).isoformat()
        with tempfile.TemporaryDirectory() as directory:
            snapshot_path = Path(directory) / "snapshot.json"
            snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(
                    [
                        "gate",
                        "--snapshot",
                        str(snapshot_path),
                        "--policy",
                        str(ROOT / "tests" / "fixtures" / "policy.json"),
                        "--format",
                        "json",
                    ]
                )
        self.assertEqual(code, 0)
        self.assertIn('"decision": "READY"', output.getvalue())

    def test_verify_rejects_non_receipt(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(["verify", str(ROOT / "tests" / "fixtures" / "policy.json")])
        self.assertEqual(code, 2)
        self.assertIn("INVALID", output.getvalue())


if __name__ == "__main__":
    unittest.main()
