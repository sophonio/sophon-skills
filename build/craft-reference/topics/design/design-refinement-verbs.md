---
id: design-refinement-verbs
summary: Bolder, quieter, distill and polish: what each changes and keeps, typical moves, before and after, the report table.
reviewed: 2026-11
---
# Refinement verbs: bolder, quieter, distill, polish

A refinement works on one named target (a hero, a table, a card, a form) and keeps the rest of the design as it is. Refining preserves the system; a change of tokens, layout model or direction is a redesign, and belongs to a different conversation.

## Bolder

- Changes: contrast of scale, weight and colour inside the target; the one move a person should remember.
- Stays: the palette, the faces, the grid, everything outside the target.
- Typical moves: one size jump of 2x or more between the key element and its neighbours; a heavier weight for the one figure that matters; the accent spent on a single element; more space around the key element; cropping an image tighter.
- Skeleton test: with the text blurred, the target's main element is the first thing found.
- Not bolder: more colours, more effects, a gradient, a glow, a bigger everything.

Example, a pricing card: before, plan name, price and features all at 16 px with three accent badges. After, the price at 40 px in the numeric face, one accent on the call to action, badges removed, features in muted text.

## Quieter

- Changes: the target's volume: fewer accents, lower contrast steps for secondary parts, less motion, fewer borders.
- Stays: the hierarchy (the primary action still comes first), the floor contrast, the content.
- Typical moves: secondary buttons to quiet or text style; borders to spacing; saturated fills to tints; two weights instead of four; motion removed from anything that is not a state change.
- Quiet needs an intent: say what should now lead, or the result goes generic.

Example, a dashboard header: before, four coloured stat cards with icons in tinted squares and a gradient banner. After, one row of four figures in the text colour with muted labels, hairline dividers, the alert figure the only one in a status colour beside its word.

## Distill

- Changes: the number of things in the target: elements, words, options, steps.
- Stays: every function the target must still perform, and its data.
- Typical moves: merge duplicate actions; cut decorative elements; turn three sentences into one; move rare options behind a disclosure; replace a card grid with a list; drop a column nobody sorts or reads.
- Check: each removed thing is listed, with where its function went (or that it had none).

Example, a settings form: before, 14 fields in three cards, a help paragraph each, Save and Apply and Cancel. After, the 5 fields people change, the 9 others under "More options", one Save, help as one line under the fields that need it.

## Polish

- Changes: execution only: alignment, spacing on the scale, optical balance, consistent radii, states, type details.
- Stays: the design. Polish never conceals a redesign.
- Typical moves: snap off-scale values to the scale; align baselines and edges; match inner and outer radii (outer = inner + padding); add the missing hover, focus-visible, disabled and loading states; tabular numerals in tables; balanced heading wraps; a real empty state.
- Check: list the values that moved and the states that were added.

Example, a data table: before, row padding 9, 11 and 12 px, numbers left-aligned in the proportional face, no focus style on rows. After, 10 px rows from the density token, numbers right-aligned with tabular numerals, a focus-visible ring on rows, a skeleton for loading.

## Report table

```
Verb: <bolder | quieter | distill | polish>   Target: <named target>
Stays as it is: <what was deliberately left alone>

| Where | Before | After | Why |
|-------|--------|-------|-----|
| hero price | 16 px, regular | 40 px numeric face, semibold | the price is the decision |
| plan badges | 3 accent badges | removed | accent kept for the action |

Outside the target (proposals, not edits):
- <change and why>
```
