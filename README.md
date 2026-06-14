# creation-skill

**版本：1.0.0**

`creation-skill` 是一个模型主导、脚本辅助的通用虚拟角色生成与演绎 Skill。它面向二次元角色、游戏角色、轻小说/漫画/动画角色、VTuber、OC、看板娘、NPC，以及以多个角色为核心的企划世界。

它的核心目标不是把角色做成一份静态设定表，而是让 Agent 能够读取 Skill 后，高质量完成：

- 搜索、筛选、确认角色资料来源。
- 从网页、字幕、视频转写、本地文本和用户设定中提取证据。
- 蒸馏角色人格、表达 DNA、关系、边界和世界观。
- 生成可直接运行的 `CHARACTER.md`。
- 让角色对话更有张力、更立体、更沉浸。
- 支持可选的长期发展模式，让角色在用户允许时积累经历和成长。
- 支持企划级多角色关系网、世界状态和群像模拟。

## 核心产物

主产物始终是：

```text
character-cards/<id>/CHARACTER.md
```

`CHARACTER.md` 同时是人物卡和角色运行 Skill。它可以被通用 Agent 直接读取，用于角色扮演、对话、企划模拟或导出到其他运行环境。

1.0.0 版本还可以生成这些辅助文件：

```text
KERNEL.md              # 高优先级角色内核摘要
PERFORMANCE.md         # 决策函数、内在张力、情绪梯度、非语言表现
OOC_NEGATIVES.md       # OOC 反例库和偏移修正规则
BENCHMARK.md           # 角色试镜题和评测标准
character.json         # 机器友好的角色摘要
prompt-card.md         # 低 token 运行提示卡
voice-fingerprint.json # 声音/表达指纹
```

长期发展模式是**可选项**，默认不开启。只有用户明确选择长期发展对话、长期关系记忆或企划发展模拟时，才生成：

```text
MEMORY.md
DEVELOPMENT.md
```

默认新对话是 `fresh` 模式，不会写入长期记忆，也不会让临时对话污染角色设定。

## 设计原则

- **模型为主，脚本为辅**：模型负责判断、蒸馏、写作、演绎和自检；脚本只做收集、清洗、校验、导出等确定性辅助工作。
- **Agent 通用**：不绑定 Codex、Hermes、World Tree、Claude、SillyTavern 或 Character.AI。
- **证据驱动**：官方、原作、台词、用户设定、二手资料、粉丝分析、模拟内容必须分层处理。
- **中文用户中文输出**：即使素材大多是日文或英文，也要保持对中文用户的中文主体回复。
- **关系网不抢戏**：关系角色只作后台推理，除非用户或场景触发，不主动乱入。
- **长期发展默认关闭**：角色可以成长，但必须由用户显式开启。
- **前台沉浸**：企划模拟不能向用户显示数值变化、debug 标签、speaker schedule 或场景焦点分析。
- **反污染**：模拟台词、自学习结果、用户偏好不能被写成 canon。

## 仓库结构

```text
SKILL.md        # Skill 主入口，模型加载时优先阅读
references/     # 按任务拆分的执行手册和方法论
scripts/        # 可选辅助脚本
profiles/       # 示例配置
agents/         # Codex Skill 展示元数据
```

运行产物默认不入库，包括：

```text
character-cards/
materials/
project-packs/
work/
```

这些目录已在 `.gitignore` 中排除，避免把素材、角色卡、缓存或用户私有内容推送到 GitHub。

## 典型工作流

1. 用户给出角色名、作品名、OC 设定、网址、本地素材或视频信息。
2. Agent 判断任务类型：搜索资料、蒸馏角色、更新旧卡、修复 OOC、企划模拟或导出。
3. Agent 搜索或读取资料，并把候选来源交给用户确认。
4. Agent 把材料拆成角色本人台词、他人评价、上下文、用户设定、二手资料和粉丝分析。
5. Agent 蒸馏角色内核、人格、表达 DNA、场景响应、边界、张力系统和 OOC 反例。
6. Agent 生成 `CHARACTER.md` 和必要 sidecar。
7. Agent 进行 3-5 轮内部试演，修正语言不一致、设定朗读、关系乱入、OOC 和后台状态泄露。
8. 如果用户开启长期发展模式，才把重要经历写入 `MEMORY.md` / `DEVELOPMENT.md`。

## 验证方式

在仓库根目录运行：

```powershell
python -m py_compile (Get-ChildItem scripts -Filter *.py | ForEach-Object { $_.FullName })
python C:\Users\Lenovo\.codex\skills\.system\skill-creator\scripts\quick_validate.py .
```

所有脚本都应支持：

```powershell
python scripts/<script-name>.py --help
```

## 自动对话评测

`profiles/model-eval-config.example.json` 提供 OpenAI-compatible endpoint 的示例配置。API Key 只允许从环境变量读取，例如：

```text
OPENAI_API_KEY
```

不要把密钥写入仓库。

## 许可证

当前尚未声明开源许可证。仓库公开只代表可见，不代表授予自由复用、分发或商用授权。正式开放复用前建议添加明确的 `LICENSE` 文件。
