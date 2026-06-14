#!/usr/bin/env python3
"""Build a v7 project-level pack around multiple character cards."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path


def slugify(text: str) -> str:
    value = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff\u3040-\u30ff]+", "-", text.strip())
    return re.sub(r"-+", "-", value).strip("-").lower() or "project"


def frontmatter(text: str) -> dict:
    match = re.match(r"---\n(.*?)\n---\n", text, re.S)
    data: dict[str, str] = {}
    if not match:
        return data
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip().strip("\"'")
    return data


def copy_character_cards(paths: list[str], out_dir: Path) -> list[dict]:
    chars: list[dict] = []
    char_dir = out_dir / "characters"
    char_dir.mkdir(parents=True, exist_ok=True)
    for path_text in paths:
        src = Path(path_text)
        text = src.read_text(encoding="utf-8", errors="replace") if src.exists() else ""
        meta = frontmatter(text)
        char_id = meta.get("name") or (src.parent.name if src.name.upper() == "CHARACTER.MD" else src.stem)
        display_name = meta.get("display_name", char_id)
        target = char_dir / char_id
        target.mkdir(parents=True, exist_ok=True)
        if src.exists() and src.is_file():
            shutil.copy2(src, target / "CHARACTER.md")
            for sidecar in ["character.json", "runtime-profile.json", "prompt-card.md", "voice-fingerprint.json"]:
                if (src.parent / sidecar).exists():
                    shutil.copy2(src.parent / sidecar, target / sidecar)
        chars.append({"id": char_id, "display_name": display_name, "path": str(target / "CHARACTER.md")})
    return chars


def attach_relationship_graph(path_text: str, out_dir: Path) -> str:
    target_md = out_dir / "relationship-graph.md"
    if not path_text:
        target_md.write_text(
            "# Relationship Graph\n\n"
            "No relationship graph supplied yet. Generate one with extract_relationship_graph.py when multi-character evidence is available.\n\n"
            "Rule: this graph is internal context only. Characters do not proactively mention untriggered relationship nodes.\n",
            encoding="utf-8",
        )
        return ""
    src = Path(path_text)
    if not src.exists():
        target_md.write_text(f"# Relationship Graph\n\nRequested graph was not found: {src}\n", encoding="utf-8")
        return str(src)
    if src.suffix.lower() == ".json":
        shutil.copy2(src, out_dir / "relationship-graph.json")
        target_md.write_text(
            "# Relationship Graph\n\nStructured graph copied to relationship-graph.json.\n\n"
            "Use this graph as backend reasoning only; do not let unmentioned characters steal focus.\n",
            encoding="utf-8",
        )
    else:
        shutil.copy2(src, target_md)
    return str(src)


def write_simulation_assets(out_dir: Path, chars: list[dict]) -> None:
    sim = out_dir / "simulation"
    sim.mkdir(parents=True, exist_ok=True)
    world_state = {
        "visibility": "frontstage-only",
        "show_state_deltas_to_user": False,
        "show_debug_labels_to_user": False,
        "scene": {"current_location": "", "current_time": "", "public_summary": ""},
        "backend": {"tension": {}, "relationship_shifts": [], "event_flags": [], "scene_focus": ""},
        "characters": {char["id"]: {"present": False, "private_state": {}} for char in chars},
    }
    (sim / "world-state.json").write_text(json.dumps(world_state, ensure_ascii=False, indent=2), encoding="utf-8")
    (sim / "backend-state-log.jsonl").write_text("", encoding="utf-8")
    (sim / "public-scene-memory.md").write_text("# Public Scene Memory\n\nOnly user-visible scene summaries go here.\n", encoding="utf-8")
    (sim / "scene-templates.md").write_text(
        "# Scene Templates\n\n"
        "- Frontstage output: narration, action, dialogue.\n"
        "- Hidden backend: tension, relationship shifts, flags, speaker schedule.\n"
        "- Never display numeric deltas or debug labels in immersive prose.\n",
        encoding="utf-8",
    )
    (sim / "event-engine.md").write_text(
        "# Event Engine\n\n"
        "Events update backend state first. Public output receives only visible consequences.\n",
        encoding="utf-8",
    )
    (sim / "narrator-rules.md").write_text(
        "# Narrator Rules\n\n"
        "- User can act as observer, director, world_admin, or participant.\n"
        "- Do not reveal hidden scheduler/state unless user explicitly asks for debug mode.\n"
        "- Characters keep separate voices and do not all speak at once.\n",
        encoding="utf-8",
    )
    voice_lines = ["# Voice Separation", "", "| Character | Style Guard | Scene Rule |", "|---|---|---|"]
    schedule = {"characters": [], "rules": ["mentioned characters speak first", "unmentioned characters do not steal focus", "backend schedule is hidden"]}
    for char in chars:
        voice_lines.append(f"| {char['display_name']} | Read their CHARACTER.md and voice-fingerprint.json if present. | Speak only when mentioned, present, or scene-required. |")
        schedule["characters"].append({"id": char["id"], "display_name": char["display_name"], "priority": "mentioned-first"})
    (sim / "voice-separation.md").write_text("\n".join(voice_lines) + "\n", encoding="utf-8")
    (sim / "speaker-scheduler.json").write_text(json.dumps(schedule, ensure_ascii=False, indent=2), encoding="utf-8")


def write_project_docs(out_dir: Path, project_name: str, project_id: str, project_type: str, chars: list[dict], graph_path: str) -> None:
    project_json = {
        "id": project_id,
        "name": project_name,
        "type": project_type,
        "characters": chars,
        "relationship_graph": graph_path,
        "simulation": {
            "enabled": True,
            "user_role_modes": ["observer", "director", "world_admin", "participant"],
            "world_state_path": "simulation/world-state.json",
            "visibility": "frontstage-only",
            "show_state_deltas_to_user": False,
            "show_debug_labels_to_user": False,
        },
    }
    (out_dir / "project.json").write_text(json.dumps(project_json, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "timeline.md").write_text("# Timeline\n\n- insufficient source evidence; fill after project-level evidence extraction.\n", encoding="utf-8")
    project_md = [
        f"# {project_name} 企划档案",
        "",
        f"- 企划ID: {project_id}",
        f"- 类型: {project_type}",
        f"- 角色数量: {len(chars)}",
        "",
        "## 1. 使用规则",
        "",
        "- 单角色对话仍以对应 `characters/<id>/CHARACTER.md` 为准。",
        "- 企划世界模拟使用上帝视角：用户可作为 observer、director、world_admin 或 participant。",
        "- 前台只显示场景叙事、动作和台词；后台状态写入 `simulation/world-state.json`。",
        "- 不显示数值变化、debug 标签、speaker schedule 或场景焦点分析。",
        "",
        "## 2. 多角色发言规则",
        "",
        "- 用户点名谁，谁优先回应。",
        "- 未点名角色不抢戏，除非已在场且场景强需求。",
        "- 角色之间可以互动，但不能覆盖用户。",
        "- 关系网只作内部推理，不主动抛出未触发角色。",
        "",
        "## 3. 企划状态",
        "",
        "- `simulation/world-state.json`: 后台状态。",
        "- `simulation/public-scene-memory.md`: 用户可见剧情摘要。",
        "- `simulation/backend-state-log.jsonl`: 后台变更记录。",
        "",
        "## 10. 企划世界模拟",
        "",
        "企划模式把用户从单一对话者扩展为上帝视角或导演视角，重点是多角色之间的互动和世界自身运转。",
        "",
        "## 11. 群像演绎规则",
        "",
        "使用 `voice-separation.md` 区分声线，使用 `speaker-scheduler.json` 调度发言，但调度结果不显示给用户。",
        "",
        "## 12. 时间线规则",
        "",
        "时间线决定角色 phase 和世界事件，不静默覆盖单角色卡。",
        "",
        "## 13. 关系网规则",
        "",
        "关系网是内部推理素材。未被用户提及的关系节点不主动进入前台。",
        "",
        "## 14. 世界状态规则",
        "",
        "后台保存 tension、relationship_shifts、event_flags、scene_focus 等字段；前台只呈现可见后果。",
        "",
        "## 15. 公开场景记忆",
        "",
        "`public-scene-memory.md` 只保存用户可见剧情摘要，不保存后台推理。",
        "",
        "## 16. 导出与运行",
        "",
        "项目包可配合单角色卡、prompt-card 和各目标导出适配器运行。",
        "",
    ]
    (out_dir / "PROJECT.md").write_text("\n".join(project_md), encoding="utf-8")

    scenes = out_dir / "scenes"
    scenes.mkdir(exist_ok=True)
    (scenes / "group-dynamics.md").write_text(
        "# Group Dynamics\n\n"
        "- Mentioned characters speak first.\n"
        "- Unmentioned characters do not interrupt or steal focus.\n"
        "- Relationship tension can affect tone but must not expose backend numbers.\n",
        encoding="utf-8",
    )
    (scenes / "shared-scene-rules.md").write_text(
        "# Shared Scene Rules\n\n"
        "- Match the user's language.\n"
        "- Keep backend state hidden in immersive output.\n"
        "- Show only narrative consequences, actions, and dialogue.\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build v7 project pack")
    parser.add_argument("--project", required=True, help="Project display name")
    parser.add_argument("--id", default="", help="Project id")
    parser.add_argument("--type", default="mixed", help="Project type")
    parser.add_argument("--character-card", action="append", default=[], help="CHARACTER.md path; repeatable")
    parser.add_argument("--relationship-graph", default="", help="relationship-graph.md/json path")
    parser.add_argument("--out", default="", help="Output project pack directory")
    args = parser.parse_args()

    project_id = args.id or slugify(args.project)
    out_dir = Path(args.out) if args.out else Path("project-packs") / project_id
    out_dir.mkdir(parents=True, exist_ok=True)
    chars = copy_character_cards(args.character_card, out_dir)
    graph_path = attach_relationship_graph(args.relationship_graph, out_dir)
    write_project_docs(out_dir, args.project, project_id, args.type, chars, graph_path)
    write_simulation_assets(out_dir, chars)
    print(f"Wrote {out_dir / 'PROJECT.md'}")
    print(f"Wrote {out_dir / 'simulation' / 'world-state.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
