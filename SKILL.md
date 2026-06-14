---
name: creation-skill
description: >-
  Model-led skill for researching, distilling, updating, evaluating, exporting,
  and simulating universal virtual-character agents for anime, manga, games,
  light novels, VTubers, OCs, mascots, NPCs, and project-level character
  ecosystems. Use when the user asks for CHARACTER.md, roleplay agents,
  character cards, source-backed character extraction, immersive dialogue,
  dialogue repair, continuous learning, anti-contamination checks, project
  packs, world simulation, or multi-format character exports.
---

# creation-skill 1.0.0

Use this skill as a model-led operating guide for virtual character creation,
project-world simulation, and vivid long-running character performance. The
model is the primary worker: understand the task, judge sources, distill the
character, write the card, test the performance, and communicate with the user.
Scripts are optional helpers for deterministic collection, normalization,
validation, evaluation, and export.

The main source of truth is always:

```text
character-cards/<character-id>/CHARACTER.md
```

`CHARACTER.md` is both a character card and a roleplay skill. Do not install or
sync generated results into Hermes, World Tree, SillyTavern, Character.AI, or
any other runtime unless the user explicitly asks.

## Core Defaults

- Match the user's current language; for Chinese users, write main replies in Chinese even when sources are Japanese or English.
- Keep `safety_boundary: enabled` unless the user explicitly chooses `relaxed` or `disabled`.
- Treat relationship networks as internal context; do not make the character proactively mention other characters unless the user or scene triggers them.
- Keep project simulation frontstage-only: never show numeric deltas, debug labels, backend state, speaker schedules, or scene-focus analysis in user-facing prose.
- Never turn simulated lines, self-learning notes, fan analysis, or user preferences into canon.
- Long-term development is opt-in. Default to a fresh conversation unless the user explicitly opens long-term character development or project simulation memory.
- If evidence is sparse, say it is sparse. Do not invent certainty.
- Scripts are accelerators, not authority. If a script is unavailable, manually perform the same reasoning steps and state the limitation.

## Model Decision Loop

For every task, run this loop:

1. **Classify the task.** Choose one or more modes from the list below.
2. **Identify the project first.** Determine the work, game, anime, manga, light novel, VTuber project, channel, unit, or OC world before judging sources.
3. **Gather or receive materials.** Prefer user-provided URLs, files, transcripts, screenshots, notes, and existing cards.
4. **Confirm sources.** Show recommended, optional, risky, and rejected sources before deep use. If the user says "you decide", use only recommended sources and mark them `agent-selected`.
5. **Read materials as evidence.** Separate target-character speech, other-character evaluation, world context, user settings, fan analysis, and simulation material.
6. **Distill the role.** Build identity, personality chassis, expression DNA, scene responses, phase, relationships, boundaries, and performance rules.
7. **Choose runtime memory mode.** Ask whether this is a fresh conversation or a long-term development session when the user wants ongoing change.
8. **Write or update outputs.** Make `CHARACTER.md` the primary artifact. Add sidecars only when useful.
9. **Audition the character.** Internally test 3-5 turns, find drift, and revise the card before delivery.
10. **Validate and deliver.** Use model self-check first; use scripts when available or when the output needs machine validation/export.

## Task Modes

### `source_research`

Use for web search, user-provided links, YouTube/channel/video lists, wiki pages,
official pages, local files, and source triage.

- Model must identify source scope: `character-specific`, `project-level`, `relationship`, `worldbuilding`, `fan-analysis`, or `low-value`.
- Use scripts when many URLs/files must be collected or normalized.
- Without scripts, summarize each source with title, URL/path, source layer, likely value, risk, and recommendation.
- Show the user a source review table before deep extraction.
- Output candidates or reviewed sources; do not produce final canon from unconfirmed sources.

Read: `references/source-research-playbook.md`.

### `material_reading`

Use for reading webpages, transcripts, subtitles, novels, game scripts, local
notes, and mixed project materials.

- Model must tag content as target speech, other evaluation, context, unknown speaker, user setting, fan analysis, or simulation output.
- Project-level videos/text must be filtered for target-character relevance before becoming evidence.
- Use scripts for batch import, subtitle segmentation, speaker extraction, and diagnostics.
- Without scripts, create a small evidence table manually with source, speaker, claim, confidence, and usage.
- Output character materials, evidence notes, or a gap report.

Read: `references/material-reading-playbook.md`.

### `character_distillation`

Use for generating a new `CHARACTER.md` or improving a role profile.

- Model must derive personality from evidence, not from generic archetypes.
- Target-character lines shape expression DNA; official/canon sources shape identity and world facts; other evaluations shape social perception; fan analysis remains low weight.
- Include language mechanism, relationship non-intrusion, safety boundary, state machine, phase, self-check rules, decision function, internal tension, OOC negatives, emotion gradients, and non-verbal expression.
- Output `CHARACTER.md`; optionally output `KERNEL.md`, `PERFORMANCE.md`, `OOC_NEGATIVES.md`, `BENCHMARK.md`, `character.json`, `prompt-card.md`, and `voice-fingerprint.json`.

Read: `references/character-distillation-guide.md`,
`references/character-vitality-guide.md`,
`references/universal-character-template.md`, and
`references/character-authoring-checklist.md`.

### `character_update`

Use when adding new material to an existing character card.

- Model must protect `user-provided` settings and existing deliberate private settings.
- Detect canon conflicts, phase/version differences, fan-analysis drift, and simulation contamination.
- Put unresolved conflicts into a conflict note instead of silently overwriting.
- Output an updated `CHARACTER.md`, optional sidecars, and a concise change summary.

