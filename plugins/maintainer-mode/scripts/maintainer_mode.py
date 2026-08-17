#!/usr/bin/env python3
"""Run Maintainer Mode directly from an installed plugin bundle."""

from __future__ import annotations

import sys
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT / "src"))

from maintainer_mode.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
