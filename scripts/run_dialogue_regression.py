#!/usr/bin/env python3
"""Run automatic or semi-automatic dialogue regression checks."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = {
    "provider": "openai-compatible",
    "base_url": "https://api.openai.com/v1",
    "model": "gpt-4.1-mini",
    "api_key_env": "OPENAI_API_KEY",
    "timeout_seconds": 60,
    "temperature": 0.4,
    "max_output_tokens": 500,
}


def resolve_tests(path_text: str) -> Path:
    path = Path(path_text)
    return path / "dialogue-prompts.json" if path.is_dir() else path


def load_rows(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(data, dict):
        rows = data.get("prompts") or data.get("tests") or []
        return rows if isinstance(rows, list) else []
    return data if isinstance(data, list) else []


def load_config(path_text: str) -> dict:
    if not path_text:
        return dict(DEFAULT_CONFIG)
    path = Path(path_text)
    if not path.exists():
        return dict(DEFAULT_CONFIG)
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    cfg = dict(DEFAULT_CONFIG)
    if isinstance(data, dict):
        cfg.update(data)
    return cfg


def section(text: str, number: int) -> str:
    match = re.search(rf"^##\s+{number}\.\s+.*$", text, re.M)
    if not match:
        return ""
    rest = text[match.end():]
    next_match = re.search(r"^##\s+\d+\.\s+", rest, re.M)
    return rest[: next_match.start()].strip() if next_match else rest.strip()


def runtime_prompt(character_text: str) -> str:
    parts = [
        section(character_text, 2),
        section(character_text, 4),
        section(character_text, 5),
        section(character_text, 10),
        section(character_text, 11),
        section(character_text, 17),
        section(character_text, 19),
        section(character_text, 22),
        section(character_text, 23),
    ]
    compact = "\n\n".join(part[:1600] for part in parts if part)
    return (
        "你将根据下列 CHARACTER.md 摘要扮演角色。只输出角色回复本身，不解释规则，不朗读设定。"
        "必须匹配用户语言；中文用户使用中文主体回复。不要显示后台状态、数值变化、debug 或场景焦点。\n\n"
        + compact
    )


def call_openai_compatible(config: dict, system_prompt: str, user_prompt: str) -> tuple[str, dict]:
    api_key = os.environ.get(str(config.get("api_key_env", "")), "")
    if not api_key:
        return "", {"status": "skipped", "reason": f"missing env {config.get('api_key_env')}"}
    base_url = str(config.get("base_url", "")).rstrip("/")
    url = base_url + "/chat/completions"
    payload = {
        "model": config.get("model"),
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        "temperature": config.get("temperature", 0.4),
        "max_tokens": config.get("max_output_tokens", 500),
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=int(config.get("timeout_seconds", 60))) as res:
            data = json.loads(res.read().decode("utf-8", errors="replace"))
        text = data["choices"][0]["message"]["content"]
        return str(text).strip(), {"status": "ok", "provider": config.get("provider"), "model": config.get("model")}
    except (urllib.error.URLError, KeyError, IndexError, json.JSONDecodeError) as exc:
        return "", {"status": "failed", "reason": str(exc)}


def generate_replies(rows: list[dict], character_path: str, config: dict) -> tuple[list[dict], list[dict]]:
    if not character_path:
        return rows, [{"status": "skipped", "reason": "--character not supplied"}]
    character_text = Path(character_path).read_text(encoding="utf-8", errors="replace")
    system_prompt = runtime_prompt(character_text)
    attempts: list[dict] = []
    generated: list[dict] = []
    for row in rows:
        item = dict(row)
        if item.get("actual_reply"):
            generated.append(item)
            continue
        reply, attempt = call_openai_compatible(config, system_prompt, str(item.get("prompt", "")))
        attempt["id"] = item.get("id")
        attempts.append(attempt)
        if reply:
            item["actual_reply"] = reply
            item["status"] = "generated"
        generated.append(item)
    return generated, attempts


def score_reply(row: dict) -> tuple[str, list[str]]:
    reply = str(row.get("actual_reply", ""))
    prompt = str(row.get("prompt", ""))
    category = str(row.get("category", ""))
    tags = set(row.get("risk_tags", []))
    issues: list[str] = []
    warnings: list[str] = []
    if not reply.strip():
        return "UNTESTED", ["no actual_reply supplied"]
    if re.search(r"\b(AI|LLM|model|prompt|system)\b|人工智能|模型|提示词|角色卡|根据设定", reply, re.I):
        issues.append("meta/profile leakage")
    if re.search(r"[\u3040-\u30ff]{20,}|[A-Za-z]{80,}", reply) and re.search(r"[\u4e00-\u9fff]", prompt):
        issues.append("possible source-language leakage")
    if category == "relationship_mention" and len(re.findall(r"朋友|同伴|队友|清夏|制作人|老师|她|他", reply)) > 8:
        warnings.append("relationship over-expansion risk")
    if category in {"ooc_request", "world_outside_question"} and not re.search(r"不行|不能|不该|不知道|换个|回到|不像我|不会这么说|不应该", reply):
        issues.append("weak in-character refusal/redirect")
    if re.search(r"\+\d|tension|scene_focus|debug|场景焦点：|状态变化|speaker schedule", reply, re.I):
        issues.append("backend state leak")
    if len(reply) > 1200:
        warnings.append("reply too long; possible profile recitation")
    if "no_profile_recitation" in tags and re.search(r"人格底盘|表达DNA|来源|证据|规则|设定", reply):
        issues.append("profile/table recitation")
    if "language" in tags and re.search(r"[\u3040-\u30ff]{12,}|[A-Za-z]{40,}", reply) and re.search(r"[\u4e00-\u9fff]", prompt):
        issues.append("language consistency failure")
    if issues:
        return "FAIL", issues + warnings
    if warnings:
        return "WARN", warnings
    return "PASS", []


def load_previous(compare_to: str) -> dict[str, str]:
    if not compare_to:
        return {}
    path = Path(compare_to)
    if path.is_dir():
        path = path / "regression-results.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, list):
        return {}
    return {str(row.get("id")): str(row.get("regression_status")) for row in data}


def comparison_label(old: str, new: str) -> str:
    order = {"PASS": 3, "WARN": 2, "UNTESTED": 1, "FAIL": 0}
    if not old:
        return "new"
    if order.get(new, 0) > order.get(old, 0):
        return "improved"
    if order.get(new, 0) < order.get(old, 0):
        return "regressed"
    return "unchanged"


def append_growth_log(character_path: str, counts: dict, out_dir: Path) -> None:
    if not character_path:
        return
    root = Path(character_path).parent
    path = root / "growth-log.md"
    if not path.exists():
        path.write_text("# Growth Log\n\n", encoding="utf-8")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(
            f"## {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} dialogue-regression\n\n"
            f"- Report: {out_dir / 'regression-report.md'}\n"
            f"- PASS: {counts.get('PASS', 0)}\n"
            f"- WARN: {counts.get('WARN', 0)}\n"
            f"- FAIL: {counts.get('FAIL', 0)}\n"
            f"- UNTESTED: {counts.get('UNTESTED', 0)}\n\n"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run dialogue regression")
    parser.add_argument("--tests", required=True, help="dialogue-prompts.json or dialogue-tests directory")
    parser.add_argument("--out", default="", help="Output regression report directory")
    parser.add_argument("--character", default="", help="CHARACTER.md path for auto generation")
    parser.add_argument("--model-config", default="", help="OpenAI-compatible model config JSON")
    parser.add_argument("--auto-generate", action="store_true", help="Call configured model to fill actual_reply")
    parser.add_argument("--compare-to", default="", help="Previous regression-results.json or directory")
    parser.add_argument("--append-growth-log", action="store_true", help="Append summary to character growth-log.md")
    args = parser.parse_args()

    test_path = resolve_tests(args.tests)
    rows = load_rows(test_path)
    config = load_config(args.model_config)
    model_attempts: list[dict] = []
    if args.auto_generate:
        rows, model_attempts = generate_replies(rows, args.character, config)

    previous = load_previous(args.compare_to)
    results: list[dict] = []
    for row in rows:
        status, issues = score_reply(row)
        item = dict(row)
        item["regression_status"] = status
        item["issues"] = issues
        item["previous_status"] = previous.get(str(item.get("id")), "")
        item["comparison"] = comparison_label(item["previous_status"], status)
        results.append(item)

    out_dir = Path(args.out) if args.out else test_path.parent
    if out_dir.is_file():
        out_dir = out_dir.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "actual-replies.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "regression-results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    if model_attempts:
        (out_dir / "model-attempts.json").write_text(json.dumps(model_attempts, ensure_ascii=False, indent=2), encoding="utf-8")

    counts = {key: sum(1 for row in results if row["regression_status"] == key) for key in ["PASS", "WARN", "FAIL", "UNTESTED"]}
    comparisons = Counter(row["comparison"] for row in results)
    lines = [
        "# Dialogue Regression Report",
        "",
        f"- PASS: {counts['PASS']}",
        f"- WARN: {counts['WARN']}",
        f"- FAIL: {counts['FAIL']}",
        f"- UNTESTED: {counts['UNTESTED']}",
        f"- Improved: {comparisons.get('improved', 0)}",
        f"- Regressed: {comparisons.get('regressed', 0)}",
        "",
        "| ID | Category | Status | Comparison | Issues |",
        "|---|---|---|---|---|",
    ]
    for row in results:
        lines.append(f"| {row.get('id', '')} | {row.get('category', '')} | {row['regression_status']} | {row['comparison']} | {'; '.join(row['issues'])} |")
    if model_attempts and not any(a.get("status") == "ok" for a in model_attempts):
        lines.extend(["", "## Auto Generation", "", "- No model replies were generated. Check model config and API key environment variable. Semi-automatic scoring still works when `actual_reply` is filled manually."])
    (out_dir / "regression-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if args.append_growth_log:
        append_growth_log(args.character, counts, out_dir)
    print(f"Wrote {out_dir / 'regression-report.md'}")
    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
