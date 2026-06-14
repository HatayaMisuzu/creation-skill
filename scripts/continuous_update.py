#!/usr/bin/env python3
"""Merge approved new evidence and self-learning lessons into CHARACTER.md."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
from pathlib import Path


def load_json_optional(path_text: str) -> dict:
    if not path_text:
        return {}
    path = Path(path_text)
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(data, dict):
        return data
    if isinstance(data, list):
        return {"items": data}
    return {}


def bump_version(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        value = match.group(1).strip()
        parts = value.split(".")
        try:
            if len(parts) == 1:
                return f"version: {int(parts[0]) + 1}"
            parts[-1] = str(int(parts[-1]) + 1)
            return "version: " + ".".join(parts)
        except ValueError:
            return "version: " + value + "+update"

    return re.sub(r"^version:\s*([^\n]+)$", repl, text, count=1, flags=re.M)


def ensure_section(text: str, heading: str, body: str) -> str:
    if heading in text:
        return text
    if not text.endswith("\n"):
        text += "\n"
    return text + "\n" + heading + "\n\n" + body.strip() + "\n"


def insert_under_section(text: str, heading: str, block: str) -> str:
    text = ensure_section(text, heading, "")
    idx = text.find(heading)
    if idx < 0:
        return text + "\n\n" + heading + "\n\n" + block.strip() + "\n"
    start = idx + len(heading)
    return text[:start] + "\n\n" + block.strip() + "\n" + text[start:]


def archive(card: Path) -> Path:
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    version_dir = card.parent / "versions" / stamp
    version_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(card, version_dir / "CHARACTER.md")
    return version_dir


def evidence_items(data: dict) -> list[dict]:
    items = data.get("evidence") or data.get("items") or []
    return items if isinstance(items, list) else []


def evidence_summary(data: dict, limit: int) -> tuple[list[str], list[str]]:
    lines: list[str] = []
    changed_dims: list[str] = []
    for item in evidence_items(data)[:limit]:
        dims = item.get("dimensions") or item.get("used_for") or []
        if isinstance(dims, str):
            dims = [dims]
        changed_dims.extend(str(dim) for dim in dims)
        summary = str(item.get("summary") or item.get("text") or item.get("quote") or "")[:180]
        source = str(item.get("source") or item.get("source_id") or "")
        layer = str(item.get("layer") or item.get("suggested_layer") or "unknown")
        confirmed = str(item.get("user_confirmed", item.get("confirmed", "unknown")))
        lines.append(
            f"| {', '.join(map(str, dims)) or 'update'} | {summary.replace('|', '/')} | {source.replace('|', '/')} | {layer} | {confirmed} |"
        )
    return lines, sorted(set(changed_dims))


def learning_lessons(path_text: str) -> list[str]:
    if not path_text:
        return []
    path = Path(path_text)
    if not path.exists():
        return []
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if isinstance(data, dict):
            return [str(x) for x in data.get("lessons", [])]
        return []
    lessons: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            lessons.append(stripped[2:])
    return lessons


def write_update_report(out_dir: Path, changed_dims: list[str], lessons: list[str], archive_dir: Path) -> None:
    lines = [
        "# Continuous Learning Update Report",
        "",
        f"Archived previous card: {archive_dir / 'CHARACTER.md'}",
        "",
        "## Changed Areas",
        "",
    ]
    lines.extend(f"- {dim}" for dim in changed_dims) if changed_dims else lines.append("- no structured evidence dimensions detected")
    lines.extend(["", "## Self-Learning Lessons", ""])
    lines.extend(f"- {lesson}" for lesson in lessons) if lessons else lines.append("- no self-learning lessons supplied")
    lines.extend(["", "## Non-Overwrite Rule", "", "- user-provided settings are not overwritten automatically."])
    report = "\n".join(lines) + "\n"
    (out_dir / "continuous-update-report.md").write_text(report, encoding="utf-8")
    (archive_dir / "diff-report.md").write_text(report, encoding="utf-8")


def append_growth_log(out_dir: Path, changed_dims: list[str], lessons: list[str], archive_dir: Path) -> None:
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    path = out_dir / "growth-log.md"
    if not path.exists():
        path.write_text("# Growth Log\n\n", encoding="utf-8")
    lines = [
        f"## {stamp} continuous-update",
        "",
        f"- Archived previous card: {archive_dir / 'CHARACTER.md'}",
        f"- Changed dimensions: {', '.join(changed_dims) if changed_dims else 'none detected'}",
        f"- Self-learning lessons: {len(lessons)}",
        "- Canon safety: new material is evidence until reviewed; user-provided settings remain protected.",
        "",
    ]
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description="Continuously update an existing CHARACTER.md")
    parser.add_argument("--character", required=True, help="Path to existing CHARACTER.md")
    parser.add_argument("--new-evidence", default="", help="New evidence.json generated from approved material")
    parser.add_argument("--learning", default="", help="self-learning.json/report/patch to merge")
    parser.add_argument("--out", default="", help="Output directory; default updates the card in place")
    parser.add_argument("--evidence-limit", type=int, default=12)
    parser.add_argument("--no-bump-version", action="store_true")
    args = parser.parse_args()

    source_card = Path(args.character)
    if not source_card.exists():
        raise FileNotFoundError(source_card)
    out_dir = Path(args.out) if args.out else source_card.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    card = out_dir / "CHARACTER.md"
    if source_card.resolve() != card.resolve():
        shutil.copy2(source_card, card)

    archive_dir = archive(card)
    text = card.read_text(encoding="utf-8", errors="replace")
    if not args.no_bump_version:
        text = bump_version(text)

    evidence_data = load_json_optional(args.new_evidence)
    evidence_lines, changed_dims = evidence_summary(evidence_data, args.evidence_limit)
    lessons = learning_lessons(args.learning)
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    text = ensure_section(
        text,
        "## 20. 自学习循环记录",
        "记录从已确认素材中复写、比较、归纳出的演绎经验。经验只修正表达策略，不自动伪造新设定。",
    )
    text = ensure_section(
        text,
        "## 21. 持续学习更新记录",
        "记录用户新增素材带来的版本更新。新素材必须保留来源、层级、适用维度和确认状态。",
    )

    if lessons:
        block = [f"### {stamp} self-learning lessons", "", "| Lesson | Runtime Use |", "|---|---|"]
        block.extend(f"| {lesson.replace('|', '/')} | Use as voice/performance guidance, not canon evidence. |" for lesson in lessons)
        text = insert_under_section(text, "## 20. 自学习循环记录", "\n".join(block))

    if evidence_lines:
        block = [
            f"### {stamp} new evidence batch",
            "",
            "| Dimension | Summary | Source | Layer | Confirmed |",
            "|---|---|---|---|---|",
        ]
        block.extend(evidence_lines)
        block.extend(
            [
                "",
                "Update rule: new evidence enters the card as reviewed material. If it conflicts with existing user-provided or canon settings, keep the conflict for user confirmation instead of silently overwriting.",
            ]
        )
        text = insert_under_section(text, "## 21. 持续学习更新记录", "\n".join(block))

    card.write_text(text, encoding="utf-8")
    write_update_report(out_dir, changed_dims, lessons, archive_dir)
    append_growth_log(out_dir, changed_dims, lessons, archive_dir)

    print(f"Updated {card}")
    print(f"Archived previous card to {archive_dir / 'CHARACTER.md'}")
    print(f"Wrote {out_dir / 'continuous-update-report.md'}")
    print(f"Wrote {out_dir / 'growth-log.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
