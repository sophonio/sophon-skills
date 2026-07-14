# Jira Skill

Atlassian Jira integration for Sophon — search issues, manage projects and tickets.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `jira.search` | None | Search issues using JQL |
| `jira.get_issue` | None | Get details of a specific issue |
| `jira.create_issue` | Medium | Create a new issue |
| `jira.list_projects` | None | List all accessible projects |

## Setup

1. Go to **Settings > Connections** in the Sophon Dashboard
2. Click **Connect** on the Jira card
3. Enter your Atlassian Cloud URL (e.g. `https://yourorg.atlassian.net`)
4. Enter your email and API token
5. Test the connection

Generate an API token at: https://id.atlassian.com/manage-profile/security/api-tokens

## Usage Examples

**Search for issues:**
> "Search Jira for open bugs assigned to me"

**Get issue details:**
> "Show me the details of PROJ-123"

**Create an issue:**
> "Create a Jira bug in project PROJ titled 'Login page 500 error'"

**List projects:**
> "Show me all Jira projects"

## Requirements

- Atlassian Cloud instance with Jira
- API token with read/write access to Jira

## Trademarks

Jira is a trademark of Atlassian Pty Ltd. This skill is an independent integration developed by Buildersoft LLC and is not affiliated with, endorsed by, or sponsored by Atlassian.

## License

MIT © 2026 Buildersoft LLC. See [LICENSE](LICENSE).
