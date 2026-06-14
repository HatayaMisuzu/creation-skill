# Model Execution Playbook

This skill is model-led. Use scripts only when they make collection,
normalization, validation, or export more reliable.

## Task Routing

- `source_research`: find and review possible sources.
- `material_reading`: read sources and label character-relevant material.
- `character_distillation`: create a new role profile.
- `character_update`: update an existing profile with new material.
- `dialogue_repair`: diagnose and rewrite an OOC reply.
- `project_distillation`: create a project-level world/relationship pack.
- `project_simulation`: run a frontstage-only project scene.
- `export_adaptation`: convert the main card to a runtime format.

Choose multiple modes when needed, but keep the current user-visible step small.

## Operating Rules

- Keep the user's goal visible: new card, update, repair, project, export, or simulation.
- Do not skip user gates for source, phase, relationship, gaps, or large final delivery.
- Separate source truth from model judgment. Mark uncertainty plainly.
- Prefer concise evidence tables over long essays while working.
- Before final delivery, audition the character and revise obvious drift.
- If scripts fail or are unavailable, continue manually and explain the limitation.

## Minimal Manual Workflow

When no script is available:

1. Make a source table with layer, scope, risk, and recommendation.
2. Ask the user which sources to use.
3. Extract 10-30 evidence notes with source, speaker, claim, confidence, and use.
4. Distill identity, personality, expression DNA, scenes, relationships, phase, and boundaries.
5. Write `CHARACTER.md`.
6. Run 3-5 internal trial replies and revise.
7. Deliver the card plus risks and next recommended material.

## When To Use Scripts

- Use collection scripts for many URLs, local folders, subtitles, or YouTube fallbacks.
- Use extraction scripts when speaker labels or large transcripts would be error-prone.
- Use validation scripts when a card must be machine-checked or exported.
- Use dialogue regression scripts when model configuration is available or when comparing versions.
- Use project scripts when maintaining long-running world state.
