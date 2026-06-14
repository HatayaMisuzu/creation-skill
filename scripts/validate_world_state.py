#!/usr/bin/env python3
"""Validate project simulation world-state and frontstage visibility."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def hidden_flags_ok(state: dict) -> bool:
    if state.get("show_state_deltas_to_user") is not False:
        return False
    if state.get("show_debug_labels_to_user") is not False:
        return False
    visibility = state.get("visibility")
    if isinstance(visibility, dict):
        if visibility.get("show_state_deltas_to_user") not in {None, False}:
            return False
        if visibility.get("show_debug_labels_to_user") not in {None, False}:
            return False
    elif visibility not in {"frontstage-only", None}:
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate project world state")
    parser.add_argument("--project", required=True, help="Project pack directory")
    args = parser.parse_args()

    sim = Path(args.project) / "simulation"
    state_path = sim / "world-state.json"
    failures: list[str] = []
    if not state_path.exists():
        failures.append("missing world-state.json")
        state = {}
    else:
        state = json.loads(state_path.read_text(encoding="utf-8-sig"))
        if not isinstance(state, dict):
            failures.append("world-state.json must be an object")
            state = {}

    for key in ["visibility", "show_state_deltas_to_user", "show_debug_labels_to_user"]:
        if key not in state:
            failures.append(f"missing state key: {key}")
    if "scene" not in state and "current_time" not in state:
        failures.append("missing scene/current_time state")
    if "backend" not in state and "event_flags" not in state:
        failures.append("missing backend/event_flags state")
    if not hidden_flags_ok(state):
        failures.append("state visibility flags must keep backend hidden")

    scene = sim / "latest-scene.md"
    if scene.exists():
        text = scene.read_text(encoding="utf-8", errors="replace")
        if re.search(r"\+\d|tension|debug|scene_focus|场景焦点：|状态变化", text, re.I):
            failures.append("frontstage scene leaks backend state/debug labels")

    report = sim / "world-state-validation.md"
    status = "FAIL" if failures else "PASS"
    lines = ["# World State Validation", "", f"Status: {status}", "", "## Failures", ""]
    lines.extend(f"- {item}" for item in failures) if failures else lines.append("- none")
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Status: {status}")
    print(f"Report: {report}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
