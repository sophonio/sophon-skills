---
id: design-sophon-default
summary: Sophon product look (2026-11): dark and light roles, status, type, space, radius, depth, motion, themes, fonts, Banned.
reviewed: 2026-11
---
# Sophon default: full token tables

The Sophon product look as of 2026-11, in tables. Values come from the Sophon Dashboard's colour, token and motion files, checked against the product design-language notes and the Sophon website's design rules. Where they disagree, the newest product rule is given, and where a shipped value misses the quality floor, the floor wins. Ratios are WCAG 2 contrast ratios on the page colour unless the row says otherwise.

- Build every screen in dark and in light. Neither mode is the default.
- This look has no logo, mark, wordmark or lockup. Sophon's are never drawn or imitated.

## Dark roles

Product theme name: Core Dark.

| Role | Value | Product token | Ratio | Use |
|---|---|---|---|---|
| Page | #09071A | color-background | - | app background |
| Panel | #110F26 | color-card | 1.06 | cards, drawers, menus; always opaque |
| Raised fill | #1A1735 | color-muted, color-secondary | 1.15 | hover rows, inactive chips |
| Selected fill | #1E1B3D | color-accent | - | selected row, open menu item |
| Text | #E2E8F0 | color-foreground | 16.12 (15.21 on panel) | body, headings |
| Muted text | #94A3B8 | color-muted-foreground | 7.75 (7.31 on panel) | meta, help text |
| Hairline | #1E1B3D | color-border | 1.21 | dividers between regions only |
| Field edge | #94A3B8 | (muted text) | 7.75 | input, select, checkbox outlines |
| Primary | #818CF8 | color-primary | 6.66 | the one main action, the current selection, links |
| On primary | #1A1735 | color-primary-foreground | 5.78 on primary | label on a primary fill |
| Focus ring | #6366F1 | color-ring | 4.45 (4.20 on panel) | focus-visible outline |

## Light roles

Product theme name: Core Light.

| Role | Value | Product token | Ratio | Use |
|---|---|---|---|---|
| Page | #F8FAFC | color-background | - | app background |
| Panel | #FFFFFF | color-card | - | cards, drawers, menus |
| Raised fill | #F1F5F9 | color-muted | - | hover rows, inactive chips |
| Selected fill | #EEF2FF | color-accent, color-secondary | - | selected row; its text #312E81 is 10.22 |
| Text | #1E293B | color-foreground | 13.98 (14.63 on panel) | body, headings |
| Muted text | #475569 | color-muted-foreground | 7.24 (7.58 on panel) | meta, help text |
| Hairline | #E2E8F0 | color-border | 1.18 | dividers between regions only |
| Field edge | #475569 | (muted text) | 7.24 | input, select, checkbox outlines |
| Primary | #4F46E5 | color-primary | 6.01 | the one main action, the current selection, links |
| On primary | #FFFFFF | color-primary-foreground | 6.29 on primary | label on a primary fill |
| Focus ring | #4F46E5 | color-ring | 6.01 | focus-visible outline |

The shell's own text ladder and its light hairline #E4E8EE are in topic `design-sophon-components`.

## Status colours

| Status | Dark | Light | Dark tint (fill, edge) | Light tint (fill, edge) |
|---|---|---|---|---|
| Success | #34D399 | #10B981 | 10% and 25% of the colour | #ECFDF5, #A7F3D0 |
| Warning | #FBBF24 | #F59E0B | 10% and 25% | #FFFBEB, #FCD34D |
| Info | #38BDF8 | #0EA5E9 | 10% and 25% | #F0F9FF, #BAE6FD |
| Danger | #F87171 | #EF4444 | 10% and 25% | #FEF2F2, #FECACA |

