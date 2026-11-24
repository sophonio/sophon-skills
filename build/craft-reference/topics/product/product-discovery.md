---
id: product-discovery
summary: A question bank by kind of product, an ambiguity sweep, premise forms with examples and evidence labels.
reviewed: 2026-11
---
# Discovery question bank and premise forms

Questions about what happened beat questions about what someone would do. "I would use that" and praise for the idea are not demand; a past event with a cost is.

## Question bank

| Kind of product | Questions that surface real demand |
|---|---|
| Consumer app | When did this last happen to you? What did you do instead? What did that cost in time or money? |
| Business tool | Who pays and who uses it, and are they the same person? What sheet or tool does the job today? Who approves a change of tool? |
| Developer tool or API | What do you run today and where does it break? How do you find out it broke? What would adopting a new one force you to change? |
| Internal tooling | Which step is slow or error-prone, and how often does it run? Who does it by hand now? |
| Two-sided product | Which side is scarce? Why would the first ten on each side join before the other side exists? |
| Change to a live product | Which users does it touch? What do they do today that must keep working? What do support requests say? |

Ambiguity sweep, one line per area, before a document is written: scope (what is in and out), data (what is stored and for how long), flow (the steps a person takes), quality (speed, scale, uptime), outside systems, edge and failure cases, constraints and trade-offs, words (terms people use in two senses), and the done signal (what shows it worked).

## Premise forms

A premise is one statement the idea stands on, small enough to accept, change or reject.

| Form | Example (invented) |
|---|---|
| <who> has <problem> about <how often> | Office managers at small firms double-book rooms about once a week. |
| Today they <workaround>, which costs <cost> | Today they keep a shared sheet, and a clash costs a meeting. |
| <who> would switch if <condition> | They would switch if booking took one step from the calendar they already use. |
| The smallest useful version is <thing> | A room list with free and busy times and one-click booking. |
| <constraint> holds | Room data can stay in the firm's own calendar service. |

| Weak premise | Why it fails | Stronger |
|---|---|---|
| Users want it faster | No who, no measure | Support staff wait about 40 s for each search |
| Everyone has this problem | Cannot be rejected | Firms with 3 to 10 rooms report clashes |
| It will grow revenue | A hope, not a fact about users | Two pilot firms paid for a trial month |

## Evidence labels

| Label | Means | Typical source |
|---|---|---|
| observed | Seen in data, logs, tickets or watched use | An export, a log query, a session recording |
| reported | A named person described a real past event | An interview note with a date |
| single-source | Only one source says it | One interview, one article |
| opinion | A belief or forecast, the user's included | "I think teams would like this" |
| none yet | Nothing backs it | -- |

Two sources that disagree get a `Source conflict:` line naming both.
