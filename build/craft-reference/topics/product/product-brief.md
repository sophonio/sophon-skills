---
id: product-brief
summary: The one-page brief skeleton, the PRODUCT.md skeleton with what each of its nine headings holds, and a filled brief.
reviewed: 2026-11
---
# Product brief and PRODUCT.md skeletons

Dashes in these forms are written `--` in plain text.

## Brief skeleton

```
Status: draft
# <name>: brief
## Problem
<who has it, in which situation, and what it costs them today>
## Evidence
- <claim> -- <observed | reported | single-source | opinion | none yet>, <source>
## Premises
1. <statement> -- accepted
2. <statement> -- changed: <the user's wording>
Dropped: <a rejected premise>
## Approach
Picked: <approach> -- <why>
Rejected: <approach> -- <why>
Rejected: use what already exists -- <why, or pick it>
## Out
- <at least one thing this will not do>
## Decision
<one question the user answers yes or no>
```

One page is about 300 to 450 words. A section with nothing known holds an `Unknown:` line rather than a guess.

## PRODUCT.md skeleton

| Heading | Holds | Form |
|---|---|---|
| What it is | One or two sentences a new teammate can repeat | Plain sentence |
| Users | Each kind of user and the situation they are in | `<who>: <situation>` |
| Jobs | What each user is trying to get done | `When <situation>, <who> wants to <motivation>, so they can <outcome>.` |
| Constraints | Limits that do not move: law, platform, budget, data location | One line each with its reason |
| Non-goals | What the product deliberately does not do | One line each with its reason |
| Measures | The few numbers that show it works, each with its counter-measure | `<measure> -- counter: <measure>` |
| Glossary | Terms with one meaning each, and words to avoid | `<term>: <meaning>. Avoid: <synonym>` |
| Decisions | Choices that shaped the product | `Decision (YYYY-MM-DD): <choice> -- <reason>` |
| Open questions | What is still unknown, with who can answer | `<question> -- <who>` |

Words only, at most 6,000 bytes: no colours, fonts or layout rules (those live in DESIGN.md), no roadmap dates, no code.

## Filled example

An invented example, to show the density.

```
Status: draft
# Room booking: brief
## Problem
Office managers at firms with 3 to 10 meeting rooms book rooms in a
shared sheet. Clashes are found when two groups arrive at one room.
## Evidence
- Two clashes in the last month at the pilot firm -- reported, interview with the office manager, 2026-11-04
- The sheet has 14 editors and no history -- observed, the sheet itself
- Clashes are common at other firms -- none yet
## Premises
1. Clashes happen about weekly at firms of this size -- changed: "about twice a month"
2. Managers will book from the calendar they already use -- accepted
3. Room data can stay in the firm's calendar service -- accepted
Dropped: managers want usage reports
## Approach
Picked: a free and busy view on top of the existing calendar -- no new place to keep data
Rejected: a standalone booking app -- a second calendar to keep in step
Rejected: use what already exists (calendar room resources) -- the pilot firm's plan lacks them
## Out
- Desk booking, visitor sign-in, usage reports
## Decision
Go ahead with a PRD for the calendar view, first version for one firm?
```
