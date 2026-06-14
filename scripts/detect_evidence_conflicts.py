#!/usr/bin/env python3
"""Detect conservative evidence conflicts against an existing character card."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def load_evidence(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return list(data.get("evidence", []) if isinstance(data, dict) else data)


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect evidence conflicts")
    parser.add_argument("--character", required=True, help="CHARACTER.md path")
    parser.add_argument("--evidence", required=True, help="evidence.json path")
    parser.add_argument("--out", required=True, help="Output evidence directory")
    args = parser.parse_args()
    card_text = Path(args.character).read_text(encoding="utf-8", errors="replace")
    conflicts: list[dict] = []
    for item in load_evidence(Path(args.evidence)):
        layer = item.get("layer", "")
        summary = str(item.get("summary", ""))
        dims = item.get("dimensions", [])
        phase = item.get("phase", "unknown")
        if layer in {"secondary", "fan-analysis"} and "user-provided" in card_text and any(dim in dims for dim in ["identity", "relationship", "personality"]):
            conflicts.append({"type": "user-provided-vs-lower-layer", "summary": summary, "layer": layer, "phase": phase, "recommendation": "do not overwrite user-provided settings without confirmation"})
        if layer == "fan-analysis" and any(term in summary.lower() for term in ["canon", "official", "confirmed"]):
            conflicts.append({"type": "fan-analysis-overclaim", "summary": summary, "layer": layer, "phase": phase, "recommendation": "downgrade to interpretation unless sourced"})
        if phase not in {"", "unknown", "default", "main"} and "default_phase" in card_text:
            conflicts.append({"type": "phase-version-signal", "summary": summary, "layer": layer, "phase": phase, "recommendation": "route into phases.json instead of overwriting default phase"})
        if re.search(r"恋人|情侣|已交往|lover", summary, re.I) and "熟悉但不亲密" in card_text:
            conflicts.append({"type": "relationship-default-risk", "summary": summary, "layer": layer, "phase": phase, "recommendation": "keep as optional relationship unless user confirms default romance"})
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "conflicts.json").write_text(json.dumps(conflicts, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# Evidence Conflicts", "", "| Type | Layer | Phase | Summary | Recommendation |", "|---|---|---|---|---|"]
    for c in conflicts:
        lines.append(f"| {c['type']} | {c['layer']} | {c['phase']} | {c['summary'].replace('|','/')} | {c['recommendation']} |")
    if not conflicts:
        lines.append("| none |  |  | no obvious conflicts detected |  |")
    (out_dir / "conflicts.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out_dir / 'conflicts.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
