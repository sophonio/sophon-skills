# SonarQube Skill

SonarQube integration for Sophon — browse projects, check quality gates, search issues and
security hotspots, read metrics and analysis history, and assign issues via the SonarQube
Web API. Works with SonarQube Server 10.0+ (including the free Community Build) and
SonarQube Cloud.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `sonar.search_projects` | None | List projects with key, name, and last analysis date |
| `sonar.get_quality_gate_status` | None | Quality gate status plus failing conditions (metric, actual vs threshold) |
| `sonar.search_issues` | None | Search issues by project, severity, type, status, assignee |
| `sonar.search_hotspots` | None | Search a project's security hotspots |
| `sonar.get_measures` | None | Current metric values for a component (coverage, duplication, ratings, ...) |
| `sonar.get_analysis_history` | None | Historical metric values as date/value series |
| `sonar.assign_issue` | Medium | Assign an issue to a user (or unassign it) |

## Setup

1. Log in to your SonarQube Server (10.0+ — the token is sent as a `Authorization: Bearer`
   header, which older servers do not accept) or SonarQube Cloud. The free Community Build
   works fine.
2. Go to **My Account > Security > Generate Tokens** and create a **User Token**. Copy it —
   it is shown only once.
3. The token inherits your permissions: you need **Browse** on the projects you want to
   query, and `sonar.assign_issue` additionally requires permission to update issues on the
   target project.
4. SonarQube Cloud only: note your **organization key** (visible in your organization's URL
   and settings); it is appended as an `organization=` query parameter on every request.
   Leave it empty for self-hosted servers.
5. Go to **Settings > Connections** in the Sophon Dashboard, click **Connect** on the
   SonarQube card, and enter the server URL, token, and (for Cloud) the organization key.
6. Test the connection. Heads-up: SonarQube's `/api/authentication/validate` endpoint
   returns HTTP 200 with `{"valid": false}` when the token is wrong — validity is judged
   from the response body, not the status code.

## Usage Examples

**Check a quality gate:**
> "What's the quality gate status of my-service, and which conditions are failing?"

**Find serious issues:**
> "Search SonarQube for open BLOCKER and CRITICAL bugs in my-service"

**Review security hotspots:**
> "List the security hotspots still to review in my-service"

**Track coverage:**
> "Show me the coverage and duplication history of my-service over the last analyses"

**Triage:**
> "Assign SonarQube issue AXi4-abc123 to jane.doe"

## Requirements

- SonarQube Server 10.0 or later (Community Build included) or SonarQube Cloud
- A user token (My Account > Security); permissions follow the token owner's
- SonarQube Cloud: the organization key must be set on the connection
- SonarQube Cloud rate-limits API calls; a 429 response is surfaced with a backoff hint

## Trademarks

SONARQUBE and SONAR are trademarks of SonarSource SA. This skill is an independent
integration developed by Buildersoft LLC and is not affiliated with, endorsed by, or
sponsored by SonarSource.

## License

MIT © 2026 Buildersoft LLC. See [LICENSE](LICENSE).
