---
id: design-open-systems
summary: Five public design systems as facts in one anatomy: licence, fit, colour model, type, space, shape, depth, motion.
reviewed: 2026-11
---
# Open design systems: five recipes

Facts about five public design systems, in our own words and one anatomy, as of 2026-11. Material, Carbon, Primer, Fluent and Radix are their owners' marks, named only to identify public design systems. Values drift between releases: read the system's own documentation for the installed version before writing tokens from this page. A system the user picked is used as its owners define it, themed through its own token or theme mechanism, not restyled by hand.

| System | Owner | Code licence | Fits |
|---|---|---|---|
| Material 3 | Google | Apache-2.0 | Android, cross-platform apps, consumer products |
| Carbon | IBM | Apache-2.0 | data-heavy enterprise tools |
| Primer | GitHub | MIT | developer tools, dense information |
| Fluent 2 | Microsoft | MIT | apps beside Microsoft products, enterprise |
| Radix | WorkOS | MIT | React product interfaces built to be themed |

## Material 3

- Colour model: one seed colour generates tonal palettes (tones 0 to 100) for primary, secondary, tertiary, neutral, neutral variant and error. Components use roles: primary and on-primary, primary-container and on-primary-container (the same for secondary, tertiary and error), surface and on-surface, on-surface-variant, five surface-container steps, outline and outline-variant. Android can derive the seed from the wallpaper.
- Type: fifteen styles, display, headline, title, body and label in large, medium and small; body medium is 14/20, body large 16/24, label large 14/20 at medium weight. Default faces: Roboto and Roboto Flex, both open-licensed.
- Space: a 4 dp grid; window size classes compact under 600, medium 600 to 839, expanded 840 and up (larger classes above 1200).
- Shape: a corner scale of none 0, extra-small 4, small 8, medium 12, large 16, extra-large 28 and full.
- Depth: levels 0 to 5 (0, 1, 3, 6, 8, 12 dp), shown mostly by a lighter or darker surface tone rather than by shadow.
- States: a state layer of the on-colour over the component: 8% hover, 10% focus and pressed, 16% dragged. Disabled content at 38% opacity.
- Motion: easing tokens emphasized, standard, and their decelerate and accelerate forms (standard is cubic-bezier(0.2, 0, 0, 1)); durations from short (50 to 200 ms) through medium, long and extra-long (up to 1000 ms). Newer releases add spring-based motion.
- Signature: tonal surfaces, filled, tonal, outlined and text buttons, a floating action button, navigation bar, rail or drawer.
- Repair for the stock look: generate the scheme from the product's own seed colour; the baseline purple left unchanged reads as a template.

## Carbon

- Colour model: four themes, White and Gray 10 (light), Gray 90 and Gray 100 (dark). A layering model stacks background, layer-01, layer-02 and layer-03; tokens name roles such as text-primary, text-secondary, border-subtle, interactive and focus. The interactive colour is Blue 60, #0F62FE.
- Type: IBM Plex Sans, Mono and Serif (open-licensed). Two sets: productive for product screens, expressive for larger editorial moments; body-01 is 14/20 with slight positive tracking, label-01 12/16.
- Space: the 2x Grid on an 8 px mini unit, 16 columns at large widths; breakpoints at 320, 672, 1056, 1312 and 1584 px. Spacing steps 2, 4, 8, 12, 16, 24, 32, 40, 48, 64, 80, 96 and 160 px.
- Shape: square corners on most components.
- Depth: few shadows; layers differ by grey value, and overlays carry a modest shadow.
- States: a 2 px focus border in the focus colour, inset on most controls; hover and active steps are named tokens per layer.
- Motion: productive (quick, for tasks) and expressive (for significant moments) curves; durations fast-01 70 ms, fast-02 110, moderate-01 150, moderate-02 240, slow-01 400, slow-02 700. Productive standard easing is cubic-bezier(0.2, 0, 0.38, 0.9).
- Signature: dense data tables, Plex everywhere, rectangular buttons with a trailing icon, a disciplined grid.
- Repair for the stock look: keep the grid and type, and carry the product's own content density; Carbon left blue-on-grey with demo content reads as an IBM tool.

