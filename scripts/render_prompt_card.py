#!/usr/bin/env python3
"""Render a compact low-token prompt-card.md from CHARACTER.md."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"---\n(.*?)\n---", text, re.S)
    data: dict[str, str] = {}
    if match:
        for line in match.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                data[k.strip()] = v.strip()
    return data


def section(text: str, number: int) -> str:
    match = re.search(rf"^##\s+{number}\.\s+.*$", text, re.M)
    if not match:
        return ""
    rest = text[match.end():]
    nxt = re.search(r"^##\s+\d+\.\s+", rest, re.M)
    return rest[:nxt.start()] if nxt else rest


def first_bullets(block: str, limit: int) -> list[str]:
    rows = [line.strip("- ").strip() for line in block.splitlines() if line.strip().startswith("- ")]
    return rows[:limit]


def main() -> int:
    parser = argparse.ArgumentParser(description="Render compact prompt-card.md")
    parser.add_argument("--character", required=True, help="CHARACTER.md path")
    parser.add_argument("--runtime", default="", help="runtime-profile.json")
    parser.add_argument("--out", required=True, help="Output prompt-card.md")
    args = parser.parse_args()
    text = Path(args.character).read_text(encoding="utf-8", errors="replace")
    meta = frontmatter(text)
    runtime = {}
    if args.runtime and Path(args.runtime).exists():
        runtime = json.loads(Path(args.runtime).read_text(encoding="utf-8-sig"))
    examples = runtime.get("interaction", {}).get("example_dialogues", [])[:3]
    lines = [
        f"# {meta.get('display_name', meta.get('name', 'Character'))} Prompt Card",
        "",
        f"- Identity: {meta.get('display_name', meta.get('name', 'Character'))} from {meta.get('source_work', 'unspecified')}.",
        f"- Language: {meta.get('response_language', 'match-user')}; Chinese user input gets Chinese main replies.",
        f"- Safety boundary: {meta.get('safety_boundary', 'enabled')}.",
        "",
        "## Core Rules",
        "",
        "- Reply as the character, not as a profile narrator.",
        "- Dialogue first, short action beats second.",
        "- Do not proactively introduce relationship characters unless the user mentions them.",
        "- Do not self-identify as AI/model/code unless the persona is explicitly meta.",
        "- Keep intimacy and conflict gradual.",
        "",
        "## Personality",
        "",
    ]
    lines.extend(f"- {x}" for x in first_bullets(section(text, 4), 5)) or lines.append("- See CHARACTER.md personality chassis.")
    lines.extend(["", "## Voice", ""])
    lines.extend(f"- {x}" for x in first_bullets(section(text, 5), 5)) or lines.append("- See CHARACTER.md expression DNA.")
    lines.extend(["", "## Reply Format", "", "Use `immersive_default`: short action, character dialogue, optional small after-beat.", "", "## Examples", ""])
    if examples:
        lines.extend(f"### {item.get('type','example')}\n\n{item.get('dialogue','')}\n" for item in examples)
    else:
        lines.append("- See CHARACTER.md section 25.")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
