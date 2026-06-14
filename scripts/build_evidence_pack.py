#!/usr/bin/env python3
"""Build an evidence pack from collected and character-filtered material."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


DIMENSION_PATTERNS = {
    "identity": r"profile|身份|角色|姓名|生日|年龄|所属|职业|character",
    "personality": r"性格|人格|害怕|恐惧|想要|愿望|执念|信念|pride|desire|fear|personality",
    "voice": r"台词|口癖|语气|称呼|voice|quote|says|saying|说",
    "scene": r"剧情|场景|事件|episode|chapter|scene|story|route",
    "timeline": r"时间线|阶段|成长|变化|before|after|arc|phase|主线|活动",
    "relationship": r"关系|朋友|同伴|敌人|对手|家人|friend|rival|mentor|sister|brother",
    "knowledge": r"世界观|设定|知道|不知道|setting|world|knowledge",
    "boundary": r"边界|拒绝|禁止|不允许|rule|limit|safety|OOC",
}


LAYER_WEIGHT = {
    "canon": 40,
    "official": 36,
    "transcript": 34,
    "user-provided": 32,
    "secondary": 16,
    "fan-analysis": 6,
    "inferred": 2,
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_manifest(collected: Path) -> list[dict]:
    path = collected / "source_manifest.json"
    if not path.exists():
        return []
    data = read_json(path)
    return data if isinstance(data, list) else [data]


def load_character_materials(collected: Path, override: str) -> list[dict]:
    path = Path(override) if override else collected / "character" / "character_materials.json"
    if not path.exists():
        return []
    data = read_json(path)
    if isinstance(data, dict):
        return data.get("items", [])
    return data if isinstance(data, list) else []


def split_sentences(text: str) -> list[str]:
    pieces = re.split(r"(?<=[。！？!?])\s+|\n+", text)
    return [piece.strip() for piece in pieces if len(piece.strip()) >= 10]


def dimensions_for(text: str, speaker: str = "") -> list[str]:
    dims = [name for name, pattern in DIMENSION_PATTERNS.items() if re.search(pattern, text, re.I)]
    if speaker == "character" and "voice" not in dims:
        dims.append("voice")
    if speaker == "other" and "relationship" not in dims:
        dims.append("relationship")
    return list(dict.fromkeys(dims or ["identity"]))


def confidence(layer: str, speaker: str, text: str) -> str:
    if layer in {"canon", "official", "transcript", "user-provided"} and speaker in {"character", "context", ""}:
        return "high"
    if layer in {"canon", "official", "transcript", "user-provided"}:
        return "medium-high"
    if len(text) > 80:
        return "medium"
    return "low"


def evidence_score(layer: str, speaker: str, dims: list[str], source_confidence: str = "") -> int:
    score = 20 + LAYER_WEIGHT.get(layer, 8)
    if speaker == "character":
        score += 25
    elif speaker == "other":
        score += 10
    elif speaker == "unknown":
        score -= 6
    if "voice" in dims and speaker == "character":
        score += 10
    if "relationship" in dims and speaker == "other":
        score += 6
    if source_confidence == "low":
        score -= 12
    return max(0, min(100, score))


def source_layer(source: dict) -> str:
    return str(source.get("suggested_layer") or source.get("layer") or "secondary")


def fallback_evidence_from_sources(manifest: list[dict], per_source: int) -> list[dict]:
    evidence: list[dict] = []
    for source in manifest:
        if source.get("status") not in {"collected", "partial"}:
            continue
        text_path = Path(source.get("text_path", ""))
        if not text_path.exists():
            continue
        text = text_path.read_text(encoding="utf-8", errors="replace")
        layer = source_layer(source)
        sentences = split_sentences(text)[: per_source * 4]
        ranked = sorted(sentences, key=lambda s: (len(dimensions_for(s)), min(len(s), 200)), reverse=True)[:per_source]
        for sent in ranked:
            dims = dimensions_for(sent)
            evidence.append(
                {
                    "id": f"E{len(evidence) + 1:03d}",
                    "summary": sent[:180],
                    "quote": sent[:260],
                    "source": source.get("url") or source.get("text_path"),
                    "source_title": source.get("title", ""),
                    "project": source.get("project", ""),
                    "source_scope": source.get("source_scope", "raw-fallback"),
                    "phase": source.get("phase", "unknown"),
                    "layer": layer,
                    "language": source.get("detected_language", "unknown"),
                    "speaker": "unknown",
                    "dimensions": dims,
                    "used_for": dims,
                    "evidence_score": evidence_score(layer, "unknown", dims, source.get("confidence", "")),
                    "confidence": confidence(layer, "unknown", sent),
                    "confirmed_by_user": source.get("confirmed_by_user", False),
                }
            )
    return evidence


def evidence_from_materials(materials: list[dict]) -> list[dict]:
    evidence: list[dict] = []
    for item in materials:
        speaker = str(item.get("speaker", "unknown"))
        if speaker == "context" and item.get("relevance_score", 0) < 0.5:
            continue
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        layer = str(item.get("layer", "secondary"))
        dims = dimensions_for(text, speaker)
        if speaker != "character" and "voice" in dims:
            dims = [dim for dim in dims if dim != "voice"] or ["relationship"]
        evidence.append(
            {
                "id": f"E{len(evidence) + 1:03d}",
                "summary": text[:180],
                "quote": text[:260],
                "source": item.get("source", ""),
                "source_title": item.get("source_title", ""),
                "project": item.get("project", ""),
                "source_scope": item.get("source_scope", "project-filtered"),
                "phase": item.get("phase", "unknown"),
                "layer": layer,
                "language": item.get("language", "unknown"),
                "speaker": speaker,
                "speaker_name": item.get("speaker_name", ""),
                "line_number": item.get("line_number"),
                "dimensions": dims,
                "used_for": dims,
                "evidence_score": evidence_score(layer, speaker, dims),
                "confidence": confidence(layer, speaker, text),
                "confirmed_by_user": item.get("confirmed_by_user", "character-filtered"),
                "material_type": item.get("material_type", ""),
            }
        )
    return evidence


def gaps_for(evidence: list[dict], manifest: list[dict]) -> list[str]:
    counts: Counter[str] = Counter()
    layers: Counter[str] = Counter()
    for item in evidence:
        for dim in item.get("dimensions", []):
            counts[dim] += 1
        layers[item.get("layer", "unknown")] += 1
    gaps = []
    for key in ["voice", "personality", "timeline", "relationship"]:
        if counts[key] == 0:
            gaps.append(f"missing {key} evidence")
    if layers["official"] == 0 and layers["canon"] == 0:
        gaps.append("no canon/official source collected")
    if not any(source.get("status") in {"collected", "partial"} for source in manifest):
        gaps.append("no collected source text")
    return gaps


def write_markdown(path: Path, pack: dict) -> None:
    lines = ["# Evidence Pack", "", f"Sources collected: {pack['source_count']}", f"Character materials: {pack['character_material_count']}", ""]
    if pack["gaps"]:
        lines.extend(["## Gaps", ""])
        lines.extend(f"- {gap}" for gap in pack["gaps"])
        lines.append("")
    lines.extend(["## Evidence", "", "| ID | Used For | Speaker | Score | Summary | Source | Layer | Confidence |", "|---|---|---|---:|---|---|---|---|"])
    for item in pack["evidence"]:
        lines.append(
            f"| {item['id']} | {', '.join(item.get('used_for', []))} | {item.get('speaker', '')} | {item.get('evidence_score', '')} | "
            f"{item.get('summary', '').replace('|', '/')} | {str(item.get('source', '')).replace('|', '/')} | {item.get('layer', '')} | {item.get('confidence', '')} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build evidence pack from collected text")
    parser.add_argument("--collected", required=True, help="Collected directory containing source_manifest.json")
    parser.add_argument("--character-materials", default="", help="Optional character_materials.json override")
    parser.add_argument("--project-materials", default="", help="Reserved for project-level metadata")
    parser.add_argument("--out", required=True, help="Output evidence directory")
    parser.add_argument("--per-source", type=int, default=5, help="Fallback evidence items per raw source")
    args = parser.parse_args()

    collected = Path(args.collected)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(collected)
    materials = load_character_materials(collected, args.character_materials)
    evidence = evidence_from_materials(materials) if materials else fallback_evidence_from_sources(manifest, args.per_source)
    evidence.sort(key=lambda item: item.get("evidence_score", 0), reverse=True)
    for idx, item in enumerate(evidence, 1):
        item["id"] = f"E{idx:03d}"

    pack = {
        "evidence": evidence,
        "gaps": gaps_for(evidence, manifest),
        "source_count": len([source for source in manifest if source.get("status") in {"collected", "partial"}]),
        "character_material_count": len(materials),
    }
    (out_dir / "evidence.json").write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(out_dir / "evidence.md", pack)
    print(f"Wrote {out_dir / 'evidence.json'}")
    print(f"Wrote {out_dir / 'evidence.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
