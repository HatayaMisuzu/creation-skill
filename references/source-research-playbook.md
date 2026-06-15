# Source Research Playbook

Use this when searching or reviewing materials for a character, OC, VTuber,
game, anime, manga, novel, or project pack.

## Source Classes

- `official`: official character pages, game sites, anime sites, publisher pages, official PVs, official channels.
- `canon`: original story text, game script, episode subtitles, voice lines, personal route, event story.
- `transcript`: video subtitles, livestream transcript, gameplay text extraction, dialogue dump.
- `user-provided`: user notes, private settings, supplied files, supplied URLs.
- `secondary`: wiki pages, encyclopedias, sourced summaries, episode summaries.
- `moegirl`: 萌娘百科. Treat it as a high-value Chinese ACG secondary source for Chinese names, aliases, localized terminology, project orientation, and source navigation. Do not treat unsourced claims as canon.
- `fan-analysis`: essays, discussions, theory posts, unsourced summaries.
- `simulation`: generated practice dialogue or world-simulation output.

## Review Table

Before deep use, show a table with:

```text
title | URL/path | source class | scope | likely value | risk | recommendation
```

Recommendations:

- `recommended`: high value and low risk.
- `optional`: useful but not essential.
- `needs-user-judgment`: unclear version, fan interpretation, private setting conflict, or sensitive source.
- `reject`: irrelevant, duplicated, low trust, inaccessible, or misleading.

## Chinese ACG Source: Moegirl

When the user is Chinese or the character belongs to an ACG project, include
萌娘百科 in candidate discovery when available:

- search `角色名 作品名 萌娘百科`
- search `site:zh.moegirl.org.cn 角色名 作品名`
- use it to confirm Chinese names, aliases, common translations, project terms, and relationship labels
- cross-check important identity, timeline, and personality claims against official/canon sources

Name and term policy:

- Prefer names and aliases already used by reliable Chinese sources such as official Chinese releases, official localized pages, 萌娘百科, and widely accepted Chinese wiki pages.
- Do not freely translate, machine-translate, or invent Chinese names for characters, units, places, skills, episodes, songs, or projects.
- If no reliable Chinese name exists, keep the original name and mark the Chinese rendering as `needs-user-confirmation`.
- When Chinese sources disagree, show the variants to the user instead of picking silently.

## Project-First Search

For known characters, identify the larger project first. Search both:

- Character-specific sources: personal page, route, PV, voice lines, personal stream, profile.
- Project-level sources: main story, event story, anime episodes, unit videos, worldbuilding pages.

Project-level sources must be filtered for target-character relevance before
they shape the card.

## User Confirmation

Unconfirmed sources remain candidates. If the user says "you decide", use only
recommended sources and mark them `agent-selected`.

## Failure Recovery

If web/video extraction fails, ask for one of:

- direct transcript/subtitle file
- alternative URL
- local downloaded subtitles
- episode/game script text
- permission to broaden search
- permission to continue with sparse evidence
