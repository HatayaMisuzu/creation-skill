#!/usr/bin/env python3
"""Export CHARACTER.md into runtime adapter formats.

CHARACTER.md remains the source of truth. Adapter exports are generated copies
or compact views for specific runtimes and should never be edited as canon.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path


TARGETS = ["hermes", "world-tree", "sillytavern", "character-ai", "json", "compact", "prompt-snippet"]
PROFILES = ["full", "compact", "runtime"]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def frontmatter(text: str) -> dict:
    match = re.match(r"---\n(.*?)\n---\n", text, re.S)
    data: dict[str, str] = {}
    if not match:
        return data
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip().strip("\"'")
    return data


def section(text: str, number: int) -> str:
    match = re.search(rf"^##\s+{number}\.\s+.*$", text, re.M)
    if not match:
        return ""
    rest = text[match.end():]
    next_match = re.search(r"^##\s+\d+\.\s+", rest, re.M)
    return rest[: next_match.start()].strip() if next_match else rest.strip()


def compact_from_character(text: str, meta: dict) -> str:
    parts = [
        f"# {meta.get('display_name', meta.get('name', 'Character'))} Runtime Prompt",
        "",
        "## Identity",
        section(text, 2)[:900] or "Use CHARACTER.md identity section.",
        "",
        "## Core Personality",
        section(text, 4)[:1200] or "Use CHARACTER.md personality section.",
        "",
        "## Voice DNA",
        section(text, 5)[:1200] or "Use CHARACTER.md voice section.",
        "",
        "## Dialogue Rules",
        section(text, 10)[:1200] or "Answer the user's latest message in character.",
        "",
        "## Language Rule",
        "Match the user's language. For Chinese users, answer mainly in Chinese; keep Japanese/English only as short catchphrases, names, or quoted source flavor.",
        "",
        "## Relationship Rule",
        "Do not proactively introduce relationship characters unless the user mentioned them or the scene clearly requires them.",
        "",
        "## Safety Boundary",
        section(text, 11)[:900] or "Respect the active safety_boundary mode in frontmatter.",
    ]
    return "\n".join(parts).strip() + "\n"


def prompt_snippet(src: Path, text: str, meta: dict) -> str:
    prompt_card = src.parent / "prompt-card.md"
    if prompt_card.exists():
        return read_text(prompt_card)
    return compact_from_character(text, meta)


def load_runtime(src: Path) -> dict:
    path = src.parent / "runtime-profile.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {"error": "runtime-profile.json is not valid JSON"}


def write_manifest(out_dir: Path, target: str, profile: str, source: Path) -> None:
    manifest = {
        "target": target,
        "profile": profile,
        "source": str(source),
        "source_of_truth": "CHARACTER.md",
        "editable": False,
    }
    (out_dir / "export-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def export_json(out_dir: Path, text: str, meta: dict, runtime: dict, profile: str) -> None:
    payload = {"frontmatter": meta, "profile": profile, "runtime_profile": runtime}
    if profile == "full":
        payload["markdown"] = text
    else:
        payload["runtime_prompt"] = compact_from_character(text, meta)
    (out_dir / "character.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def export_sillytavern(out_dir: Path, text: str, meta: dict, compact: str) -> None:
    name = meta.get("display_name", meta.get("name", "character"))
    card = {
        "spec": "chara_card_v2",
        "spec_version": "2.0",
        "data": {
            "name": name,
            "description": compact,
            "personality": section(text, 4)[:1600],
            "scenario": section(text, 7)[:1200],
            "first_mes": f"（{name}抬起视线，语气放轻。）“你来了。今天想从哪里开始？”",
            "mes_example": section(text, 25)[:1800],
            "creator_notes": "Generated from CHARACTER.md. Keep canon changes in the source card, not this export.",
            "tags": ["virtual-character", "roleplay", "creation-skill"],
        },
    }
    (out_dir / "sillytavern-card.json").write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")


def export_character_ai(out_dir: Path, text: str, meta: dict, compact: str) -> None:
    name = meta.get("display_name", meta.get("name", "character"))
    lines = [
        f"# {name} Character-AI Style Definition",
        "",
        "## Short Description",
        compact.splitlines()[0].lstrip("# ").strip()[:500],
        "",
        "## Long Definition",
        compact[:3200],
        "",
        "## Example Dialogue",
        section(text, 25)[:2200] or "User: 你今天还好吗？\nChar: “嗯……我在。你呢？”",
        "",
        "## Export Note",
        "This is a portable definition-style export. CHARACTER.md remains the source of truth.",
    ]
    (out_dir / "character-ai-definition.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Export CHARACTER.md adapter formats")
    parser.add_argument("character_md", nargs="?", help="Path to CHARACTER.md")
    parser.add_argument("--character", dest="character_md_flag", default="", help="Path to CHARACTER.md; alias for positional")
    parser.add_argument("--target", required=True, choices=TARGETS)
    parser.add_argument("--profile", default="full", choices=PROFILES)
    parser.add_argument("--out", default="", help="Output directory")
    args = parser.parse_args()

    character_arg = args.character_md_flag or args.character_md
    if not character_arg:
        parser.error("CHARACTER.md path is required as positional argument or --character")
    src = Path(character_arg)
    text = read_text(src)
    meta = frontmatter(text)
    runtime = load_runtime(src)
    out_dir = Path(args.out) if args.out else src.parent / "exports" / args.target
    out_dir.mkdir(parents=True, exist_ok=True)

    compact = prompt_snippet(src, text, meta) if args.profile != "full" or args.target in {"compact", "prompt-snippet", "character-ai", "sillytavern"} else compact_from_character(text, meta)

    if args.target in {"hermes", "world-tree"}:
        shutil.copy2(src, out_dir / "CHARACTER.md")
        if (src.parent / "prompt-card.md").exists():
            shutil.copy2(src.parent / "prompt-card.md", out_dir / "prompt-card.md")
        if (src.parent / "runtime-profile.json").exists():
            shutil.copy2(src.parent / "runtime-profile.json", out_dir / "runtime-profile.json")
    elif args.target == "json":
        export_json(out_dir, text, meta, runtime, args.profile)
    elif args.target == "compact":
        (out_dir / "compact-character.md").write_text(compact_from_character(text, meta), encoding="utf-8")
    elif args.target == "prompt-snippet":
        (out_dir / "prompt-snippet.md").write_text(prompt_snippet(src, text, meta), encoding="utf-8")
    elif args.target == "sillytavern":
        export_sillytavern(out_dir, text, meta, compact)
    elif args.target == "character-ai":
        export_character_ai(out_dir, text, meta, compact)
    else:
        raise ValueError(args.target)

    write_manifest(out_dir, args.target, args.profile, src)
    print(f"Wrote export to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
