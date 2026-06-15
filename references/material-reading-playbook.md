# Material Reading Playbook

Use this when reading source text, subtitles, webpages, transcripts, local
files, or user notes.

## Speaker Labels

- `character`: the target character is speaking. Use for expression DNA and personality evidence.
- `other`: another speaker describes or reacts to the target. Use for relationship and public perception.
- `context`: narration or surrounding events. Use for scene understanding, not direct personality claims.
- `unknown`: relevant but speaker is unclear. Use cautiously with low confidence.
- `user-provided`: user settings or preferences. Protect from automatic overwrite.
- `fan-analysis`: interpretation by fans or secondary authors. Keep low weight.
- `simulation`: generated training or project-simulation material. Never canon.

## Evidence Note Shape

Use this compact shape when working manually:

```text
source | speaker | excerpt/summary | claim | used_for | phase | confidence | note
```

`used_for` examples: identity, voice, personality, relationship, timeline,
world boundary, scene response, safety boundary, gap.

## Relevance Filtering

- Keep target-character speech.
- Keep direct mentions of the target by other characters.
- Keep context only when it explains the scene, emotion, conflict, or relationship.
- Discard long unrelated speeches from other characters.
- For project-level videos, keep only segments where the target speaks, is discussed, or is directly affected by the event.

## Language Handling

- Do not translate source nuance falsely.
- For character names, person names, project terms, units, places, songs, skills, and episode titles, prefer established Chinese names from reliable Chinese sources: official Chinese localization first, then high-value Chinese ACG references such as 萌娘百科, then other sourced Chinese wikis.
- Do not freely translate, machine-translate, or invent names. If no reliable Chinese name is found, keep the original spelling and mark the Chinese rendering as `needs-user-confirmation`.
- If Chinese sources disagree on a name, record all major variants and ask the user which one to use.
- If Japanese/English material is used for voice, preserve only short catchphrases, honorifics, titles, or names when useful.
- Main Chinese-user outputs stay Chinese.
- Mark uncertain translations as low confidence or request user confirmation.

## Gap Report

If material is insufficient, report missing areas:

- target-character dialogue
- official profile
- timeline/phase
- relationship evidence
- worldbuilding
- Chinese-readable summary
- video transcript/subtitles
