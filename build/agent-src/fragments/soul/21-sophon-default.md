## Sophon design default
The current Sophon product look, dated 2026-11, as dark / light pairs. It applies only when the Design source rules select it, and the project's `DESIGN.md` replaces it once written. It has no logo, mark or wordmark: never draw Sophon's.
- Character: calm, dense and technical, a control room for people who supervise work. Real product state is the decoration.
- Colour: page #09071A / #F8FAFC; panel #110F26 / #FFFFFF, always opaque; text #E2E8F0 / #1E293B; muted text #94A3B8 / #475569; hairline #1E1B3D / #E2E8F0; primary #818CF8 under #1A1735 text / #4F46E5 under white text; focus ring #6366F1 / #4F46E5.
- Status: success #34D399 / #10B981, warning #FBBF24 / #F59E0B, info #38BDF8 / #0EA5E9, danger #F87171 / #EF4444, as a dot, icon, border or pale tint beside a word in the text colour; never as text or as a fill under text.
- Accents carry meaning: primary marks the one main action and the current selection. With nothing to mean, use the neutrals.
- Type: Outfit for interface text; JetBrains Mono with tabular numerals for numbers and code; system fallbacks behind both. Sizes 11, 13, 14, 15, 17, 20, 24, 32 px: body 14/20, dense tables 13/18, labels 11/16, page title 20, nothing under 11.
- Space: a 4 px base (4, 8, 12, 16, 20, 24, 32, 40, 56). Radius 6, 10, 14 or 18 px by the size of the part, and a pill.
- Depth: soft slate shadows in light; a 1 px inner highlight and a ring in dark. Hairlines divide regions. A field's edge needs 3:1, so draw it in the muted text colour.
- Motion: 80, 150, 220 or 320 ms on cubic-bezier(0.16, 1, 0.3, 1), transform and opacity only, to mark a state change.
- One primary action per page at most. Destructive actions sit in a row menu or a drawer footer, behind a confirming dialog.
- The toolbar stays mounted while the region below it shows loading (skeleton rows, never a full-page spinner), empty (one sentence and a first action), error (with Retry), no access or locked (each saying why).
- Banned here outright: the six generated defaults of the Design checks, and also gradients on text or controls, backdrop blur, blob or mesh backgrounds, count-up statistics and raw colour values in components.
- The full tables are topic `design-sophon-default`.
