# Jenkins Skill

Jenkins CI/CD integration for Sophon — browse jobs and folders, inspect builds and console logs, watch the build queue, and trigger builds.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `jenkins.list_jobs` | None | List jobs at the top level or inside a folder, with status |
| `jenkins.get_job` | None | Get a job's health, queue state, and recent build pointers |
| `jenkins.get_build` | None | Get a build's result, timing, parameters, causes, and changes |
| `jenkins.get_console_log` | None | Fetch a build's console log (by offset or last N KiB) |
| `jenkins.get_queue` | None | List items waiting in the build queue and why |
| `jenkins.trigger_build` | High | Trigger a build, optionally with parameters |

## Setup

1. Sign in to your Jenkins instance and open **{your Jenkins URL}/me/configure** (your user page > **Configure**)
2. Under **API Token**, click **Add new token**, give it a name (e.g. `sophon`), and click **Generate**
3. Copy the token immediately — Jenkins shows it only once
4. Make sure your Jenkins instance is reachable from Sophon. Many Jenkins servers sit behind a VPN or firewall; those cannot be reached and the connection test will fail
5. In Sophon, open **Settings > Connections**, click **Connect** on the Jenkins card, and fill in:
   - **Jenkins URL** — your instance base URL (e.g. `https://jenkins.example.com`)
   - **Username** — the account the token belongs to
   - **API Token** — the token you generated
6. Test the connection

No CSRF crumb setup is needed: requests authenticated with an API token are CSRF-exempt in Jenkins.

## Usage Examples

> "List the Jenkins jobs in the team-a folder"

> "What's the health of team-a/service-x and when did it last fail?"

> "Show me the last 100 KB of the console log for build 214 of service-x"

> "Is anything stuck in the Jenkins build queue?"

> "Trigger a build of team-a/service-x with BRANCH=release/2.4"

## Requirements

- A Jenkins instance (LTS 2.129+ for per-user API tokens) reachable from Sophon — VPN-only or private-network instances will not work
- A Jenkins account with **Overall/Read** and **Job/Read** permissions for the read tools
- **Job/Build** permission on the target job for `jenkins.trigger_build`

## Trademarks

Jenkins is a registered trademark of LF Charities Inc. This project is not affiliated with or endorsed by LF Charities Inc. or the Jenkins project.

## License

MIT © 2026 Buildersoft LLC. See [LICENSE](LICENSE).
