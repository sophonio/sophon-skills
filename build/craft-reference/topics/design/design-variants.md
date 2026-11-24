---
id: design-variants
summary: Variant axes with examples, the comparison table, and a one-at-a-time switcher in one route or file.
reviewed: 2026-11
---
# Variants: axes, comparison table, switcher

## Axes

Each variant differs from the others on one named axis; three tints of one idea give the user nothing to choose between.

| Axis | Variant A | Variant B | Variant C |
|---|---|---|---|
| Layout | table with a detail drawer | master list and detail pane | cards grouped by status |
| Density | compact rows, 13 px | comfortable rows, 14 px | spacious, two lines per item |
| Hierarchy | the total leads | the exceptions lead | the newest item leads |
| Interaction model | edit in place | edit in a drawer | a step-by-step flow |

## Comparison table

```
| Variant | Axis | Wins when | Costs |
|---|---|---|---|
| A Table + drawer | layout | people compare many rows | less room for long text |
| B List + pane | layout | people work one item at a time | fewer rows visible |
| C Status board | layout | the status is the decision | weak for sorting and search |
```

## Switcher

- One route (`/prototype/<name>?v=a`) or one HTML file shows one variant at a time, full size, with the same real data in each.
- A small fixed control names the variants by their axis value ("A Table + drawer"), switches with a click or the keys 1 to 5, and keeps the choice in the URL.
- The control is excluded from the variants' own layout and is easy to delete: one component, one import.
- After the choice the route or file, the control and the losing variants are removed; only the chosen one is built for real.
