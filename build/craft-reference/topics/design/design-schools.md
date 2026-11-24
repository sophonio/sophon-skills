---
id: design-schools
summary: Six design schools as recipes in one anatomy: thesis, fit, palette with ratios, type, space, shape, motion, moves.
reviewed: 2026-11
---
# Design schools: six recipes in one anatomy

A school is a way of working, not a theme to paste. Each recipe is a starting point: the palette, faces and moves are examples to bend toward the product, so a direction built from it still passes the swap test (it should not fit another field's product unchanged). Every face named is under the SIL Open Font License or is a system stack. Ratios are WCAG 2 contrast on the recipe's page colour; each recipe shows one mode, and the other mode is derived role by role.

## Index

| School | In one line | Fits | Poor fit |
|---|---|---|---|
| Swiss | a strict grid, one accent, type does the work | data, documentation, public services | playful consumer products |
| Editorial | reading first: measure, rhythm, serif text | long reads, journals, knowledge bases | dense operational tools |
| Modern tool | hairlines, compact type, a quiet dark canvas | developer tools, dashboards, admin | marketing that must persuade warmly |
| Brutalist | raw structure shown on purpose | archives, indie tools, manifestos | anything that must feel safe and polished |
| Warm humanist | soft forms, warm neutrals, a friendly voice | health, education, community, consumer | high-density data work |
| Experimental | one bold idea carries the page | launches, portfolios, events | daily-use product screens |

Options in one round come from different rows. Two recipes from the same row are one option with a tint.

## Swiss

- Thesis: order is the beauty; a visible grid and strong type replace decoration.
- Fits: persuade or read surfaces with real information; operate surfaces that need calm.
- Palette: `paper  #FFFFFF  page`; `ink  #111111  text (18.88)`; `grey  #5C5C5C  muted text (6.69)`; `rule  #D9D9D9  hairline`; `signal  #D62D20  the one accent (4.93; white on it 4.93)`.
- Type: Public Sans for everything, two or three weights; tabular numerals; a large size jump between title and body (2.5x or more).
- Space and density: a 12-column grid, an 8 px rhythm, generous outer margins, tight internal grouping.
- Shape and depth: square or 2 px corners; no shadows; rules and alignment separate content.
- Motion: almost none; a crisp 150 ms opacity or position change on state.
- Signature moves: flush-left ragged-right text; numbers set large in a grid; one red element per view; asymmetric layouts that still sit on the grid.
- Avoid: centred stacks; more than one accent; decorative icons.

## Editorial

- Thesis: the page is for reading; hierarchy comes from typographic rhythm, not boxes.
- Fits: read surfaces, essays, documentation with long prose.
- Palette: `paper  #FCFCFA  page`; `ink  #1A1A1A  text (16.94)`; `stone  #5E5A55  muted text (6.66)`; `rule  #E6E2DC  hairline`; `oxblood  #7A1F2B  links and one accent (9.93)`.
- Type: Newsreader or Source Serif 4 for text at 18-21 px with a 1.5-1.6 line height; Fraunces for display; Source Sans 3 for interface labels.
- Space and density: a measure of 60-75 characters; wide margins; space between sections larger than any gap inside them.
- Shape and depth: flat; hairline rules; pull quotes and figures break the column, not cards.
- Motion: none beyond link and focus states.
- Signature moves: drop caps or a large first line; marginal notes; figures with real captions; a strong table of contents.
- Avoid: cream paper with a terracotta accent and a thin serif display (a generated default); italic accent words in every heading.

## Modern tool

- Thesis: a quiet, exact instrument; density is respect for the expert's time.
- Fits: operate surfaces, developer tools, consoles, admin.
- Palette (dark first): `canvas  #0B0D10  page`; `panel  #14171C  surface`; `text  #E6E8EB  text (15.85)`; `muted  #9BA3AE  muted text (7.64; 7.05 on panel)`; `line  #232830  hairline`; `blue  #4C8DFF  primary and selection (6.08; canvas text on it 6.08)`.
- Type: Geist Sans for interface text at 13-14 px; Geist Mono with tabular numerals for ids, numbers and code.
- Space and density: a 4 px base; 32-36 px rows; compact controls; a side navigation on the canvas colour.
- Shape and depth: 6-8 px radius; hairline edges; shadows only on floating layers; field edges at 3:1 or more.
- Motion: 100-200 ms ease-out on state changes; nothing on frequent actions.
- Signature moves: a command palette; keyboard hints beside actions; monospace chips for ids; one accent for selection only.
- Avoid: near-black with an acid green or neon accent (a generated default); glow; glass.

## Brutalist

- Thesis: the structure is the style; nothing pretends to be softer than it is.
- Fits: archives, indie software, manifestos, tools for people who like their web raw.
- Palette: `white  #FFFFFF  page`; `black  #000000  text and edges (21.00)`; `grey  #6B6B6B  muted text (5.33)`; `link  #0000EE  links (9.40)`; `marker  #FFE600  fill only, black text on it (16.57)`.
- Type: the system sans stack in bold for headings; a system serif or mono for body; huge size contrast.
- Space and density: visible grid lines; content packed edge to edge or with blunt gaps.
- Shape and depth: 0 radius; 2-4 px black borders; hard offset shadows if any.
- Motion: instant changes; at most a hard cut.
- Signature moves: underlined links that look like links; exposed metadata; tables as the main layout; one fluorescent highlight.
- Avoid: brutal for its own sake on a page someone must trust with money or health; low-contrast grey on grey.

## Warm humanist

- Thesis: a calm, kind interface that feels made by people for people.
- Fits: persuade and experience surfaces in health, learning, community, consumer apps.
- Palette: `linen  #FAF7F2  page`; `cocoa  #2B2622  text (14.01)`; `clay grey  #6B625A  muted text (5.58)`; `sand  #E7E0D6  hairline`; `sage  #4F6F52  primary (5.27; white on it 5.63)`; `ochre  #E9B44C  highlight fill, cocoa text on it (7.91)`.
- Type: Fraunces at a soft optical setting for headings; Nunito Sans for body at 16-17 px.
- Space and density: generous; 8 px base; large touch targets; short lines.
- Shape and depth: 12-20 px radius; soft, low shadows; hand-drawn or photographic detail used sparingly.
- Motion: gentle 200-300 ms ease-out; a small spring on success moments only.
- Signature moves: real photographs of real people the client supplies; plain-spoken copy; one warm illustration style used consistently.
- Avoid: pastel everything; a mascot on every screen; rounded type at every size.

## Experimental

- Thesis: one idea, pushed far, carries the page; everything else stays plain so the idea reads.
- Fits: launches, portfolios, events, campaign pages with a short life.
- Palette: `concrete  #F2F2EE  page`; `ink  #0A0A0A  text (17.64)`; `slate  #55554F  muted text (6.69)`; `coral  #FF4F1F  fill only, ink text on it (6.02)`; `ultramarine  #2B3BFF  links and accents (5.90; white on it 6.62)`.
- Type: Unbounded or Syne for display, set very large; Instrument Sans for text.
- Space and density: deliberate breaks of the grid; one oversized element per viewport.
- Shape and depth: chosen by the idea; usually flat.
- Motion: one orchestrated moment (a load sequence, a scroll-bound scene), with a still frame under reduced motion and a pause control if it runs over 5 seconds.
- Signature moves: kinetic or variable type; an unusual navigation that is still a list of links underneath; a single bold colour field.
- Avoid: scroll-jacking; motion on every section; an experiment on a screen people use every day.
