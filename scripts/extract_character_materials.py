#!/usr/bin/env python3
"""Extract target-character material from collected project sources."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_manifest(path: Path) -> list[dict]:
    data = read_json(path)
    return data if isinstance(data, list) else [data]


def load_rules(path_text: str) -> dict:
    if not path_text:
        return {}
    data = read_json(Path(path_text))
    return data if isinstance(data, dict) else {}


def normalize_aliases(character: str, aliases: list[str], rules: dict) -> list[str]:
    values = [character] + aliases + list(rules.get("aliases", []))
    seen: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text.lower() not in [x.lower() for x in seen]:
            seen.append(text)
    return seen


def has_any(text: str, needles: list[str]) -> bool:
    lower = text.lower()
    return any(needle.lower() in lower for needle in needles if needle)


def speaker_prefix(line: str) -> tuple[str, str, str]:
    line = line.strip().lstrip("\ufeff")
    patterns = [
        ("bracket", r"^\[([^\]]{1,40})\]\s*(.+)$"),
        ("colon", r"^([^:：]{1,40})\s*[:：]\s*(.+)$"),
        ("corner-quote", r"^([^「」『』“”\"]{1,40})[「『“\"](.+)[」』”\"]$"),
        ("jp-corner", r"^【([^】]{1,40})】\s*(.+)$"),
    ]
    for kind, pattern in patterns:
        match = re.match(pattern, line)
        if match:
            return match.group(1).strip(), match.group(2).strip(), kind
    return "", line, "none"


def normalize_speaker(speaker: str, rules: dict) -> str:
    if not speaker:
        return ""
    mapping = rules.get("speaker_aliases", {})
    for canonical, names in mapping.items():
        if speaker == canonical or speaker in names:
            return canonical
    return speaker


def split_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw in re.split(r"\r?\n+", text):
        line = raw.strip()
        if not line:
            continue
        lines.append(line)
    return lines


def classify_line(line: str, aliases: list[str], exclude_aliases: list[str], rules: dict) -> dict:
    speaker, content, pattern = speaker_prefix(line)
    speaker = normalize_speaker(speaker, rules)
    has_target_in_speaker = has_any(speaker, aliases)
    has_target_in_content = has_any(content, aliases)
    has_excluded_speaker = has_any(speaker, exclude_aliases)
    has_excluded_content = has_any(content, exclude_aliases)
    if has_excluded_speaker and not has_target_in_content:
        return {"speaker": "irrelevant", "speaker_name": speaker, "text": content, "pattern": pattern, "score": 0.0, "reason": "excluded speaker"}
    if has_target_in_speaker:
        return {"speaker": "character", "speaker_name": speaker, "text": content, "pattern": pattern, "score": 1.0, "reason": "target speaker"}
    if speaker and has_target_in_content and not has_excluded_content:
        return {"speaker": "other", "speaker_name": speaker, "text": content, "pattern": pattern, "score": 0.78, "reason": "other speaker mentions target"}
    if has_target_in_content:
        return {"speaker": "unknown", "speaker_name": speaker, "text": content, "pattern": pattern, "score": 0.58, "reason": "target mention without speaker"}
    if speaker:
        return {"speaker": "other", "speaker_name": speaker, "text": content, "pattern": pattern, "score": 0.18, "reason": "other speaker context"}
    return {"speaker": "irrelevant", "speaker_name": "", "text": content, "pattern": pattern, "score": 0.0, "reason": "no target signal"}


def material_type(label: str) -> str:
    if label == "character":
        return "self_dialogue"
    if label == "other":
        return "external_observation"
    if label == "unknown":
        return "uncertain"
    if label == "context":
        return "context"
    return "discarded"


def extract_source(source: dict, aliases: list[str], exclude_aliases: list[str], rules: dict, args: argparse.Namespace) -> tuple[list[dict], list[dict]]:
    text_path = Path(source.get("text_path", ""))
    if not text_path.exists():
        return [], [{"source_id": source.get("id", ""), "line_number": 0, "text": "", "reason": "missing text_path"}]
    lines = split_lines(text_path.read_text(encoding="utf-8", errors="replace"))
    labels = [classify_line(line, aliases, exclude_aliases, rules) for line in lines]
    relevant = {idx for idx, item in enumerate(labels) if item["score"] >= args.min_relevance and item["speaker"] in {"character", "other", "unknown"}}
    include = set(relevant)
    if args.window > 0:
        for idx in relevant:
            for pos in range(max(0, idx - args.window), min(len(lines), idx + args.window + 1)):
                include.add(pos)

    kept: list[dict] = []
    discarded: list[dict] = []
    for idx, line in enumerate(lines):
        label = labels[idx]
        if idx not in include:
            discarded.append({"source_id": source.get("id", ""), "line_number": idx + 1, "text": line, "reason": label["reason"]})
            continue
        speaker_label = label["speaker"]
        score = label["score"]
        reason = label["reason"]
        if idx not in relevant:
            speaker_label = "context"
            score = 0.25
            reason = "context window"
        if speaker_label == "context" and not args.keep_context_only and not relevant:
            pass
        if speaker_label == "irrelevant":
            discarded.append({"source_id": source.get("id", ""), "line_number": idx + 1, "text": line, "reason": reason})
            continue
        kept.append(
            {
                "id": f"{source.get('id', 'S')}-{idx + 1}",
                "source_id": source.get("id", ""),
                "source_title": source.get("title", ""),
                "source": source.get("url") or source.get("text_path"),
                "project": args.project or source.get("project", ""),
                "source_scope": source.get("source_scope", "project"),
                "phase": args.phase or source.get("phase", "unknown"),
                "line_number": idx + 1,
                "speaker": speaker_label,
                "speaker_name": label["speaker_name"],
                "material_type": material_type(speaker_label),
                "text": label["text"],
                "relevance_score": round(score, 2),
                "reason": reason,
                "layer": source.get("suggested_layer", source.get("layer", "secondary")),
                "language": source.get("detected_language", "unknown"),
            }
        )
    return kept, discarded


def write_materials_md(path: Path, items: list[dict]) -> None:
    lines = [
        "# Character Materials",
        "",
        "Use `speaker=character` for voice DNA. Use `speaker=other` for relationship/social perception. Treat `speaker=unknown` as low confidence.",
        "",
        "| Source | Line | Speaker | Type | Score | Name | Text |",
        "|---|---:|---|---|---:|---|---|",
    ]
    for item in items:
        lines.append(
            "| {source_id} | {line_number} | {speaker} | {material_type} | {relevance_score} | {speaker_name} | {text} |".format(
                **{key: str(value).replace("|", "/").replace("\n", " ") for key, value in item.items()}
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_audit(path: Path, items: list[dict], discarded: list[dict]) -> None:
    counts: dict[str, int] = {}
    for item in items:
        counts[item["speaker"]] = counts.get(item["speaker"], 0) + 1
    lines = ["# Speaker Audit", "", f"Kept lines: {len(items)}", f"Discarded lines: {len(discarded)}", ""]
    for key in ["character", "other", "unknown", "context"]:
        lines.append(f"- {key}: {counts.get(key, 0)}")
    lines.extend(["", "## Rules", "", "- Only `speaker=character` should directly shape expression DNA.", "- Project-level material must pass target-character filtering before evidence use."])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_discarded(path: Path, discarded: list[dict]) -> None:
    lines = ["# Discarded Context", "", "| Source | Line | Reason | Text |", "|---|---:|---|---|"]
    for item in discarded[:2000]:
        lines.append(
            "| {source_id} | {line_number} | {reason} | {text} |".format(
                **{key: str(value).replace("|", "/").replace("\n", " ") for key, value in item.items()}
            )
        )
    if len(discarded) > 2000:
        lines.append(f"| ... | ... | truncated | {len(discarded) - 2000} additional discarded lines omitted |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract target-character lines from collected material")
    parser.add_argument("--collected", required=True, help="Collected directory containing source_manifest.json")
    parser.add_argument("--character", required=True, help="Target character name")
    parser.add_argument("--alias", action="append", default=[], help="Character alias; repeatable")
    parser.add_argument("--exclude-alias", action="append", default=[], help="Names that should not be treated as target aliases")
    parser.add_argument("--project", default="", help="Project/franchise name")
    parser.add_argument("--speaker-rules", default="", help="Optional JSON speaker normalization rules")
    parser.add_argument("--out", default="", help="Output directory, default: <collected>/character")
    parser.add_argument("--window", type=int, default=2, help="Context lines around relevant lines")
    parser.add_argument("--min-relevance", type=float, default=0.5, help="Minimum relevance score for direct extraction")
    parser.add_argument("--keep-context-only", action="store_true", help="Keep context window lines in outputs")
    parser.add_argument("--phase", default="", help="Override phase label for extracted items")
    args = parser.parse_args()

    collected = Path(args.collected)
    out_dir = Path(args.out) if args.out else collected / "character"
    out_dir.mkdir(parents=True, exist_ok=True)
    rules = load_rules(args.speaker_rules)
    aliases = normalize_aliases(args.character, args.alias, rules)
    exclude_aliases = [x.strip() for x in args.exclude_alias if x.strip()] + list(rules.get("exclude_aliases", []))
    manifest = load_manifest(collected / "source_manifest.json")

    items: list[dict] = []
    discarded: list[dict] = []
    for source in manifest:
        if source.get("status") not in {"collected", "partial"}:
            continue
        kept, dropped = extract_source(source, aliases, exclude_aliases, rules, args)
        if not args.keep_context_only:
            kept = [item for item in kept if item["speaker"] != "context" or any(x["source_id"] == item["source_id"] for x in kept if x["speaker"] != "context")]
        items.extend(kept)
        discarded.extend(dropped)

    payload = {"character": args.character, "aliases": aliases, "exclude_aliases": exclude_aliases, "items": items}
    (out_dir / "character_materials.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_materials_md(out_dir / "character_materials.md", items)
    write_audit(out_dir / "speaker_audit.md", items, discarded)
    write_discarded(out_dir / "discarded_context.md", discarded)
    (out_dir / "character_materials.txt").write_text("\n".join(item["text"] for item in items) + ("\n" if items else ""), encoding="utf-8")
    print(f"Wrote {out_dir / 'character_materials.json'}")
    print(f"Extracted {len(items)} lines")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
