#!/usr/bin/env python3
"""Build project-level voice separation notes from character cards."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def character_name(text: str, fallback: str) -> str:
    match = re.search(r"^display_name:\s*(.+)$", text, re.M)
    return match.group(1).strip() if match else fallback


def main() -> int:
    parser = argparse.ArgumentParser(description="Build voice separation for project simulation")
    parser.add_argument("--project", required=True, help="Project pack directory")
    parser.add_argument("--out", default="", help="Output simulation directory")
    args = parser.parse_args()
    project = Path(args.project)
    out = Path(args.out) if args.out else project / "simulation"
    out.mkdir(parents=True, exist_ok=True)
    cards = list((project / "characters").glob("*/CHARACTER.md"))
    rows = []
    for card in cards:
        text = card.read_text(encoding="utf-8", errors="replace")
        name = character_name(text, card.parent.name)
        rows.append({
            "character": name,
            "sentence_length": "short-medium",
            "interrupt_tendency": "medium",
            "silence_tendency": "medium",
            "emotional_visibility": "medium",
            "address_style": "use CHARACTER.md expression DNA",
            "conflict_response": "use dialogue state machine",
        })
    (out / "speaker-scheduler.json").write_text(json.dumps({"characters": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# Voice Separation", "", "| Character | Sentence | Interrupt | Silence | Emotion | Conflict |", "|---|---|---|---|---|---|"]
    for row in rows:
        lines.append(f"| {row['character']} | {row['sentence_length']} | {row['interrupt_tendency']} | {row['silence_tendency']} | {row['emotional_visibility']} | {row['conflict_response']} |")
    if not rows:
        lines.append("| insufficient characters |  |  |  |  |  |")
    (out / "voice-separation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out / 'voice-separation.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
