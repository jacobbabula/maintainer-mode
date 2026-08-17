#!/usr/bin/env python3
"""Render a 30-second GIF from the real disposable demo output."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError as exc:  # pragma: no cover - release tooling only
    raise SystemExit("Install Pillow to render the demo: python -m pip install Pillow") from exc


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets" / "demo.gif"
WIDTH, HEIGHT = 1200, 675
BACKGROUND = "#0B1220"
PANEL = "#111827"
MUTED = "#93A3BA"
WHITE = "#F8FAFC"
AMBER = "#F7B84B"
GREEN = "#55D6A8"
BLUE = "#76C7FF"
RED = "#FF8B8B"


def font(size: int, *, bold: bool = False):
    candidates = [
        Path("C:/Windows/Fonts/CascadiaMono.ttf"),
        Path("C:/Windows/Fonts/consolab.ttf" if bold else "C:/Windows/Fonts/consola.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default(size=size)


REGULAR = font(24)
SMALL = font(19)
BOLD = font(25, bold=True)
TITLE = font(30, bold=True)


def colorize(line: str) -> str:
    if "ASK" in line or "stale" in line.lower():
        return AMBER
    if "READY" in line or line.lstrip().startswith("PASS"):
        return GREEN
    if "PROVEN" in line:
        return BLUE
    if "FAIL" in line or "STOP" in line:
        return RED
    if line.startswith("#") or line.startswith("["):
        return WHITE
    return MUTED


def frame(lines: list[str], *, step: str, cursor: bool = False) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((36, 30, WIDTH - 36, HEIGHT - 30), radius=18, fill=PANEL, outline="#2D3A52", width=2)
    draw.rectangle((36, 30, WIDTH - 36, 91), fill="#172033")
    for x, fill in ((66, "#FF6B6B"), (94, AMBER), (122, GREEN)):
        draw.ellipse((x - 8, 53, x + 8, 69), fill=fill)
    draw.text((158, 48), "maintainer-mode / disposable proof", font=SMALL, fill=MUTED)
    draw.text((WIDTH - 68, 48), step, font=SMALL, fill=AMBER, anchor="ra")

    y = 124
    for line in lines:
        active_font = BOLD if line.startswith(("$", "#", "[")) or "PROVEN" in line else REGULAR
        draw.text((72, y), line, font=active_font, fill=colorize(line))
        y += 39
    if cursor:
        draw.rectangle((72, y + 2, 87, y + 31), fill=AMBER)
    draw.text((72, HEIGHT - 67), "No invented certainty.", font=SMALL, fill="#66758E")
    return image


def main() -> int:
    run = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "demo.py")],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    for required in ("Contribution gate: ASK", "Contribution gate: READY", "PR evidence: PROVEN"):
        if required not in run.stdout:
            raise SystemExit(f"Demo output is missing required proof: {required}")

    scenes = [
        (["$ python scripts/demo.py"], "START", True, 2200),
        (["$ python scripts/demo.py", "", "[1/3] Stale issue state"], "1 / 3", True, 1800),
        (["[1/3] Stale issue state", "# Contribution gate: ASK", "", "ASK / snapshot.stale", "Snapshot is 49.0 hours old."], "1 / 3", False, 4300),
        (["# Contribution gate: ASK", "", "The issue may have changed.", "Refresh before writing code."], "BLOCKED", False, 2600),
        (["[2/3] Fresh, accepted task", "# Contribution gate: READY", "", "PASS / gate.ready", "No configured policy gate blocks implementation."], "2 / 3", False, 4300),
        (["[3/3] Checks bound to one exact tree", "", "PASS  unit-tests", "PASS  lint"], "3 / 3", True, 3300),
        (["[3/3] Checks bound to one exact tree", "", "PASS  unit-tests", "PASS  lint", "", "# PR evidence: PROVEN"], "PROOF", False, 4700),
        (["# PR evidence: PROVEN", "", "Every required check passed.", "Every receipt matches one Git tree.", "Receipt integrity: valid", "", "Local evidence is not CI or maintainer approval."], "DONE", False, 6800),
    ]
    frames = [frame(lines, step=step, cursor=cursor) for lines, step, cursor, _ in scenes]
    durations = [duration for _, _, _, duration in scenes]
    frames[0].save(
        OUTPUT,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
        disposal=2,
    )
    print(f"Rendered {sum(durations) / 1000:.1f}s demo to {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