## Primer

- Colour model: functional tokens by purpose, not hue: foreground (default, muted, on-emphasis), background (default, muted, emphasis), border, and role families accent, success, attention, severe, danger, done and sponsors. Themes include light, dark, dark dimmed, high contrast and colour-vision variants of each. The accent foreground is #0969DA in light; the dark canvas is #0D1117; the primary button is green (#1F883D in light).
- Type: the system font stack, 14 px body at a 1.5 line height; a system monospace stack for code. Brand pages use Mona Sans (open-licensed).
- Space: a 4 px base with steps 4, 8, 16, 24, 32, 40 and 48 px.
- Shape: radius small 3 px, medium 6 px, large 12 px, and full.
- Depth: border-led; boxes have a 1 px border and a header row; shadows appear on overlays only.
- States: a 2 px focus outline in the accent colour; selected tabs use a bottom border.
- Motion: minimal; short fades and slides on overlays.
- Signature: bordered boxes with header rows, counters as small pills, underline navigation, 16 px line icons, one green primary action.
- Repair for the stock look: change the accent and the primary action to the product's own roles; Primer left stock reads as a GitHub page.

## Fluent 2

- Colour model: neutral ramps plus a 16-step brand ramp; components read alias tokens such as background, foreground, stroke and brand. Default web brand colour #0F6CBD; light foreground #242424, secondary foreground #424242, stroke #D1D1D1. Light, dark and high-contrast themes.
- Type: Segoe UI Variable on Windows, Segoe UI with system fallbacks elsewhere. Segoe UI is a system font, not one to bundle on the web; use the system stack. Ramp: caption 12/16, body 14/20, subtitle 20/26 (and 16/22), title 24/32 to 32/40, large title 40/52, display 68/92.
- Space: a 4 px grid; spacing tokens 2, 4, 6, 8, 10, 12, 16, 20, 24 and 32 px.
- Shape: radius 2, 4, 6 and 8 px, and circular; buttons and inputs use 4.
- Depth: shadow tokens 2, 4, 8, 16, 28 and 64, each a key shadow plus an ambient one; the number rises with the layer.
- States: a 2 px focus stroke (dark and light pair) visible on any background.
- Motion: durations from 50 ms (ultra fast) through 100, 150, 200, 250, 300 and 400 to 500 ms (ultra slow); named curves such as decelerate, accelerate and easy ease.
- Signature: soft layered surfaces, subtle acrylic only on platform shells, compact command bars.
- Repair for the stock look: set the brand ramp from the product's colour; keep neutrals.

## Radix

- Colour model: 12-step scales per hue, each in light and dark, with alpha and wide-gamut variants. Steps 1 and 2 are backgrounds; 3 to 5 component backgrounds (normal, hover, pressed or selected); 6 to 8 borders (subtle, element, strong and focus); 9 and 10 solid fills (9 the purest, 10 its hover); 11 low-contrast text; 12 high-contrast text. Steps 11 and 12 stay readable on step 2. Grey families (gray, mauve, slate, sage, olive, sand) pair with nearby accents.
- Type: Radix Themes sizes 1 to 9 are 12, 14, 16, 18, 20, 24, 28, 35 and 60 px on the system stack by default.
- Space: steps 1 to 9 are 4, 8, 12, 16, 24, 32, 40, 48 and 64 px; a scaling setting runs from 90% to 110%.
- Shape: a radius setting of none, small, medium, large or full applied across components.
- Depth: hairlines from steps 6 to 8 do most of the work; small shadows on floating panels; panels may be solid or translucent.
- States: Radix Primitives supply behaviour without styling: roles, keyboard support, focus management and dismissal for dialogs, popovers, menus, tabs, tooltips and selects. shadcn/ui copies styled versions of them into a project.
- Motion: none by default; enter and exit states are exposed as data attributes for the project's own CSS.
- Signature: hairline borders, small radii, one accent at step 9, grey text at step 11.
- Repair for the stock look: choose the accent and grey family for the product; indigo or violet on slate, left stock, reads as a template.
