# Project Simulation Guide

Use this for project packs, multi-character worlds, and god-view simulation.

## Project Pack Outputs

Use only when the user asks for project-level work:

```text
project-packs/<project-id>/PROJECT.md
project-packs/<project-id>/project.json
project-packs/<project-id>/timeline.md
project-packs/<project-id>/relationship-graph.md
project-packs/<project-id>/characters/<character-id>/CHARACTER.md
project-packs/<project-id>/scenes/group-dynamics.md
project-packs/<project-id>/simulation/
```

## PROJECT.md Contents

- project identity and type
- world rules
- central conflicts
- timeline and phase map
- source boundaries
- relationship graph policy
- group-scene rules
- simulation visibility rules

## Frontstage And Backend

Frontstage output is what the user sees:

- scene prose
- action
- dialogue
- visible consequences

Backend state is private:

- tension
- hidden relationship shifts
- event flags
- speaker schedule
- scene focus
- unresolved simulation notes

Never show backend values or labels in frontstage text.

## Group Scene Rules

- If the user names a character, that character gets priority.
- If the user names multiple characters, keep turns balanced but do not make every character speak every time.
- Unmentioned characters stay quiet unless the scene logically requires them.
- Characters may interact with each other, but their interaction must not bury the user's agency.
- Use relationship evidence to guide conflict, warmth, avoidance, and silence.

## Public Memory

`public-scene-memory.md` should contain only user-visible story events. Do not
store hidden reasoning, private scoring, or backend state there.
