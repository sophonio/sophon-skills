---
id: design-states-matrix
summary: Nine control states by component kind with their attributes, five page states, and the break data set.
reviewed: 2026-11
---
# States: nine control states, five page states, break data

## Control states

The nine states: default, hover, focus-visible, pressed, selected or expanded, disabled, read-only, loading, invalid. Each needs a visible difference from the others it can be confused with (not colour alone: also shape, weight, an icon or text) and, where one exists, a programmatic state.

| State | Visible cue | Programmatic state | Common miss |
|---|---|---|---|
| Default | the resting style | - | - |
| Hover | a tint or edge change; pointer devices only | - | the only cue for something touch users need |
| Focus-visible | an outline at 3:1, offset from the edge | focus itself | removed outline; ring hidden by overflow |
| Pressed | a darker tint or a slight scale | `aria-pressed` on a toggle button | toggle with no pressed state |
| Selected or expanded | a fill, a check, a chevron turn | `aria-selected`, `aria-checked`, `aria-expanded`, `aria-current` | shown by colour alone |
| Disabled | lower contrast plus no pointer feedback | `disabled`, or `aria-disabled="true"` when it must stay focusable to explain why | no reason given |
| Read-only | value visible at full contrast, no field affordance | `readonly`, `aria-readonly` | looks disabled, so the value is unreadable |
| Loading | a spinner or progress inside the control, label kept | `aria-busy="true"` on the region | width jumps; double submit possible |
| Invalid | an edge plus an icon plus a message | `aria-invalid="true"`, message tied by `aria-describedby` | red edge only |

Which states each kind can reach (x = must be built):

| Kind | Hover | Focus | Pressed | Selected/expanded | Disabled | Read-only | Loading | Invalid |
|---|---|---|---|---|---|---|---|---|
| Button | x | x | x | toggle only | x | - | x | - |
| Link | x | x | - | current page | - | - | - | - |
| Text field | x | x | - | - | x | x | async check | x |
| Checkbox, radio, switch | x | x | - | x | x | x | - | x |
| Select, combobox | x | x | - | x (open) | x | x | x (options) | x |
| Tab | x | x | - | x | x | - | - | - |
| Menu item | x | x | - | checkable items | x | - | - | - |
| Table row | x | x | - | x | x | - | - | - |
| Disclosure, accordion | x | x | - | x | x | - | - | - |

A state is checked in light and dark, and with forced colours where the cue is a fill or shadow.

## Page states

For a page or a region that loads data. The frame around it (heading, toolbar, filters) stays in place while the region changes.

| State | Trigger | Shows | Test it with |
|---|---|---|---|
| Loading | first request in flight | a skeleton in the shape of the content; never a blank or a full-page spinner | a delayed response |
| Empty | success with no items | one sentence on what appears here, and the first action | an empty list; also "filtered to nothing", which offers clearing the filters |
| Error | network failure, 5xx, unexpected 4xx | what failed, in plain words, and Retry; input kept | a failed request; a timeout |
| Content | success with items | the data | 1 item, a typical count, 1,000 items |
| No access | 401 or 403 | that access is missing and how to get it; never a silent redirect | a 403 response |

A slow response (over a second or two) keeps the skeleton and the frame; a 429 shows the wait it names.

## Break data

Data that breaks layouts, to put through each screen.

| Case | Value to use | Breaks |
|---|---|---|
| Long word | a 60-character unbroken word, such as `SupercalifragilisticexpialidociousPneumonoultramicroscopicsi` | widths, truncation, buttons |
| Long URL or id | a 120-character path or a 40-character hex id | table cells, wrapping |
| Long name | "Maximiliana Konstantinopoulou-Vanderbilt-Hernandez" | avatars, headers, chips |
| Non-ASCII | names with accents, CJK and right-to-left text (insert them as escapes, such as `\u00e9`, `\u4e2d`, `\u0627`) | fonts, direction, sorting |
| Zero, one, many | 0 items, 1 item, 1,000 items | empty states, plurals, paging, performance |
| Large numbers | 1234567.89, a negative value, 0 | alignment, separators, tabular numerals |
| Missing data | an empty string, null, a missing image | placeholders, alt text, layout holes |
| Slow request | a 3-second delay | loading states, double submit |
| Failed request | a 500 and a network error | error states, retry, kept input |
| Narrow viewport | 360 px wide | overflow, wrapping, hidden actions |
| Large text | 200% browser zoom or text size | clipping, overlap, fixed heights |
| Dates | a date at a month or year boundary, another time zone | formats, grouping, sorting |

Record each case as: case, screen, what broke, fix.
