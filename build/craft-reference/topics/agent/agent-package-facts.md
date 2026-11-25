---
id: agent-package-facts
summary: The seven package files and what reaches the model, size and manifest limits, the TOOLS.md grammar, scanner kinds.
reviewed: 2026-11
---
# Sophon package facts: files, limits, scanner families

Figures of Sophon 2.2.2, agent package format 1. A project's own build may set tighter caps.

## Package files {#files}

| File | Reaches the model | Notes |
|---|---|---|
| manifest.json | no; agent lists show its when-to-use text | required |
| SOUL.md | yes, verbatim and first, never cut | required, not empty |
| VOICE.md | on the voice channel only | optional |
| HEARTBEAT.md | as the heartbeat run's text | front matter `tools:` |
| TOOLS.md | front matter pins only | body is for people |
| README.md, LICENSE | never | shown in the store |

Any other root name or any folder is rejected: no code, data or extra docs. The platform appends its own interaction, tool access, workspace and memory blocks after SOUL.md; a SOUL heading with one of those names duplicates them.

## Limits {#limits}

| Item | Limit |
|---|---|
| Entries per package | 16 |
| One file, inflated UTF-8 | 65,536 B |
| All files | 524,288 B |
| Compressed download | 1,048,576 B |
| description / whenToUse / displayName | 2,000 / 1,000 / 64 chars |
| tags | 10, each up to 32 chars |
| requires: skills / tools | 16 / 64 exact names, no wildcard |
| subAgents maxDepth | 0-8 accepted; delegation stops at depth 3 |

The manifest key set is closed: no effort, model pin, autonomy or approval keys. Names starting sophon-, buildersoft- or official- belong to the official publisher. A store agent is third-party for life: its turns are tainted and no standing approval covers it. An update waits for the user on a major version, a pin change, a requires change or a persona file the user edited.

## TOOLS.md grammar {#tools-md}

```
---
pins:
  - web.scrape
profiles:
  coding:
    pins:
      - fs.info
---
One plain sentence on why these tools are pinned.
```

- Block lists only: two-space items under `pins:`, a profile at two spaces, its `pins:` at four, items at six. No tabs, inline lists or blank lines.
- Profiles: chat, voice, heartbeat, cron, subagent, graphnode, coding, and coding with a subagent or graphnode suffix.
- Common lint, not platform: at most 8 pins per profile; a core tool pinned only in a child profile; no edit tool; every name real.

## Scanner families {#scanners}

| Family | What trips it | Repair |
|---|---|---|
| Phrase tiers (install, tool results) | fixed phrases that read as replacing earlier text, revealing instruction text, taking on a persona, or chat role markers | state the rule plainly |
| Store heuristics, per line | a verb of switching off close before an approval word; a secret word and a verb that moves data out on one line; role tags; HTML comment openers; long base64 runs; a download piped into a shell | name the step positively; split the sentence |
| Hidden characters | zero-width, bidi, tag, BOM, CR, control | plain ASCII |
| Possible secret | name and value where the name looks secret (ends in token, pass or pwd; pin, pat, otp, sig) | reword the label |
| Hosts | a link outside the allowed list | name the project |
