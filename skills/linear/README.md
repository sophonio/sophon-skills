# Linear

Interact with Linear from Sophon: search issues, read issue details, list teams, create and update
issues, and add comments.

Implemented with the Linear GraphQL API over the Python standard library (no dependencies), so it
runs in the sandbox unchanged.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `linear.search_issues` | none | Search issues by free-text query |
| `linear.get_issue` | none | Get one issue by UUID or identifier (e.g. `ENG-123`) |
| `linear.list_teams` | none | List teams with their id, name, and key |
| `linear.create_issue` | medium | Create a new issue in a team |
| `linear.update_issue` | medium | Update fields on an existing issue |
| `linear.add_comment` | medium | Add a comment to an issue |

Issues can be addressed either by their UUID or by their human identifier such as `ENG-123`;
`create_issue` and `update_issue` take a team/user/state UUID for those fields (use `list_teams`
to find team ids).

## Connection

Connect the **Linear** integration with:

- **Personal API Key** — create one in your
  [Linear API settings](https://linear.app/settings/api). The key carries the read/write
  permissions of your account.

The key is stored in Sophon's credential vault and supplied to the skill at call time; it is never
written into the skill. Linear authenticates with a bare `Authorization` header (no `Bearer`
prefix).

## Notes

- `linear.create_issue`, `linear.update_issue`, and `linear.add_comment` change data and are marked
  medium-risk so Sophon can gate them behind approval.
- Priority values are Linear's own scale: `0` none, `1` urgent, `2` high, `3` normal, `4` low.

## Trademarks

Linear is a trademark of Linear Orbit, Inc. This is an unofficial, independently built integration
and is not affiliated with or endorsed by Linear.
