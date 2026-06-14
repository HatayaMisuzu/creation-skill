#!/usr/bin/env python3
"""Collect confirmed sources into normalized, traceable text files.

The collector is deliberately dependency-light. Optional tools such as
youtube-transcript-api and yt-dlp are used when available, and every failed
attempt is recorded with recovery advice instead of disappearing.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


TEXT_SUFFIXES = {".txt", ".md", ".srt", ".vtt", ".ass", ".html", ".htm", ".json"}
SUBTITLE_SUFFIXES = {".srt", ".vtt", ".ass"}


class CollectionError(RuntimeError):
    def __init__(self, message: str, attempts: list[dict] | None = None):
        super().__init__(message)
        self.attempts = attempts or []


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def detect_language(text: str) -> str:
    sample = text[:6000]
    langs: list[str] = []
    if re.search(r"[\u3040-\u30ff]", sample):
        langs.append("ja")
    if re.search(r"[\u4e00-\u9fff]", sample):
        langs.append("zh")
    if len(re.findall(r"[A-Za-z]", sample)) > 40:
        langs.append("en")
    return ",".join(langs) if langs else "unknown"


def collapse_ws(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_subtitle(content: str, keep_timestamps: bool) -> tuple[str, list[dict]]:
    content = content.replace("\ufeff", "")
    content = re.sub(r"^WEBVTT.*?\n", "", content, flags=re.I | re.S)
    content = re.sub(r"\{\\.*?\}", "", content)
    segments: list[dict] = []
    current_time = ""
    buffer: list[str] = []
    line_no = 0

    def flush() -> None:
        nonlocal buffer, current_time
        if not buffer:
            return
        text = collapse_ws(" ".join(buffer))
        text = re.sub(r"<[^>]+>", "", text)
        if text:
            segments.append({"index": len(segments) + 1, "time": current_time, "text": text})
        buffer = []
        current_time = ""

    for raw in content.splitlines():
        line_no += 1
        line = raw.strip()
        if not line:
            flush()
            continue
        if re.fullmatch(r"\d+", line):
            continue
        if "-->" in line:
            flush()
            current_time = line
            continue
        line = re.sub(r"<[^>]+>", "", line)
        line = re.sub(r"\\N", " ", line)
        if line:
            buffer.append(line)
    flush()

    deduped: list[dict] = []
    seen_recent: list[str] = []
    for seg in segments:
        key = seg["text"]
        if key in seen_recent[-4:]:
            continue
        seen_recent.append(key)
        deduped.append(seg)

    lines = []
    for seg in deduped:
        if keep_timestamps and seg["time"]:
            lines.append(f"[{seg['time']}] {seg['text']}")
        else:
            lines.append(seg["text"])
    return "\n".join(lines).strip(), deduped


def html_to_text(content: str) -> str:
    content = re.sub(r"(?is)<(script|style|noscript|svg|canvas).*?</\1>", " ", content)
    content = re.sub(r"(?is)<br\s*/?>", "\n", content)
    content = re.sub(r"(?is)</(p|div|li|h[1-6]|tr|section|article)>", "\n", content)
    content = re.sub(r"(?is)<.*?>", " ", content)
    return collapse_ws(html.unescape(content))


def json_to_text(value: Any) -> str:
    lines: list[str] = []

    def walk(node: Any, prefix: str = "") -> None:
        if isinstance(node, dict):
            for key, child in node.items():
                walk(child, f"{prefix}{key}.")
        elif isinstance(node, list):
            for idx, child in enumerate(node):
                walk(child, f"{prefix}{idx}.")
        elif node is not None:
            text = str(node).strip()
            if text:
                lines.append(text)

    walk(value)
    return collapse_ws("\n".join(lines))


def decode_bytes(raw: bytes, content_type: str = "") -> str:
    encoding = "utf-8"
    match = re.search(r"charset=([\w.-]+)", content_type, re.I)
    if match:
        encoding = match.group(1)
    return raw.decode(encoding, errors="replace")


def fetch_url(url: str, max_bytes: int) -> tuple[str, str, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 creation-skill/8"})
    with urllib.request.urlopen(req, timeout=25) as res:
        raw = res.read(max_bytes + 1)
        content_type = res.headers.get("content-type", "")
    if len(raw) > max_bytes:
        raw = raw[:max_bytes]
    text = decode_bytes(raw, content_type)
    if "json" in content_type or url.lower().split("?", 1)[0].endswith(".json"):
        try:
            return text, json_to_text(json.loads(text)), "http-json"
        except json.JSONDecodeError:
            return text, text, "http-json-raw"
    if "html" in content_type or "<html" in text[:800].lower():
        return text, html_to_text(text), "http-html"
    return text, text, "http-text"


def youtube_id(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc.endswith("youtu.be"):
        return parsed.path.strip("/")
    if "youtube.com" in parsed.netloc:
        qs = urllib.parse.parse_qs(parsed.query)
        if qs.get("v"):
            return qs["v"][0]
        match = re.search(r"/(?:shorts|embed)/([^/?#]+)", parsed.path)
        if match:
            return match.group(1)
    return ""


def fetch_youtube_transcript_api(url: str, languages: list[str]) -> tuple[str, str, list[dict]]:
    video_id = youtube_id(url)
    if not video_id:
        raise RuntimeError("not a YouTube video URL")
    try:
        from youtube_transcript_api import YouTubeTranscriptApi  # type: ignore
    except Exception as exc:
        raise RuntimeError("youtube-transcript-api is not available") from exc

    api = YouTubeTranscriptApi()
    try:
        fetched = api.fetch(video_id, languages=languages)
        rows = [{"time": str(getattr(item, "start", "")), "text": item.text} for item in fetched if item.text.strip()]
    except Exception:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)  # type: ignore[attr-defined]
        rows = [{"time": str(item.get("start", "")), "text": item.get("text", "")} for item in transcript if item.get("text", "").strip()]
    text = "\n".join(row["text"] for row in rows)
    return text, text, rows


def fetch_youtube_ytdlp(url: str, languages: list[str], keep_timestamps: bool) -> tuple[str, str, list[dict]]:
    exe = shutil.which("yt-dlp")
    if not exe:
        raise RuntimeError("yt-dlp is not installed")
    with tempfile.TemporaryDirectory() as tmp:
        out_template = str(Path(tmp) / "%(id)s.%(ext)s")
        cmd = [
            exe,
            "--skip-download",
            "--write-auto-subs",
            "--write-subs",
            "--sub-langs",
            ",".join(languages),
            "--sub-format",
            "vtt/srt/best",
            "-o",
            out_template,
            url,
        ]
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=120)
        subtitle_files = sorted(list(Path(tmp).glob("*.vtt")) + list(Path(tmp).glob("*.srt")))
        if not subtitle_files:
            detail = proc.stderr.strip() or proc.stdout.strip() or "no subtitle file produced"
            raise RuntimeError(detail[-800:])
        raw_parts: list[str] = []
        text_parts: list[str] = []
        segments: list[dict] = []
        for path in subtitle_files:
            raw = path.read_text(encoding="utf-8", errors="replace")
            text, segs = parse_subtitle(raw, keep_timestamps)
            raw_parts.append(raw)
            text_parts.append(text)
            segments.extend(segs)
        return "\n\n".join(raw_parts), "\n\n".join(text_parts), segments


def fetch_youtube(url: str, languages: list[str], keep_timestamps: bool, max_bytes: int) -> tuple[str, str, list[dict], list[dict], str, str]:
    attempts: list[dict] = []
    try:
        raw, text, segments = fetch_youtube_transcript_api(url, languages)
        attempts.append({"method": "youtube-transcript-api", "status": "ok", "char_count": len(text)})
        return raw, text, segments, attempts, "youtube-transcript-api", "high"
    except Exception as exc:
        attempts.append({"method": "youtube-transcript-api", "status": "failed", "error": str(exc)[-800:]})
    try:
        raw, text, segments = fetch_youtube_ytdlp(url, languages, keep_timestamps)
        attempts.append({"method": "yt-dlp subtitles", "status": "ok", "char_count": len(text)})
        return raw, text, segments, attempts, "yt-dlp subtitles", "high"
    except Exception as exc:
        attempts.append({"method": "yt-dlp subtitles", "status": "failed", "error": str(exc)[-800:]})
    try:
        raw, text, method = fetch_url(url, max_bytes)
        attempts.append({"method": "html fallback", "status": "ok", "char_count": len(text)})
        return raw, text, [], attempts, method, "low"
    except Exception as exc:
        attempts.append({"method": "html fallback", "status": "failed", "error": str(exc)[-800:]})
    raise CollectionError("all YouTube collection methods failed", attempts)


def read_local(path: Path, max_bytes: int, keep_timestamps: bool) -> tuple[str, str, list[dict], str]:
    raw_bytes = path.read_bytes()[:max_bytes]
    raw = raw_bytes.decode("utf-8", errors="replace")
    suffix = path.suffix.lower()
    if suffix in SUBTITLE_SUFFIXES:
        text, segments = parse_subtitle(raw, keep_timestamps)
        return raw, text, segments, "local-subtitle"
    if suffix in {".html", ".htm"}:
        return raw, html_to_text(raw), [], "local-html"
    if suffix == ".json":
        try:
            return raw, json_to_text(json.loads(raw)), [], "local-json"
        except json.JSONDecodeError:
            return raw, raw, [], "local-json-raw"
    return raw, raw, [], "local-text"


def is_confirmed(row: dict, include_agent_selected: bool) -> bool:
    value = row.get("confirmed_by_user", row.get("user_confirmed", False))
    return value is True or (include_agent_selected and value == "agent-selected")


def user_recovery_advice(row: dict, attempts: list[dict]) -> str:
    url = str(row.get("url", ""))
    if "youtube.com" in url or "youtu.be" in url:
        return "Ask the user for a public video URL with captions, exported .srt/.vtt subtitles, a pasted transcript, or permission to use/install yt-dlp."
    if "bilibili.com" in url:
        return "Ask the user for exported subtitles, a pasted transcript, or a local subtitle/text file; Bilibili pages often require session access."
    if row.get("source_type") in {"youtube-channel", "youtube-playlist"}:
        return "Expand the channel/playlist into individual confirmed video URLs before collection."
    return "Ask the user for a directly accessible URL, local HTML/text export, .txt, .md, .json, .srt, .vtt, or .ass file."


def normalize_manifest_rows(manifest: Path | None, input_dir: Path | None) -> list[dict]:
    rows: list[dict] = []
    if manifest and manifest.exists():
        data = read_json(manifest)
        rows.extend(data if isinstance(data, list) else [data])
    if input_dir and input_dir.exists():
        for path in sorted(input_dir.rglob("*")):
            if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
                rows.append(
                    {
                        "id": f"LOCAL{len(rows) + 1:03d}",
                        "title": path.name,
                        "url": str(path),
                        "source_type": "local-file",
                        "suggested_layer": "user-provided",
                        "confirmed_by_user": True,
                        "source_scope": "character",
                    }
                )
    return rows


def write_report(path: Path, rows: list[dict], diagnostics_level: str) -> None:
    lines = ["# Collection Report", "", "| ID | Status | Method | Confidence | Characters | Advice | Source |", "|---|---|---|---|---:|---|---|"]
    for row in rows:
        advice = str(row.get("recovery_advice", "")).replace("|", "/").replace("\n", " ")
        lines.append(
            "| {id} | {status} | {method} | {confidence} | {chars} | {advice} | {source} |".format(
                id=str(row.get("id", "")).replace("|", "/"),
                status=str(row.get("status", "")).replace("|", "/"),
                method=str(row.get("collection_method", "")).replace("|", "/"),
                confidence=str(row.get("confidence", "")).replace("|", "/"),
                chars=row.get("char_count", 0),
                advice=advice,
                source=str(row.get("url", "")).replace("|", "/"),
            )
        )
    if diagnostics_level == "full":
        lines.extend(["", "## Attempts", ""])
        for row in rows:
            lines.append(f"### {row.get('id', '')}")
            for attempt in row.get("attempts", []):
                lines.append(f"- {attempt}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect confirmed source text")
    parser.add_argument("--manifest", default="", help="reviewed_sources.json; optional when --input-dir is used")
    parser.add_argument("--out", required=True, help="Output collected directory")
    parser.add_argument("--input-dir", default="", help="Batch import readable local files from a directory")
    parser.add_argument("--include-agent-selected", action="store_true", help="Collect recommended agent-selected rows")
    parser.add_argument("--allow-partial", action="store_true", help="Return success when some sources fail but diagnostics were written")
    parser.add_argument("--preferred-languages", default="ja,zh-Hans,zh,en", help="Subtitle/transcript language priority")
    parser.add_argument("--max-bytes", type=int, default=5_000_000, help="Maximum bytes read per source")
    parser.add_argument("--keep-timestamps", action="store_true", help="Keep subtitle timestamps in normalized text")
    parser.add_argument("--diagnostics-level", choices=["basic", "full"], default="basic")
    args = parser.parse_args()

    manifest = Path(args.manifest) if args.manifest else None
    input_dir = Path(args.input_dir) if args.input_dir else None
    rows = normalize_manifest_rows(manifest, input_dir)
    out_dir = Path(args.out)
    raw_dir = out_dir / "raw"
    text_dir = out_dir / "text"
    seg_dir = out_dir / "segments"
    raw_dir.mkdir(parents=True, exist_ok=True)
    text_dir.mkdir(parents=True, exist_ok=True)
    seg_dir.mkdir(parents=True, exist_ok=True)
    languages = [item.strip() for item in args.preferred_languages.split(",") if item.strip()]

    collected: list[dict] = []
    for row in rows:
        if not is_confirmed(row, args.include_agent_selected):
            continue
        item = dict(row)
        source_id = str(item.get("id") or f"S{len(collected) + 1:03d}")
        item["id"] = source_id
        attempts: list[dict] = []
        try:
            url = str(item.get("url", ""))
            parsed = urllib.parse.urlparse(url)
            if parsed.scheme in {"http", "https"}:
                if "youtube.com" in parsed.netloc or "youtu.be" in parsed.netloc:
                    raw, text, segments, attempts, method, confidence = fetch_youtube(url, languages, args.keep_timestamps, args.max_bytes)
                else:
                    raw, text, method = fetch_url(url, args.max_bytes)
                    attempts = [{"method": method, "status": "ok", "char_count": len(text)}]
                    segments = []
                    confidence = "medium" if method != "http-html" else "low"
            else:
                raw, text, segments, method = read_local(Path(url), args.max_bytes, args.keep_timestamps)
                attempts = [{"method": method, "status": "ok", "char_count": len(text)}]
                confidence = "high" if method in {"local-subtitle", "local-text", "local-json"} else "medium"
            raw_path = raw_dir / f"{source_id}.txt"
            text_path = text_dir / f"{source_id}.txt"
            segment_path = seg_dir / f"{source_id}.segments.json"
            raw_path.write_text(raw, encoding="utf-8")
            text_path.write_text(text, encoding="utf-8")
            segment_path.write_text(json.dumps(segments, ensure_ascii=False, indent=2), encoding="utf-8")
            partial = method in {"http-html", "html fallback"} and ("youtube.com" in url or "youtu.be" in url)
            item.update(
                {
                    "status": "partial" if partial else "collected",
                    "raw_path": str(raw_path),
                    "text_path": str(text_path),
                    "segments_path": str(segment_path),
                    "char_count": len(text),
                    "detected_language": detect_language(text),
                    "collection_method": method,
                    "confidence": confidence,
                    "attempts": attempts,
                    "source_scope": item.get("source_scope") or ("project" if item.get("source_type") in {"youtube-video", "web-page"} else "character"),
                }
            )
            if partial:
                item["recovery_advice"] = user_recovery_advice(item, attempts)
        except Exception as exc:
            attempts = exc.attempts if isinstance(exc, CollectionError) else attempts
            item.update(
                {
                    "status": "failed",
                    "failure_reason": str(exc),
                    "attempts": attempts,
                    "recovery_advice": user_recovery_advice(item, attempts),
                    "confidence": "none",
                }
            )
        collected.append(item)

    (out_dir / "source_manifest.json").write_text(json.dumps(collected, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "collection_diagnostics.json").write_text(json.dumps(collected, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(out_dir / "collection-report.md", collected, args.diagnostics_level)
    failures = [item for item in collected if item.get("status") == "failed"]
    print(f"Wrote {out_dir / 'source_manifest.json'}")
    print(f"Wrote {out_dir / 'collection-report.md'}")
    if failures:
        print(f"Collection failures: {len(failures)}")
    return 0 if (not failures or args.allow_partial) else 1


if __name__ == "__main__":
    raise SystemExit(main())
