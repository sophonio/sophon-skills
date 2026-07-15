# GitLab

Interact with GitLab from Sophon: triage and create issues, review and open merge requests, inspect
CI/CD pipelines, and — via a raw API passthrough — reach anything else in the REST API. Works with
gitlab.com and self-managed instances.

Implemented with the GitLab REST API v4 over the Python standard library (no dependencies), so it
runs in the sandbox unchanged.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `gitlab.list_issues` | none | List issues in a project (filter by state/labels) |
| `gitlab.get_issue` | none | Get one issue by internal id (iid) |
| `gitlab.create_issue` | medium | Open a new issue |
| `gitlab.list_merge_requests` | none | List merge requests (filter by state) |
| `gitlab.get_merge_request` | none | Get one merge request by internal id (iid) |
| `gitlab.create_merge_request` | medium | Open a merge request |
| `gitlab.list_pipelines` | none | List recent CI/CD pipelines |
| `gitlab.api` | high | Raw authenticated REST v4 request (escape hatch) |

Projects are addressed by numeric id (e.g. `123`) or by path (e.g. `group/project`); paths are
URL-encoded automatically.

## Connection

Connect the **GitLab** integration with:

- **Personal Access Token** — a [PAT](https://gitlab.com/-/user_settings/personal_access_tokens)
  with `api` scope.
- **GitLab Host** *(optional)* — set only for self-managed GitLab, e.g.
  `https://gitlab.example.com`. Defaults to `https://gitlab.com`. The base URL is built as
  `<host>/api/v4`.

The token is stored in Sophon's credential vault and supplied to the skill at call time; it is never
written into the skill.

## Notes

- Issues and merge requests are addressed by their project-scoped internal id (`iid`), the number
  shown in the GitLab UI, not the global database id.
- `gitlab.api` can make irreversible changes — it is marked high-risk so Sophon can gate it behind
  approval.

## Trademarks

GitLab is a trademark of GitLab B.V. This is an unofficial, independently built integration and is
not affiliated with or endorsed by GitLab.
