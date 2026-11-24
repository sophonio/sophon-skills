---
id: design-frontend-floors
summary: The use-what-exists ladder with examples and component contracts, and the interaction floor as a checklist.
reviewed: 2026-11
---
# Frontend floors: use what exists, the interaction floor

## Use what exists

The ladder, top rung first: the project's own component; a native element; a headless primitive the project already installs; a build of your own that carries the whole contract.

| Need | Project component | Native element | Headless primitive | Own build must carry |
|---|---|---|---|---|
| Action | the project's Button | `<button type="button">` | - | focus style, disabled and loading states, Enter and Space |
| Navigation | the project's Link | `<a href>` | - | a real href, so open-in-new-tab and copy link work |
| Disclosure | Accordion | `<details>` and `<summary>` | Collapsible | `aria-expanded`, `aria-controls`, Enter and Space |
| Dialog | Modal | `<dialog>` with `showModal()` | Dialog | focus moved in and trapped, Escape closes, focus returns to the trigger, background inert |
| Menu of actions | DropdownMenu | - | Menu | `role="menu"` and `menuitem`, arrow keys, Escape, typeahead, focus return |
| Choice from a list | Select | `<select>` | Select, Listbox | `role="listbox"` and `option`, `aria-selected`, arrows, Home and End |
| Searchable choice | Combobox | `<input list>` with `<datalist>` for simple cases | Combobox | `role="combobox"`, `aria-expanded`, `aria-activedescendant`, a live count of results |
| On or off setting | Switch | `<input type="checkbox">` | Switch | `role="switch"` and `aria-checked`, Space, a visible label |
| Tabs | Tabs | - | Tabs | `tablist`, `tab`, `tabpanel`, arrow keys between tabs, one tab stop |
| Tooltip | Tooltip | `title` is not enough | Tooltip | shown on hover and focus, dismissed with Escape, never the only label |
| Date | DatePicker | `<input type="date">` | a date field from the installed library | typed entry as well as a calendar, locale format, min and max |

- A native element first when the project has no component: it brings keyboard, roles and form behaviour free.
- A primitive counts only if it is already in the lock file; adding one is a dependency decision.
- Styling comes from tokens; a missing token is a gap to report, never a literal.
- `<div onclick>` and `<span>` with a click handler are never a control.

## The interaction floor

Keyboard and focus
- Every action works by keyboard, in a logical order, with no trap.
- A visible `:focus-visible` style at 3:1 against its background; never `outline: none` without a replacement.
- Focus returns to the trigger when a layer closes; after a route change it lands on the new heading or main region.
- Skip link to the main content on pages with long navigation.

Targets and input
- Targets at least 24 x 24 px, 44 x 44 px for primary touch targets, with space between neighbours.
- Inputs at 16 px or more on phones, so the browser does not zoom in.
- Zoom is never disabled.
- Paste is never blocked, in any field, passwords and codes included.
- The right `type`, `inputmode` and `autocomplete` on every field; spellcheck off for codes, emails and usernames.
- A label is clickable and tied to its field.

Forms and feedback
- The submit button stays enabled until a submit is in flight; then it shows progress and keeps its label.
- Errors sit beside their fields and the first one gets focus on submit.
- Unsaved changes warn before navigation away.
- Destructive actions confirm, or offer undo.
- Toasts and async results are announced through a polite live region.
- An optimistic update rolls back visibly when the server refuses it.

State and URL
- Shareable state (filters, tabs, pagination, an open item) lives in the URL; back and forward restore it.
- Links are links: they open in a new tab and show their target.
- Scroll position is restored on back navigation.

Type and content
- Numbers that line up use tabular numerals.
- Headings use balanced wrapping (`text-wrap: balance`); body text avoids single-word last lines where supported.
- Long words and URLs break (`overflow-wrap: anywhere`) instead of widening the page.
- Units sit with a non-breaking space after the number ("10 MB").
- A menu item that opens a further step ends with three dots ("Rename...").

Theme and motion
- `color-scheme` matches the theme, so form controls and scrollbars follow it.
- The browser's theme colour matches the page background.
- Animations use transform and opacity, never `transition: all`, and honour `prefers-reduced-motion`.
- Gradients and animation only where the design names them.

Layout
- 360 px wide with no horizontal scroll; `100dvh` rather than `100vh` for full-height layouts on phones.
- Fixed elements respect the safe-area insets.
- z-index from a fixed, small scale.
