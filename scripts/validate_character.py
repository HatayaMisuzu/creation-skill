#!/usr/bin/env python3
"""Validate 1.0.0 CHARACTER.md and PROJECT.md outputs."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


REQUIRED_FRONTMATTER = [
    "name",
    "display_name",
    "character_type",
    "source_work",
    "default_phase",
    "response_language",
    "safety_boundary",
    "version",
]


def parse_frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not match:
        return {}
    data: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip().strip("\"'")
    return data


def numbered_sections(text: str) -> set[int]:
    return {int(match.group(1)) for match in re.finditer(r"^##\s+(\d+)\.", text, re.M)}


def section(text: str, number: int) -> str:
    match = re.search(rf"^##\s+{number}\.\s+.*$", text, re.M)
    if not match:
        return ""
    rest = text[match.end():]
    next_match = re.search(r"^##\s+\d+\.\s+", rest, re.M)
    return rest[: next_match.start()].strip() if next_match else rest.strip()


def table_rows(block: str) -> int:
    rows = [line for line in block.splitlines() if line.strip().startswith("|")]
    return max(0, len(rows) - 2)


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None


def has_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, re.I | re.S) for pattern in patterns)


def has_backend_leak(text: str) -> bool:
    forbidden = re.compile(r"(^|\s)(\+\d|tension|scene_focus|debug|speaker schedule)(\s|$)|场景焦点：|状态变化：", re.I)
    allowed_context = re.compile(r"不显示|禁止|避免|隐藏|不可|never|do not|forbidden|frontstage", re.I)
    for line in text.splitlines():
        if forbidden.search(line) and not allowed_context.search(line):
            return True
    return False


def check_json(path: Path, rel: str, passes: list[str], warns: list[str], fails: list[str], strict: bool) -> None:
    if not path.exists():
        (fails if strict else warns).append(f"missing runtime artifact: {rel}")
        return
    if path.suffix.lower() == ".json" and read_json(path) is None:
        fails.append(f"{rel} is not valid JSON")
    else:
        passes.append(f"{rel} present")


def check_runtime_files(root: Path, strict: bool, development_mode: str) -> tuple[list[str], list[str], list[str]]:
    passes: list[str] = []
    warns: list[str] = []
    fails: list[str] = []
    for rel in ["character.json", "runtime-profile.json", "prompt-card.md", "voice-fingerprint.json"]:
        check_json(root / rel, rel, passes, warns, fails, strict)
    for rel in ["KERNEL.md", "PERFORMANCE.md", "OOC_NEGATIVES.md", "BENCHMARK.md"]:
        if (root / rel).exists():
            passes.append(f"{rel} present")
        else:
            warns.append(f"missing 1.0.0 sidecar: {rel}")
    memory = root / "MEMORY.md"
    development = root / "DEVELOPMENT.md"
    if development_mode in {"long-term-development", "project-development", "session-summary"}:
        if memory.exists() and development.exists():
            passes.append("long-term development sidecars present")
        else:
            fails.append("development_mode is enabled but MEMORY.md or DEVELOPMENT.md is missing")
    else:
        if memory.exists() or development.exists():
            warns.append("fresh mode has persistent development sidecars; confirm this is intentional")
        else:
            passes.append("fresh mode does not create persistent development sidecars")
    return passes, warns, fails


def check_character(path: Path, strict_dialogue: bool) -> tuple[list[str], list[str], list[str]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    root = path.parent
    passes: list[str] = []
    warns: list[str] = []
    fails: list[str] = []

    fm = parse_frontmatter(text)
    missing_fm = [key for key in REQUIRED_FRONTMATTER if not fm.get(key)]
    if missing_fm:
        fails.append("missing frontmatter fields: " + ", ".join(missing_fm))
    else:
        passes.append("frontmatter complete")
    if fm.get("safety_boundary") in {"enabled", "relaxed", "disabled"}:
        passes.append("safety_boundary valid")
    else:
        fails.append("safety_boundary must be enabled, relaxed, or disabled")
    development_mode = fm.get("development_mode", "fresh")
    if development_mode in {"fresh", "session-summary", "long-term-development", "project-development"}:
        passes.append("development_mode valid")
    else:
        fails.append("development_mode must be fresh, session-summary, long-term-development, or project-development")

    sections = numbered_sections(text)
    missing_core = [str(i) for i in range(1, 29) if i not in sections]
    if missing_core:
        fails.append("missing standard sections: " + ", ".join(missing_core))
    else:
        passes.append("standard sections 1-28 complete")
    missing_vitality = [str(i) for i in range(29, 43) if i not in sections]
    if missing_vitality:
        warns.append("missing 1.0.0 vitality sections: " + ", ".join(missing_vitality))
    else:
        passes.append("1.0.0 vitality sections 29-42 complete")

    if re.search(r"<[^>\n]+>|\[TODO\]|TODO|待填|未填写|�", text, re.I):
        fails.append("unfilled placeholders or mojibake found")
    else:
        passes.append("no placeholders or mojibake")

    row_checks = [
        (4, 10, "personality chassis"),
        (5, 7, "expression DNA"),
        (6, 10, "scene responses"),
        (14, 1, "key evidence"),
        (17, 8, "dialogue state machine"),
        (18, 4, "relationship progress"),
        (23, 4, "reply format templates"),
        (24, 5, "greetings"),
        (25, 3, "example dialogues"),
        (26, 6, "intent router"),
    ]
    for number, minimum, label in row_checks:
        rows = table_rows(section(text, number))
        if rows >= minimum:
            passes.append(f"{label} rows ok")
        else:
            fails.append(f"{label} has {rows} rows; expected at least {minimum}")

    required_patterns = [
        ("language matching rule", [r"match-user", r"中文用户.*中文", r"用户.*语言"]),
        ("relationship non-intrusion rule", [r"不主动.*关系", r"用户.*提到.*关系", r"untriggered relationship"]),
        ("anti-profile-recitation rule", [r"不朗读", r"不解释.*角色卡", r"do not recite"]),
        ("learning/contamination guard", [r"模拟台词.*不.*canon", r"不更新 canon", r"污染"]),
        ("frontstage protocol", [r"前台", r"后台.*不.*显示", r"frontstage"]),
        ("decision function", [r"角色决策函数", r"第一反应.*核心动机"]),
        ("internal tension", [r"内在矛盾", r"张力"]),
        ("OOC negatives", [r"OOC 反例", r"OOC_NEGATIVES"]),
        ("long-term opt-in", [r"长期发展.*可选", r"默认 fresh", r"不写入长期记忆"]),
    ]
    for label, patterns in required_patterns:
        if has_any(text, patterns):
            passes.append(f"{label} present")
        else:
            fails.append(f"missing {label}")

    if has_backend_leak(text):
        fails.append("backend/debug state appears in CHARACTER.md")
    else:
        passes.append("no obvious backend state leak")

    file_passes, file_warns, file_fails = check_runtime_files(root, strict_dialogue, development_mode)
    passes.extend(file_passes)
    warns.extend(file_warns)
    fails.extend(file_fails)
    if strict_dialogue and warns:
        fails.extend("strict dialogue: " + item for item in warns)
        warns = []
    return passes, warns, fails


def check_project(path: Path) -> tuple[list[str], list[str], list[str]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    root = path.parent
    passes: list[str] = []
    warns: list[str] = []
    fails: list[str] = []
    if text.lstrip().startswith("#"):
        passes.append("PROJECT.md has title")
    else:
        fails.append("PROJECT.md missing title")
    required = [
        "project.json",
        "timeline.md",
        "relationship-graph.md",
        "scenes/group-dynamics.md",
        "scenes/shared-scene-rules.md",
        "simulation/world-state.json",
        "simulation/public-scene-memory.md",
    ]
    missing = [rel for rel in required if not (root / rel).exists()]
    if missing:
        fails.append("missing project pack files: " + ", ".join(missing))
    else:
        passes.append("project pack files complete")
    if has_any(text, [r"上帝视角", r"observer", r"director", r"world_admin"]):
        passes.append("god-view/user mode rules present")
    else:
        fails.append("missing project simulation user modes")
    if has_any(text, [r"未点名.*不", r"不抢戏", r"Unmentioned characters"]):
        passes.append("group non-stealing rule present")
    else:
        fails.append("missing group non-stealing rule")
    latest = root / "simulation" / "latest-scene.md"
    if latest.exists():
        scene = latest.read_text(encoding="utf-8", errors="replace")
        if has_backend_leak(scene):
            fails.append("latest-scene.md leaks backend/debug state")
        else:
            passes.append("latest-scene.md has no obvious backend leak")
    return passes, warns, fails


def write_report(path: Path, passes: list[str], warns: list[str], fails: list[str]) -> Path:
    report = path.with_name("validation-report.md")
    status = "FAIL" if fails else "WARN" if warns else "PASS"
    lines = ["# Validation Report", "", f"File: {path}", "", "## Result", "", f"Status: {status}"]
    for title, items in [("Passes", passes), ("Warnings", warns), ("Failures", fails)]:
        lines.extend(["", f"## {title}", ""])
        if items:
            lines.extend(f"- {item}" for item in items)
        else:
            lines.append("- none")
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate CHARACTER.md or PROJECT.md")
    parser.add_argument("path", help="Path to CHARACTER.md or PROJECT.md")
    parser.add_argument("--json", action="store_true", help="Print machine-readable result")
    parser.add_argument("--mode", default="character", choices=["character", "project"], help="Validation mode")
    parser.add_argument("--strict-dialogue", action="store_true", help="Fail on warnings in character mode")
    args = parser.parse_args()

    path = Path(args.path)
    passes, warns, fails = check_project(path) if args.mode == "project" else check_character(path, args.strict_dialogue)
    report = write_report(path, passes, warns, fails)
    result = {"status": "FAIL" if fails else "WARN" if warns else "PASS", "passes": passes, "warnings": warns, "failures": fails, "report": str(report)}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Status: {result['status']}")
        print(f"Pass: {len(passes)} Warn: {len(warns)} Fail: {len(fails)}")
        print(f"Report: {report}")
        for item in fails:
            print(f"FAIL: {item}")
        for item in warns:
            print(f"WARN: {item}")
    return 1 if fails else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except UnicodeEncodeError:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        raise
