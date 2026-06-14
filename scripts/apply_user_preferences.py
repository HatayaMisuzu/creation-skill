#!/usr/bin/env python3
"""Apply a user preference profile as a runtime overlay without changing canon."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def load_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected object JSON: {path}")
    return data


def frontmatter(text: str) -> dict:
    match = re.match(r"---\n(.*?)\n---\n", text, re.S)
    data: dict[str, str] = {}
    if not match:
        return data
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()
    return data


def build_runtime_overlay(meta: dict, prefs: dict) -> dict:
    return {
        "character": {
            "name": meta.get("name", "unknown"),
            "display_name": meta.get("display_name", meta.get("name", "unknown")),
        },
        "preference_overlay": prefs,
        "rules": [
            "Do not rewrite canon facts from user preferences.",
            "Preferences only affect response language, pacing, narration density, intimacy speed, and visible format.",
            "Project simulation visibility must remain frontstage-only unless the user explicitly asks for debug output.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a runtime preference overlay")
    parser.add_argument("--preferences", required=True, help="user-preferences.json path")
    parser.add_argument("--character", required=True, help="CHARACTER.md path")
    parser.add_argument("--out", required=True, help="Output directory")
    args = parser.parse_args()

    prefs = load_json(Path(args.preferences))
    text = Path(args.character).read_text(encoding="utf-8", errors="replace")
    meta = frontmatter(text)
    overlay = build_runtime_overlay(meta, prefs)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "applied-preferences.json").write_text(json.dumps(overlay, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Preference Overlay",
        "",
        f"Character: {overlay['character']['display_name']}",
        "",
        "## Active Preferences",
        "",
        "| Key | Value |",
        "|---|---|",
    ]
    for key, value in prefs.items():
        lines.append(f"| {key} | {str(value).replace('|', '/')} |")
    lines.extend(
        [
            "",
            "## Guardrails",
            "",
            "- This overlay must not change canon facts, source layers, or relationship defaults.",
            "- It may change output language, pacing, narration density, intimacy speed, and visible response format.",
            "- Background simulation state remains hidden in normal immersive output.",
        ]
    )
    (out_dir / "preference-applied.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out_dir / 'applied-preferences.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