- A status shows as a dot, an icon, an edge or a pale tint, always beside a word in the text colour. The word carries the meaning; the colour repeats it.
- Never status-coloured text, and never text on a status fill: light status colours on the page reach only 2.05 to 3.60, and the shipped white labels on status fills 1.92 to 3.76. The text colour on a light tint passes (13.89 on #ECFDF5).
- A focus or selection ring in a status colour uses 40% alpha in dark and 30% in light.
- Chart series, in order: dark #818CF8, #38BDF8, #A78BFA, #34D399, #FBBF24; light #4F46E5, #0EA5E9, #A855F7, #10B981, #F59E0B. A series is named in a legend or label, never by colour alone.

## Type

- Interface face: Outfit, then system-ui, sans-serif. The product loads weights 300 to 700.
- Numeric and code face: JetBrains Mono, then ui-monospace, SFMono-Regular, Menlo, Consolas, monospace, always with tabular numerals (`font-variant-numeric: tabular-nums`). Use it for numbers that line up, ids, timestamps and code, not as a look for headings.

| Step | Size / line (px) | Role |
|---|---|---|
| xs | 11 / 16 | labels, captions, pills; the smallest text anywhere |
| sm | 13 / 18 | dense tables and their controls |
| base | 14 / 20 | body text and controls (density changes it, see the components topic) |
| md, lg | 15 / 22, 17 / 24 | no fixed role in the sources; panel, drawer and dialog headings |
| xl | 20 / 28 | page title |
| 2xl | 24 / 32 | a statistic, in the numeric face |
| 3xl | 32 / 38 | rare; one large figure per screen |

Tracking: tight -0.01em, tighter -0.02em, wide 0.02em. Nothing is set under 11 px; older 10 px labels are not copied.

## Space and radius

| Space step | 1 | 2 | 3 | 4 | 5 | 6 | 8 | 10 | 12 |
|---|---|---|---|---|---|---|---|---|---|
| px | 4 | 8 | 12 | 16 | 20 | 24 | 32 | 40 | 56 |

| Radius | px | Typical part |
|---|---|---|
| sm | 6 | badges, small buttons, checkboxes |
| md | 10 | panels, inputs, buttons, menus |
| lg | 14 | dialogs, large cards |
| xl | 18 | the largest surfaces |
| pill | 9999 | status pills, toggles |

A nested corner follows outer radius = inner radius + the padding between them. Density values (card padding, row height) are in topic `design-sophon-components`.

## Elevation

| Level | Light (soft slate shadow, rgb 15 23 42) | Dark (highlight and ring) |
|---|---|---|
| 0 | none | none |
| 1 | 0 1px 2px at 4% and 0 1px 1px at 3% | inset 0 1px 0 white at 4% |
| 2 | 0 2px 4px at 6% and 0 4px 8px at 4% | inset 0 1px 0 white at 6%, plus a 1px ring of white at 3% |
| 3 | 0 4px 12px at 8% and 0 12px 24px at 6% | inset 0 1px 0 white at 8%, plus 0 8px 24px black at 40% |

- Level 1 for resting cards, 2 for menus and popovers, 3 for dialogs and drawers. A rare light level 4 is 0 8px 28px at 12%; the dark level 4 is a primary glow, which this look bans.
- Panels are opaque in every theme. The dark shell panel flattens to about #100E21; use the named panel value #110F26. The product's translucent surface steps serve glass only, which this look bans.

## Motion tokens

| Token | Value | Typical use |
|---|---|---|
| instant | 80 ms | press feedback, a toggle |
| fast | 150 ms | hover and small state changes |
| base | 220 ms | menus, popovers, tabs |
| slow | 320 ms | drawers and dialogs |
| page | 280 ms | a route change |
| ease-out | cubic-bezier(0.16, 1, 0.3, 1) | entering and most state changes |
| ease-in | cubic-bezier(0.4, 0, 1, 1) | leaving |
| ease-in-out | cubic-bezier(0.65, 0, 0.35, 1) | moving from one place to another |
| spring | cubic-bezier(0.34, 1.56, 0.64, 1) | small contained values only: a count, one chip |

- Animate transform and opacity only: never width, height, top or left, and no path morphs in lists. Focus rings and theme switches never animate.
- Only loading indicators loop: a 1.4 s linear shimmer on skeleton rows and a 1.4 s progress bar, both CSS; the bar stops under reduced motion.
- Under `prefers-reduced-motion: reduce` every duration becomes 1 ms and the spring becomes linear, so end states stay.

## Other themes

The product also ships two more dark themes. Build them only when the project asks for them.

| Role | Core Extra Dark | Graphite |
|---|---|---|
| Page | #000000 | #1D1D1D |
| Panel | #0F0F0F | #2C2C2C |
| Raised fill | #151515 | #323232 |
| Text | #E1E1E1 (16.06) | #E1E1E1 (12.89) |
| Muted text | #B3B3B3 (10.02) | #B3B3B3 (8.04) |
| Hairline | #212121 (1.30) | #3E3E3E (1.58) |
| Primary | #2680EB (5.37) | #2680EB |
| On primary | #000000 (5.37) | #1D1D1D (4.31) |
| Focus ring | #2680EB | #2680EB |

- Status colours equal the dark ones, with tints of 12% and 28%. Elevation highlights are white at 6%, 8% and 10% (level 3 shadow: black at 50%).
- Graphite's label on primary is 4.31: enough for large text and UI parts, short of 4.5 for a small label. Check the pair before use.

## Fonts

| Face | Licence | Notes |
|---|---|---|
| Outfit | SIL Open Font License 1.1 | interface text |
| JetBrains Mono | SIL Open Font License 1.1 | numbers and code |

- Both may be used, embedded and self-hosted in any product. Keep the licence text with bundled font files; the fonts may not be sold on their own.
- Self-host: WOFF2 files in the project's static folder, one `@font-face` per weight with `font-display: swap`, only the weights used (for example 400, 500 and 600), a Latin `unicode-range` subset, and a preload for the body weight.
- Self-hosting keeps the page working offline with no third-party request. Two older faces the product still loads are not part of this look.

## Banned list

| Banned | Repair |
|---|---|
| Gradient text | solid text colour; emphasis by weight or size |
| Gradient or glowing buttons and controls | flat primary fill with its label colour |
| Glow shadows | the elevation levels above |
| Backdrop blur, glass panels | an opaque panel |
| Blob, mesh or aurora backgrounds | the page colour; real state as the visual |
| Count-up statistics | the final number at once, in the numeric face |
| Raw colour values in components (hex, rgb, stock palette classes) | a role token |
| Pixel literals for font size | a type step |
| Status colour as text or under text | dot, icon, edge or tint beside a word |
| Grids of identical icon cards; icons in tinted squares | a table, or a list with a detail drawer; 16 px icons beside text |
| A centred eyebrow, heading and lead on every section | left-aligned headings, one statement each |
| One radius, shadow and typeface everywhere | the scales above, by part |
| Fade-up and hover lift on everything | motion only where state changes |
| Invented numbers, quotes, logos or window chrome | real content or a labelled gap |
| A full-page spinner | skeleton rows in the region that loads |
| A second primary action | one primary; the rest secondary or quiet |
| A field edge in the hairline colour | the muted text colour |
| An accent used for decoration or emphasis | the neutrals |
