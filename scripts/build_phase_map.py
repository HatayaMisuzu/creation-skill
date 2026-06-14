#!/usr/bin/env python3
"""Build phases.json and phase-map.md from evidence phase labels."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Build phase map")
    parser.add_argument("--character", required=True, help="CHARACTER.md path")
    parser.add_argument("--evidence", required=True, help="evidence.json path")
    parser.add_argument("--out", required=True, help="Output character directory")
    args = parser.parse_args()
    text = Path(args.character).read_text(encoding="utf-8", errors="replace")
    fm = frontmatter(text)
    data = json.loads(Path(args.evidence).read_text(encoding="utf-8-sig"))
    evidence = data.get("evidence", []) if isinstance(data, dict) else data
    grouped: dict[str, list[dict]] = defaultdict(list)
    for item in evidence:
        grouped[item.get("phase") or fm.get("default_phase") or "main"].append(item)
    default_phase = fm.get("default_phase", "main")
    phases = {}
    for phase, items in grouped.items():
        summaries = " / ".join(str(item.get("summary", ""))[:80] for item in items[:3])
        phases[phase] = {
            "tone": "derived from evidence",
            "trust_baseline": 40,
            "motivation": summaries or "insufficient source evidence",
            "knowledge_scope": f"{phase} evidence scope",
            "relationship_defaults": {},
            "evidence_count": len(items),
        }
    if default_phase not in phases:
        phases[default_phase] = {"tone": "default", "trust_baseline": 40, "motivation": "default phase", "knowledge_scope": "default", "relationship_defaults": {}, "evidence_count": 0}
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    payload = {"default_phase": default_phase, "phases": phases}
    (out / "phases.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# Phase Map", "", f"Default phase: `{default_phase}`", "", "| Phase | Evidence | Motivation/Notes |", "|---|---:|---|"]
    for phase, info in phases.items():
        lines.append(f"| {phase} | {info['evidence_count']} | {str(info['motivation']).replace('|','/')} |")
    (out / "phase-map.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out / 'phases.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
