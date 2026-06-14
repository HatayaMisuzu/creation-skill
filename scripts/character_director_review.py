#!/usr/bin/env python3
"""Review a bad roleplay reply and produce director notes plus a repair draft."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def read(path_text: str) -> str:
    return Path(path_text).read_text(encoding="utf-8", errors="replace")


def detect_issues(character_text: str, user_message: str, bad_reply: str) -> list[str]:
    issues: list[str] = []
    if re.search(r"\b(AI|LLM|model|prompt|system|developer)\b|模型|提示词|设定卡", bad_reply, re.I):
        issues.append("meta_leak: reply exposes model/prompt/card language.")
    if re.search(r"\+\d|tension|debug|scene_focus|场景焦点|状态变化", bad_reply, re.I):
        issues.append("backend_leak: reply shows hidden simulation/debug state.")
    if len(bad_reply) > 900:
        issues.append("overlong: reply is likely explaining rather than performing.")
    if len(re.findall(r"##|人格|世界观|规则|证据|来源", bad_reply)) >= 2:
        issues.append("profile_recitation: reply reads like a character file instead of dialogue.")
    if re.search(r"[\u3040-\u30ff]{8,}|[A-Za-z]{40,}", bad_reply) and re.search(r"[\u4e00-\u9fff]", user_message):
        issues.append("language_mismatch: Chinese user received too much non-Chinese output.")
    if re.search(r"他|她|他们|队友|朋友|同伴", bad_reply) and "关系角色不主动提及" in character_text:
        issues.append("relationship_overreach: other characters may be entering without user trigger.")
    if not re.search(r"[“\"「].{2,}[”\"」]|[。！？!?]", bad_reply):
        issues.append("low_dialogue_signal: reply lacks clear spoken line or natural cadence.")
    if not issues:
        issues.append("needs_human_review: no strong static issue found; compare against voice fingerprint and source lines.")
    return issues


def repair_strategy(issues: list[str]) -> list[str]:
    strategies = []
    if any(x.startswith("meta_leak") for x in issues):
        strategies.append("Remove all prompt/model/card words; keep the response inside character perception.")
    if any(x.startswith("backend_leak") for x in issues):
        strategies.append("Convert state changes into visible action, pause, tone, or scene consequences; never print numbers.")
    if any(x.startswith("overlong") or x.startswith("profile_recitation") for x in issues):
        strategies.append("Cut exposition; use one short action beat plus direct speech that answers the user.")
    if any(x.startswith("language_mismatch") for x in issues):
        strategies.append("Answer in the user's language; keep foreign catchphrases short and meaningful.")
    if any(x.startswith("relationship_overreach") for x in issues):
        strategies.append("Do not introduce relationship characters unless the user named them or the scene requires them.")
    if any(x.startswith("low_dialogue_signal") for x in issues):
        strategies.append("Add a clear spoken line and a small sensory/action beat.")
    if not strategies:
        strategies.append("Compare the reply against source dialogue and voice fingerprint, then adjust cadence and emotional pressure.")
    return strategies


def draft_reply(user_message: str) -> str:
    user_excerpt = re.sub(r"\s+", " ", user_message).strip()[:80]
    return (
        "（她停顿了一下，像是在把情绪压回更柔软的位置。）\n"
        f"“我听见你说的了。关于‘{user_excerpt}’，我不会急着替你下结论……但我会认真陪你把这一步走完。”"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Review an OOC reply and write director notes")
    parser.add_argument("--character", required=True, help="CHARACTER.md path")
    parser.add_argument("--user-message", required=True, help="Text file containing user message")
    parser.add_argument("--bad-reply", required=True, help="Text file containing bad reply")
    parser.add_argument("--out", required=True, help="Output director-notes.md path")
    args = parser.parse_args()

    character_text = read(args.character)
    user_message = read(args.user_message)
    bad_reply = read(args.bad_reply)
    issues = detect_issues(character_text, user_message, bad_reply)
    strategies = repair_strategy(issues)

    lines = [
        "# Character Director Notes",
        "",
        "## OOC Causes",
        "",
    ]
    lines.extend(f"- {issue}" for issue in issues)
    lines.extend(["", "## Repair Strategy", ""])
    lines.extend(f"- {strategy}" for strategy in strategies)
    lines.extend(
        [
            "",
            "## New Reply Draft",
            "",
            draft_reply(user_message),
            "",
            "## Learning Patch",
            "",
            "- Treat this review as performance guidance, not canon evidence.",
            "- If merged, add it to growth-log/self-learning sections only.",
        ]
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
