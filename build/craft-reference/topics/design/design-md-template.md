---
id: design-md-template
summary: DESIGN.md skeleton in the fixed section order, the YAML token block and its slots, the dated-rule line, ownership.
reviewed: 2026-11
---
# DESIGN.md: skeleton, token block and dated rules

DESIGN.md follows the public DESIGN.md convention (format version "alpha", read at a pinned commit in 2026-11). The file has machine-readable YAML tokens and human-readable prose; the tokens are normative and the prose explains how to apply them.

## Skeleton

Sections use `##` headings in this order; a section that does not apply may be left out, and an unknown section is kept by readers.

```
---
version: alpha
name: <system name>
description: <one line>
<token block: see below>
---

# <Product> design system

## Overview
Users, job, constraints, surface mode, character; for a system adopted
from code, where each value came from.

## Colors
Each colour's role and meaning; dark and light pairs; text-pair ratios.

## Typography
Faces with fallbacks and licences; the scale; numerals.

## Layout
Grid, spacing, density, content widths, breakpoints.

## Elevation & Depth
The one depth strategy; a table of levels and their use.

## Shapes
Radius scale, and which part takes which radius.

## Motion & Micro-interaction
What moves and what never does; durations and easings by purpose;
the reduced-motion rule.

## Voice & Content Strategy
Tone, capitalization, terms, button labels, empty and error wording,
numbers, dates and units.

## Components
Variants and states, the icon set, component files as @components/button.html.

## Do's and Don'ts
- Do ...
- Don't ...
- YYYY-MM-DD: <rule>. Why: "<the user's words>"
```

The headings "Brand & Style", "Layout & Spacing", "Elevation" and "Motion" are accepted aliases of the matching sections. Two sections with the same heading make the file invalid.

## Token block

Tokens sit in the front matter or in fenced `yaml` blocks inside their sections; each top-level key appears once per file.

```yaml
colors:
  light:
    page: "#F8FAFC"
    surface: "#FFFFFF"
    text: "#1E293B"
    text-muted: "#475569"
    primary: "#4F46E5"
    on-primary: "#FFFFFF"
  dark:
    page: "#09071A"
    surface: "#110F26"
    text: "#E2E8F0"
    text-muted: "#94A3B8"
    primary: "#818CF8"
    on-primary: "#1A1735"
typography:
  body-md: { fontFamily: Outfit, fontSize: 14px, fontWeight: 400, lineHeight: 20px }
  numeric: { fontFamily: JetBrains Mono, fontSize: 13px, fontFeature: '"tnum"' }
rounded: { sm: 6px, md: 10px, lg: 14px, full: 9999px }
spacing: { xs: 4px, sm: 8px, md: 16px, lg: 24px, xl: 32px }
motion:
  state-change: { duration: 150ms, delay: 0ms, timingFunction: "cubic-bezier(0.16, 1, 0.3, 1)" }
  surface-enter: { duration: 220ms, delay: 0ms, timingFunction: "cubic-bezier(0.16, 1, 0.3, 1)" }
  surface-exit: { duration: 150ms, delay: 0ms, timingFunction: "cubic-bezier(0.4, 0, 1, 1)" }
components:
  button-primary: { backgroundColor: "{colors.light.primary}", textColor: "{colors.light.on-primary}", rounded: "{rounded.md}", padding: 12px }
```

| Slot | Holds | Notes |
|---|---|---|
| colors | any CSS colour, hex preferred | groups such as `light` and `dark` are allowed and flatten to dotted paths |
| typography | fontFamily, fontSize, fontWeight, lineHeight, letterSpacing, fontFeature, fontVariation | px, em or rem; a unitless line height multiplies |
| rounded, spacing | named scale steps | dimensions in px, em or rem |
| motion | duration, delay, timingFunction per purpose name | durations in ms |
| components | backgroundColor, textColor, typography, rounded, padding, size, height, width | values or `{path.to.token}` references; a state is its own key (`button-primary-hover`) |

- No slot exists for shadows, borders, focus-ring width or opacity: those go in a table in their prose section (Elevation & Depth, Components), and the table binds like a token.
- A reference points at one value (`{colors.dark.text}`), never a group; only component tokens may point at a whole typography entry.
- A flat key and a group that flatten to the same name (`primary-light` beside `primary.light`) are an error.
- `omitted` lists sections left out on purpose, with an optional reason.

## Dated rules

One correction the user wants kept becomes one line under Do's and Don'ts:

```
- 2026-11-24: Tables use 13 px text with 18 px lines, never 14. Why: "the old table felt loose"
- 2026-11-24: Never put the brand colour on body text. Why: "it read like a link"
```

- One class of thing per rule (all tables, every link), not one element and not the whole product.
- The why quotes the user's own words; with no words, there is no why to write.
- A rule a check can enforce (a lint rule, a token restriction) names that check.

## Ownership

| Part | Written by | Read by |
|---|---|---|
| Token block (front matter or yaml blocks) | Design System Engineer, kept equal to the code tokens | everyone |
| Overview, Colors, Typography, Layout, Elevation & Depth, Shapes, Motion prose | UI/UX Designer | Frontend Developer, Visual Designer |
| Voice & Content Strategy | UI/UX Designer | anyone writing interface copy |
| Components, icon set | UI/UX Designer | Frontend Developer |
| Do's and Don'ts and dated rules | any of the four design agents, one line at a time | everyone |
