#!/usr/bin/env python3
"""Patch project simulation world-state.json without exposing backend state."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path


def default_state() -> dict:
    return {
        "visibility": "frontstage-only",
        "show_state_deltas_to_user": False,
        "show_debug_labels_to_user": False,
        "scene": {"current_time": "main/default", "current_location": "unspecified", "public_summary": ""},
        "backend": {"tension": {}, "event_flags": [], "relationship_shifts": [], "scene_focus": ""},
        "user_role": {"mode": "observer", "intervention_level": "none"},
        "characters": {},
    }


def deep_update(base: dict, patch: dict) -> dict:
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            deep_update(base[key], value)
        else:
            base[key] = value
    return base


def normalize_visibility(state: dict) -> dict:
    if isinstance(state.get("visibility"), dict):
        visibility = state["visibility"]
        visibility["mode"] = visibility.get("mode", "frontstage-only")
    else:
        state["visibility"] = "frontstage-only"
    state["show_state_deltas_to_user"] = False
    state["show_debug_labels_to_user"] = False
    return state


def main() -> int:
    parser = argparse.ArgumentParser(description="Update project world state")
    parser.add_argument("--project", required=True, help="Project pack directory")
    parser.add_argument("--patch", default="", help="JSON patch file")
    parser.add_argument("--public-summary", default="", help="User-visible scene memory summary")
    args = parser.parse_args()

    sim = Path(args.project) / "simulation"
    sim.mkdir(parents=True, exist_ok=True)
    state_path = sim / "world-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8-sig")) if state_path.exists() else default_state()
    if not isinstance(state, dict):
        state = default_state()
    patch = json.loads(Path(args.patch).read_text(encoding="utf-8-sig")) if args.patch else {}
    if not isinstance(patch, dict):
        patch = {}
    state = normalize_visibility(deep_update(state, patch))
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    stamp = dt.datetime.now().isoformat(timespec="seconds")
    with (sim / "backend-state-log.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"timestamp": stamp, "patch": patch, "state": state}, ensure_ascii=False) + "\n")
    if args.public_summary:
        with (sim / "public-scene-memory.md").open("a", encoding="utf-8") as handle:
            handle.write(f"## {stamp}\n\n{args.public_summary}\n\n")
    (sim / "state-editor-report.md").write_text(
        "# State Editor Report\n\n- Updated world-state.json\n- Backend state remains hidden from user-facing scenes\n",
        encoding="utf-8",
    )
    print(f"Updated {state_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
