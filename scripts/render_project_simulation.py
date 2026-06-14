#!/usr/bin/env python3
"""Render or refresh project-world simulation assets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def default_world_state() -> dict:
    return {
        "visibility": "frontstage-only",
        "show_state_deltas_to_user": False,
        "show_debug_labels_to_user": False,
        "scene": {"current_time": "main/default", "current_location": "unspecified", "public_summary": ""},
        "backend": {"tension": {}, "event_flags": [], "relationship_shifts": [], "scene_focus": ""},
        "user_role": {"mode": "observer", "intervention_level": "none"},
        "characters": {},
    }


def simulation_sections() -> str:
    return """
## 10. 世界模拟模式

世界模拟模式用于让用户从对话者切换为观察者、导演、世界管理员或参与者，观察企划内多角色和世界观自然运转。

## 11. 用户上帝视角协议

| 模式 | 权限 | 输出方式 |
|---|---|---|
| observer | 只观察世界自然运行 | 只显示场景叙事和角色互动 |
| director | 给出场景方向但不入场 | 根据导演指令安排场景 |
| world_admin | 修改时间、地点、事件条件 | 更新后台 world-state.json |
| participant | 用户作为角色或存在入场 | 角色可直接回应用户 |

## 12. 多角色场景调度

- 用户点名谁，谁优先回应。
- 未点名角色不抢戏。
- 后台调度不显示给用户。

## 13. 世界状态

世界状态保存在 `simulation/world-state.json`。状态变化只写入后台文件，不直接显示给用户。

## 14. 事件推进器

事件来自世界观规则、时间线、角色目标、关系图、当前冲突和用户导演指令。

## 15. 群像对话格式

前台只显示地点、时间、场景叙事、动作和台词。不要显示数值变化、debug 标签或场景焦点分析。

## 16. 观察与干预规则

observer 只观看；director 给方向；world_admin 改条件；participant 入场互动。
""".strip()


def append_project_sections(project_path: Path) -> None:
    text = project_path.read_text(encoding="utf-8", errors="replace")
    if "## 10. 世界模拟模式" not in text:
        project_path.write_text(text.rstrip() + "\n\n" + simulation_sections() + "\n", encoding="utf-8")


def write_assets(project_dir: Path) -> None:
    sim = project_dir / "simulation"
    sim.mkdir(parents=True, exist_ok=True)
    world_state = sim / "world-state.json"
    if not world_state.exists():
        world_state.write_text(json.dumps(default_world_state(), ensure_ascii=False, indent=2), encoding="utf-8")
    (sim / "backend-state-log.jsonl").touch()
    if not (sim / "public-scene-memory.md").exists():
        (sim / "public-scene-memory.md").write_text("# Public Scene Memory\n\nOnly user-visible scene summaries go here.\n", encoding="utf-8")
    (sim / "scene-templates.md").write_text(
        "# Scene Templates\n\nFrontstage: scene, action, dialogue. Backend: state, schedule, flags.\n",
        encoding="utf-8",
    )
    (sim / "event-engine.md").write_text("# Event Engine\n\nEvents update backend state first; public output receives visible consequences only.\n", encoding="utf-8")
    (sim / "narrator-rules.md").write_text("# Narrator Rules\n\nDo not display debug state, numeric deltas, or analysis labels.\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Render project simulation assets")
    parser.add_argument("--project", required=True, help="Path to PROJECT.md or project pack directory")
    args = parser.parse_args()

    project_arg = Path(args.project)
    project_dir = project_arg if project_arg.is_dir() else project_arg.parent
    project_md = project_dir / "PROJECT.md" if project_arg.is_dir() else project_arg
    if project_md.exists():
        append_project_sections(project_md)
    write_assets(project_dir)
    project_json = project_dir / "project.json"
    if project_json.exists():
        data = json.loads(project_json.read_text(encoding="utf-8-sig"))
    else:
        data = {"id": project_dir.name, "name": project_dir.name, "characters": []}
    data["simulation"] = {
        "enabled": True,
        "user_role_modes": ["observer", "director", "world_admin", "participant"],
        "world_state_path": "simulation/world-state.json",
        "visibility": "frontstage-only",
        "show_state_deltas_to_user": False,
        "show_debug_labels_to_user": False,
    }
    project_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {project_dir / 'simulation' / 'world-state.json'}")
    print(f"Updated {project_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
