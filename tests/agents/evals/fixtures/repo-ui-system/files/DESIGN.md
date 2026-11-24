# plainboard design

Warm, editorial and quiet: boards read like a well-set page, not a dashboard.

## Colour

| Token | Value | Use |
|---|---|---|
| `--color-page` | `#FBF7F0` | page background |
| `--color-surface` | `#FFFDF9` | cards and forms |
| `--color-text` | `#2B2118` | body text |
| `--color-muted` | `#6B5B4B` | secondary text, field borders |
| `--color-line` | `#D8CBB8` | hairlines |
| `--color-primary` | `#C2410C` | the one main action per page, links |
| `--color-on-primary` | `#FFFFFF` | text on the primary colour |

## Type

- Interface and body: Fraunces, then Georgia and serif. Body 16/24, labels 13/18, page title 32/40.
- Numbers: the body face with tabular figures.

## Space and shape

- A 4 px base: 4, 8, 12, 16, 24, 32, 48.
- Square corners everywhere except buttons, which take 2 px.
- No shadows. Regions are divided by hairlines.

## Components

- One primary button per page; every other action is a text link in the primary colour.
- Cards are a surface with a hairline border and 16 px padding.
- Every field has a visible label above it.
