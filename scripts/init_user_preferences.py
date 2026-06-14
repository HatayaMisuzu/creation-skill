#!/usr/bin/env python3
"""Create the default user preference profile for roleplay/runtime output."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


DEFAULT_PREFERENCES = {
    "default_language": "zh",
    "reply_format": "immersive_default",
    "romance_level": "slow-burn",
    "action_detail": "low",
    "narration_style": "light_novel",
    "meta_tolerance": "low",
    "world_simulation_visibility": "frontstage-only",
}


def resolve_output(path_text: str) -> Path:
    path = Path(path_text)
    if path.suffix.lower() == ".json":
        return path
    return path / "user-preferences.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize user-preferences.json")
    parser.add_argument("--out", default="profiles", help="Output directory or JSON path")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing file")
    args = parser.parse_args()

    out_path = resolve_output(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists() and not args.overwrite:
        print(f"Exists: {out_path}")
        print("Use --overwrite to replace it.")
        return 0

    out_path.write_text(json.dumps(DEFAULT_PREFERENCES, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
