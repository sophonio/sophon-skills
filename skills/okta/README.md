# Okta Skill

Okta identity and access management integration for Sophon — search users and groups, inspect app assignments, query the system log, add users to groups, and suspend users via the Okta admin API.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `okta.search_users` | None | Search users by name/email prefix or SCIM-style filter |
| `okta.get_user` | None | Get a user's full profile, status, and lifecycle timestamps |
| `okta.list_groups` | None | List groups, optionally filtered by name prefix |
| `okta.list_group_members` | None | List the users in a group (paginated) |
| `okta.list_user_apps` | None | List the applications assigned to a user |
| `okta.query_system_log` | None | Query audit events by time window, filter, or keyword |
| `okta.add_user_to_group` | Medium | Add a user to a group |
| `okta.suspend_user` | High | Suspend an active user (reversible, but blocks sign-in immediately) |

## Setup

1. Sign in to your **Okta Admin Console** as an administrator. Prefer a dedicated, read-mostly service-account admin (e.g. Read-only Administrator plus only the group/user permissions you need) rather than a super admin — the API token inherits the permissions of the admin who creates it.
2. Go to **Security > API > Tokens** and click **Create token**. Give it a recognizable name (e.g. `sophon`) and copy the token value — it is shown only once.
3. (Recommended) Restrict the token to a network zone under **API token network restrictions** so it can only be used from expected IP ranges.
4. Note that Okta API tokens **expire after 30 days of non-use** (each successful use resets the clock). If the connection stops working after a period of inactivity, create a new token.
5. In Sophon, open **Settings > Connections**, click **Connect** on the Okta card, and fill in:
   - **Okta Org URL** — your org base URL, e.g. `https://acme.okta.com` (or `acme.okta-emea.com` for EMEA orgs, `acme.oktapreview.com` for preview orgs)
   - **API Token** — the SSWS token from step 2
6. Test the connection (this calls `/api/v1/users/me`, which returns the token owner).

## Usage Examples

> "Find the Okta user with the email ada@acme.com and show me her profile"

> "Which apps are assigned to user 00u1ab2c3d4e5f6g7h8i in Okta?"

> "List the members of the Engineering group in Okta"

> "Show me failed Okta sign-in events since yesterday"

> "Add user 00u1ab2c3d to the okta group 00g9xy8z7 and confirm"

## Requirements

- An Okta org (Workforce Identity) on `okta.com`, `okta-emea.com`, or `oktapreview.com`
- An admin account able to create SSWS API tokens; the token inherits that admin's permissions
- Read tools work with a read-only administrator; `okta.add_user_to_group` and `okta.suspend_user` require group-membership / user-lifecycle admin permissions
- Okta API rate limits apply per org; on HTTP 429 the error includes the `X-Rate-Limit-Reset` epoch

## Trademarks

Okta is a trademark of Okta, Inc. This project is not affiliated with or endorsed by Okta, Inc.

## License

MIT © 2026 Buildersoft LLC. See [LICENSE](LICENSE).
