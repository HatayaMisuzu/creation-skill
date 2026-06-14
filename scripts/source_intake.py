#!/usr/bin/env python3
"""Normalize user-provided source hints into reviewable source candidates.

Accepts direct URLs, local files, YouTube channel names/handles, playlists, and
search queries. It is deliberately agent-generic: when a tool such as yt-dlp is
available it expands playlists/channels; otherwise it records fallback actions
instead of failing the whole workflow.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import urllib.parse
from pathlib import Path


def slugify(text: str) -> str:
    value = re.sub(r"[^0-9A-Za-z\u4e00-\u9fffぁ-んァ-ン一-龥]+", "-", text.strip())
    return re.sub(r"-+", "-", value).strip("-").lower() or "source-intake"


def classify(url: str, title: str = "") -> tuple[str, str, str]:
    text = f"{url} {title}".lower()
    if "google.com/search" in text or "duckduckgo.com" in text or "bing.com/search" in text:
        return "manual-search", "secondary", "search page; open to choose individual sources"
    if any(x in text for x in ["youtube.com", "youtu.be"]):
        if "results?search_query=" in text or "/results" in text:
            return "manual-search", "secondary", "YouTube search page; open to choose individual videos"
        if "playlist" in text or "list=" in text:
            return "youtube-playlist", "transcript", "playlist or collection; expand into videos when possible"
        if re.search(r"/@[^/]+|/channel/|/c/|/user/", text):
            return "youtube-channel", "transcript", "channel source; expand or search videos before evidence use"
        return "youtube-video", "transcript", "video transcript/subtitle candidate"
    if "bilibili.com" in text:
        return "bilibili-video", "transcript", "video page candidate; may need user subtitle/download help"
    if "nicovideo.jp" in text:
        return "niconico-video", "transcript", "video page candidate; may need login or user-provided subtitles"
    if re.search(r"\.(srt|vtt|ass|txt|md|json)(\?|#|$)", text):
        return "text-or-subtitle", "transcript", "direct text/subtitle candidate"
    return "web-page", "secondary", "web page candidate"


def base_row(url: str, title: str, query: str, project: str, user_note: str = "") -> dict:
    source_type, layer, value = classify(url, title)
    decision = "recommended" if source_type in {"youtube-video", "text-or-subtitle"} else "needs-user-review"
    return {
        "title": title or url,
        "url": url,
        "query": query,
        "project": project,
        "source_type": source_type,
        "suggested_layer": layer,
        "likely_value": value,
        "decision": decision,
        "risk": "unconfirmed until user review",
        "confirmed_by_user": False,
        "intake_note": user_note,
    }


def run_ytdlp_flat(url: str, limit: int) -> tuple[list[dict], str]:
    exe = shutil.which("yt-dlp")
    if not exe:
        return [], "yt-dlp not installed"
    cmd = [exe, "--flat-playlist", "--dump-json", "--playlist-end", str(limit), url]
    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=60)
    except Exception as exc:
        return [], str(exc)
    rows: list[dict] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        video_id = data.get("id")
        if not video_id:
            continue
        webpage_url = data.get("webpage_url") or data.get("url") or f"https://www.youtube.com/watch?v={video_id}"
        if not str(webpage_url).startswith("http"):
            webpage_url = f"https://www.youtube.com/watch?v={video_id}"
        rows.append({"title": data.get("title", webpage_url), "url": webpage_url})
    err = proc.stderr.strip()
    return rows[:limit], err


def youtube_search_url(query: str) -> str:
    return "https://www.youtube.com/results?search_query=" + urllib.parse.quote(query)


def google_search_url(query: str) -> str:
    return "https://www.google.com/search?q=" + urllib.parse.quote(query)


def normalize_channel(value: str) -> str:
    if value.startswith("http://") or value.startswith("https://"):
        return value
    if value.startswith("@"):
        return "https://www.youtube.com/" + value
    if re.match(r"^UC[\w-]{20,}$", value):
        return "https://www.youtube.com/channel/" + value
    return youtube_search_url(value)


def add_expanded(rows: list[dict], source: str, label: str, project: str, limit: int) -> None:
    expanded, note = run_ytdlp_flat(source, limit)
    if expanded:
        for item in expanded:
            rows.append(base_row(item["url"], item["title"], label, project, "expanded with yt-dlp"))
    else:
        rows.append(base_row(source, label, label, project, f"not expanded automatically: {note}"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize source hints into candidates.json")
    parser.add_argument("--character", default="", help="Target character name")
    parser.add_argument("--project", default="", help="Project/work/franchise name")
    parser.add_argument("--url", action="append", default=[], help="Direct URL, repeatable")
    parser.add_argument("--local", action="append", default=[], help="Local source file, repeatable")
    parser.add_argument("--youtube-channel", action="append", default=[], help="YouTube channel name, handle, channel ID, or URL")
    parser.add_argument("--playlist", action="append", default=[], help="Playlist or collection URL, repeatable")
    parser.add_argument("--query", action="append", default=[], help="Search query, repeatable")
    parser.add_argument("--out", required=True, help="Output source directory")
    parser.add_argument("--limit", type=int, default=20, help="Expansion limit per playlist/channel")
    args = parser.parse_args()

    project = args.project
    rows: list[dict] = []
    for url in args.url:
        rows.append(base_row(url, url, "user-url", project, "direct user URL"))
    for path in args.local:
        rows.append(base_row(str(Path(path)), Path(path).name, "user-local-file", project, "direct local file"))
    for playlist in args.playlist:
        add_expanded(rows, playlist, "user-playlist", project, args.limit)
    for channel in args.youtube_channel:
        channel_url = normalize_channel(channel)
        add_expanded(rows, channel_url, f"youtube-channel: {channel}", project, args.limit)
        if "results?search_query=" not in channel_url:
            rows.append(base_row(channel_url.rstrip("/") + "/videos", f"{channel} videos", "channel videos page", project, "channel videos page fallback"))
    for query in args.query:
        full = " ".join(x for x in [args.character, project, query] if x).strip()
        rows.append(base_row(youtube_search_url(full), f"YouTube search: {full}", full, project, "search fallback"))
        rows.append(base_row(google_search_url(full), f"Web search: {full}", full, project, "search fallback"))

    deduped: list[dict] = []
    seen = set()
    for row in rows:
        key = str(row["url"]).split("#", 1)[0]
        if key in seen:
            continue
        seen.add(key)
        row["id"] = f"S{len(deduped) + 1:03d}"
        deduped.append(row)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "candidates.json").write_text(json.dumps(deduped, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Source Intake Candidates",
        "",
        "Confirm rows before collection. Search/channel rows are discovery aids, not evidence.",
        "",
        "| ID | Decision | Type | Title | Value | Note | URL |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in deduped:
        safe = {k: str(v).replace("|", "/") for k, v in row.items()}
        lines.append(f"| {safe['id']} | {safe['decision']} | {safe['source_type']} | {safe['title']} | {safe['likely_value']} | {safe['intake_note']} | {safe['url']} |")
    (out_dir / "candidates.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out_dir / 'candidates.json'}")
    print(f"Wrote {out_dir / 'candidates.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
