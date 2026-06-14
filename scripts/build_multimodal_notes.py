#!/usr/bin/env python3
"""Build review notes from a multimodal manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build multimodal-notes.md from a manifest")
    parser.add_argument("--manifest", required=True, help="multimodal-manifest.json path")
    parser.add_argument("--out", required=True, help="Output directory or markdown path")
    args = parser.parse_args()

    data = json.loads(Path(args.manifest).read_text(encoding="utf-8-sig"))
    items = data.get("items", []) if isinstance(data, dict) else []
    out_path = Path(args.out)
    if out_path.suffix.lower() != ".md":
        out_path = out_path / "multimodal-notes.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Multimodal Material Notes",
        "",
        "These notes are an index and review scaffold. They do not claim automatic visual, OCR, or audio recognition.",
        "",
        "| Kind | File | Exists | Review Use | Notes |",
        "|---|---|---:|---|---|",
    ]
    for item in items:
        kind = item.get("kind", "unknown")
        name = str(item.get("name") or item.get("path") or "").replace("|", "/")
        exists = "yes" if item.get("exists") else "no"
        use = "appearance/style reference" if kind == "visual" else "voice/audio reference" if kind == "audio" else "manual review"
        lines.append(f"| {kind} | {name} | {exists} | {use} | Requires human/agent observation note before entering evidence. |")

    lines.extend(
        [
            "",
            "## Review Rules",
            "",
            "- Mark screenshots as appearance/context evidence unless text/dialogue is manually transcribed.",
            "- Mark audio as low-confidence voice reference unless a user-approved transcript exists.",
            "- If ASR/OCR is added later, label it as machine transcription and keep confidence low until reviewed.",
        ]
    )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
