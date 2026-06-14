# creation-skill

Model-led skill for creating, researching, distilling, updating, evaluating, and
simulating universal virtual-character agents.

It is built for anime, manga, games, light novels, VTubers, OCs, mascots, NPCs,
and project-level character ecosystems. The core design goal is to let an agent
load the skill and perform high-quality character work mostly through model
reasoning, with scripts used only as optional deterministic helpers.

## What It Produces

The main artifact is always:

```text
character-cards/<id>/CHARACTER.md
```

`CHARACTER.md` is both a character card and a runtime roleplay skill. v10 can
also produce sidecars:

```text
KERNEL.md              # compact high-priority character core
PERFORMANCE.md         # decision function, tension, emotion gradients, gestures
OOC_NEGATIVES.md       # anti-drift and negative examples
BENCHMARK.md           # audition prompts and scoring criteria
character.json         # machine-readable helper
prompt-card.md         # compact runtime prompt
voice-fingerprint.json # expression summary
```

Long-term development is opt-in. These files are generated only when the user
explicitly enables a persistent development mode:

```text
MEMORY.md
DEVELOPMENT.md
```

Default conversations are fresh and do not mutate persistent memory.

## Design Principles

- Model first, scripts second.
- Generic agent ecosystem, not tied to one runtime.
- Chinese users receive Chinese main replies even when source material is in Japanese or English.
- Source confirmation is required before deep use of web/video/wiki material.
- Relationships are internal context unless the user or scene triggers them.
- Project simulation is frontstage-only: no visible debug state, numeric deltas, or speaker schedules.
- Self-learning and simulated lines improve performance guidance, but never become canon.

## Repository Layout

```text
SKILL.md        # concise model-led entrypoint
references/     # progressive-disclosure playbooks
scripts/        # optional deterministic helpers
profiles/       # example local configuration files
agents/         # Codex UI metadata
```

Runtime output folders such as `character-cards/`, `materials/`,
`project-packs/`, and `work/` are ignored by git.

## Quick Validation

From the repository root:

```powershell
python -m py_compile (Get-ChildItem scripts -Filter *.py | ForEach-Object { $_.FullName })
python C:\Users\Lenovo\.codex\skills\.system\skill-creator\scripts\quick_validate.py .
```

All scripts support `--help`.

## Optional Model Evaluation

`profiles/model-eval-config.example.json` shows the shape for automatic
dialogue regression with an OpenAI-compatible endpoint. API keys must come from
environment variables, for example `OPENAI_API_KEY`; do not write secrets into
the repository.

## License

No open-source license has been declared yet. Public visibility does not grant
reuse rights beyond what GitHub's terms allow for viewing and forking. Add a
license file before inviting broad reuse.
