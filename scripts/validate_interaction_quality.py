#!/usr/bin/env python3
"""Validate immersive interaction/runtime quality for a character card."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


REQUIRED_RUNTIME_SECTIONS = {17: "dialogue state machine", 18: "relationship progress", 19: "performance self-check"}
IMMERSION_SECTIONS = {22: "frontstage response format", 23: "reply templates", 24: "greetings", 25: "example dialogues", 26: "intent router", 27: "pacing", 28: "project world simulation"}


def section(text: str, number: int) -> str:
    match = re.search(rf"^##\s+{number}\.\s+.*$", text, re.M)
    if not match:
        return ""
    rest = text[match.end():]
    next_match = re.search(r"^##\s+\d+\.\s+", rest, re.M)
    return rest[: next_match.start()].strip() if next_match else rest.strip()


def table_rows(text: str) -> int:
    rows = [line for line in text.splitlines() if line.strip().startswith("|")]
    return max(0, len(rows) - 2)


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None


def has_backend_leak(text: str) -> bool:
    for line in text.splitlines():
        if not re.search(r"\+\d|tension|scene_focus|debug|场景焦点：|状态变化|speaker schedule", line, re.I):
            continue
        if re.search(r"不显示|不输出|不要|禁止|隐藏|hidden|never|do not|forbidden|避免|禁用", line, re.I):
            continue
        return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate immersive interaction quality")
    parser.add_argument("--character", required=True, help="CHARACTER.md path")
    parser.add_argument("--dir", default="", help="Character output directory")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    character = Path(args.character)
    root = Path(args.dir) if args.dir else character.parent
    text = character.read_text(encoding="utf-8", errors="replace")
    failures: list[str] = []
    warnings: list[str] = []
    passes: list[str] = []

    for number, label in REQUIRED_RUNTIME_SECTIONS.items():
        passes.append(f"section {number} present: {label}") if section(text, number) else failures.append(f"missing section {number}: {label}")
    for number, label in IMMERSION_SECTIONS.items():
        passes.append(f"section {number} present: {label}") if section(text, number) else warnings.append(f"missing immersive section {number}: {label}")

    if re.search(r"match-user|用户.*语言|中文用户|语言一致|response_language", text, re.I):
        passes.append("language consistency rule present")
    else:
        failures.append("missing language consistency rule")
    if re.search(r"不主动.*(关系|其他角色|他人)|relationship.*not.*proactive|unless.*user.*mention", text, re.I | re.S):
        passes.append("relationship non-intrusion rule present")
    else:
        failures.append("missing relationship non-intrusion rule")
    if re.search(r"后台|frontstage-only|不显示.*(数值|debug|调度|状态)|hidden.*state", text, re.I):
        passes.append("frontstage-only/backstage hiding rule present")
    else:
        warnings.append("frontstage/backstage hiding rule may be weak")
    if has_backend_leak(text):
        failures.append("backend/debug state appears in CHARACTER.md visible text")

    runtime = load_json(root / "runtime-profile.json")
    if runtime:
        passes.append("runtime-profile.json readable")
    else:
        warnings.append("missing or unreadable runtime-profile.json")
    prompt_card = root / "prompt-card.md"
    if prompt_card.exists() and prompt_card.read_text(encoding="utf-8", errors="replace").strip():
        passes.append("prompt-card.md present")
    else:
        warnings.append("missing prompt-card.md")
    voice_fp = load_json(root / "voice-fingerprint.json")
    if isinstance(voice_fp, dict) and "forbidden_drift" in voice_fp:
        passes.append("voice-fingerprint.json has forbidden_drift")
    else:
        warnings.append("missing voice-fingerprint.json or forbidden_drift")
    tests = load_json(root / "dialogue-tests" / "dialogue-prompts.json")
    prompts = tests.get("prompts", []) if isinstance(tests, dict) else tests if isinstance(tests, list) else []
    if len(prompts) >= 20:
        passes.append("dialogue test set has at least 20 prompts")
    else:
        warnings.append("missing dialogue-tests/dialogue-prompts.json or fewer than 20 prompts")

    examples = section(text, 25)
    if examples:
        rows = table_rows(examples)
        if rows >= 3 or re.search(r"User:|用户[:：]", examples):
            passes.append("example dialogue signal present")
        else:
            warnings.append("example dialogue section may be too thin")

    if args.strict and warnings:
        failures.extend("strict: " + item for item in warnings)
        warnings = []
    status = "FAIL" if failures else "WARN" if warnings else "PASS"
    report = root / "interaction-validation.md"
    lines = ["# Interaction Validation", "", f"Status: {status}", "", "## Passes", ""]
    lines.extend(f"- {item}" for item in passes) if passes else lines.append("- none")
    lines.extend(["", "## Warnings", ""])
    lines.extend(f"- {item}" for item in warnings) if warnings else lines.append("- none")
    lines.extend(["", "## Failures", ""])
    lines.extend(f"- {item}" for item in failures) if failures else lines.append("- none")
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Status: {status}")
    print(f"Report: {report}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
