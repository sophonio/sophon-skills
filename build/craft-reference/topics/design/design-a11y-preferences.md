---
id: design-a11y-preferences
summary: What to check in code for reduced motion, contrast preference and forced colours, with passing and failing examples.
reviewed: 2026-11
---
# Preference checks: reduced motion, contrast, forced colours

Each check reads the stylesheets and components; none needs a browser. WCAG references are to 2.2.

## Reduced motion

What to look for: every `animation`, `transition`, scroll-bound effect and script-driven animation, and whether a `prefers-reduced-motion: reduce` path keeps its end state.

Failing: the reduce path is missing, or it removes the end state.

```css
.panel { animation: slide-in 300ms ease-out both; }
@media (prefers-reduced-motion: reduce) { .panel { display: none; } }
```

Passing: the end state stays; the movement goes.

```css
.panel { animation: slide-in 300ms ease-out both; }
@media (prefers-reduced-motion: reduce) {
  .panel { animation: fade-in 1ms both; }
}
```

- A global rule that sets every duration to about 1 ms passes, if nothing depends on an `animationend` event that then fires late or never.
- Script: an animation library configured to follow the user setting, or a `matchMedia("(prefers-reduced-motion: reduce)")` check that is read and listened to.
- Anything that plays by itself for over 5 seconds needs a pause, stop or hide control in every mode: that is 2.2.2, level A. The reduce path itself maps to 2.3.3, level AAA.
- Parallax, zoom-on-scroll and auto-advancing carousels are the usual misses.

## Contrast preference

What to look for: a `prefers-contrast: more` block, and what it changes.

- Useful changes: hairlines and field edges to a stronger colour, muted text one step darker, translucent and blurred surfaces made opaque, thin focus rings made thicker.
- Failing patterns: secondary text at about 4.5:1 that never gets stronger; meaning carried by a low-alpha tint alone; a block that exists but changes nothing visible.

```css
@media (prefers-contrast: more) {
  :root { --border: var(--text-muted); --text-muted: var(--text); }
  .surface { background: var(--panel); backdrop-filter: none; }
}
```

`prefers-contrast: less` and `custom` are rarely handled; note them only when the project targets them.

## Forced colours

Under `forced-colors: active` (Windows high contrast) the browser replaces colours with a small system palette and drops shadows and background images that are colour only. What to look for in code:

| Pattern in code | Under forced colours | Fix |
|---|---|---|
| Focus ring drawn with `box-shadow` only | invisible | add `outline: 2px solid transparent`; it turns visible in forced colours |
| A selected state shown by background colour only | identical to unselected | add a border, outline, check icon or `aria-current` styling with `Highlight` |
| A button or chip with no border, only a fill | its edge disappears | `border: 1px solid transparent` on the base style |
| Icon as a CSS background image, or an SVG with a fixed fill | may vanish or keep a wrong colour | inline SVG with `fill: currentColor` |
| Status shown by a coloured dot alone | all dots look alike | a word or an icon shape beside it |
| `forced-color-adjust: none` on a large region | the user's palette is refused | limit it to swatches and previews that must show real colour |

System colour keywords for a deliberate forced-colours style: `Canvas`, `CanvasText`, `LinkText`, `ButtonFace`, `ButtonText`, `ButtonBorder`, `Highlight`, `HighlightText`, `GrayText`, `Field`, `FieldText`.

```css
@media (forced-colors: active) {
  .chip[aria-pressed="true"] { border-color: Highlight; color: HighlightText; background: Highlight; }
  .card { border: 1px solid CanvasText; }
}
```

This check is in code only: it says where meaning would be lost, not how the screen looks under a given palette.
