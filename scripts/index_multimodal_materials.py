#!/usr/bin/env python3
"""Index visual/audio materials without pretending to perform recognition."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


VISUAL_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".avif"}
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac"}


def item_for(path_text: str, kind_hint: str) -> dict:
    path = Path(path_text)
    suffix = path.suffix.lower()
    kind = kind_hint
    if kind == "auto":
        if suffix in VISUAL_EXT:
            kind = "visual"
        elif suffix in AUDIO_EXT:
            kind = "audio"
        else:
            kind = "unknown"
    return {
        "path": str(path),
        "name": path.name,
        "kind": kind,
        "extension": suffix,
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() and path.is_file() else None,
        "recognition_status": "not-run",
        "confidence": "manual-review-required",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Index visual/audio materials into a manifest")
    parser.add_argument("--visual", action="append", default=[], help="Visual file path; may be repeated")
    parser.add_argument("--audio", action="append", default=[], help="Audio file path; may be repeated")
    parser.add_argument("--file", action="append", default=[], help="Auto-classified file path; may be repeated")
    parser.add_argument("--out", required=True, help="Output directory or manifest JSON path")
    args = parser.parse_args()

    items = [item_for(path, "visual") for path in args.visual]
    items.extend(item_for(path, "audio") for path in args.audio)
    items.extend(item_for(path, "auto") for path in args.file)

    out_path = Path(args.out)
    if out_path.suffix.lower() != ".json":
        out_path = out_path / "multimodal-manifest.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"items": items, "policy": "No automatic ASR/OCR/vision inference was performed."}
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
