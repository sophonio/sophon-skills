# Todoist

Manage your Todoist tasks and projects from Sophon: list active tasks (optionally by project or a
filter query), list projects, add tasks, complete tasks, and update existing tasks.

Implemented with the Todoist API v1 over the Python standard library (no dependencies), so it runs
in the sandbox unchanged. Todoist retired the older `/rest/v2` endpoints, which now answer
`410 This endpoint is deprecated`.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `todoist.list_tasks` | none | List active tasks, optionally by project id or filter query |
| `todoist.list_projects` | none | List all projects |
| `todoist.add_task` | medium | Create a new task |
| `todoist.complete_task` | medium | Mark a task complete (closes it) |
| `todoist.update_task` | medium | Update a task's content, due date, priority, or description |

Tasks are addressed by their string `id`; projects by their `id`. Priority runs from `1` (normal) to
`4` (urgent). Due dates are supplied as human-readable strings (e.g. `tomorrow at 4pm`, `every Monday`).

## Connection

Connect the **Todoist** integration with:

- **API Token** — copy your token from
  [Todoist Settings > Integrations > Developer](https://todoist.com/app/settings/integrations/developer).

The token is stored in Sophon's credential vault and supplied to the skill at call time; it is never
written into the skill.

## Notes

- `todoist.list_tasks` accepts a `filter` using Todoist's
  [filter query syntax](https://todoist.com/help/articles/introduction-to-filters), e.g.
  `today | overdue` or `p1 & #Work`. Filtering uses the dedicated `GET /tasks/filter` endpoint,
  which takes no project id, so combining `filter` with `projectId` narrows the returned tasks to
  that project afterwards.
- `limit` is passed to the API (1–200, default 30).
- `todoist.complete_task` closes the task and returns `{"closed": true}`; Todoist's API returns no
  content for this operation.
- API v1 no longer returns a `url` on tasks and projects, so `url` is derived from the id
  (`https://app.todoist.com/app/task/<id>`), which is the form the official client builds when it
  has no title slug to append.

## Trademarks

Todoist is a trademark of Doist Inc. This is an unofficial, independently built integration and is
not affiliated with or endorsed by Doist.
