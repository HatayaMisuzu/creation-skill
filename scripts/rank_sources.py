#!/usr/bin/env python3
"""Rank source candidates and produce a user-review manifest."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


DISCOVERY_ONLY = {"manual-search", "youtube-channel", "youtube-playlist"}


def score(row: dict) -> tuple[int, list[str]]:
    text = " ".join(str(row.get(k, "")) for k in ["title", "url", "source_type", "suggested_layer", "likely_value"]).lower()
    points = 0
    reasons: list[str] = []
    source_type = row.get("source_type", "")

    if source_type not in DISCOVERY_ONLY and row.get("suggested_layer") in {"official", "canon", "transcript"}:
        points += 40
        reasons.append("primary-or-near-primary")
    if any(x in text for x in ["official", "公式", "character", "chara"]):
        points += 20
        reasons.append("official-profile-signal")
    if source_type in DISCOVERY_ONLY:
        points -= 18
        reasons.append("discovery-entry-not-evidence")
    if source_type == "youtube-video" or any(x in text for x in ["bilibili", "transcript", "voice", "台词", "セリフ", "ボイス"]):
        points += 18
        reasons.append("voice-or-transcript-signal")
    if source_type == "moegirl" or any(x in text for x in ["萌娘百科", "moegirl"]):
        points += 25
        reasons.append("chinese-acg-reference-and-name-source")
    if any(x in text for x in ["wiki", "fandom", "wikipedia", "pixiv", "百科"]):
        points += 10
        reasons.append("summary-source")
    if any(x in text for x in ["forum", "reddit", "tieba", "blog", "analysis", "论坛", "贴吧"]):
        points -= 10
        reasons.append("fan-analysis-risk")
    if re.search(r"google\.com/search|duckduckgo\.com|youtube\.com/results", text):
        points -= 15
        reasons.append("manual-search-placeholder")
    return points, reasons


def decision(points: int, current: str, source_type: str) -> str:
    if current == "reject":
        return "reject"
    if source_type in DISCOVERY_ONLY:
        return "needs-user-review"
    if points < 0:
        return "reject"
    if points >= 45:
        return "recommended"
    if points >= 20:
        return "optional"
    return "needs-user-review"


def write_review(path: Path, rows: list[dict]) -> None:
    lines = [
        "# Source Review",
        "",
        "Confirm which sources to use. Only confirmed or agent-selected recommended rows should enter evidence.",
        "",
        "| ID | Decision | Score | Project | Type | Title | Layer | Reason | URL |",
        "|---|---|---:|---|---|---|---|---|---|",
    ]
    for row in rows:
        safe = {k: str(v).replace("|", "/") for k, v in row.items()}
        lines.append(
            f"| {safe.get('id','')} | {safe.get('decision','')} | {safe.get('score','')} | {safe.get('project','')} | "
            f"{safe.get('source_type','')} | {safe.get('title','')} | {safe.get('suggested_layer','')} | {safe.get('rank_reason','')} | {safe.get('url','')} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Rank candidate character sources")
    parser.add_argument("candidates", help="Path to candidates.json")
    parser.add_argument("--out", default="", help="Output reviewed_sources.json path")
    parser.add_argument("--delegate-recommended", action="store_true", help="Mark recommended rows agent-selected")
    args = parser.parse_args()

    in_path = Path(args.candidates)
    rows = json.loads(in_path.read_text(encoding="utf-8-sig"))
    if isinstance(rows, dict):
        rows = [rows]
    for row in rows:
        points, reasons = score(row)
        row["score"] = points
        row["rank_reason"] = ", ".join(reasons) if reasons else "weak signal"
        row["decision"] = decision(points, row.get("decision", "needs-user-review"), row.get("source_type", ""))
        if args.delegate_recommended and row["decision"] == "recommended":
            row["confirmed_by_user"] = "agent-selected"

    rows.sort(key=lambda r: r.get("score", 0), reverse=True)
    out_path = Path(args.out) if args.out else in_path.with_name("reviewed_sources.json")
    out_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    write_review(out_path.with_suffix(".md"), rows)
    print(f"Wrote {out_path}")
    print(f"Wrote {out_path.with_suffix('.md')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
