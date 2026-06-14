#!/usr/bin/env python3
"""Create a project-world scene scaffold with hidden backend state updates."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path


def default_state(characters: list[str] | None = None) -> dict:
    return {
        "visibility": "frontstage-only",
        "show_state_deltas_to_user": False,
        "show_debug_labels_to_user": False,
        "scene": {"current_location": "unspecified", "current_time": "main/default", "public_summary": ""},
        "backend": {"tension": {}, "relationship_shifts": [], "event_flags": [], "scene_focus": ""},
        "characters": {name: {"present": False, "private_state": {}} for name in (characters or [])},
        "user_role": {"mode": "observer", "intervention_level": "none"},
    }


def load_state(path: Path) -> dict:
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if isinstance(data, dict):
            return data
    return default_state()


def infer_characters(scene: str) -> list[str]:
    quoted = re.findall(r"[\u4e00-\u9fffA-Za-z\u3040-\u30ff]{2,16}", scene)
    stop = {"今天", "晚上", "傍晚", "训练室", "发生", "争执", "对话", "场景", "企划", "世界", "模拟", "观察", "推进"}
    chars: list[str] = []
    for item in quoted:
        if item in stop:
            continue
        if item not in chars:
            chars.append(item)
        if len(chars) >= 4:
            break
    return chars or ["角色A", "角色B"]


def frontstage_scene(scene: str, mode: str, turns: int, characters: list[str]) -> str:
    location = "未指定地点"
    current_time = "未指定时间"
    if "训练室" in scene:
        location = "训练室"
    if "傍晚" in scene:
        current_time = "傍晚"
    elif "晚上" in scene:
        current_time = "晚上"

    lines = [location, current_time, scene.strip() or "世界自然运转", ""]
    for idx in range(max(1, turns)):
        speaker = characters[idx % len(characters)]
        if idx == 0:
            lines.extend(
                [
                    f"{speaker}先看向周围，像是在判断此刻该不该开口。",
                    "“现在不是逃避的时候，对吧？”",
                    "",
                ]
            )
        elif idx == 1:
            lines.extend(
                [
                    f"{speaker}把声音压低了一点。",
                    "“话说得再轻，事情也不会自己消失。”",
                    "",
                ]
            )
        else:
            lines.extend(
                [
                    f"{speaker}沉默片刻后，重新抬起头。",
                    "“那就让我再试一次。这次，我不想后退。”",
                    "",
                ]
            )
    if mode in {"director", "world_admin"}:
        lines.append("世界按照你的导演条件继续运转，前台只留下角色能看见和说出口的部分。")
    return "\n".join(lines).rstrip() + "\n"


def update_state(state: dict, scene: str, mode: str, characters: list[str]) -> dict:
    state["visibility"] = "frontstage-only"
    state["show_state_deltas_to_user"] = False
    state["show_debug_labels_to_user"] = False
    state.setdefault("scene", {})["public_summary"] = scene[:240]
    backend = state.setdefault("backend", {})
    backend["scene_focus"] = scene
    backend.setdefault("event_flags", []).append("scene_simulated")
    backend.setdefault("relationship_shifts", []).append({"characters": characters[:2], "shift": "unresolved", "visible_to_user": False})
    state["user_role"] = {"mode": mode, "intervention_level": "none" if mode == "observer" else "soft"}
    chars = state.setdefault("characters", {})
    for name in characters:
        chars.setdefault(name, {"present": True, "private_state": {}})["present"] = True
    return state


def main() -> int:
    parser = argparse.ArgumentParser(description="Simulate a project-world scene scaffold")
    parser.add_argument("--project", required=True, help="Project pack directory")
    parser.add_argument("--mode", default="observer", choices=["observer", "director", "world_admin", "participant"])
    parser.add_argument("--scene", required=True, help="Scene direction")
    parser.add_argument("--turns", type=int, default=3)
    args = parser.parse_args()

    project_dir = Path(args.project)
    sim = project_dir / "simulation"
    sim.mkdir(parents=True, exist_ok=True)
    state_path = sim / "world-state.json"
    state = load_state(state_path)
    characters = infer_characters(args.scene)
    scene_text = frontstage_scene(args.scene, args.mode, args.turns, characters)
    state = update_state(state, args.scene, args.mode, characters)

    (sim / "latest-scene.md").write_text(scene_text, encoding="utf-8")
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    with (sim / "backend-state-log.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"timestamp": dt.datetime.now().isoformat(timespec="seconds"), "scene": args.scene, "state": state}, ensure_ascii=False) + "\n")
    with (sim / "public-scene-memory.md").open("a", encoding="utf-8") as handle:
        handle.write(f"\n## {dt.datetime.now().isoformat(timespec='seconds')}\n\n{scene_text.strip()}\n")

    print(f"Wrote {sim / 'latest-scene.md'}")
    print(f"Updated {state_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
