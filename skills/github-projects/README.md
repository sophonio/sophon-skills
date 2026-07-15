# GitHub Projects

Work with **GitHub Projects (v2)** from Sophon: list an organization's or user's projects, inspect
the items on a board (with the linked issue/PR title and state), add draft issues, and move items
between statuses.

Implemented with the GitHub GraphQL API over the Python standard library (no dependencies), so it
runs in the sandbox unchanged.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `projects.list` | none | List projects (v2) owned by an org or user |
| `projects.get_items` | none | List items on a project, with linked issue/PR title and state |
| `projects.add_draft_issue` | medium | Add a draft issue to a project |
| `projects.update_item_status` | medium | Set a single-select field (e.g. Status) on an item |

Projects are addressed by their `owner` (org or user login) plus project `number` (from the project
URL). Mutations operate on GraphQL node ids (`projectId` `PVT_…`, `itemId` `PVTI_…`,
`fieldId` `PVTSSF_…`, and an `optionId`), which you can read from `projects.get_items` and the
project's field configuration.

## Connection

Connect the **GitHub Projects** integration with:

- **Personal Access Token** — a [fine-grained or classic PAT](https://github.com/settings/tokens)
  with `project` scope (add `repo` to resolve linked issues and pull requests). Grant only the
  organizations and permissions you need.

The token is stored in Sophon's credential vault and supplied to the skill at call time; it is never
written into the skill.

## Notes

- All calls go to `https://api.github.com/graphql`. GraphQL-level `errors` are surfaced as
  `{"error": "..."}`.
- `projects.add_draft_issue` and `projects.update_item_status` modify the board and are marked
  medium-risk so Sophon can gate them behind approval.

## Trademarks

GitHub is a trademark of GitHub, Inc. / Microsoft. This is an unofficial, independently built
integration and is not affiliated with or endorsed by GitHub.
