#!/usr/bin/env python3
"""Extract a lightweight voice fingerprint from evidence or character material."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_items(path: Path) -> list[dict]:
    data = read_json(path)
    if isinstance(data, dict):
        return list(data.get("evidence") or data.get("items") or [])
    return list(data) if isinstance(data, list) else []


def text_of(item: dict) -> str:
    return str(item.get("quote") or item.get("text") or item.get("summary") or "").strip()


def has_voice_tag(item: dict) -> bool:
    dims = item.get("dimensions") or item.get("used_for") or []
    if isinstance(dims, str):
        dims = [dims]
    return any(str(dim).lower() == "voice" for dim in dims)


def sentence_bucket(length: float) -> str:
    if length < 18:
        return "short"
    if length < 46:
        return "short-medium"
    if length < 90:
        return "medium"
    return "long"


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract voice fingerprint")
    parser.add_argument("--evidence", required=True, help="evidence.json or character_materials.json")
    parser.add_argument("--out", required=True, help="Output character directory")
    args = parser.parse_args()

    items = [item for item in load_items(Path(args.evidence)) if text_of(item)]
    voice_items = [item for item in items if item.get("speaker") == "character" and has_voice_tag(item)]
    voice_items = voice_items or [item for item in items if item.get("speaker") == "character"] or [item for item in items if has_voice_tag(item)] or items
    texts = [text_of(item) for item in voice_items]
    joined = "\n".join(texts)
    sentence_lengths = [len(s.strip()) for s in re.split(r"[。！？!?]\s*|\n+", joined) if s.strip()]
    avg_len = sum(sentence_lengths) / max(1, len(sentence_lengths))

    hesitation = Counter(re.findall(r"…|那个|其实|也许|大概|可能|少し|ちょっと|えっと|あの|maybe|perhaps", joined, re.I))
    address = Counter(re.findall(r"老师|同学|制作人|前辈|你|您|さん|ちゃん|様|君|producer", joined, re.I))
    punctuation = {
        "ellipsis": joined.count("…") + joined.count("..."),
        "question": joined.count("?") + joined.count("？"),
        "exclamation": joined.count("!") + joined.count("！"),
        "comma": joined.count("，") + joined.count(","),
    }
    assertiveness = "low" if punctuation["exclamation"] == 0 and hesitation else "medium"
    if punctuation["exclamation"] > max(2, len(texts) // 2):
        assertiveness = "high"
    emotional_pressure = "suppressed" if punctuation["ellipsis"] or hesitation else "steady"

    fingerprint = {
        "sentence_length": sentence_bucket(avg_len),
        "average_sentence_length": round(avg_len, 1),
        "hesitation_markers": [key for key, _ in hesitation.most_common(8)],
        "address_style": [key for key, _ in address.most_common(8)],
        "emotional_pressure": emotional_pressure,
        "assertiveness": assertiveness,
        "humor_style": "unknown",
        "punctuation_profile": punctuation,
        "forbidden_drift": ["设定朗读", "百科腔", "过度迎合", "整段切换素材语言", "作为AI", "作为模型", "后台状态外泄"],
        "sample_count": len(texts),
    }

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "voice-fingerprint.json").write_text(json.dumps(fingerprint, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Voice Fingerprint",
        "",
        f"- Sentence length: {fingerprint['sentence_length']}",
        f"- Emotional pressure: {emotional_pressure}",
        f"- Assertiveness: {assertiveness}",
        f"- Sample count: {len(texts)}",
        "",
        "## Hesitation Markers",
        "",
    ]
    lines.extend(f"- {item}" for item in fingerprint["hesitation_markers"]) if fingerprint["hesitation_markers"] else lines.append("- none detected")
    lines.extend(["", "## Address Style", ""])
    lines.extend(f"- {item}" for item in fingerprint["address_style"]) if fingerprint["address_style"] else lines.append("- none detected")
    lines.extend(["", "## Forbidden Drift", ""])
    lines.extend(f"- {item}" for item in fingerprint["forbidden_drift"])
    (out_dir / "voice-fingerprint.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out_dir / 'voice-fingerprint.json'}")
    print(f"Wrote {out_dir / 'voice-fingerprint.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
