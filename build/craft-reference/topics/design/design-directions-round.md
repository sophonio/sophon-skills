---
id: design-directions-round
summary: Direction option anatomy as a fill-in template, one filled example, safer and bolder redraws, a side-by-side picker.
reviewed: 2026-11
---
# Direction round: option anatomy and examples

## Option anatomy

Every option uses the same fields in the same order, so the four can be compared line by line.

```
Option <n>: <name, 1-3 words>
Thesis: <one sentence: what this direction believes about the product>
Colours:
  <name>  #RRGGBB  <role>            (text pairs: <ratio> on <surface>)
  ... 4 to 6 lines: page, surface, text, muted text, one accent, one more if it has a meaning
Type: <heading face> / <body face> / <numeric or code face>, each with fallbacks
First viewport:
  <ASCII wireframe, at most 12 lines, the real first screen of this product>
Risk: <the honest cost: who it may not suit, what it makes harder>
```

- The name says the idea ("Night shift"), not a mood word ("Modern").
- A colour with no role is cut. An accent's role says what it means.
- The risk is real for every option, the recommended one included.

## Filled example

A scheduling tool for clinic front desks, operate surface.

```
Option 2: Ward board
Thesis: the day is a board people read at a glance from two metres away.
Colours:
  wall     #F4F6F8  page
  card     #FFFFFF  surface
  ink      #14202B  text          (15.25 on wall)
  pencil   #51606E  muted text    (5.97 on wall)
  late     #B42318  overdue edge and icon, beside "Late" (6.57 on card)
  free     #1F6F43  open slot edge and icon, beside "Free" (6.15 on card)
Type: Public Sans / Public Sans / IBM Plex Mono, system fallbacks
First viewport:
  +--------------------------------------------------+
  | Tue 24 Nov    Dr. Rao  Dr. Kim  Dr. Osei   [+]   |
  | 08:00  [Free]   [J. Park] [Late: A. Diaz]        |
  | 08:30  [M. Ali] [Free]    [S. Cho]               |
  | 09:00  ...                                       |
  +--------------------------------------------------+
Risk: large type and a fixed board cut what fits; a clinic with
twenty rooms needs scrolling the board was meant to avoid.
```

## Safer and bolder

A redraw changes options 2 and 3 only, and keeps the product truth and the first viewport's content.

| Register | What changes | Ward board becomes |
|---|---|---|
| Safer | closer to the category standard: familiar layout, quieter colour, stock components | a standard day calendar with the same two status colours and a list of today's arrivals |
| Bolder | one move pushed further, the rest kept plain | the board fills the screen at wall-display size, rooms as columns, the time line moving down in real time |

A safer option is still specific to the product; a bolder one is still usable at the floor.

## Picker layout

The four options side by side, the same specimen in each column, so only the direction differs.

```
Picker
  Heading "Choose a direction" + one line: what each column shows
  Grid (4 columns; stacks to 1 column under 900 px)
    Column (one per option)
      Name and thesis
      Swatches: chip + name + hex + role; ratio beside each text pair
      Type sample: heading line, body line, a number in the numeric face
      Specimen: the same real screen fragment, rendered in this direction
      Risk line
      Choose button (label "Choose <name>")
  Footer: free-text field "Safer or bolder?" + submit
```

- Same specimen content in every column: the product's real words and numbers, never placeholder text.
- Columns keep equal width and order 1 to 4; the recommended option is marked in its label only, never by size or colour.
- Each column renders its own light and dark surface, or one toggle switches all four together.
