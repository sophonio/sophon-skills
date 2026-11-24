---
id: design-motion
summary: Motion decision steps: frequency, purpose, easing, duration; enter and exit patterns; reduced-motion equivalents.
reviewed: 2026-11
---
# Motion: purpose, durations, easing, reduced motion

Where the project has motion tokens (a Motion section in DESIGN.md, or duration and easing tokens in code), their values come first; the numbers here are the fallback.

## Purpose

Four questions, in order. A "no" at the first one ends it.

1. How often is it seen? Used many times a day (a command palette, a list's keyboard selection, a tab switch an expert makes constantly): no animation. A few times a day: short and subtle. Rarely (onboarding, a first load, a success moment): it may be expressive.
2. What does it explain? A good answer names a change: where a panel came from, that an item was added, removed or moved, that something is loading, that an action took effect. "It looks nice" is not an answer.
3. Which easing fits the kind of change? See the table below.
4. How long? As short as still reads; interface motion stays under 300 ms.

| Purpose | Example | Keep it |
|---|---|---|
| Feedback | a button press, a toggle | 100-160 ms, a small scale or colour change |
| Spatial origin | a menu or popover opening from its trigger | 150-250 ms, scaling from the trigger's side |
| Change of content | an item added, removed, reordered | 200-300 ms, opacity plus a short move |
| Continuity | a drawer, a sheet, a route change | 250-300 ms, a slide from the edge it lives at |
| Waiting | loading, progress | a loop only while waiting; never decoration |

## Duration and easing

| Kind of change | Easing | Duration |
|---|---|---|
| Entering (appears, opens) | ease-out, such as cubic-bezier(0.16, 1, 0.3, 1) | 150-250 ms |
| Leaving (closes, dismisses) | ease-in, or ease-out at about 75% of the enter time | 100-200 ms |
| Moving on screen (reorder, resize by transform) | ease-in-out | 200-300 ms |
| Hover and colour changes | ease or linear | 100-150 ms |
| A small playful value (a count, a chip) | a gentle spring with slight overshoot | 200-300 ms |

- Ease-in on an entrance feels slow at the moment people watch, so entrances use ease-out.
- Bounce and elastic curves suit playful, physical subjects only.
- Stagger lists at 20-50 ms per item, and cap the total under 300 ms.
- Animate transform and opacity only. Never `transition: all`; name each property.
- Motion is interruptible: a second click reverses from the current position instead of waiting.
- Focus rings, text input and theme switches change instantly.

## Enter and exit

| Element | Enter | Exit |
|---|---|---|
| Dropdown, popover | opacity 0 to 1, scale 0.96 to 1 from the trigger side (set transform-origin) | the reverse, faster |
| Dialog | opacity, scale 0.96 to 1, backdrop fades | opacity only |
| Drawer, sheet | translate from its edge, 100% to 0 | back to its edge |
| Toast | from its edge, 8-16 px plus opacity | opacity, then the stack closes up |
| Tooltip | opacity after a 300-500 ms delay; instant for the next tooltip while one is open | instant |
| List item added | opacity and 4-8 px translate | opacity, then the gap closes |
| Page or route | a short opacity change, or none | none |

- Never grow from scale(0): nothing in the world appears from a point. Start from about 0.95.
- Content that exists in the server HTML (a page heading) is visible before any script; an entrance may move it, never hide it.

## Reduced motion

Under `@media (prefers-reduced-motion: reduce)` the end state stays and the journey goes.

| Motion | Reduced equivalent |
|---|---|
| Slide, scale, parallax | an opacity change of 150 ms or less, or an instant change |
| Spring or bounce | linear, short |
| Autoplay longer than 5 seconds | paused, or one still frame, with a visible pause control in every mode |
| Scroll-bound scene | the final frame, static |
| Loading shimmer | a static skeleton, or a slow opacity pulse |
| Duration tokens | set to about 1 ms so every component inherits the change |

```css
@media (prefers-reduced-motion: reduce) {
  :root { --duration-fast: 1ms; --duration-base: 1ms; --duration-slow: 1ms; }
  .sheet { transition-property: opacity; }
}
```

In script, read `window.matchMedia("(prefers-reduced-motion: reduce)").matches` once and listen for its change event; an animation library's own reduced-motion setting goes to "user".
