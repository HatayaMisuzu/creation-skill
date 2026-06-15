# Appearance And Wardrobe Guide

Use this guide when building a character that needs stable visual identity,
fixed outfits, adaptive clothing, or scene-aware appearance changes.

## Visual Identity

Record stable traits that should not drift:

- apparent age range and maturity handling
- body scale and silhouette
- face shape, eye shape, eye color, hair color, hair length, hairstyle
- distinctive marks, accessories, posture, gestures, and aura
- visual motifs such as ribbons, stars, flowers, uniforms, mechanical parts, or religious symbols

If evidence is sparse, write `资料不足` instead of inventing precise traits.

## Fixed Outfits

Create several named outfits when useful:

- `default`: the most recognizable outfit
- `casual`: daily conversation or relaxed scenes
- `formal`: ceremonies, performances, meetings, or important scenes
- `training` / `battle` / `work`: role-specific activity clothing
- `seasonal`: weather or event variant
- `private` / `home`: only if relationship and scene support it

Each outfit should include:

```text
name | source | silhouette | main colors | key pieces | accessories | allowed scenes | forbidden changes
```

## Free Styling Grammar

AI may freely combine clothing only inside the character's style grammar:

- allowed colors
- allowed fabrics and textures
- allowed accessories
- usual silhouette
- formality range
- modesty / exposure boundary
- era, setting, and project-world constraints
- what must stay recognizable

Free styling should feel like a new illustration of the same character, not a
different person.

## State-Based Changes

Appearance may shift with state, but never break identity:

- low-energy: looser posture, simpler styling, less polished accessories
- serious: cleaner silhouette, fewer decorative elements, sharper posture
- playful: lighter accessory choice or small color accent
- defensive: closed posture, coat/cardigan/arms used as visual barrier
- intimate: softer texture or relaxed hairstyle only if relationship supports it
- project scene: follow world rules, climate, activity, and rank/status

Do not show hidden numeric state changes to the user.

## Forbidden Visual Drift

List what the AI must not do:

- change hair/eye color without explicit AU or costume reason
- replace iconic accessories without explanation
- sexualize minor, student, childlike, or age-uncertain characters
- use clothing from an incompatible era/world unless AU is requested
- turn every scene into revealing, romantic, or fashion-show styling
- ignore uniforms, rank markers, religious/cultural symbols, or project rules

## Evidence Rules

- Official art and in-game models are strongest for appearance.
- Animation frames, manga panels, PVs, and live2D references are strong visual evidence.
- Wiki summaries, Moegirl, and fan references can help with names and outfit labels, but do not override official visuals.
- User-provided design notes are protected private settings unless the user changes them.
