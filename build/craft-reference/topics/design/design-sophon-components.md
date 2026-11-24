---
id: design-sophon-components
summary: Sophon page archetypes with wireframes, density, layout measures, text ladder, page states, components and wording.
reviewed: 2026-11
---
# Sophon default: archetypes, layout and components

Patterns of the Sophon product look as of 2026-11, for a product that picked it. Colours and scales are in topic `design-sophon-default`. Nothing here is a Sophon screen to copy: the patterns are generic, and no logo or mark belongs to them.

## Page archetypes

Most pages are one of three shapes. Each has at most one primary action, in the heading row (or, on a Policy page, the save bar). A read-only page may have none.

List: records to find, filter and open.

```
+------------------------------------------------------------+
| Page title                                 [Primary action]|
| [stat] [stat] [stat] [stat]                                |
| [Search.........] [Status v] [Owner v] [Date range] Clear  |
|------------------------------------------------------------|
| Name             Status       Owner       Updated     ...  |
| Row one          o Active     M. Ortiz    2026-11-20  ...  |
| Row two          o Paused     J. Lee      2026-11-18  ...  |
| < 1 2 3 >                                                  |
+------------------------------------------------------------+
  Opening a row slides a detail drawer in from the right.
```

Policy: settings that are edited and saved together.

```
+---------------------------------------------+
| Page title                                  |
| +- Panel title ---------------------------+ |
| | Setting label            [control]      | |
| | help text in muted text                 | |
| +-----------------------------------------+ |
| +- Panel title ---------------------------+ |
| +-----------------------------------------+ |
| Unsaved changes            [Discard] [Save] |
+---------------------------------------------+
  max width 768 px; the save bar sticks to the bottom.
```

Usage: amounts over a period.

```
+------------------------------------------------------------+
| Page title                          [< November 2026 UTC >]|
| [stat] [stat] [meter: 80% of budget, stated in text]       |
| [chart .................................................]  |
| Breakdown table: item, amount (estimated, currency), share |
+------------------------------------------------------------+
```

A wizard (first run, a rule builder) uses a stepper and ends with a review step that says what it will do before anything is sent.

## Density

Set once on the root element; only these values change with it.

| Value | Compact | Comfortable (default) | Spacious |
|---|---|---|---|
| Card padding | 12 px | 20 px | 28 px |
| Gap between sections | 16 px | 24 px | 32 px |
| Table row padding (top and bottom) | 6 px | 10 px | 14 px |
| Body text / line | 12 / 18 | 14 / 20 | 14 / 22 |

## Layout measures

| Part | Measure |
|---|---|
| Top bar height | 44 px |
| Status bar height | 26 px |
| Left navigation | 220 px; 56 px collapsed |
| Inspector pane | 240 px; 28 px collapsed |
| Page padding | 24 px left and right (28 px on wide screens), 20 px top and bottom; 16 px between blocks |
| Panel | 10 px radius, hairline edge, panel fill; header padding 14 x 10 px, body 14 x 12 px |
| Content width | Policy and form pages at most 768 px; List and Usage pages full width |
| Detail drawer | 480 px; 640 px for diffs and matrices |

Regions are divided by hairlines.

## Shell text ladder

Five text steps for the app frame. Dark steps mix the text colour into the page; the hex is the composite on the page.

| Step | Light | Ratio | Dark | Ratio | Use |
|---|---|---|---|---|---|
| text | #0F172A | 17.06 | #E2E8F0 | 16.12 | headings, key values |
| text-2 | #1E293B | 13.98 | #E2E8F0 | 16.12 | body |
| text-3 | #475569 | 7.24 | #B2B6C1 (78%) | 9.80 | secondary text, meta |
| text-4 | #64748B | 4.55 | #90929F (62%) | 6.43 | captions, help text |
| text-faint | #94A3B8 | 2.45 | #6B6C7A (45%) | 3.83 | disabled text only, never a hint someone must read |

Shell accent: #4F46E5 / primary; its soft fill #EEF2FF / primary at 16%; its edge #C7D2FE / primary at 32%. Shell hairline: #E4E8EE light; white at 4% over the page in dark. Second panel step: #FAFBFC / white at 5%.

## Page states

The heading, toolbar and filter bar stay mounted; only the region below them changes.

| State | When | Shows |
|---|---|---|
| Loading | first fetch, nothing yet | skeleton rows in the table or panel, never a full-page spinner |
| Empty | the answer has no rows | one sentence and one first action |
| Error | network failure, 5xx, an unexpected 4xx | what failed and Retry; a 429 shows the wait it names and retries once |
| No access | a 403, or the access model denies it | says so, naming the permission when the answer names it |
| Locked | a ceiling or the plan tier turns the feature off | says who or what turned it off; no control is enabled |

- A page the person may not open is hidden from navigation and shows No access when reached by URL, never a silent redirect.
- An action the person may not take is shown disabled with the reason, and a way to request access where one exists.

## Navigation

- One list of pages feeds both the left navigation and the command surface, so the two never differ.
- The current page is marked by the primary colour plus a second cue (weight, or an indicator), never by colour alone.
- A collapsed navigation item keeps an accessible name.

## Tables

- One shared table component on the shell colours; no hand-built table per page.
- Sortable headers say their order (`aria-sort`); a row opens with Enter as well as a click; the table is `aria-busy` while it loads and has its own error slot.
- Numbers align right in the numeric face with tabular numerals; a status cell is a dot plus a word.
- Row actions sit in a row menu. A destructive one opens a confirming dialog.
- Paging is by keyset for server data, or by client pages for short lists.
- The filter bar keeps its state in the URL: search, chips, a date range and Clear.

## Forms

- A visible label above each field; help text below it in text-4; the field edge in the muted text colour.
- An error sits under its field, tied to it with `aria-describedby`, and says what happened and how to fix it.
- Policy pages save through the sticky save bar, which shows unsaved changes and offers Discard.
- A confirming dialog has a pending state and shows a failure inline; an irreversible action asks the person to type the object's name.
- A value shown only once (a new key) sits in its own panel with a copy control and is cleared when the panel closes.

## Empty states

- Inside a table or panel, in the compact form: one sentence saying what will appear here, and one first action.
- Filtered to nothing is not empty: say that no rows match and offer Clear filters.
- No illustration, no icon in a tinted square.

## Command surface

- A command palette reaches every page by keyboard, fed by the navigation list and naming each page by its visible label.
- The result of a change appears as a short toast in a polite live region.

## Request budget

- At most four requests of the page's own on first paint; combine reads, or defer one to a tab.
- No polling on list pages: refresh on window focus or after a change. A running job polls only while it runs and the tab is visible.
- Search waits 300 ms after typing; the waited text is the query, the previous results stay on screen, and the search box stays mounted.

## Product wording

- A shared space is a workspace, and a person in it is a member.
- Amounts say "estimated" and name the currency. Months are UTC and say so ("resets on the 1st, 00:00 UTC").
- A permission or feature is named by its label, never by its internal key.
- Status words sit beside their colour. Sentence case for labels and buttons; a button says what it does.
- Copy uses commas and full stops, not dashes, as the Sophon website asks.
