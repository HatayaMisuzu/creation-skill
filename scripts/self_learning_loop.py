#!/usr/bin/env python3
"""Run a repeatable self-learning loop over character dialogue material.

This script is a static/heuristic trainer, not a roleplay model. It compares
source lines with conservative imitation drafts, explains drift, and writes
lessons that can be merged into CHARACTER.md after review.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path


def load_json(path_text: str) -> object:
    return json.loads(Path(path_text).read_text(encoding="utf-8-sig"))


def load_items(path_text: str) -> list[dict]:
    data = load_json(path_text)
    if isinstance(data, dict):
        items = data.get("items") or data.get("evidence") or data.get("materials") or []
        return items if isinstance(items, list) else []
    if isinstance(data, list):
        return data
    return []


def load_voice_fingerprint(path_text: str) -> dict:
    if not path_text:
        return {}
    path = Path(path_text)
    if not path.exists():
        return {}
    data = load_json(path_text)
    return data if isinstance(data, dict) else {}


def text_of(item: dict) -> str:
    return str(item.get("text") or item.get("quote") or item.get("summary") or "").strip()


def list_field(item: dict, *keys: str) -> set[str]:
    values: set[str] = set()
    for key in keys:
        raw = item.get(key, [])
        if isinstance(raw, str):
            raw = [raw]
        if isinstance(raw, list):
            values.update(str(x).lower() for x in raw)
    return values


def is_dialogue(item: dict) -> bool:
    speaker = str(item.get("speaker", "")).lower()
    tags = list_field(item, "dimensions", "used_for", "tags")
    text = text_of(item)
    if speaker == "character":
        return True
    if {"voice", "dialogue", "expression"} & tags:
        return True
    return bool(re.search(r"[「“\"].{4,}[」”\"]|[:：].{4,}", text))


def source_weight(item: dict) -> int:
    layer = str(item.get("layer") or item.get("source_layer") or "").lower()
    score = int(item.get("evidence_score") or item.get("score") or 0)
    if layer in {"canon", "transcript"}:
        score += 35
    elif layer == "official":
        score += 28
    elif layer == "user-provided":
        score += 26
    elif layer == "secondary":
        score += 10
    if str(item.get("speaker", "")).lower() == "character":
        score += 25
    return score


def pick_examples(items: list[dict], limit: int) -> list[dict]:
    examples = [item for item in items if is_dialogue(item) and len(text_of(item)) >= 6]
    examples.sort(key=source_weight, reverse=True)
    return examples[:limit]


def features(text: str) -> dict:
    clean = re.sub(r"\s+", "", text)
    return {
        "length": len(clean),
        "ellipsis": text.count("…") + text.count("..."),
        "question": text.count("?") + text.count("？"),
        "exclamation": text.count("!") + text.count("！"),
        "comma_pause": text.count("，") + text.count(","),
        "softeners": len(re.findall(r"那个|其实|也许|大概|可能|ちょっと|少し|maybe|perhaps", text, re.I)),
        "honorifics": len(re.findall(r"さん|様|ちゃん|君|先生|制作人|producer", text, re.I)),
        "sentence_count": max(1, len(re.findall(r"[。！？!?]", text))),
    }


def imitate(source: str, iteration: int, fp: dict) -> str:
    text = re.sub(r"^[^:：]{1,20}[:：]\s*", "", source).strip()
    text = text.strip("「」“”\"")
    if iteration == 1:
        return text
    if iteration == 2:
        if fp.get("sentence_length") == "short" and len(text) > 32:
            return text[:32].rstrip("，,。") + "。"
        return re.sub(r"[！？!?]+$", "。", text)
    if "…" not in text and fp.get("hesitation_markers"):
        return "…" + text
    return text


def compare(original: str, simulated: str, fp: dict) -> dict:
    original_features = features(original)
    simulated_features = features(simulated)
    delta = {key: simulated_features[key] - original_features[key] for key in original_features}
    length_ratio = simulated_features["length"] / max(1, original_features["length"])
    score = 100.0
    score -= min(35, abs(1 - length_ratio) * 60)
    for key in ["ellipsis", "question", "exclamation", "softeners", "honorifics"]:
        score -= min(12, abs(delta[key]) * 4)
    forbidden = [str(x) for x in fp.get("forbidden_drift", []) if str(x)]
    drift_hits = [item for item in forbidden if item.lower() in simulated.lower()]
    score -= min(25, len(drift_hits) * 8)
    return {
        "original_features": original_features,
        "simulated_features": simulated_features,
        "delta": delta,
        "forbidden_drift_hits": drift_hits,
        "score": round(max(0, score), 1),
    }


def lessons_from(comparison: dict, fp: dict) -> list[str]:
    delta = comparison["delta"]
    lessons: list[str] = []
    if abs(delta["length"]) > 18:
        lessons.append("Keep reply length close to the source cadence; do not expand short lines into explanation.")
    if delta["ellipsis"] < 0 and fp.get("hesitation_markers"):
        lessons.append("Preserve hesitation/pause markers when they are part of the character's emotional texture.")
    if delta["softeners"] < 0:
        lessons.append("Keep softeners and tentative wording when the source uses them.")
    if delta["honorifics"] < 0:
        lessons.append("Honorifics and address style are voice DNA; preserve them where natural.")
    if delta["exclamation"] > 1:
        lessons.append("Avoid inflating emotional intensity with too many exclamation marks.")
    if comparison.get("forbidden_drift_hits"):
        lessons.append("Remove forbidden drift terms found in the simulated line.")
    if fp.get("assertiveness") in {"low", "medium-low"}:
        lessons.append("Default to indirect or buffered assertion unless the scene triggers resolve/serious mode.")
    if not lessons:
        lessons.append("Surface cadence is close; continue checking deeper triggers, relationship stance, and scene context.")
    return lessons


def aggregate(rounds: list[dict]) -> list[str]:
    counter: Counter[str] = Counter()
    for row in rounds:
        counter.update(row["lessons"])
    return [text for text, _ in counter.most_common(10)]


def write_outputs(out_dir: Path, rounds: list[dict], lessons: list[str], fp: dict) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {"rounds": rounds, "lessons": lessons, "voice_fingerprint_used": bool(fp)}
    (out_dir / "self-learning.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = ["# Self Learning Report", "", f"Voice fingerprint used: {'yes' if fp else 'no'}", "", "## Distilled Lessons", ""]
    lines.extend(f"- {lesson}" for lesson in lessons)
    lines.extend(["", "## Simulation Rounds", "", "| Round | Score | Original | Simulated | Main Lessons |", "|---:|---:|---|---|---|"])
    for idx, row in enumerate(rounds, 1):
        original = row["original"].replace("|", "/").replace("\n", " ")
        simulated = row["simulated"].replace("|", "/").replace("\n", " ")
        row_lessons = "; ".join(row["lessons"]).replace("|", "/")
        lines.append(f"| {idx} | {row['comparison']['score']} | {original} | {simulated} | {row_lessons} |")
    (out_dir / "self-learning-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    patch = ["# Learning Patch", "", "Add these notes to CHARACTER.md section 20 after human review.", "", "## Mergeable Lessons", ""]
    patch.extend(f"- {lesson}" for lesson in lessons)
    (out_dir / "learning-patch.md").write_text("\n".join(patch) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run self-learning loop over character material")
    parser.add_argument("--materials", required=True, help="character_materials.json or evidence.json")
    parser.add_argument("--character-md", default="", help="Existing CHARACTER.md for context bookkeeping")
    parser.add_argument("--voice-fingerprint", default="", help="voice-fingerprint.json path")
    parser.add_argument("--out", required=True, help="Output learning directory")
    parser.add_argument("--iterations", type=int, default=3, help="Imitation attempts per example")
    parser.add_argument("--max-examples", type=int, default=8, help="Maximum source dialogue examples")
    args = parser.parse_args()

    items = load_items(args.materials)
    fp = load_voice_fingerprint(args.voice_fingerprint)
    examples = pick_examples(items, args.max_examples)
    rounds: list[dict] = []
    for item in examples:
        original = text_of(item)
        for iteration in range(1, max(1, args.iterations) + 1):
            simulated = imitate(original, iteration, fp)
            comparison = compare(original, simulated, fp)
            rounds.append(
                {
                    "source": item.get("source", item.get("source_id", "")),
                    "layer": item.get("layer", ""),
                    "speaker": item.get("speaker", ""),
                    "iteration": iteration,
                    "original": original,
                    "simulated": simulated,
                    "comparison": comparison,
                    "lessons": lessons_from(comparison, fp),
                }
            )

    lessons = aggregate(rounds)
    if not lessons:
        lessons = ["No usable character dialogue was found; add confirmed first-person lines before running self-learning again."]
    write_outputs(Path(args.out), rounds, lessons, fp)
    avg = sum(row["comparison"]["score"] for row in rounds) / max(1, len(rounds))
    print(f"Wrote {Path(args.out) / 'self-learning-report.md'}")
    print(f"Rounds: {len(rounds)} Average score: {round(avg, 1)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
