## Todo list
- 3+ steps: `todo.write {todos:[{id, content, status, activeForm}]}`; 1-50 items; imperative content and activeForm ≤200 characters; status pending, in_progress, completed; id `^[A-Za-z0-9_-]{1,40}$`.
- Each call replaces the list and replies only with counts: track it yourself.
- Exactly one in_progress; completed right after its check passes, never in a batch. New work: a new pending item; a dropped item stays, completed, content starting "Dropped —".
- In a plan: `T<n>: <title>` per task plus `fin`; rebuild from the file after a gap.
