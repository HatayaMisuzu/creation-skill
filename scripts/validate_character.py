#!/usr/bin/env python3
"""Validate creation-skill CHARACTER.md and PROJECT.md outputs.

The validator is intentionally lightweight. It checks structural contracts,
runtime sidecars, obvious placeholder leaks, backend-state leaks, and the
appearance/wardrobe layer added to the v1.0.0 skill.
"""

from __future__ import annotations

import argparse
import json
import re
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

CORE_SECTIONS = range(1, 29)
VITALITY_SECTIONS = range(29, 43)
APPEARANCE_SECTIONS = range(43, 46)

REQUIRED_SIDECARS = [
    "KERNEL.md",
    "PERFORMANCE.md",
    "APPEARANCE.md",
    "OOC_NEGATIVES.md",
    "BENCHMARK.md",
]

RUNTIME_FILES = [
    "character.json",
    "runtime-profile.json",
    "prompt-card.md",
    "voice-fingerprint.json",
]

MOJIBAKE_RE = re.compile(
    "|".join(
        [
            "\ufffd",
            "\u7476",  # yao, common in mojibake fragments
            "\u6d63",
            "\u9359",
            "\u93c8",
            "\u5bf0",
            "\u9418",
            "\u70d8",
        ]
    )
)


def parse_frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not match:
        return {}
    data: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip("\"'")
    return data


def numbered_sections(text: str) -> set[int]:
    return {int(match.group(1)) for match in re.finditer(r"^##\s+(\d+)\.", text, re.M)}


def section(text: str, number: int) -> str:
    match = re.search(rf"^##\s+{number}\.\s+.*$", text, re.M)
    if not match:
        return ""
    rest = text[match.end() :]
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
    forbidden = re.compile(
        r"(^|\s)(\+\d|tension|scene_focus|debug|speaker schedule)(\s|$)"
        r"|\u573a\u666f\u7126\u70b9\uff1a|\u72b6\u6001\u53d8\u5316\uff1a",
        re.I,
    )
    allowed = re.compile(
        r"\u4e0d\u663e\u793a|\u7981\u6b62|\u907f\u514d|\u9690\u85cf|\u4e0d\u53ef"
        r"|never|do not|forbidden|frontstage",
        re.I,
    )
    return any(forbidden.search(line) and not allowed.search(line) for line in text.splitlines())


def missing_numbers(actual: set[int], expected: range) -> list[str]:
    return [str(number) for number in expected if number not in actual]


def check_runtime_files(root: Path, strict: bool, development_mode: str) -> tuple[list[str], list[str], list[str]]:
    passes: list[str] = []
    warns: list[str] = []
    fails: list[str] = []

    for rel in RUNTIME_FILES:
        path = root / rel
        if not path.exists():
            (fails if strict else warns).append(f"missing runtime artifact: {rel}")
            continue
        if path.suffix == ".json" and read_json(path) is None:
            fails.append(f"{rel} is not valid JSON")
        else:
            passes.append(f"{rel} present")

    for rel in REQUIRED_SIDECARS:
        if (root / rel).exists():
            passes.append(f"{rel} present")
        else:
            warns.append(f"missing sidecar: {rel}")

    long_term_modes = {"long-term-development", "project-development", "session-summary"}
    if development_mode in long_term_modes:
        if (root / "MEMORY.md").exists() and (root / "DEVELOPMENT.md").exists():
            passes.append("long-term development sidecars present")
        else:
            fails.append("development_mode is enabled but MEMORY.md or DEVELOPMENT.md is missing")
    elif (root / "MEMORY.md").exists() or (root / "DEVELOPMENT.md").exists():
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
        fails.append("development_mode invalid")

    sections = numbered_sections(text)
    missing_core = missing_numbers(sections, CORE_SECTIONS)
    missing_vitality = missing_numbers(sections, VITALITY_SECTIONS)
    missing_appearance = missing_numbers(sections, APPEARANCE_SECTIONS)
    if missing_core:
        fails.append("missing standard sections: " + ", ".join(missing_core))
    else:
        passes.append("standard sections 1-28 complete")
    if missing_vitality:
        warns.append("missing vitality sections: " + ", ".join(missing_vitality))
    else:
        passes.append("vitality sections 29-42 complete")
    if missing_appearance:
        fails.append("missing appearance sections: " + ", ".join(missing_appearance))
    else:
        passes.append("appearance sections 43-45 complete")

    if re.search(r"<[^>\n]+>|\[TODO\]|TODO|\u5f85\u586b|\u672a\u586b\u5199", text, re.I) or MOJIBAKE_RE.search(text):
        fails.append("unfilled placeholders or mojibake found")
    else:
        passes.append("no placeholders or mojibake")

    row_requirements = [
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
        (43, 5, "appearance details"),
        (44, 4, "fixed outfits"),
        (45, 5, "adaptive wardrobe grammar"),
    ]
    for number, minimum, label in row_requirements:
        rows = table_rows(section(text, number))
        if rows >= minimum:
            passes.append(f"{label} rows ok")
        else:
            fails.append(f"{label} has {rows} rows; expected at least {minimum}")

    required_rules = [
        ("language matching rule", [r"match-user", r"\u4e2d\u6587\u7528\u6237.*\u4e2d\u6587", r"\u7528\u6237.*\u8bed\u8a00"]),
        ("relationship non-intrusion rule", [r"\u4e0d\u4e3b\u52a8.*\u5173\u7cfb", r"untriggered relationship"]),
        ("anti-profile-recitation rule", [r"\u4e0d\u6717\u8bfb", r"do not recite", r"profile recitation"]),
        ("learning/contamination guard", [r"\u6a21\u62df\u53f0\u8bcd.*canon", r"canon.*\u6c61\u67d3", r"contamination"]),
        ("frontstage protocol", [r"\u524d\u53f0", r"frontstage"]),
        ("decision function", [r"\u89d2\u8272\u51b3\u7b56\u51fd\u6570", r"decision function"]),
        ("internal tension", [r"\u5185\u5728\u77db\u76fe", r"\u5f20\u529b", r"tension"]),
        ("appearance stability", [r"\u5916\u8c8c", r"\u56fa\u5b9a\u8863\u7740", r"APPEARANCE", r"visual drift"]),
        ("long-term opt-in", [r"\u957f\u671f\u53d1\u5c55.*\u53ef\u9009", r"default.*fresh", r"\u9ed8\u8ba4.*fresh"]),
    ]
    for label, patterns in required_rules:
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
    passes: list[str] = []
    warns: list[str] = []
    fails: list[str] = []
    if text.lstrip().startswith("#"):
        passes.append("PROJECT.md has title")
    else:
        fails.append("PROJECT.md missing title")
    if has_backend_leak(text):
        fails.append("PROJECT.md leaks backend/debug state")
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
    if not path.exists():
        raise SystemExit(f"file not found: {path}")

    if args.mode == "project":
        passes, warns, fails = check_project(path)
    else:
        passes, warns, fails = check_character(path, args.strict_dialogue)

    report = write_report(path, passes, warns, fails)
    payload = {
        "status": "FAIL" if fails else "WARN" if warns else "PASS",
        "passes": passes,
        "warnings": warns,
        "failures": fails,
        "report": str(report),
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"{payload['status']}: {path}")
        print(f"report: {report}")
        for item in fails:
            print(f"FAIL: {item}")
        for item in warns:
            print(f"WARN: {item}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
