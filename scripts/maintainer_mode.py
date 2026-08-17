#!/usr/bin/env python3
"""Run Maintainer Mode from a source checkout without installing it."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "plugins" / "maintainer-mode" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from maintainer_mode.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
