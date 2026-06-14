#!/usr/bin/env python3
"""Create a backend-only speaker schedule for a project scene."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def infer_names(scene: str, known: list[str]) -> list[str]:
    selected = [name for name in known if name and name in scene]
    if selected:
        return selected[:4]
    match = re.search(r"[，,]\s*([^，,。；;]+?)\s*(?:发生|相遇|争执|对话|谈话|冲突)", scene)
    if match:
        return [x.strip() for x in re.split(r"和|与|、|/|&", match.group(1)) if x.strip()][:4]
    return known[:3] or ["角色A", "角色B"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Schedule project scene speakers")
    parser.add_argument("--project", required=True, help="Project pack directory")
    parser.add_argument("--scene", required=True, help="Scene direction")
    parser.add_argument("--out", default="", help="Output simulation directory")
    args = parser.parse_args()
    project = Path(args.project)
    out = Path(args.out) if args.out else project / "simulation"
    scheduler = out / "speaker-scheduler.json"
    known = []
    if scheduler.exists():
        data = json.loads(scheduler.read_text(encoding="utf-8-sig"))
        known = [row.get("character", "") for row in data.get("characters", [])]
    active = infer_names(args.scene, known)
    turns = [{"turn": idx + 1, "speaker": name, "reason": "mentioned or scene-relevant", "visible_to_user": False} for idx, name in enumerate(active)]
    payload = {"scene": args.scene, "active_characters": active, "turns": turns, "frontstage_visibility": "do not show this schedule to user"}
    out.mkdir(parents=True, exist_ok=True)
    (out / "speaker-schedule.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out / 'speaker-schedule.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
