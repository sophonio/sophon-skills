# Todoist

Manage your Todoist tasks and projects from Sophon: list active tasks (optionally by project or a
filter query), list projects, add tasks, complete tasks, and update existing tasks.

Implemented with the Todoist REST API v2 over the Python standard library (no dependencies), so it
runs in the sandbox unchanged.

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
  `today | overdue` or `p1 & #Work`. Combine with `projectId` to scope to one project.
- `todoist.complete_task` closes the task and returns `{"closed": true}`; Todoist's API returns no
  content for this operation.

## Trademarks

Todoist is a trademark of Doist Inc. This is an unofficial, independently built integration and is
not affiliated with or endorsed by Doist.
