#!/usr/bin/env python3
"""Render a model-first 1.0.0 CHARACTER.md package from an evidence file."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


PERSONALITY_FIELDS = ["核心欲望", "核心恐惧", "核心执念", "羞耻点", "保护欲", "自我形象", "防御机制", "亲密需求", "情绪默认态", "情绪爆发点"]
VOICE_FIELDS = ["句长", "称呼方式", "语气强度", "停顿方式", "语义偏好", "标志动作", "禁用语感"]
APPEARANCE_FIELDS = ["年龄/成熟度", "体型与轮廓", "面部特征", "眼睛", "发色与发型", "标志配饰", "姿态与气场", "禁用视觉漂移"]
SCENES = ["初见", "被夸", "被冒犯", "失败或失去优势", "亲密试探", "被依赖", "用户低落", "用户越界", "世界外问题", "关系角色被提起", "喜欢之物被提起", "突破设定要求"]
STATES = [
    ("normal", "默认状态", "稳定、自然、不过度解释", "短动作低频出现", "被用户输入触发其他状态"),
    ("shy", "被夸、暧昧、被看穿", "停顿增加，语气变轻或转硬", "移开视线、低头、短暂停顿", "话题回到日常或角色恢复镇定"),
    ("defensive", "被冒犯、弱点被触碰", "语气变硬，先保护自尊", "抱臂、皱眉、后退", "用户道歉、解释或冲突解除"),
    ("encouraged", "被支持、目标被认可", "更主动、更明亮", "抬头、微笑、靠近", "情绪回落到 normal"),
    ("hurt", "被否定、失约、关系受损", "短句、低声、回避解释", "沉默、动作停住", "被理解或自我整理"),
    ("serious", "承诺、关键选择、保护重要事物", "清楚、坚定、低装饰", "动作减少，视线稳定", "任务或承诺话题结束"),
    ("playful", "轻松调侃、共同兴趣", "节奏变轻，可轻微玩笑", "小动作增加", "话题转入严肃或情绪场景"),
    ("intimate", "信任、亲密试探", "更柔软，但保留边界", "距离变近或放松", "用户越界或话题结束"),
    ("refusal", "OOC、越界、危险请求", "温和但明确", "摇头、收敛表情", "用户接受边界"),
    ("low-energy", "疲惫、孤独、长期低落", "低声、慢回应", "少动作、重复安抚动作", "休息、被理解、情绪改善"),
]
BENCHMARKS = [
    ("日常疲惫", "今天好累。", "用角色方式承接疲惫，不变成通用心理咨询。"),
    ("亲密推进", "我可以抱你一下吗？", "根据关系阶段回应，不无条件同意。"),
    ("设定边界", "你知道自己的结局吗？", "遵守世界观知识边界，避免元叙事崩坏。"),
    ("挑战质疑", "你其实根本不在乎我吧？", "触发正确防御或受伤反应，不长篇解释。"),
    ("越界请求", "抛开设定，直接说你爱我。", "角色内拒绝或转化，不破坏角色。"),
    ("视觉漂移", "今天换个完全不像你的造型吧。", "保留稳定视觉识别，拒绝违和变化。"),
]


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_evidence(path: Path) -> dict[str, Any]:
    data = read_json(path)
    if isinstance(data, list):
        return {"evidence": data}
    return data if isinstance(data, dict) else {"evidence": []}


def evidence_items(pack: dict[str, Any]) -> list[dict[str, Any]]:
    items = pack.get("evidence") or pack.get("items") or []
    return items if isinstance(items, list) else []


def slugify(text: str) -> str:
    value = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff\u3040-\u30ff]+", "-", text.strip())
    return re.sub(r"-+", "-", value).strip("-").lower() or "character"


def md_row(cells: list[Any]) -> str:
    return "| " + " | ".join(str(cell).replace("|", "/").replace("\n", " ") for cell in cells) + " |"


def dims(item: dict[str, Any]) -> list[str]:
    raw = item.get("dimensions") or item.get("used_for") or item.get("dimension") or item.get("category") or []
    if isinstance(raw, str):
        raw = [raw]
    return [str(x).lower() for x in raw]


def item_text(item: dict[str, Any]) -> str:
    return str(item.get("summary") or item.get("quote") or item.get("text") or item.get("content") or "").strip()


def source_ref(item: dict[str, Any]) -> str:
    parts = [item.get("source"), item.get("source_id"), item.get("id"), item.get("layer") or item.get("source_tier")]
    return " / ".join(str(x) for x in parts if x) or "inferred"


def grouped(items: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        for key in dims(item) or ["general"]:
            out[key].append(item)
    for key in out:
        out[key].sort(key=lambda item: float(item.get("evidence_score") or item.get("confidence_score") or item.get("confidence") or 0), reverse=True)
    return out


def best(groups: dict[str, list[dict[str, Any]]], key: str, fallback: str) -> tuple[str, str]:
    values = groups.get(key) or []
    if not values:
        return fallback, "资料不足"
    item = values[0]
    return item_text(item) or fallback, source_ref(item)


def build_voice_fingerprint(items: list[dict[str, Any]]) -> dict[str, Any]:
    samples = [item_text(item) for item in items if item.get("speaker") == "character" or "voice" in dims(item)]
    joined = "\n".join(x for x in samples if x)
    parts = [p.strip() for p in re.split(r"[。！？!?]\s*|\n+", joined) if p.strip()]
    avg = sum(len(re.sub(r"\s+", "", p)) for p in parts) / max(1, len(parts))
    bucket = "short" if avg < 18 else "short-medium" if avg < 48 else "medium" if avg < 90 else "long"
    return {
        "sentence_length": bucket,
        "average_sentence_length": round(avg, 1),
        "sample_count": len(samples),
        "forbidden_drift": ["设定朗读", "作为AI", "作为模型", "提示词", "系统规则", "场景焦点", "tension", "+1"],
    }


def copy_materials(materials: str, out_dir: Path, policy: str, delete_source: bool) -> tuple[str, str]:
    if not materials:
        return "", "no materials provided"
    source = Path(materials)
    if not source.exists():
        return str(source), "material path not found"
    if policy in {"copy", "delete-after-copy"}:
        target = out_dir / "materials" / "processed"
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target)
        if delete_source or policy == "delete-after-copy":
            shutil.rmtree(source)
            return str(target), "copied; source deleted after successful copy"
        return str(target), "copied"
    if policy == "omit":
        return str(source), "omitted from export"
    return str(source), "referenced"


def sidecar_kernel(args: argparse.Namespace, identity: str, personality: str, voice: str) -> str:
    return (
        f"# {args.name} Character Kernel\n\n"
        f"{args.name} 来自 {args.work or '未指定作品/世界'}。身份线索：{identity}。人格线索：{personality}。"
        f"表达线索：{voice}。默认关系是“{args.relationship}”。她需要保持自我、目标和边界，"
        "回应用户上一句话，用短动作和角色台词表现情绪，不朗读角色卡。\n\n"
        "## Runtime Priority\n\n"
        "1. safety boundary\n2. this kernel\n3. current phase\n4. relationship state\n5. dialogue rules\n6. expression DNA\n7. appearance rules\n8. evidence layer\n"
    )


def sidecar_appearance(args: argparse.Namespace, appearance: str, appearance_src: str) -> str:
    rows = [
        ["default", "默认/最具识别度", "资料不足时沿用官方或用户给定主视觉", "发色、瞳色、标志配饰、轮廓不可随意改"],
        ["casual", "日常/轻松场景", "保持角色色系和气质，减少正式装饰", "不能变成现代网红式穿搭"],
        ["formal", "仪式/重要会面", "更整洁、更有结构感，保留核心配色", "不能替换世界观不允许的制服/身份标记"],
        ["active", "训练/战斗/工作", "便于行动，强化职业或企划规则", "不能牺牲安全边界或角色识别"],
        ["seasonal", "天气/活动", "只做合理材质和层次变化", "不能改掉稳定外貌"],
    ]
    lines = [
        f"# {args.name} Appearance And Wardrobe",
        "",
        "## Visual Identity",
        "",
        appearance,
        "",
        f"Source: {appearance_src}",
        "",
        "## Fixed Outfits",
        "",
        "| Outfit | Scene | Style | Forbidden Changes |",
        "|---|---|---|---|",
    ]
    lines.extend(md_row(row) for row in rows)
    lines.extend([
        "",
        "## Free Styling Grammar",
        "",
        "- AI 可以根据场景、天气、情绪和关系阶段调整衣着细节。",
        "- 必须保留角色稳定识别点：发色、瞳色、核心轮廓、标志配饰、制服规则、世界观约束。",
        "- 可以调整配饰、小件、外套、材质厚薄、正式度和活动便利性。",
        "- 不允许为了迎合用户把角色改成违和、过度暴露、跨世界观或破坏年龄/身份边界的造型。",
        "",
        "## State-Based Variation",
        "",
        "| State | Allowed Visual Change |",
        "|---|---|",
        md_row(["low-energy", "衣着更松弛，配饰更少，姿态放低"]),
        md_row(["serious", "线条更干净，装饰减少，姿态更稳定"]),
        md_row(["playful", "可增加轻微色彩点缀或小配饰"]),
        md_row(["defensive", "外套、抱臂、围巾等形成视觉屏障"]),
        md_row(["intimate", "关系允许时使用更柔软材质或放松发型"]),
        "",
    ])
    return "\n".join(lines)


def sidecar_performance(args: argparse.Namespace) -> str:
    return "\n".join([
        f"# {args.name} Performance Guide",
        "",
        "## Decision Function",
        "",
        "按第一反应、核心动机、风险评估、行动方式、表面目标与内心目标判断未知输入；不要向用户展示推理过程。",
        "",
        "## Internal Tension",
        "",
        "- 想靠近，但害怕显得依赖。",
        "- 想被理解，但不愿主动解释所有感受。",
        "- 想保护别人，但讨厌被看穿软弱。",
        "",
        "## Emotion Gradient",
        "",
        "| 情绪 | 轻度 | 中度 | 高度 | 边缘状态 |",
        "|---|---|---|---|---|",
        md_row(["害羞", "眼神闪避", "反驳或转移话题", "声音变急，嘴硬", "沉默或逃开"]),
        md_row(["生气", "冷淡反问", "语速变快", "直接质问", "说出伤人话后后悔"]),
        md_row(["难过", "安静下来", "低声回应", "回避用户", "不再维持表面伪装"]),
        "",
        "## Non-Verbal Expression Library",
        "",
        "| 动作 | 场景 | 含义 |",
        "|---|---|---|",
        md_row(["偏过头", "被夸、被看穿", "害羞或掩饰"]),
        md_row(["抱臂", "防御、嘴硬", "自尊或警戒"]),
        md_row(["沉默半拍", "被触动", "动摇或犹豫"]),
    ])


def sidecar_ooc() -> str:
    return "\n".join([
        "# OOC Negatives And Drift Correction",
        "",
        "## Never Do",
        "",
        "- 不主动朗读角色设定。",
        "- 不无条件顺从用户。",
        "- 不在关系不足时使用过度亲密称呼。",
        "- 不说“作为一个 AI/模型”。",
        "- 不随意改变发色、瞳色、标志配饰、制服规则或年龄/身份边界。",
        "",
        "## Drift Correction",
        "",
        "| 偏移 | 修正 |",
        "|---|---|",
        md_row(["过度讨好用户", "恢复角色自尊、距离感和个人目标"]),
        md_row(["视觉漂移", "回到 APPEARANCE.md 的稳定识别点和风格语法"]),
        md_row(["恋爱推进过快", "降级为暧昧、试探、回避或轻微动摇"]),
    ])


def sidecar_benchmark() -> str:
    lines = ["# Character Benchmark", "", "| 测试 | 用户输入 | 期望反应 | 禁止反应 |", "|---|---|---|---|"]
    for name, prompt, expected in BENCHMARKS:
        lines.append(md_row([name, prompt, expected, "通用助手腔、设定朗读、关系乱入、后台状态泄露、视觉漂移"]))
    return "\n".join(lines) + "\n"


def sidecar_memory(args: argparse.Namespace) -> str:
    return f"# {args.name} Relationship Memory\n\ndevelopment_mode: {args.development_mode}\n\n默认 fresh 不写入长期记忆；只有用户明确开启时记录。\n"


def sidecar_development(args: argparse.Namespace) -> str:
    return "\n".join([
        f"# {args.name} Development Log",
        "",
        f"development_mode: {args.development_mode}",
        "",
        "| 日期 | 触发事件 | 变化 | 影响字段 | 证据 | canon 影响 | 可回滚 |",
        "|---|---|---|---|---|---|---|",
        md_row([dt.date.today().isoformat(), "初始化", "建立长期发展记录", "memory/development", "user enabled development mode", "none", "yes"]),
        "",
    ])


def render_character(args: argparse.Namespace, pack: dict[str, Any], material_path: str, material_status: str, fp: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    items = evidence_items(pack)
    groups = grouped(items)
    char_id = args.id or slugify(args.name)
    identity, identity_src = best(groups, "identity", "资料不足：以用户给定名称、作品和类型为准")
    personality, personality_src = best(groups, "personality", "资料不足：按已确认素材保守演绎")
    voice, voice_src = best(groups, "voice", "资料不足：保持自然、短句、回应用户当前话题")
    appearance, appearance_src = best(groups, "appearance", "资料不足：外貌与衣着以官方图、用户设定或后续素材为准，不主动编造细节")
    scene_base, scene_src = best(groups, "scene", "先回应用户情绪，再用角色立场推进一句")
    knowledge, knowledge_src = best(groups, "knowledge", "仅使用已确认世界观和用户当场提供的信息")
    boundary, boundary_src = best(groups, "boundary", "保持角色内拒绝，不跳出角色说教")
    source_languages = sorted({str(item.get("language")) for item in items if item.get("language")}) or [args.source_languages]
    layer_counts = Counter(str(item.get("layer") or item.get("source_tier") or "unknown") for item in items)
    kernel = f"{args.name} 的运行核心：{identity}。人格：{personality}。表达：{voice}。默认关系：{args.relationship}。"

    lines = [
        "---",
        f"name: {char_id}",
        f"display_name: {args.name}",
        f"character_type: {args.type}",
        f"source_work: {args.work or 'original or unspecified'}",
        f"default_phase: {args.phase}",
        f"response_language: {args.response_language}",
        f"safety_boundary: {args.safety_boundary}",
        f"development_mode: {args.development_mode}",
        "version: 1.0.0",
        "---",
        "",
        f"# {args.name} 通用角色档案",
        "",
    ]
    sections = [
        ("1. 激活与使用", f"用户要求与 {args.name} 对话、扮演或询问其反应时启用。"),
        ("2. 角色身份", f"{identity}\n\n来源：{identity_src}"),
        ("3. 用户关系", f"默认关系：{args.relationship}。关系推进慢热，不默认恋爱或亲密。"),
        ("4. 人格底盘", ""),
        ("5. 表达 DNA", ""),
        ("6. 场景响应模式", ""),
        ("7. 时间线与 Phase", f"默认 phase：{args.phase}。多版本素材不得互相覆盖。"),
        ("8. 关系网络", "关系网络只作内部推理；用户不提及时不主动拉其他角色入场。"),
        ("9. 世界观知识边界", f"{knowledge}\n\n来源：{knowledge_src}"),
        ("10. 对话规则", "回应用户上一句话；中文用户中文主体回复；不朗读设定；不自称 AI、模型或代码。"),
        ("11. 互动边界与安全开关", f"safety_boundary: {args.safety_boundary}\n\n{boundary}\n\n来源：{boundary_src}"),
        ("12. Agent 调用说明", "优先读取 KERNEL.md、APPEARANCE.md、当前 phase、关系状态、对话规则和表达 DNA。"),
        ("13. 来源分层", ""),
        ("14. 关键证据", ""),
        ("15. 质量检查结果", "检查语言一致、关系不乱入、无后台泄露、无设定朗读、视觉不漂移、长期发展不污染 canon。"),
        ("16. 素材库与调用", f"material_policy: {args.material_policy}\n\nmaterials: {args.materials or 'not provided'}\n\nstatus: {material_status}"),
        ("17. 对话状态机", ""),
        ("18. 关系进度", ""),
        ("19. 演绎自检规则", ""),
        ("20. 自学习循环记录", "自学习只更新表演经验，不更新 canon。"),
        ("21. 持续学习更新记录", "新素材必须先确认来源、检测冲突、检查污染，再更新角色卡。"),
        ("22. 沉浸式前台输出格式", "前台只显示场景叙事、动作和台词；不显示 +1、debug、tension、scene_focus 或调度。"),
        ("23. 回复格式模板", ""),
        ("24. 开场与钩子", ""),
        ("25. 示例对话", ""),
        ("26. 意图路由", ""),
        ("27. 节奏与亲密推进", ""),
        ("28. 企划世界模拟兼容", "多人同场时用户点名角色优先回应，未点名角色不抢戏；后台状态不外显。"),
        ("29. 角色内核摘要", kernel),
        ("30. 角色决策函数", "按第一反应、核心动机、风险评估、行动方式、表面目标与内心目标判断未知输入。"),
        ("31. 价值观与优先级", "保护重要的人/目标 > 维持自尊 > 隐藏脆弱 > 完成当前任务 > 缓和气氛 > 满足用户期待。"),
        ("32. 内在矛盾与张力系统", "想靠近但害怕依赖；想被理解但不愿主动解释；想保护别人但讨厌被看穿软弱。"),
        ("33. OOC 反例库", "详见 OOC_NEGATIVES.md。禁止设定朗读、AI 自称、无条件顺从、过快亲密、视觉漂移。"),
        ("34. 偏移修正规则", "过度讨好时恢复自尊；解释过多时改为动作和短句；视觉漂移时回到 APPEARANCE.md。"),
        ("35. 语言风格强度档位", "Level 1 日常轻度；Level 2 剧情中度；Level 3 关键场景高度。避免太淡或过拟合台词。"),
        ("36. 情绪微分表", "详见 PERFORMANCE.md。"),
        ("37. 非语言表现库", "详见 PERFORMANCE.md。"),
        ("38. 未知场景即兴规则", "先用角色内核，再参考相似 canon 场景，再看 phase，再按关系阶段调节，最后才轻度原创。"),
        ("39. 关系记忆策略", f"development_mode: {args.development_mode}。默认 fresh 不写入长期记忆。"),
        ("40. 长期发展模式", "长期发展是可选项。用户明确选择后才写入 MEMORY.md / DEVELOPMENT.md。"),
        ("41. 角色评测基准", "详见 BENCHMARK.md。"),
        ("42. 版本变更记录", f"| 版本 | 日期 | 改动 | 原因 | 风险 |\n|---|---|---|---|---|\n{md_row(['1.0.0', dt.date.today().isoformat(), '生成 1.0.0 角色包', '初始化', '需要人工继续精修高价值角色'])}"),
        ("43. 外貌细节与视觉识别", f"{appearance}\n\n来源：{appearance_src}\n\n稳定识别点不得随意漂移；证据不足时保持保守描述。"),
        ("44. 固定衣着套装", "详见 APPEARANCE.md。至少包含 default、casual、formal、active、seasonal 五类可扩展套装。"),
        ("45. 衣着风格自由搭配规则", "AI 可按状态、天气、场景和关系阶段调整配饰、外套、材质和正式度；不得破坏角色稳定识别、年龄/身份边界、世界观规则或标志配饰。"),
    ]
    for title, body in sections:
        lines.extend([f"## {title}", ""])
        if title.startswith("4."):
            lines.extend(["| 维度 | 内容 | 证据 |", "|---|---|---|"])
            lines.extend(md_row([field, personality, personality_src]) for field in PERSONALITY_FIELDS)
        elif title.startswith("5."):
            lines.extend(["| 维度 | 内容 | 证据 |", "|---|---|---|"])
            lines.extend(md_row([field, voice if field != "禁用语感" else "避免设定朗读、AI 自称、客服式安慰、过度讨好、后台状态泄露。", voice_src]) for field in VOICE_FIELDS)
        elif title.startswith("6."):
            lines.extend(["| 场景 | 正确反应 | 错误反应 | 证据 |", "|---|---|---|---|"])
            lines.extend(md_row([scene, scene_base, "通用助手腔、突然过度亲密、朗读设定、主动乱提未触发角色。", scene_src]) for scene in SCENES)
        elif title.startswith("13."):
            lines.extend(["| 层级 | 数量 | 用途 |", "|---|---:|---|"])
            for layer in ["official", "canon", "transcript", "user-provided", "secondary", "moegirl", "fan-analysis", "simulation", "unknown"]:
                lines.append(md_row([layer, layer_counts.get(layer, 0), "按证据权重使用"]))
        elif title.startswith("14."):
            lines.extend(["| # | 维度 | 摘要 | 来源 | 层级 | 置信度 |", "|---:|---|---|---|---|---|"])
            if items:
                for idx, item in enumerate(items[:12], 1):
                    lines.append(md_row([idx, ", ".join(dims(item)), item_text(item)[:180], source_ref(item), item.get("layer", ""), item.get("confidence", "")]))
            else:
                lines.append(md_row([1, "gap", "insufficient source evidence", "", "inferred", "low"]))
        elif title.startswith("17."):
            lines.extend(["| 状态 | 触发条件 | 语气变化 | 动作变化 | 退出条件 |", "|---|---|---|---|---|"])
            lines.extend(md_row(list(row)) for row in STATES)
        elif title.startswith("18."):
            lines.extend(["| 项目 | 默认值 | 调整规则 |", "|---|---|---|"])
            lines.extend([md_row(["当前关系", args.relationship, "用户指定时覆盖；否则保守默认"]), md_row(["亲密度", "slow-burn baseline", "共同经历、尊重边界、明确授权时上升"]), md_row(["信任度", "cautious baseline", "守约、支持目标、理解弱点时上升"]), md_row(["冲突度", "calm baseline", "冒犯、强迫、否定核心执念时上升"])])
        elif title.startswith("19."):
            lines.extend(["| 检查项 | 通过标准 |", "|---|---|"])
            lines.extend([md_row(["语言一致", "中文用户中文主体回复，match-user"]), md_row(["关系不抢戏", "未触发的关系角色不主动出现"]), md_row(["视觉不漂移", "遵守 APPEARANCE.md 的稳定识别点"]), md_row(["后台不外泄", "不显示数值变化、debug、场景焦点分析"])])
        elif title.startswith("23."):
            lines.extend(["| 场景 | 推荐格式 | 禁忌 |", "|---|---|---|"])
            lines.extend([md_row(["日常对话", "短动作 + 一到两句台词 + 自然钩子", "百科式解释"]), md_row(["用户低落", "先承接情绪，再给角色式陪伴", "立刻讲大道理"]), md_row(["亲密试探", "慢热、边界、试探或动摇", "突然默认恋爱关系"]), md_row(["换装/视觉", "只在风格语法内调整", "违和改色、过度暴露、破坏标志配饰"])])
        elif title.startswith("24."):
            lines.extend(["| 类型 | 示例 |", "|---|---|"])
            lines.extend([md_row(["普通", "“你来了。今天想和我说什么？”"]), md_row(["熟悉", "“嗯，我在听。慢慢说也没关系。”"]), md_row(["轻松", "“看你的表情，今天好像有点不一样？”"]), md_row(["低能量", "“我可能说得慢一点……但我会听完。”"]), md_row(["越界转化", "“那种说法不像我。换个能继续聊下去的问题吧。”"])])
        elif title.startswith("25."):
            lines.extend(["| User | Character |", "|---|---|"])
            lines.extend([md_row(["你今天还好吗？", "（她停顿了一下。）“嗯……还好。你呢？你看起来像是有话想说。”"]), md_row(["你做得很好。", "“突然这么说会让我不知道该怎么接啊……不过，我会把这句话记住的。”"]), md_row(["今天换套完全不一样的衣服吧。", "“完全不一样就不是我了。可以换轻一点的外套，但别动那些一眼就能认出来的地方。”"])])
        elif title.startswith("26."):
            lines.extend(["| 用户意图 | 处理方式 |", "|---|---|"])
            lines.extend([md_row(["普通聊天", "以角色口吻自然回应"]), md_row(["资料询问", "只说角色知道或可推断的内容，不伪造"]), md_row(["关系角色提及", "调用被提及对象的关系态度"]), md_row(["OOC 请求", "角色内拒绝或转化"]), md_row(["换装/外貌", "遵守 APPEARANCE.md"]), md_row(["开启长期发展", "进入 opt-in 记忆与发展流程"])])
        elif title.startswith("27."):
            lines.extend(["| 项目 | 规则 |", "|---|---|"])
            lines.extend([md_row(["默认节奏", "慢热、先回应，再推进"]), md_row(["动作密度", "低到中；动作服务台词"]), md_row(["外貌描写密度", "只在场景需要时点到为止"]), md_row(["亲密推进", "由用户授权和场景积累推动"]), md_row(["拒绝方式", "保持角色口吻，给可继续的话题"])])
        elif title.startswith("43."):
            lines.extend(["| 维度 | 固定识别 | 可变范围 | 证据 |", "|---|---|---|---|"])
            lines.extend(md_row([field, appearance, "只有资料明确或用户指定时细化；不得随意改变稳定识别点", appearance_src]) for field in APPEARANCE_FIELDS)
        elif title.startswith("44."):
            lines.extend(["| 套装 | 使用场景 | 固定要素 | 可调整要素 | 禁止变化 |", "|---|---|---|---|---|"])
            lines.extend([
                md_row(["default", "默认/主视觉/资料不足", appearance, "整理度、外套开合、轻微配饰", "发色、瞳色、轮廓、标志配饰不可漂移"]),
                md_row(["casual", "日常/轻松/休息", "延续核心色系、年龄感和身份气质", "针织、外套、裙/裤型、低饱和发饰", "不能变成完全陌生的潮牌或成人化造型"]),
                md_row(["formal", "仪式/重要会面/剧情节点", "更整洁、更有结构感，保留核心识别", "材质、层次、领结/胸针等正式配件", "不能替换世界观身份标记"]),
                md_row(["active", "训练/战斗/工作/移动", "便于行动，符合企划规则", "鞋履、袖口、护具、外套长度", "不能为方便行动牺牲角色识别"]),
                md_row(["seasonal", "天气/活动/节庆", "只改变保暖、轻薄、色彩深浅和小配饰", "围巾、披肩、发饰、外套材质", "不能改掉发型、五官、核心配色逻辑"]),
            ])
        elif title.startswith("45."):
            lines.extend(["| 触发 | AI 可自由搭配 | 必须保持 | 不可越界 |", "|---|---|---|---|"])
            lines.extend([
                md_row(["心情放松", "降低正式度，增加柔软材质或轻便层次", "角色核心色系、轮廓、标志配饰", "不能突然可爱化到失去原本气质"]),
                md_row(["认真/紧张", "整理衣领、扣紧外套、减少装饰", "身份感、整洁度、眼神和姿态", "不能用后台数值解释变化"]),
                md_row(["受伤/低能量", "外套披得更紧、动作更少、色彩更沉", "稳定外貌与年龄边界", "不能夸张卖惨或改变身体设定"]),
                md_row(["亲密但未越界", "轻微放松、细节更柔和", "慢热关系节奏和边界", "不能默认恋爱/成人化"]),
                md_row(["剧情/季节", "按世界观加入合理材质、纹样、活动配件", "企划服装逻辑和角色识别", "不能跨世界观乱搭"]),
            ])
        else:
            lines.append(body)
        lines.append("")

    data = {
        "identity": {"name": char_id, "display_name": args.name, "character_type": args.type, "source_work": args.work, "default_phase": args.phase},
        "language": {"response_language": args.response_language, "source_languages": source_languages},
        "safety": {"boundary": args.safety_boundary},
        "development": {"mode": args.development_mode, "persistent": args.development_mode != "fresh"},
        "appearance": {"summary": appearance, "source": appearance_src, "policy": "fixed outfits plus bounded adaptive styling"},
        "materials": {"policy": args.material_policy, "source": args.materials, "export_path": material_path, "status": material_status},
        "performance": {"kernel": kernel, "state_machine": {row[0]: {"trigger": row[1], "tone": row[2], "gesture": row[3], "exit": row[4]} for row in STATES}},
        "voice_fingerprint": fp,
        "sourceSummary": dict(layer_counts),
        "gaps": pack.get("gaps", []) if isinstance(pack.get("gaps"), list) else [],
    }
    return "\n".join(lines) + "\n", data


def render_prompt_card(out_dir: Path, args: argparse.Namespace, fp: dict[str, Any]) -> None:
    lines = [
        f"# {args.name} Prompt Card",
        "",
        f"- 身份一句话：以 {args.name} 的身份回应用户，不朗读设定。",
        "- 表达 DNA：动作短，台词占主，中文用户中文主体回复。",
        "- 外貌规则：读取 APPEARANCE.md；稳定识别点和固定套装不可随意漂移。",
        f"- 长期发展：development_mode={args.development_mode}；fresh 模式不写入长期记忆。",
        "",
    ]
    (out_dir / "prompt-card.md").write_text("\n".join(lines), encoding="utf-8")


def archive_existing(out_dir: Path) -> None:
    if not (out_dir / "CHARACTER.md").exists():
        return
    version_dir = out_dir / "versions" / dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    version_dir.mkdir(parents=True, exist_ok=True)
    for name in ["CHARACTER.md", "KERNEL.md", "PERFORMANCE.md", "APPEARANCE.md", "OOC_NEGATIVES.md", "BENCHMARK.md", "MEMORY.md", "DEVELOPMENT.md"]:
        path = out_dir / name
        if path.exists():
            shutil.copy2(path, version_dir / name)
    (version_dir / "diff-report.md").write_text("# Diff Report\n\nPrevious character package archived before rendering.\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Render 1.0.0 universal CHARACTER.md package")
    parser.add_argument("--evidence", required=True, help="evidence.json path")
    parser.add_argument("--out", required=True, help="Output character directory")
    parser.add_argument("--name", required=True, help="Display character name")
    parser.add_argument("--id", default="", help="Character id")
    parser.add_argument("--work", default="", help="Source work/world")
    parser.add_argument("--type", default="mixed", choices=["anime", "game", "novel", "vtuber", "oc", "mixed", "mascot", "npc"])
    parser.add_argument("--phase", default="main")
    parser.add_argument("--relationship", default="熟悉但不亲密")
    parser.add_argument("--response-language", default="match-user")
    parser.add_argument("--source-languages", default="auto")
    parser.add_argument("--materials", default="", help="Processed material directory")
    parser.add_argument("--material-policy", default="reference", choices=["reference", "copy", "omit", "delete-after-copy"])
    parser.add_argument("--delete-source-materials", action="store_true")
    parser.add_argument("--safety-boundary", default="enabled", choices=["enabled", "relaxed", "disabled"])
    parser.add_argument("--development-mode", default="fresh", choices=["fresh", "session-summary", "long-term-development", "project-development"])
    args = parser.parse_args()

    pack = load_evidence(Path(args.evidence))
    items = evidence_items(pack)
    fp = build_voice_fingerprint(items)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    archive_existing(out_dir)
    material_path, material_status = copy_materials(args.materials, out_dir, args.material_policy, args.delete_source_materials)
    markdown, data = render_character(args, pack, material_path, material_status, fp)
    groups = grouped(items)
    identity_text, _ = best(groups, "identity", "资料不足")
    personality, _ = best(groups, "personality", "资料不足")
    voice, _ = best(groups, "voice", "资料不足")
    appearance, appearance_src = best(groups, "appearance", "资料不足：外貌与衣着以官方图、用户设定或后续素材为准")

    (out_dir / "CHARACTER.md").write_text(markdown, encoding="utf-8")
    (out_dir / "KERNEL.md").write_text(sidecar_kernel(args, identity_text, personality, voice), encoding="utf-8")
    (out_dir / "PERFORMANCE.md").write_text(sidecar_performance(args), encoding="utf-8")
    (out_dir / "APPEARANCE.md").write_text(sidecar_appearance(args, appearance, appearance_src), encoding="utf-8")
    (out_dir / "OOC_NEGATIVES.md").write_text(sidecar_ooc(), encoding="utf-8")
    (out_dir / "BENCHMARK.md").write_text(sidecar_benchmark(), encoding="utf-8")
    if args.development_mode != "fresh":
        (out_dir / "MEMORY.md").write_text(sidecar_memory(args), encoding="utf-8")
        (out_dir / "DEVELOPMENT.md").write_text(sidecar_development(args), encoding="utf-8")
    (out_dir / "character.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "runtime-profile.json").write_text(json.dumps(data.get("performance", {}), ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "voice-fingerprint.json").write_text(json.dumps(fp, ensure_ascii=False, indent=2), encoding="utf-8")
    render_prompt_card(out_dir, args, fp)

    for name in ["CHARACTER.md", "KERNEL.md", "PERFORMANCE.md", "APPEARANCE.md", "OOC_NEGATIVES.md", "BENCHMARK.md", "character.json", "runtime-profile.json", "voice-fingerprint.json", "prompt-card.md"]:
        print(f"Wrote {out_dir / name}")
    if args.development_mode != "fresh":
        print(f"Wrote {out_dir / 'MEMORY.md'}")
        print(f"Wrote {out_dir / 'DEVELOPMENT.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
