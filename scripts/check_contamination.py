#!/usr/bin/env python3
"""Check whether learning or new evidence contaminated canon/user settings."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Check character contamination risks")
    parser.add_argument("--character", required=True, help="CHARACTER.md path")
    parser.add_argument("--evidence", default="", help="Optional evidence.json path")
    parser.add_argument("--out", required=True, help="Output directory")
    args = parser.parse_args()
    text = Path(args.character).read_text(encoding="utf-8", errors="replace")
    risks: list[dict] = []
    if re.search(r"模拟台词.*原作|self-learning.*canon", text, re.I):
        risks.append({"risk": "simulated-line-as-canon", "severity": "high", "detail": "self-learning output may be treated as canon"})
    if re.search(r"默认关系.*恋人|默认.*情侣", text):
        risks.append({"risk": "romance-default-contamination", "severity": "medium", "detail": "romance may have become default relationship"})
    if re.search(r"\+\d|tension|debug|场景焦点：", text, re.I):
        risks.append({"risk": "backend-state-leak", "severity": "medium", "detail": "backend state marker appears in user-facing text"})
    if args.evidence and Path(args.evidence).exists():
        data = json.loads(Path(args.evidence).read_text(encoding="utf-8-sig"))
        for item in data.get("evidence", []) if isinstance(data, dict) else data:
            if item.get("layer") == "fan-analysis" and any(dim in item.get("dimensions", []) for dim in ["identity", "relationship"]):
                risks.append({"risk": "fan-analysis-overreach", "severity": "low", "detail": item.get("summary", "")[:160]})
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    payload = {"status": "WARN" if risks else "PASS", "risks": risks}
    (out / "contamination-report.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# Contamination Check", "", f"Status: {payload['status']}", "", "| Risk | Severity | Detail |", "|---|---|---|"]
    for risk in risks:
        lines.append(f"| {risk['risk']} | {risk['severity']} | {str(risk['detail']).replace('|','/')} |")
    if not risks:
        lines.append("| none |  | no obvious contamination detected |")
    target_md = out / "contamination-check.md"
    target_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {target_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