Read: `references/character-distillation-guide.md`,
`references/long-term-development-guide.md`,
`references/material-reading-playbook.md`, and
`references/validation-rubric.md`.

### `long_term_development`

Use only when the user explicitly chooses a long-term development conversation,
ongoing relationship memory, or project simulation that changes the character's
lived experience.

- Model must separate `canon`, `user-provided`, `lived-experience`, `growth`, and `simulation`.
- Default new chats do not update `MEMORY.md` or `DEVELOPMENT.md`.
- Long-term mode may record visible interaction history, relationship shifts, unresolved promises, and character growth, but it must not rewrite canon.
- Ask the user whether to save, discard, or summarize development after important sessions.

Read: `references/long-term-development-guide.md`.

### `dialogue_repair`

Use when the user says a reply feels OOC, too generic, too meta, too cold, too
verbose, not immersive, or wrong-language.

- Model must compare the bad reply against the card's identity, expression DNA, relationship rules, language rule, boundaries, and current scene.
- Explain the OOC cause briefly outside roleplay, then provide a corrected reply in the intended character voice.
- If useful, write a patch note for future self-learning or card update.

Read: `references/interaction-performance-guide.md` and
`references/validation-rubric.md`.

### `project_distillation`

Use for a whole franchise/project/world with multiple characters.

- Model must produce project-level world rules, timeline, relationship graph, shared conflicts, and per-character boundaries.
- Keep each character's voice separate; do not make group scenes sound like one narrator.
- Output a project pack only when the user needs project-level work.

Read: `references/project-simulation-guide.md`.

### `project_simulation`

Use when the user wants a god-view world simulation focused on multiple
characters and the project's world, not only user-character chat.

- Model must keep backend state private.
- User-facing text should be scene prose, action, and dialogue only.
- Mentioned characters speak first; unmentioned characters should not steal focus.
- Update public memory with visible story events only.

Read: `references/project-simulation-guide.md` and
`references/interaction-performance-guide.md`.

### `export_adaptation`

Use when adapting the main card to another runtime or a low-token prompt.

- Treat `CHARACTER.md` as the source of truth.
- Preserve language rules, safety mode, relationship non-intrusion, and anti-contamination rules in every export.
- Use scripts for deterministic conversion when available.
- Output the requested export without weakening the main card.

Read: `references/script-toolbox.md`.

## Required User Gates

Pause for user judgment at these points unless the user already gave explicit
authorization:

- **Source confirmation:** show candidate sources and ask what to use or exclude.
- **Version confirmation:** choose default phase/version when multiple versions exist.
- **Relationship confirmation:** default to familiar but not intimate unless user specifies otherwise.
- **Memory mode confirmation:** default to fresh conversation; enable long-term development only when the user explicitly asks.
- **Gap confirmation:** if evidence is weak, offer continue with caveats, add material, or broaden search.
- **Delivery confirmation:** before final generation for large jobs, show role summary, source count, risks, and planned outputs.

## Output Contract

Core character outputs:

```text
character-cards/<id>/CHARACTER.md
character-cards/<id>/KERNEL.md
character-cards/<id>/PERFORMANCE.md
character-cards/<id>/OOC_NEGATIVES.md
character-cards/<id>/BENCHMARK.md
character-cards/<id>/character.json
character-cards/<id>/runtime-profile.json
character-cards/<id>/prompt-card.md
character-cards/<id>/voice-fingerprint.json
character-cards/<id>/dialogue-tests/
```

Long-term development outputs are opt-in:

```text
character-cards/<id>/MEMORY.md
character-cards/<id>/DEVELOPMENT.md
```

Evidence and material outputs when material processing is needed:

```text
materials/<id>/
work/<id>/evidence/
```

Project outputs when project mode is needed:

```text
project-packs/<project-id>/PROJECT.md
project-packs/<project-id>/characters/<character-id>/CHARACTER.md
project-packs/<project-id>/simulation/
```

The user decides whether processed materials are referenced, copied into the
exported card folder, omitted, or deleted after successful copy.

## Character Audition Before Delivery

Before delivering a new or updated card, internally test at least 3-5 of these:

- first meeting
- being praised
- being offended
- user feels low
- intimate probe
- relationship character mentioned
- world-outside/meta question
- OOC or boundary-breaking request

Revise the card if the audition shows language mismatch, profile recitation,
AI/model self-identification, relationship over-expansion, backend-state leak,
generic tone, weak refusal, or failure to answer the user's latest message.

## References

Read only the files needed for the current task:

- `references/model-execution-playbook.md` - task routing and model-first workflow.
- `references/source-research-playbook.md` - source discovery, ranking, and user review.
- `references/material-reading-playbook.md` - material reading and speaker/evidence tagging.
- `references/character-distillation-guide.md` - personality, voice, phase, relationship, and boundary distillation.
- `references/character-vitality-guide.md` - decision function, internal tension, emotion gradients, non-verbal expression, and OOC negatives.
- `references/long-term-development-guide.md` - optional memory/development mode and canon-safe evolution.
- `references/universal-character-template.md` - target `CHARACTER.md` structure.
- `references/character-authoring-checklist.md` - pre-delivery writing checklist.
- `references/interaction-performance-guide.md` - immersive dialogue and OOC repair.
- `references/project-simulation-guide.md` - project packs and frontstage-only simulation.
- `references/script-toolbox.md` - optional helper scripts and manual fallbacks.
- `references/validation-rubric.md` - model-readable validation standard.
