#!/usr/bin/env python3
"""Discover candidate sources for a virtual character profile.

Results are candidates only until the user confirms them. The script favors
project-first search and includes Chinese secondary sources such as Moegirl
百科 for Chinese names, localized terminology, and fandom orientation.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Iterable


SEARCH_ENDPOINT = "https://duckduckgo.com/html/?q="


def slugify(text: str) -> str:
    value = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff\u3040-\u30ff]+", "-", text.strip())
    value = re.sub(r"-+", "-", value).strip("-")
    return value.lower() or "character"


def fetch_search(query: str, limit: int) -> list[dict[str, str]]:
    if limit <= 0:
        return []
    url = SEARCH_ENDPOINT + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=12) as res:
            body = res.read().decode("utf-8", errors="replace")
    except Exception:
        return []

    results: list[dict[str, str]] = []
    pattern = re.compile(r'<a rel="nofollow" class="result__a" href="([^"]+)">(.*?)</a>', re.S)
    for match in pattern.finditer(body):
        href = html.unescape(match.group(1))
        title = re.sub(r"<.*?>", "", html.unescape(match.group(2))).strip()
        if "uddg=" in href:
            parsed = urllib.parse.urlparse(href)
            qs = urllib.parse.parse_qs(parsed.query)
            href = qs.get("uddg", [href])[0]
        results.append({"title": title or href, "url": href})
        if len(results) >= limit:
            break
    return results


def classify_url(url: str, title: str) -> tuple[str, str, str, str]:
    text = f"{url} {title}".lower()
    if any(x in text for x in ["google.com/search", "duckduckgo.com", "bing.com/search"]):
        return "manual-search", "secondary", "search query placeholder; open and review before use", "unknown"
    if any(x in text for x in ["youtube.com", "youtu.be", "bilibili.com", "nicovideo.jp"]):
        return "video", "transcript", "possible transcript or primary scene material", "unknown"
    if any(x in text for x in ["zh.moegirl.org.cn", "moegirl.org.cn", "萌娘百科"]):
        return "moegirl", "secondary", "high-value Chinese ACG reference; useful for Chinese names and aliases, cross-check canon claims", "zh"
    if any(x in text for x in ["official", "公式", "character", "chara", "game", "anime"]):
        return "official-page", "official", "possible official identity or profile", "unknown"
    if any(x in text for x in ["fandom", "wikipedia", "pixiv", "dic.pixiv", "wiki", "百科"]):
        return "wiki", "secondary", "useful map; cross-check before canon claims", "unknown"
    if any(x in text for x in ["quote", "voice", "transcript", "script", "台词", "セリフ", "ボイス"]):
        return "text", "transcript", "possible voice or dialogue evidence", "unknown"
    return "web", "secondary", "candidate background source", "unknown"


def infer_project_type(work: str, character_type: str) -> str:
    text = f"{work} {character_type}".lower()
    if character_type in {"anime", "game", "novel", "vtuber", "oc", "mixed", "mascot", "npc"}:
        return character_type
    if any(x in text for x in ["game", "手游", "ゲーム", "idolmaster"]):
        return "game"
    if any(x in text for x in ["anime", "动画", "アニメ"]):
        return "anime"
    if any(x in text for x in ["novel", "小说", "ラノベ"]):
        return "novel"
    if any(x in text for x in ["vtuber", "直播", "channel"]):
        return "vtuber"
    return "mixed"


def candidate(title: str, url: str, query: str, user_provided: bool = False, project: str = "", project_type: str = "mixed") -> dict[str, object]:
    source_type, layer, value, language = classify_url(url, title)
    decision = "needs-user-review"
    if user_provided:
        layer = "user-provided"
        value = "user-provided URL; confirm intended use"
    elif layer in {"official", "transcript"}:
        decision = "recommended"
    elif source_type == "moegirl":
        decision = "recommended"
    elif source_type == "wiki":
        decision = "optional"
    return {
        "decision": decision,
        "title": title or url,
        "url": url,
        "query": query,
        "project": project,
        "project_type": project_type,
        "source_type": source_type,
        "language": language,
        "suggested_layer": layer,
        "likely_value": value,
        "risk": "unconfirmed until user review",
        "confirmed_by_user": False,
    }


def wants_chinese(language: str) -> bool:
    value = language.lower()
    return value == "auto" or value.startswith(("zh", "cn", "中文", "汉语"))


def wants_japanese(language: str, character_type: str) -> bool:
    value = language.lower()
    return value.startswith(("ja", "jp", "日文", "日本語")) or character_type in {"anime", "game", "vtuber"}


def search_queries(character: str, work: str, language: str, character_type: str, mode: str = "both") -> list[str]:
    base = f"{character} {work}".strip()
    queries: list[str] = []
    if mode in {"character", "both"}:
        queries.extend([
            f"{base} official character profile",
            f"{base} wiki",
            f"{base} voice lines",
            f"{base} transcript",
            f"{base} quotes",
        ])
        if wants_chinese(language):
            queries.extend([
                f"{base} 萌娘百科",
                f"site:zh.moegirl.org.cn {base}",
                f"{base} 中文名",
                f"{base} 台词",
                f"{base} 剧情",
            ])
        if wants_japanese(language, character_type):
            queries.extend([
                f"{base} 公式",
                f"{base} キャラクター",
                f"{base} セリフ",
                f"{base} ボイス",
            ])
        if character_type == "vtuber":
            queries.extend([f"{base} official channel", f"{base} stream transcript"])
    if work and mode in {"project", "both"}:
        project_queries = [
            f"{work} official PV",
            f"{work} official YouTube character story {character}",
            f"{work} gameplay story {character}",
            f"{work} episode transcript {character}",
            f"{work} unit story {character}",
            f"{work} voice collection {character}",
        ]
        if wants_chinese(language):
            project_queries.extend([
                f"{work} 萌娘百科 {character}",
                f"site:zh.moegirl.org.cn {work} {character}",
                f"{work} 剧情 {character}",
                f"{work} 角色剧情 {character}",
                f"{work} 官方视频 {character}",
            ])
        if wants_japanese(language, character_type):
            project_queries.extend([
                f"{work} 公式動画 {character}",
                f"{work} ストーリー {character}",
                f"{work} キャラコミュ {character}",
            ])
        queries.extend(project_queries)
    return list(dict.fromkeys(q for q in queries if q.strip()))


def write_markdown(path: Path, rows: Iterable[dict[str, object]]) -> None:
    lines = [
        "# Candidate Sources",
        "",
        "These are candidates only. Confirm sources before extraction.",
        "",
        "| Decision | Project | Project Type | Title | Type | Layer | Language | Value | Risk | URL |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        safe = {k: str(v).replace("|", "/") for k, v in row.items()}
        lines.append(
            "| {decision} | {project} | {project_type} | {title} | {source_type} | {suggested_layer} | {language} | {likely_value} | {risk} | {url} |".format(
                **safe
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Discover character source candidates")
    parser.add_argument("--character", required=True, help="Character name")
    parser.add_argument("--work", default="", help="Source work/franchise")
    parser.add_argument("--project", default="", help="Project/franchise override, defaults to --work")
    parser.add_argument("--type", default="mixed", choices=["anime", "game", "novel", "vtuber", "oc", "mixed", "mascot", "npc"])
    parser.add_argument("--mode", default="both", choices=["character", "project", "both"], help="Search character-specific, project-level, or both")
    parser.add_argument("--language", default="auto", help="Preferred language")
    parser.add_argument("--url", action="append", default=[], help="User-provided URL, repeatable")
    parser.add_argument("--out", default="", help="Output work directory")
    parser.add_argument("--limit", type=int, default=5, help="Search results per query")
    args = parser.parse_args()

    char_id = slugify(args.character)
    project = args.project or args.work
    project_type = infer_project_type(project, args.type)
    out_dir = Path(args.out) if args.out else Path("work") / char_id / "sources"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, object]] = []
    for url in args.url:
        rows.append(candidate(url, url, "user-provided", user_provided=True, project=project, project_type=project_type))

    queries = search_queries(args.character, args.work, args.language, args.type, args.mode)
    for query in queries:
        found = fetch_search(query, args.limit)
        if found:
            for item in found:
                rows.append(candidate(item["title"], item["url"], query, project=project, project_type=project_type))
        else:
            search_url = "https://www.google.com/search?q=" + urllib.parse.quote(query)
            rows.append(candidate(f"Manual search: {query}", search_url, query, project=project, project_type=project_type))

    deduped: list[dict[str, object]] = []
    seen = set()
    for row in rows:
        key = str(row["url"]).split("#", 1)[0]
        if key in seen:
            continue
        seen.add(key)
        row["id"] = f"S{len(deduped) + 1:03d}"
        deduped.append(row)

    json_path = out_dir / "candidates.json"
    md_path = out_dir / "candidates.md"
    json_path.write_text(json.dumps(deduped, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(md_path, deduped)
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
