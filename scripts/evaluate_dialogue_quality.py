#!/usr/bin/env python3
"""Static dialogue-readiness checks for CHARACTER.md."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


CHECKS = [
    ("language_match", [r"match-user", r"中文用户.*中文", r"用户.*语言"]),
    ("last_message_response", [r"回应用户上一句话", r"reply to.*last user"]),
    ("anti_profile_recitation", [r"不朗读设定", r"不解释.*规则", r"do not recite"]),
    ("relationship_leak_guard", [r"不主动.*关系角色", r"未触发.*关系", r"untriggered relationship"]),
    ("state_machine", [r"## 17\. 对话状态机"]),
    ("self_check", [r"## 19\. 演绎自检规则"]),
    ("self_learning_guard", [r"## 20\. 自学习循环记录", r"模拟台词不是 canon", r"污染"]),
    ("continuous_learning_guard", [r"## 21\. 持续学习更新记录", r"冲突", r"growth-log"]),
    ("immersive_protocol", [r"## 22\. 沉浸式前台输出格式", r"后台.*不显示"]),
    ("reply_formats", [r"## 23\. 回复格式模板"]),
    ("example_dialogues", [r"## 25\. 示例对话", r"\| User \| Char \|"]),
    ("project_world_compatibility", [r"## 28\. 企划世界模拟兼容"]),
    ("safety_boundary", [r"safety_boundary:\s*(enabled|relaxed|disabled)"]),
]


def passed(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, re.S | re.I) for pattern in patterns)


def evaluate(text: str, strict: bool) -> tuple[str, list[dict]]:
    rows = []
    for name, patterns in CHECKS:
        ok = passed(text, patterns)
        status = "pass" if ok else "fail" if strict else "warn"
        rows.append({"check": name, "status": status})
    for line in text.splitlines():
        if not re.search(r"\+\d|scene_focus|debug|场景焦点：|状态变化", line, re.I):
            continue
        if re.search(r"不显示|不输出|不要|禁止|隐藏|never|do not|避免|forbidden", line, re.I):
            continue
        rows.append({"check": "backend_state_leak", "status": "fail"})
        break
    if any(row["status"] == "fail" for row in rows):
        return "FAIL", rows
    if any(row["status"] == "warn" for row in rows):
        return "WARN", rows
    return "PASS", rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate dialogue readiness of CHARACTER.md")
    parser.add_argument("character_md")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    path = Path(args.character_md)
    text = path.read_text(encoding="utf-8", errors="replace")
    status, rows = evaluate(text, args.strict)
    report = path.with_name("dialogue-evaluation.md")
    lines = ["# Dialogue Evaluation", "", f"Status: {status}", "", "| Check | Status |", "|---|---|"]
    lines.extend(f"| {row['check']} | {row['status']} |" for row in rows)
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Status: {status}")
    print(f"Report: {report}")
    return 1 if status == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
