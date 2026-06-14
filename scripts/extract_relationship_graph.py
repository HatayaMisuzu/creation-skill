#!/usr/bin/env python3
"""Extract a relationship graph from one or more evidence packs."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def load_evidence(paths: list[str]) -> list[dict]:
    items: list[dict] = []
    for path in paths:
        data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
        items.extend(data.get("evidence", []) if isinstance(data, dict) else data)
    return items


def relation_type(text: str) -> str:
    if re.search(r"朋友|同伴|伙伴|搭档|friend|unit|ユニット", text, re.I):
        return "friend_or_partner"
    if re.search(r"竞争|对手|敌|rival|ライバル", text, re.I):
        return "rival"
    if re.search(r"制作人|producer|先輩|前辈", text, re.I):
        return "producer_or_mentor"
    return "relationship_signal"


def build_graph(evidence: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for item in evidence:
        if "relationship" not in item.get("dimensions", []) and "relationship" not in item.get("used_for", []):
            continue
        target = item.get("speaker_name") or "unknown"
        rows.append({
            "target": target,
            "relationship": relation_type(item.get("summary", "")),
            "attitude": item.get("summary", ""),
            "source": item.get("source", ""),
            "layer": item.get("layer", ""),
            "speaker": item.get("speaker", ""),
            "invocation_rule": "internal only; use only when the user mentions this person or the scene explicitly requires it",
        })
    return rows


def write_md(path: Path, rows: list[dict]) -> None:
    lines = [
        "# Relationship Graph",
        "",
        "Relationships are internal context. Do not proactively introduce these people in character dialogue.",
        "",
        "| Target | Relationship | Speaker | Attitude/Evidence | Source | Invocation |",
        "|---|---|---|---|---|---|",
    ]
    for row in rows:
        safe = {k: str(v).replace("|", "/").replace("\n", " ") for k, v in row.items()}
        lines.append(f"| {safe['target']} | {safe['relationship']} | {safe['speaker']} | {safe['attitude']} | {safe['source']} | {safe['invocation_rule']} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract relationship graph from evidence")
    parser.add_argument("--evidence", action="append", required=True, help="evidence.json path, repeatable")
    parser.add_argument("--out", required=True, help="Output directory")
    args = parser.parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = build_graph(load_evidence(args.evidence))
    (out_dir / "relationship-graph.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    write_md(out_dir / "relationship-graph.md", rows)
    print(f"Wrote {out_dir / 'relationship-graph.json'}")
    print(f"Wrote {out_dir / 'relationship-graph.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
