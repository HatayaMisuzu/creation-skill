# Script Toolbox

Scripts are optional helpers. They improve repeatability, but the model must be
able to continue manually when they fail or are unavailable.

## Material Tools

- `collect_sources.py`
  - Use for URL batches, local folders, subtitles, HTML, JSON, and YouTube fallback collection.
  - Outputs material manifests, cleaned text, segments, diagnostics, and recovery advice.
  - Manual fallback: read accessible sources directly, summarize source value, and ask the user for missing transcripts/subtitles.

- `extract_character_materials.py`
  - Use for speaker tagging, alias matching, relevance filtering, and target-character material extraction.
  - Outputs target speech, other evaluation, context, low-confidence material, audit, and discarded context.
  - Manual fallback: build evidence notes with `source | speaker | claim | used_for | confidence`.

## Evidence Tools

- `build_evidence_pack.py`
  - Use to consolidate collected material into evidence JSON and gap reports.
  - Manual fallback: keep a compact evidence table and source summary.

- `detect_evidence_conflicts.py`
  - Use to find phase, canon, user-setting, or fan-analysis conflicts.
  - Manual fallback: list conflicting claims and ask the user which to preserve.

- `check_contamination.py`
  - Use to detect simulated lines, user preferences, or fan analysis being mislabeled as canon.
  - Manual fallback: audit each new claim for source type and overwrite risk.

## Generation Tools

- `render_character.py`
  - Use when an evidence pack should be rendered into standard files.
  - In 1.0.0 it can also emit `KERNEL.md`, `PERFORMANCE.md`, `OOC_NEGATIVES.md`, and `BENCHMARK.md`; `MEMORY.md` and `DEVELOPMENT.md` are emitted only when long-term development is explicitly enabled.
  - Manual fallback: write `CHARACTER.md` from the template and add sidecars only when they help runtime quality.

- `render_prompt_card.py`
  - Use to create a low-token runtime card.
  - Manual fallback: compress identity, personality, voice, language, relationship, safety, and examples.

- `build_phase_map.py`
  - Use when versions/phases need machine-readable output.
  - Manual fallback: write phase differences in section 7.

## Evaluation Tools

- `build_dialogue_tests.py`
  - Use to create reusable audition prompts.
  - Manual fallback: test 3-5 core scenarios.

- `run_dialogue_regression.py`
  - Use with an OpenAI-compatible model config when automatic reply generation and scoring are desired.
  - Manual fallback: fill replies manually and score against the validation rubric.

- `evaluate_dialogue_quality.py`
  - Use for static or semi-automatic dialogue quality checks.
  - Manual fallback: inspect language, voice, relationship, boundary, and immersion risks.

## Project Tools

- `build_project_pack.py`
  - Use to assemble project-level files and multiple character cards.
  - Manual fallback: write `PROJECT.md`, timeline, relationship graph, and group rules.

- `simulate_project_scene.py`, `update_world_state.py`, `validate_world_state.py`
  - Use for long-running simulations.
  - Manual fallback: keep backend notes private and summarize only visible scene events.

## Export Tools

- `export_adapters.py`
  - Use for Hermes, World Tree, SillyTavern, Character.AI style, JSON, compact, or prompt-snippet exports.
  - Manual fallback: adapt from `CHARACTER.md` while preserving language, safety, relationship non-intrusion, and anti-contamination rules.

## General Failure Policy

- Do not stop just because a helper fails.
- Record the failure and recovery advice.
- Ask the user for missing files, transcripts, alternate URLs, or permission to continue with caveats when needed.
