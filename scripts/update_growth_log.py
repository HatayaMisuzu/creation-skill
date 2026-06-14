#!/usr/bin/env python3
"""Append a durable growth-log entry for a character directory."""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Append character growth log")
    parser.add_argument("--character-dir", required=True, help="character-cards/<id> directory")
    parser.add_argument("--event", default="update", help="Event label")
    parser.add_argument("--note", default="", help="Optional note")
    args = parser.parse_args()
    root = Path(args.character_dir)
    root.mkdir(parents=True, exist_ok=True)
    path = root / "growth-log.md"
    if not path.exists():
        path.write_text("# Growth Log\n\n", encoding="utf-8")
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"## {stamp} {args.event}\n\n")
        handle.write(f"- Note: {args.note or 'no note supplied'}\n")
        for name in ["voice-fingerprint.json", "phases.json", "prompt-card.md", "continuous-update-report.md"]:
            handle.write(f"- {name}: {'present' if (root / name).exists() else 'missing'}\n")
        handle.write("\n")
    print(f"Updated {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
