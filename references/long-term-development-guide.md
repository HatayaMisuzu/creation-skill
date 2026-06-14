# Long-Term Development Guide

Long-term development is optional. Default to a fresh conversation unless the
user explicitly asks to continue a long-running relationship, save memory, or
run a project simulation whose events should shape later behavior.

## Modes

- `fresh`: default. Do not write `MEMORY.md` or `DEVELOPMENT.md`; use only the card and current chat.
- `session-summary`: summarize this session at the end, but do not apply it unless the user approves.
- `long-term-development`: update lived experience, relationship memory, and growth notes.
- `project-development`: update project simulation memory and character growth caused by visible project events.

Ask which mode to use when the user's wording implies persistence but is not
explicit.

## Layer Separation

- `canon`: official/original facts. Dialogue cannot overwrite this.
- `user-provided`: private settings and user choices. Protect unless changed by the user.
- `lived-experience`: things the character and user experienced in this runtime.
- `growth`: stable changes caused by repeated or important lived experiences.
- `simulation`: generated practice or project events. It can influence runtime growth only if marked as accepted.

## MEMORY.md

Record relationship memory from the character's viewpoint, not as a database
dump. Good memory items include:

- how the user addressed the character
- promises made or broken
- moments that made the character trust, doubt, soften, or withdraw
- boundaries the user respected or crossed
- repeated interaction preferences
- unresolved emotional threads

Do not write private sensitive data unless the user explicitly asks. Do not
quote long conversations.

## DEVELOPMENT.md

Record durable character changes:

```text
date | trigger event | change | affected fields | evidence | canon impact | rollback note
```

Default `canon impact` is `none`. If a change would alter canon, ask the user to
mark it as AU or private setting.

## Save/Discard Gate

At the end of a long-term session or important project scene, ask the user
whether to:

- save development
- save only a short memory summary
- discard development and keep the next chat fresh
- convert events into AU/private-setting material

## Anti-Contamination

- Simulated practice lines are not original dialogue.
- User preferences are not official personality facts.
- Romance progression is not default canon.
- Project simulation backend state is not frontstage memory.
- A single intense scene should not permanently rewrite personality unless the user approves.
